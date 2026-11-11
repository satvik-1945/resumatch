# Parent workflows, dated runs and raw-text field extraction

## User-tested product structure

The repeated activity is a **workflow**; each timed session is a **run**. Existing session IDs,
capture IDs, original text, decisions and recaps remain intact. Run names default to UTC dates
and can be renamed without changing the original intention or activity history. The start form
accepts an optional custom name and previews the next automatic name. Same-workflow runs on the
same UTC day use `YYYY-MM-DD`, `YYYY-MM-DD (1)`, `YYYY-MM-DD (2)`, etc. Custom/renamed runs also
count toward that day's sequence, and occupied suffixes are skipped. Different workflows and new
UTC days have independent sequences. Allocation runs under the existing owner-row creation lock;
the final server-assigned name is authoritative if the preview crosses midnight. One open run
per account remains; completing it allows another run immediately, even on the same day.

User-confirmed existing groups:
- Fintech founder connections: the November 9 and 10 runs, including the 40-record pending review.
- Contact outreach: the November 9 outreach run.

Migration `0003_workflows` groups only the two explicitly known founder intention strings and
the known outreach intention; unrelated intentions keep their own parent. Classification does
not guess which people were messaged or turn research into connection requests. A private ignored
pre-migration DB dump was saved at `.local/pre-workflows.dump`; no reset occurred.

## Data model

- `workflows`: private owner, name/description/kind, current version.
- `workflow_versions`: immutable versioned definition JSONB (workflow ID + version composite key).
- `outreach_sessions`: adds workflow ID, workflow version and renameable `run_name`.
- `captures.details.fields`: validated typed custom values. Person/company remain existing top-level
  fields; Contact URL stays `source_url` to preserve old clients and provenance.
- `captures.details.notes`: **Raw capture text**, up to 16,000 characters. No separate source text
  or page title input in the active UI. Historical quote/title fields remain stored. Legacy quote
  text is included for processing when not already present in notes. `original` remains unchanged.
- `captures.analysis`: workflow schema version 2 result, source hash/text, workflow ID/version,
  provider/method, cited field values, filled/preserved field keys and warning.

Owner checks cover workflow list/update/contract/consolidation and run selection/linking. No browser
pairing credential can create workflows, read consolidated history, process AI or approve records.

## Field DSL and JSONata

Workflow setup accepts at most 20 fields. Each field declares:

```json
{
  "key": "industry",
  "label": "Industry / focus",
  "type": "text",
  "instruction": "Only explicit focus from the pasted text"
}
```

Types: text, long_text, number, boolean, date, url. Contact URL, Name (`person`) and Company remain
available. System/action/owner field keys cannot be overridden. Unknown facts are null/empty.
Numerical values must be finite; URLs require HTTP(S) without credentials. Manual writes are
validated against the run's version, including approval writes.

Saving compiles and persists a definition containing `dsl_version`, `fields`, `system_prompt`,
`output_schema` and `jsonata`. **Download DSL & JSONata** produces the private versioned JSON file.
No per-user files/secrets are committed into the repository. The generated JSONata expression maps
only validated field keys and is executed by `jsonata-python`; users do not submit executable code.

Example provider output and generated expression:

```json
{"fields":{"person":{"value":"Mira Example","source_quote":"Name: Mira Example"}}}
```

```jsonata
{"person": fields."person".value, "company": fields."company".value}
```

The output is checked against allowed fields, declared types and literal evidence **before** mapping.
Every non-null value needs a source quote found in the supplied raw text. The prompt distinguishes
main profile vs recommendations, education vs employer, and profile status buttons vs actions.
This supports reviewed extraction, not independent verification of profile claims.

## Processing a run

The top **Process with AI** button sequentially requests pending records with saved raw text. Each
request is owner/origin checked, validates its run contract and commits separately. It releases DB
transactions before calling the provider and rechecks raw text/state/schema afterward. A completed
or approved record is not rewritten. Non-empty manual/custom values are preserved, including zero
and false. Source URL, activity action, follow-up date and approval are never model-generated.

Grounding is per field. A value is kept only if it appears inside its `source_quote` and that quote
appears in the raw text, compared after normalizing whitespace, case and smart quotes/dashes (not
wording). Unsupported or invalid values are dropped individually, listed in `rejected_fields` and
the record's warning; the supported values still fill empty fields, and labeled `Field: value`
lines fill anything the model omitted. Malformed/out-of-contract output (unknown or system fields,
missing evidence) still rejects the whole answer (`failure: "output"`). Provider errors set
`failure: "provider"`; only those stop the UI pass. Other records are flagged and the pass continues.

The UI blocks Process with AI while capture forms have unsaved edits, and locks editable capture
fields for the duration of a processing pass. Clean forms refresh when returned fields change
(including retries whose source hash is unchanged); unsaved drafts are not remounted on AI hash
changes. The API already reloads the latest stored details after a provider call before filling
blanks, so manual values saved in another request during processing are also preserved. Repeated
cached processing returns current saved details rather than replaying old model values.

Successful identical text + workflow/version reuses stored results. Changed field definitions do
not silently change an existing run: an explicit additive sync updates its version; incompatible
type/removal changes require a new run. Old contract versions remain stored.

The UI shows processed count and can stop after the current record. Leaving the run stops further
requests; closing/crashing can leave the current server request completed, with its result reused
next time. This is a resumable foreground loop, **not** a background worker or scheduled job.
Fallback/provider failure stops the pass after that record; already saved results remain. Local
fallback only fills explicitly labeled fields and is visibly distinguished from an LLM result.

The provider input is bounded to 16,000 raw-text characters per record, 4,000 output tokens for the
workflow response, 64 KB response bytes and 25-second timeout. The API session capture limit remains
200. The user decides when to send text to the configured provider. No live LinkedIn page extraction.

## Consolidated records

An owned parent view groups non-discarded entries by normalized profile URL, or exact normalized
name/company, with URL fallback for unknown names. Latest non-empty logged values are displayed;
each run, action and pending/approved decision remains linked. This is not perfect identity
resolution and does not erase or merge capture history. Pending values are not verified facts.
Current bound: 5,000 source records per consolidated workflow view; exceeding it gives an explicit
limit error rather than a silently incomplete result. Server-side scalable pagination is future work.

## Activity and recap compatibility

Connection request sent (`connection_requested`) is separate from an initial message (`sent`).
Like messages/follow-ups/replies, request approval requires a named person and user confirmation.
No historical actions are reclassified from the workflow name or from pasted “Pending” buttons.
New recaps include workflow/run/version metadata and custom fields. Historical recap snapshots
remain unchanged and render missing new action counts as zero.

## Verification boundaries

API tests use real PostgreSQL and actual JSONata evaluation with synthetic provider results. A
synthetic 40-record run verifies field processing without approving or inventing activity. Browser
tests cover creating fields, dated runs, batch fallback, preserving manual fields, renaming,
consolidated cross-run contacts and native extension capture. A bounded live OpenAI request with
synthetic profile text successfully passed the generated contract and actual JSONata mapping.
The user's 40 real records were **not** automatically sent to the provider during implementation.

## Reused pasted text and bulk approve

Session views mark `same_raw_text_as` when a non-discarded record's raw text (whitespace/case
normalized) equals another record's under a different subject, usually a stale clipboard after
moving to the next profile. Every record in the group is flagged; only the user knows which profile
the text belongs to. `POST /api/sessions/{id}/captures/bulk-approve` takes the exact capture IDs
the user saw (max 500) in a review-state run. It approves those records as saved and skips, with a
reason: non-pending records, connection requests/sent/follow-ups/replies (always individually
confirmed), `duplicate_of`/`same_raw_text_as` records, and contacts already approved in the run.
Records captured after the list was shown are never swept in. The UI asks for confirmation first
and is disabled while edits are unsaved or AI is processing.

## Review counts, filters and consolidated manual entry

Workflow cards show total, waiting-for-review and approved counts (discarded excluded) before
opening. `workflow_view` returns `pending_count` per workflow and `pending_count`/`approved_count`
per run. Filter chips with counts are client-side: dated runs (runs with any pending/approved
record), consolidated contacts (any entry with that decision) and a run's records (also Discarded
when present). Filters never change bulk approval, which still uses the full eligible list.

**Consolidated records → + Add a record manually** reuses the capture form and Process with AI. A
record always belongs to a run: the form adds to this workflow's open active run. If the run is
paused it offers Resume. If none is open it offers an explicit "Start a run for manual entries"
(next default name; starts the timer). A run in review or another workflow's open run is not
bypassed; the UI explains what to finish first. Records still need approval in review.
