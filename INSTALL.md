# Installing the English patch

## What you need

Just two things:

1. **Your Japanese PSP ISO of CHAOS;HEAD NOAH** (ULJM05692), unmodified, as a `.iso` file
   (1,416,232,960 bytes). If yours is a `.cso`, convert it back to `.iso` first.
   **The file name doesn't matter.** The patcher recognises the game by its contents (size and
   checksum), so `chn.iso`, `ULJM05692.iso` or anything else works.
2. **This release** (`CHN-PSP-English-x.y.z.zip`).

That's it. You do **not** need the PC or Steam version, the Committee of Zero patch, Python, or any
other download. Everything the patch adds (the translated script, pictures, fonts, menus, the English
videos and subtitles, the code changes) is packed into `ChaosHeadNoah_PSP_EN.dat`, which ships next to
the patchers. The patchers only use tools Windows and Linux already have.

You'll also want about 1.5 GB of free disk space for the new English ISO.

The original ISO is never changed. The patcher writes a new file, `Chaos;Head Noah (English).iso`,
in the same folder as your ISO, and checks at the end that the result is byte-for-byte correct.

## Windows

1. Unzip the release to a folder.
2. Double-click **`Patch-Windows.bat`** and pick your Japanese ISO in the window that opens.
   (Or drag the ISO onto `Patch-Windows.bat`.)
3. Wait for `Done`. Checking and verifying take a minute or two.

If Windows SmartScreen warns about the batch file, choose *More info → Run anyway*.

## Linux (and macOS)

1. Unzip the release.
2. In a terminal, in the release folder:

   ```sh
   sh patch-linux.sh "/path/to/Chaos;Head Noah (Japan).iso"
   ```

   An optional second argument sets the output file name.
3. Wait for `Done`.

The script needs only `sh`, `dd`, `cp`, `awk` and `sha256sum` (or `shasum` on macOS), which every system has.

## Playing

- **PPSSPP** (PC, Android, etc.): open the English ISO.
- **PSP**: copy the ISO to `ms0:/ISO/` and run it with custom firmware (ARK-4, PRO-C, LME).
- **PS Vita / PS TV**: Adrenaline, ISO in `ux0:/pspemu/ISO/`.

## Controls (default, "Type 1")

| Button | Action |
|---|---|
| ○ | advance text / confirm (hold: auto mode) |
| △ | backlog |
| L | Tips for the highlighted words on the current page |
| R (hold) | force skip |
| START | message skip |
| SELECT | auto mode |
| Analog stick left / right | positive / negative delusion when a delusion trigger appears |

The full layout, in English, is under System → Help in the title menu.

## Troubleshooting

- **"This is not the expected ISO"**: the ISO is a different version, compressed, or already modified.
  You need the original Japanese release (ULJM05692) as a plain `.iso`.
- **"Verification failed"**: delete the output file and run the patcher again. If it keeps failing,
  download the release again (the patch file may be damaged).
- **PowerShell is blocked** on a locked-down Windows PC: run `Patch-Windows.bat` from a normal user account.
  It starts PowerShell with `-ExecutionPolicy Bypass` for this one script only.

## Building it yourself (optional)

You only need more if you want to rebuild the patch from source, change the translation, or work on
the project. Then you need a Steam copy of CHAOS;HEAD NOAH with the Committee of Zero patch installed,
Python and a few tools; see [BUILDING.md](BUILDING.md). Players never need any of that.
