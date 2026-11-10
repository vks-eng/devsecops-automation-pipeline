import { jsx as _jsx, Fragment as _Fragment, jsxs as _jsxs } from "react/jsx-runtime";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { EmptyState, ErrorState, GradeBadge, KpiCard, SeverityBadge, SeverityBar, StatusPill } from "./ui";
describe("ui components", () => {
    it.each([
        ["critical", "Critical"],
        ["high", "High"],
        ["medium", "Medium"],
        ["low", "Low"],
        ["info", "Info"],
    ])("renders a %s severity badge", (severity, label) => {
        render(_jsx(SeverityBadge, { severity: severity, count: 4 }));
        const badge = screen.getByTestId(`severity-${severity}`);
        expect(badge).toHaveTextContent(label);
        expect(badge).toHaveTextContent("4");
        expect(badge.className).toContain(`text-sev-${severity}`);
    });
    it("colours KPI deltas by whether the change is good", () => {
        const { rerender } = render(_jsx(KpiCard, { label: "Open findings", value: 10, delta: -12.5, deltaGoodWhen: "down" }));
        expect(screen.getByTestId("kpi-delta")).toHaveTextContent("12.5%");
        expect(screen.getByTestId("kpi-delta").className).toContain("text-ok");
        rerender(_jsx(KpiCard, { label: "Open findings", value: 10, delta: 8, deltaGoodWhen: "down" }));
        expect(screen.getByTestId("kpi-delta").className).toContain("text-bad");
        rerender(_jsx(KpiCard, { label: "Success", value: "80%", delta: null }));
        expect(screen.queryByTestId("kpi-delta")).toBeNull();
    });
    it("renders status pills, grades and states", () => {
        render(_jsxs(_Fragment, { children: [_jsx(StatusPill, { status: "in_progress" }), _jsx(StatusPill, { status: null }), _jsx(GradeBadge, { grade: "B", score: 84.25 }), _jsx(ErrorState, { error: new Error("boom") }), _jsx(EmptyState, { title: "Nothing here" }), _jsx(SeverityBar, { counts: {} })] }));
        expect(screen.getByText("in progress")).toBeInTheDocument();
        expect(screen.getByText("none")).toBeInTheDocument();
        expect(screen.getByText("84.3")).toBeInTheDocument();
        expect(screen.getByRole("alert")).toHaveTextContent("boom");
        expect(screen.getByText("Nothing here")).toBeInTheDocument();
        expect(screen.getByTitle("No open findings")).toBeInTheDocument();
    });
});
