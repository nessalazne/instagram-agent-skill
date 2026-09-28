#!/usr/bin/env python3
"""
fetch.py - read public Instagram data through Apify, for /ig-audience-insights
and /ig-viral.

Optional. Every skill in the pack works without it by asking you to paste or
collect by hand instead. With a token it fetches for you, using Apify's own
no-login actors, so your Instagram login is never involved.

    python3 fetch.py --check                               # is the token valid?
    python3 fetch.py hashtag TAG --max 20                  # what is traveling under a tag
    python3 fetch.py hashtag TAG --type posts              # feed posts instead of reels
    python3 fetch.py profile HANDLE [HANDLE ...]           # stats + median views per account
    python3 fetch.py swipe TAG --max 30 --out captured.tsv # reels + owner medians, as swipe.py input
    python3 fetch.py swipe TAG --dry-run                   # show the plan and the cost, spend nothing
    python3 fetch.py profile HANDLE --from-file raw.json   # normalise a saved actor dump

`swipe` writes the tab-separated file ../ig-viral/swipe.py reads (account,
followers, median, views, hook), so the ranking step does not change at all.

Keys come from ~/.claude/instagram/.env (or --env PATH), falling back to the
process environment:

    APIFY_TOKEN=apify_api_...

Standard library only. Actor choices adapted from sergebulaev/instagram-skills
(MIT); field shapes verified live 2026-09-28.
"""

import argparse
import json
import os
import re
import statistics
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

DEFAULT_ENV = Path.home() / ".claude" / "instagram" / ".env"
API = "https://api.apify.com/v2"
HASHTAG_ACTOR = "apify~instagram-hashtag-scraper"
PROFILE_ACTOR = "apify~instagram-profile-scraper"
COST_PER_RESULT = 0.0026   # hashtag scraper, free tier, per post
COST_PER_PROFILE = 0.0026  # profile scraper, free tier, per profile
ASK_ABOVE = 1.00           # dollars; the skill asks before any run estimated above this


def load_env(path: Path):
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


def token() -> str:
    val = os.environ.get("APIFY_TOKEN", "").strip()
    if not val:
        sys.exit(
            f"APIFY_TOKEN is not set. Put it in {DEFAULT_ENV}, or paste the posts "
            "or profile stats into Claude instead. The skills work either way."
        )
    return val


# ── Apify ─────────────────────────────────────────────────────────────────────


def call(method: str, path: str, payload=None, timeout: float = 300.0):
    # The token goes in the Authorization header, never the URL, so it stays
    # out of shell history, proxy logs and error traces.
    req = urllib.request.Request(
        f"{API}{path}",
        data=json.dumps(payload).encode() if payload is not None else None,
        method=method,
        headers={"Authorization": f"Bearer {token()}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read() or b"null")
    except urllib.error.HTTPError as e:
        sys.exit(f"Apify HTTP {e.code}: {e.read()[:400].decode(errors='replace')}")
    except urllib.error.URLError as e:
        sys.exit(f"Could not reach Apify: {e.reason}")
    if isinstance(data, dict) and "error" in data:
        sys.exit(f"Apify actor failed: {data['error']}")
    return data


def run_actor(actor: str, payload: dict, max_charge: float) -> list:
    # maxTotalChargeUsd is a hard ceiling Apify enforces on pay-per-event
    # actors, so a bad estimate here can never turn into a surprise bill.
    q = urllib.parse.urlencode({"maxTotalChargeUsd": f"{max_charge:.4f}"})
    data = call("POST", f"/acts/{actor}/run-sync-get-dataset-items?{q}", payload)
    rows = data if isinstance(data, list) else []
    if rows and isinstance(rows[0], dict) and rows[0].get("error"):
        sys.exit(f"Apify actor error: {rows[0].get('errorDescription') or rows[0]['error']}")
    return [r for r in rows if isinstance(r, dict)]


# ── Normalisers ───────────────────────────────────────────────────────────────


def _views(p: dict):
    v = p.get("videoPlayCount") or p.get("videoViewCount")
    return v if isinstance(v, int) and v > 0 else None


def _likes(p: dict):
    # Instagram returns -1 when the owner has hidden the like count.
    v = p.get("likesCount")
    return v if isinstance(v, int) and v >= 0 else None


def normalise_post(p: dict) -> dict:
    if "owner" in p and "views" in p:  # already normalised
        return p
    code = p.get("shortCode") or p.get("shortcode")
    return {
        "url": p.get("url") or (f"https://www.instagram.com/p/{code}/" if code else None),
        "owner": p.get("ownerUsername"),
        "format": {"clips": "reel", "carousel_container": "carousel"}.get(
            p.get("productType"), (p.get("type") or "").lower() or None),
        "views": _views(p),
        "likes": _likes(p),
        "comments": p.get("commentsCount"),
        "seconds": round(p["videoDuration"], 1) if p.get("videoDuration") else None,
        "posted": p.get("timestamp"),
        "caption": p.get("caption") or "",
        "hook": first_line(p.get("caption") or ""),
    }


def normalise_profile(p: dict) -> dict:
    if "median_views" in p:  # already normalised
        return p
    latest = p.get("latestPosts") or []
    views = [v for v in (_views(x) for x in latest) if v]
    likes = [v for v in (_likes(x) for x in latest) if v is not None]
    return {
        "username": p.get("username"),
        "name": p.get("fullName"),
        "followers": p.get("followersCount"),
        "following": p.get("followsCount"),
        "posts": p.get("postsCount"),
        "bio": p.get("biography") or "",
        "category": p.get("businessCategoryName"),
        "verified": bool(p.get("verified")),
        "business": bool(p.get("isBusinessAccount")),
        "private": bool(p.get("private")),
        "links": [u.get("url") for u in (p.get("externalUrls") or []) if isinstance(u, dict)],
        # The baseline swipe.py wants: this account's typical recent reel.
        "median_views": int(statistics.median(views)) if views else None,
        "median_likes": int(statistics.median(likes)) if likes else None,
        "sample": len(latest),
        "reels_in_sample": len(views),
        "url": f"https://www.instagram.com/{p.get('username')}/" if p.get("username") else None,
    }


def first_line(caption: str) -> str:
    # The written hook: the first sentence of the first line that is not a
    # hashtag. Captions often open with a whole paragraph, and the formula
    # classifier in swipe.py is built for a line someone would say.
    for line in caption.splitlines():
        line = " ".join(line.split())
        if not line or line.startswith("#"):
            continue
        m = re.match(r"(.+?[.!?])(?:\s|$)", line)
        if m and len(m.group(1).split()) >= 3:
            line = m.group(1)
        return line[:200]
    return ""


def load_dump(path: str) -> list:
    raw = json.loads(Path(path).expanduser().read_text())
    return raw if isinstance(raw, list) else [raw]


# ── Commands ──────────────────────────────────────────────────────────────────


def cmd_check(_):
    me = call("GET", "/users/me", timeout=30).get("data") or {}
    print(f"OK  Apify user: {me.get('username')}  plan: {(me.get('plan') or {}).get('id', '?')}")


def estimate(posts: int, profiles: int) -> float:
    return posts * COST_PER_RESULT + profiles * COST_PER_PROFILE


def announce(what: str, cost: float):
    flag = "  (over $%.2f: confirm with the user first)" % ASK_ABOVE if cost > ASK_ABOVE else ""
    print(f"{what}, est. max ${cost:.2f}{flag}", file=sys.stderr)


def fetch_hashtag(tag: str, kind: str, n: int) -> list:
    tag = tag.lstrip("#")
    items = run_actor(HASHTAG_ACTOR, {"hashtags": [tag], "resultsLimit": n, "resultsType": kind},
                      estimate(n, 0) * 1.2 + 0.01)
    return [normalise_post(p) for p in items if p.get("shortCode") or p.get("id")]


def fetch_profiles(handles: list) -> list:
    handles = list(dict.fromkeys(h.lstrip("@") for h in handles if h))
    if not handles:
        return []
    items = run_actor(PROFILE_ACTOR, {"usernames": handles},
                      estimate(0, len(handles)) * 1.2 + 0.01)
    return [normalise_profile(p) for p in items if p.get("username")]


def cmd_hashtag(a):
    if a.from_file:
        posts = [normalise_post(p) for p in load_dump(a.from_file)]
    else:
        announce(f"1 run of {HASHTAG_ACTOR}, up to {a.max} {a.type}", estimate(a.max, 0))
        if a.dry_run:
            print(json.dumps({"actor": HASHTAG_ACTOR, "input": {
                "hashtags": [a.tag.lstrip("#")], "resultsLimit": a.max, "resultsType": a.type}}))
            return
        posts = fetch_hashtag(a.tag, a.type, a.max)
    posts.sort(key=lambda p: -((p["views"] or 0) + 10 * ((p["likes"] or 0) + (p["comments"] or 0))))
    print(f"{len(posts)} {a.type} under #{a.tag.lstrip('#')}", file=sys.stderr)
    emit(posts, a.out)


def cmd_profile(a):
    if a.from_file:
        profiles = [normalise_profile(p) for p in load_dump(a.from_file)]
    else:
        announce(f"1 run of {PROFILE_ACTOR}, {len(a.handles)} profile(s)", estimate(0, len(a.handles)))
        if a.dry_run:
            print(json.dumps({"actor": PROFILE_ACTOR, "input": {
                "usernames": [h.lstrip("@") for h in a.handles]}}))
            return
        profiles = fetch_profiles(a.handles)
    missing = {h.lstrip("@").lower() for h in (a.handles or [])} - {
        (p["username"] or "").lower() for p in profiles}
    for h in sorted(missing):
        print(f"  not returned: @{h} (private, renamed or does not exist)", file=sys.stderr)
    emit(profiles, a.out)


def cmd_swipe(a):
    # Two runs: the reels under the tag, then every owner's profile in one
    # batch, whose last 12 posts give the median that swipe.py ranks against.
    announce(f"2 runs: up to {a.max} reels, then up to {a.max} owner profiles",
             estimate(a.max, a.max))
    if a.dry_run:
        print(json.dumps({"actor": HASHTAG_ACTOR, "input": {
            "hashtags": [a.tag.lstrip("#")], "resultsLimit": a.max, "resultsType": "reels"}}))
        print(json.dumps({"actor": PROFILE_ACTOR, "input": {"usernames": ["<owners of the reels above>"]}}))
        return
    reels = [r for r in fetch_hashtag(a.tag, "reels", a.max) if r["views"] and r["hook"] and r["owner"]]
    profiles = {p["username"].lower(): p for p in fetch_profiles([r["owner"] for r in reels])}
    rows, no_median = [], 0
    for r in reels:
        p = profiles.get(r["owner"].lower(), {})
        if not p.get("median_views"):
            no_median += 1
        rows.append([f"@{r['owner']}", p.get("followers") or "", p.get("median_views") or "",
                     r["views"], r["hook"].replace("\t", " ")])
    lines = ["account\tfollowers\tmedian\tviews\thook"] + ["\t".join(map(str, row)) for row in rows]
    print(f"{len(rows)} reels from {len({r[0] for r in rows})} accounts"
          + (f", {no_median} without a median (they fall back to followers)" if no_median else ""),
          file=sys.stderr)
    text = "\n".join(lines) + "\n"
    if a.out:
        Path(a.out).expanduser().write_text(text)
        print(f"wrote {a.out}  ->  python3 ../ig-viral/swipe.py {a.out}", file=sys.stderr)
    else:
        sys.stdout.write(text)


def emit(data, out):
    text = json.dumps(data, indent=2, ensure_ascii=False)
    if out:
        Path(out).expanduser().write_text(text + "\n")
        print(f"wrote {out}", file=sys.stderr)
    else:
        print(text)


def main():
    ap = argparse.ArgumentParser(description="Read public Instagram data through Apify.")
    ap.add_argument("--env", default=str(DEFAULT_ENV))
    ap.add_argument("--check", action="store_true", help="validate APIFY_TOKEN and exit")
    sub = ap.add_subparsers(dest="cmd")

    h = sub.add_parser("hashtag", help="posts or reels traveling under a hashtag")
    h.add_argument("tag")
    h.add_argument("--type", choices=("reels", "posts"), default="reels")
    h.add_argument("--max", type=int, default=20, help="posts to fetch (default 20)")
    h.add_argument("--out")
    h.add_argument("--dry-run", action="store_true", help="print the actor call and cost, send nothing")
    h.add_argument("--from-file", help="normalise a saved actor dump instead of calling Apify")

    p = sub.add_parser("profile", help="public stats and median views for one or more handles")
    p.add_argument("handles", nargs="*")
    p.add_argument("--out")
    p.add_argument("--dry-run", action="store_true", help="print the actor call and cost, send nothing")
    p.add_argument("--from-file", help="normalise a saved actor dump instead of calling Apify")

    s = sub.add_parser("swipe", help="reels under a hashtag + owner medians, as swipe.py input")
    s.add_argument("tag")
    s.add_argument("--max", type=int, default=30, help="reels to fetch (default 30)")
    s.add_argument("--out")
    s.add_argument("--dry-run", action="store_true", help="print the actor calls and cost, send nothing")

    a = ap.parse_args()
    load_env(Path(a.env).expanduser())
    if a.check:
        return cmd_check(a)
    if a.cmd == "hashtag":
        return cmd_hashtag(a)
    if a.cmd == "profile":
        if not a.handles and not a.from_file:
            p.error("give at least one handle, or --from-file")
        return cmd_profile(a)
    if a.cmd == "swipe":
        return cmd_swipe(a)
    ap.print_help()


if __name__ == "__main__":
    main()
