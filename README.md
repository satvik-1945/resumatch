# Outreach sessions

**Start a session → capture as you browse → review → see your progress.**

A private-first outreach activity tracker for Satvik's international startup/fintech job search.
Resumatch is the working repository name. The former resume-first app was explicitly reset.

- [Product baseline](PRODUCT_PLAN.md)
- [Active checklist and exact verification results](V1_TASKS.md)
- [daily.dev MCP/API research](docs/daily-dev-research.md)
- [Architecture and activity definitions](docs/outreach-architecture.md)

## What works now

Local accounts, session intentions and durable timers, pause/resume, browser-assisted or manual
capture, review/edit/approve/discard, private history, weekly goals, and due follow-up reminders.
Research, drafts, sends, follow-ups and replies remain separate. Only approved records count.
Review also supports explicit source-text analysis, and completed sessions have stored recap
cards with downloadable JSON. [Analysis and recap details](docs/source-analysis-and-recaps.md).

## Local setup

Requires Python 3.12+, uv, Node **22.13+**, npm, and Docker Compose.
Run commands from the repository root. Copy the example only on a **fresh** installation;
keep your existing ignored `.env` if it already contains credentials.

```sh
cp .env.example .env
docker compose up -d --wait db
uv sync --frozen
npm --prefix apps/web ci
uv run alembic upgrade head
```

The dedicated database is `resumatch`, container **resumatch-db-1**, host **127.0.0.1:55432**,
volume **resumatch_postgres_data**. Other project databases are independent.

Start the API:

```sh
uv run uvicorn resumatch.main:app --reload --host 127.0.0.1 --port 8000
```

In a second terminal:

```sh
npm --prefix apps/web run dev
```

Open **http://localhost:3000** and create a new account. The reset removed previous accounts,
profiles and imports. `http://127.0.0.1:3000` is also explicitly allowed. Cookies are host-specific.
There is no seed data or required candidate-profile form. API docs: http://127.0.0.1:8000/docs.

## Your first real session

1. Enter a small intention, for example “Research and contact one fintech founder.”
2. Choose a time intention and **Start session**. The timer measures elapsed session time,
   not verified focus. Pause before a break. Closing the page does not pause it.
3. Use the extension below, or **Add a quick manual capture**. Keep unknown person/company
   fields blank. Paste a source URL and choose what actually happened.
4. **Finish & review**. Correct records and approve or discard each one. Sends, follow-ups
   and replies require a named person and explicit confirmation. Approval is your confirmation,
   not platform-verified sending or delivery.
5. **Complete session**. It contributes to the weekly session goal only if at least one record
   was approved. Weekly boundaries use UTC. History includes empty/discarded sessions honestly.

Follow-up dates create reminders after approval. **Clear reminder** only clears the reminder;
capture a real follow-up action separately if you sent one.

## Browser capture (Chrome / Chromium)

1. Open `chrome://extensions`, enable **Developer mode**, then **Load unpacked**.
2. Select this repository's **apps/extension** folder and pin **Outreach capture**.
3. Open its popup and copy the **Extension ID**.
4. In the app, choose **Browser capture**, paste the ID, and generate a pairing token.
5. Paste the token in the extension. Choose **Local API · 8000** and save pairing.
6. Start a session in the app. On a normal web page, optionally select a useful passage, then
   click the extension or use **Alt+Shift+L** (configurable at `chrome://extensions/shortcuts`).
7. Check the URL/title/selection, add known details, and **Capture for review**.

### Placement and LinkedIn mode

Reload the extension in `chrome://extensions` after updating to version **0.3.0**. In its popup,
choose **Open movable window**. It starts near the left of your source browser. Drag its native
window title bar to place it anywhere, resize it, use **Collapse / Expand**, or **Hide window**.
Enable **Hide window after a successful capture** if desired. This is a separate browser window,
not an element placed over LinkedIn's HTML. Nothing opens automatically on page navigation.

**LinkedIn pages use manual logging.** Their URL may be populated from the browser tab, but the
extension does not execute page scripts to read LinkedIn HTML, titles, selected text or messages.
Enter your own activity details and notes. On other normal sites, explicit selected-text capture
is available. Our earlier non-modifying capture behavior was not enough to establish compliance:
LinkedIn's terms also restrict software used to copy data. We do not claim LinkedIn approval or
guarantee account safety. See the [official-source review](docs/linkedin-capture-review.md).

The movable window targets the active tab in the source browser window. After a cross-site
navigation, Chrome may require you to invoke the toolbar again for a new activeTab grant. Use
manual capture in the app if the browser won't expose the page.

### One person, one session record

Same-session duplicate captures are rejected using normalized profile URLs and known names.
Update the existing card through **Edit capture** instead: change its action, note or reminder.
Different sessions may include the same person again. This matching is deterministic rather than
fuzzy identity resolution; use a direct profile URL and accurate name when possible.
Older duplicates remain in your data, get flagged, and can be discarded during review.

### Where follow-up dates appear

- Every captured card displays **Company**, **Activity time**, and **Follow-up**.
- Before approval the date says **planned, awaiting approval**; it is not a scheduled reminder yet.
- After approval, a future date appears under **Upcoming follow-ups** on Today.
- When that UTC date arrives, it appears under **Due follow-ups**.
- **Clear reminder** clears the task only. Record an actual follow-up action separately.
- No date selected is shown as **No reminder set**. Nothing invents a follow-up date.

### Source-text analysis and your session recap

During **Finish & review**, expand **Source text & analysis**, paste relevant text, then choose
**Analyze source text**. Source-backed name, company, role and key-point suggestions appear below.
Choose **Use name/company in form**, edit as needed, then approve separately. Actions/reminder dates
are never inferred. Nothing is extracted from LinkedIn HTML, and pasting text into an LLM does not
establish permission under LinkedIn's terms. Only process content you are entitled to use.

After completing a session, its recap shows session time, approved action counts, known people/
companies, and next follow-ups. It is stored in PostgreSQL and available in history. Use
**Download session JSON** for your structured record. **Find AI observations** optionally extracts
source-linked points from bounded excerpts of approved notes/source text; metrics remain computed
by the server. Source analysis and observations require an explicit click, never automatic sending.

Optional OpenAI configuration in ignored `.env`:

```dotenv
LLM_API_KEY=your-valid-openai-key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4.1-mini
```

Restart the API after editing `.env`. The stored key was rejected by OpenAI during a synthetic
smoke test; replace it with a valid key to enable live results. Local labeled-field suggestions
and the full computed recap work without it. Provider failures are shown explicitly. No real
key belongs in `.env.example` or a browser bundle. See [the data contracts](docs/source-analysis-and-recaps.md).

For supported non-LinkedIn pages, the extension reads the current tab only after invocation. No passive monitoring, guessed contact
facts, automated sends or full-inbox scraping. Chrome's internal pages cannot be captured.
Manual capture remains available. Source text is limited to the first 4,000 selected characters.

Pairing tokens last seven days and are capture-only: they cannot read account history or approve
records. Revoke from the app's Browser capture page. The popup stores an unsent draft locally and
reuses its request ID on retry, so an interrupted request doesn't create duplicate records.
After editing extension files, reload the unpacked extension in Chrome.

## daily.dev

Official remote MCP endpoint: **https://api.daily.dev/mcp**. It supports personalized feeds,
article search and post details, with OAuth or a daily.dev personal access token. It is in beta;
access and quotas require verification with your account. See the [research note](docs/daily-dev-research.md).

The app currently offers links to daily.dev and its MCP setup guide. This is **not a connected
feed or scheduled discovery job**. No daily.dev credential was supplied. You can immediately
capture selected context from daily.dev/company/news pages as research. Do not reuse an LLM key
as a daily.dev token; personal tokens belong only in ignored local configuration.

## Health and verification

```sh
curl --fail http://127.0.0.1:8000/api/health/live
curl --fail http://127.0.0.1:8000/api/health/ready
uv run alembic current
uv run alembic check
```

Create the test database **once** if absent:

```sh
docker compose exec -T db createdb -U resumatch resumatch_test
```

`TEST_DATABASE_URL` must point to a disposable PostgreSQL DB ending in `_test`. Tests drop its
public schema and run migrations from empty; they never reset the normal application DB.

```sh
uv run ruff check .
uv run pytest -q
npm --prefix apps/web run typecheck
npm --prefix apps/web run lint
npm --prefix apps/web run build
```

Install the Playwright Chromium browser once (from `apps/web`):

```sh
npx playwright install chromium
```

Then from the root:

```sh
npm --prefix apps/web run test:e2e
```

Run API and browser tests **sequentially**: they share the test DB. Playwright starts/stops test
API/web servers on 8001/3001 and uses `.next-e2e` output alongside any normal dev server. Tests
include desktop/mobile session flow and a real unpacked extension capturing a controlled local
page. This does not establish LinkedIn inbox or daily.dev authenticated API access. Screenshots,
traces and isolated Chromium profiles are ignored test artifacts.

## Stop/restart and troubleshooting

Ctrl-C stops foreground app servers. `docker compose stop db` stops only this project's DB;
`docker compose up -d --wait db` restarts it with its data. `docker compose down` retains the
volume; `docker compose down -v` deletes it.

- **Origin rejected:** use localhost:3000 or 127.0.0.1:3000. Update `WEB_ORIGIN` and the explicit
  `WEB_ADDITIONAL_ORIGINS` JSON list for a different address, then restart the API.
- **No active session in extension:** start/resume a session in the app and refresh the popup.
- **Restricted-page capture error:** open a normal HTTP(S) page and invoke the toolbar again.
- **Pairing expired/revoked:** generate a new token in the app. Tokens are never account passwords.
- **503 / readiness failure:** check the DB container, `.env` database URL, and migration head.
- **Post-reset first start:** use the new schema head `0001_outreach`. Archived migrations are
  deliberately not part of the new chain; the earlier project reset has already been executed.
  Existing installs now run `uv run alembic upgrade head` to reach `0002_analysis_recaps`.

### Inspect tables

```sh
docker compose exec db psql -U resumatch -d resumatch -c '\dt'
docker compose exec db psql -U resumatch -d resumatch -c '\d session_recaps'
```

## Layout

```text
apps/web/                  Next.js + TypeScript app and Playwright tests
apps/extension/            Explicit Chrome active-tab capture extension
services/api/resumatch/    FastAPI auth, session/capture/review domain API
services/api/migrations/   New Alembic schema, starting at 0001_outreach
services/api/tests/        Real PostgreSQL tests
docs/archive/              Superseded planning references, not active requirements
```

Public sharing, maps, passive provider synchronization, MCP capture adapter, automatic discovery
and a broader job tracker wait until five real sessions establish whether this loop is useful.
