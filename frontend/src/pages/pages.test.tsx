import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { renderApp } from "../test/render";
import { API, server } from "../test/server";

describe("authentication", () => {
  it("redirects unauthenticated users to the login page", async () => {
    renderApp("/vulnerabilities", { authenticated: false });
    expect(await screen.findByRole("heading", { name: "Sign in" })).toBeInTheDocument();
  });

  it("shows an error for bad credentials and signs in with good ones", async () => {
    const user = userEvent.setup();
    renderApp("/", { authenticated: false });
    await user.type(await screen.findByLabelText("Email"), "admin@example.com");
    await user.type(screen.getByLabelText("Password"), "wrong");
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid email or password");

    await user.clear(screen.getByLabelText("Password"));
    await user.type(screen.getByLabelText("Password"), "CorrectHorse1");
    await user.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("heading", { name: "Security overview" })).toBeInTheDocument();
    expect(sessionStorage.getItem("shieldops.token")).toBe("test-token");
  });
});

describe("dashboard", () => {
  it("renders KPIs, deltas, charts, top rules and activity", async () => {
    renderApp("/");
    expect(await screen.findByRole("heading", { name: "Security overview" })).toBeInTheDocument();
    expect(screen.getAllByText("Open findings").length).toBeGreaterThan(0);
    expect(screen.getByText("11")).toBeInTheDocument(); // 2+3+5+1 open
    expect(screen.getByText("80.0%")).toBeInTheDocument();
    await waitFor(() => expect(screen.getAllByTestId("kpi-delta").length).toBe(2));
    expect(screen.getByTestId("trend-chart")).toBeInTheDocument();
    expect(await screen.findByTestId("top-rules")).toHaveTextContent("CVE-2023-45853");
    expect(screen.getAllByText("Payments API").length).toBeGreaterThan(0);
    expect(screen.getAllByTestId("severity-critical")[0]).toHaveTextContent("2");
    expect(await screen.findByLabelText("3 unread")).toBeInTheDocument();
  });

  it("shows an error state when the API fails", async () => {
    server.use(http.get(`${API}/dashboard/summary`, () => HttpResponse.json({ detail: "boom" }, { status: 500 })));
    renderApp("/");
    expect(await screen.findByRole("alert")).toHaveTextContent("boom");
  });
});

describe("vulnerabilities", () => {
  it("filters by severity and expands remediation guidance", async () => {
    const user = userEvent.setup();
    renderApp("/vulnerabilities");
    expect(await screen.findByText("zlib: integer overflow")).toBeInTheDocument();
    expect(screen.getByText("GHSA-j8r2-6x86-q33q")).toBeInTheDocument();

    const filter = screen.getByRole("group", { name: "Severity filter" });
    await user.click(within(filter).getByRole("button", { name: "critical" }));
    await waitFor(() => expect(screen.queryByText("GHSA-j8r2-6x86-q33q")).not.toBeInTheDocument());

    await user.click(screen.getByText("zlib: integer overflow"));
    expect(screen.getByText(/No fixed version of zlib1g/)).toBeInTheDocument();
  });

  it("shows an empty state", async () => {
    server.use(http.get(`${API}/findings`, () => HttpResponse.json({ items: [], total: 0, limit: 25, offset: 0 })));
    renderApp("/vulnerabilities");
    expect(await screen.findByText("No open findings match these filters")).toBeInTheDocument();
  });
});

describe("projects", () => {
  it("validates the repository URL before submitting", async () => {
    const user = userEvent.setup();
    let posted = false;
    server.use(
      http.post(`${API}/projects`, () => {
        posted = true;
        return HttpResponse.json({}, { status: 201 });
      }),
    );
    renderApp("/projects");
    await user.click(await screen.findByRole("button", { name: "New project" }));
    await user.type(screen.getByLabelText("Name"), "New service");
    await user.type(screen.getByLabelText("GitHub repository URL"), "https://github.com/acme/new.git");
    await user.click(screen.getByRole("button", { name: "Register project" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Omit the .git suffix");
    expect(posted).toBe(false);
  });

  it("triggers a scan from the project page", async () => {
    const user = userEvent.setup();
    renderApp("/projects/1");
    expect(await screen.findByRole("heading", { name: "Payments API" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Start scan" }));
    expect(await screen.findByText("Scan #99 completed")).toBeInTheDocument();
  });
});
