# Installing the English patch

## What you need

- The **Japanese PSP ISO of CHAOS;HEAD NOAH** (ULJM05692), unmodified, as a `.iso` file
  (1,416,232,960 bytes). If yours is a `.cso`, convert it back to `.iso` first.
- About 1.5 GB of free disk space for the new English ISO.
- Nothing else. The patchers use only what Windows or Linux already includes.

The original ISO is never changed. The patcher writes a new file, `Chaos;Head Noah (English).iso`,
next to it.

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
