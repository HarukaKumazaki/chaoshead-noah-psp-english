"""Build the English ISO.

Usage: build.py out.iso [--only SCENE ...] [--preview SCENE]
--preview copies SCENE's script over SCH00_001 so New Game starts there (testing only).
Steps: font -> scene scripts -> (images, eboot when present in work/ov) -> AFS -> ISO.
"""
import os, sys, subprocess, shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = os.path.join(ROOT, 'tools')
BASE_ISO = os.path.join(os.path.dirname(ROOT), 'Chaos;Head Noah (Japan).iso')
OV = os.path.join(ROOT, 'work', 'ov')


def run(*a):
    print('>', ' '.join(os.path.basename(x) if os.sep in x else x for x in a), flush=True)
    subprocess.check_call([sys.executable] + list(a), cwd=ROOT)


def main():
    subprocess.run(['powershell', '-NoProfile', '-Command', 'Stop-Process -Name PPSSPPWindows64 -Force -EA SilentlyContinue'])
    out = sys.argv[1]
    args = sys.argv[2:]
    preview = None
    if '--preview' in args:
        i = args.index('--preview'); preview = args[i + 1].upper(); del args[i:i + 2]
    images = '--images' in args
    args = [a for a in args if a != '--images']
    only = args[args.index('--only') + 1:] if '--only' in args else []
    if images or not os.path.isdir(os.path.join(OV, 'DATA0', 'BGL00.AFS.d')):
        # translated pictures: CoZ/official images, chat logs, terminal/ESO logs, questionnaire
        for tool in ('images.py', 'chatimg.py', 'logimg.py', 'miscimg.py'):
            run(os.path.join(T, tool), OV)
    if images or not os.path.isdir(os.path.join(OV, 'DATA0', 'OBJSY.AFS.d')):
        run(os.path.join(T, 'uitex.py'), OV)        # menu textures, CAUTION screen, help
    if images or not os.path.isdir(os.path.join(OV, 'DATA0', 'CHL00.AFS.d')):
        run(os.path.join(T, 'spriteimg.py'), OV)    # CoZ's English sign on Kazuki's sprites
    scene_dir = os.path.join(OV, 'DATA0', 'SCENE00.AFS.d')
    shutil.rmtree(scene_dir, ignore_errors=True)
    run(os.path.join(T, 'mkfont.py'), os.path.join(OV, 'DATA0', 'FONTS.AFS.d'))
    run(os.path.join(T, 'inject.py'), scene_dir, *(['--only'] + only if only else []))
    os.replace(os.path.join(scene_dir, '_report.tsv'), os.path.join(ROOT, 'work', 'report.tsv'))
    run(os.path.join(T, 'fullimg.py'), OV, os.path.join(ROOT, 'work', 'report.tsv'))   # full-screen text cards
    run(os.path.join(T, 'sysfiles.py'), scene_dir)
    run(os.path.join(T, 'musictr.py'), os.path.join(OV, 'DATA0', 'CONFIG.AFS.d', 'MUSIC.CFG'))
    if preview:
        src = os.path.join(scene_dir, preview + '.BIN')
        if not os.path.exists(src):            # untranslated script (e.g. the developer menu)
            src = os.path.join(ROOT, 'unpacked', 'DATA0', 'SCENE00.AFS.d', preview + '.BIN')
        shutil.copyfile(src, os.path.join(scene_dir, 'SCH00_001.BIN'))
    repl = []
    for a in ('DATA0', 'DATA1'):
        if os.path.isdir(os.path.join(OV, a)):
            dst = os.path.join(ROOT, 'work', a + '_build.AFS')
            run(os.path.join(T, 'afs_pack.py'), os.path.join(ROOT, 'unpacked', a), dst,
                os.path.join(OV, a), os.path.join(ROOT, 'iso', 'PSP_GAME', 'USRDIR', a + '.AFS'))
            repl.append('PSP_GAME/USRDIR/%s.AFS=%s' % (a, dst))
    for f in os.listdir(os.path.join(ROOT, 'work', 'usrdir')):
        repl.append('PSP_GAME/USRDIR/%s=%s' % (f, os.path.join(ROOT, 'work', 'usrdir', f)))
    gamedir = os.path.join(ROOT, 'work', 'psp_game')       # uitex.py output (ICON0.PNG)
    if os.path.isdir(gamedir):
        for f in os.listdir(gamedir):
            repl.append('PSP_GAME/%s=%s' % (f, os.path.join(gamedir, f)))
    movdir = os.path.join(ROOT, 'work', 'ov_mov')          # movies.py output (English movies)
    if os.path.isdir(movdir):
        for f in sorted(os.listdir(movdir)):
            repl.append('PSP_GAME/USRDIR/MOV/%s=%s' % (f, os.path.join(movdir, f)))
    eboot = os.path.join(ROOT, 'work', 'eboot', 'EBOOT_patched.BIN')
    run(os.path.join(T, 'eboot_tr.py'), os.path.join(ROOT, 'work', 'eboot', 'EBOOT_dec.ELF'), eboot)
    repl.append('PSP_GAME/SYSDIR/EBOOT.BIN=' + eboot)
    run(os.path.join(T, 'iso_patch.py'), BASE_ISO, out, *repl)


if __name__ == '__main__':
    main()
