// Mirrors the backend validator (app/core/validators.py) for instant feedback.
export const GITHUB_REPO_RE = /^https:\/\/github\.com\/[A-Za-z0-9](?:[A-Za-z0-9]|-(?=[A-Za-z0-9])){0,38}\/[A-Za-z0-9._-]{1,100}$/;

export function validateRepoUrl(url: string): string | null {
  if (!GITHUB_REPO_RE.test(url)) return "Must match https://github.com/<owner>/<repo>";
  const repo = url.split("/").pop() ?? "";
  if (repo === "." || repo === ".." || repo.toLowerCase().endsWith(".git")) return "Omit the .git suffix";
  return null;
}
