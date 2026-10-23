"""Build English PSP scene scripts from the CoZ Steam text.

Usage: inject.py outdir [--only NAME ...] [--report report.tsv]

For every SCENE00 script, PSP lines are aligned to CoZ Japanese segments (align.py),
the matching English segment is converted to PSP markup, re-wrapped for the PSP
message box and written back into the script's string pool.
"""
import sys, os, re, glob, json, unicodedata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pspscr import Script
import msb
import align
import enc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SC = os.path.join(ROOT, 'unpacked', 'DATA0', 'SCENE00.AFS.d')

CODE = r'%(?:LC|LE|FS|FE|N|K|P|O\d{3}|T\d{3}|S\d{3}|t\d{3}|n|p)'
# original line = lead codes, optional 【name】, more codes, body, tail codes
LINE = re.compile(r'^((?:%s)*)(?:【([^】]*)】)?((?:%s)*)(.*?)((?:%s)*)$' % (CODE, CODE, CODE), re.S)


def seg_to_parts(seg):
    """English msb segment -> (name or None, list of (kind, text)) where kind is
    'text', 'nl' (forced newline), 'wait' (mid-line pause, frames), 'ruby' (base, ruby)."""
    name = None
    parts = []
    buf = []
    mode = 'text'
    rb_base = []
    rb_txt = []

    def flush():
        if buf:
            parts.append(('text', ''.join(buf))); buf.clear()

    for t in seg:
        if t[0] == 'g':
            ch = msb.CH[t[1]] if t[1] < len(msb.CH) else msb.EXT.get(t[1], '?')
            if mode == 'name': name = (name or '') + ch
            elif mode == 'rb': rb_base.append(ch)
            elif mode == 'rt': rb_txt.append(ch)
            else: buf.append(ch)
            continue
        c = t[1]
        if c == 0x01: flush(); mode = 'name'; name = ''
        elif c == 0x02: mode = 'text'
        elif c == 0x00: flush(); parts.append(('nl', None))
        elif c == 0x09: flush(); mode = 'rb'; rb_base = []; rb_txt = []
        elif c == 0x0A: mode = 'rt'
        elif c == 0x0B:
            parts.append(('ruby', (''.join(rb_base), ''.join(rb_txt)))); mode = 'text'
        elif c == 0x07: flush(); parts.append(('wait', t[2][0] if t[2] else 0))
        elif c == 0x04:
            flush(); parts.append(('cend' if t[2] in (b'\x80', b'') else 'cstart', t[2]))
    flush()
    # trailing forced newlines carry no meaning on PSP
    while parts and parts[-1][0] == 'nl':
        parts.pop()
    return name, parts


def vlen(t):
    """visible glyph count (italic markers and highlight placeholders take no space)"""
    return len(t) - sum(t.count(c) for c in (chr(14), chr(15), chr(1), chr(2)))


def wrap(parts, width, first_indent=0, hard_nl=False, first_chars=0):
    """Greedy word wrap. Returns list of lines; each line is a list of PSP-encoded chunks.
    hard_nl keeps the source's line breaks (TIPS paragraphs); otherwise they become spaces."""
    lines = [[]]
    cur = first_indent
    nch = first_chars
    nby = first_chars
    maxc = getattr(enc, 'MAX_CHARS', 10 ** 6)
    maxb = getattr(enc, 'MAX_BYTES', 10 ** 6)

    def nb(t):
        return len(enc.encode(t))

    def newline():
        nonlocal cur, nch, nby
        lines.append([]); cur = 0; nch = 0; nby = 0

    for kind, val in parts:
        if kind == 'nl' and hard_nl:
            newline()
            continue
        if kind == 'nl':
            # CoZ breaks were laid out for 1280px; keep them only as soft spaces
            if lines[-1] and cur:
                lines[-1].append(' '); cur += enc.width(' '); nch += 1; nby += 2
            continue
        if kind == 'wait':
            lines[-1].append('%%T%03d' % val)
            continue
        if kind in ('cstart', 'cend'):
            lines[-1].append('\x01' if kind == 'cstart' else '\x02')   # placeholders, zero width
            continue
        if kind == 'ruby':
            base, rt = val
            w = enc.width(base)
            if (cur + w > width or nch + vlen(base) > maxc) and cur: newline()
            lines[-1].append('{%s}[%s]' % (base, rt)); cur += w; nch += vlen(base)
            continue
        for word in re.findall(r'\S+|\s+', val):
            if word.isspace():
                sp = ' ' if ' ' in word else ' '          # keep the thin space of tight pages
                if cur: lines[-1].append(sp); cur += enc.width(sp); nch += 1; nby += 2
                continue
            w = enc.width(word)
            if (cur + w > width or nch + vlen(word) > maxc or nby + nb(word) > maxb) and cur:
                # drop the trailing space before breaking
                while lines[-1] and lines[-1][-1] in (' ', ' '):
                    lines[-1].pop()
                newline()
            if w > width:  # overlong token: hard split
                for ch in word:
                    cw = enc.width(ch)
                    if cur + cw > width or nch + vlen(ch) > maxc or nby + nb(ch) > maxb: newline()
                    lines[-1].append(ch); cur += cw; nch += vlen(ch); nby += nb(ch)
                continue
            lines[-1].append(word); cur += w; nch += vlen(word); nby += nb(word)
    while lines and not lines[-1]:
        lines.pop()
    for ln in lines:
        while ln and ln[-1] in (' ', ' '):
            ln.pop()
    return [''.join(l) for l in lines]


# speaker key -> {CoZ English name: count}; written to work/name_votes.json for DATA.BIN
NAME_VOTES = {}

# strings with no CoZ counterpart (character viewer menu etc.)
MANUAL = {
    '次へ': 'Next', '☆全部☆': '☆All☆', 'デフォ': 'Default', '戻る': 'Back',
    '服装Ａ': 'Outfit A', '服装Ｂ': 'Outfit B', '服装Ｃ': 'Outfit C', '服装Ｄ': 'Outfit D', '服装Ｅ': 'Outfit E',
    'No:%d-%d　%s/%s/%s/表情%D%K%P': 'No:%d-%d %s/%s/%s/Expression %D%K%P',
    # choice menus (opcode 0x1B): delusion triggers, then developer branch/viewer menus
    'ポジティブ妄想': 'Positive Delusion', 'ネガティブ妄想': 'Negative Delusion', '妄想しない': 'Neutral',
    'どちらでもない': 'Neither', 'グランドフィナーレ': 'Grand Finale', 'バッドエンド': 'Bad End',
    'ノーマルエンド': 'Normal End', 'タイトルから': 'From Title', '十章頭から': 'From Start of Ch.10',
    '未使用': 'Unused', 'Ａ': 'A', 'Ｂ': 'B', '大': 'Large', '小': 'Small', 'アニメ無し': 'No Animation',
    'ＲＯＯＭ３６有り': 'ROOM36: On', 'ＲＯＯＭ３６無し': 'ROOM36: Off',
    '３章あやせ妄想しない分岐有り': 'Went Neutral During Chapter 3’s Ayase Delusion',
    '３章あやせ妄想しない分岐無し': 'Did Not Go Neutral During Chapter 3’s Ayase Delusion',
    '１章エンドフラグ①有り': 'Ch.1 End Flag 1: On', '１章エンドフラグ①無し': 'Ch.1 End Flag 1: Off',
    '７章エンドフラグ①有り': 'Ch.7 End Flag 1: On', '７章エンドフラグ①無し': 'Ch.7 End Flag 1: Off',
    'あやせ白下着': 'Ayase: White Underwear', 'あやせスク水': 'Ayase: School Swimsuit', 'あやせ制服': 'Ayase: Uniform',
    '５章梨深Ｙシャツ': 'Ch.5 Rimi: Dress Shirt', '５章梨深私服': 'Ch.5 Rimi: Casual',
    '葉月メガネ有り': 'Hazuki: Glasses', '葉月メガネ無し': 'Hazuki: No Glasses',
    '梨深ソファあり': 'Rimi on Sofa', '梨深ソファなし': 'Rimi off Sofa',
    '競泳水着': 'Racing Swimsuit', 'スクール': 'School', 'それ以外': 'Other', '服装Ｆ': 'Outfit F',
    'ポーズ01': 'Pose 01', 'ポーズ02': 'Pose 02', 'ポーズ03': 'Pose 03', 'ポーズ04': 'Pose 04',
    'ポーズ05': 'Pose 05', 'ポーズ06': 'Pose 06',
    '梨深': 'Rimi', '優愛': 'Yua', 'セナ': 'Sena', '梢': 'Kozue', 'あやせ': 'Ayase', '七海': 'Nanami', '将軍': 'Shogun',
    '咲畑梨深': 'Sakihata Rimi', '西條七海': 'Nishijou Nanami', '楠優愛': 'Kusunoki Yua', '楠美愛': 'Kusunoki Mia',
    '岸本あやせ': 'Kishimoto Ayase', '蒼井セナ': 'Aoi Sena', '折原梢': 'Orihara Kozue', '星来': 'Seira',
    '三住大輔': 'Misumi Daisuke', '判安二': 'Ban Yasuji', '諏訪護': 'Suwa Mamoru', '百瀬克子': 'Momose Katsuko',
    '高科史男': 'Takashina Fumio', '葉月志乃': 'Hazuki Shino', '波多野一成': 'Hatano Kazunari', '野呂瀬玄一': 'Norose Gen’ichi',
    '圭　　': 'Kei', 'ノゾミ': 'Nozomi', 'トモミ': 'Tomomi', 'ことり': 'Kotori', 'アキラ': 'Akira', 'ミズキ': 'Mizuki',
    'ヒナノ': 'Hinano', 'マリィ': 'Marie', 'ネココ': 'Nekoko', '久遠　': 'Kuon', 'おババ': 'Granny', 'エルナ': 'Erna',
    'レイナ': 'Reina', '雑魚　': 'Mook',
    # PSP-only line splits / lines CoZ reworded; wording follows CoZ's surrounding text
    '【七海】「あ～～～～っ！！！」%K%P': '【Nanami】“Aaaaaaahhh!”%K%P',
    '【七海】「バカ～～～～～！」%K%P': '【Nanami】“\x0eJeeeeeeeeeeeeeeeeeeeeerk!\x0f”%K%P',
    '【梨深】「ん～～～」%K%P': '【Rimi】“Hup... Nnnnn...! Aaah...”%K%P',
    '次の瞬間には、再生していた。%K%P': 'In the very next moment, it had regenerated.%K%P',
    '訳が分からなかった。%K%P': 'I couldn’t comprehend it.%K%P',
    '【梨深】%N%N%N「……殺さなくちゃ……いけないの」∬∬∬∬∬%T300%P': '【Rimi】%N%N%N“I’ll put you to rest now...”∬∬∬∬∬%T300%P',
    '【梨深】%N%N%N「ごめん……ごめんね……」∬∬∬∬%T300%P': '【Rimi】%N%N%N“I’m sorry... I’m so sorry...”∬∬∬∬%T300%P',
    '【梨深】%N%N%N「ん……っ」∬∬∬%T180%P': '【Rimi】%N%N%N“Mm...”∬∬∬%T180%P',
}

# (scene, line) -> full replacement where CoZ's text is incomplete for the PSP line
SPLIT_TEXT = {
    ('sch03_048', 81): 'With a cell phone, your voice is first converted into electrical signals. Then, it travels '
                       'to a nearby base station via radio waves,',
    ('sch03_048', 82): 'which then run through normal phone lines to the switching station, then to the closest '
                       'base station to the recipient, before finally arriving at their cell phone right '
                       'afterward. It was a bizarre, complicated process.',
}

OVERRIDE = {
    ('schz_214', 8): 'Internal organs litter the floor. But not a single drop%Nof blood falls with them.%K%P',
    # left untranslated in CoZ 1.1.3 itself (their English file repeats the Japanese)
    # the repeated threat: same words, line breaks only (three repeats per row, as in the original's rows)
    ('schk_161', 86): 'I’llfuckingkillyouI’llfuckingkillyouI’llfuckingkillyou%NI’llfuckingkillyou',
    ('schk_161', 87): 'I’llfuckingkillyouI’llfuckingkillyou%NI’llfuckingkillyouI’llfuckingkillyou',
    ('schk_161', 88): 'I’llfuckingkillyou%NI’llfuckingkillyouI’llfuckingkillyouI’llfuckingkillyou%K%P',
    ('sch10_217', 73): 'And so I was forced to relive the New Gen murders%Nvicariously.%K%P',
    ('sch10_217', 74): 'Seven incidents. Fourteen dead.%K%P',
    ('sch10_217', 75): 'Forced into the victims’ point of view, I was killed%Nagain and again, just as they had been.%K%P',
    ('sch10_217', 76): 'A man cosplaying as Darth Spider, and a female nurse.%NI was killed over and over by the two culprits.%K%P',
    ('sch10_217', 77): 'The pain. The fear. I was made to share every%Nsensation the victims had felt.%K%P',
}

# TIPS keywords CoZ left uncolored: (scene, line) -> English word to mark
TIPS_FALLBACK = {('sch01_003', 2): 'handle', ('sch01_003', 51): 'Lurking'}


def add_pauses(out, n):
    """insert n mid-line click pauses (%K) after sentence ends, spread evenly"""
    if n <= 0:
        return out
    ends = [mo.end() for mo in re.finditer(r'[.!?…”’]+(?=(?:%N| )\S)', out)]
    if not ends:
        return out
    pick = sorted(set(ends[min(len(ends) - 1, round((j + 1) * len(ends) / (n + 1)) - 1)] for j in range(n)))
    for pos in reversed(pick):
        out = out[:pos] + '%K' + out[pos:]
    return out


def build_line(orig, name, parts, key=None, indent=0, indent_chars=0):
    """orig: original PSP string (unicode). Returns new PSP string (unicode).
    indent: pixel column where this string starts (it continues the previous string's line)"""
    m = LINE.match(orig)
    lead, jp_name, mid, body, tail = m.groups()
    if re.search(r'%T\d{3}', tail):            # the PSP line already pauses here: drop CoZ's own wait
        parts = list(parts)
        while parts and parts[-1][0] in ('wait', 'nl') or (parts and parts[-1][0] == 'text' and not parts[-1][1].strip()):
            parts.pop()
    cont = not re.search(r'(%N|%P|%LE)$', tail) and not re.search(r'%K%P', tail)
    if lead or jp_name is not None or mid:
        indent = 0
    bcodes = re.findall(r'%B(\d)S', body)
    centered = '%LC' in orig
    head = lead
    if jp_name is not None:
        # speaker tags are keys into DATA.BIN's name table (translated there), keep them
        head += '【%s】' % jp_name
        NAME_VOTES.setdefault(jp_name, {}).setdefault(name, 0)
        NAME_VOTES[jp_name][name] += 1
    head += mid
    lines = wrap(parts, enc.BOX_WIDTH, first_indent=indent, first_chars=indent_chars if indent else 0)
    if cont and lines and lines[-1] and not lines[-1].endswith(' '):
        lines[-1] += ' '                         # the next string continues on this line
    if centered:
        head = head.replace('%LC', '')
        tail = tail.replace('%LE', '')
        out = head + '%N'.join('%LC' + l + '%LE' for l in lines) + tail
    else:
        out = head + '%N'.join(lines) + tail
    # TIPS keyword highlights: reuse the original line's %B codes in order
    opened = []
    def sub(mo):
        if mo.group() == '\x01':
            if not bcodes:
                return ''
            n = bcodes.pop(0); opened.append(n); return '%%B%sS' % n
        return '%%B%sE' % opened.pop() if opened else ''
    out = re.sub('[\x01\x02]', sub, out)
    if bcodes and key in TIPS_FALLBACK:
        w = TIPS_FALLBACK[key]
        out = out.replace(w, '%%B%sS%s%%B%sE' % (bcodes[0], w, bcodes[0]), 1)
    mid_k = len(re.findall(r'%K(?!%P|$)', body))
    return add_pauses(out, mid_k)


def split_sentences(parts, n):
    """Split one English segment into n roughly proportional pieces at sentence ends."""
    text_parts = parts
    flat = ''.join(v if k == 'text' else (' ' if k == 'nl' else '') for k, v in text_parts if k in ('text', 'nl'))
    sents = re.findall(r'.+?(?:[.!?…”"]+(?=\s|$)|$)', flat.strip())
    sents = [s.strip() for s in sents if s.strip()]
    if len(sents) < n:
        words = flat.split()
        per = max(1, len(words) // n)
        sents = [' '.join(words[i * per:(i + 1) * per if i < n - 1 else None]) for i in range(n)]
    total = sum(len(s) for s in sents)
    out, acc, cur = [], 0, []
    for s in sents:
        cur.append(s); acc += len(s)
        if len(out) < n - 1 and acc >= total * (len(out) + 1) / n:
            out.append(' '.join(cur)); cur = []
    if cur: out.append(' '.join(cur))
    while len(out) < n: out.append('')
    return [[('text', s)] for s in out]


_COZ_SHORT = None
RUBY_BASE = re.compile(r'\{([^}]*)\}\[[^\]]*\]')


def manual(orig):
    """choice/flag labels: CoZ's own translation of the same Japanese when it has one, else MANUAL"""
    global _COZ_SHORT
    if _COZ_SHORT is None:
        _COZ_SHORT = {}
        for f in glob.glob(os.path.join(ROOT, 'steam', 'mes00', '**', '*.msb'), recursive=True):
            en = dict(msb.mes(msb.en_file(os.path.basename(f).replace('_00.msb', '_01.msb'))))
            for i, r in msb.mes(f):
                t = unicodedata.normalize('NFKC', msb.dec(r, False))
                e = msb.dec(en.get(i, b''), False) if i in en else ''
                if len(t) <= 24 and e and 'PLACEHOLDER' not in e and '\n' not in e:
                    _COZ_SHORT.setdefault(t, e)
    t = _COZ_SHORT.get(unicodedata.normalize('NFKC', orig)) or MANUAL[orig]
    return t.replace('①', '1')                    # circled digits are not in the PSP font


BOX_ROWS = 5            # message box rows (SYSTEM.CFG window geometry set by sysfiles.py)
WIDE_STEPS = ('thin',)      # overflow pages: same words with a 2 px space glyph
OVERFLOW = []
_PCODE = re.compile(r'%(?:K|LC|LE|O\d{3}|T\d{3}|S\d{3}|t\d{3}|FS|FE|B\d[SE]|n|p)|【[^】]*】|∬')


def page_is_box(group):
    """Japanese page fits the 3-row box (~25 full-width characters per row)"""
    rows = 0
    for it in group:
        t = _PCODE.sub('', it[2]).replace('%N', '').replace('%P', '')
        w = sum(8 if ord(c) < 0x100 else (11 if c in '、。，．・「」『』（）！？…―ー' else 17) for c in t)
        rows += -(-w // 432) if t.strip() else 0
    return rows <= 3


def page_rows(outs):
    rows, open_ = 0, False
    for s in outs:
        for k, seg in enumerate(s.replace('%P', '').split('%N')):
            if k > 0:
                open_ = False
            if _PCODE.sub('', seg).strip() and not open_:
                rows += 1; open_ = True
        if s.rstrip().endswith('%N'):
            open_ = False
    return rows


def process(name, data, report):
    s = Script(data)
    res, info = align.align(name, s)
    if res is None:
        return None
    st, enmap, jp, psp = info
    strs = s.strings()
    # group PSP lines per Steam msg id to detect segment-count mismatches
    en_by_id = {}
    for (i, k), sg in enmap.items():
        en_by_id.setdefault(i, {})[k] = sg
    jp_count = {}
    for i, k, _ in jp:
        jp_count[i] = max(jp_count.get(i, 0), k + 1)
    new = {}
    split_cache = {}
    items = []
    for p, line, so, _ in psp:
        m = res.get(so)
        orig = strs[so].decode('cp932')
        if not re.sub(r'%(?:LC|LE|N|K|P|O\d{3}|T\d{3})', '', orig).strip():
            report.append((name, line, 'EMPTY', orig, orig))   # only control codes: nothing to translate
            continue
        segs = None
        src = name
        if m is None:
            g = align.global_lookup(align.norm(orig))
            if g is None:
                if orig in MANUAL:
                    t = manual(orig); new[so] = enc.encode(t); report.append((name, line, 'manual', orig, t))
                else:
                    report.append((name, line, 'UNMATCHED', orig, ''))
                continue
            gf, i, k, how = g
            src = gf
            gen = {(a, b): sg for a, b, sg in align.steam_segs(gf, 1)}
            gjp = align.steam_segs(gf, 0)
            segs = {kk: sg for (a, kk), sg in gen.items() if a == i}
            nseg = max(kk for a, kk, _ in gjp if a == i) + 1
        else:
            i, k, how = m
        if segs is None:
            segs = en_by_id.get(i, {})
            nseg = jp_count.get(i)
        if len(segs) == nseg and k in segs:
            nm, parts = seg_to_parts(segs[k])
        else:
            # EN/JP segment counts differ: distribute the whole English message
            if (src, i) not in split_cache:
                allparts = []
                nm = None
                for kk in sorted(segs):
                    n2, pp = seg_to_parts(segs[kk])
                    nm = nm or n2
                    allparts += pp + [('nl', None)]
                split_cache[(src, i)] = (nm, split_sentences(allparts, nseg or 1))
            nm, pieces = split_cache[(src, i)]
            parts = pieces[min(k, len(pieces) - 1)]
        if (name, line) in SPLIT_TEXT:
            parts = [('text', SPLIT_TEXT[(name, line)])]; how += '+split'
        items.append([so, line, orig, nm, parts, how])
    # CoZ merged some sentences into the previous message and left '<REMOVED LINE PLACEHOLDER>' in
    # the next one; the PSP keeps both lines, so the merged English is split back across them
    def is_ph(parts):
        return 'REMOVED LINE PLACEHOLDER' in ''.join(v for k, v in parts if k == 'text')
    j = 0
    while j < len(items):
        if is_ph(items[j][4]):
            a = j - 1
            b = j
            while b + 1 < len(items) and is_ph(items[b + 1][4]):
                b += 1
            if a >= 0 and not is_ph(items[a][4]):
                pieces = split_sentences(items[a][4], b - a + 1)
                if any(not ''.join(v for k, v in pc if k == 'text').strip() for pc in pieces):
                    # too few sentence breaks: split the words in proportion to the Japanese lengths
                    words = ' '.join(''.join(v for k, v in pc if k == 'text') for pc in pieces).split()
                    jl = [max(1, len(re.sub(r'%\w\d*|【[^】]*】', '', items[x][2]))) for x in range(a, b + 1)]
                    pieces, w0 = [], 0
                    for q, L in enumerate(jl):
                        w1 = len(words) if q == len(jl) - 1 else max(w0 + 1, round(len(words) * sum(jl[:q + 1]) / sum(jl)))
                        pieces.append([('text', ' '.join(words[w0:w1]))]); w0 = w1
                # re-apply TIPS/colour highlights (cstart text cend) that the plain split dropped
                src = items[a][4]
                hl = [(src[q], src[q + 1][1], src[q + 2]) for q in range(len(src) - 2)
                      if src[q][0] == 'cstart' and src[q + 1][0] == 'text' and src[q + 2][0] == 'cend']
                for pc_i, pc in enumerate(pieces):
                    t = ''.join(v for k, v in pc if k == 'text')
                    for cs, word, ce in hl:
                        if word and word in t:
                            pre, post = t.split(word, 1)
                            pieces[pc_i] = [('text', pre), cs, ('text', word), ce, ('text', post)]
                            break
                for n_, idx in enumerate(range(a, b + 1)):
                    items[idx][4] = pieces[n_]
                    items[idx][5] += '+merged'
            else:
                for idx in range(j, b + 1):
                    items[idx][4] = []
            j = b + 1
        else:
            j += 1
    def layout(group):
        """build the strings of one text page; returns outputs"""
        outs, col, colc = [], 0, 0
        for so, line, orig, nm, parts, how in group:
            out = OVERRIDE.get((name, line)) or build_line(orig, nm, parts, (name, line), indent=col,
                                                            indent_chars=colc)
            # where the next string starts: same line unless this one ends the line/page
            if re.search(r'(%N|%P|%LE)$', out) or '%P' in out[-6:]:
                col = 0; colc = 0
            else:
                last = re.split(r'%N', out)[-1]
                vis = re.sub(r'%(?:[KP]|T\d{3}|S\d{3}|t\d{3}|O\d{3}|FS|FE|B\d[SE]|n|p)|【[^】]*】|∬', '', last)
                col = (col if '%N' not in out else 0) + enc.width(vis)
                colc = (colc if '%N' not in out else 0) + vlen(RUBY_BASE.sub(lambda m: m.group(1), vis))
            outs.append(out)
        return outs

    # pages = runs of strings up to one that ends the page; the message box holds BOX_ROWS rows
    pages, cur = [], []
    for it in items:
        cur.append(it)
        if '%P' in it[2]:
            pages.append(cur); cur = []
    if cur:
        pages.append(cur)
    for group in pages:
        outs = layout(group)
        if page_is_box(group) and page_rows(outs) > BOX_ROWS:
            for step in WIDE_STEPS:
                thin = [(g[0], g[1], g[2], g[3], [(k, v.replace(' ', ' ') if k == 'text' else v)
                                                     for k, v in g[4]], g[5]) for g in group]
                outs2 = layout(thin)
                if page_rows(outs2) < page_rows(outs):
                    outs = outs2
                if page_rows(outs) <= BOX_ROWS:
                    break
            if page_rows(outs) > BOX_ROWS:
                OVERFLOW.append((name, [g[1] for g in group], page_rows(outs)))
        for (so, line, orig, nm, parts, how), out in zip(group, outs):
            new[so] = enc.encode(out)
            report.append((name, line, how, orig, out))
    # every other Japanese string the script references (effect/log copies, sentinel lines)
    for q, so in s.refs:
        if so in new:
            continue
        raw = strs[so]
        if not re.search(rb'[\x81-\x9f\xe0-\xef][\x40-\xfc]', raw):
            continue
        orig = raw.decode('cp932')
        if orig in MANUAL:
            t = manual(orig); new[so] = enc.encode(t); report.append((name, -1, 'manual', orig, t)); continue
        g = align.global_lookup(align.norm(orig))
        if g is None:
            report.append((name, -1, 'UNMATCHED', orig, '')); continue
        gf, i, k, how = g
        segs = sorted((kk, sg) for a, kk, sg in align.steam_segs(gf, 1) if a == i)
        nm, parts = None, []
        for kk, sg in segs:
            n2, pp = seg_to_parts(sg); nm = nm or n2; parts += pp + [('nl', None)]
        out = build_line(orig, nm, parts, (name, -1))
        new[so] = enc.encode(out)
        report.append((name, -1, 'extra-' + how, orig, out))
    return s.rebuild(new)


def main():
    outdir = sys.argv[1]
    only = None
    if '--only' in sys.argv:
        only = set(x.lower() for x in sys.argv[sys.argv.index('--only') + 1:] if not x.startswith('--'))
    os.makedirs(outdir, exist_ok=True)
    report = []
    for f in sorted(glob.glob(os.path.join(SC, '*.BIN'))):
        n = os.path.basename(f)[:-4].lower()
        if only and n not in only:
            continue
        out = process(n, open(f, 'rb').read(), report)
        if out is not None:
            open(os.path.join(outdir, os.path.basename(f)), 'wb').write(out)
    if not only:
        json.dump(NAME_VOTES, open(os.path.join(ROOT, 'work', 'name_votes.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False, indent=0)
    rp = os.path.join(outdir, '_report.tsv')
    with open(rp, 'w', encoding='utf-8') as fo:
        for r in report:
            fo.write('\t'.join(str(x).replace('\t', ' ').replace('\n', '\\n') for x in r) + '\n')
    bad = sum(1 for r in report if r[2] == 'UNMATCHED')
    print('lines', len(report), 'unmatched', bad, '->', rp)
    print('message-box pages over %d rows: %d' % (BOX_ROWS, len(OVERFLOW)), OVERFLOW[:20])


# developer route flags in branch menus: 梨深ルート有り -> Rimi Route: On
for _jp, _en in (('梨深', 'Rimi'), ('七海', 'Nanami'), ('優愛', 'Yua'), ('あやせ', 'Ayase'), ('セナ', 'Sena'), ('梢', 'Kozue')):
    MANUAL[_jp + 'ルート有り'] = _en + ' Route: On'
    MANUAL[_jp + 'ルート無し'] = _en + ' Route: Off'


if __name__ == '__main__':
    main()
