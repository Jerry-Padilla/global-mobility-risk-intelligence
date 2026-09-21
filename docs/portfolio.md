# Static portfolio on Vercel

Deploy only the `portfolio` directory. It contains public HTML/CSS/JS, synthetic sample content, application screenshots and a silent walkthrough recording. It needs no database, API keys, environment variables, dependency installation or build step.

## Import from GitHub

1. In Vercel, choose Add New Project and import `Jerry-Padilla/global-mobility-risk-intelligence`.
2. Set **Root Directory** to `portfolio` (essential: do not deploy the repository root).
3. Choose Framework Preset **Other**, no build/install commands, and Output Directory `.`. The included `vercel.json` provides these settings.
4. Deploy and open the resulting HTTPS URL. Check mobile layout, all four investigation steps and the score controls.

The full Django application remains separate. The repository can remain private; visitors do not need repository access to view the deployed website. The GitHub link requires access while the repository is private.

## Freshness and limitations

The sample identifies its source as the Meridian synthetic scenario and displays the reference date of 18 September 2026. It is a fixed snapshot, not a live feed. Automatic public-source refresh has not been implemented. Do not replace the reference date with a deployment date or label simulated data as live.

A future scheduled refresh should publish sanitized public JSON with source identity, last successful retrieval time and record period. Preserve the last good snapshot when refreshes fail and show a stale-data state. No Snowflake account is required for that design.

## Local verification

Run `python scripts/check_portfolio.py` from the configured project virtual environment. It serves only `portfolio` over loopback, verifies desktop/mobile and no-JavaScript behavior, checks score interactions, and refreshes the screenshots and walkthrough. Playwright Chromium is required. No PostgreSQL or Django server is required.

Private SSH keys, Terraform exports, `.env` and local database files are excluded from Git and Docker. They are outside the static publish directory. Vercel project metadata is also ignored. Deploy this folder only, never a ZIP of the whole workspace.
