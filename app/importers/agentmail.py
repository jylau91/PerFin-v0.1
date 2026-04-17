from __future__ import annotations

import logging
from dataclasses import asdict, dataclass

from app.config import get_settings
from app.db.repo import already_ingested, record_ingest, record_poll
from app.services.ingest import ingest_pdf

log = logging.getLogger("perfin.agentmail")


@dataclass
class IngestReport:
    matched: int = 0
    ingested: int = 0
    skipped: int = 0
    errored: int = 0
    errors: list[str] = None

    def __post_init__(self) -> None:
        if self.errors is None:
            self.errors = []

    def as_dict(self) -> dict:
        d = asdict(self)
        return d


def _client():
    from agentmail import AgentMail  # lazy import keeps tests happy without dep.

    return AgentMail(api_key=get_settings().AGENTMAIL_API_KEY)


def _password_for(sender: str | None) -> str | None:
    if not sender:
        return None
    mapping = get_settings().agentmail_sender_passwords
    # Try exact match, then domain fallback.
    if sender in mapping:
        return mapping[sender]
    if "@" in sender:
        domain = sender.split("@", 1)[1]
        return mapping.get(domain)
    return None


def poll_and_ingest(*, limit: int = 50, client=None) -> IngestReport:
    settings = get_settings()
    report = IngestReport()
    if not settings.agentmail_enabled:
        report.errors.append("AgentMail not configured")
        record_poll("agentmail", 0, 0, 0, 0, note="disabled")
        return report

    client = client or _client()
    needle = (settings.AGENTMAIL_SUBJECT_FILTER or "").lower()

    try:
        listing = client.inboxes.messages.list(settings.AGENTMAIL_INBOX_ID, limit=limit)
    except Exception as exc:
        log.exception("AgentMail list failed")
        report.errors.append(str(exc))
        report.errored += 1
        record_poll("agentmail", 0, 0, 0, 1, note=f"list_failed: {exc}")
        return report

    messages = getattr(listing, "messages", None) or []

    for msg in messages:
        subject = getattr(msg, "subject", "") or ""
        if needle and needle not in subject.lower():
            continue
        report.matched += 1
        message_id = getattr(msg, "message_id", None) or getattr(msg, "id", None)
        sender = getattr(msg, "from_", None) or getattr(msg, "from_address", None) or getattr(msg, "sender", None)
        attachments = getattr(msg, "attachments", None) or []
        if not attachments:
            report.skipped += 1
            continue

        for att in attachments:
            filename = getattr(att, "filename", None) or getattr(att, "name", "") or ""
            if not filename.lower().endswith(".pdf"):
                report.skipped += 1
                continue
            attachment_id = getattr(att, "attachment_id", None) or getattr(att, "id", None)
            if already_ingested("agentmail", str(message_id), filename):
                report.skipped += 1
                continue
            try:
                pdf_bytes = client.inboxes.messages.get_attachment(
                    inbox_id=settings.AGENTMAIL_INBOX_ID,
                    message_id=message_id,
                    attachment_id=attachment_id,
                )
                if hasattr(pdf_bytes, "read"):
                    pdf_bytes = pdf_bytes.read()
                if isinstance(pdf_bytes, str):
                    pdf_bytes = pdf_bytes.encode("latin-1")
            except Exception as exc:
                log.exception("get_attachment failed")
                record_ingest("agentmail", str(message_id), subject, sender, filename, None, str(exc))
                report.errored += 1
                report.errors.append(f"{filename}: {exc}")
                continue

            outcome = ingest_pdf(
                pdf_bytes=pdf_bytes,
                filename=filename,
                password=_password_for(sender),
                source="agentmail",
                external_id=str(message_id),
                raw_subject=subject,
                raw_sender=sender,
            )
            if outcome.ok:
                report.ingested += 1
            else:
                report.errored += 1
                report.errors.append(f"{filename}: {outcome.error}")

    record_poll(
        "agentmail",
        report.matched,
        report.ingested,
        report.skipped,
        report.errored,
        note="; ".join(report.errors[:3]),
    )
    return report
