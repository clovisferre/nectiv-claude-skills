# Setup: DataForSEO credentials

This skill calls the DataForSEO API via a minimal stdlib client bundled at `scripts/_lib.py`. No external CLI, no `pip install`, no `dataforseo` package needed. Just Python 3.9+ and credentials.

## What DataForSEO is

DataForSEO is an SEO data API. We use two of its Labs endpoints:

- `keyword_suggestions` — autocomplete-style related keywords for a seed term
- `ranked_keywords` — keywords a domain ranks for in Google

Pricing is per API row consumed. Check current pricing at https://dataforseo.com/pricing — a typical 100-prompt library validation consumes ~100-200 API rows total (well under a dollar at typical rates).

## Step 1: get credentials

1. Sign up at https://dataforseo.com (free trial is usually available).
2. Open your dashboard. Note your API username (an email) and password (a hex string).

## Step 2: provide credentials to the skill

Two paths. **Environment variables take precedence** if both are set.

### Option A: environment variables (preferred for CI / shared machines)

```bash
export DATAFORSEO_USERNAME="your_username@example.com"
export DATAFORSEO_PASSWORD="your_password_hex"
```

Add to your shell rc file (`~/.zshrc`, `~/.bashrc`) to persist.

### Option B: .env file (preferred for one-time local setup)

Create a file named `.env` somewhere in the directory tree at or above this skill. The script walks up from `scripts/` looking for the first `.env` it can find (stopping at a workspace marker like `.claude/` or `.git/`, or at `$HOME`).

Typical locations:

- `<workspace-root>/.env` (next to `.claude/`, `.git/`) — recommended
- `$HOME/.env` — works as fallback

Contents:

```
DATAFORSEO_USERNAME=your_username@example.com
DATAFORSEO_PASSWORD=your_password_hex
```

Parser tolerates: blank lines, `#`-prefixed comments, surrounding `'` or `"` on values, CRLF/LF line endings, UTF-8 BOM. Does NOT handle multi-line values or shell variable interpolation.

## Step 3: verify setup

```bash
python3 .claude/skills/geo-prompt-library-v2/scripts/check_setup.py
```

Pass `--verbose` to see which credential source resolved.

Exit 0 means credentials work end-to-end. Anything else, read the printed message — it names exactly what is missing.

This script consumes 1 API row per run (effectively negligible cost).

## Failure modes

### Missing credentials (exit 5)
`SetupError`. The printed message names exactly what is missing (no env vars set; no `.env` found via walk-up; `.env` found but username or password empty). Fix per Step 2.

### Bad credentials (exit 4)
DataForSEO returns HTTP 200 with JSON `status_code: 40100`. The script translates this to `APIError("Authentication failed — check DATAFORSEO_USERNAME/PASSWORD")`. Re-verify your credentials in the DataForSEO dashboard.

### Rate limit (exit 4 after one retry)
HTTP 429. The script automatically retries once with a 60-second sleep. If it still fails, you have hit a sustained rate limit; wait a few minutes and re-run.

### No network (exit 4)
`urllib.error.URLError`, DNS failure, or socket timeout. The script wraps these into a clear network error message.

### Malformed `.env`
Lines without `=` are skipped. The parser is forgiving. If credentials still do not resolve, run `check_setup.py --verbose` to confirm the right `.env` is being loaded.

### macOS Python.org SSL certs
The Python.org installer ships without root CAs configured. If `urlopen` raises `CERTIFICATE_VERIFY_FAILED`, run once:

```bash
/Applications/Python\ 3.X/Install\ Certificates.command
```

(Replace `3.X` with your installed version.) Brew Python and system Python on macOS do not have this issue.

## Path overrides

If the skill folder is in a non-standard location and the walk-up search cannot find a workspace marker, the env-vars path always works. There are no `--cli-path` flags in the scripts since the API client is inlined.
