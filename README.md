# Outreach sessions

**Create a workflow → run it by date → capture raw text → process fields → review.**

A private-first outreach activity tracker for Satvik's international startup/fintech job search.
Resumatch is the working repository name. The former resume-first app was explicitly reset.

Project docs live in the private [personel-docs](https://github.com/satvik-1945/personel-docs/tree/main/resumatch)
repo (locally `~/f/personel-docs/resumatch`):

- [Codebase guide](https://github.com/satvik-1945/personel-docs/blob/main/resumatch/codebase-guide.md): architecture, flows, data model, invariants
- [Product](https://github.com/satvik-1945/personel-docs/blob/main/resumatch/product.md)
- [Dev log with exact verification results](https://github.com/satvik-1945/personel-docs/blob/main/resumatch/dev-log.md)

## What works now

Parent workflows with configurable fields, renameable dated runs, consolidated contacts across
runs, durable timers, browser/manual raw-text capture, and run-level AI processing. Each workflow
generates a versioned field DSL, extraction prompt, JSON output schema and executable JSONata mapping.
Research, drafts, connection requests, messages, follow-ups and replies remain separate. Only
reviewed/approved records count. Completed runs have stored recap cards and downloadable JSON.
[Workflow contracts and AI grounding](https://github.com/satvik-1945/personel-docs/blob/main/resumatch/codebase-guide.md#53-process-with-ai-workflowsprocess_capture).

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

Open **http://localhost:3000** and sign in (or create an account for a fresh install).
`http://127.0.0.1:3000` is also explicitly allowed. Cookies are host-specific.
There is no seed data or required candidate-profile form. API docs: http://127.0.0.1:8000/docs.

## Workflows and dated runs

1. Open **Workflows → Create workflow**. Start with founder connections, the contact-outreach
   template, or only contact fields. Name it, edit/add fields and their extraction instructions,
   then **Save workflow**. Contact URL, Name and Company stay available; other fields are optional.
2. Open the workflow and **Start a run**. Enter an optional session name, or leave it blank for
   the suggested UTC date-based name: `2026-11-11`, `2026-11-11 (1)`, `2026-11-11 (2)`, etc.
   Repeat the same workflow after completing the previous run; there is no one-run-per-day limit.
   Numbering is per workflow and UTC day, including custom-named or subsequently renamed runs.
   Choose an intention/time, then **Start run**. Pause before a break; closing the page doesn't pause.
3. Capture the **Contact URL** and paste **Raw capture text** in the extension or manual form.
   The same box holds copied snippets, context and rough notes. Known fields can be entered,
   otherwise leave them blank for processing. No separate page-title/source-analysis input.
4. At the top of the run, **Process with AI** works through pending saved raw text using the
   workflow's field DSL and JSONata. Progress is saved per record; stop after the current record
   or resume later. Existing non-empty fields are preserved, including numeric `0` and boolean
   `false`. Unsaved capture edits must be saved/cancelled before processing; form fields are
   temporarily disabled during an AI pass. Unknowns remain empty. Each AI value must appear in
   a quote found in the raw text (ignoring spacing, case and smart quotes); unsupported values are
   skipped individually and named on the record, and the pass continues. Only a provider failure
   (key, quota, network) stops the pass, rather than repeatedly charging retries.
5. **Finish & review**. Check each compact record, expand **Review fields & approve**, correct
   extracted values, then approve/discard. Requests, messages, follow-ups and replies require your
   explicit confirmation; AI cannot infer actions from a profile's buttons or “Pending” text.
   **Approve all eligible** (two-step) approves the listed pending records as saved, skipping
   confirmed actions and possible duplicates. Records whose pasted text matches another record
   under a different profile URL are flagged as a likely stale clipboard; fix or discard those.
   Filter chips (All / Waiting for review / Approved, with counts) narrow a run's records.
6. **Complete session** to save the run and recap. Return to the parent workflow for dated runs
   or **Consolidated records**. Repeated profile identities across dates share one contact row,
   with each run/action/decision still visible. Pending records are labeled and discarded ones excluded.

**Edit fields & name** creates a new workflow version. Existing runs keep their field contract;
use **Use latest workflow fields** to adopt additive updates in an open run. Removing/changing
field types applies to new runs instead. **Download DSL & JSONata** gives the generated contract.
Only completed runs with an approved record count toward weekly goals; boundaries use UTC.

The workflow migration preserves existing sessions/captures, including the current 40-record run.
The two known fintech-founder runs are grouped under **Fintech founder connections**; the other
known run is under **Contact outreach**. No capture decisions/actions are reclassified by migration.

Follow-up dates create reminders after approval. **Clear reminder** only clears the reminder;
capture a real follow-up action separately if you sent one.

## Browser capture (Chrome / Chromium)

1. Open `chrome://extensions`, enable **Developer mode**, then **Load unpacked**.
2. Select this repository's **apps/extension** folder and pin **Outreach capture**.
3. Open its popup and copy the **Extension ID**.
4. In the app, choose **Browser capture**, paste the ID, and generate a pairing token.
5. Paste the token in the extension. Choose **Local API · 8000** and save pairing.
6. Start a run in the app. On a normal web page, optionally select a useful passage, then
   click the extension or use **Alt+Shift+L** (configurable at `chrome://extensions/shortcuts`).
7. Check **Contact URL**, paste **Raw capture text**, optionally choose known details/activity,
   and **Capture for review**. Process configured fields from the run in the app.

### Contact check and message briefs (Contact outreach)

After you connect with someone, start a **Contact outreach** run. Open their profile and click the
extension (reload it in `chrome://extensions` after updating; v0.5.0). It sends **only the tab's URL**
to your API and shows right away whether that profile is already in your records (e.g. your
Fintech founder run): name, company, fields, run, action and review state.

**Generate message brief** (labeled Premium · research; not gated yet) needs **About you**, saved
once in the app under any record's **Check records & message brief**. Optionally give the company
website. The server reads only that public site (homepage + `/about`, never LinkedIn). It refuses
private/local addresses, ports other than 80/443, and non-HTML. It returns talking points for a note
you write by hand:
what they do (each fact must quote the site or it's dropped), hooks, your matching credential,
bridge, soft ask, things to avoid, and a reference draft to rewrite. Nothing is sent or logged as
activity; log what you actually sent as a capture. In the app, records in Contact outreach runs with
a LinkedIn/X profile URL have the same **Check records & message brief** panel.

### Placement and LinkedIn mode

Reload the extension in `chrome://extensions` after updating to version **0.4.0**. In its popup,
choose **Open movable window**. It starts near the left of your source browser. Drag its native
window title bar to place it anywhere, resize it, use **Collapse / Expand**, or **Hide window**.
Enable **Hide window after a successful capture** if desired. This is a separate browser window,
not an element placed over LinkedIn's HTML. Nothing opens automatically on page navigation.

**LinkedIn pages use manual logging.** Their URL may be populated from the browser tab, but the
extension does not execute page scripts to read LinkedIn HTML, titles, selected text or messages.
Enter your own activity details and notes. On other normal sites, explicit selected-text capture
is available. Our earlier non-modifying capture behavior was not enough to establish compliance:
LinkedIn's terms also restrict software used to copy data. We do not claim LinkedIn approval or
guarantee account safety. See the [official-source review](https://github.com/satvik-1945/personel-docs/blob/main/resumatch/decisions/linkedin-policy.md).

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

### Raw-text processing and your run recap

**Process with AI** uses saved **Raw capture text** to fill this run's configured fields. When
editing text/fields during review, **Save draft changes** before processing. Analysis stores the
workflow/version, source hash, cited facts, filled/preserved keys and actual provider/fallback
method separately from original captures. It does not approve records or infer action/reminder
dates. No LinkedIn HTML reading was added. Only process content you are entitled to use.

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

Restart the API after editing `.env`. The rotated key passed a live synthetic source-analysis
check with gpt-4.1-mini; no real contact text was used. Local labeled-field suggestions
and the full computed recap also work without it. Provider failures are shown explicitly. No real
key belongs in `.env.example` or a browser bundle. See [workflow contracts](https://github.com/satvik-1945/personel-docs/blob/main/resumatch/codebase-guide.md#6-workflow-field-dsl-workflow_contractspy).

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
access and quotas require verification with your account. See the [research note](https://github.com/satvik-1945/personel-docs/blob/main/resumatch/decisions/daily-dev.md).

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
  Existing installs now run `uv run alembic upgrade head` to reach `0004_contact_briefs`.

### Inspect tables

For a browser-based database UI, start **Adminer**:

```sh
docker compose up -d db-ui
```

Open **http://localhost:8082** and enter:

| Login field | Value |
| --- | --- |
| System | PostgreSQL |
| Server | `db` |
| Username | `resumatch` |
| Password | The `POSTGRES_PASSWORD` value in your ignored `.env` |
| Database | `resumatch` |

Use `db` rather than localhost in the Server field: Adminer connects to PostgreSQL across the
project's Docker network. The UI is bound only to `127.0.0.1`; `DB_UI_PORT` can change its host port.
Select a table, then **Select data** to browse/filter rows. **SQL command** runs queries; for
readable capture fields, try:

```sql
SELECT id, details->>'person' AS person, details->>'company' AS company,
       details->>'action' AS action, decision
FROM captures
ORDER BY created_at DESC
LIMIT 50;
```

You can also log in to `resumatch_test` to inspect this project's disposable test data. Adminer
can edit/delete data as well as read it, so use **Select data** when you only want to browse.
Stop just the UI with `docker compose stop db-ui`; PostgreSQL keeps running and its volume is
unchanged. This setup connects only this project's databases, not other Docker projects.

For terminal access:

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
```

Public sharing, maps, passive provider synchronization, MCP capture adapter, automatic discovery
and a broader job tracker wait until five real sessions establish whether this loop is useful.
