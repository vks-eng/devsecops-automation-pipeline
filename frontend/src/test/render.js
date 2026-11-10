import { jsx as _jsx } from "react/jsx-runtime";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import App from "../App";
import { tokenStore } from "../lib/api";
import { AuthProvider } from "../lib/auth";
export function renderApp(path = "/", { authenticated = true } = {}) {
    if (authenticated)
        tokenStore.set("test-token");
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    return render(_jsx(QueryClientProvider, { client: client, children: _jsx(MemoryRouter, { initialEntries: [path], children: _jsx(AuthProvider, { children: _jsx(App, {}) }) }) }));
}
export function renderWithClient(ui) {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    return render(_jsx(QueryClientProvider, { client: client, children: _jsx(MemoryRouter, { children: ui }) }));
}
