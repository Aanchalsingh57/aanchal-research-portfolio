# Implementation validation — 26 October 2026

## Actual results

| Check | Result |
|---|---|
| Automated backend and CMS tests | **167 passed** in the final run |
| Database engines exercised | SQLite and local PostgreSQL 16 |
| Fresh PostgreSQL migration | Initial Alembic upgrade applied successfully |
| PostgreSQL schema-drift check | No new upgrade operations detected |
| SQLite migration/repeated upgrade | Passed in automated tests |
| Production configuration guards | Strong secret, PostgreSQL, HTTPS origin, trusted hosts, secure cookies tested |
| Resolved production dependency audit | No known vulnerabilities reported by pip-audit at delivery |
| Chromium responsive checks | 1440×1100, 768×1024, 390×844, 320×740 |
| Public pages per viewport | Homepage, projects, publications, notes, contact, login, about, privacy |
| Horizontal overflow | None on the tested pages at tested widths |
| Browser JavaScript errors | None observed |
| Automated accessibility | axe-core 4.11.0: zero violations in tested WCAG A/AA/2.1 checks |
| Accessibility pages | Homepage at four widths; contact/login at desktop and mobile; admin dashboard at desktop |
| Mobile menu | Open/close and Escape-key behavior passed |
| Workflow interaction | Native details disclosure opened/closed correctly |
| JavaScript-disabled navigation | Visible and reachable at 390 px |
| Reduced motion | Smooth scrolling disabled as expected |
| Contact in a real browser | CSRF-protected submission saved in disposable local inbox |
| Admin in a real browser | Login, draft creation, private preview, guest 404, logout passed |
| Desktop/mobile screenshots | Captured from locally rendered application and visually inspected |
| Render deployment | **Not performed** |
| Real email provider delivery | **Not performed**; success and failure paths tested with mocks |

Detailed machine-readable evidence is in `validation/`. The two browser reports separate functional authentication/contact checks from the final responsive screenshot run. Every browser test used disposable local data; no test project or message is included in production seeds or the downloadable source database. Screenshots are previews, not evidence of a live deployment.

## Scope and limits

Automated accessibility scans do not replace a full manual accessibility review or screen-reader testing. Passing tests and a clean package audit do not constitute a penetration test, security certification, or guarantee against unknown vulnerabilities. PDF validation is deliberately limited; only trusted administrator uploads should be used. Production database credentials, service uptime, DNS/TLS, backups, mail delivery, and retention scheduling must be configured and verified by the deployer.

See README.md for exact local setup commands, environment variables, Render instructions, account/hosting limitations, onboarding, and remaining manual steps. Render free PostgreSQL currently expires after 30 days and must not be treated as permanently free storage.
