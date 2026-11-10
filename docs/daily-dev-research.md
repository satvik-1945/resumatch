# daily.dev: verified research for the outreach workflow

Checked 2026-11-08 against official documentation; not an authenticated integration test.

## Confirmed
- Official remote MCP server: https://api.daily.dev/mcp (Streamable HTTP).
- OAuth sign-in or personal access token. No local daily.dev server is required.
- Tools include getFeedsForyou, getFeedsPopular, getFeedsDiscussed, getSearchPosts,
  getPostsById and getPostsByIdComments. Read-only tools can support a research digest.
- Public REST base: https://api.daily.dev/public/v1; same account quota as MCP.
- API/MCP are described as beta with gradual rollout; tools/access can change.
- Current site agent index states free accounts get 200 requests/month and Plus raises limits.
  The API guide also describes per-user/per-IP minute limits. Verify effective account quota
  from response headers/settings; docs landing-page FAQ still calls API a Plus feature.
  Do not assume unlimited free access or purchase an upgrade.
- PAT creation: https://daily.dev/settings/api. For a multi-user product use per-user OAuth;
  do not use one developer's personal feed/token as everybody's account.

## Fit
Good candidate for developer news, product launches, technical trends and company research.
Not a complete funding database, CEO directory, email finder or evidence of current hiring.
Follow article links to primary company/investor announcements and preserve source dates.
No reading, bookmarking or funding announcement should count as outreach sent.

## Small proposed daily experiment
At most 3 API calls/day initially (personalized feed + two searches), including retries in the
budget. Review up to five interesting leads. Keep original URL, publication time if supplied,
why interesting, company if explicitly identified, and verification needed. MCP host/scheduler
must enforce the call budget; three calls is not an already implemented scheduler.
Topics: fintech infrastructure, applied AI, developer tools, funding/product launches.

## Access and next step
No daily.dev token supplied or OAuth flow completed. Official pages were fetched live, but no
feed or authenticated MCP tool call was tested. Do not reuse LLM_API_KEY for daily.dev.
The first browser-capture slice can save selected context from daily.dev pages immediately.
Connect MCP in a compatible client with the URL above and read-only OAuth scope, then test
getSearchPosts or getFeedsForyou. PATs may have read/write access; invoke only read tools.
No OpenCode configuration or plugins were installed as part of this research.

## Sources
- https://docs.daily.dev/mcp-server.md/
- https://docs.daily.dev/public-api.md/
- https://api.daily.dev/llms.txt
- https://daily.dev/ (agent-readable index including free quota)
- https://api.daily.dev/public/v1/docs/json (schema reference; not yet used for integration)
