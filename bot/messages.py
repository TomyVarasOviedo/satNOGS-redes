from __future__ import annotations

import html
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

MAX_MESSAGE = 4000
UTC = ZoneInfo("UTC")


def esc(value) -> str:
    return html.escape("" if value is None else str(value), quote=False)


def parse_iso(value: str) -> datetime:
    moment = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def _clock(value: str, tz: ZoneInfo) -> str:
    moment = parse_iso(value)
    local = moment.astimezone(tz)
    return f"{moment:%H:%M} UTC ({local:%H:%M} local)"


def _date(value: str, tz: ZoneInfo) -> str:
    return parse_iso(value).astimezone(tz).strftime("%d/%m")


def _mhz(hz) -> str:
    return f"{float(hz) / 1e6:.3f} MHz"


def _number(value, fmt: str, default: str = "?") -> str:
    try:
        return format(float(value), fmt)
    except (TypeError, ValueError):
        return default


def _margin(link: dict | None, key: str) -> float | None:
    if not link:
        return None
    try:
        return float(link.get(key))
    except (TypeError, ValueError):
        return None


def source_note(source: str | None) -> str:
    if source == "stale":
        return "\n<i>⚠️ Datos de caché: pueden estar desactualizados.</i>"
    if source == "cache":
        return "\n<i>Datos de caché.</i>"
    return ""


def combine_sources(sources) -> str:
    values = set(sources)
    for candidate in ("stale", "cache", "live"):
        if candidate in values:
            return candidate
    return next(iter(values), "live")


def _pass_line(satellite_pass: dict, tz: ZoneInfo, with_date: bool = True) -> str:
    prefix = f"{_date(satellite_pass['aos'], tz)} " if with_date else ""
    elevation = _number(satellite_pass.get("max_elevation_deg"), ".0f") + "°"
    margin = _margin(satellite_pass.get("link"), "margin_at_tca_db")
    if margin is None:
        margin_text = "sin margen"
    else:
        margin_text = f"{margin:+.1f} dB " + ("✅" if margin >= 0 else "❌")
    return f"• {prefix}{_clock(satellite_pass['aos'], tz)} · {elevation} · {margin_text}"


def format_pass_alert(
    sat_name: str,
    satellite_pass: dict,
    doppler: dict | None = None,
    tz: ZoneInfo = UTC,
    source: str | None = None,
    minutes_to_aos: int | None = None,
) -> str:
    if minutes_to_aos is None:
        when = "Próximo pase"
    elif minutes_to_aos <= 0:
        when = "Pase en curso"
    elif minutes_to_aos == 1:
        when = "Pasa en 1 min"
    else:
        when = f"Pasa en {minutes_to_aos} min"

    duration = satellite_pass.get("duration_s")
    duration_text = f"{max(1, round(duration / 60))} min" if duration else "?"

    lines = [
        f"🛰️ <b>{esc(sat_name)}</b> — {when}",
        f"AOS {_clock(satellite_pass['aos'], tz)} · LOS {_clock(satellite_pass['los'], tz)} · {duration_text}",
    ]

    elevation = satellite_pass.get("max_elevation_deg")
    if elevation is not None:
        geometry = f"Elev. máx {_number(elevation, '.0f')}°"
        az_aos = satellite_pass.get("aos_azimuth_deg")
        az_los = satellite_pass.get("los_azimuth_deg")
        if az_aos is not None and az_los is not None:
            geometry += f" · az {_number(az_aos, '.0f')}° → {_number(az_los, '.0f')}°"
        lines.append(geometry)

    link = satellite_pass.get("link") or {}
    tuning = []
    if doppler:
        for label, hz in (
            ("AOS", doppler.get("aos_frequency_hz")),
            ("TCA", doppler.get("f0_hz")),
            ("LOS", doppler.get("los_frequency_hz")),
        ):
            if hz:
                tuning.append(f"{label} {_mhz(hz)}")
    elif link.get("freq_hz"):
        tuning.append(f"nominal {_mhz(link['freq_hz'])}")
    if tuning:
        lines.append("Sintonizar: " + " → ".join(tuning))

    margin_aos = _margin(link, "margin_at_aos_db")
    margin_tca = _margin(link, "margin_at_tca_db")
    if margin_aos is not None or margin_tca is not None:
        parts = []
        if margin_aos is not None:
            parts.append(f"{margin_aos:+.1f} dB en AOS")
        if margin_tca is not None:
            parts.append(f"{margin_tca:+.1f} dB en TCA")
        verdict = ""
        if margin_tca is not None:
            verdict = " ✅ decodable" if margin_tca >= 0 else " ❌ sin margen"
        lines.append("Margen: " + " · ".join(parts) + verdict)
    elif link:
        detail = []
        if link.get("mode"):
            detail.append(f"modo {esc(link['mode'])}")
        if link.get("baud"):
            detail.append(f"{_number(link.get('baud'), 'g')} baud")
        lines.append("Margen no calculable" + (f" ({', '.join(detail)})" if detail else "") + ".")
    else:
        lines.append("Sin datos de enlace para este pase.")

    return "\n".join(lines) + source_note(source)


def format_passes(entries, tz: ZoneInfo = UTC, source: str | None = None) -> str:
    lines = ["📡 <b>Próximos pases</b>"]
    for sat_name, passes in entries:
        lines.extend(["", f"<b>{esc(sat_name)}</b>"])
        if passes:
            lines.extend(_pass_line(satellite_pass, tz) for satellite_pass in passes)
        else:
            lines.append("• sin pases sobre la máscara")
    return "\n".join(lines) + source_note(source)


def format_agenda(entries, tz: ZoneInfo = UTC, source: str | None = None) -> str:
    lines = ["📅 <b>Agenda próximas 24 h</b>"]
    for sat_name, passes in entries:
        lines.extend(["", f"<b>{esc(sat_name)}</b>"])
        if passes:
            lines.extend(_pass_line(satellite_pass, tz, with_date=False) for satellite_pass in passes)
        else:
            lines.append("• sin pases sobre la máscara")
    return "\n".join(lines) + source_note(source)


def format_orbit(
    sat_name: str,
    orbit: dict,
    tle_max_age_days: float | None = None,
    source: str | None = None,
) -> str:
    lines = [
        f"🛰️ <b>{esc(sat_name)}</b> · {esc(orbit.get('orbit_type') or '?')}",
        f"Período {_number(orbit.get('period_min'), '.1f')} min · altura {_number(orbit.get('altitude_km'), '.0f')} km",
        f"Inclinación {_number(orbit.get('inclination_deg'), '.1f')}° · huella {_number(orbit.get('footprint_radius_km'), '.0f')} km",
    ]
    age = orbit.get("tle_age_days")
    if age is not None:
        line = f"TLE: {_number(age, '.1f')} días"
        if tle_max_age_days is not None and age > tle_max_age_days:
            line += f" ⚠️ (máximo sugerido {tle_max_age_days:g})"
        lines.append(line)
    return "\n".join(lines) + source_note(source)


def format_tle_warning(
    sat_name: str,
    orbit: dict,
    max_age_days: float,
    source: str | None = None,
) -> str:
    lines = [
        f"⚠️ <b>TLE de {esc(sat_name)} desactualizado</b>",
        f"Antigüedad: {_number(orbit.get('tle_age_days'), '.1f')} días (máximo sugerido {max_age_days:g}).",
        "La predicción de pases y Doppler puede desviarse; conviene actualizar el TLE.",
    ]
    if orbit.get("orbit_type"):
        lines.append(
            f"Órbita: {esc(orbit.get('orbit_type'))} · altura {_number(orbit.get('altitude_km'), '.0f')} km"
        )
    return "\n".join(lines) + source_note(source)


def format_help(names: list[str] | None = None) -> str:
    lines = [
        "🛰️ <b>NOC Satelital — bot de alertas</b>",
        "",
        "<b>Comandos</b>",
        "/pases [satélite] [días] — próximos pases",
        "/proximo [satélite] — próximo pase con Doppler",
        "/agenda — agenda de las próximas 24 h",
        "/tle [satélite] — órbita y antigüedad del TLE",
        "/test [5|10] — modo prueba con escaneo rápido",
        "/stop — vuelve al tiempo normal",
        "",
    ]
    if names:
        lines.append("<b>Satélites monitoreados</b>")
        lines.extend(f"• {esc(name)}" for name in names)
    else:
        lines.append("No pude leer la lista de satélites del backend.")
    return "\n".join(lines)


def format_test_mode(scan_seconds: int, lead_min: int, sent: int) -> str:
    lines = [
        "🧪 <b>Modo prueba activado</b>",
        f"Escaneo cada {scan_seconds} s · alerta T-{lead_min} min.",
        f"Alertas enviadas en el escaneo inmediato: {sent}.",
        "Usá /stop para volver al tiempo normal.",
    ]
    return "\n".join(lines)


def format_normal_mode(scan_interval_min: int, lead_min: int) -> str:
    lines = [
        "✅ <b>Modo prueba desactivado</b>",
        f"Escaneo normal cada {scan_interval_min} min · alerta T-{lead_min} min.",
        "El bot sigue funcionando.",
    ]
    return "\n".join(lines)


def format_error(message: str) -> str:
    return f"⚠️ {esc(message)}"


def chunk(text: str, limit: int = MAX_MESSAGE) -> list[str]:
    if len(text) <= limit:
        return [text]

    parts: list[str] = []
    current = ""
    for line in text.splitlines(keepends=True):
        while len(line) > limit:
            if current:
                parts.append(current)
                current = ""
            parts.append(line[:limit])
            line = line[limit:]
        if len(current) + len(line) > limit:
            parts.append(current)
            current = ""
        current += line
    if current:
        parts.append(current)
    return parts or [text[:limit]]
