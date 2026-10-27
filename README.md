# Aanchal Singh — Biotechnology Research & AI/ML Portfolio

A complete server-rendered Flask research portfolio, not a static mockup. Includes a PostgreSQL-compatible data model, migrations, authenticated content management, durable database-backed uploads, and privacy-aware contact handling.

**Status:** implemented and tested locally. Not deployed to Render. No real administrator, email address, CV, photograph, project, publication, academic score, or research result is bundled. Initial biography copy must be reviewed by Aanchal before launch.

## 1. What is included

- Light ivory/white, navy, and teal research-focused interface; responsive navigation, keyboard focus, reduced-motion support, and conceptual interactive AI/ML workflow.
- Editable profile; confirmed research interests and AI/ML topics; laboratory/computational skills; education; experience; projects; publications; achievements; research notes; professional links.
- Structured project detail pages: scientific background, question, methods, data provenance, ML methodology, validation, results, limitations, reproducibility, and references. Blank sections do not appear.
- Publication status separate from public visibility; private project/publication/blog drafts and authenticated previews; featured projects; title search, category/status filters, and pagination.
- Secure administrator login, scrypt password hashing, CSRF on every POST, role checking, two-hour session expiry, database-backed shared rate limits, upload allowlists and quotas, strict security headers, and safe text rendering.
- Contact validation, consent, honeypot, five submissions per IP per hour, private inbox, optional Resend HTTPS email notifications, accurate saved-versus-accepted messaging.
- PostgreSQL-backed binary image and PDF storage; no production filesystem dependency. Images are decoded using only permitted formats, resized to 1800 px, and re-encoded to WebP without source metadata. PDFs are download-only.
- Configurable section visibility, SEO metadata, local social image, canonical URLs, sitemap, robots rules, health endpoint, custom error pages, migrations, deployment config, tests, optional Dockerfile, and GitHub CI.

### Content integrity

The only seeded academic record is M.Tech Biotechnology at NIT Jalandhar. No dates or scores are inferred. The two seeded interest cards express only the supplied broad interests in biotechnology and AI/ML. More specialized topics and all skills, research outputs, experiences, and achievements are absent until added. The scientific graphic is decorative and the workflow is conceptual, not scientific evidence or a record of completed work.

## 2. Local quick start

Use Python 3.12. From the project root on macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
```

Edit `.env` and replace `SECRET_KEY` with a random value. Generate one with:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

The production dependency file applies the fully resolved versions in `requirements.lock` for reproducible installs.

The app reads environment variables; it deliberately does not auto-load `.env`. Export the file in your shell before every new terminal session:

```bash
set -a
. ./.env
set +a
flask --app wsgi db upgrade
flask --app wsgi seed
flask --app wsgi create-admin
flask --app wsgi run --host 127.0.0.1 --port 8000
```

Visit `http://127.0.0.1:8000` and `/admin/login`. The administrator command prompts privately for an email and a password of 14–256 characters. There is no default production account and no public registration.

For Windows PowerShell, use `py -m venv .venv`, `.\.venv\Scripts\Activate.ps1`, then set environment variables with `$env:NAME='value'` rather than sourcing the POSIX file. Run the same Flask commands afterward.

SQLite is an optional **development-only** fallback. It stores the local database in Flask's `instance/` directory. `APP_ENV=production` refuses SQLite and weak secrets.

### Local PostgreSQL

Create a database using your normal PostgreSQL administrator tools and set:

```bash
export DATABASE_URL='postgresql://USER:PASSWORD@localhost:5432/aanchal_portfolio'
flask --app wsgi db upgrade
flask --app wsgi seed
flask --app wsgi create-admin
```

Use a different database for tests. Do not run `db.create_all()` against production; schema management uses Alembic migrations.

## 3. Administrator onboarding

1. Sign in at `/admin/login`; review the seeded introduction and biography.
2. Upload a real photo and CV under **Files & CV**. Select the appropriate asset type and explicitly mark files public only when they can be shared.
3. Select the photo and CV in **Profile & biography**. Private assets remain hidden from public pages. CV buttons do not appear without a selected public CV.
4. Add undergraduate degree/institution and actual academic dates; do not guess them.
5. Add the current research topic, specialization, supervisor, and laboratory only when authorized.
6. Confirm and edit the two broad research interests. Add specialized topics only if relevant. Use `AI/ML topic` for cards in the computational section.
7. Add verified laboratory and technical skills. Proficiency is optional free-text, never a percentage. Skills can link to a project.
8. Add projects, publications, experience, achievements, and research notes as private drafts first. Save, use **Preview**, then publish after checking content.
9. Use **Sort order** to reorder cards/entries; lower values appear first. Use **Is featured** to place published projects on the homepage.
10. Add actual professional links and contact email. Only complete HTTP(S) profile links are accepted.
11. Choose section visibility. Disabled sections also return 404 at their public URLs. Empty optional experience, skills, output, notes, and award sections remain hidden.
12. Add publications only when they exist. `Under Review` or `In Preparation` never implies acceptance. The visibility checkbox is independent of the bibliographic status.

Research-note bodies and project references support CommonMark Markdown, including headings, lists, fenced code blocks, and citation links. Raw HTML and embedded external Markdown images are disabled. Other fields preserve paragraphs as escaped plain text. Upload a properly licensed research figure using the relevant image field. External paper, poster, PDF, repository, and dataset links must be complete HTTP(S) URLs. A DOI is displayed verbatim, so supply its correct identifier; use the publisher URL for navigation.

Asset deletion clears its database references. Publication/project deletion preserves unrelated records and clears foreign-key links. Deletion actions require a confirmation prompt in JavaScript-enabled browsers. With JavaScript disabled, use the delete action carefully: it remains an authenticated, CSRF-protected POST.

## 4. Environment variables

| Variable | Required | Meaning |
|---|---|---|
| `APP_ENV` | Production | `production` enables production guards, secure cookies, HTTPS redirection, and trusted proxy handling. Use `development` locally. |
| `SECRET_KEY` | Production | Random secret at least 32 characters; keep stable across deploys. Never commit it. |
| `DATABASE_URL` | Production | PostgreSQL connection URL. `postgres://` and `postgresql://` are normalized to `postgresql+psycopg://`. Add `?sslmode=require` for external providers when required. |
| `BASE_URL` | Production | Actual HTTPS origin, e.g. `https://YOUR-SERVICE.onrender.com`, no path or trailing slash. Used for canonical URLs, trusted host validation, redirects, sitemap, and social metadata. |
| `SITE_INDEXABLE` | Optional | Defaults `false`; set `true` only after personal review and launch. Admin and preview pages remain noindex. |
| `MAIL_API_KEY` | Optional | Resend API key. Never sent to browsers. |
| `MAIL_FROM` | Optional | Verified sender, e.g. `Portfolio <contact@YOUR-VERIFIED-DOMAIN>`. Required for email notifications. |
| `MAIL_TO` | Optional | Real destination email for notification delivery. |
| `PORT` | Hosting | Render sets this automatically. Local Gunicorn fallback is 8000. |
| `WEB_CONCURRENCY` | Optional | Default 1 worker with two threads; sensible for a low-memory hobby service. |
| `TEST_POSTGRES_URL` | Tests only | Local database named exactly `portfolio_test`; refused for remote hosts or another database name. |

Do not place secrets in repository files or frontend JavaScript. Flask reads configuration at process startup; restart after changing environment variables.

## 5. GitHub and Render deployment

### Push source to GitHub

Create an empty GitHub repository, then run these commands in the project root after reviewing `.gitignore`:

```bash
git init
git add .
git commit -m "Build academic biotechnology research portfolio"
git branch -M main
git remote add origin https://github.com/YOUR-ACCOUNT/YOUR-REPOSITORY.git
git push -u origin main
```

The CI workflow tests SQLite and a dedicated PostgreSQL 16 service and runs a dependency audit. Its hardcoded password belongs **only to an isolated throwaway CI database**, never to the application administrator or a deployed database.

### Configure persistent PostgreSQL first

Use a provider/account that meets your storage, uptime, TLS, and backup requirements. The blueprint intentionally does not silently provision a paid database. You may use a Render database or an external PostgreSQL service whose current plan you have reviewed. Examples of external services to evaluate include Neon and Supabase; no permanent free availability or capacity is promised for any provider.

Use the connection string provided by your service. If using Render Postgres, prefer its internal URL for the web service in the same region, and its external URL for initial administrator creation from your laptop. For an external database, follow that provider's TLS and pooling requirements. Persistent content includes uploaded files, so database backups must include binary asset columns.

### Deploy with the included blueprint

1. In Render, select **New > Blueprint**, connect the repository, and review `render.yaml`.
2. Set `DATABASE_URL` to your actual persistent PostgreSQL URL.
3. Set `BASE_URL` to the real HTTPS service URL. Choose your Render service name first so the origin is known. If you later attach a custom domain, update `BASE_URL`, keep the onrender origin from being indexed, and verify host/health checks before switching traffic.
4. Let Render generate `SECRET_KEY`. Keep `SITE_INDEXABLE=false` while reviewing.
5. Review plan availability in your own account. The configuration requests a free web service but does not create a database or require upgrading one.
6. Deploy. The start script runs `flask db upgrade`, initializes verified defaults without replacing existing profile content, and starts Gunicorn. This is a non-destructive initial migration, not a per-request database reset.
7. Confirm `https://YOUR-SERVICE.onrender.com/health` returns HTTP 200 and `{"status":"healthy"}`. Initialization or database failures return 503. Do not treat an HTTP loading page during a cold start as a successful health check.

**Manual Render settings if not using the blueprint:**

```text
Runtime: Python 3
Build Command: pip install -r requirements.txt
Start Command: bash scripts/start.sh
Health Check Path: /health
Python version: 3.12.12
```

The underlying production server command is:

```bash
gunicorn wsgi:app --bind "0.0.0.0:${PORT:-8000}" --workers 1 --threads 2 --timeout 60
```

The wrapper start script handles migration and initialization. Future schema migrations must be reviewed and backed up before deployment. For a larger multi-service deployment, migrate once in a release step instead of concurrently in multiple web replicas.

### Create the first production administrator without a Render shell

Render free services do not provide dashboard shell access. Create the user from your own trusted computer using the same source revision and the production database's **external** connection URL. In a separate terminal with the virtual environment active:

```bash
export APP_ENV=production
export DATABASE_URL='YOUR-EXTERNAL-POSTGRESQL-URL'
export SECRET_KEY='THE-SAME-STRONG-SECRET-CONFIGURED-IN-RENDER'
export BASE_URL='https://YOUR-ACTUAL-SERVICE.onrender.com'
flask --app wsgi db upgrade
flask --app wsgi seed
flask --app wsgi create-admin
```

Enter the actual administrator email and a unique strong password at the prompts. Do not put a real password in a command, log, environment example, or README. Remove temporary exported secrets and shell-history entries where appropriate. For local development again, open a new terminal and source your development `.env`. Never run destructive database commands against the production URL.

### Optional email notification delivery

Create a Resend account, verify your sender/domain according to its current policy, and set `MAIL_API_KEY`, `MAIL_FROM`, and `MAIL_TO` in Render. Delivery uses the provider's HTTPS API, not blocked SMTP ports. With no provider or if delivery fails, the message is retained in the private inbox. A provider acceptance response is not proof of delivery to the recipient's inbox. Review provider quotas, agreements, and current pricing independently.

### Launch verification

Review on desktop and mobile, upload actual content, test contact submission, verify receipt in the admin inbox, verify CV access and private drafts, confirm canonical URLs, and set `SITE_INDEXABLE=true` only after review. Use the real deployed origin in all sitemap entries. Visit `/robots.txt` and `/sitemap.xml`. Nothing in this package proves that a deployment has happened.

## 6. Current Render free-plan limitations

Verified from Render's official documentation during implementation (26 October 2026):

- Free web services spin down after **15 minutes** without inbound traffic and can take about **one minute** to start again.
- The local filesystem is ephemeral; free web services cannot attach persistent disks. This app persists portfolio records and assets in PostgreSQL instead.
- A workspace gets **750 free web-service instance hours per calendar month**; services can be suspended when included limits are exhausted.
- Free Render Postgres is limited to **1 GB**, expires **30 days after creation**, and does not include backups. After expiry, it becomes inaccessible; Render documents a 14-day grace period before deletion unless upgraded.
- Free services do not include dashboard shell access, one-off jobs, or SMTP on ports 25, 465, or 587. Use local CLI initialization and optional HTTPS email delivery.
- Render explicitly recommends not using free instances for production applications. A public academic hobby portfolio can technically run there, but permanent availability, backup, and production reliability require separate choices.

Do not treat Render's free database as permanent storage. Budget and configure a durable database and backups before relying on the portfolio for applications. Recheck the documentation and account-specific plan limits before deploying:

- https://render.com/docs/free
- https://render.com/docs/deploy-flask
- https://render.com/docs/postgresql-creating-connecting

## 7. Tests and validation

```bash
pip install -r requirements-dev.txt
pytest -q
```

SQLite tests use a unique temporary database per test. With `TEST_POSTGRES_URL` unset, PostgreSQL tests are not included. To run both engines, create a **local throwaway** database named `portfolio_test`, then run:

```bash
export TEST_POSTGRES_URL='postgresql+psycopg://YOUR-TEST-USER:YOUR-TEST-PASSWORD@127.0.0.1:5432/portfolio_test'
pytest -q
```

The fixture refuses remote hosts or any other database name, sets `TESTING=true`, and clears **only that dedicated test database**. Never reuse a production database for tests. The environment-guard tests construct applications without opening production connections.

See `VALIDATION.md` for the actual final results, browser checks, and limitations of those checks. The production dependencies were separately checked with `pip-audit`; no audit is a guarantee against unknown vulnerabilities. Re-run audits regularly and retest before upgrades.

## 8. Operations, privacy, and security

- Back up PostgreSQL with your provider's supported backup system. For a conventional database, `pg_dump --format=custom --file=portfolio-backup.dump "$DATABASE_URL"` can be used after changing the scheme to the provider's ordinary `postgresql://` URL if needed. Backups contain contact data and uploaded documents: encrypt them, restrict access, and test restoration to a separate database.
- The contact privacy notice states an intended 90-day retention period. Run `flask --app wsgi prune-private-data` regularly from a secure scheduled job or your trusted machine with production environment variables. **No retention job is automatically scheduled by this package.** The command also prunes expired rate-limit buckets. Do not publish until you can maintain the stated retention policy. Account for copies in backups separately.
- Reset an administrator password with `flask --app wsgi reset-admin-password`. To invalidate **all existing sessions**, rotate `SECRET_KEY` in Render and restart the service. Password resets alone do not revoke existing signed session cookies.
- Login rate limits: five POST attempts per hashed network identifier per 15-minute fixed window. Contact: five per hour. Counters live in the database and work across workers/restarts. Shared networks can cause shared limits. A fixed-window boundary can allow a burst spanning adjacent windows; this is sensible hobby-site throttling, not a comprehensive bot defense.
- `ProxyFix` trusts exactly one proxy hop, appropriate for the documented Render setup. Revisit this for any other proxy/CDN chain; do not run it directly exposed to arbitrary client-supplied forwarding headers.
- Production cookies are Secure, HttpOnly, and SameSite=Lax. Administrator and preview responses are no-store and noindex. Production forces HTTPS and checks the host against `BASE_URL` and Render's automatically provided `RENDER_EXTERNAL_HOSTNAME` when present, so the native health-check host remains valid with a custom domain.
- A strong CSP prohibits third-party scripts, fonts, frames, inline scripts, inline styles, and embedded documents. No analytics trackers or remote font/image dependencies are included.
- Uploads are administrator-only, with an 8 MB per-file limit, 9 MB request limit, 20-megapixel image limit, and 64 MB total-asset quota. These deliberately conservative defaults protect a small database; adjust application config deliberately or move to object storage when research assets grow. Files never depend on the ephemeral web filesystem.
- PDFs are validated using extension, signature, footer, and a basic active-content denylist, then served as attachments with `nosniff`. **This is not antivirus, complete PDF parsing, or a guarantee that a PDF is harmless.** Upload only trusted PDFs, scan them independently, and do not enable anonymous file uploads. Previously public assets can remain cached for up to one hour after access changes; never upload confidential information as public.
- No code execution, HTML authoring, or uploaded SVG rendering is exposed through the CMS. Use permitted images and safe Markdown for presentation.
- Health checks require database connectivity, a migrated schema, and the seeded profile record. Schema changes never run per request. The error page is independent of database availability.
- This is a tested implementation, not a professional penetration test, regulatory certification, legal opinion, or promise of production uptime. Configure privacy contacts, policies, provider agreements, backups, and monitoring for the actual deployment.

## 9. Structure

```text
app/
  __init__.py       # Application factory, headers, error handlers, CLI
  extensions.py    # SQLAlchemy, migrations, login, CSRF
  models.py        # Academic records, assets, messages, counters
  catalog.py       # Explicit CMS field allowlists
  forms.py         # Validation and dynamic editors
  security.py      # Shared atomic SQL rate limiting
  public/routes.py # Public pages, contact, assets, health, sitemap
  admin/routes.py  # Login, CMS CRUD, assets, inbox, visibility
  templates/       # Public and administrative Jinja templates
  static/          # Local CSS, JS, branding assets
migrations/        # Versioned Alembic schema
scripts/start.sh   # Migration + seed + Gunicorn
scripts/check_browser.py # Optional local browser validation
tests/             # Isolated automated tests
config.py
wsgi.py
requirements.txt
requirements-dev.txt
render.yaml
Dockerfile
.env.example
.github/workflows/tests.yml
```

The schema includes foreign keys with SET NULL behavior where records can be removed independently. Large binary columns are deferred until files are served. Foreign-key enforcement is enabled for SQLite development as well as PostgreSQL. Test-only fixture content never seeds the public application.

## 10. Remaining manual steps and information needed

**Configuration:** GitHub repository; hosting account; persistent PostgreSQL URL; strong secret; actual site origin; first administrator; database backup/restore procedure; retention-job operation; optional Resend sender and credentials; optional custom-domain DNS.

**Aanchal's content:** real photograph and alt text; reviewed headline/biography; undergraduate details; specialization, topic, supervisor, laboratory, expected dates and scores if she chooses to publish them; confirmed skills and specialized interests; project material and actual results; experience; permitted publications and figures; CV; actual professional email and profile links. Any of these may stay absent until verified.

No external image assets were downloaded, and no generated microscopy or experimental data are included. No deployment has been performed or verified as part of delivering this source package.
