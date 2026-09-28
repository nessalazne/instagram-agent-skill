---
name: ig-hashtags
description: >-
  Pick the three to five hashtags for one Instagram post, sized niche / mid /
  broad so they describe the post precisely instead of dumping it into a
  million-post feed, with a one-line reason each and a rotation note. Use when
  the user says "which hashtags", "give me hashtags for this", "is my hashtag
  set any good", pastes a block of twenty saved tags, or has a caption from
  /ig-caption and wants the tag line. Not for the caption itself (use
  /ig-caption).
---

# ig-hashtags

`/ig-caption` already says the important part and this skill does not argue
with it: **hashtags are labels, not a reach lever.** Instagram capped them at
five per post on 18 December 2025, and Adam Mosseri said in February 2025 that
they do not increase reach. `caption.py` fails anything over five.

So the job here is narrow. Given five slots, which five words tell Instagram,
and the few people who search tags, exactly what this post is. That is a
sizing problem, and it is the part people get wrong.

## Sizes

| size | posts using it | what it does | how many |
| --- | --- | --- | --- |
| niche | under ~50k | names the exact community and topic | 2 to 3 |
| mid | ~50k to 500k | names the sub-topic | 1 to 2 |
| broad | 500k and up | a category label, nothing more | 0 or 1 |

Three to five in total. Leave the broad slot empty rather than fill it with
something vague.

**The counts are estimates.** Nothing in this pack reads a tag's real post
count reliably. Size by specificity: two words joined (`#notionforfreelancers`)
or a community's own name is niche; a known sub-topic (`#contentstrategy`) is
mid; one common word (`#marketing`) is broad. Tell the user to check the count
in Instagram search for any tag on the border between two sizes, and say which
ones those are.

## Steps

1. **Get the post.** The caption or the idea, who it is for, and the account's
   rough size. Read `~/.claude/instagram/voice.md` for the audience if it is
   filled in.
2. **Name what the post is actually about**, in three to five topics: the
   subject, the community, the format, the outcome.
3. **Propose candidates for each size**, then cut every tag that is popular but
   does not describe this post. A mismatched tag labels the post wrong.
4. **Drop filler on sight.** `#viral #fyp #explorepage #foryou #instagood
   #like4like #follow4follow` and anything like them describe nothing. The same
   list lives in `caption.py`.
5. **Assemble three to five** and run the caption through
   `python3 ../ig-caption/caption.py caption.txt` with the tags on their own last
   line. It must pass HASHTAGS and TAG PLACEMENT.
6. **Rotation note.** The niche tags change with each post's topic. Pasting one
   saved block under every post is the pattern to avoid.

If `/ig-insights` has run, `~/.claude/instagram/insights/` shows which tags the
top reels in the niche actually used. Prefer those over guesses, and say where
they came from.

## Output

```
TAGS  (4)
  #notionforfreelancers   niche   the exact community this post is for
  #freelanceworkflow      niche   names the topic, long-tail
  #productivitytips       mid     sub-topic label, check the count in search
  #notion                 broad   category label

placement:  last line of the caption, or the first comment
rotate:     swap the two niche tags per topic; the mid and broad can repeat
caption.py: HASHTAGS PASS, TAG PLACEMENT PASS
```

## Rules

- Five is the ceiling. Never write a block of more, and never hide extras
  behind dots or line breaks.
- Every tag describes this post. No tag chosen only for its size.
- Tags never go inside the first 125 characters or mid-sentence.
- The phrase the user wants to be found for goes in the caption as words (see
  `/ig-caption`, "Search terms matter more than hashtags now"), not only as a tag.
- Never claim a tag will bring reach. It labels the post.

Adapted from `ig-hashtag-strategist` in Serge Bulaev's
[instagram-skills](https://github.com/sergebulaev/instagram-skills) (MIT),
rewritten to fit this pack's position that hashtags are labels.
