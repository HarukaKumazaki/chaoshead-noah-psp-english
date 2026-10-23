"""Translate PSP system data files in SCENE00 (name table, chapter jump, clear list, debug menus).

Usage: sysfiles.py outdir      (writes translated .BIN files; needs work/name_votes.json from inject.py)
"""
import sys, os, json, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import strpatch, ui_tr, enc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SC = os.path.join(ROOT, 'unpacked', 'DATA0', 'SCENE00.AFS.d')
JPCHR = re.compile('[　-鿿＀-￯]')


def data_bin():
    """speaker table: (【key】, display) pairs -> English display names from CoZ usage"""
    b = open(os.path.join(SC, 'DATA.BIN'), 'rb').read()
    votes = json.load(open(os.path.join(ROOT, 'work', 'name_votes.json'), encoding='utf-8'))
    coz = json.load(open(os.path.join(ROOT, 'work', 'coz_names.json'), encoding='utf-8'))
    st = strpatch.strings(b)
    # the first record's 【key】 follows table bytes instead of a NUL, so strings() misses it (and with
    # it the pairing for 拓巳 / Takumi): add 【…】 strings that the u32 record pointers reference
    import struct
    for p in range(0, len(b) - 3, 4):
        v = struct.unpack_from('<I', b, p)[0]
        if v not in st and 0 < v < len(b) and b[v:v + 2] == '【'.encode('cp932'):
            st[v] = (b[v:b.index(b'\0', v)], None)
    seq = [(o, st[o][0].decode('cp932', 'replace')) for o in sorted(st)]
    tr, missing = {}, []
    for (o, t), nxt in zip(seq, seq[1:] + [(None, '')]):
        m = re.fullmatch(r'【(.*)】', t)
        if m and nxt[0] is not None and not nxt[1].startswith('【'):
            key = m.group(1)
            v = votes.get(key)
            disp = nxt[1]
            if v:
                tr[nxt[0]] = max(v.items(), key=lambda kv: kv[1])[0] or '???'
            elif disp == '？？？':
                tr[nxt[0]] = '???'
            elif disp in coz:
                tr[nxt[0]] = coz[disp]
            elif ui_tr.extra_name(disp):
                tr[nxt[0]] = ui_tr.extra_name(disp)
            elif JPCHR.search(disp):
                missing.append((key, disp))
        elif not t.startswith('【') and o not in tr and JPCHR.search(t):
            g = ui_tr.general(t)
            if g:
                tr[o] = g
    return b, tr, missing


# CoZ's Tips screen has no category column; the list row has room for ~10 glyphs (longer ones are
# overwritten by the next row's text), so keep these to 9 characters.
TIPS_CATEGORY = {'ネット・オタク': 'Net/Otaku', '一般用語': 'General', 'ディソード': 'DI-sword',
                 '架空用語': 'Fictional', '診断結果': 'Diagnosis'}
TIPS_WIDTH = 400   # px; TIPS description pane


def coz_tips():
    """NFKC(japanese term) -> (english term, english description parts) from CoZ's _tips files"""
    import msb, unicodedata, inject
    jp = msb.mes(os.path.join(ROOT, 'steam', 'mes00', '_tips_00.msb'))
    en = dict(msb.mes(msb.en_file('_tips_01.msb')))
    cats = {'人名', 'ディソード'}
    out = {}
    # entries are [category, term, reading, sort key, description]
    for k in range(1, len(jp) - 3):
        if msb.dec(jp[k - 1][1], False) not in cats:
            continue
        term_jp = tips_key(msb.dec(jp[k][1], False))
        term_en = msb.dec(en[jp[k][0]], False)
        reading_en = msb.dec(en[jp[k + 1][0]], False)
        _, parts = inject.seg_to_parts(list(msb.tokens(en[jp[k + 3][0]])))
        out.setdefault(term_jp, (term_en, reading_en, parts))
    return out


def tips_key(t):
    import unicodedata
    return re.sub(r'\s', '', unicodedata.normalize('NFKC', t))


def dict_bin():
    import unicodedata, inject, struct
    b = open(os.path.join(SC, 'DICT.BIN'), 'rb').read()
    tips = coz_tips()
    recs = []
    n = 0
    while n * 32 + 26 <= len(b):
        offs = struct.unpack_from('<5H', b, n * 32 + 16)
        if not all(0 < o < len(b) for o in offs):
            break
        recs.append(offs); n += 1
    table_end = n * 32
    first = min(min(r) for r in recs)

    def s(o):
        return b[o:b.index(b'\0', o)]
    out = bytearray(b[:first])
    cache = {}
    missing = []
    for r, offs in enumerate(recs):
        term, idx, reading, cat, desc = [s(o).decode('cp932') for o in offs]
        key = tips_key(term)
        if key in tips:
            t_en, r_en, parts = tips[key]
            d_en = '%N'.join(inject.wrap(parts, TIPS_WIDTH, hard_nl=True))
        else:
            missing.append(term); t_en, r_en, d_en = term, reading, desc
        new = [t_en, idx, r_en, TIPS_CATEGORY.get(cat, cat), d_en]
        for j, txt in enumerate(new):
            raw = enc.encode(txt) if txt not in (idx,) else txt.encode('cp932')
            if raw not in cache:
                cache[raw] = len(out); out += raw + b'\0'
            struct.pack_into('<H', out, r * 32 + 16 + 2 * j, cache[raw])
    if len(out) > 0xFFFF:
        raise ValueError('DICT.BIN string area exceeds 16-bit offsets')
    return bytes(out), missing


def system_cfg():
    """USRDIR/SYSTEM.CFG: the game reads at most 0x1000 bytes into a 4 KB buffer, so the file must
    not grow past that. Save titles are rewritten in place (plain ASCII, system font); the option
    strings referenced by the u16 table at 0x5F8-0x653 are rebuilt compactly from 0x718."""
    import struct
    b = bytearray(open(os.path.join(ROOT, 'iso', 'PSP_GAME', 'USRDIR', 'SYSTEM.CFG'), 'rb').read())
    for off in (0x660, 0x672, 0x684, 0x6A0):            # 'カオスヘッド ノア' x4, 17 bytes + NUL each
        b[off:off + 18] = b'CHAOS;HEAD NOAH'.ljust(18, b'\0')
    # message window shapes (64-byte records from 0x140). The box cannot scroll, and CoZ's English is
    # longer than the Japanese, so it holds 5 rows instead of 3: 18 px line pitch (glyph 18 + gap 0),
    # text 464 px wide (side margins 4), last row 2 px above the screen edge -> box 98 px (was 76).
    for k in range(2):                                          # records 0/1: message box
        r = 0x140 + k * 64
        b[r + 9] = 0                                            # line gap (pitch = 18 + gap)
        struct.pack_into('<4h', b, r + 0x1C, 4, 4, 6, 2)        # margins: left, right, top, bottom
        struct.pack_into('<h', b, r + 0x10, 4 * 18 + 18 + 6 + 2)  # box height: 5 rows + margins
    # full-screen text rectangle (prologue, %L1 pages): x, y, w, h at 0x134; text runs from x, w - 8 wide.
    # Was x 16 / w 448 (440 px); the English is wrapped to 464 px, so x 8 / w 472 (8 px margins).
    assert struct.unpack_from('<4h', b, 0x134) == (16, 28, 448, 216)
    struct.pack_into('<2h', b, 0x134, 8, 28)
    struct.pack_into('<h', b, 0x138, 472)
    tbl0, tbl1, region = 0x5F8, 0x654, 0x718
    ptrs = [struct.unpack_from('<H', b, p)[0] for p in range(tbl0, tbl1, 2)]
    assert min(ptrs) == region, hex(min(ptrs))
    out = bytearray(b[:region])
    placed = {}
    left = []
    for i, o in enumerate(ptrs):
        t = bytes(b[o:b.index(b'\0', o)]).decode('cp932')
        e = ui_tr.system_cfg(t)
        if e is None:
            left.append(t); e_raw = t.encode('cp932')
        else:
            e_raw = enc.encode(e)
        if e_raw not in placed:
            placed[e_raw] = len(out); out += e_raw + b'\0'
        struct.pack_into('<H', out, tbl0 + 2 * i, placed[e_raw])
    if len(out) > 0x1000:
        raise ValueError('SYSTEM.CFG is %d bytes; the game only reads 4096' % len(out))
    return bytes(out), left


def clrflg_first(b, fn):
    """The first ending notice in CLRFLG.BIN (offset from the u16 table at 0x18) follows table bytes
    instead of a NUL, so strpatch.strings() misses it: translate it in place."""
    import struct
    off = struct.unpack_from('<H', b, 0x18)[0]
    end = b.index(b'\0', off)
    slot = end - off
    while b[off + slot] == 0:
        slot += 1
    e = fn(bytes(b[off:end]).decode('cp932'))
    if not e:
        return b
    raw = enc.encode(e) + b'\0'
    if len(raw) > slot:
        raise ValueError('CLRFLG first notice too long: %r' % e)
    b = bytearray(b)
    b[off:off + slot] = raw.ljust(slot, b'\0')
    return bytes(b)


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    b, tr, missing = data_bin()
    nb, n, tot = strpatch.patch(b, tr, refs='u32')
    open(os.path.join(out, 'DATA.BIN'), 'wb').write(nb)
    print('DATA.BIN', n, '/', tot, 'strings; speakers without CoZ name:', len(missing))
    for k, d in missing:
        print('   ', k, d)
    for name, fn in (('SHORTCUT.BIN', ui_tr.shortcut), ('CLRFLG.BIN', ui_tr.clearlist)):
        b = open(os.path.join(SC, name), 'rb').read()
        st = strpatch.strings(b)
        tr, left = {}, []
        for o, (raw, slot) in st.items():
            t = raw.decode('cp932', 'replace')
            if not JPCHR.search(t) or len(t) < 3:
                continue
            e = fn(t)
            if e: tr[o] = e
            else: left.append(t)
        nb, n, tot = strpatch.patch(b, tr, refs='u16')
        if name == 'CLRFLG.BIN':
            nb = clrflg_first(nb, fn)
        open(os.path.join(out, name), 'wb').write(nb)
        print(name, n, '/', tot, 'untranslated:', left)
    nb, missing = dict_bin()
    open(os.path.join(out, 'DICT.BIN'), 'wb').write(nb)
    print('DICT.BIN', len(nb), 'bytes; TIPS without CoZ entry:', missing)

    # CONFIG.AFS (title menu help, clear list) and USRDIR/SYSTEM.CFG
    cfg_out = os.path.join(os.path.dirname(out), 'CONFIG.AFS.d')   # out = .../DATA0/SCENE00.AFS.d
    os.makedirs(cfg_out, exist_ok=True)
    menu = os.path.join(ROOT, 'unpacked', 'DATA0', 'CONFIG.AFS.d', 'MENU.CFG')
    b = open(menu, 'rb').read()
    nb, n = strpatch.patch_seq(b, 0x394, ui_tr.MENU_HELP.get)   # strings addressed by index
    open(os.path.join(cfg_out, 'MENU.CFG'), 'wb').write(nb)
    print('MENU.CFG', n, '/', len(ui_tr.MENU_HELP) + 1)
    nb, left = system_cfg()
    os.makedirs(os.path.join(ROOT, 'work', 'usrdir'), exist_ok=True)
    open(os.path.join(ROOT, 'work', 'usrdir', 'SYSTEM.CFG'), 'wb').write(nb)
    print('SYSTEM.CFG', len(nb), 'bytes (max 4096); untranslated:', left)
    jobs = [(os.path.join(ROOT, 'unpacked', 'DATA0', 'CONFIG.AFS.d', 'CLRLST.CFG'), cfg_out, ui_tr.clrlst, 'u32')]
    for src, dst, fn, refs in jobs:
        b = open(src, 'rb').read()
        tr, left = {}, []
        for o, (raw, slot) in strpatch.strings(b).items():
            t = raw.decode('cp932', 'replace')
            if not JPCHR.search(t):
                continue
            e = fn(t)
            if e: tr[o] = e
            elif len(t) > 1 and '─' not in t: left.append(t)
        nb, n, tot = strpatch.patch(b, tr, refs=refs)
        os.makedirs(dst, exist_ok=True)
        open(os.path.join(dst, os.path.basename(src)), 'wb').write(nb)
        print(os.path.basename(src), n, '/', tot, 'untranslated:', left)


if __name__ == '__main__':
    main()
