# LinkedIn terms review and capture UX decision

Checked 2026-11-09 against LinkedIn's official pages, not a search-engine AI summary.

## Finding

We cannot describe the original extension's LinkedIn selected-text capture as approved or
compliant just because it did not change HTML or send messages. Reading data and modifying
the page are separate issues. A user click does not supply LinkedIn's permission.

LinkedIn User Agreement, effective November 3, 2025:

- **8.2.2** prohibits developing/supporting/using software, scripts or browser plugins to scrape
  **or copy** the Services, including profiles and other data.
- **8.2.4** restricts copying/using/displaying/distributing information obtained from the Services
  without the content owner's consent. It is broader than automated bulk scraping.
- **8.2.13** prohibits unauthorized automated access/actions, including contacts and messaging.
- **8.2.15** prohibits overlays and modifications to the Services or their appearance.
- **3.4** reserves restriction, suspension and termination for contract violations or misuse.

The official help page restates scraping/copying, automation and overlays as prohibited and
describes account restriction/shutdown as possible consequences. It does not say that every
browser extension, regardless of behavior, is forbidden.

These are contractual/platform rules. They are not enough to establish that a particular use is
criminal, lawful in every jurisdiction, or immune from civil/privacy claims. This research is not
a legal determination, LinkedIn review, written authorization or assurance against restrictions.
No detection-evasion research or anti-detection behavior is part of the implementation.

## Implemented change

On linkedin.com and its subdomains, the extension now dispatches **manual logging**:

- No scripting execution to read LinkedIn HTML, title, selected text, messages or profiles.
- The browser's user-selected tab URL can populate the source link; title and quote start blank.
- Person/company/action/notes/reminder are entered by the user, not inferred.
- No page overlays, buttons, styles, DOM mutation, request interception or auto-send behavior.
- A defensive guard inside the page-reader also refuses LinkedIn before accessing the DOM.
- Previously stored drafts/history are not erased; review any older captured content yourself.

This narrows integration behavior substantially but **does not establish an express contractual
exception**. URL collection/deep-linking and content-owner rules still need consideration; the
agreement also has a deep-link restriction (8.2.12). The lower-integration option is recording your
own activity/notes manually in our independent app. For commercial claims/distribution, obtain
specific legal advice and/or written permission rather than advertising “LinkedIn-compliant.”

Generic company/news-page selected-text capture remains explicit, subject to each site's terms.
The LinkedIn mode is not a promise about X, email or other platforms' permission policies.

## Panel placement and behavior

The existing toolbar popup is anchored/closed by Chrome; its position is not freely controlled by
the page. A draggable HTML overlay would contradict the user's requirement and LinkedIn's overlay
rule. Chrome's side panel is a legitimate browser-owned alternative, with left/right preference
controlled by Chrome, but it is docked rather than freely draggable and opening requires a gesture.

Implemented **Open movable window** instead: a separate extension-owned popup window starts near
the source browser's left edge, can be moved/resized with native window controls, collapses/expands,
and can be hidden/minimized. A user-selected checkbox hides it after successful capture. Capture
stays explicit; there are no unsolicited popups or navigation-triggered page reads. It uses the
active tab of the source browser window. Navigating elsewhere may require invoking the toolbar
again to renew activeTab permission. OS focus and minimum window sizes remain browser/OS controlled.

## Duplicate policy

One record per identified person per session. A capture request's ID still handles retry safety;
a second, new request ID additionally checks the subject under the session row lock.

- LinkedIn `/in/<slug>` variants normalize scheme, subdomain, query, fragment, trailing slash and
  profile detail subpaths. X/Twitter direct profile URLs normalize to one identity too.
- Known names normalize case/Unicode/whitespace and a trailing platform label. A matching name
  with compatible/unknown company is a duplicate candidate even on different channels.
- Different explicit profile identities beat equal names. Known different people on one shared
  article/inbox page are not merged. Anonymous identical-source research is blocked as a repeat.
- This is conservative deterministic matching, not proof that two names are the same person.
  Different spellings, alternate profiles or different unknown source URLs may need manual review.
- New duplicates return 409 with the existing capture ID. Use **Edit capture** while active/paused
  to update its action, notes or reminder. One card holds the current reviewed action; it is not a
  full multi-message timeline. Original captured fields remain preserved separately.
- Historical duplicates are retained, flagged and resolved through review/discard. Approval prevents
  a second approved subject in that session. Future sessions can contact the same person again.

## Sources

- https://www.linkedin.com/legal/user-agreement
- https://www.linkedin.com/help/linkedin/answer/a1341387/prohibited-software-and-extensions
- https://developer.chrome.com/docs/extensions/reference/api/sidePanel
- https://developer.chrome.com/docs/extensions/reference/api/windows

## Verification boundary

Automated tests exercise the packaged LinkedIn dispatch with synthetic tab metadata and an executor
that must not be called. They do not visit a LinkedIn account or establish live platform approval.
The real unpacked extension/window capture test uses a controlled loopback page. Native drag behavior
is OS-provided; collapse/expand/window creation and capture flow are browser-tested.
