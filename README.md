# CHAOS;HEAD NOAH — English patch for the PSP

**CHAOS;HEAD NOAH** came out on the PSP in 2010, but only in Japanese. English speakers finally got the game
years later on PC and Switch, and on Steam there's Committee of Zero's excellent fan translation. That
version never made it back to the PSP.

This patch brings it home. It takes Committee of Zero's English translation and puts it into the original
Japanese PSP release, as close to 1:1 as the PSP allows: the same words, the same jokes, the same Tips,
on the handheld the game was made for.

> **What you need:** your own copy of the Japanese PSP game (ULJM05692) as an `.iso`. No game files are
> included here; the patcher only works on the original, unmodified ISO.

**[Download the latest release](https://github.com/HarukaKumazaki/chaoshead-noah-psp-english/releases/latest)**
and see [INSTALL.md](INSTALL.md) for the two-minute setup.

---

## What you get

Everything you read in the game is in English. You can play every route and see every ending without
running into Japanese text.

| Part of the game | Status | Where the English comes from |
|---|---|---|
| Story (all routes, all 9 endings) | 25,988 / 25,988 lines | Committee of Zero, word for word |
| Choices and delusion triggers | complete | Committee of Zero |
| Character names, chapter titles | complete | Committee of Zero |
| Tips glossary | 146 / 146 entries | Committee of Zero |
| Highlighted Tips words in the story | 113 / 113 | placed on the same words CoZ highlights |
| Menus, config, save/load, backlog | complete | CoZ's terms; PSP-only screens written for this port |
| Pictures with text (chat logs, forums, screens, signs) | complete | CoZ's translated artwork |
| Full-screen text pages (prologue, late chapters) | 75 pages | Committee of Zero |
| Movies (opening, endings, story videos) | 19 videos | CoZ's English videos and subtitles |
| Music Gallery (46 songs) | titles, credits and lyrics | CoZ's song subtitles; a few extra verses translated here |
| Extras (Clear List, CG Gallery, Music Gallery, Tips) | complete | |

The extras work exactly like the original: they show up as `???` on a new save and unlock as you clear
the game.

### What's not from Committee of Zero

A handful of things only exist in the PSP version, so CoZ never had to translate them. I translated those
myself, sticking to CoZ's wording and terms:

- around 8 short PSP-only lines (mostly shouts and sighs), plus 5 lines CoZ's own patch leaves in Japanese
- lyrics for song verses that CoZ never subtitled
- the scrolling news ticker in one video
- the PSP's own menu, config and save messages, and the Tips category labels

If you want the full numbers (lines per chapter and route, how each line was matched, every change), it's
all in **[TRANSLATION.md](TRANSLATION.md)**.

## What was brought over from the PC version

- **The full script**, Tips, character names and chapter titles from CoZ's patch
- **Translated artwork**: CoZ's English chat logs, forum pages and screens, plus the Steam release's
  English backgrounds
- **English videos**: the English ending credits and story videos, with CoZ's subtitles and song karaoke
- **CoZ's English warning screen** at startup

The PC and Switch versions have a few extras the PSP version never had (like a movie gallery). Those
aren't part of this patch, since the PSP game has nowhere to put them.

## What had to change on the PSP

English takes up more room than Japanese, and I didn't want to cut or reword anything, so the game was
adjusted to fit the text instead:

- a proper **English font** (with italics) instead of wide Japanese-style letters
- a **5-line text box** instead of 3 (still only about a third of the screen)
- the **backlog** and full-screen pages now wrap between words, never in the middle of one
- more room for English in the **Clear List** and **Config** screens, so names and labels aren't cut off
- the **button guides** at the bottom of the menus are redrawn in English with the original icons
- a small engine bug that drew a thin line under every letter is fixed

Everything else (controls, menus, how the extras unlock) is left exactly as it was.

## Playing

Works in **PPSSPP** and on a real **PSP** or **PS Vita** with custom firmware (ARK-4, PRO/LME, Adrenaline).
It's been tested thoroughly in PPSSPP. Testing on real hardware is still in progress, so if you run into
anything odd, please [open an issue](https://github.com/HarukaKumazaki/chaoshead-noah-psp-english/issues)
with a screenshot or photo.

## For tinkerers

The whole pipeline that builds the English ISO is in this repo: the script injector, font builder, image
and movie tools, the code patches for the game, and the patchers. [BUILDING.md](BUILDING.md) explains how
to rebuild everything yourself from the Japanese ISO and a Steam copy of the game with CoZ's patch.
[NOTES.md](NOTES.md) has the technical details on file formats and engine limits.

| Folder | What's inside |
|---|---|
| `tools/` | the build pipeline (Python) |
| `tools/test/` | helpers that drive PPSSPP for automated testing |
| `patcher/` | the Windows and Linux patchers, and the scripts that make a release |

## Credits

- **Committee of Zero** for the English translation, artwork and subtitles this whole thing is built on
  (<https://sonome.dareno.me/>). Go play their patches.
- **5pb. and Nitroplus** for the original game, and **MAGES. / Spike Chunsoft** for the PC release.

This is a free, non-commercial fan project. It isn't affiliated with or endorsed by the rights holders or
by Committee of Zero. If you enjoy it, please support the official releases.
