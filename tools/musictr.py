"""Music Gallery (CONFIG.AFS/MUSIC.CFG) in English.

Layout: 46 track records (32 bytes from 0xA0): +16 lyric table, +20 title, +24/+28 credit lines.
Lyric tables: 16-byte entries (u16 time, u16 flag, u32 0x300, u32 text, u32 0) up to 0x1930.
All text lives in a cp932 pool from 0x1940 and is referenced by absolute offsets; the pool is
rebuilt in English and every pointer rewritten.

Lyrics come from CoZ's song subtitles (kanji karaoke line -> time-aligned translation);
lines CoZ never subtitled (music-gallery-only songs) use LYRICS below.

Usage: musictr.py out.CFG
"""
import os, sys, struct, re, unicodedata, difflib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import enc, cozlyrics

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'unpacked', 'DATA0', 'CONFIG.AFS.d', 'MUSIC.CFG')
POOL = 0x1940
TAB_END = 0x1930
MAXW = 600

TITLES = {
    'Ｉ’ｍ ｒｏｕｎｄｅｒ': "I'm rounder",
    'クライ': 'Kurai',
    'グラジオール': 'Gladiol',
    '罪過に契約の血を': 'A Contract of Blood to Seal Our Sin',
    '心の闇を切り裂いて': 'Tear Apart the Darkness in Your Heart',
    'ちいさな声に気づいて': 'Hear My Tiny Voice',
    'アレルイヤの福音～使徒からの手紙第二編より～':
        'The Gospel of Hallelujah ~Excerpt from the Second Apostolic Letter~',
    '密教の首飾り～グラジオール列王記邪心編より～':
        'The Necklace of Vajrayana ~Gladiol Book of the Wicked-Hearted King~',
    'イノセンス～殺戮の創世記詩編最終章より～':
        'Innocence ~Finale of the Genesis Psalms of Slaughter~',
    'ｆａｋｅ ｍｅ': 'Fake Me', 'Ａ ＷＩＬＬ': 'A Will', 'Ｆｉｎｄ ｔｈｅ ｂｌｕｅ': 'Find the Blue',
}
NAMES = {
    '阿保 剛': 'Abo Takeshi', '磯江 俊道': 'Isoe Toshimichi', '大山 曜': 'Ohyama Yo', '神保 伸太郎': 'Jinbo Shintaro',
    'いとうかなこ': 'Itou Kanako', '志倉千代丸': 'Shikura Chiyomaru', '江幡 育子': 'Ebata Ikuko',
    'ファンタズム （FES cv.榊原 ゆい）': 'Phantasm (FES cv. Sakakibara Yui)', '林 達志': 'Hayashi Tatsushi',
    '咲畑 梨深 （cv.喜多村 英梨）': 'Sakihata Rimi (cv. Kitamura Eri)', '橋詰 亮子': 'Hashizume Ryoko',
    '勝 誠二': 'Katsu Seiji', '西條 七海 （cv.宮崎 羽衣）': 'Nishijou Nanami (cv. Miyazaki Ui)',
    '葉月みこ': 'Hazuki Miko', '林 良太': 'Hayashi Ryota', '幡手 康隆': 'Hatate Yasutaka',
    '楠 優愛 （cv.たかはし 智秋）': 'Kusunoki Yua (cv. Takahashi Chiaki)', '絵莉': 'Eri', '酒井 陽一': 'Sakai Yoichi',
    '岸本 あやせ （cv.榊原 ゆい）': 'Kishimoto Ayase (cv. Sakakibara Yui)', 'TK-J': 'TK-J',
    '蒼井 セナ （cv.生天目 仁美）': 'Aoi Sena (cv. Namatame Hitomi)', '吉野 麻希': 'Yoshino Maki',
    '沢村 竣': 'Sawamura Shun', 'Orca Okinaka': 'Orca Okinaka', '折原 梢 （cv.辻 あゆみ）': 'Orihara Kozue (cv. Tsuji Ayumi)',
    '夏蓮': 'Karen', '平川 達也': 'Hirakawa Tatsuya', '南 利一': 'Minami Riichi',
}
ROLES = [('作詞／作曲', 'Wr / Comp'), ('作曲／編曲', 'Comp / Arr'), ('作詞', 'Wr'), ('作曲', 'Comp'), ('編曲', 'Arr'),
         ('歌', 'Vo')]

# lyric lines CoZ has no subtitle for (my translations)
from music_lyrics import LYRICS
REVIEW = []


def norm(t):
    t = unicodedata.normalize('NFKC', t)
    return re.sub(r'[\s・、。…―─\-!?「」『』（）()~～.]', '', t).lower()


def credit(t):
    parts = re.split('　', t)
    out = []
    for p in parts:
        m = re.match(r'(.+?)：(.+)', p)
        if not m:
            return None
        role, name = m.groups()
        role = dict(ROLES).get(role)
        name = NAMES.get(name.strip())
        if not role or not name:
            return None
        out.append('%s: %s' % (role, name))
    return '   '.join(out)


def title(t):
    if t in TITLES:
        return TITLES[t]
    n = unicodedata.normalize('NFKC', t)
    if n.isascii():
        return n
    return None


def split_half(en):
    """one English line covering two Japanese lines -> two halves at a natural break"""
    words = en.split(' ')
    if len(words) < 2:
        return en, ''
    best = None
    for i in range(1, len(words)):
        a, b = ' '.join(words[:i]), ' '.join(words[i:])
        score = abs(len(a) - len(b)) - (12 if a[-1] in ',.;:!?—…' else 0)
        if best is None or score < best[0]:
            best = (score, a, b)
    return best[1], best[2]


def lyric_db():
    """(normalised Japanese, English) for every run of 1-3 consecutive CoZ karaoke lines;
    a single line whose English also covers its neighbour gets its half of that English"""
    exact, items = {}, []

    def add(n, en):
        if n not in exact:
            exact[n] = en; items.append((n, en))
    for name, prs in sorted(cozlyrics.all_pairs().items()):
        for k in range(len(prs)):
            for w in (1, 2, 3):
                win = prs[k:k + w]
                if len(win) < w:
                    break
                ens = []
                for jp, en in win:
                    if en not in ens:
                        ens.append(en)
                outer = (k > 0 and prs[k - 1][1] == win[0][1]) or (k + w < len(prs) and prs[k + w][1] == win[-1][1])
                n = norm(''.join(jp for jp, en in win))
                if not outer:
                    add(n, ' '.join(ens))
                elif w == 1:
                    first = k + 1 < len(prs) and prs[k + 1][1] == win[0][1]
                    h = split_half(win[0][1])
                    add(n, h[0] if first else h[1])
    return exact, items


def lookup(jp, exact, items):
    n = norm(jp)
    if not jp.strip():
        return ''
    if jp in LYRICS:
        return LYRICS[jp]
    if n in exact:
        return exact[n]
    best = max(items, key=lambda it: difflib.SequenceMatcher(None, n, it[0]).ratio())
    r = difflib.SequenceMatcher(None, n, best[0]).ratio()
    if r >= 0.85:
        REVIEW.append((round(r, 2), jp, best[1]))
        return best[1]
    return None


def main():
    d = bytearray(open(SRC, 'rb').read())

    def s_at(o):
        return bytes(d[o:d.index(b'\0', o)]).decode('cp932')
    ptrs = []                                      # (field offset, kind)
    recs = list(range(0xa0, 0x660, 32))
    tabs = sorted({struct.unpack_from('<I', d, r + 16)[0] for r in recs} - {0})
    for r in recs:
        for k, f in enumerate((20, 24, 28)):
            if struct.unpack_from('<I', d, r + f)[0]:
                ptrs.append((r + f, 'title' if k == 0 else 'credit'))
    bounds = tabs + [TAB_END]
    for i, t in enumerate(tabs):
        for e in range(t, bounds[i + 1], 16):
            if struct.unpack_from('<I', d, e + 8)[0]:
                ptrs.append((e + 8, 'lyric'))
    exact, items = lyric_db()
    pool = bytearray(); where = {}; missing = []; wide = []
    for off, kind in ptrs:
        jp = s_at(struct.unpack_from('<I', d, off)[0])
        en = title(jp) if kind == 'title' else credit(jp) if kind == 'credit' else lookup(jp, exact, items)
        if en is None:
            missing.append((kind, jp)); en = jp
            raw = jp.encode('cp932')
        else:
            if enc.width(en) > MAXW:
                wide.append((kind, en, enc.width(en)))
            raw = enc.encode(en)
        if raw not in where:
            where[raw] = POOL + len(pool); pool += raw + b'\0'
        struct.pack_into('<I', d, off, where[raw])
    out = bytes(d[:POOL]) + bytes(pool)
    out += bytes(-len(out) % 4)
    open(sys.argv[1], 'wb').write(out)
    print('MUSIC.CFG: %d strings, %d untranslated, %d too wide, %d -> %d bytes' %
          (len(ptrs), len(missing), len(wide), len(d), len(out)))
    for m in missing:
        print('  missing', m)
    for w in wide:
        print('  wide', w)
    for r in REVIEW:
        print('  fuzzy', r)


if __name__ == '__main__':
    main()
