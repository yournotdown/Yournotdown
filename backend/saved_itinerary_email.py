"""Premium transactional email rendering for saved Tonight's Move itineraries."""
import html
import os
from datetime import datetime
from urllib.parse import quote_plus


VIBE_META = {
    "just-vibing": "😇 Take It Easy",
    "down": "😏 Let's See Where This Goes",
    "very-down": "🔥 Let's Make It Count",
    "send-it": "🚀 No Regrets",
}

STEP_LABELS = {
    "dinner": "DINNER",
    "drinks": "DRINKS",
    "entertainment": "LIVE MUSIC",
    "late-night": "LATE NIGHT",
}

EMAIL_SUBJECT = "Your Tonight’s Move is locked in"
EMAIL_PREHEADER = "Nashville is set. Here’s your locked-in move."


def _escape(value) -> str:
    return html.escape(str(value or ""), quote=True)


def _friendly_vibe_label(vibe: str) -> str:
    return VIBE_META.get(vibe or "", "✨ Tonight's Move")


def _friendly_city_label(city_slug: str) -> str:
    return (city_slug or "nashville").replace("-", " ").title()


def _friendly_step_label(slot: str, fallback: str = "") -> str:
    return STEP_LABELS.get(slot or "", (fallback or slot or "STEP").upper())


def _friendly_time(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    for fmt in ("%H:%M:%S", "%H:%M"):
        try:
            parsed = datetime.strptime(raw, fmt)
            return parsed.strftime("%I:%M %p").lstrip("0")
        except ValueError:
            pass
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return raw
    return parsed.strftime("%b %d, %I:%M %p").replace(" 0", " ")


def _directions_url(business: dict) -> str:
    name = (business.get("name") or "").strip()
    address = (business.get("address") or "").strip()
    query = quote_plus(address or name or "")
    return f"https://www.google.com/maps/search/?api=1&query={query}" if query else ""


def _step_links(step: dict) -> list[tuple[str, str]]:
    business = step.get("business") or {}
    event = step.get("event") or {}
    links = []
    if business.get("website"):
        links.append(("View Venue", business["website"]))
    directions_url = _directions_url(business)
    if directions_url:
        links.append(("Get Directions", directions_url))
    if event.get("ticket_url"):
        links.append(("Buy Tickets", event["ticket_url"]))
    return links


def _step_card_html(step: dict) -> str:
    business = step.get("business") or {}
    event = step.get("event") or {}
    number = str(step.get("number") or "").zfill(2) if step.get("number") else ""
    step_label = _friendly_step_label(step.get("slot", ""), step.get("label", ""))
    business_name = _escape(business.get("name", "Unknown spot"))
    address = _escape(business.get("address", ""))
    event_title = _escape(event.get("title", ""))
    event_time = _escape(_friendly_time(event.get("local_time") or event.get("starts_at") or ""))
    detail_lines = []
    if address:
        detail_lines.append(
            f'<div style="margin-top:8px;color:#CFCFCF;font-size:14px;line-height:1.5;">{address}</div>'
        )
    if event_title:
        detail_lines.append(
            f'<div style="margin-top:10px;color:#FFFFFF;font-size:15px;line-height:1.5;"><strong>Tonight:</strong> {event_title}</div>'
        )
    if event_time:
        detail_lines.append(
            f'<div style="margin-top:4px;color:#CFCFCF;font-size:14px;line-height:1.5;">{event_time}</div>'
        )
    buttons = []
    for label, url in _step_links(step):
        buttons.append(
            '<a href="{url}" '
            'style="display:inline-block;margin:8px 10px 0 0;padding:12px 16px;border:1px solid #C6FF00;'
            'color:#0B0B0B;background:#C6FF00;text-decoration:none;font-size:12px;font-weight:700;'
            'letter-spacing:0.14em;text-transform:uppercase;border-radius:999px;">{label}</a>'.format(
                url=_escape(url),
                label=_escape(label),
            )
        )
    button_block = f'<div style="margin-top:14px;">{"".join(buttons)}</div>' if buttons else ""
    return (
        '<div style="margin-top:18px;padding:24px;border:1px solid rgba(255,255,255,0.10);'
        'border-radius:20px;background:#111111;">'
        f'<div style="color:#C6FF00;font-size:12px;letter-spacing:0.22em;text-transform:uppercase;">{_escape(number)} {step_label}</div>'
        f'<div style="margin-top:10px;color:#FFFFFF;font-size:28px;line-height:1.05;font-weight:700;">{business_name}</div>'
        f'{"".join(detail_lines)}'
        f"{button_block}"
        '</div>'
    )


def _text_step_block(step: dict) -> str:
    business = step.get("business") or {}
    event = step.get("event") or {}
    lines = [
        f'{str(step.get("number") or "").zfill(2)} {_friendly_step_label(step.get("slot", ""), step.get("label", ""))}',
        business.get("name", "Unknown spot"),
    ]
    if business.get("address"):
        lines.append(business["address"])
    if event.get("title"):
        lines.append(f'Tonight: {event["title"]}')
    friendly_time = _friendly_time(event.get("local_time") or event.get("starts_at") or "")
    if friendly_time:
        lines.append(f'Time: {friendly_time}')
    for label, url in _step_links(step):
        lines.append(f"{label}: {url}")
    return "\n".join(lines)


def saved_itinerary_email_subject(doc: dict) -> str:
    return EMAIL_SUBJECT


def saved_itinerary_email_preheader(doc: dict) -> str:
    city = _friendly_city_label(doc.get("city_slug", "nashville"))
    return EMAIL_PREHEADER.replace("Nashville", city)


def saved_itinerary_email_content(doc: dict) -> tuple[str, str]:
    city_label = _friendly_city_label(doc.get("city_slug", "nashville"))
    vibe_label = _friendly_vibe_label(doc.get("vibe", ""))
    site_url = (
        os.environ.get("PUBLIC_SITE_URL", "").strip()
        or os.environ.get("FRONTEND_PUBLIC_URL", "").strip()
    )
    build_another_url = f"{site_url.rstrip('/')}/{doc.get('city_slug', 'nashville')}/vibe" if site_url else ""
    preheader = _escape(saved_itinerary_email_preheader(doc))
    html_parts = [
        '<html><body style="margin:0;padding:0;background:#050505;color:#FFFFFF;">',
        f'<div style="display:none;max-height:0;overflow:hidden;opacity:0;">{preheader}</div>',
        '<div style="background:#050505;padding:24px 12px;">',
        '<div style="max-width:600px;margin:0 auto;">',
        '<div style="padding:24px 24px 18px;border:1px solid rgba(255,255,255,0.08);border-radius:28px;'
        'background:linear-gradient(180deg,#0D0D0D 0%,#070707 100%);">',
        '<div style="display:flex;align-items:flex-end;gap:8px;flex-wrap:wrap;">',
        '<span style="color:#C6FF00;font-size:24px;font-weight:800;letter-spacing:0.36em;text-transform:uppercase;line-height:1;">YND</span>',
        '<span style="color:#8F8F8F;font-size:11px;font-weight:700;letter-spacing:0.24em;text-transform:uppercase;line-height:1.2;">/ EST. 26</span>',
        '</div>',
        '<div style="margin-top:14px;width:72px;height:2px;background:#C6FF00;border-radius:999px;"></div>',
        '<div style="margin-top:12px;color:#8F8F8F;font-size:12px;letter-spacing:0.20em;text-transform:uppercase;">Tonight’s Move</div>',
        '<h1 style="margin:28px 0 10px;color:#FFFFFF;font-size:40px;line-height:0.96;font-weight:700;">You’re Locked In</h1>',
        '<p style="margin:0;color:#CFCFCF;font-size:16px;line-height:1.65;">Your Tonight’s Move is saved and ready.</p>',
        '<div style="margin-top:18px;">',
        '<span style="display:inline-block;margin:0 10px 10px 0;padding:10px 14px;border:1px solid rgba(255,255,255,0.12);'
        'border-radius:999px;background:#111111;color:#FFFFFF;font-size:12px;font-weight:700;letter-spacing:0.12em;'
        'text-transform:uppercase;">{city}</span>'.format(city=_escape(city_label)),
        '<span style="display:inline-block;margin:0 10px 10px 0;padding:10px 14px;border:1px solid rgba(198,255,0,0.30);'
        'border-radius:999px;background:rgba(198,255,0,0.12);color:#C6FF00;font-size:12px;font-weight:700;'
        'letter-spacing:0.08em;">{vibe}</span>'.format(vibe=_escape(vibe_label)),
        '</div>',
    ]
    for step in doc.get("steps") or []:
        html_parts.append(_step_card_html(step))
    html_parts.extend([
        '<div style="margin-top:26px;padding-top:22px;border-top:1px solid rgba(255,255,255,0.08);">',
        '<div style="color:#CFCFCF;font-size:14px;line-height:1.6;">Built with YourNotDown</div>',
        '<div style="margin-top:4px;color:#8F8F8F;font-size:14px;line-height:1.6;">Curated for no regrets.</div>',
        '<div style="margin-top:16px;">',
        '<a href="https://www.yournotdown.com" style="color:#C6FF00;text-decoration:none;font-size:13px;'
        'font-weight:700;letter-spacing:0.08em;">yournotdown.com</a>',
        '</div>',
    ])
    if build_another_url:
        html_parts.append(
            '<div style="margin-top:18px;"><a href="{url}" '
            'style="display:inline-block;padding:13px 18px;border:1px solid rgba(255,255,255,0.16);'
            'border-radius:999px;color:#FFFFFF;text-decoration:none;font-size:12px;font-weight:700;'
            'letter-spacing:0.16em;text-transform:uppercase;">Build Another Move</a></div>'.format(
                url=_escape(build_another_url),
            )
        )
    html_parts.extend([
        '</div>',
        '</div>',
        '</div>',
        '</div>',
        '</body></html>',
    ])
    text_parts = [
        "YOURNOTDOWN",
        "Tonight's Move",
        "",
        "You're Locked In",
        "Your Tonight's Move is saved and ready.",
        "",
        f"City: {city_label}",
        f"Vibe: {vibe_label}",
        "",
    ]
    for step in doc.get("steps") or []:
        text_parts.append(_text_step_block(step))
        text_parts.append("")
    text_parts.extend([
        "Built with YourNotDown",
        "Curated for no regrets.",
        "https://www.yournotdown.com",
    ])
    if build_another_url:
        text_parts.extend(["", f"Build Another Move: {build_another_url}"])
    return "\n".join(text_parts), "".join(html_parts)
