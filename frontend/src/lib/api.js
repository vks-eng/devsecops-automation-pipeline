// Small typed fetch client for the ShieldOps API.
export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";
const TOKEN_KEY = "shieldops.token";
export class ApiError extends Error {
    status;
    detail;
    constructor(status, message, detail) {
        super(message);
        this.status = status;
        this.detail = detail;
    }
}
export const tokenStore = {
    get() {
        try {
            return sessionStorage.getItem(TOKEN_KEY);
        }
        catch {
            return null;
        }
    },
    set(token) {
        try {
            sessionStorage.setItem(TOKEN_KEY, token);
        }
        catch {
            /* storage unavailable: token stays in memory only */
        }
    },
    clear() {
        try {
            sessionStorage.removeItem(TOKEN_KEY);
        }
        catch {
            /* ignore */
        }
    },
};
let onUnauthorized = null;
export function setUnauthorizedHandler(handler) {
    onUnauthorized = handler;
}
function messageFrom(detail, fallback) {
    if (typeof detail === "string")
        return detail;
    if (Array.isArray(detail) && detail.length > 0) {
        const first = detail[0];
        const field = Array.isArray(first.loc) ? first.loc.slice(1).join(".") : "";
        return field ? `${field}: ${first.msg ?? fallback}` : (first.msg ?? fallback);
    }
    return fallback;
}
export function buildUrl(path, query) {
    const url = new URL(API_BASE.replace(/\/$/, "") + path);
    for (const [key, value] of Object.entries(query ?? {})) {
        if (value !== undefined && value !== null && value !== "")
            url.searchParams.set(key, String(value));
    }
    return url.toString();
}
async function request(method, path, body, query) {
    const headers = { Accept: "application/json" };
    const token = tokenStore.get();
    if (token)
        headers.Authorization = `Bearer ${token}`;
    if (body !== undefined)
        headers["Content-Type"] = "application/json";
    const response = await fetch(buildUrl(path, query), {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (response.status === 401 && token) {
        tokenStore.clear();
        onUnauthorized?.();
    }
    if (!response.ok) {
        let detail = undefined;
        try {
            detail = (await response.json()).detail;
        }
        catch {
            /* non-JSON error body */
        }
        throw new ApiError(response.status, messageFrom(detail, `Request failed (${response.status})`), detail);
    }
    if (response.status === 204)
        return undefined;
    return (await response.json());
}
export const api = {
    get: (path, query) => request("GET", path, undefined, query),
    post: (path, body) => request("POST", path, body),
    patch: (path, body) => request("PATCH", path, body),
    put: (path, body) => request("PUT", path, body),
    delete: (path) => request("DELETE", path),
};
/** Fetch a report with the auth header and hand it to the browser as a file download. */
export async function downloadFile(path, query, filename) {
    const token = tokenStore.get();
    const response = await fetch(buildUrl(path, { ...query, download: true }), {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    if (!response.ok)
        throw new ApiError(response.status, `Download failed (${response.status})`);
    const blob = await response.blob();
    const href = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = href;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(href);
}
