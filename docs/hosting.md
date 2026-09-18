# Publish the portfolio demo on Render + Neon

This is a deployment recipe, not a claim that the site is already hosted. Use a dedicated Neon database for this public demo. No Snowflake account is needed.

1. Create a free Neon project. Copy its PostgreSQL connection string directly into Render's secret environment settings; never commit it or paste it into an issue.
2. In Render, create a Blueprint from `Jerry-Padilla/global-mobility-risk-intelligence`. Grant the GitHub integration access to this private repository. The included `render.yaml` selects a free Docker web service.
3. Supply `DATABASE_URL` using Neon's connection string with `sslmode=require`. Render generates `SECRET_KEY`. Keep `DJANGO_DEBUG=false`.
4. Deploy. Startup applies migrations, seeds synthetic data only when no demo factories exist, and rebuilds demo analytical files from PostgreSQL before serving traffic. Render provides the public HTTPS URL.
5. Open the homepage, select **Explore the earthquake scenario**, and follow the event, dependency, inventory and options. Check `/health/`, `/analytics/` and the mobile layout.
6. Restart the service and repeat the checks. A successful local recovery test does not replace this hosted acceptance check. Monitor memory and startup duration on the free instance before calling the deployment reliable.

## Storage and limits

This recipe supports one service instance and a demonstration dataset. PostgreSQL persists in Neon; local DuckDB/Parquet files are disposable and rebuilt on every startup. Database publication history is retained, but old local versions may no longer exist after a restart. This is not durable archival storage for live ingestion. Keep live ingestion off this hosted demo until object storage, retention and a scheduled writer are configured. The full local Docker deployment retains durable files through its volume.

Render free services sleep when idle, so the first visit can be slow. The free plan also has usage/resource limits. Do not create Render's expiring free PostgreSQL database for this recipe. Free-tier capacity, pricing and verification requirements are controlled by each provider.

The application trusts the forwarded HTTPS header only when configured with Render's external hostname. Do not set that variable on an untrusted proxy deployment. Staff accounts are not created automatically.

## Two-minute visitor walkthrough

- Start on Operations overview and select the earthquake scenario.
- Read the event time and affected supplier; note that all company records in this mode are synthetic.
- Compare 3.8 days of semiconductor coverage with the current supplier's 45-day lead time.
- Review the candidate's pending qualification. It cannot be treated as an approved production alternative.
- Open the factory and supplier profiles for supporting detail; inspect the factor contributions behind the score.

For a walkthrough recording, capture this sequence at desktop width, then show the same investigation on mobile. Do not display service dashboards or credentials in the recording.
