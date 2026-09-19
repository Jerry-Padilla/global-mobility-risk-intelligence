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

## Choosing a long-term low-cost host (reviewed 2026-09-19)

Keep Django templates + HTMX. They have no license fee, already render the whole frontend, and avoid an extra frontend deployment. React, Vue, Svelte or Astro are alternatives, but changing the UI framework does not remove PostgreSQL, scheduled ingestion or analytical storage. Vercel supports Django; the main adaptation is backend execution and persistent data, not HTML rendering.

- **Existing Raspberry Pi or spare PC:** can run the whole Docker stack, including PostgreSQL and persistent analytics volumes. Recommended starting target: a Pi 4/5 with 4 GB or more, 64-bit Linux, SSD storage and reliable power. This is an engineering recommendation, not a measured hardware minimum; ARM builds and memory usage remain unverified. Hardware, electricity, internet and backups are still your costs. A spare computer you already own may be better value than buying a Pi.
- **Public access from home:** Cloudflare Tunnel makes outbound connections, avoiding router port forwarding. A stable published application needs a domain on Cloudflare; registration may cost money. Quick Tunnels provide temporary random URLs for demonstrations. Configure production Django settings, an explicit hostname and trusted HTTPS proxy before exposing the app; do not publish the development server or PostgreSQL port.
- **Oracle Always Free:** a VM is a good architectural fit because the application, database and files can stay together. Confirm the current Always Free allocation in your account (the current documentation describes 2 OCPUs / 12 GB total for A1 Free Tier). Capacity can be unavailable and idle instances may be reclaimed. Use backups and avoid provisioning trial-only resources by mistake. Signup may require card verification.
- **AWS:** useful for learning AWS, but not the best answer to indefinite free VM hosting. New customers' Free Plan expires after six months or when credits are exhausted, whichever comes first. Some services have recurring free allowances, but that does not make this whole Django/PostgreSQL deployment permanently free.
- **Vercel static portfolio edition:** an optional separate, read-only snapshot could publish precomputed JSON and pages and run filters/charts in the browser. This can remove the online database/server requirement, but refreshes require generating and redeploying a snapshot. Live ingestion, Django admin, server-side APIs and warehouse queries would remain in the full application. Do not rewrite the working app simply to host a snapshot.

Recommendation: use existing hardware if available and home uptime is acceptable; otherwise try an Oracle Always Free VM for the complete platform. Keep Render + Neon as the simpler managed demo alternative. No deployment or free-tier availability is guaranteed by these recipes.

Sources:
- https://aws.amazon.com/free/terms/
- https://docs.oracle.com/iaas/Content/FreeTier/freetier.htm
- https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm
- https://vercel.com/docs/functions/runtimes/python
- https://developers.cloudflare.com/tunnel/get-started/
- https://www.raspberrypi.com/products/raspberry-pi-5/
