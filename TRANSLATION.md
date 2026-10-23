# Translation and port report

What this patch translates, where the English comes from, and what was changed in the PSP game to fit it.
Base: Committee of Zero's CHAOS;HEAD NOAH patch 1.1.3 (Steam), ported to the Japanese PSP release ULJM05692.

## Summary

| Part | Translated | English source |
|---|---|---|
| Story script (all routes, all 9 endings) | 32,631 / 32,631 lines (100%) | CoZ, word for word |
| Choices and delusion triggers | all | CoZ |
| Speaker names | 225 / 225 | CoZ |
| Chapter titles, chapter-jump menu | 33 / 33 | CoZ |
| Tips | 146 / 146 entries, 113 / 113 in-text highlights | CoZ |
| Clear List (endings, scene titles, unlock notices) | 22 + 9 / 22 + 9 | CoZ ending and scene names |
| Menus, config, save/load, system messages (EBOOT) | 303 strings | CoZ terms; PSP-only text written for the port |
| Title-menu help, config files | 21 + 9 | PSP-only, written for the port |
| Pictures with text (backgrounds, CGs, chat/BBS/terminal screens, signs) | 401 of 1,476 pictures changed; the rest have no text | CoZ's English pictures, or re-typeset with CoZ's text |
| Full-screen text cards (prologue, chapters 9-10) | 75 | CoZ |
| Menu textures (button bars, help screen, CAUTION, song cards) | 8 texture sets, 27 button bars | CoZ / port |
| Movies | 19 of 32 changed; the other 13 have no text to translate | CoZ's English videos and subtitles |
| Music Gallery | 46 songs: titles, credits, 389 lyric lines | CoZ subtitles; lines CoZ never subtitled translated for the port |
| Japanese text left anywhere in the scripts | 0 | |

## Story script in detail

How each of the 32,631 PSP script lines got its English:

| Method | Lines | Meaning |
|---|---|---|
| exact | 24,884 | the same Japanese line exists in CoZ's script; CoZ's English used as is |
| fuzzy | 371 | the PSP wording differs slightly from the PC script; matched to the same CoZ line (checked) |
| global / extra-global | 230 | the line sits in a different scene on PSP; CoZ's line found elsewhere in the script |
| manual | 227 | choice labels and debug-menu labels; mostly CoZ's own wording (45 x 3 delusion choices) |
| empty | 276 | lines with no text (timing / effect lines) |

Lines per part of the game:

| Part | Lines | | Part | Lines |
|---|---|---|---|---|
| Prologue | 80 | | Chapter 7 | 2,409 |
| Chapter 1 | 1,918 | | Chapter 8 | 1,625 |
| Chapter 2 | 950 | | Chapter 9 | 2,638 |
| Chapter 3 | 1,605 | | Chapter 10 | 2,655 |
| Chapter 4 | 2,090 | | Ayase route (scha) | 1,399 |
| Chapter 5 | 1,995 | | Kozue route (schk) | 1,101 |
| Chapter 6 | 1,179 | | Nanami route (schn) | 568 |
| | | | Rimi route (schr) | 864 |
| | | | Sena route (schs) | 1,323 |
| | | | Yua route (schy) | 1,202 |
| | | | other route scenes (schz) | 387 |

### English that is not CoZ's

These exist only on the PSP (or CoZ left them untranslated), so they were translated for this port in
CoZ's style and terms:

- about 8 short PSP-only lines (mostly exclamations, e.g. Nanami's "Aaaaaaahhh!")
- 5 lines in sch10_217 and one repeated line in schk_161 that CoZ 1.1.3 itself leaves in Japanese
- Music Gallery lyrics for songs and verses CoZ never subtitled (full-length versions)
- the scrolling news ticker in movie INSERT05
- PSP-only menu, config help and save-dialog text; Tips category labels (General, Fictional, Net/Otaku,
  DI-sword, Diagnosis); developer menus (not reachable in normal play)

## What was changed in the game to fit English

The goal was CoZ's text word for word, so the PSP game was adapted rather than the text shortened.

- **Font**: a proportional English font (regular + italic) replaces the full-width Japanese letters.
- **Message box**: 5 lines instead of 3 (about a third of the screen), 464 px wide. Long pages use a
  narrower space so they fit 5 lines without rewording.
- **Full-screen text pages**: text area widened to 464 px so English wraps between words.
- **Backlog**: rows split at spaces, and whole messages reflowed, so words are never cut.
- **Underline glitch**: the engine left a white line under every letter of the new font; fixed.
- **Clear List**: room for the English labels and for full ending and scene names (up to 49 characters).
- **Config screen**: room for the longer English labels, values and help texts.
- **Button bars and help screen**: redrawn in English with the original icons.
- **Movies**: re-encoded for the PSP (H.264 Main@2.1) with the original audio.

Everything else (the menus, the Extras unlocking as you clear the game, the controls) works exactly as in
the original PSP release.

## What was ported from CoZ

- The full English script, Tips, names and chapter titles (`languagebarrier/c0mes01`, which CoZ's
  patch loads in place of the game's own text)
- CoZ's translated pictures (`c0data`) and the Steam release's English pictures (`bg_eng`, `system_eng`)
- CoZ's English movie versions (ending credits, insert videos) and its song subtitles and karaoke
- CoZ's CAUTION screen

Not ported, because the PSP version doesn't have them: the PC/Switch-only extras (e.g. its movie gallery).
The PSP's own extras are Clear List, CG Gallery, Music Gallery and Tips, and all four are translated.

## Testing

Tested in PPSSPP: boot, title, prologue, chapter 1 (dialogue, Tips highlights and the L button, backlog,
skip, choices), save/load screens, config (every row), all Extra screens with an unlocked save, and a fresh
save (Extras locked, as in the original). Not yet tested on real PSP hardware, and not every route has
been played to the end.
