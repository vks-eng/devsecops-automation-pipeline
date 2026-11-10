// Captures README screenshots from a RUNNING local stack (API on :8000 with seed data,
// `vite preview` on :4173). Uses the installed Microsoft Edge, so no browser download is needed:
//   node scripts/screenshots.mjs
// Env: APP_URL (default http://localhost:4173), API_URL (default http://localhost:8000),
//      SHOT_EMAIL / SHOT_PASSWORD (default: local-only seed admin), BROWSER_CHANNEL (default msedge).
import { mkdirSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { chromium } from "@playwright/test";

const here = dirname(fileURLToPath(import.meta.url));
const out = resolve(here, "../../docs/screenshots");
mkdirSync(out, { recursive: true });

const APP = process.env.APP_URL ?? "http://localhost:4173";
const API = process.env.API_URL ?? "http://localhost:8000";
const EMAIL = process.env.SHOT_EMAIL ?? "admin@example.com";
const PASSWORD = process.env.SHOT_PASSWORD ?? "ShieldOpsAdmin2026";

const browser = await chromium.launch({ channel: process.env.BROWSER_CHANNEL ?? "msedge" });
const context = await browser.newContext({ viewport: { width: 1440, height: 900 }, colorScheme: "dark" });
const page = await context.newPage();

async function shot(name, path, waitFor) {
  if (path) await page.goto(APP + path, { waitUntil: "networkidle" });
  if (waitFor) await page.getByText(waitFor, { exact: false }).first().waitFor({ timeout: 15_000 });
  await page.waitForTimeout(700); // let charts finish layout
  await page.screenshot({ path: resolve(out, name) });
  console.log("captured", name);
}

await page.goto(APP + "/login", { waitUntil: "networkidle" });
await shot("login.png", null, "Sign in");
await page.getByLabel("Email").fill(EMAIL);
await page.getByLabel("Password").fill(PASSWORD);
await page.getByRole("button", { name: "Sign in" }).click();
await page.getByRole("heading", { name: "Security overview", exact: true }).waitFor();

await shot("dashboard.png", "/", "Top rules");
await shot("projects.png", "/projects", "Payments API");
await page.goto(APP + "/vulnerabilities", { waitUntil: "networkidle" });
await page.locator("tbody tr").first().click();
await shot("vulnerabilities.png", null, "Remediation");
await shot("container-scans.png", "/containers", "details");
await shot("pipelines.png", "/pipelines", "Daily results");
await shot("reports.png", "/reports", "Project reports");

await page.goto(API + "/api/v1/docs", { waitUntil: "networkidle" });
await page.getByText("ShieldOps").first().waitFor();
await shot("swagger.png", null, null);

await browser.close();
