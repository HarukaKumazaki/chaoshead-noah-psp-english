# CHAOS;HEAD NOAH (PSP, ULJM05692) — English patch from CoZ 1.1.3

## Build (one command)

```
python tools/build.py out.iso                 # full English ISO
python tools/build.py out.iso --preview SCH01_002   # test build: New Game starts in that scene
python tools/build.py out.iso --images        # also regenerate all translated pictures/textures/sprites
python tools/movies.py work/ov_mov            # (once, ~10 min) English movies; build.py picks them up
```
Input: `..\Chaos;Head Noah (Japan).iso` (never modified) and the Steam CHN folder with the CoZ patch.
First-time setup: see BUILDING.md (`tools/setup.py`, EBOOT dump).

## Layout

| Path | What |
|---|---|
| `iso/` | files extracted from the original ISO (read-only reference) |
| `unpacked/DATA0`, `unpacked/DATA1` | AFS archives unpacked (byte-identical repack verified) |
| `steam/` | CoZ text (`mes00` JP / `mes01` EN) and `c0data` assets extracted from the Steam install |
| `work/ov/` | overlay: patched files that replace originals at build time |
| `work/eboot/` | decrypted EBOOT, string catalog, patched EBOOT |
| `work/usrdir/` | patched loose files (SYSTEM.CFG) |
| `tools/` | all tooling (below) |

## Tools

- `build.py` — font → scripts → system files → EBOOT → AFS → ISO
- `afs_unpack.py` / `afs_pack.py` — AFS archives (pack copies untouched sub-archives from the original)
- `iso_patch.py` — replaces files inside the ISO (in place, or moved to the end)
- `pspscr.py` — PSP script format; string pointers only in opcodes 0x18/0x23/0x1B/0xD8/0xD9
- `msb.py`, `align.py`, `inject.py` — CoZ text decode, JP-content alignment, injection + wrapping
- `mkfont.py`, `enc.py`, `simtext.py` — English font (ASCII = 1 byte, engine draws byte b with glyph 752+b-0x21), encoder, offline renderer
- `sysfiles.py`, `ui_tr.py`, `strpatch.py` — speaker names, chapter titles, TIPS, clear list, menus, config files
- `ebootcat.py`, `eboot_tr.py` — EBOOT strings (config screen, menus, save dialogs)
- `klz.py`, `tim2.py`, `p2t.py`, `p2tlz.py` — image codecs (KLZ = BG/CG/sprites; P2T = menu textures,
  blobs = u32 size + Okumura LZSS, 4 KB zero ring, start 0xFEE)
- `images.py`, `chatimg.py`, `logimg.py`, `miscimg.py` — BG/CG/chat/terminal/questionnaire pictures
- `uitex.py` — CAUTION screen (CoZ z_warning), 27 button-guide bars, controls help, voice cast, song cards
- `spriteimg.py` — CoZ's English sign on Kazuki's sprites (MVL mesh + atlas reconstruction, aligned at 1/4)
- `movies.py`, `pmf.py`, `usm_demux.py` — English movies: CoZ videos (English credits/screens) or PSP
  video + CoZ .ass burned in, x264 Main@2.1 P-only + AUD/HRD/pic-timing, remuxed with original ATRAC3+
  audio packs and regenerated per-GOP 0xBF index (picture sizes + pack offsets of pictures 1-4)
- `musictr.py`, `cozlyrics.py`, `music_lyrics.py` — Music Gallery titles, credits and timed lyrics
- `ppdbg.py` — drives a hidden PPSSPP via its debugger API for testing (no keyboard input)
- `setup.py` — extracts the ISO, AFS archives and Steam/CoZ archives (build inputs)
- `../patcher/makepatch.py` — release patch: one self-contained `.dat` (index + new sectors) for the batch / shell patchers

## Hard constraints learned

- SYSTEM.CFG is read into a 4 KB buffer: keep it ≤ 4096 bytes.
- EBOOT data section mixes strings with initialized variables: only reuse a string's own bytes + alignment.
- Developer menu labels stay Japanese (title font can't draw them → hidden, like retail).
- Speaker tags 【…】 in scripts are lookup keys into DATA.BIN; translate DATA.BIN values, not the tags.
- Save-data title / PSP system dialog strings must be plain ASCII (system font).

## Status

Done
- [x] All 25,988 script strings (dialogue, effect copies, choices) — 0 Japanese left (`tools/jpscan.py`)
- [x] 5 lines CoZ left untranslated in sch10_217 translated by hand (inject.py OVERRIDE)
- [x] Proportional English font (regular + italic), engine spacing rule measured
- [x] Speaker names, chapter titles/jump menu, clear list, 146 TIPS, title-menu help, config labels
- [x] EBOOT: config screen, in-game menus, save/load messages, dates

- [x] Images: CAUTION screen, BBS/chat/terminal/ESO pages, chapter cards, all menu textures (P2T)
- [x] Music Gallery: 46 titles/credits + timed lyrics (CoZ translations; full-length verses by hand)
- [x] Movies: OP/DEMO with CoZ karaoke + translation; END01-09, INSERT01/02/07-10/12 from CoZ's
      English videos (+ subs); INSERT05 news ticker re-typeset; verified playing in PPSSPP
- [x] PARAM.SFO title already ASCII; EBOOT is a plain ELF (runs on CFW/ARK/Adrenaline, which ISOs need)

Remaining / notes
- [x] All chat pages fully English (unmatched rows pinned in chatimg.PIN, join/leave notices)
- [x] Kazuki's sign sprites (L/S 1C-1E) with CoZ's English sign
- [x] Extra menu (Clear List / CG Gallery / Music Gallery / Tips) verified in-game with an unlocked save
      (work/save_unlocked). The PSP release only has these 4 extras; PC-only extras have no PSP engine code.
- [x] TIPS: 146 DICT.BIN entries from CoZ _tips (term, reading, category, description wrapped 400 px);
      all 113 in-text %B highlight markers kept on the CoZ-highlighted words (2 hand fallbacks)
- [x] Clear List: label/row glyph slots moved (ebootfix.clear_list_slots) so 'Total Play Time' and
      full ending/scene names fit (clamps 31/27 -> 49 chars); CLRFLG Silent Sky notice translated
- [x] Full-screen %L1 pages (prologue): text rect x 8 / w 472 in SYSTEM.CFG 0x134 -> no mid-word wraps
- [x] Config screen: label/value/help glyph slots re-laid out (ebootfix.config_slots); help texts <= 400 px
- [x] Load/Save button bar (OBJ_SC #28): icon at x 5 given explicitly (uitex BARS third field)
- [x] Tips category labels <= 9 characters (list rows hold ~10 glyphs)
- [x] Backlog: whole messages reflowed (stripper %N -> space while filling 0x089EA010), no short leftovers
- [x] English text from steam/c0mes01, which CoZ's patchdef.json redirects mes01 to (msb.en_file)
- [x] Characters missing from the font mapped (ë, CoZ's garbled hacker handle)
- [x] L button (Tips for the highlighted words) verified in-game: opens the right CoZ entry
- [x] Chat logs: one font size, long lines wrap inside the row to the visible ~360 px, links drawn as text,
      window header (Reload / Enter / Users (n)) relabelled in place; lone-line pages handled
- [x] ESO logs: one font size (12 px) for every log
- [x] Mid-row click pauses removed (%K only at row ends): they stalled force-skip (R) until START
- [ ] Final playtest on hardware
- Ending credits come from CoZ's videos, i.e. the PC/Switch release credits (as in CoZ).

## Text layout (final)
- Message box: 5 rows (was 3), 18 px pitch, 464 px text width, box 98 px tall (~1/3 of the screen);
  set in SYSTEM.CFG window records (sysfiles.py). CoZ's English is used word for word; pages that
  would not fit 5 rows use a 2 px space glyph (inject.WIDE_STEPS) -- no rewording anywhere.
- EBOOT code fixes (ebootfix.py): glyph-cache clear (no underline), backlog word-aware row split and
  message reflow in an unused routine at 0x088F2868, backlog piece width 336 px, layout loops reset y
  after a page token, Clear List and Config glyph-slot layouts.
- Kazuki/Shiina/Sena sprites keep their face-patch data (tim2.write keeps trailing data + palette).
