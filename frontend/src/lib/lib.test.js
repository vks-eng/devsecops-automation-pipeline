import { describe, expect, it } from "vitest";
import { ApiError, api, buildUrl, tokenStore } from "./api";
import { formatDuration, formatPercent, percentChange, relativeTime, totalOpen } from "./format";
import { findingsDelta, successRateDelta } from "./metrics";
import { validateRepoUrl } from "./validation";
import { stats, trends } from "../test/fixtures";
import { server, API } from "../test/server";
import { http, HttpResponse } from "msw";
describe("validateRepoUrl (mirrors backend validator)", () => {
    it.each(["https://github.com/acme/api", "https://github.com/a-b/repo.name_1"])("accepts %s", (url) => {
        expect(validateRepoUrl(url)).toBeNull();
    });
    it.each([
        "http://github.com/acme/api",
        "https://github.com/acme/api.git",
        "https://github.com/acme/api/",
        "https://gitlab.com/acme/api",
        "https://github.com/-acme/api",
        "https://github.com/acme/..",
        "https://github.com/acme/api;rm -rf",
    ])("rejects %s", (url) => {
        expect(validateRepoUrl(url)).not.toBeNull();
    });
});
describe("format helpers", () => {
    it("formats durations, percentages and totals", () => {
        expect(formatDuration(65)).toBe("1m 05s");
        expect(formatDuration(9)).toBe("9s");
        expect(formatDuration(null)).toBe("—");
        expect(formatPercent(0.8312)).toBe("83.1%");
        expect(formatPercent(null)).toBe("—");
        expect(totalOpen({ critical: 1, high: 2, medium: 3, low: 4, info: 9 })).toBe(10);
    });
    it("computes percent change with a missing baseline", () => {
        expect(percentChange(12, 10)).toBeCloseTo(20);
        expect(percentChange(0, 0)).toBe(0);
        expect(percentChange(5, 0)).toBeNull();
    });
    it("renders relative times", () => {
        const now = new Date("2026-11-10T12:00:00Z");
        expect(relativeTime("2026-11-10T11:59:30Z", now)).toBe("just now");
        expect(relativeTime("2026-11-10T10:00:00Z", now)).toBe("2h ago");
        expect(relativeTime("2026-11-07T12:00:00Z", now)).toBe("3d ago");
        expect(relativeTime(null, now)).toBe("—");
    });
});
describe("dashboard metrics", () => {
    it("compares open findings with 7 days earlier", () => {
        // fixture: 15 open findings 7 days ago, 11 today
        expect(findingsDelta(trends)).toBeCloseTo(((11 - 15) / 15) * 100);
        expect(findingsDelta(undefined)).toBeNull();
    });
    it("compares pipeline success rate week over week", () => {
        // prior week 50% -> last week 100%
        expect(successRateDelta(stats)).toBeCloseTo(100);
        expect(successRateDelta(undefined)).toBeNull();
    });
});
describe("api client", () => {
    it("builds URLs and drops empty query values", () => {
        expect(buildUrl("/findings", { severity: "high", q: "", project_id: undefined })).toBe(`${API}/findings?severity=high`);
    });
    it("sends the bearer token and surfaces API error details", async () => {
        let auth = null;
        server.use(http.get(`${API}/projects/42`, ({ request }) => {
            auth = request.headers.get("Authorization");
            return HttpResponse.json({ detail: "Project not found" }, { status: 404 });
        }));
        tokenStore.set("abc123");
        await expect(api.get("/projects/42")).rejects.toMatchObject({ status: 404, message: "Project not found" });
        expect(auth).toBe("Bearer abc123");
    });
    it("formats FastAPI validation errors and clears the token on 401", async () => {
        server.use(http.post(`${API}/projects`, () => HttpResponse.json({ detail: [{ loc: ["body", "repo_url"], msg: "invalid URL" }] }, { status: 422 })), http.get(`${API}/auth/me`, () => HttpResponse.json({ detail: "Not authenticated" }, { status: 401 })));
        const err = await api.post("/projects", {}).catch((e) => e);
        expect(err).toBeInstanceOf(ApiError);
        expect(err.message).toBe("repo_url: invalid URL");
        tokenStore.set("expired");
        await expect(api.get("/auth/me")).rejects.toMatchObject({ status: 401 });
        expect(tokenStore.get()).toBeNull();
    });
});
