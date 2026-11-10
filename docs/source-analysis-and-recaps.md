# Source analysis and session recaps

## Explicit source-text analysis

On a pending capture in **Finish & review**, paste/edit up to 4,000 characters in **Source text**
and press **Analyze source text**. The request is authenticated, owner-scoped and origin-checked.
Only that text is sent to the configured provider, not the user's full history or credentials.
LinkedIn page reading remains disabled: pasting text does not create a contractual exemption or
remove content-owner/privacy restrictions. Use text you are entitled to process.

The server stores a proposal in `captures.analysis` (JSONB), separate from original capture and
reviewed details. It contains:

```text
schema_version: 1
method: llm | local
model: configured model, or null
analyzed_at: UTC timestamp
source_text: the analyzed input
source_sha256: hash of the input
suggestions:
  person: {value, source_quote} | null
  company: {value, source_quote} | null
  role: {value, source_quote} | null
  key_points: [{value, source_quote}]
warning: provider/configuration/fallback explanation | null
```

`Suggestions`, `Fact` and `Analysis` in `services/api/resumatch/intelligence.py` are the validating
Pydantic contracts. The provider receives their JSON schema. Unknown or ambiguous fields stay
null; values/quotes must be exact source substrings. Unsupported fields such as `action` are
rejected. Suggestions are candidate source claims, not independently verified facts.

**Use name/company in form** or **Use source points as note** changes only the editable form.
Saving/approval remains separate. Existing values are not silently overwritten. If the source
changes after analysis, use buttons are disabled until reanalysis. Approved/discarded records
cannot be analyzed. The server rechecks state after the external call to prevent late writes.
No row locks/database transaction are held during provider latency.

## Provider configuration

User selected OpenAI. Server-only ignored `.env` configuration:

```dotenv
LLM_API_KEY=your-valid-openai-key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4.1-mini
```

The model is configurable. This is an OpenAI-compatible chat-completions adapter, with JSON output,
a 25-second timeout, no redirects, a 64 KB response cap and a bounded completion size. Source text
is explicitly treated as untrusted data; no tools, URL following or external actions are available.

Missing settings, unsupported output, provider rejection, quota failures and network errors produce
visible local fallback. Local extraction only recognizes explicitly labeled `Name:`, `Company:`
and `Role:` lines; it is not presented as an LLM result. Stored suggestions record the actual method.
Successful identical-source analysis is cached to avoid repeated calls. Failed/local analysis can
be retried once configuration is corrected. Provider bodies/keys are not returned in errors.

One bounded live test used synthetic text against OpenAI. The stored key was rejected for
credentials/access; **no successful live LLM result was established**. No real contact text was
sent in that smoke check. Replace the key in ignored `.env` and restart the API before retrying.

## Structured completed-session recap

At completion, the same transaction stores a `session_recaps` record. Older completed sessions
get a snapshot on their first recap request. `RecapPayload` in `recaps.py` validates schema v1:

```text
schema_version, session_id, intention, generated_at, completed_at
session_seconds, target_minutes
approved_records, discarded_records
action_counts: researched/drafted/sent/followed_up/replied
channel_counts
known_people, known_companies, unknown_person_records
highlights, limitations
activities: [capture_id, action, channel, person, company, source_url,
             notes, source_text, occurred_at, followup_on]
```

All metrics and highlights are computed by the server from **approved** records. The model cannot
write action counts, invent replies or claim delivery. Normalized logged identities are not
verified unique real-world entities. The immutable completion snapshot keeps original reminder
dates; Today shows current cleared/due state separately.

The recap card presents time, reviewed activity bars, people/companies recorded and follow-up
steps. **View structured session JSON** and **Download session JSON** expose the private record
to its owner. The download is generated in the authenticated browser; it is not a public share.

## Optional AI observations

**Find AI observations** is a second explicit call on completed sessions. It uses only approved
notes/source-text excerpts: at most 20 populated records and 16,000 input characters. It does not
send pending/discarded content or fetch profile URLs. The model returns source-linked observations
with capture IDs and verbatim quotes. Unknown IDs or unsupported observations are rejected.

Observations, model/method, generation time and reviewed capture IDs are stored separately in
`session_recaps.reflection`. Successful results are reused. Failures leave the computed recap intact.
These are bounded source extracts, not broad career predictions or externally verified outcomes.

## Tables and migrations

Migration head: `0002_analysis_recaps`, preserving existing accounts and captures.

```sh
docker compose exec db psql -U resumatch -d resumatch
```

Inside psql:

```sql
\dt
\d captures
\d session_recaps
SELECT session_id, payload->'action_counts' AS actions FROM session_recaps;
\q
```

The UI, analysis routes and recap routes enforce per-user access. Browser-pairing credentials
remain capture-only and cannot trigger analysis or read a recap.
