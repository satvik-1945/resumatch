import { expect, test } from "@playwright/test";

test("review counts on cards, filters, and manual entry with AI from consolidated records", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "New here? Create an account" }).click();
  await page.getByLabel("Email", { exact: true }).fill(`filters-${crypto.randomUUID()}@example.com`);
  await page.getByLabel("Password", { exact: true }).fill("synthetic filters passphrase");
  await page.getByRole("button", { name: "Create account", exact: true }).click();
  await page.getByRole("navigation").getByRole("button", { name: "Workflows" }).click();
  await page.getByRole("button", { name: "Create workflow", exact: true }).click();
  await page.getByRole("button", { name: "Save workflow", exact: true }).click();

  await page.getByRole("button", { name: "Consolidated records", exact: true }).click();
  await page.getByRole("button", { name: "+ Add a record manually" }).click();
  await page.getByRole("button", { name: "Start a run for manual entries" }).click();
  const entry = page.locator(".workflow-entry");
  for (const name of ["Ada", "Grace"]) {
    await entry.getByLabel("Contact URL", { exact: true }).fill(`https://example.com/${name.toLowerCase()}`);
    await entry.getByRole("textbox", { name: "Raw capture text", exact: true }).fill(`Name: ${name} Example\nCompany: Synthetic Labs`);
    await entry.getByRole("button", { name: "Capture for review", exact: true }).click();
    await expect(entry.getByText("Captured for review.", { exact: false })).toBeVisible();
  }
  // One step from an unsaved form: browser validation applies, then the new record is processed.
  await entry.getByLabel("Contact URL", { exact: true }).fill("");
  await entry.getByRole("textbox", { name: "Raw capture text", exact: true }).fill("Name: Linus Example");
  await entry.getByRole("button", { name: "Capture & process with AI" }).click();
  await expect(entry.getByText("Captured for review.", { exact: false })).toHaveCount(0);
  await entry.getByLabel("Contact URL", { exact: true }).fill("https://example.com/linus");
  await entry.getByRole("button", { name: "Capture & process with AI" }).click();
  await expect(entry.getByText(/Captured for review\. AI unavailable: AI needs LLM_API_KEY.*Labeled lines filled 1 field\./)).toBeVisible();
  await expect(page.getByRole("table")).toContainText("Linus Example");
  // No provider key in tests: the pass stops on the provider error and keeps the local fill.
  await entry.getByRole("button", { name: "Process with AI", exact: true }).click();
  await expect(entry.getByRole("alert")).toContainText("AI needs LLM_API_KEY");
  await expect(page.getByRole("table")).toContainText("Ada Example");

  const filters = page.getByRole("group", { name: "Filter contacts" });
  await expect(filters.getByRole("button", { name: "All 3" })).toBeVisible();
  await expect(filters.getByRole("button", { name: "Waiting for review 3" })).toBeVisible();
  await filters.getByRole("button", { name: "Approved 0" }).click();
  await expect(page.getByText("No contacts match this filter.")).toBeVisible();
  const card = page.locator(".workflow-card");
  await expect(card).toContainText("3Total records");
  await expect(card).toContainText("3Waiting for review");
  await expect(card).toContainText("0Approved");

  await page.getByRole("button", { name: "Dated runs", exact: true }).click();
  const runFilters = page.getByRole("group", { name: "Filter runs" });
  await runFilters.getByRole("button", { name: "Waiting for review 1" }).click();
  await expect(page.getByRole("button", { name: /3 records.*3 waiting for review · 0 approved/ })).toBeVisible();

  await page.getByRole("navigation").getByRole("button", { name: "Today" }).click();
  const recordFilters = page.getByRole("group", { name: "Filter records" });
  await expect(recordFilters.getByRole("button", { name: "Waiting for review 3" })).toBeVisible();
  await recordFilters.getByRole("button", { name: "Approved 0" }).click();
  await expect(page.getByText("No records match this filter.")).toBeVisible();
});
