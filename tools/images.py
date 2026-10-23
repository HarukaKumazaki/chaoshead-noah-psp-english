"""Replace PSP background / event CG images with CoZ's translated versions.

Usage: images.py ovroot        (writes KLZ files into ovroot/DATA0|DATA1/<archive>.d/)
CoZ images are 4:3 (1920x1440 / 3840x2880) like the PSP's 480x360 pictures, so a plain resize
maps them exactly (verified: mean pixel difference ~3-9 against the Japanese originals).
Multi-page BBS screens are located inside CoZ's tall scroll image by matching each PSP page.
"""
import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageChops, ImageStat
import klz, tim2

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COZ = os.path.join(ROOT, 'steam', 'c0data')
DIRS = [('DATA0', 'BGL00.AFS.d'), ('DATA1', 'BGL01.AFS.d'), ('DATA1', 'BGS00.AFS.d'), ('DATA1', 'BGS01.AFS.d')]


# still shown after a movie = the movie's last frame at y=44 of a 480x360 picture; taken from the
# English movie (movies.py output) so it matches CoZ's bg_mvpc01_end / bg_mveyes03_end
LAST_STILLS = ('INSERT07', 'INSERT10')


def movie_stills(ov):
    import subprocess
    n = 0
    for mv in LAST_STILLS:
        pmf = os.path.join(ROOT, 'work', 'ov_mov', mv + '.PMF')
        src = os.path.join(ROOT, 'unpacked', 'DATA0', 'BGL00.AFS.d', mv + '_LAST.KLZ')
        if not (os.path.exists(pmf) and os.path.exists(src)):
            continue
        png = os.path.join(ROOT, 'work', 'mv', mv + '_enlast.png')
        os.makedirs(os.path.dirname(png), exist_ok=True)
        subprocess.run([os.path.join(ROOT, 'tools', 'ffmpeg', 'ffmpeg.exe'), '-v', 'error', '-y',
                        '-i', pmf, '-update', '1', png], check=True)
        img, info = tim2.read(klz.decompress(open(src, 'rb').read()))
        img = img.convert('RGBA').copy()
        img.paste(Image.open(png).convert('RGBA').resize((480, 272)), (0, 44))
        od = os.path.join(ov, 'DATA0', 'BGL00.AFS.d'); os.makedirs(od, exist_ok=True)
        open(os.path.join(od, mv + '_LAST.KLZ'), 'wb').write(klz.compress(tim2.write(img, info)))
        n += 1
    return n


def coz_images():
    out = {}
    for f in os.listdir(COZ):
        n, e = os.path.splitext(f)
        if e in ('.webp', '.png') and not n.endswith('_jp'):
            out[n.lower()] = os.path.join(COZ, f)
    return out


def best_offset(page, tall):
    """vertical offset of a PSP page inside the scaled CoZ scroll image"""
    p = page.convert('L').resize((120, page.height // 4))
    t = tall.convert('L').resize((120, tall.height // 4))
    best = None
    for dy in range(0, t.height - p.height + 1):
        d = ImageStat.Stat(ImageChops.difference(t.crop((0, dy, 120, dy + p.height)), p)).mean[0]
        if best is None or d < best[0]:
            best = (d, dy * 4)
    return best


def convert(src_klz, coz_path, page_of=None):
    psp, info = tim2.read(klz.decompress(open(src_klz, 'rb').read()))
    w, h = info['w'], info['h']
    coz = Image.open(coz_path).convert('RGBA')
    if page_of is None:
        new = coz.resize((w, h), Image.LANCZOS)
    else:
        # the PSP splits each thread over N pages: cut CoZ's scroll at blank rows between posts into
        # N consecutive pieces (no repeats, nothing cut), each shown from the top of its page
        import numpy as np
        tall = coz.resize((w, round(coz.height * w / coz.width)), Image.LANCZOS)
        k, n = page_of[0] - 1, page_of[1]
        T = tall.height
        g = np.asarray(tall.convert('L'), float)
        bright = np.nonzero((g > 225).mean(0) > 0.6)[0]          # columns of the white post panel
        x0, x1 = (bright.min() + 4, bright.max() - 4) if len(bright) > 40 else (10, w - 10)
        gap = g[:, x0:x1].std(1) < 6
        cuts = [0]
        for j in range(1, n):
            target = min(round(j * T / n), cuts[-1] + h)
            lo, hi = max(cuts[-1] + 1, target - 90), min(T - 1, cuts[-1] + h)
            run = np.zeros(T, int)                 # length of the blank run ending at y
            for y in range(1, T):
                run[y] = run[y - 1] + 1 if gap[y] else 0
            cands = [y for y in range(lo, hi + 1) if run[y] >= 9 and not gap[min(T - 1, y + 1)]]   # end of a post gap
            cands = [y - 2 for y in cands] or [y for y in range(lo, hi + 1) if gap[y]]
            cuts.append(min(cands, key=lambda y: abs(y - target)) if cands else min(T, cuts[-1] + h))
        cuts.append(T)
        new = Image.new('RGBA', (w, h))
        tile = tall.crop((0, 0, 24, 48))   # plain brick from the left margin
        for y in range(0, h, 48):
            for x in range(0, w, 24):
                new.paste(tile, (x, y))
        new.paste(tall.crop((0, cuts[k], w, min(cuts[k + 1], cuts[k] + h))), (0, 0))
    # keep the original transparency (sprites/overlays)
    if psp.getextrema()[3][0] < 255:
        new.putalpha(psp.getchannel('A'))
    return klz.compress(tim2.write(new, info)), 'ok'


def tall_part(src_klz, coz_path, k, n):
    """part k of n: the English page scaled to the PSP width (no squashing), parts spread evenly from
    the top to the bottom so every line is shown (consecutive parts may overlap)"""
    psp, info = tim2.read(klz.decompress(open(src_klz, 'rb').read()))
    w, h = info['w'], info['h']
    coz = Image.open(coz_path).convert('RGBA')
    tall = coz.resize((w, round(coz.height * w / coz.width)), Image.LANCZOS)
    if tall.height <= h:
        new = psp.convert('RGBA').copy(); new.paste(tall, (0, 0))
    else:
        dy = 0 if n == 1 else round(k * (tall.height - h) / (n - 1))
        new = tall.crop((0, dy, w, dy + h))
    if psp.getextrema()[3][0] < 255:
        new.putalpha(psp.getchannel('A'))
    return klz.compress(tim2.write(new, info))


CHAPTER_CARDS = {
    '01': ('Chapter 1', 'Eyes in Eyes'), '02': ('Chapter 2', 'Click Me'), '03': ('Chapter 3', 'Shogun'),
    '04': ('Chapter 4', 'DI-sword'), '05': ('Chapter 5', 'Delusion'), '06': ('Chapter 6', 'Noah'),
    '07': ('Chapter 7', 'Psychopath'), '08': ('Chapter 8', 'Ir2'), '09': ('Chapter 9', 'Gigalomaniac'),
    '10': ('Chapter 10', 'Blue Sky'), '10_2': ('Chapter 10', 'Crying Sky'),
    'A': ('Ayase Route', 'A Contract of Blood to Seal Our Sin'), 'K': ('Kozue Route', 'The Sickness unto Slaughter'),
    'N': ('Nanami Route', 'Daydream'), 'R': ('Rimi Route', 'The Anima Image'),
    'S': ('Sena Route', 'Deus Ex Machina'), 'Y': ('Yua Route', 'Sun and Moon'),
}
SERIF = os.path.join(r'C:\program files (x86)\steam\steamapps\common\CHAOS;HEAD NOAH\languagebarrier\subs\fonts',
                     'IPAexMincho.ttf')


def chapter_card(label, title, w=480, h=360):
    """white serif text with a soft glow, centred on black like the original cards (text band y≈172-187)"""
    from PIL import ImageDraw, ImageFont, ImageFilter
    small = ImageFont.truetype(SERIF, 12)
    big = ImageFont.truetype(SERIF, 17)
    t2 = '[%s]' % title
    gap = 14
    w1, w2 = small.getlength(label), big.getlength(t2)
    if w1 + gap + w2 > w - 20:          # long route titles: shrink the title
        big = ImageFont.truetype(SERIF, 14); w2 = big.getlength(t2)
    x = (w - (w1 + gap + w2)) / 2
    base = 184
    txt = Image.new('L', (w, h), 0)
    d = ImageDraw.Draw(txt)
    d.text((x, base), label, font=small, fill=255, anchor='ls', stroke_width=1, stroke_fill=255)    # bold like the original
    d.text((x + w1 + gap, base), t2, font=big, fill=255, anchor='ls', stroke_width=1, stroke_fill=255)
    glow = txt.filter(ImageFilter.GaussianBlur(2)).point(lambda v: min(255, v * 2))
    out = Image.new('RGBA', (w, h), (0, 0, 0, 255))
    out.paste((140, 140, 140, 255), (0, 0), glow)
    out.paste((255, 255, 255, 255), (0, 0), txt)
    return out


def main():
    ov = sys.argv[1]
    coz = coz_images()
    # Steam's official English images (ID-named) matched to PSP names by match_eng.py; CoZ wins on overlap
    import json
    official = json.load(open(os.path.join(ROOT, 'work', 'eng_map.json')))
    done, skipped = 0, []
    for arch, sub in DIRS:
        d = os.path.join(ROOT, 'unpacked', arch, sub)
        for f in sorted(os.listdir(d)):
            if not f.upper().endswith('.KLZ'):
                continue
            n = f[:-4].lower()
            page = None
            m_tall = re.fullmatch(r'(bg\d+_\d+_\d)([abc])', n)
            if m_tall and m_tall.group(1) in coz:
                # one tall PC page shown on the PSP as scroll parts A/B/C: cut each part from CoZ's tall
                # English page at the scroll position that matches the Japanese part's layout
                parts = sorted(x[:-4].lower()[-1] for x in os.listdir(d)
                               if re.fullmatch(re.escape(m_tall.group(1)) + r'[abc]\.klz', x.lower()))
                data = tall_part(os.path.join(d, f), coz[m_tall.group(1)], parts.index(m_tall.group(2)), len(parts))
                od = os.path.join(ov, arch, sub); os.makedirs(od, exist_ok=True)
                open(os.path.join(od, f), 'wb').write(data); done += 1
                continue
            if n == 'bg042_04_2' and 'bg042_01_2' in coz:     # portrait view of Shogun's link list
                psp, info = tim2.read(klz.decompress(open(os.path.join(d, f), 'rb').read()))
                new = Image.open(coz['bg042_01_2']).convert('RGBA').resize((info['w'], info['h']), Image.LANCZOS)
                od = os.path.join(ov, arch, sub); os.makedirs(od, exist_ok=True)
                open(os.path.join(od, f), 'wb').write(klz.compress(tim2.write(new, info))); done += 1
                continue
            if n in coz:
                src = coz[n]
            elif f[:-4] in official:
                src = os.path.join(ROOT, official[f[:-4]])
            else:
                m = re.fullmatch(r'(bbs_\d\d_\d\d\da)(\d)', n)   # BBS pages A1..A4 -> one scroll image
                if not (m and m.group(1) in coz):
                    continue
                cnt = len([x for x in os.listdir(d) if re.fullmatch(re.escape(f[:-5]) + r'\d\.KLZ', x, re.I)])
                src, page = coz[m.group(1)], (int(m.group(2)), cnt)
            data, why = convert(os.path.join(d, f), src, page)
            if data is None:
                skipped.append((f, why)); continue
            od = os.path.join(ov, arch, sub)
            os.makedirs(od, exist_ok=True)
            open(os.path.join(od, f), 'wb').write(data)
            done += 1
    # chapter title cards: typeset in English (CoZ animates these as movies on Steam)
    for key, (label, title) in CHAPTER_CARDS.items():
        name = 'CHAPTER_%s.KLZ' % key
        for arch, sub in DIRS:
            src = os.path.join(ROOT, 'unpacked', arch, sub, name)
            if not os.path.exists(src):
                continue
            psp, info = tim2.read(klz.decompress(open(src, 'rb').read()))
            od = os.path.join(ov, arch, sub)
            os.makedirs(od, exist_ok=True)
            open(os.path.join(od, name), 'wb').write(klz.compress(tim2.write(chapter_card(label, title).resize((info['w'], info['h']), Image.LANCZOS), info)))
            done += 1
    done += movie_stills(ov)
    print('images replaced:', done, 'skipped:', skipped)


if __name__ == '__main__':
    main()
