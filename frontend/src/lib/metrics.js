import { percentChange, totalOpen } from "./format";
/** Change of open findings: latest day versus the same day one week earlier. */
export function findingsDelta(trends) {
    const series = trends?.vulnerabilities ?? [];
    if (series.length < 8)
        return null;
    const last = totalOpen(series[series.length - 1]);
    const prev = totalOpen(series[series.length - 8]);
    return percentChange(last, prev);
}
/** Success-rate change: last 7 days versus the 7 days before. */
export function successRateDelta(stats) {
    const daily = stats?.daily ?? [];
    if (daily.length === 0)
        return null;
    const rate = (rows) => {
        const ok = rows.reduce((s, r) => s + r.success, 0);
        const bad = rows.reduce((s, r) => s + r.failure, 0);
        return ok + bad === 0 ? null : ok / (ok + bad);
    };
    const current = rate(daily.slice(-7));
    const previous = rate(daily.slice(-14, -7));
    if (current === null || previous === null)
        return null;
    return percentChange(current, previous);
}
