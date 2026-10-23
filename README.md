# CHAOS;HEAD NOAH (PSP) — English Translation Patch

An English patch for the Japanese PSP release of **CHAOS;HEAD NOAH** (ULJM05692), built from
**Committee of Zero's English translation** (CoZ patch 1.1.3 for the Steam release), ported 1:1 to the PSP.

> You need your own copy of the Japanese PSP game as an ISO. This project contains no game files;
> the patch only works on the original, unmodified ISO.

## What is translated

- **The full script**: all 25,988 lines, every route and all 9 endings, using CoZ's English word for word.
- **Choices, delusion triggers, speaker names, chapter titles, chapter-jump menu**
- **Tips**: all 146 entries (term, reading, category, CoZ's description). Tips words are highlighted in the
  text, and the L button opens their Tips page, as in the original.
- **Menus and system text**: title, config, save/load, backlog, system menus, PSP save dialogs, Clear List
- **Images**: CAUTION screen, chat logs, BBS/terminal/ESO screens, chapter cards, menu textures, signs
- **Movies**: opening and ending videos with CoZ's English subtitles and karaoke; insert videos with English
- **Music Gallery**: song titles, credits and timed lyrics
- **Extras**: Clear List, CG Gallery, Music Gallery and Tips (the four extras the PSP version has).
  As in the original, they show as ??? on a new save and unlock as you clear the game.

The PSP text box shows 5 lines (the original shows 3) so CoZ's longer English fits without rewording,
and a proportional English font is included.

### Text that is not CoZ's

A few things exist only in the PSP version, so CoZ has no English for them. These were translated
for this port, following CoZ's wording and terms:

- about 8 short PSP-only lines (mostly exclamations), and 5 lines CoZ 1.1.3 left in Japanese
- Music Gallery lyrics for songs/verses CoZ never subtitled
- the scrolling news ticker in one insert video
- PSP-only menu, config and save-dialog messages, and the Tips category labels

A full breakdown (lines per chapter and route, how each line was matched to CoZ, every change made to
the game) is in **[TRANSLATION.md](TRANSLATION.md)**.

## Installing

See **[INSTALL.md](INSTALL.md)**. In short: download the release, then run `Patch-Windows.bat` (Windows)
or `patch-linux.sh` (Linux) and choose your Japanese ISO. Nothing else needs to be installed.

Plays on PPSSPP and on a real PSP or PS Vita with custom firmware (ARK-4, PRO/LME, Adrenaline).

## Building from source

See **[BUILDING.md](BUILDING.md)**. The tools in `tools/` rebuild the English ISO from the Japanese ISO
and a Steam copy of CHAOS;HEAD NOAH with the CoZ patch installed. `patcher/makepatch.py` turns the result
into the release patch.

## Repository layout

| Path | Contents |
|---|---|
| `tools/` | the build pipeline (Python): script injection, font, images, movies, EBOOT patches, ISO rebuild |
| `patcher/` | release patchers (Windows batch + PowerShell, Linux shell) and the patch generator |
| `tools/test/` | test helpers that drive PPSSPP through its debugger (button tours, highlight finder, glyph-slot tracer) |
| `TRANSLATION.md` | what is translated, line counts per part, where the English comes from, what was changed |
| `NOTES.md` | technical notes: file formats, engine limits, every code patch |

## Credits

- **Committee of Zero**: the English translation, images and subtitles this port is built on
  (<https://sonome.dareno.me/projects/chn.html>)
- **5pb. / Nitroplus / MAGES. / Spike Chunsoft**: the original game
- PSP port: this project

This is a non-commercial fan project. It is not affiliated with or endorsed by the rights holders
or by Committee of Zero. Please support the official releases.
