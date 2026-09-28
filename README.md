# The Instagram agent skill (Ness edition)

Sixteen Claude skills that run an Instagram account. Fifteen of them write or
read, and they need no signup, no API key, nothing to connect. The sixteenth
posts, through Blotato, and only after you have said "publish". One of them
can also fetch public Instagram data through Apify if you give it a key,
instead of you collecting it by hand.

One of them writes your Reels off 26 hook formulas and scores the hook before
you waste a take on it. One goes and finds the reels that are actually working
in your niche and ranks them by how far each beat its own account. One writes
the caption and shows you exactly what the feed shows before the "... more".
One scores your profile out of 100 and rewrites what lost points. One plans the
week.

And one is the humanizer, which is the reason the rest are usable. It strips
the em dashes, the slop vocabulary and the invisible watermark characters out
of a draft, then scores what is left against a five-check panel before you ever
see it.

**Nothing gets posted until you say publish.** The writing skills never
touch Instagram. `/ig-publish` does, once, after you approve the exact caption
and media.

## Install

Paste this into Claude:

```
https://github.com/nessalazne/instagram-agent-skill

Install this skill, then confirm /ig-reel works.
```

Or do it yourself, in Claude Code:

```bash
git clone https://github.com/nessalazne/instagram-agent-skill.git
cp -r instagram-agent-skill/skills/ig-* ~/.claude/skills/
```

Or as a plugin:

```
/plugin marketplace add nessalazne/instagram-agent-skill
/plugin install instagram-agent
```

Project-local instead of global: copy the same folders into your repo's
`.claude/skills/`. No Claude Code at all? Paste any single `SKILL.md` at the top
of a chat and it runs as a mode. You lose the five Python tools, which is most
of the point of `/ig-reel` and `/ig-human`, but the rest works.

Then spend ten minutes on `templates/voice.md`. Copy it to
`~/.claude/instagram/voice.md` and fill it in, or send Claude three of your own
reels and say "write my voice.md from these". Every skill reads that file. It
matters more here than on other platforms, because you have to say the words
out loud.

## The sixteen

| command | what it does |
| --- | --- |
| `/ig-reel` | One idea into a Reel. Three hooks from [26 formulas](skills/ig-reel/hooks.json), scored, then the script, the on-screen text and a timed beat sheet. |
| `/ig-viral` | Goes and finds what is working in your niche, ranks it by multiple over each account's own median, names the formula, writes the swipe file. |
| `/ig-caption` | The caption, linted. Shows you the 125 characters the feed actually shows before the tap. |
| `/ig-carousel` | Swipe posts. The cover that earns the swipe, slide copy, and the 1080x1350 files. |
| `/ig-story` | The daily story sequence, which sticker does which job, and the DM funnel that starts with them moving first. |
| `/ig-profile` | Scores your profile against a [12-part rubric](skills/ig-profile/rubric.json) out of 100, then rewrites in fix-first order. |
| `/ig-plan` | The week. What to post, which format, when, and the 10 accounts to engage with. |
| `/ig-human` | The humanizer. Two scripts that actually run. See below. |
| `/ig-comment` | Comments on other people's posts. Nine types, picked by what the post actually is. Never "🔥🔥🔥". |
| `/ig-reply` | The thread under your own post. Sorts into keyword / lead / substance / question / support / noise, then writes in that order. |
| `/ig-dm` | The keyword delivery, the first message, the collab pitch, and the two follow-ups. Two. |
| `/ig-repurpose` | One video, podcast or newsletter into a week of reels and carousels that each stand alone. |
| `/ig-audit` | Post-mortem on what you already posted. Ranks by outlier multiple and sends per reach, not views. |
| `/ig-publish` | Posts or schedules the approved Reel, photo, carousel or story through Blotato. Names the account, asks for the word "publish", polls until it is live, prints the URL. See below. |
| `/ig-insights` | The reels traveling under a hashtag, any account's stats and median views, and a ready-made input file for `/ig-viral`'s swipe ranking. Needs an Apify token. See below. |
| `/ig-hashtags` | The three to five tags for one post, sized niche / mid / broad, each with a reason. Labels, not a reach lever. |

## The five tools that actually run

No dependencies, no network, nothing uploaded. They run on your machine, on
your text.

### Hooks

```bash
python3 hookscore.py hooks.txt              # rank your options
python3 beats.py script.txt --target 30     # time it before you shoot it
```

```
HOOK RANKING
==============================================================================
->  85.6 STRONG  Nobody tells you that your first 30 reels are supposed to f...
        weakest: SPECIFICITY (75)
    81.4 STRONG  I lost $18,000 because of one missing contract.
        weakest: ADDRESS (70)
    54.4 OK      Stop scrolling if you want to grow on Instagram in 2026 🔥
        weakest: STAKES (70)
        dealbreaker: Opens with "stop scrolling". Asking for attention proves
                     you have not earned it.
     9.6 WEAK    Hey guys, today I wanted to talk about content strategy
        weakest: FRONTLOAD (0)
        dealbreaker: Greeting. Nobody came to the feed to be greeted.
```

`beats.py` estimates how long each line takes to say, stacks them into
timecodes, and flags the four things that kill a Reel in the edit: a hook that
runs past three seconds, a beat long enough for the viewer to leave, a run of
lines with nothing concrete in them, and no loop back to the first line.

```
BEAT SHEET  ·  73 words  ·  ~26.6s at 165 wpm  ·  target 30.0s
========================================================================
  0:00.0   2.9s  HOOK    I lost $18,000 because of one missing contract.
  0:02.9  14.6s  MID     Here is the exact clause I now put in every single...
                         ^ 14.6s on one beat
  0:17.4   2.9s          Section 4. Payment on delivery, not on approval.
  0:20.4   2.9s          Approval is a feeling. Delivery is a date.
  0:23.3   3.3s  CTA     That one word change is worth $18,000 to me.
------------------------------------------------------------------------
  - Beat 2 runs past 4s. Either split the line or change what is on screen
    inside it. A static frame is where people leave.
  - Loops: the last beat repeats "$18,000" from the hook. Second watches are
    free reach.
  - 3.5s under target. Either add 9 words or shoot it short. Short is usually
    right.
```

### The caption

```bash
python3 caption.py caption.txt --keywords "client contracts,freelance pricing"
```

Instagram gives a caption about 125 characters in the feed and hides the rest
behind a tap. Almost every caption that fails, fails there. So the first thing
this prints is that window, as a box, the way a scrolling stranger reads it:

```
  WHAT THE FEED SHOWS
  +------------------------------------------------------+
  | I lost $18,000 because of one missing clause in a    |
  | contract, and the worst part is that I had read the  |
  | thing twice before I si                              |
  +-------------------------------------------- ... more +

  PASS  LENGTH            389 / 2200 characters
  WARN  FIRST LINE        133 characters, so it gets cut at 125 mid-thought
  PASS  HOOK IS CONCRETE  2 numbers or names in the visible window
  PASS  HASHTAGS          3 tags: #freelance #contracts #agencyowner
  PASS  ONE ASK           one call to action: comment a keyword
  WARN  SEARCH TERMS      1/2 present. Missing: client contracts
```

It enforces the current hashtag cap, which is **five per post**, not thirty.
Instagram cut it on 18 December 2025.

### The humanizer

```bash
python3 humanize.py draft.txt --report      # clean it, show every change
python3 detect.py draft.txt                  # score it, five checks
python3 detect.py before.txt after.txt       # prove the delta
```

**What comes out automatically:**

- **Invisible characters.** Zero-width spaces and joiners, word joiners, soft
  hyphens, byte-order marks, Unicode tag characters, invisible separators,
  non-breaking and narrow spaces. Your keyboard does not make these. They
  survive copy-paste and they are invisible in every editor you own.
- **Typography.** Em dash to comma, en dash to hyphen, curly quotes to
  straight, ellipsis to three dots, and the orphaned punctuation that leaves.
- **The lexicon.** 160 stock words and phrases with plain-English replacements.
  The last block of it is Instagram-specific: "stop scrolling", "in today's
  video", "follow for more", "tag someone who needs this", "the algorithm
  loves", "run don't walk". It lives in
  [`slop.json`](skills/ig-human/slop.json) and it is meant to be edited.

**What gets flagged instead of fixed:** "It's not just X, it's Y", rule-of-three
triads, the video preamble, emoji bullet lists, three shouted words in a row,
hashtag walls, reflex follow bait, uniform sentence length. Changing the shape
of a sentence needs judgement, so those come back for a rewrite rather than
getting mangled by a regex.

Run against a caption written to be as bad as possible:

```
  BURSTINESS    ###################.....  78.4
  SPECIFICITY   #############...........  53.6    3.4 concrete markers per 100 words
  SLOP DENSITY  ........................   0.0    20 stock terms, 23.0 per 100 words
  FINGERPRINT   ################........  68.7    1 em dash
  VOICE         #################.......  70.0    9 structural tells
  ------------------------------------------------------------
  HUMAN SCORE   ########................  32.5   FLAGGED
```

After `humanize.py`, with the flagged structures still unrewritten:

```
  HUMAN SCORE   ###################.....  79.7   PASS    (+47.2)
```

### The swipe file

```bash
python3 swipe.py captured.tsv --out ~/.claude/instagram/swipe.md
```

Raw views are not evidence. A 2,000,000-follower account doing 400,000 views
had a quiet Tuesday. A 4,000-follower account doing 400,000 views found
something. `swipe.py` ranks on the multiple over each account's own median,
names the hook formula, and prints what separates the top third from the
bottom third.

```
SWIPE FILE  ·  4 reels  ·  4 accounts  ·  baseline: account median
==============================================================================
    60.0x  hook  57  #9  The Steal              @c                 180,000
           "steal this four line follow up it took me two years"
    37.5x  hook  86  #3  Nobody Tells You       @a                 412,000
           "nobody tells you that your first 30 reels are supposed to flop"
     1.3x  hook  13  -   unclassified           @b               1,200,000
           "in this video I am going to show you my morning routine"
```

## Publishing

`/ig-publish` is the one skill that sends anything. It uses
[Blotato](https://blotato.com/?ref=ness), which publishes through Instagram's
official Content Publishing API on an account you connected to Blotato
yourself, so the post does not come from a browser pretending to be you. The
account must be a Business or Creator account. It needs two lines in
`~/.claude/instagram/.env`:

```
BLOTATO_API_KEY=your-key
BLOTATO_ACCOUNT_INSTAGRAM=1234
```

The account id comes from Blotato's account list. Then:

```bash
python3 skills/ig-publish/publish.py --check                                  # which @account is that id?
python3 skills/ig-publish/publish.py caption.txt --video reel.mp4 --dry-run   # the payload, nothing sent
python3 skills/ig-publish/publish.py caption.txt --video reel.mp4             # a Reel, now
python3 skills/ig-publish/publish.py caption.txt --images 1.png 2.png 3.png   # a carousel, in order
python3 skills/ig-publish/publish.py caption.txt --images photo.jpg --first-comment link.txt
python3 skills/ig-publish/publish.py --story frame.png
python3 skills/ig-publish/publish.py caption.txt --video reel.mp4 --schedule next_slot
python3 skills/ig-publish/publish.py caption.txt --video reel.mp4 --schedule 2026-09-22T12:15:00Z
```

Instagram takes no post without media, so every run names a video, images or
a story frame. Local files are uploaded to Blotato first; hosted URLs pass
straight through. The script refuses a caption over 2,200 characters or with
more than five hashtags rather than cutting it, refuses a carousel outside 2
to 10 items, and refuses a schedule in the past. Before every live send it
looks the account up and prints its `@username`, because one Blotato workspace
can hold several Instagram accounts.

Inside Claude the skill does this for you, but it will not send anything until
you type the word "publish" under the final caption. It polls Blotato every 20
seconds until the post is published, scheduled or failed, and prints the URL.
Every send is appended to `~/.claude/instagram/log.md`.

The script needs Python 3 and the `requests` package. Your caption and media
go to Blotato and from there to Instagram, nowhere else.

## Reading Instagram (optional)

`/ig-viral` collects by hand, and it still works exactly that way. If you
would rather not, add an [Apify](https://apify.com) token to the same
`~/.claude/instagram/.env` and `/ig-insights` collects for you:

```
APIFY_TOKEN=apify_api_...
```

```bash
python3 skills/ig-insights/fetch.py --check                       # is the token good?
python3 skills/ig-insights/fetch.py hashtag contentcreatortips    # reels traveling under a tag
python3 skills/ig-insights/fetch.py profile HANDLE1 HANDLE2       # stats + median views
python3 skills/ig-insights/fetch.py swipe TAG --dry-run           # the runs and the cost, nothing sent
python3 skills/ig-insights/fetch.py swipe TAG --max 30 --out captured.tsv
python3 skills/ig-viral/swipe.py captured.tsv                     # unchanged, same ranking
```

`swipe` writes the exact file `/ig-viral` asks you to fill in by hand
(account, followers, median, views, hook), taking each owner's median from
their last 12 posts. The one difference: the hook is the caption's first
sentence, not the spoken first line, so expect more rows the formula
classifier cannot name.

It uses Apify's own public, no-login actors, so your Instagram account is
never involved and nothing is done as you. It is pay-per-use, about $0.0026
per post or profile, so a 30-reel swipe file is about $0.16, and Apify's free
tier includes $5 a month. Every run carries a hard spending ceiling, and the
skill shows the estimate first and asks before anything over $1.
`fetch.py` is standard library only.

## What I actually measured, which is the part worth reading

I did not want to publish a hook scorer on the claim that it feels right, so I
tested it. The corpus is **74 real short-form hooks**: the first three seconds
of the auto-caption track from the top eight and bottom eight performing shorts
on each of five channels, view counts from 931 to 550,000.

They are YouTube Shorts rather than Reels, because Instagram does not hand you
view counts you can collect without logging into somebody's account, and
scraping it would violate the Terms this repo tells you not to violate. The
hook grammar is the same and the sourcing is public. That is a real limitation
and it is stated here rather than buried.

**Three results, two of them uncomfortable:**

**1. It catches bad hooks well.** Against ten hooks written deliberately badly,
AUC 0.83, and nine of the ten scored below the median of the real corpus. If
your hook opens on a greeting, a preamble or nothing concrete, this tells you.

**2. It does not pick winners.** Separating a good creator's hits from that
same creator's misses: **AUC 0.56, where 0.50 is a coin flip.** Of the five
checks, only SPECIFICITY separated the bands meaningfully, by 60 points of
median. STAKES and ADDRESS had identical medians in both bands, which means on
this corpus they measured nothing.

So the honest use is: kill the obviously weak hooks before you shoot them, then
trust your own retention graph. Nothing that reads text can tell you which of
two decent hooks will travel, because that is decided by your face, your edit,
your audio and who Instagram shows it to.

**3. The formula classifier was broken and the test is what caught it.** The
`match` regexes in `hooks.json` were written off my own templates, and they
named **8%** of real hooks. People do not speak in templates. Rewriting them
against actual transcribed speech took it to **49%**, and four formulas went
into the set because they kept appearing and were not there: Contrarian Flip,
The Statistic, The Reveal, Someone Else's Result, plus The Superlative. On the
other 51% it abstains, which is correct: a lot of short-form is podcast clips
that have no hook formula at all.

One fixed bug worth naming: `SPECIFICITY` only counted digits, so "zero
dollars" and "three marketing books" scored as having nothing concrete in them.
Spoken hooks say their numbers out loud.

If you re-run this on a bigger or cleaner corpus and get a different answer, I
would rather know. The measurement script is not in the repo because it depends
on `yt-dlp`, but the method is four lines and is written out in
[`/ig-viral`](skills/ig-viral/SKILL.md).

## The fine print, which is the honest part

**The writing skills do not post to Instagram.** There is a real Content
Publishing API for Professional accounts, and it needs a Meta developer app, a
linked Page, a long-lived token and app review, which is not a thing a skill
can hand you. Automating comments, follows, likes or DMs through browser
automation violates
[Instagram's Terms of Use](https://help.instagram.com/581066165581870) and gets
accounts action-blocked. So every writing skill ends the same way: a
copy-ready block. The only way out of this pack is `/ig-publish`, which posts
your own content through a publishing tool that already holds that API access,
and asks you twice. It never comments, follows, likes or messages. That is the
design, not a setting.

The one exception is keyword auto-replies in DMs, which Instagram supports
through its own tools and approved partners, and which only fire after somebody
comments first. `/ig-dm` says where that line is.

**`/ig-viral` reads, it does not scrape.** Ten accounts, a dozen reels each, at
human speed, with you driving your own browser. It never asks for your password
and never logs in as you. Automated collection at volume is the thing that gets
accounts restricted, and a crawler is not what this is.

`/ig-insights` is the opt-in exception, and it is different in the way that
matters: it reads public data through Apify's own no-login actors, a few dozen
posts at a time, and never touches your account. If you would rather not use a
paid data service at all, don't add the token, and `/ig-viral` works as before.

**The five detection checks are local heuristics, not detector APIs.** They are
modelled on the signals public detectors key on and they run entirely on your
machine. They are not GPTZero, Originality, Copyleaks, Winston or Turnitin,
they do not call those services, and they cannot promise those verdicts. Fixing
what they measure tends to move those numbers, because they are measuring the
same underlying things. That is the whole claim. Nobody can honestly sell you
"undetectable", and anybody who does is selling you something.

**The invisible-character pass is real and it is narrow.** It removes the
zero-width and format characters that end up in generated text and survive a
copy-paste. That is a genuine, checkable fingerprint. It is not a claim about
defeating a cryptographic watermarking scheme, and this repo does not make one.

**Nothing here fabricates.** No invented metrics, clients or outcomes go under
your name. If a draft needs a number you have not given, it comes back with
`{{your number}}` in it and a flag, every time.

**Platform numbers go stale.** The hashtag cap moved from 30 to 5 in December
2025 while this repo was being written, and the linter had the old number in it
until the fact got checked. If something here contradicts what Instagram is
doing when you read it, Instagram is right.

## Files

```
skills/ig-reel/hooks.json          26 hook formulas: template, example, on-screen line,
                                   what it is for, how it gets ruined, and a match regex
skills/ig-reel/hookscore.py        the five-property hook panel
skills/ig-reel/beats.py            script to timed beat sheet
skills/ig-caption/caption.py       the truncation preview and the caption linter
skills/ig-human/slop.json          the lexicon: 160 terms, 18 invisible classes, 17 tells
skills/ig-human/humanize.py        the three cleaning passes
skills/ig-human/detect.py          the five-check panel
skills/ig-viral/swipe.py           outlier ranking and formula classification
skills/ig-profile/rubric.json      the 100-point profile score
skills/ig-publish/publish.py       the Blotato sender: check, dry run, upload, post, schedule, poll
skills/ig-insights/fetch.py        the optional Apify reader: hashtags, profiles, swipe.py input
templates/voice.md                 your voice profile. Fill this in first.
```

## What changed in the Ness edition

- `/ig-publish`: new skill and `publish.py`, posting or scheduling Reels,
  photos, carousels and stories through Blotato, with a dry run, an account
  check on every send, caption, hashtag, carousel and schedule guards, and
  status polling.
- `/ig-insights`: new skill and `fetch.py`, adapted from `ig-audience-insights`
  in Serge Bulaev's [instagram-skills](https://github.com/sergebulaev/instagram-skills)
  (MIT). Its `swipe` command writes `/ig-viral`'s input file, so `swipe.py`
  did not change.
- `/ig-hashtags`: new skill, adapted from Serge's `ig-hashtag-strategist` and
  rewritten to agree with `/ig-caption` that hashtags are labels.
- `slop.json`: added vibrant, "let's dive in", "dive in", "game changer",
  "I hope this helps", and an announcement-opener structural tell, to match
  the house humanizer rules.
- `/ig-reel`, `/ig-caption`, `/ig-carousel`, `/ig-story`, `/ig-plan`,
  `/ig-repurpose`: one line each pointing at `/ig-publish` after the user's
  yes. Nothing else in those skills changed. The five Python tools are
  byte-identical to the original.
- Plugin manifests and this README.

## Credit

Original pack by Jake Schincariol, [opusjake.ai](https://opusjake.ai).
`/ig-insights` and `/ig-hashtags` are adapted from Serge Bulaev's
[instagram-skills](https://github.com/sergebulaev/instagram-skills) (MIT).
This edition is maintained by Ness Alazne,
[builds.digicuratoragency.com](https://builds.digicuratoragency.com).

Sibling repo, same idea for a different platform:
[linkedin-agent-skill](https://github.com/Jakeschincariol/linkedin-agent-skill).

## License

MIT. Take it, change it, ship it.
