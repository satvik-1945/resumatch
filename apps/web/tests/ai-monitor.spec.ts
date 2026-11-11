import { expect, test } from "@playwright/test";

test("every AI click is stored and can be inspected and rated in the AI monitor", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "New here? Create an account" }).click();
  await page.getByLabel("Email", { exact: true }).fill(`ai-monitor-${crypto.randomUUID()}@example.com`);
  await page.getByLabel("Password", { exact: true }).fill("synthetic ai monitor passphrase");
  await page.getByRole("button", { name: "Create account", exact: true }).click();
  await page.getByRole("navigation").getByRole("button", { name: "AI monitor" }).click();
  await expect(page.getByText("No AI runs yet.")).toBeVisible();

  await page.getByRole("navigation").getByRole("button", { name: "Workflows" }).click();
  await page.getByRole("button", { name: "Create workflow", exact: true }).click();
  await page.getByRole("button", { name: "Save workflow", exact: true }).click();
  await page.getByRole("button", { name: "Start a run", exact: true }).click();
  await page.getByLabel("Session intention").fill("Monitor experiment");
  await page.getByRole("button", { name: "Start run", exact: false }).click();
  await page.getByRole("button", { name: "+ Add a quick manual capture" }).click();
  await page.getByLabel("Contact URL", { exact: true }).fill("https://example.com/ada");
  await page.getByRole("textbox", { name: "Raw capture text", exact: true }).fill("Name: Ada Example");
  await page.getByRole("button", { name: "Capture for review", exact: true }).click();
  await expect(page.getByText("Captured for review.", { exact: false })).toBeVisible();
  // Tests have no provider key: the real API falls back locally and logs the provider failure.
  await page.getByRole("button", { name: "Process with AI", exact: true }).click();
  await expect(page.getByText(/Local fallback/)).toBeVisible();

  await page.getByRole("navigation").getByRole("button", { name: "AI monitor" }).click();
  const versions = page.locator("table");
  await expect(versions).toContainText("Process with AI");
  const row = page.getByRole("button", { name: /Process with AI\s*Provider error/ });
  await expect(row).toBeVisible();
  await row.click();
  await expect(page.locator(".ai-run-detail .error")).toContainText("LLM_API_KEY");
  await page.getByText("Input sent to the model").click();
  await expect(page.locator(".ai-run-detail")).toContainText("Name: Ada Example");
  await page.getByText(/Prompt version [0-9a-f]{8}/).click();

  await page.getByRole("group", { name: "Rate this AI result" }).getByRole("button", { name: "👎" }).click();
  await page.getByLabel("What should be better?").fill("Never got a model answer");
  await page.getByRole("button", { name: "Save note" }).click();
  await expect(page.getByRole("button", { name: "Save note" })).toBeDisabled();
  await page.getByRole("button", { name: "Refresh" }).click();
  await expect(row).toContainText("👎");
  await expect(versions).toContainText("0 / 1");

  await page.getByRole("group", { name: "Filter by status" }).getByRole("button", { name: "OK" }).click();
  await expect(page.getByText("No runs match.")).toBeVisible();
});
