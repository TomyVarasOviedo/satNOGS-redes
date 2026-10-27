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


def _local_time(value: str, tz: ZoneInfo) -> str:
    return parse_iso(value).astimezone(tz).strftime("%H:%M")


def _utc_time(value: str) -> str:
    return parse_iso(value).astimezone(UTC).strftime("%H:%M")


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


def _tag(label: str) -> str:
    return f"<code>{esc(label)}</code>"


def _header(tag: str, title: str, suffix: str | None = None) -> str:
    text = f"{_tag(tag)} · <b>{esc(title)}</b>"
    if suffix:
        text += f" · {esc(suffix)}"
    return text


def _tz_name(tz: ZoneInfo) -> str:
    key = getattr(tz, "key", "") or str(tz)
    if key == "UTC":
        return "UTC"
    return key.rsplit("/", 1)[-1].replace("_", " ")


def _footer(source: str | None) -> str:
    status = {
        "live": "● live",
        "cache": "◐ caché",
        "stale": "○ caché vencida",
    }.get(source or "")
    parts = [status, "NOC Satelital"] if status else ["NOC Satelital"]
    return f"<i>{' · '.join(parts)}</i>"


def source_note(source: str | None) -> str:
    if source == "stale":
        return (
            "\n\n<blockquote>⚠️ Datos de caché vencidos: "
            "la predicción puede estar desactualizada.</blockquote>\n"
            + _footer(source)
        )
    return "\n\n" + _footer(source)


def combine_sources(sources) -> str:
    values = set(sources)
    for candidate in ("stale", "cache", "live"):
        if candidate in values:
            return candidate
    return next(iter(values), "live")


def _time_range(
    aos: str,
    los: str,
    tz: ZoneInfo,
    duration_text: str | None = None,
) -> str:
    local = f"{_local_time(aos, tz)}–{_local_time(los, tz)}"
    utc = f"{_utc_time(aos)}–{_utc_time(los)}"
    is_utc = getattr(tz, "key", None) == "UTC" or str(tz) == "UTC"
    text = f"{utc} UTC" if is_utc else f"{local} local · {utc} UTC"
    if duration_text:
        text += f" · {duration_text}"
    return text


def _pass_strip(satellite_pass: dict, tz: ZoneInfo) -> str:
    link = satellite_pass.get("link") or {}
    aos = satellite_pass["aos"]
    los = satellite_pass["los"]
    tca = satellite_pass.get("tca") or aos
    elevation = _number(satellite_pass.get("max_elevation_deg"), ".0f")
    az_aos = satellite_pass.get("aos_azimuth_deg")
    az_los = satellite_pass.get("los_azimuth_deg")
    margin_tca = _margin(link, "margin_at_tca_db")

    aos_tail = f"AZ {_number(az_aos, '.0f')}°" if az_aos is not None else ""
    los_tail = f"AZ {_number(az_los, '.0f')}°" if az_los is not None else ""
    tca_tail = f"{elevation}°"
    if margin_tca is not None:
        tca_tail += f"   {margin_tca:+.1f} dB"

    rows = [
        f"{_local_time(aos, tz)}  AOS   ↗  {aos_tail}".rstrip(),
        f"{_local_time(tca, tz)}  TCA   ▲  {tca_tail}".rstrip(),
        f"{_local_time(los, tz)}  LOS   ↘  {los_tail}".rstrip(),
    ]
    return "<pre>" + "\n".join(rows) + "</pre>"


def _pass_header(with_date: bool = True) -> str:
    if with_date:
        return "FECHA  PASE       ELEV  MARGEN"
    return "PASE       ELEV  MARGEN"


def _pass_row(satellite_pass: dict, tz: ZoneInfo, with_date: bool = True) -> str:
    date = f"{_date(satellite_pass['aos'], tz)}  " if with_date else ""
    times = (
        f"{_local_time(satellite_pass['aos'], tz)}–"
        f"{_local_time(satellite_pass['los'], tz)}"
    )
    elevation = f"{_number(satellite_pass.get('max_elevation_deg'), '.0f')}°"
    margin = _margin(satellite_pass.get("link"), "margin_at_tca_db")
    margin_text = "sin margen" if margin is None else f"{margin:+.1f} dB"
    return f"{date}{times}  {elevation:>4}  {margin_text:>10}"


def _ledger(
    passes: list[dict],
    tz: ZoneInfo,
    with_date: bool,
    header: bool = True,
) -> str:
    lines = [_pass_header(with_date)] if header else []
    lines.extend(_pass_row(satellite_pass, tz, with_date) for satellite_pass in passes)
    return "<pre>" + "\n".join(lines) + "</pre>"


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

    link = satellite_pass.get("link") or {}
    lines = [
        _header("PASS", sat_name, when),
        f"<i>{_time_range(satellite_pass['aos'], satellite_pass['los'], tz, duration_text)}</i>",
        "",
        _pass_strip(satellite_pass, tz),
    ]

    tuning: list[str] = []
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

    details: list[str] = []
    if tuning:
        details.append("SINTONÍA  " + " · ".join(tuning))

    margin_aos = _margin(link, "margin_at_aos_db")
    margin_tca = _margin(link, "margin_at_tca_db")
    if margin_aos is not None or margin_tca is not None:
        parts: list[str] = []
        if margin_aos is not None:
            parts.append(f"{margin_aos:+.1f} dB AOS")
        if margin_tca is not None:
            parts.append(f"{margin_tca:+.1f} dB TCA")
            parts.append("DECODABLE" if margin_tca >= 0 else "SIN MARGEN")
        details.append("ENLACE    " + " · ".join(parts))
    elif link:
        detail: list[str] = []
        if link.get("mode"):
            detail.append(f"modo {esc(link['mode'])}")
        if link.get("baud"):
            detail.append(f"{_number(link.get('baud'), 'g')} baud")
        suffix = f" · {', '.join(detail)}" if detail else ""
        details.append("ENLACE    sin margen calculable" + suffix)
    else:
        details.append("ENLACE    sin datos de enlace")

    if details:
        lines.append("")
        lines.extend(details)

    return "\n".join(lines) + source_note(source)


def format_passes(entries, tz: ZoneInfo = UTC, source: str | None = None) -> str:
    lines = [
        _header("PASS", "Próximos pases"),
        f"<i>Horarios en {esc(_tz_name(tz))}.</i>",
    ]
    for sat_name, passes in entries:
        lines.extend(["", f"<b>{esc(sat_name)}</b>"])
        if passes:
            lines.append(_ledger(passes, tz, with_date=True))
        else:
            lines.append("<i>Sin pases sobre la máscara.</i>")
    return "\n".join(lines) + source_note(source)


def format_agenda(entries, tz: ZoneInfo = UTC, source: str | None = None) -> str:
    lines = [
        _header("AGENDA", "Próximas 24 h"),
        f"<i>Horarios en {esc(_tz_name(tz))}.</i>",
    ]
    for sat_name, passes in entries:
        lines.extend(["", f"<b>{esc(sat_name)}</b>"])
        if passes:
            lines.append(_ledger(passes, tz, with_date=True))
        else:
            lines.append("<i>Sin pases en las próximas 24 h.</i>")
    return "\n".join(lines) + source_note(source)


def format_orbit(
    sat_name: str,
    orbit: dict,
    tle_max_age_days: float | None = None,
    source: str | None = None,
) -> str:
    orbit_type = orbit.get("orbit_type") or "?"
    rows = [
        f"PERÍODO  {_number(orbit.get('period_min'), '.1f')} min",
        f"ALTURA   {_number(orbit.get('altitude_km'), '.0f')} km",
        f"INCLIN.  {_number(orbit.get('inclination_deg'), '.1f')}°",
        f"HUELLA   {_number(orbit.get('footprint_radius_km'), '.0f')} km",
    ]
    age = orbit.get("tle_age_days")
    if age is not None:
        rows.append(f"TLE      {_number(age, '.1f')} días")

    lines = [
        _header("TLE", sat_name, orbit_type),
        "",
        "<pre>" + "\n".join(rows) + "</pre>",
    ]
    if age is not None and tle_max_age_days is not None and age > tle_max_age_days:
        lines.extend(
            [
                "",
                "<blockquote>⚠️ TLE mayor al máximo sugerido "
                f"({tle_max_age_days:g} días): la predicción puede desviarse.</blockquote>",
            ]
        )
    return "\n".join(lines) + source_note(source)


def format_tle_warning(
    sat_name: str,
    orbit: dict,
    max_age_days: float,
    source: str | None = None,
) -> str:
    rows = [
        f"ANTIGÜEDAD  {_number(orbit.get('tle_age_days'), '.1f')} días",
        f"MÁXIMO      {max_age_days:g} días",
    ]
    if orbit.get("orbit_type"):
        rows.append(
            f"ÓRBITA      {esc(orbit.get('orbit_type'))} · "
            f"{_number(orbit.get('altitude_km'), '.0f')} km"
        )

    lines = [
        _header("TLE", sat_name, "desactualizado"),
        "",
        "<pre>" + "\n".join(rows) + "</pre>",
        "",
        "<blockquote>⚠️ TLE mayor al máximo sugerido "
        f"({max_age_days:g} días). Actualizalo antes de operar.</blockquote>",
    ]
    return "\n".join(lines) + source_note(source)


def format_help(names: list[str] | None = None) -> str:
    lines = [
        _header("HELP", "NOC Satelital"),
        "<i>Pases, Doppler y margen de enlace para tus satélites.</i>",
        "",
        "<b>Comandos</b>",
        "<b>/pases</b> [satélite] [días] — próximos pases",
        "<b>/proximo</b> [satélite] — próximo pase con Doppler",
        "<b>/agenda</b> — próximas 24 h",
        "<b>/tle</b> [satélite] — órbita y antigüedad del TLE",
        "<b>/test</b> [5|10] — escaneo rápido",
        "<b>/stop</b> — modo normal",
        "",
        "<b>Cómo leer un pase</b>",
        "AOS inicio · TCA punto más alto · LOS fin",
        "● live · ◐ caché · ○ caché vencida",
        "",
    ]
    if names:
        lines.append("<b>Satélites monitoreados</b>")
        lines.append(" · ".join(esc(name) for name in names))
    else:
        lines.append("No pude leer la lista de satélites del backend.")
    return "\n".join(lines)


def format_test_mode(scan_seconds: int, lead_min: int, sent: int) -> str:
    lines = [
        _header("TEST", "Modo prueba activado"),
        "",
        "<pre>"
        + "\n".join(
            [
                f"ESCANEO   cada {scan_seconds} s",
                f"ALERTA    T-{lead_min} min",
                f"ENVIADAS  {sent}",
            ]
        )
        + "</pre>",
        "",
        "Usá /stop para volver al modo normal.",
    ]
    return "\n".join(lines)


def format_normal_mode(scan_interval_min: int, lead_min: int) -> str:
    lines = [
        _header("NORMAL", "Modo prueba desactivado"),
        "",
        "<pre>"
        + "\n".join(
            [
                f"ESCANEO   cada {scan_interval_min} min",
                f"ALERTA    T-{lead_min} min",
            ]
        )
        + "</pre>",
        "",
        "El bot sigue funcionando.",
    ]
    return "\n".join(lines)


def format_error(message: str) -> str:
    return f"<code>ERROR</code>\n{esc(message)}"


def _chunk_lines(text: str, limit: int) -> list[str]:
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


def chunk(text: str, limit: int = MAX_MESSAGE) -> list[str]:
    if len(text) <= limit:
        return [text]
    if "<pre>" not in text and "<code>" not in text:
        return _chunk_lines(text, limit)

    parts: list[str] = []
    current = ""
    for block in text.split("\n\n"):
        if not block:
            continue
        piece = block if not current else "\n\n" + block
        if len(piece) <= limit:
            if current and len(current) + len(piece) > limit:
                parts.append(current)
                current = block
            else:
                current += piece
            continue
        if current:
            parts.append(current)
            current = ""
        parts.extend(_chunk_lines(block, limit))
    if current:
        parts.append(current)
    return parts or _chunk_lines(text, limit)
