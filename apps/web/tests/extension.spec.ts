import { chromium, expect, test } from "@playwright/test";
import path from "node:path";

test("real extension captures selected browser context, reviews once, and revokes access", async ({}, testInfo) => {
  const extensionPath = path.resolve(process.cwd(), "../extension");
  const context = await chromium.launchPersistentContext(testInfo.outputPath("chromium-profile"), {
    channel: "chromium", headless: true, viewport: null,
    args: [`--disable-extensions-except=${extensionPath}`, `--load-extension=${extensionPath}`],
  });
  try {
    let worker = context.serviceWorkers()[0];
    if (!worker) worker = await context.waitForEvent("serviceworker");
    const id = new URL(worker.url()).host;
    const app = await context.newPage();
    await app.goto("http://localhost:3001");
    await app.getByRole("button", { name: "New here? Create an account" }).click();
    await app.getByLabel("Email", { exact: true }).fill(`extension-${crypto.randomUUID()}@example.com`);
    await app.getByLabel("Password", { exact: true }).fill("synthetic extension passphrase");
    await app.getByRole("button", { name: "Create account", exact: true }).click();
    await app.getByRole("navigation").getByRole("button", { name: "Workflows" }).click();
    await app.getByRole("button", { name: "Create workflow", exact: true }).click();
    await app.getByRole("button", { name: "Save workflow", exact: true }).click();
    await app.getByRole("button", { name: "Start a run", exact: true }).click();
    await app.getByLabel("Session intention").fill("Browser-assisted research");
    await app.getByRole("button", { name: /Start run/ }).click();
    await expect(app.getByRole("button", { name: "Pause session" })).toBeVisible();
    await app.getByRole("navigation").getByRole("button", { name: "Browser capture" }).click();
    await app.getByLabel("Extension ID", { exact: true }).fill(id);
    await app.getByRole("button", { name: "Generate pairing token" }).click();
    const token = await app.getByLabel("Pairing token — shown once").inputValue();
    let popup = await context.newPage();
    await popup.goto(`chrome-extension://${id}/popup.html`);
    // Action popup has a stable intrinsic width even when pairing/session content is short.
    expect(await popup.evaluate(() => getComputedStyle(document.documentElement).minWidth)).toBe("420px");
    expect(await popup.evaluate(() => getComputedStyle(document.body).width)).toBe("420px");
    await popup.screenshot({ path: testInfo.outputPath("unpaired-popup.png"), fullPage: true });
    await popup.getByLabel("API address").selectOption("http://127.0.0.1:8001");
    await popup.getByLabel("Pairing token", { exact: true }).fill(token);
    await popup.getByRole("button", { name: "Save pairing" }).click();
    await expect(popup.getByRole("status")).toContainText("Pairing saved");
    // The real extension reads a controlled local source, not a LinkedIn fixture pretending
    // to establish inbox access. API host permission covers this test source origin.
    await context.route("http://127.0.0.1:8001/capture-fixture", route => route.fulfill({
      contentType: "text/html", body: "<title>Synthetic startup news</title><h1>Example fintech</h1><p id='source'>Example company launched a payment product.</p><p>Other private text not selected.</p>",
    }));
    const source = await context.newPage();
    await source.goto("http://127.0.0.1:8001/capture-fixture");
    await source.evaluate(() => {
      const range = document.createRange(); range.selectNodeContents(document.querySelector("#source")!);
      getSelection()!.removeAllRanges(); getSelection()!.addRange(range);
    });
    await source.bringToFront();
    await popup.reload();
    await expect(popup.getByLabel("Contact URL", { exact: true })).toHaveValue("http://127.0.0.1:8001/capture-fixture");
    await expect(popup.getByLabel("Raw capture text")).toHaveValue("Example company launched a payment product.");
    // A typed draft from another run is kept but blocked; an untouched stale one is replaced.
    type Storage = { get(key: string): Promise<{ draft: { details: object } }>; set(items: object): Promise<void> };
    const seed = (notes: string) => popup.evaluate(async notes => {
      const storage = (globalThis as unknown as { chrome: { storage: { local: Storage } } }).chrome.storage.local;
      const { draft } = await storage.get("draft");
      await storage.set({ draft: { ...draft, sessionId: crypto.randomUUID(), sessionLabel: "Contact outreach / 2026-11-10",
        details: { ...draft.details, source_url: "https://example.com/someone-else", notes } } });
    }, notes);
    await seed("Typed notes about someone else");
    await popup.reload();
    await expect(popup.getByRole("status")).toContainText("Unsent draft from “Contact outreach / 2026-11-10” for https://example.com/someone-else");
    await expect(popup.getByRole("button", { name: "Capture for review", exact: true })).toBeDisabled();
    await expect(popup.getByLabel("Contact URL", { exact: true })).toHaveValue("https://example.com/someone-else");
    await seed("");
    await popup.reload();
    await expect(popup.getByLabel("Contact URL", { exact: true })).toHaveValue("http://127.0.0.1:8001/capture-fixture");
    await expect(popup.getByLabel("Raw capture text")).toHaveValue("Example company launched a payment product.");
    await expect(popup.getByRole("button", { name: "Capture for review", exact: true })).toBeEnabled();
    const guard = await popup.evaluate(async () => {
      // Exercise the packaged capture dispatch with synthetic browser metadata. No LinkedIn
      // page is requested, injected, or scraped by this test.
      const captureModule = await import(location.origin + "/capture.js");
      let reads = 0;
      const result = await captureModule.contextForTab({ id: 1, url: "https://www.linkedin.com/in/example/" }, async () => { reads++; throw new Error("Must not read LinkedIn"); });
      return { reads, result };
    });
    expect(guard.reads).toBe(0);
    expect(guard.result).toEqual({ source_url: "https://www.linkedin.com/in/example/", source_title: "", quote: "" });
    const [movable] = await Promise.all([
      context.waitForEvent("page"),
      popup.getByRole("button", { name: "Open movable window" }).click(),
    ]);
    popup = movable;
    await popup.waitForLoadState();
    await expect(popup.locator("body")).toHaveClass("floating");
    await popup.getByRole("button", { name: "Collapse", exact: true }).click();
    await expect(popup.locator("body")).toHaveClass("floating collapsed");
    await expect(popup.getByRole("alert")).toBeHidden();
    await popup.getByRole("button", { name: "Expand", exact: true }).click();
    await expect(popup.getByRole("button", { name: "Capture for review", exact: true })).toBeVisible();
    await expect(popup.getByRole("alert")).toBeHidden();
    await popup.getByText("Known details & activity (optional)", { exact: true }).click();
    await popup.getByLabel("Company", { exact: true }).fill("Example fintech");
    await popup.getByLabel("Follow-up reminder", { exact: true }).fill("2030-01-10");
    await popup.getByRole("checkbox", { name: "Hide window after a successful capture" }).check();
    await popup.screenshot({ path: testInfo.outputPath("movable-capture.png"), fullPage: true });
    await popup.getByRole("button", { name: "Capture for review", exact: true }).click();
    await expect(popup.getByRole("status")).toContainText("Captured for review");
    await expect.poll(() => popup.evaluate(async () => (await Reflect.get(globalThis, "chrome").windows.getCurrent()).state)).toBe("minimized");
    await popup.evaluate(async () => {
      const windows = Reflect.get(globalThis, "chrome").windows;
      await windows.update((await windows.getCurrent()).id, { state: "normal" });
    });
    await popup.getByRole("button", { name: "Refresh session" }).click();
    await popup.getByRole("button", { name: "Capture for review", exact: true }).click();
    await expect(popup.getByRole("alert")).toContainText("Already captured in this session");
    await app.bringToFront();
    await app.getByRole("navigation").getByRole("button", { name: "Today" }).click();
    await expect(app.getByText("1 pending · 0 approved")).toBeVisible({ timeout: 10000 });
    await expect(app.locator(".capture-facts")).toContainText("2030-01-10 · planned, awaiting approval");
    await app.getByRole("button", { name: "Finish & review" }).click();
    await expect(app.getByRole("textbox", { name: "Company", exact: true })).toHaveValue("Example fintech");
    await app.getByRole("button", { name: "Approve record" }).click();
    await app.getByRole("button", { name: "Complete session" }).click();
    await expect(app.getByRole("status")).toContainText("1 approved record");
    await expect(app.getByRole("heading", { name: "Upcoming follow-ups 1" })).toBeVisible();
    await app.getByRole("navigation").getByRole("button", { name: "Browser capture" }).click();
    await app.getByRole("button", { name: "Revoke", exact: true }).click();
    await popup.getByRole("button", { name: "Refresh session" }).click();
    await expect(popup.getByRole("alert")).toContainText("expired or revoked");
  } finally { await context.close(); }
});
