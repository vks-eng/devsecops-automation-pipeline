import { jsx as _jsx } from "react/jsx-runtime";
import { useQueryClient } from "@tanstack/react-query";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, setUnauthorizedHandler, tokenStore } from "./api";
const AuthContext = createContext(null);
export function AuthProvider({ children }) {
    const queryClient = useQueryClient();
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(() => tokenStore.get() !== null);
    const logout = useCallback(() => {
        tokenStore.clear();
        setUser(null);
        queryClient.clear();
    }, [queryClient]);
    useEffect(() => {
        setUnauthorizedHandler(() => setUser(null));
        return () => setUnauthorizedHandler(null);
    }, []);
    useEffect(() => {
        if (!tokenStore.get())
            return;
        api
            .get("/auth/me")
            .then(setUser)
            .catch(() => tokenStore.clear())
            .finally(() => setLoading(false));
    }, []);
    const login = useCallback(async (email, password) => {
        const token = await api.post("/auth/login", { email, password });
        tokenStore.set(token.access_token);
        setUser(await api.get("/auth/me"));
    }, []);
    const value = useMemo(() => ({ user, loading, login, logout }), [user, loading, login, logout]);
    return _jsx(AuthContext.Provider, { value: value, children: children });
}
// eslint-disable-next-line react-refresh/only-export-components -- hook colocated with its provider
export function useAuth() {
    const ctx = useContext(AuthContext);
    if (!ctx)
        throw new Error("useAuth must be used inside <AuthProvider>");
    return ctx;
}
