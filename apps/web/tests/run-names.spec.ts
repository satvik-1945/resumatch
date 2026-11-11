import { expect, test } from "@playwright/test";

test("repeat same-day runs get incrementing defaults or the name entered at start", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "New here? Create an account" }).click();
  await page.getByLabel("Email", { exact: true }).fill(`names-${crypto.randomUUID()}@example.com`);
  await page.getByLabel("Password", { exact: true }).fill("synthetic run names passphrase");
  await page.getByRole("button", { name: "Create account", exact: true }).click();
  await page.getByRole("navigation").getByRole("button", { name: "Workflows" }).click();
  await page.getByRole("button", { name: "Create workflow", exact: true }).click();
  await page.getByRole("button", { name: "Save workflow", exact: true }).click();
  await page.getByRole("button", { name: "Start a run", exact: true }).click();
  const startCard = page.locator(".start-card");
  const day = await startCard.getByLabel("Run name", { exact: true }).getAttribute("placeholder");
  expect(day).toMatch(/^\d{4}-\d{2}-\d{2}$/);

  for (let i = 0; i < 4; i++) {
    const expectedDefault = i === 0 ? day! : `${day} (${i})`;
    const chosen = i === 2 ? "Evening follow-ups" : expectedDefault;
    await expect(startCard.getByLabel("Run name", { exact: true })).toHaveAttribute("placeholder", expectedDefault);
    await startCard.getByLabel("Run name", { exact: true }).fill(i === 2 ? chosen : "");
    await startCard.getByLabel("Session intention").fill(`Naming experiment ${i + 1}`);
    await startCard.getByRole("button", { name: /Start run/ }).click();
    await expect(page.locator(".rename-run").getByLabel("Run name", { exact: true })).toHaveValue(chosen);
    await page.getByRole("button", { name: "Finish & review", exact: true }).click();
    await page.getByRole("button", { name: "Complete session", exact: true }).click();
    await expect(startCard.getByRole("button", { name: /Start run/ })).toBeVisible();
  }
  await page.getByRole("navigation").getByRole("button", { name: "Run history" }).click();
  await expect(page.locator(".history-row")).toHaveCount(4);
  await expect(page.locator(".history-row").filter({ hasText: `${day} (1)` })).toHaveCount(1);
  await expect(page.locator(".history-row").filter({ hasText: "Evening follow-ups" })).toHaveCount(1);
  await expect(page.locator(".history-row").filter({ hasText: `${day} (3)` })).toHaveCount(1);
});
