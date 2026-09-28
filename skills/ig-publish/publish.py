#!/usr/bin/env python3
"""
publish.py - post or schedule an approved Instagram post through Blotato.

Blotato publishes through Instagram's official Content Publishing API, on an
account you connected to Blotato yourself, rather than a browser pretending to
be you. The
script never decides to post: the skill that calls it has already collected an
explicit "publish".

Instagram will not take a post without media, so every run names exactly one
of --video, --images or --story.

    python3 publish.py caption.txt --video reel.mp4                  # a Reel, now
    python3 publish.py caption.txt --images 1.png 2.png 3.png        # a carousel (2-10)
    python3 publish.py caption.txt --images photo.jpg                # a single photo
    python3 publish.py --story frame.png                             # a story, no caption
    python3 publish.py caption.txt --video reel.mp4 --schedule next_slot
    python3 publish.py caption.txt --video reel.mp4 --schedule 2026-09-22T22:15:00Z
    python3 publish.py caption.txt --video https://.../reel.mp4      # hosted URLs pass through
    python3 publish.py caption.txt --video reel.mp4 --dry-run        # print the payload, no network
    python3 publish.py --check                                       # which account is pinned?

Keys come from ~/.claude/instagram/.env (or --env PATH), falling back to the
process environment:

    BLOTATO_API_KEY=...
    BLOTATO_ACCOUNT_INSTAGRAM=1234

Only `requests` is needed beyond the standard library.
"""

import argparse
import datetime as dt
import json
import mimetypes
import os
import re
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("publish.py needs the requests package: pip install requests")

MCP_URL = "https://mcp.blotato.com/mcp"
DEFAULT_ENV = Path.home() / ".claude" / "instagram" / ".env"
LOG_PATH = Path.home() / ".claude" / "instagram" / "log.md"
CAPTION_LIMIT = 2200
HASHTAG_LIMIT = 5          # Instagram's cap since 18 Dec 2025, same as caption.py
CAROUSEL_MIN, CAROUSEL_MAX = 2, 10
HASHTAG_RE = re.compile(r"(?:^|\s)(#[A-Za-z0-9_]+)")
TERMINAL = ("published", "scheduled", "failed", "completed")
VIDEO_EXT = {".mp4", ".mov", ".m4v", ".webm"}
IMAGE_EXT = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


# ── env ───────────────────────────────────────────────────────────────────────

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


def require(key: str) -> str:
    val = os.environ.get(key, "").strip()
    if not val:
        sys.exit(f"{key} is not set. Put it in {DEFAULT_ENV} or pass --env.")
    return val


# ── Blotato MCP ───────────────────────────────────────────────────────────────

_rpc_id = 0


def _blotato_headers() -> dict:
    return {
        "blotato-api-key": require("BLOTATO_API_KEY"),
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }


def _parse_rpc_body(text: str) -> dict:
    text = text.strip()
    if text.startswith("{"):
        return json.loads(text)
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            payload = line[5:].strip()
            if payload and payload != "[DONE]":
                return json.loads(payload)
    raise RuntimeError(f"Unparseable MCP response: {text[:200]}")


def _rpc(tool: str, arguments: dict, timeout: int = 60):
    global _rpc_id
    _rpc_id += 1
    resp = requests.post(
        MCP_URL,
        headers=_blotato_headers(),
        json={
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": tool, "arguments": arguments},
            "id": _rpc_id,
        },
        timeout=timeout,
    )
    if not resp.ok:
        raise RuntimeError(f"Blotato MCP {tool} HTTP {resp.status_code}: {resp.text[:300]}")
    data = _parse_rpc_body(resp.text)
    if data.get("error"):
        raise RuntimeError(f"Blotato MCP {tool} error: {data['error']}")
    result = data.get("result", {})
    if result.get("isError"):
        raise RuntimeError(f"Blotato MCP {tool} tool error: {result}")
    content = result.get("content") or []
    if content and content[0].get("type") == "text":
        raw = content[0]["text"]
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return raw
    return result


def upload_media(path: Path) -> str:
    size_mb = path.stat().st_size / 1024 / 1024
    print(f"Uploading {path.name} ({size_mb:.1f} MB) to Blotato...")
    res = _rpc("blotato_create_presigned_upload_url", {"filename": path.name}, timeout=60)
    presigned = res.get("presignedUrl") or res.get("uploadUrl")
    public = res.get("publicUrl") or res.get("url")
    if not presigned or not public:
        sys.exit(f"Blotato presigned URL response missing expected fields: {res}")
    # Without a Content-Type the file is served as application/octet-stream,
    # which Instagram's media fetch can refuse. Verified: with it, the public
    # URL serves the real type.
    ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    put = requests.put(presigned, data=path.read_bytes(), headers={"Content-Type": ctype}, timeout=1800)
    if not put.ok:
        sys.exit(f"Upload PUT failed {put.status_code}: {put.text[:200]}")
    print("Upload complete.")
    return public


def _poll_until_terminal(submission_id: str, max_wait: int = 600) -> dict:
    """Reels transcode on Instagram's side, so this can take a few minutes."""
    deadline = time.time() + max_wait
    last = {}
    while time.time() < deadline:
        time.sleep(20)
        try:
            data = _rpc("blotato_get_post_status", {"postSubmissionId": str(submission_id)})
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        last = data
        status = str(data.get("status", "")).lower()
        if status in TERMINAL:
            return data
        print(f"  status: {status or 'in-progress'} ...", flush=True)
    last.setdefault("status", "timeout")
    return last


# ── account check ─────────────────────────────────────────────────────────────

def _accounts() -> list:
    res = _rpc("blotato_list_accounts", {}, timeout=30)
    if isinstance(res, dict):
        for key in ("accounts", "items", "data"):
            if isinstance(res.get(key), list):
                return res[key]
    return res if isinstance(res, list) else []


def verify_account(account_id: str) -> str:
    """Return '@username' for an Instagram account id, or exit.

    A Blotato workspace can hold several Instagram accounts and an id alone
    says nothing about which one it is, so every live run names it.
    """
    for acc in _accounts():
        if str(acc.get("id")) == str(account_id):
            platform = str(acc.get("platform", "")).lower()
            handle = acc.get("username") or acc.get("fullname") or "?"
            if platform != "instagram":
                sys.exit(f"Account {account_id} is {platform or 'unknown'} ({handle}), not Instagram.")
            return f"@{handle}"
    sys.exit(f"Account {account_id} not found in this Blotato workspace.")


# ── helpers ───────────────────────────────────────────────────────────────────

def read_text(source: str) -> str:
    text = sys.stdin.read() if source == "-" else Path(source).read_text()
    return text.strip("\n")


def is_url(s: str) -> bool:
    return s.startswith("http://") or s.startswith("https://")


def check_caption(text: str):
    # Refuse rather than truncate: a caption cut at 2,200 loses its ask and its
    # tags, and the user approved the whole thing.
    problems = []
    if len(text) > CAPTION_LIMIT:
        problems.append(f"caption is {len(text):,} characters, Instagram allows {CAPTION_LIMIT:,}")
    tags = HASHTAG_RE.findall(text)
    if len(tags) > HASHTAG_LIMIT:
        problems.append(f"{len(tags)} hashtags, Instagram's cap is {HASHTAG_LIMIT}")
    if problems:
        sys.exit("Not sent: " + "; ".join(problems) + ". Fix the draft and rerun.")


def check_media(items: list, kind: str):
    for m in items:
        if is_url(m):
            continue
        p = Path(m).expanduser()
        if not p.exists():
            sys.exit(f"Media not found: {m}")
        ext = p.suffix.lower()
        if kind == "reel" and ext not in VIDEO_EXT:
            sys.exit(f"--video wants a video file ({', '.join(sorted(VIDEO_EXT))}), got {p.name}")
        if kind == "carousel" and ext not in IMAGE_EXT | VIDEO_EXT:
            sys.exit(f"Unsupported carousel item: {p.name}")
    if kind == "carousel" and len(items) > 1 and not CAROUSEL_MIN <= len(items) <= CAROUSEL_MAX:
        sys.exit(f"A carousel takes {CAROUSEL_MIN} to {CAROUSEL_MAX} items through the API, got {len(items)}.")


def build_payload(account_id: str, text: str, kind: str, media_urls: list, schedule: str,
                  first_comment: str = "", alt_text: str = "", cover_url: str = "") -> dict:
    args = {"accountId": account_id, "platform": "instagram", "text": text, "mediaUrls": media_urls}
    # Blotato: mediaType is reel|story; a photo or carousel omits it.
    if kind in ("reel", "story"):
        args["mediaType"] = kind
    if first_comment and kind != "story":
        args["firstComment"] = first_comment
    if alt_text and kind in ("photo", "carousel"):
        args["altText"] = alt_text
    if cover_url and kind == "reel":
        args["coverImageUrl"] = cover_url
    if schedule == "next_slot":
        args["useNextFreeSlot"] = True
    elif schedule and schedule != "now":
        # Blotato wants ISO 8601 UTC, e.g. 2026-09-22T22:15:00Z
        try:
            when = dt.datetime.fromisoformat(schedule.replace("Z", "+00:00"))
        except ValueError:
            sys.exit(f"--schedule must be now, next_slot, or an ISO 8601 UTC time, got {schedule!r}")
        if when.tzinfo is None:
            sys.exit(f"--schedule needs a timezone, e.g. {schedule}Z for UTC")
        if when < dt.datetime.now(dt.timezone.utc):
            sys.exit(f"--schedule {schedule} is in the past.")
        args["scheduledTime"] = schedule
    return args


def append_log(kind: str, account: str, text: str, status: str, url: str, schedule: str):
    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        first = text.strip().splitlines()[0][:140] if text.strip() else "(no caption)"
        stamp = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
        with LOG_PATH.open("a") as fh:
            fh.write(f"- {stamp} | ig-publish | {kind} | {account} | {status} | {schedule} | {url or '-'} | {first}\n")
    except OSError as exc:
        print(f"(could not write {LOG_PATH}: {exc})", file=sys.stderr)


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(description="Post or schedule an Instagram post through Blotato.")
    ap.add_argument("caption", nargs="?", help="path to the approved caption, or - for stdin")
    media = ap.add_mutually_exclusive_group()
    media.add_argument("--video", help="a Reel: video file or hosted URL")
    media.add_argument("--images", nargs="+", help="one photo, or 2-10 carousel items in order")
    media.add_argument("--story", help="a story: one image or video file or hosted URL")
    ap.add_argument("--schedule", default="now", help="now (default), next_slot, or ISO 8601 UTC time")
    ap.add_argument("--first-comment", help="path to text posted as the first comment (links go here)")
    ap.add_argument("--alt-text", help="alt text for a photo or carousel")
    ap.add_argument("--cover", help="Reel cover image: file or hosted URL")
    ap.add_argument("--account", help="Blotato account id, overriding BLOTATO_ACCOUNT_INSTAGRAM")
    ap.add_argument("--env", type=Path, default=DEFAULT_ENV, help=f"env file (default {DEFAULT_ENV})")
    ap.add_argument("--dry-run", action="store_true", help="print the payload and exit without any network call")
    ap.add_argument("--check", action="store_true", help="name the pinned Instagram account and exit")
    ap.add_argument("--max-wait", type=int, default=600, help="seconds to poll for a terminal status")
    args = ap.parse_args()

    load_env(args.env)

    if args.check:
        account_id = args.account or require("BLOTATO_ACCOUNT_INSTAGRAM")
        print(f"OK: account {account_id} is Instagram {verify_account(account_id)}.")
        return

    if args.video:
        kind, items = "reel", [args.video]
    elif args.images:
        kind, items = ("carousel" if len(args.images) > 1 else "photo"), args.images
    elif args.story:
        kind, items = "story", [args.story]
    else:
        ap.error("Instagram needs media: give --video, --images or --story")
    check_media(items, "carousel" if kind == "photo" else kind)

    if kind == "story":
        # Stories carry no caption; any text belongs on the frame itself.
        text = read_text(args.caption) if args.caption else ""
        if text:
            print("Note: stories have no caption field, the text is ignored.", file=sys.stderr)
            text = ""
    else:
        if not args.caption:
            ap.error("caption path (or -) is required for a reel, photo or carousel")
        text = read_text(args.caption)
        if not text.strip():
            sys.exit("The caption is empty.")
        check_caption(text)

    first_comment = read_text(args.first_comment) if args.first_comment else ""
    account_id = (args.account or os.environ.get("BLOTATO_ACCOUNT_INSTAGRAM", "").strip()
                  or ("<BLOTATO_ACCOUNT_INSTAGRAM>" if args.dry_run else require("BLOTATO_ACCOUNT_INSTAGRAM")))

    if args.dry_run:
        urls = [m if is_url(m) else f"<upload of {m}>" for m in items]
        cover = (args.cover if args.cover and is_url(args.cover)
                 else f"<upload of {args.cover}>" if args.cover else "")
        print(json.dumps(build_payload(account_id, text, kind, urls, args.schedule,
                                       first_comment, args.alt_text or "", cover),
                         indent=2, ensure_ascii=False))
        return

    handle = verify_account(account_id)
    # Validate the schedule before uploading anything.
    build_payload(account_id, text, kind, [], args.schedule)
    urls = [m if is_url(m) else upload_media(Path(m).expanduser()) for m in items]
    cover = ""
    if args.cover:
        cover = args.cover if is_url(args.cover) else upload_media(Path(args.cover).expanduser())
    payload = build_payload(account_id, text, kind, urls, args.schedule,
                            first_comment, args.alt_text or "", cover)

    print(f"Submitting {kind} to Instagram {handle} (account {account_id}, schedule={args.schedule})...")
    try:
        res = _rpc("blotato_create_post", payload, timeout=90)
    except Exception as exc:
        append_log(kind, handle, text, "failed", "", args.schedule)
        sys.exit(f"FAILED {exc}")

    sub_id = None
    if isinstance(res, dict):
        sub_id = res.get("postSubmissionId") or res.get("submissionId") or res.get("id")
        # Immediate posts may already be terminal: Blotato polls up to 20s itself.
        if str(res.get("status", "")).lower() in TERMINAL:
            final = res
            sub_id = None
    if sub_id:
        print(f"Submission {sub_id}, polling...")
        final = _poll_until_terminal(sub_id, max_wait=args.max_wait)
    elif not isinstance(res, dict) or str(res.get("status", "")).lower() not in TERMINAL:
        append_log(kind, handle, text, "submitted", "", args.schedule)
        print(f"SUBMITTED (no submission id returned): {str(res)[:300]}")
        return

    status = str(final.get("status", "")).lower()
    url = final.get("publicUrl") or final.get("url") or ""
    append_log(kind, handle, text, status, url, args.schedule)

    if status in ("published", "completed"):
        print(f"PUBLISHED {url or '(no public URL returned yet, check Blotato)'}")
    elif status == "scheduled":
        when = final.get("scheduledTime") or payload.get("scheduledTime") or "next free slot"
        print(f"SCHEDULED {when}")
    elif status == "timeout":
        sys.exit(f"STILL PROCESSING after {args.max_wait}s. Submission {sub_id}: check Blotato before retrying.")
    else:
        err = final.get("errorMessage") or final.get("error") or json.dumps(final)[:300]
        sys.exit(f"FAILED {status}: {err}")


if __name__ == "__main__":
    main()
