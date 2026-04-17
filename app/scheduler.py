from __future__ import annotations

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config import get_settings

log = logging.getLogger("perfin.scheduler")


def _agentmail_job() -> None:
    from app.importers.agentmail import poll_and_ingest

    report = poll_and_ingest()
    log.info("AgentMail poll: %s", report.as_dict())


def _net_worth_job() -> None:
    from app.services.net_worth import snapshot_today

    snapshot_today()


def _prices_job() -> None:
    from app.importers.prices import refresh_prices

    refresh_prices()


def start_scheduler() -> BackgroundScheduler | None:
    settings = get_settings()
    scheduler = BackgroundScheduler(timezone="Asia/Singapore")
    if settings.agentmail_enabled:
        scheduler.add_job(
            _agentmail_job,
            CronTrigger.from_crontab(settings.AGENTMAIL_POLL_CRON),
            id="agentmail_poll",
            max_instances=1,
            coalesce=True,
        )
    scheduler.add_job(_net_worth_job, CronTrigger.from_crontab("30 23 * * *"), id="net_worth")
    scheduler.add_job(_prices_job, CronTrigger.from_crontab("15 23 * * *"), id="prices")
    scheduler.start()
    return scheduler


def stop_scheduler(scheduler: BackgroundScheduler | None) -> None:
    if scheduler is not None:
        scheduler.shutdown(wait=False)
