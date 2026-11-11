import { expect, test } from "@playwright/test";

test("a rejected AI answer flags one record and the pass continues; a provider failure stops it", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "New here? Create an account" }).click();
  await page.getByLabel("Email", { exact: true }).fill(`ai-pass-${crypto.randomUUID()}@example.com`);
  await page.getByLabel("Password", { exact: true }).fill("synthetic ai pass passphrase");
  await page.getByRole("button", { name: "Create account", exact: true }).click();
  await page.getByRole("navigation").getByRole("button", { name: "Workflows" }).click();
  await page.getByRole("button", { name: "Create workflow", exact: true }).click();
  await page.getByRole("button", { name: "Save workflow", exact: true }).click();
  await page.getByRole("button", { name: "Start a run", exact: true }).click();
  await page.getByLabel("Session intention").fill("AI pass experiment");
  await page.getByRole("button", { name: "Start run", exact: false }).click();
  await page.getByRole("button", { name: "+ Add a quick manual capture" }).click();
  for (const name of ["Ada", "Grace", "Linus"]) {
    await page.getByLabel("Contact URL", { exact: true }).fill(`https://example.com/${name.toLowerCase()}`);
    await page.getByRole("textbox", { name: "Raw capture text", exact: true }).fill(`Name: ${name} Example`);
    await page.getByRole("button", { name: "Capture for review", exact: true }).click();
    await expect(page.getByText("Captured for review.", { exact: false })).toBeVisible();
  }

  // Synthetic provider outcomes: rejected output, partially grounded answer, then provider failure.
  const outcomes = [
    { method: "local", failure: "output", rejected_fields: [], warning: "AI output contains unknown/system fields" },
    { method: "llm", failure: null, rejected_fields: ["industry"], warning: "Skipped AI values not found in the raw text: industry" },
    { method: "local", failure: "provider", rejected_fields: [], warning: "Provider quota/rate limit reached. Check billing or retry." },
  ];
  let calls = 0;
  await page.route("**/captures/*/process-ai", async route => {
    const outcome = outcomes[calls++];
    await route.fulfill({ json: { cached: false, capture: { analysis: {
      schema_version: 2, filled_fields: [], preserved_fields: [], fields: {}, ...outcome,
    } } } });
  });
  await page.getByRole("button", { name: "Process with AI", exact: true }).click();
  await expect(page.getByRole("alert").filter({ hasText: "Provider quota/rate limit reached" })).toBeVisible();
  await expect(page.getByRole("status").filter({ hasText: "3 of 3 records processed · 2 had AI values skipped" })).toBeVisible();
  expect(calls).toBe(3);
});
