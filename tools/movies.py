"""English movies: CoZ's re-edited videos (English credits / on-screen text) or the PSP video,
with CoZ's song/dialogue subtitles burned in, encoded as PSP-compatible H.264 and remuxed with
the original ATRAC3plus audio (frame counts match the retail PMFs exactly).

Usage: movies.py outdir [NAME ...]
"""
import os, sys, subprocess, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pmf, usm_demux

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FF = os.path.join(ROOT, 'tools', 'ffmpeg', 'ffmpeg.exe')
FFPROBE = os.path.join(ROOT, 'tools', 'ffmpeg', 'ffprobe.exe')
MOV = os.path.join(ROOT, 'iso', 'PSP_GAME', 'USRDIR', 'MOV')
C0 = os.path.join(ROOT, 'steam', 'c0data')
SUBS = r'C:\program files (x86)\steam\steamapps\common\CHAOS;HEAD NOAH\languagebarrier\subs'
WORK = os.path.join(ROOT, 'work', 'mv')

# PMF -> (video source: CoZ usm name or None for the PSP video, CoZ subtitle script or None)
MOVIES = {
    'OP': (None, 'mvoppsp'),
    'DEMO': (None, 'mvdemo'),
    'END01': ('mvend01', None),
    'END02': ('mvend02', 'mvend02'),
    'END03': ('mvend03', 'mvend03'),
    'END04': ('mvend04', 'mvend04'),
    'END05': ('mvend05', 'mvend05'),
    'END06': ('mvend06', 'mvend06'),
    'END07': ('mvend07', 'mvend07'),
    'END08': ('mvend08', 'mvend08'),
    'END09': ('mvend09', 'mvend09'),
    'INSERT01': ('mvinter01', 'mvinter01'),
    'INSERT02': ('mvgaya', None),
    'INSERT07': ('mvpc01', None),
    'INSERT08': ('mvpc02', None),
    'INSERT09': ('mveyes01', None),
    'INSERT10': ('mveyes03', None),
    'INSERT12': ('mvsword03a', 'mvsword03a'),
    'INSERT05': (None, None),          # news ticker: re-typeset in English (ticker())
}

TICKER = ('〈New Gen〉 A sixth case?…   On the 28th, the body of a woman in her twenties was found under '
          'unusual circumstances in the Shibuya River, Shibuya Ward. She had eaten the flesh of her own right hand '
          'and died of suffocation after choking on the bones.')
TICK_WIN = (92, 88, 388, 134)          # screen area the ticker crosses (video pixels)
TICK_FRAMES = (3, 520)                 # first char enters at the right .. last char leaves at the left


def ticker_frames(orig, n):
    """original frames with the Japanese crawl inpainted (vertical interpolation across the band)
    and the English crawl composited -> PNG sequence pattern"""
    import numpy as np
    from PIL import Image
    over = ticker(n)
    d = os.path.join(WORK, 'ticker_out'); os.makedirs(d, exist_ok=True)
    raw = subprocess.run([FF, '-v', 'error', '-i', orig, '-frames:v', str(n), '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                         capture_output=True, check=True).stdout
    x0, y0, x1, y1 = TICK_WIN
    fr = np.frombuffer(raw, np.uint8).reshape(-1, 272, 480, 3)
    w = np.linspace(0, 1, y1 - y0 + 2)[1:-1][:, None, None]
    for k in range(n):
        f = fr[k].astype(float).copy()
        top, bot = f[y0 - 1, x0:x1], f[y1, x0:x1]
        f[y0:y1, x0:x1] = top[None] * (1 - w) + bot[None] * w
        im = Image.fromarray(f.clip(0, 255).astype(np.uint8)).convert('RGBA')
        im.alpha_composite(Image.open(over % k), (x0, y0))
        im.convert('RGB').save(os.path.join(d, 'f%04d.png' % k))
    return os.path.join(d, 'f%04d.png')


def ticker(n):
    """per-frame RGBA overlays (window-sized) of the English crawl, tilted like the screen"""
    from PIL import Image, ImageDraw, ImageFont, ImageFilter
    d = os.path.join(WORK, 'ticker'); os.makedirs(d, exist_ok=True)
    font = ImageFont.truetype(os.path.join(SUBS, 'fonts', 'VL-PGothic-Regular.ttf'), 15)
    tw = int(font.getlength(TICKER)) + 4
    x0, y0, x1, y1 = TICK_WIN
    W, H = x1 - x0, y1 - y0
    f0, f1 = TICK_FRAMES
    speed = (tw + W) / (f1 - f0)
    strip = Image.new('L', (tw, 24), 0)
    ImageDraw.Draw(strip).text((2, 18), TICKER, font=font, fill=255, anchor='ls')
    glow = strip.filter(ImageFilter.GaussianBlur(2.2))
    for k in range(n):
        frame = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        x = int(round(W - speed * (k - f0)))
        if k >= f0 and x > -tw:
            canvas = Image.new('RGBA', (W + 40, H + 40), (0, 0, 0, 0))
            g = Image.new('RGBA', strip.size, (200, 210, 230, 0)); g.putalpha(glow.point(lambda v: min(255, v * 2) // 2))
            t = Image.new('RGBA', strip.size, (238, 238, 238, 0)); t.putalpha(strip)
            canvas.alpha_composite(g, (x + 20, 20 + 7)); canvas.alpha_composite(t, (x + 20, 20 + 7))
            canvas = canvas.rotate(-2.3, resample=Image.BICUBIC, center=(W // 2 + 20, H // 2 + 20))
            frame = canvas.crop((20, 20, 20 + W, 20 + H))
            # soft fade at the screen's left/right edges
            m = Image.linear_gradient('L').rotate(90).resize((8, H))
            a = frame.getchannel('A')
            a.paste(Image.composite(a.crop((0, 0, 8, H)), Image.new('L', (8, H), 0), m.transpose(Image.FLIP_LEFT_RIGHT)), (0, 0))
            frame.putalpha(a)
        frame.save(os.path.join(d, 'k%04d.png' % k))
    return os.path.join(d, 'k%04d.png')

X264 = ('bframes=0:ref=1:keyint=60:min-keyint=10:scenecut=40:aud=1:nal-hrd=vbr:pic-struct=1:'
        'vbv-maxrate=2500:vbv-bufsize=480:crf=20:weightp=0:'
        'colorprim=smpte170m:transfer=smpte170m:colormatrix=smpte170m:sar=1/1')


def frames(path):
    out = subprocess.run([FFPROBE, '-v', 'error', '-count_packets', '-select_streams', 'v', '-show_entries',
                          'stream=nb_read_packets', '-of', 'csv=p=0', path], capture_output=True, text=True).stdout
    return int(out.strip())


def ass_for_psp(name):
    """CoZ script minus the auto-generated furigana lines (unreadable at 272p)"""
    src = os.path.join(SUBS, name + '.ass')
    lines = open(src, encoding='utf-8-sig').read().splitlines()
    out = [ln for ln in lines if not (ln.startswith(('Dialogue:', 'Comment:')) and '-furigana' in ln.split(',')[3])]
    dst = os.path.join(WORK, name + '_psp.ass')
    open(dst, 'w', encoding='utf-8').write('\n'.join(out) + '\n')
    return dst


def _esc(p):
    return p.replace('\\', '/').replace(':', '\\:').replace("'", "\\'").replace(';', '\\;')


def build(name, outdir):
    src, sub = MOVIES[name]
    orig = os.path.join(MOV, name + '.PMF')
    n = frames(orig)
    if src:
        sfv = os.path.join(WORK, src + '.sfv')
        if not os.path.exists(sfv):
            usm_demux.demux(os.path.join(C0, src + '.usm'), os.path.join(WORK, src))
            os.replace(os.path.join(WORK, src + '.sfv'), sfv)
        inp = ['-r', '30000/1001', '-i', sfv]
    else:
        inp = ['-i', orig]
    vf = []
    if name == 'INSERT05':
        inp = ['-framerate', '30000/1001', '-i', ticker_frames(orig, n)]
        vf = []
    elif sub:
        vf.append("subtitles='%s':fontsdir='%s'" % (_esc(ass_for_psp(sub)), _esc(os.path.join(SUBS, 'fonts'))))
    if True:
        if src:          # burn at 1080p, then scale down (sharper text)
            vf.append('scale=480:272:flags=lanczos')
        elif sub:
            vf.insert(0, 'scale=1920:1080:flags=bicubic')
            vf.append('scale=480:272:flags=lanczos')
        filt = ['-vf', ','.join(vf)] if vf else []
    es = os.path.join(WORK, name + '.h264')
    subprocess.check_call([FF, '-v', 'error', '-y'] + inp + filt + ['-frames:v', str(n),
                           '-an', '-c:v', 'libx264', '-profile:v', 'main', '-level', '2.1', '-pix_fmt', 'yuv420p',
                           '-r', '30000/1001', '-x264-params', X264, '-f', 'h264', es])
    data = pmf.mux(pmf.read_orig(orig), open(es, 'rb').read(), n)
    open(os.path.join(outdir, name + '.PMF'), 'wb').write(data)
    print(name, 'frames', n, 'size %.1f MB (was %.1f)' % (len(data) / 1e6, os.path.getsize(orig) / 1e6), flush=True)


def main():
    outdir = sys.argv[1]
    os.makedirs(outdir, exist_ok=True); os.makedirs(WORK, exist_ok=True)
    for name in (sys.argv[2:] or MOVIES):
        build(name, outdir)


if __name__ == '__main__':
    main()
