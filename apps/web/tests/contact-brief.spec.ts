import { expect, test, type Page } from "@playwright/test";

// The profile URL is only stored as text; no LinkedIn page is opened or requested.
const profile = "https://www.linkedin.com/in/synthetic-mira/";

async function captureProfile(page: Page, notes: string) {
  await page.getByRole("button", { name: "+ Add a quick manual capture" }).click();
  await page.getByLabel("Contact URL", { exact: true }).fill(profile);
  await page.getByRole("textbox", { name: "Raw capture text", exact: true }).fill(notes);
  await page.getByRole("button", { name: "Capture for review", exact: true }).click();
  await expect(page.getByText("Captured for review.", { exact: false })).toBeVisible();
  await page.getByRole("button", { name: "Close manual capture" }).click();
}

test("outreach record checks the founder workflow and shows a grounded message brief", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "New here? Create an account" }).click();
  await page.getByLabel("Email", { exact: true }).fill(`brief-${crypto.randomUUID()}@example.com`);
  await page.getByLabel("Password", { exact: true }).fill("synthetic brief passphrase");
  await page.getByRole("button", { name: "Create account", exact: true }).click();
  await page.getByRole("navigation").getByRole("button", { name: "Workflows" }).click();
  await page.getByRole("button", { name: "Create workflow", exact: true }).click();
  await page.getByRole("button", { name: "Save workflow", exact: true }).click();
  await page.getByRole("button", { name: "Start a run", exact: true }).click();
  await page.getByLabel("Session intention").fill("Find founders");
  await page.getByRole("button", { name: /Start run/ }).click();
  await captureProfile(page, "Name: Mira Example\nCompany: Synthetic Pay");
  await page.getByRole("button", { name: "Process with AI", exact: true }).click();
  await expect(page.getByText(/Local fallback · 2 fields filled/)).toBeVisible();
  await page.getByRole("button", { name: "Finish & review" }).click();
  await page.getByRole("button", { name: "Approve record", exact: true }).click();
  await page.getByRole("button", { name: "Complete session", exact: true }).click();

  await page.getByRole("navigation").getByRole("button", { name: "Workflows" }).click();
  await page.getByRole("button", { name: "Use contact outreach template" }).click();
  await page.getByRole("button", { name: "Save workflow", exact: true }).click();
  await page.getByRole("button", { name: "Start a run", exact: true }).click();
  await page.locator(".start-card").getByLabel("Workflow").selectOption({ label: "Contact outreach" });
  await page.getByLabel("Session intention").fill("Message new connections");
  await page.getByRole("button", { name: /Start run/ }).click();
  await captureProfile(page, "Connected today");

  await page.getByRole("button", { name: "Check records & message brief" }).click();
  const panel = page.getByRole("region", { name: "Contact check and message brief" });
  await expect(panel.getByRole("heading", { name: "✓ Already in your records · 2" })).toBeVisible();
  await expect(panel).toContainText("Mira Example · Synthetic Pay");
  await expect(panel).toContainText("Fintech founder connections");
  await expect(panel.getByRole("button", { name: "Generate message brief" })).toBeDisabled();

  // About you: upload a resume file, save, and build a persona.
  await panel.getByRole("button", { name: "Add your resume under About you" }).click();
  await expect(page.getByRole("heading", { name: "About you", level: 1 })).toBeVisible();
  await page.getByLabel("Upload resume file").setInputFiles({ name: "resume.txt", mimeType: "text/plain",
    buffer: Buffer.from("Forward Deployed Engineer, fintech\n- Built 2 products from scratch") });
  await expect(page.getByLabel("Your resume")).toHaveValue(/Built 2 products from scratch/);
  await page.getByLabel("About you").fill("Casual. Sign off: cheers, Sam");
  await page.getByRole("button", { name: "Save", exact: true }).click();
  await expect(page.getByRole("status")).toContainText("Saved.");
  await page.getByRole("button", { name: "Build my persona" }).click();
  await expect(page.locator("p.error")).toContainText("AI persona unavailable");
  await page.route("**/api/profile/persona", async route => {
    const profile = await (await page.request.get("/api/profile")).json();
    await route.fulfill({ json: { ...profile, persona: { headline: "Forward deployed engineer in fintech", summary: "Ships products.", domains: ["fintech"],
      strengths: [], proof_points: [{ point: "Built 2 products from scratch", evidence: "Built 2 products from scratch" }],
      dropped: 0, stale: false, generated_at: new Date().toISOString(), model: null } } });
  });
  await page.getByRole("button", { name: "Build my persona" }).click();
  const persona = page.getByRole("region", { name: "Your persona" });
  await expect(persona.getByRole("heading", { name: "Forward deployed engineer in fintech" })).toBeVisible();
  await expect(persona).toContainText("“Built 2 products from scratch”");

  await page.getByRole("navigation").getByRole("button", { name: "Today" }).click();
  await page.getByRole("button", { name: "Check records & message brief" }).click();
  await panel.getByLabel("What you know & your goal").fill("Posted about hiring. Goal: intro chat.");

  // Tests have no provider key: the real API reports it instead of inventing a brief.
  await panel.getByRole("button", { name: "Generate message brief" }).click();
  await expect(panel.getByRole("alert")).toContainText("AI brief unavailable");

  // Synthetic provider output, served on top of the real cross-workflow lookup.
  const found = await (await page.request.get(`/api/contacts/lookup?url=${encodeURIComponent(profile)}`)).json();
  expect(found.records).toHaveLength(2);
  await page.route("**/api/contacts/brief", async route => {
    expect(route.request().postDataJSON().context).toBe("Posted about hiring. Goal: intro chat.");
    await route.fulfill({ json: { ...found, brief: { company_url: "https://synthetic-pay.example", context: "Posted about hiring. Goal: intro chat.", updated_at: new Date().toISOString(),
      research: { pages: ["https://synthetic-pay.example/"], facts: [{ fact: "Reconciliation APIs for card issuers", source_quote: "reconciliation APIs" }], dropped_facts: 1, fetched_at: null, model: null },
      brief: { hooks: ["your recon APIs for card issuers"], credentials: ["FDE in fintech, 2.5 years"], bridges: ["seen recon pain firsthand"], asks: ["just saying hi"], avoid: ["pitching"], reference_draft: "Hey Mira," } } } });
  });
  await panel.getByLabel("Company website").fill("https://synthetic-pay.example");
  await panel.getByRole("button", { name: "Generate message brief" }).click();
  await expect(panel).toContainText("Reconciliation APIs for card issuers");
  await expect(panel).toContainText("your recon APIs for card issuers");
  await expect(panel).toContainText("1 company claim(s) dropped");
  await expect(panel.getByRole("button", { name: "Regenerate message brief" })).toBeVisible();
  await expect(page.getByText("1 pending · 0 approved")).toBeVisible();
});
