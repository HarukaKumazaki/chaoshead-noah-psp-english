"""Unicode -> PSP Shift-JIS encoding for English text, plus glyph widths for wrapping.

Two modes, chosen by font.json in work/ (written by mkfont.py):
  - custom font: ASCII and italic ASCII are mapped to free SJIS rows (0x85xx/0x86xx)
    that mkfont.py fills with proportional English glyphs.
  - fallback: ASCII is mapped to full-width forms (Ａ etc.).
Italic text is marked in the input with \x0e ... \x0f.
"""
import os, json, re

CTRL = re.compile(r'%(?:LC|LE|FS|FE|N|K|P|O\d{3}|T\d{3}|S\d{3}|t\d{3}|B\d[SE]|n|p'
                  r'|CF[0-9A-F]{4}|CE|T\d|T(?![0-9])|0?\d*d|s|D|savesize%|B(?![0-9]))')  # system/menu codes
RUBY = re.compile(r'\{([^{}]*)\}\[([^\[\]]*)\]')

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTMAP = os.path.join(ROOT, 'work', 'font.json')

# PSP message box usable width in pixels (480 wide screen, margins)
BOX_WIDTH = 464     # message box text width (SYSTEM.CFG margins set by sysfiles.py)
MAX_CHARS = 72      # backlog: no re-wrap below 448 px (ebootfix), rows stored in 96-byte buffers
MAX_BYTES = 92

# punctuation without a direct cp932 form
SUBST = {
    '—': '―', '–': '-', '…': '…', '‘': '‘', '’': '’', '“': '“', '”': '”',
    'é': 'e', 'è': 'e', 'à': 'a', 'ï': 'i', 'ü': 'u', 'ç': 'c', 'ö': 'o', 'á': 'a',
    ' ': ' ', '♪': '♪', '～': '～', '〜': '～', '·': '・',
    'ë': 'e',
    # CoZ's garbled hacker handle: closest glyphs the PSP font has
    '¦': '｜', 'Ѓ': 'Г', '€': '∈', 'ђ': 'h',
}

_map = None


def _load():
    global _map
    if _map is None:
        if os.path.exists(FONTMAP):
            _map = json.load(open(FONTMAP, encoding='utf-8'))
        else:
            _map = {'regular': {}, 'italic': {}, 'width': {}, 'iwidth': {}, 'custom': False}
    return _map


def _fw(c):
    o = ord(c)
    if 0x21 <= o <= 0x7E:
        return chr(o + 0xFEE0)
    if c == ' ':
        return '　'
    return c


def _chars(text):
    """yield (char, italic) skipping markers"""
    it = False
    i = 0
    while i < len(text):
        c = text[i]
        if c == '\x0e': it = True
        elif c == '\x0f': it = False
        else: yield c, it
        i += 1


def encode(text):
    m = _load()
    out = bytearray()
    i = 0
    it = False
    # PSP control sequences (%N, %T030, {ruby}[..], 【】) pass through untouched
    while i < len(text):
        c = text[i]
        ctl = CTRL.match(text, i) if c == '%' else None
        if ctl:
            out += ctl.group().encode('ascii'); i = ctl.end(); continue
        rb = RUBY.match(text, i) if c == '{' else None
        if rb:
            # ruby markup: raw braces/brackets, contents encoded normally
            out += b'{' + encode(rb.group(1)) + b'}[' + encode(rb.group(2)) + b']'
            i = rb.end(); continue
        i += 1
        if c == '\x0e':
            it = True; continue
        if c == '\x0f':
            it = False; continue
        out += enc_char(c, it, m)
    return bytes(out)


def enc_char(c, italic, m=None):
    m = m or _load()
    c = SUBST.get(c, c)
    # (a single-byte 0x20 gets a fixed wide advance from the engine, so spaces use the
    #  2-byte narrow-space glyph from the font table below)
    # regular printable ASCII as one byte; %, {}, [] are markup bytes in PSP text so keep them 2-byte
    if m.get('custom') and not italic and '!' <= c <= '~' and c not in '%{}[]':
        return c.encode('ascii')
    table = m['italic'] if italic else m['regular']
    if m.get('custom') and c in table:
        return bytes.fromhex(table[c])
    if m.get('custom') and c in m['regular']:
        return bytes.fromhex(m['regular'][c])
    try:
        return _fw(c).encode('cp932')
    except UnicodeEncodeError:
        return '？'.encode('cp932')


def width(text):
    m = _load()
    w = 0
    for c, it in _chars(text):
        c = SUBST.get(c, c)
        tab = m['iwidth'] if it else m['width']
        if m.get('custom') and c in tab:
            w += tab[c]
        else:
            w += 20 if not m.get('custom') else m['width'].get(c, 20)
    return w
