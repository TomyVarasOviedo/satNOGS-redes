from __future__ import annotations

import argparse
import asyncio
import logging
from datetime import datetime, time, timezone

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, ContextTypes, TypeHandler

from alerts import AlertService, parse_iso, send_chunks
from api import ApiError, NocApi
from chat_store import ChatStore
from config import Settings, load_settings
from messages import (
    combine_sources,
    format_error,
    format_help,
    format_normal_mode,
    format_orbit,
    format_pass_alert,
    format_passes,
    format_test_mode,
)
from runtime import Runtime
from state import State

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _settings(context: ContextTypes.DEFAULT_TYPE) -> Settings:
    return context.application.bot_data["settings"]


def _api(context: ContextTypes.DEFAULT_TYPE) -> NocApi:
    return context.application.bot_data["api"]


def _service(context: ContextTypes.DEFAULT_TYPE) -> AlertService:
    return context.application.bot_data["service"]


def _chats(context: ContextTypes.DEFAULT_TYPE) -> ChatStore:
    return context.application.bot_data["chats"]


def _runtime(context: ContextTypes.DEFAULT_TYPE) -> Runtime:
    return context.application.bot_data["runtime"]


def _split_args(args: list[str], allow_days: bool = False) -> tuple[str | None, int | None]:
    parts = list(args)
    days = None
    if allow_days and parts and parts[-1].isdigit():
        days = int(parts.pop())
    name = " ".join(parts).strip() or None
    return name, days


async def _pairs(api: NocApi, name: str | None) -> list[tuple[str, str]]:
    if name:
        sat_id = await api.resolve_sat_id(name)
        return [(name, sat_id)]

    result = await api.monitored()
    pairs: list[tuple[str, str]] = []
    for item in result.data if isinstance(result.data, list) else []:
        sat_name = (item.get("name") or "").strip()
        if not sat_name:
            continue
        try:
            pairs.append((sat_name, await api.resolve_sat_id(sat_name)))
        except ApiError as exc:
            logger.warning("No se pudo resolver %s: %s", sat_name, exc)
    return pairs


async def _reply(update: Update, text: str) -> None:
    await update.message.reply_text(
        text,
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True,
    )


async def remember_chat(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not isinstance(update, Update) or update.effective_chat is None:
        return
    try:
        _chats(context).remember(update.effective_chat.id)
    except Exception:
        logger.exception("No se pudo guardar el chat de alertas")


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    names: list[str] = []
    try:
        result = await _api(context).monitored()
        names = [item.get("name") for item in result.data if item.get("name")]
    except ApiError as exc:
        logger.warning("Sin lista de satélites: %s", exc)
    await _reply(update, format_help(names))


async def cmd_passes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = _settings(context)
    name, days = _split_args(context.args, allow_days=True)
    days = max(1, min(7, days or 2))

    try:
        pairs = await _pairs(_api(context), name)
    except ApiError as exc:
        await _reply(update, format_error(str(exc)))
        return
    if not pairs:
        await _reply(update, format_error("No hay satélites para consultar."))
        return

    entries: list[tuple[str, list[dict]]] = []
    sources: set[str] = set()
    for sat_name, sat_id in pairs:
        try:
            result = await _api(context).passes(
                sat_id,
                days=days,
                horizon_deg=settings.min_elevation_deg,
            )
        except ApiError as exc:
            logger.warning("No se pudieron leer pases de %s: %s", sat_name, exc)
            continue
        passes = result.data.get("passes", []) if isinstance(result.data, dict) else []
        entries.append((sat_name, passes[:8]))
        sources.add(result.source)

    if not entries:
        await _reply(update, format_error("No pude obtener pases del backend."))
        return

    await send_chunks(
        context.bot,
        update.effective_chat.id,
        format_passes(entries, settings.tz, combine_sources(sources)),
    )


async def cmd_next(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = _settings(context)
    name, _ = _split_args(context.args)

    try:
        pairs = await _pairs(_api(context), name)
    except ApiError as exc:
        await _reply(update, format_error(str(exc)))
        return
    if not pairs:
        await _reply(update, format_error("No hay satélites para consultar."))
        return

    now = datetime.now(timezone.utc)
    blocks: list[str] = []
    for sat_name, sat_id in pairs:
        try:
            result = await _api(context).passes(
                sat_id,
                days=2,
                horizon_deg=settings.min_elevation_deg,
            )
        except ApiError as exc:
            logger.warning("No se pudieron leer pases de %s: %s", sat_name, exc)
            continue

        passes = result.data.get("passes", []) if isinstance(result.data, dict) else []
        if not passes:
            continue

        satellite_pass = passes[0]
        doppler = None
        try:
            doppler = (await _api(context).doppler(sat_id, start=satellite_pass["aos"])).data
        except ApiError as exc:
            logger.info("Sin Doppler para %s: %s", sat_name, exc)

        minutes = round((parse_iso(satellite_pass["aos"]) - now).total_seconds() / 60)
        blocks.append(
            format_pass_alert(
                sat_name,
                satellite_pass,
                doppler,
                settings.tz,
                result.source,
                minutes,
            )
        )

    if not blocks:
        await _reply(update, format_error("No hay pases en los próximos 2 días."))
        return

    await send_chunks(context.bot, update.effective_chat.id, "\n\n".join(blocks))


async def cmd_agenda(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    service = _service(context)
    try:
        count = await service.send_agenda(context.bot, update.effective_chat.id, force=True)
    except ApiError as exc:
        await _reply(update, format_error(str(exc)))
        return
    if count == 0:
        await _reply(update, format_error("No hay pases para las próximas 24 h."))


async def cmd_tle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = _settings(context)
    name, _ = _split_args(context.args)

    try:
        pairs = await _pairs(_api(context), name)
    except ApiError as exc:
        await _reply(update, format_error(str(exc)))
        return
    if not pairs:
        await _reply(update, format_error("No hay satélites para consultar."))
        return

    blocks: list[str] = []
    for sat_name, sat_id in pairs:
        try:
            result = await _api(context).orbit(sat_id)
        except ApiError as exc:
            logger.warning("No se pudo leer la órbita de %s: %s", sat_name, exc)
            continue
        blocks.append(
            format_orbit(
                sat_name,
                result.data,
                settings.tle_max_age_days,
                result.source,
            )
        )

    if not blocks:
        await _reply(update, format_error("No pude obtener datos orbitales del backend."))
        return

    await send_chunks(context.bot, update.effective_chat.id, "\n\n".join(blocks))


async def cmd_test(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = _settings(context)
    seconds = settings.test_scan_seconds
    if context.args:
        if not context.args[0].isdigit():
            await _reply(update, format_error("Usá /test, /test 5 o /test 10."))
            return
        seconds = int(context.args[0])
    if seconds not in (5, 10):
        await _reply(update, format_error("El intervalo de prueba debe ser 5 o 10 segundos."))
        return

    runtime = _runtime(context)
    runtime.enter_test(seconds)
    try:
        sent = await _service(context).scan_pass_alerts(context.bot, ignore_dedup=True)
    except Exception:
        logger.exception("Error en el escaneo de prueba")
        sent = 0
    await _reply(update, format_test_mode(seconds, runtime.lead_min, sent))


async def cmd_stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings = _settings(context)
    _runtime(context).stop_test()
    await _reply(
        update,
        format_normal_mode(settings.pass_scan_interval_min, settings.alert_lead_min),
    )


async def pass_alert_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    runtime = _runtime(context)
    now = datetime.now(timezone.utc)
    if not runtime.due(now):
        return
    runtime.mark_scan(now)
    if _chats(context).chat_id is None:
        return
    try:
        await _service(context).scan_pass_alerts(context.bot)
    except Exception:
        logger.exception("Error en la alerta de pases")


async def daily_job(context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = _chats(context).chat_id
    if chat_id is None:
        return

    service = _service(context)
    try:
        await service.send_agenda(context.bot, chat_id)
    except Exception:
        logger.exception("Error en la agenda diaria")
    try:
        await service.send_tle_warnings(context.bot, chat_id)
    except Exception:
        logger.exception("Error en los avisos de TLE")


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Error no controlado: %s", context.error, exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                format_error("Ocurrió un error al procesar el comando."),
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass


async def post_stop(application: Application) -> None:
    api = application.bot_data.get("api")
    if api is not None:
        await api.aclose()


def build_application(settings: Settings) -> Application:
    application = Application.builder().token(settings.bot_token).post_stop(post_stop).build()
    api = NocApi(settings.backend_url)
    chats = ChatStore(settings.chat_id_file, settings.chat_id)
    runtime = Runtime(settings)
    application.bot_data.update(
        settings=settings,
        api=api,
        chats=chats,
        runtime=runtime,
        service=AlertService(
            api,
            State(settings.state_path),
            settings,
            chats,
            runtime,
        ),
    )

    application.add_handler(TypeHandler(Update, remember_chat), group=-1)
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("help", cmd_start))
    application.add_handler(CommandHandler("pases", cmd_passes))
    application.add_handler(CommandHandler("proximo", cmd_next))
    application.add_handler(CommandHandler("agenda", cmd_agenda))
    application.add_handler(CommandHandler("tle", cmd_tle))
    application.add_handler(CommandHandler("test", cmd_test))
    application.add_handler(CommandHandler("stop", cmd_stop))
    application.add_error_handler(on_error)

    if application.job_queue is None:
        logger.error("JobQueue no disponible; instalá python-telegram-bot[job-queue].")
        return application

    tick = max(1, min(5, settings.test_scan_seconds))
    application.job_queue.run_repeating(
        pass_alert_job,
        interval=tick,
        first=tick,
        name="pass_alerts",
    )
    application.job_queue.run_daily(
        daily_job,
        time=time(hour=settings.agenda_hour_utc, tzinfo=timezone.utc),
        name="daily_agenda",
    )
    if chats.chat_id is None:
        logger.info("Sin chat configurado: se guardará el último chat que hable con el bot.")
    return application


class PrintBot:
    """Reemplazo mínimo de Bot para --demo: imprime en vez de enviar a Telegram."""

    async def send_message(self, chat_id: int, text: str, **kwargs) -> None:
        print(text)
        print("-" * 60)


async def run_demo() -> None:
    settings = load_settings(require_token=False)
    api = NocApi(settings.backend_url)
    chats = ChatStore(settings.chat_id_file, settings.chat_id)
    runtime = Runtime(settings)
    service = AlertService(api, State(settings.state_path), settings, chats, runtime)
    bot = PrintBot()
    chat_id = chats.chat_id or 0
    try:
        try:
            count = await service.send_agenda(bot, chat_id, force=True)
            if count == 0:
                print("No se pudo obtener la agenda del backend.")
        except ApiError as exc:
            print(f"No se pudo obtener la agenda: {exc}")

        try:
            stale = await service.send_tle_warnings(bot, chat_id, force=True)
            if stale == 0:
                print("No hay TLE vencidos.")
        except ApiError as exc:
            print(f"No se pudieron revisar los TLE: {exc}")
    finally:
        await api.aclose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Bot de alertas del NOC Satelital")
    parser.add_argument(
        "--demo",
        action="store_true",
        help="imprime agenda y avisos de TLE una vez y sale; no requiere token",
    )
    args = parser.parse_args()

    if args.demo:
        asyncio.run(run_demo())
        return

    try:
        settings = load_settings()
    except ValueError as exc:
        raise SystemExit(str(exc))

    application = build_application(settings)
    logger.info("Bot iniciado; backend en %s", settings.backend_url)
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
