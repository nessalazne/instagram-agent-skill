---
name: ig-publish
description: >-
  Post or schedule an approved Instagram Reel, photo, carousel or story through
  Blotato, which uses Instagram's official publishing API, not browser
  automation.
  Use when the user says "post this", "publish it", "schedule this reel", "send
  it to Instagram", or answers "publish" after /ig-caption, /ig-carousel or
  /ig-reel. Requires media, a humanized caption and two explicit yeses. Never
  runs on its own.
---

# ig-publish

The only skill in this pack that touches Instagram. The others write. This one
sends, and only after the user has said so twice.

It goes through Blotato, which publishes through Instagram's official Content
Publishing API on an account the user connected to Blotato themselves, using
the account pinned in `~/.claude/instagram/.env`. No
browser, no cookies, no password. The account has to be a Business or Creator
account connected in Blotato.

## Before you run anything

1. **The caption must have been through `/ig-human` and `caption.py` in this
   conversation**, and the user must have said "yes" to it. If either is
   missing, run them now, show the result, and ask. Do not publish a caption
   you have not cleaned. `publish.py` refuses more than 2,200 characters or
   more than five hashtags. It does not rewrite them.
2. **Media is required.** Instagram takes no text-only posts. Ask for the file
   or the hosted URL. The skills in this pack write words, so the user supplies
   the video or the images.
3. **Check the keys exist.** `~/.claude/instagram/.env` needs `BLOTATO_API_KEY`
   and `BLOTATO_ACCOUNT_INSTAGRAM`. If it is missing, tell the user exactly
   those two lines and stop. Never ask them to paste the key into the chat.
4. **Name the account.** Run `python3 publish.py --check` and put the
   `@username` it prints in the check below. A Blotato workspace can hold several
   Instagram accounts and the id alone does not say which one this is.
5. **No link in the caption.** Captions are not clickable. Put the link in
   `--first-comment` and say so.

## Which kind

| the user has | flag | notes |
| --- | --- | --- |
| a video for Reels | `--video reel.mp4` | optional `--cover cover.jpg` |
| one image | `--images photo.jpg` | a feed photo, optional `--alt-text` |
| 2 to 10 images or clips | `--images 1.png 2.png ...` | a carousel, in the order given |
| a story frame | `--story frame.png` | no caption field, one frame per run |

For a carousel, list the files one by one in slide order. Do not use a glob,
because `s10.png` sorts before `s2.png`. Every video item in a carousel must be
at least 3 seconds long. Hosted `https://` URLs pass straight through. Local
files are uploaded to Blotato first.

## The second yes

Show the user, in one block:

```
PUBLISH CHECK
account:   Instagram @yourhandle (from publish.py --check)
kind:      reel  |  photo  |  carousel (7 slides)  |  story
media:     reel.mp4 (48 MB)   cover: cover.jpg
when:      now  |  next free slot  |  2026-09-22 08:15 local (12:15 UTC)
caption:   389 of 2,200 characters, 3 hashtags, caption.py READY
first comment:  the template link

<the final caption, exactly as it will go out>

Reply "publish" to send it, or tell me what to change.
```

Wait for the word "publish". "yes", "ok" and "looks good" are not enough for
something that goes out under their name. Ask once more if it is ambiguous.

## Scheduling

Blotato wants ISO 8601 UTC with the `Z`. Convert from the user's local time,
say both, and put the UTC one in the command. The script refuses a time in the
past or one with no timezone.

- `--schedule now` (default)
- `--schedule next_slot` uses Blotato's next free slot for that account
- `--schedule 2026-09-22T12:15:00Z` for an exact time

## Run it

Write the approved caption to a temp file exactly as shown, then one of:

```bash
python3 publish.py caption.txt --video reel.mp4
python3 publish.py caption.txt --video reel.mp4 --cover cover.jpg --schedule next_slot
python3 publish.py caption.txt --images 1.png 2.png 3.png 4.png --alt-text "..."
python3 publish.py caption.txt --images photo.jpg --first-comment link.txt
python3 publish.py --story frame.png
python3 publish.py caption.txt --video reel.mp4 --dry-run   # the payload, nothing sent
```

The script names the account, uploads any local files, submits, then polls
Blotato every 20 seconds until the post is `published`, `scheduled` or
`failed`, for up to ten minutes. Reels can take a few minutes because Instagram
transcodes them. It prints one of:

```
PUBLISHED https://www.instagram.com/reel/...
SCHEDULED 2026-09-22T12:15:00Z
FAILED <reason>
STILL PROCESSING after 600s. Submission <id>: check Blotato before retrying.
```

Do not end your turn while it is still polling. Relay the final line with the
URL. If it says FAILED, quote the reason and do not retry the same command,
because the reason tells you what to fix. If it says STILL PROCESSING, do not
resubmit, or the user gets the post twice.

## After

The script appends a line to `~/.claude/instagram/log.md` with the date, kind,
account, status, schedule, URL and the caption's first line, so `/ig-audit` can
find it later.

## Never

- Never run the script without the word "publish" from the user in this
  conversation.
- Never use `--account` for an account the user did not name in this
  conversation, and show its `@username` from `--check` first. The default is
  the account in `.env`.
- Never publish to any platform other than Instagram from this skill, even if
  the workspace has other accounts.
- Never change the caption or the media between the PUBLISH CHECK and the
  command. What they approved is what goes out.
- Never automate comments, follows, likes or DMs through this. It publishes the
  user's own posts, and nothing else.
