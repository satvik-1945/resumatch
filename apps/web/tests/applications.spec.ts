import { expect, test } from "@playwright/test";

const now = new Date().toISOString();
const fields = [
  { key: "contact_url", label: "Email link", type: "url" }, { key: "person", label: "Sender", type: "text" },
  { key: "company", label: "Company", type: "text" }, { key: "role", label: "Role", type: "text" },
  { key: "applied_via", label: "Applied via", type: "text" }, { key: "needs_reply", label: "Needs your reply", type: "boolean" },
];
function record(id: string, company: string, action: "applied" | "replied", extra: Record<string, unknown> = {}) {
  const details = { source_url: `https://mail.google.com/mail/u/me@example.com/#all/${id}`, source_title: `About ${company}`, quote: "",
    person: action === "replied" ? "Reshma LTM Interview" : "", company, channel: "email", action, occurred_at: now,
    notes: `From: someone\nSubject: About ${company}`, followup_on: action === "replied" ? now.slice(0, 10) : null,
    fields: { role: null, applied_via: action === "applied" ? "LinkedIn" : null, needs_reply: action === "replied" }, ...extra };
  return { id, details, original: details, source: "email", decision: "pending", created_at: now, reviewed_at: null, followup_done: false };
}

test("applications: setup state, counts, amber replies and the inbox review run", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "New here? Create an account" }).click();
  await page.getByLabel("Email", { exact: true }).fill(`apps-${crypto.randomUUID()}@example.com`);
  await page.getByLabel("Password", { exact: true }).fill("synthetic applications passphrase");
  await page.getByRole("button", { name: "Create account", exact: true }).click();

  // Real API: this test stack has no Google client, so the page explains what to configure.
  await page.getByRole("navigation").getByRole("button", { name: "Applications" }).click();
  await expect(page.getByRole("heading", { name: "Applications", level: 1 })).toBeVisible();
  await expect(page.getByText("Gmail isn’t set up on this server yet.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Scan inbox" })).toBeDisabled();

  // Synthetic inbox data on top of the real UI (Google is never contacted from tests).
  const runId = "00000000-0000-4000-8000-0000000000e1";
  const overview = { configured: true, open_run_id: runId,
    accounts: [{ id: "a1", email: "me@example.com", connected_at: now, last_scanned_at: now, last_error: null }],
    counts: { applied: 12, applied_this_week: 5, applied_to_review: 2, responses: 1, responses_to_review: 1, needs_reply: 1 },
    recent_responses: [{ id: "r1", decision: "pending", person: "Reshma LTM Interview", company: "LTM", subject: "Register your LTM Application",
      source_url: "https://mail.google.com/mail/u/me@example.com/#all/m4", received_at: now, needs_reply: true }] };
  await page.route("**/api/email", route => route.fulfill({ json: overview }));
  await page.route("**/api/email/scan", route => route.fulfill({ json: { ...overview, scanned: 6, applications: 2, responses: 1,
    ignored: 2, viewed: 0, duplicates: 1, warnings: [], run_id: runId } }));
  const captures = [record("c1", "GTECH LLC", "applied"), record("c2", "Humaniti AI", "applied"), record("c3", "LTM", "replied")];
  await page.route(`**/api/sessions/${runId}`, route => route.fulfill({ json: { id: runId, intention: "Inbox scan: applications and replies",
    target_minutes: 5, state: "review", elapsed_seconds: 0, started_at: now, finished_at: now, completed_at: null, approved_count: 0,
    pending_count: 3, counts: {}, captures, workflow_id: "w1", workflow_name: "Job applications", workflow_version: 1, run_name: "2026-11-17",
    workflow_kind: "job_applications", source: "email", field_definition: fields } }));
  await page.reload();
  await page.getByRole("navigation").getByRole("button", { name: "Applications" }).click();
  await expect(page.locator(".app-stats")).toContainText("12");
  await expect(page.locator(".app-stats section.amber")).toContainText("NEED YOUR REPLY");
  await expect(page.locator(".reply-row.amber")).toContainText("LTM");
  await page.getByRole("button", { name: "Scan inbox" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Checked 6 new emails" })).toContainText("2 applications, 1 reply, 2 not about a job, 1 repeat of the same thread");

  await page.getByRole("button", { name: "Review 3 new records →" }).click();
  await expect(page.getByRole("heading", { name: "Inbox scan: applications and replies" })).toBeVisible();
  await expect(page.locator(".capture.reply")).toHaveCount(1);
  await expect(page.locator(".capture.reply")).toContainText("Needs your reply");
  await expect(page.getByRole("button", { name: "Approve all eligible (2)" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(0);
  await page.screenshot({ path: test.info().outputPath("applications.png"), fullPage: true });
});
