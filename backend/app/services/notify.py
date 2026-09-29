"""WhatsApp-style farmer notifications.

Messages are formatted here and *logged*, not sent. The wording mirrors the
farmer screen (frontend/src/lib/farmerCopy.ts); keep the two in sync until
the copy moves to a single shared source.
"""

import logging
from datetime import date, datetime, timezone

from app.core.config import Settings
from app.models import Panchayat
from app.schemas.decision import Action, DecisionResponse, DecisionStatus
from app.schemas.forecast import ForecastResponse
from app.schemas.notify import Delivery, NotifyMessage, NotifyResult, TranslationPlaceholder

logger = logging.getLogger("app.notify")

LANGUAGE_NAMES = {"mr": "Marathi", "hi": "Hindi", "en": "English"}

# (emoji, headline, one-line body). {crop} is filled in.
ACTION_MESSAGE: dict[Action, tuple[str, str, str]] = {
    Action.SOW: ("✅", "Good time to sow your {crop}", "The rains look steady enough. You can go ahead and sow this week."),
    Action.WAIT: ("⏳", "Wait before sowing", "Hold off sowing for 1–2 weeks, until the rains are steady and the soil is moist."),
    Action.SPRAY: (
        "⚠️",
        "Sow, but protect your {crop}",
        "Wet weather is likely in the coming weeks. Plan a protective spray, only on a dry day with no rain expected for a few hours.",
    ),
    Action.REASSESS: (
        "🔄",
        "Wait a few days, then check again",
        "The weather is unclear. Don't spend money on sowing yet.",
    ),
}

BLOCKED_PENDING_REVIEW = "Flagged for officer review. Approve or override it in the review queue before sending."


def rain_words(mm: float) -> str:
    if mm < 5:
        return "very little rain"
    if mm < 25:
        return "light rain"
    if mm < 75:
        return "moderate rain"
    if mm < 150:
        return "heavy rain"
    return "very heavy rain"


def chance_in_ten(p: float) -> str:
    if p < 0.05:
        return "very low"
    if p > 0.95:
        return "almost certain"
    return f"{min(9, max(1, round(p * 10)))} in 10"


def build_message(
    panchayat: Panchayat,
    decision: DecisionResponse | None,
    forecast: ForecastResponse,
    settings: Settings,
) -> NotifyMessage:
    """Format today's advice. `decision` is None when the crop has no advice model."""
    crop = panchayat.primary_crop.replace("_", " ")
    farmer_url = f"{settings.public_app_url.rstrip('/')}/farmer/{panchayat.id}"
    w1 = forecast.weeks[0]

    lines = [
        f"🌧️ *Monsoon advice – {panchayat.name}*",
        f"{crop.capitalize()} · {_short_date(forecast.issued_on)}",
        "",
    ]

    if decision is None:
        lines.append(f"Advice for {crop} is coming soon.")
    else:
        emoji, headline, body = ACTION_MESSAGE[decision.escalation.final_action]
        lines += [f"{emoji} *{headline.format(crop=crop)}*", body.format(crop=crop)]

    lines += [
        "",
        f"This week: {rain_words(w1.rainfall_mm.p50)} (about {round(w1.rainfall_mm.p50)} mm). "
        f"Chance of 5+ dry days in a row: {chance_in_ten(w1.dry_spell_probability)}.",
    ]

    status = decision.escalation.status if decision else None
    if status == DecisionStatus.OVERRIDDEN:
        lines.append("✔ Updated by your agriculture officer.")
    elif status == DecisionStatus.APPROVED:
        lines.append("✔ Checked by your agriculture officer.")

    lines += ["", f"Details: {farmer_url}", "_Demo – sample weather data._"]
    text = "\n".join(lines)

    blocked = status == DecisionStatus.NEEDS_OFFICER_REVIEW
    lang = settings.notify_regional_language
    return NotifyMessage(
        panchayat_id=panchayat.id,
        crop=panchayat.primary_crop,
        text=text,
        char_count=len(text),
        decision_status=status,
        final_action=decision.escalation.final_action if decision else None,
        farmer_url=farmer_url,
        # TODO: translate `text` into the regional language (e.g. a reviewed
        # template per action, or a translation API) and fill in `text` here.
        translations=[TranslationPlaceholder(language=lang, language_name=LANGUAGE_NAMES.get(lang, lang))],
        can_send=not blocked,
        blocked_reason=BLOCKED_PENDING_REVIEW if blocked else None,
    )


def send(message: NotifyMessage, settings: Settings) -> NotifyResult:
    """'Send' a message. For now this only logs it."""
    # TODO: wire up Twilio's WhatsApp API. Roughly:
    #   from twilio.rest import Client
    #   client = Client(settings.twilio_account_sid, settings.twilio_auth_token)
    #   for number in subscribers_for(message.panchayat_id):  # farmer opt-in list, not built yet
    #       client.messages.create(
    #           from_=settings.twilio_whatsapp_from,  # e.g. "whatsapp:+14155238886"
    #           to=f"whatsapp:{number}",
    #           body=message.text,
    #       )
    # Credentials come from env vars TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN and
    # TWILIO_WHATSAPP_FROM (see app/core/config.py). Business-initiated WhatsApp
    # messages outside a 24h session need a pre-approved template, so this text
    # will likely need to become a template with variables.
    logger.info(
        "WhatsApp message (not sent, log only) panchayat=%s crop=%s chars=%d\n%s",
        message.panchayat_id,
        message.crop,
        message.char_count,
        message.text,
    )
    return NotifyResult(message=message, delivery=Delivery(logged_at=datetime.now(timezone.utc)))


def _short_date(d: date) -> str:
    return f"{d.day} {d.strftime('%b')}"
