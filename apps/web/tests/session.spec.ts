import { expect, test, type Page } from "@playwright/test";

export async function register(page: Page) {
  await page.goto("/");
  await page.getByRole("button", { name: "New here? Create an account" }).click();
  await page.getByLabel("Email", { exact: true }).fill(`session-${crypto.randomUUID()}@example.com`);
  await page.getByLabel("Password", { exact: true }).fill("synthetic browser passphrase");
  await page.getByRole("button", { name: "Create account", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Make one good connection." })).toBeVisible();
}

for (const width of [1440, 390]) {
  test(`session capture review and progress at ${width}px`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: 1000 });
    await register(page);
    await page.getByLabel("Session intention").fill("Research one synthetic fintech company");
    await page.getByRole("button", { name: "Start session", exact: false }).click();
    await expect(page.getByRole("button", { name: "Pause session" })).toBeVisible();
    await page.getByRole("button", { name: "Pause session" }).click();
    await page.reload();
    await expect(page.getByRole("button", { name: "Resume session" })).toBeVisible();
    await page.getByRole("button", { name: "Resume session" }).click();
    await page.getByRole("button", { name: "+ Add a quick manual capture" }).click();
    await page.getByLabel("Source URL", { exact: true }).fill("https://example.com/founder");
    await page.getByLabel("Person", { exact: false }).fill("Example Founder");
    await page.getByLabel("Company", { exact: false }).fill("Synthetic Fintech");
    await page.getByRole("combobox", { name: "Action", exact: true }).selectOption("drafted");
    await page.getByRole("button", { name: "Capture for review", exact: true }).click();
    await expect(page.getByText("1 pending · 0 approved")).toBeVisible();
    await page.getByLabel("Source URL", { exact: true }).fill("https://example.com/founder");
    await page.getByRole("textbox", { name: "Person optional until contact confirmed", exact: true }).fill("Example Founder");
    await page.getByRole("button", { name: "Capture for review", exact: true }).click();
    await expect(page.getByRole("alert").filter({ hasText: "Already captured in this session" })).toBeVisible();
    await page.getByRole("button", { name: "Close manual capture" }).click();
    await page.getByRole("button", { name: "Edit capture", exact: true }).click();
    await page.getByLabel("Follow-up reminder", { exact: true }).fill("2030-02-15");
    await page.getByRole("button", { name: "Save capture changes" }).click();
    await expect(page.locator(".capture-facts")).toContainText("2030-02-15 · planned, awaiting approval");
    await page.getByRole("button", { name: "Finish & review" }).click();
    await expect(page.getByRole("button", { name: "Complete session" })).toBeDisabled();
    await page.getByRole("combobox", { name: "Action", exact: true }).selectOption("sent");
    await expect(page.getByRole("button", { name: "Approve record" })).toBeDisabled();
    await page.getByRole("textbox", { name: "Source text", exact: true }).fill("Name: Reviewed Founder\nCompany: Reviewed Labs\nRole: CTO\nBuilds payment APIs.");
    await page.getByRole("button", { name: "Analyze source text", exact: true }).click();
    await expect(page.getByText("Local suggestions · not an AI response", { exact: true })).toBeVisible();
    await expect(page.getByRole("textbox", { name: "Person optional until contact confirmed", exact: true })).toHaveValue("Example Founder");
    await page.getByRole("button", { name: "Use name in form", exact: true }).click();
    await page.getByRole("button", { name: "Use company in form", exact: true }).click();
    await expect(page.getByRole("textbox", { name: "Person optional until contact confirmed", exact: true })).toHaveValue("Reviewed Founder");
    await expect(page.getByRole("combobox", { name: "Action", exact: true })).toHaveValue("sent");
    await page.getByRole("checkbox").check();
    await page.screenshot({ path: testInfo.outputPath(`review-${width}.png`), fullPage: true });
    await page.getByRole("button", { name: "Approve record" }).click();
    await expect(page.getByText("0 pending · 1 approved")).toBeVisible();
    await page.getByRole("button", { name: "Complete session" }).click();
    await expect(page.getByRole("status")).toContainText("Session saved");
    await expect(page.getByRole("heading", { name: "Upcoming follow-ups 1" })).toBeVisible();
    const recap = page.getByRole("region", { name: "Session recap" });
    await expect(recap.getByRole("heading", { name: "You showed up. Here’s the record." })).toBeVisible();
    await expect(recap).toContainText("1 initial send confirmed by you.");
    await recap.getByRole("button", { name: "Find AI observations" }).click();
    await expect(recap).toContainText("Your computed recap is still available.");
    const downloadEvent = page.waitForEvent("download");
    await recap.getByRole("button", { name: "Download session JSON" }).click();
    expect((await downloadEvent).suggestedFilename()).toMatch(/^outreach-session-.*\.json$/);
    await recap.screenshot({ path: testInfo.outputPath(`recap-${width}.png`) });
    await page.reload();
    await page.getByRole("navigation").getByRole("button", { name: "Session history" }).click();
    await page.getByRole("button", { name: /Research one synthetic fintech company/ }).click();
    await expect(page.getByText("Reviewed Founder", { exact: true })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth - innerWidth)).toBeLessThanOrEqual(0);
    await page.screenshot({ path: testInfo.outputPath(`history-${width}.png`), fullPage: true });
    await page.getByRole("button", { name: "Sign out" }).click();
    await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();
  });
}
