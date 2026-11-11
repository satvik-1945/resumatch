import { expect, test } from "@playwright/test";

test("bulk approve confirms first and skips reused pasted text and confirmed actions", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: "New here? Create an account" }).click();
  await page.getByLabel("Email", { exact: true }).fill(`bulk-${crypto.randomUUID()}@example.com`);
  await page.getByLabel("Password", { exact: true }).fill("synthetic bulk approve passphrase");
  await page.getByRole("button", { name: "Create account", exact: true }).click();
  await page.getByRole("navigation").getByRole("button", { name: "Workflows" }).click();
  await page.getByRole("button", { name: "Create workflow", exact: true }).click();
  await page.getByRole("button", { name: "Save workflow", exact: true }).click();
  await page.getByRole("button", { name: "Start a run", exact: true }).click();
  await page.getByLabel("Session intention").fill("Bulk approve experiment");
  await page.getByRole("button", { name: "Start run", exact: false }).click();
  await page.getByRole("button", { name: "+ Add a quick manual capture" }).click();
  const records = [
    { url: "https://www.linkedin.com/in/anchal", text: "Anchal Example · 2nd\nPrecision hiring" },
    { url: "https://www.linkedin.com/in/oss", text: "Anchal Example · 2nd\nPrecision hiring" },
    { url: "https://example.com/ada", text: "Name: Ada Example" },
    { url: "https://example.com/grace", text: "Name: Grace Example" },
    { url: "https://example.com/bo", text: "Name: Bo Example", action: "sent" },
  ];
  for (const r of records) {
    await page.getByLabel("Contact URL", { exact: true }).fill(r.url);
    await page.getByRole("textbox", { name: "Raw capture text", exact: true }).fill(r.text);
    if (r.action) await page.getByRole("combobox", { name: "Action", exact: true }).selectOption(r.action);
    await page.getByRole("button", { name: "Capture for review", exact: true }).click();
    await expect(page.getByText("Captured for review.", { exact: false })).toBeVisible();
  }
  await page.getByRole("button", { name: "Finish & review", exact: true }).click();
  await expect(page.getByText("Same pasted text as another record", { exact: false })).toHaveCount(2);

  await page.getByRole("button", { name: "Approve all eligible (2)" }).click();
  await expect(page.getByText("3 stay pending for individual review", { exact: false })).toBeVisible();
  await page.getByRole("button", { name: "Cancel", exact: true }).click();
  await expect(page.getByText("0 approved", { exact: false })).toBeVisible();

  await page.getByRole("button", { name: "Approve all eligible (2)" }).click();
  await page.getByRole("button", { name: "Yes, approve 2" }).click();
  await expect(page.getByRole("status").filter({ hasText: "Approved 2 records." })).toBeVisible();
  await expect(page.getByText("3 pending · 2 approved")).toBeVisible();
  await expect(page.getByRole("button", { name: "Approve all eligible (0)" })).toBeDisabled();
  await expect(page.getByRole("button", { name: "Complete session" })).toBeDisabled();
});
