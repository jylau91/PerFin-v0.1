from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock


def _msg(message_id, subject, attachments=(), sender="bank@example.com"):
    return SimpleNamespace(
        message_id=message_id,
        subject=subject,
        from_=sender,
        attachments=list(attachments),
    )


def _att(attachment_id, filename):
    return SimpleNamespace(attachment_id=attachment_id, filename=filename)


def _fake_client(messages, attachment_bytes=b"%PDF-1.4 fake"):
    client = MagicMock()
    listing = SimpleNamespace(messages=messages)
    client.inboxes.messages.list.return_value = listing
    client.inboxes.messages.get_attachment.return_value = attachment_bytes
    return client


def test_disabled_when_not_configured(migrated_db, monkeypatch):
    from app.importers.agentmail import poll_and_ingest

    report = poll_and_ingest(client=None)
    assert report.matched == 0
    assert report.ingested == 0
    assert "not configured" in " ".join(report.errors).lower()


def test_subject_filter(migrated_db, monkeypatch):
    monkeypatch.setenv("AGENTMAIL_API_KEY", "test")
    monkeypatch.setenv("AGENTMAIL_INBOX_ID", "inbox_test")
    from app.config import get_settings
    get_settings.cache_clear()

    from app.importers.agentmail import poll_and_ingest

    messages = [
        _msg("m1", "Re: JY Statement Jan DBS", [_att("a1", "dbs-jan.pdf")]),
        _msg("m2", "Unrelated marketing", [_att("a2", "x.pdf")]),
    ]
    client = _fake_client(messages)

    # Force parser detection to fail so we don't need a real PDF.
    from app.parsers import registry as parser_registry
    from app.parsers.base import ParseError

    monkeypatch.setattr(parser_registry, "detect_bank",
                        lambda *a, **kw: (_ for _ in ()).throw(ParseError("no match")))

    report = poll_and_ingest(client=client)
    assert report.matched == 1
    assert report.errored == 1
    assert report.skipped == 0


def test_skips_non_pdf(migrated_db, monkeypatch):
    monkeypatch.setenv("AGENTMAIL_API_KEY", "test")
    monkeypatch.setenv("AGENTMAIL_INBOX_ID", "inbox_test")
    from app.config import get_settings
    get_settings.cache_clear()

    from app.importers.agentmail import poll_and_ingest

    messages = [_msg("m1", "JY Statement Feb", [_att("a1", "img.png")])]
    report = poll_and_ingest(client=_fake_client(messages))
    assert report.matched == 1
    assert report.skipped == 1
    assert report.ingested == 0


def test_dedup_via_ingest_sources(migrated_db, monkeypatch):
    monkeypatch.setenv("AGENTMAIL_API_KEY", "test")
    monkeypatch.setenv("AGENTMAIL_INBOX_ID", "inbox_test")
    from app.config import get_settings
    get_settings.cache_clear()

    from app.db.repo import record_ingest
    from app.importers.agentmail import poll_and_ingest

    record_ingest("agentmail", "m1", "JY Statement Feb", "bank@example.com", "x.pdf", None, None)

    messages = [_msg("m1", "JY Statement Feb", [_att("a1", "x.pdf")])]
    report = poll_and_ingest(client=_fake_client(messages))
    assert report.matched == 1
    assert report.skipped == 1
    assert report.ingested == 0


def test_list_failure_recorded(migrated_db, monkeypatch):
    monkeypatch.setenv("AGENTMAIL_API_KEY", "test")
    monkeypatch.setenv("AGENTMAIL_INBOX_ID", "inbox_test")
    from app.config import get_settings
    get_settings.cache_clear()

    client = MagicMock()
    client.inboxes.messages.list.side_effect = RuntimeError("500")

    from app.importers.agentmail import poll_and_ingest

    report = poll_and_ingest(client=client)
    assert report.errored == 1
    row = migrated_db.execute(
        "SELECT * FROM poll_log WHERE source='agentmail' ORDER BY ran_at DESC LIMIT 1"
    ).fetchone()
    assert row is not None
    assert "list_failed" in (row["note"] or "")
