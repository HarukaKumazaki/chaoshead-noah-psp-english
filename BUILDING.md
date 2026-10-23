# Building the English ISO from source

Players don't need any of this: use the release and [INSTALL.md](INSTALL.md).
This page is for rebuilding the patch yourself or changing it.

## Requirements

- Windows 10/11 (the build calls PowerShell and Windows builds of ffmpeg / PPSSPP)
- Python 3.10 or newer, with `pip install pillow numpy websocket-client`
- The Japanese PSP ISO, unmodified: `Chaos;Head Noah (Japan).iso` (ULJM05692)
- CHAOS;HEAD NOAH on Steam, with the Committee of Zero patch 1.1.3 installed (the `languagebarrier` folder)
- `tools/ffmpeg/ffmpeg.exe` and `ffprobe.exe` (any recent ffmpeg build with libx264)
- `tools/ppsspp/` with a portable PPSSPP (for the EBOOT dump and for testing)

## Folder layout

Put the repository folder next to the Japanese ISO:

```
Downloads/
  Chaos;Head Noah (Japan).iso
  CHN_PSP_EN/          <- this repository
```

`build.py` reads `../Chaos;Head Noah (Japan).iso` and never modifies it. If Steam is not in the default
location, set `CHN_STEAM_DIR` to the `CHAOS;HEAD NOAH` folder.

## 1. Prepare the inputs (once)

```bat
python tools\setup.py "..\Chaos;Head Noah (Japan).iso" "C:\Program Files (x86)\Steam\steamapps\common\CHAOS;HEAD NOAH"
```

This fills `iso/` (the ISO's files), `unpacked/` (the AFS archives) and `steam/` (CoZ's text and
images from the Steam release).

## 2. Dump the decrypted EBOOT (once)

The PSP's `EBOOT.BIN` is encrypted. PPSSPP can save a decrypted copy:

1. In `tools/ppsspp/memstick/PSP/SYSTEM/ppsspp.ini`, under `[General]`, set `DumpDecryptedEboots = True`.
2. Start the Japanese ISO in that PPSSPP once (the title screen is enough).
3. Copy `tools/ppsspp/memstick/PSP/SYSTEM/DUMP/ULJM05692_EBOOT.BIN` to `work/eboot/EBOOT_dec.ELF`.

## 3. English movies (once, ~10 minutes)

```bat
python tools\movies.py work\ov_mov
```

## 4. Build

```bat
python tools\build.py "work\Chaos;Head Noah (English).iso" --images
```

`--images` regenerates every translated picture and texture; later builds can leave it out to reuse them.
A full build takes a few minutes. Useful extras:

- `--preview SCH01_002`: test build where New Game starts in that scene
- `tools\ppdbg.py`: drives PPSSPP through its debugger API for automated testing

## 5. Make the release patch

```bat
python patcher\makepatch.py "..\Chaos;Head Noah (Japan).iso" "work\Chaos;Head Noah (English).iso" release
```

This writes `release/ChaosHeadNoah_PSP_EN.patch.bin` and `.patch.txt`. Then

```bat
python patcher\package.py 1.0.1
```

puts the patchers, the patch and `README.txt` (from INSTALL.md) in `dist/CHN-PSP-English-1.0.1.zip`.

## Testing

`tools/test/tour.py` presses buttons in a running PPSSPP and takes screenshots, for example
`python tools	est	our.py circle wait:4 circle wait:4 shot:title`. Screenshots go to `work/shots/`.
`run_to_hl.py` advances until a Tips word is highlighted; `slottrace.py` logs which glyph slots a screen
draws into (useful when menu text overlaps).

## How it works

See [NOTES.md](NOTES.md) for the file formats, engine limits and the code patches applied to the EBOOT.
