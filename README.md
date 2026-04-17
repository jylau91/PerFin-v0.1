# PerFin

Personal asset manager for a local Mac mini, reachable over Tailscale.

- Parses monthly bank / credit-card PDFs (Trust, DBS, POSB, OCBC, UOB) via a custom `TrustBankParser` + `monopoly-core` adapters.
- Ingests statements either from manual upload **or** a daily pull from an AgentMail inbox (subject contains `JY Statement`).
- Consolidates cash balances, CSV-imported investment holdings, and net worth.
- Reconciles parsed transactions against statement closing balances.
- Uses Claude (via `anthropic` SDK) to surface spending insights, flag suspicious expenses, and generate a monthly save plan.

## Setup

```bash
uv sync
cp .env.example .env
# edit .env: PERFIN_PASSPHRASE, ANTHROPIC_API_KEY, AGENTMAIL_API_KEY, AGENTMAIL_INBOX_ID
uv run python -m migrations.runner
bash deploy/run.sh
```

From another Tailscale device: `http://<mac-mini-tailnet>:8787`.

## AgentMail ingestion

Forward monthly statement emails to the AgentMail inbox with subject containing **`JY Statement`**. A scheduled job (`AGENTMAIL_POLL_CRON`, default `0 7 * * *` SGT) pulls new PDF attachments and runs them through the parser pipeline. Click **Pull from AgentMail now** on the dashboard for an on-demand sync.

Per-sender PDF passwords: set `AGENTMAIL_SENDER_PASSWORDS_JSON='{"statements@uob.com.sg":"pw","uob.com.sg":"pw"}'`.

## launchd (macOS)

Edit `deploy/com.perfin.app.plist` (replace `YOUR_USER`), then:

```bash
cp deploy/com.perfin.app.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.perfin.app.plist
```

## Tests

```bash
uv run pytest
```

## License notes

We depend on `monopoly-core` (AGPL-3.0). Acceptable for single-user / local use. If you ever publish a hosted instance, AGPL obliges source disclosure. We keep `monopoly-core` as an unmodified dependency.
