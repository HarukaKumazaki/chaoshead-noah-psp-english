"""Code patches for the decrypted EBOOT (applied by eboot_tr.py after the string patches).

Glyph cache (0x088E4F68): the engine copies a character's 20 font rows into a 32-row cache slot and
never writes rows 20-31; whatever was in that memory before (often 0xFF = white) gets drawn by the
texture filter as a thin line under every character. The routine is rewritten, in the same space,
to clear the whole slot first. UNDERLINE = True keeps the old behaviour.
"""
import struct

BASE_VA = 0x08804000
FILE_OFF = 0x54
UNDERLINE = False

R = {n: i for i, n in enumerate(
    'zero at v0 v1 a0 a1 a2 a3 t0 t1 t2 t3 t4 t5 t6 t7 s0 s1 s2 s3 s4 s5 s6 s7 t8 t9 k0 k1 gp sp fp ra'.split())}


def I(op, rs, rt, imm):
    return (op << 26) | (R[rs] << 21) | (R[rt] << 16) | (imm & 0xFFFF)


def Rt(fn, rs='zero', rt='zero', rd='zero', sa=0):
    return (R[rs] << 21) | (R[rt] << 16) | (R[rd] << 11) | (sa << 6) | fn


def lui(rt, imm): return I(0x0F, 'zero', rt, imm)
def addiu(rt, rs, imm): return I(0x09, rs, rt, imm)
def andi(rt, rs, imm): return I(0x0C, rs, rt, imm)
def lbu(rt, off, rs): return I(0x24, rs, rt, off)
def lhu(rt, off, rs): return I(0x25, rs, rt, off)
def sb(rt, off, rs): return I(0x28, rs, rt, off)
def sll(rd, rt, sa): return Rt(0x00, rt=rt, rd=rd, sa=sa)
def srl(rd, rt, sa): return Rt(0x02, rt=rt, rd=rd, sa=sa)
def addu(rd, rs, rt): return Rt(0x21, rs, rt, rd)
def subu(rd, rs, rt): return Rt(0x23, rs, rt, rd)
def or_(rd, rs, rt): return Rt(0x25, rs, rt, rd)
def slt(rd, rs, rt): return Rt(0x2A, rs, rt, rd)
def jr(rs): return Rt(0x08, rs)
def mult(rs, rt): return Rt(0x18, rs, rt)
def mflo(rd): return Rt(0x12, rd=rd)
def ext(rt, rs, pos, size): return (0x1F << 26) | (R[rs] << 21) | (R[rt] << 16) | ((size - 1) << 11) | (pos << 6)
NOP = 0


def glyph_copy(at):
    """returns the new routine as words; branch targets are relative to `at` (its address)"""
    code = []
    lbl = {}

    def here():
        return at + 4 * len(code)

    def br(op, rs, rt, target):
        return lambda: I(op, rs, rt, (lbl[target] - (at + 4 * idx_of[id_]) - 4) >> 2)
    fix = []

    def emit(w):
        code.append(w)

    def branch(op, rs, rt, target):
        fix.append((len(code), op, rs, rt, target)); code.append(None)

    emit(lui('v0', 0x09BF))
    emit(lhu('a3', -0x16F6, 'v0'))              # current font
    emit(lui('v1', 0x09BF))
    emit(addiu('v1', 'v1', -0x16F8))            # font table 0x09BEE908, 60 bytes per font
    emit(sll('a2', 'a3', 4)); emit(subu('a2', 'a2', 'a3')); emit(sll('a2', 'a2', 2))
    emit(addu('a3', 'v1', 'a2'))
    emit(lbu('t1', 0x3D, 'a3'))                 # rows in the font (20)
    emit(lbu('t2', 0x3C, 'a3')); emit(srl('t2', 't2', 1))   # bytes per font row (10)
    emit(lbu('t3', 0x3E, 'a3'))                 # padding bytes per cache row (6)
    # cache slot height = next power of two >= font rows (20 -> 32, 10 -> 16)
    emit(addiu('t5', 'zero', 1))
    lbl['pow'] = here()
    emit(sll('t5', 't5', 1)); emit(slt('t4', 't5', 't1'))
    branch(0x05, 't4', 'zero', 'pow')
    emit(NOP)
    emit(addu('t7', 't2', 't3')); emit(mult('t5', 't7')); emit(mflo('t5'))
    emit(addu('t6', 'a1', 'zero'))
    lbl['zero'] = here()
    emit(sb('zero', 0, 't6')); emit(addiu('t5', 't5', -1))
    branch(0x07, 't5', 'zero', 'zero')          # bgtz t5, zero
    emit(addiu('t6', 't6', 1))
    emit(addiu('v0', 'zero', 0))
    lbl['row'] = here()
    emit(slt('t4', 'v0', 't1'))
    branch(0x04, 't4', 'zero', 'done')          # beq t4, zero, done
    emit(addiu('t0', 'zero', 0))
    lbl['copy'] = here()
    emit(lbu('v1', 0, 'a0')); emit(addiu('a0', 'a0', 1))
    emit(ext('a2', 'v1', 4, 4)); emit(sll('v1', 'v1', 4)); emit(andi('v1', 'v1', 0xF0)); emit(or_('v1', 'a2', 'v1'))
    emit(sb('v1', 0, 'a1')); emit(addiu('t0', 't0', 1)); emit(slt('t4', 't0', 't2'))
    branch(0x05, 't4', 'zero', 'copy')          # bne t4, zero, copy
    emit(addiu('a1', 'a1', 1))
    emit(addu('a1', 'a1', 't3'))                # skip the (already cleared) padding
    branch(0x04, 'zero', 'zero', 'row')         # b row
    emit(addiu('v0', 'v0', 1))
    lbl['done'] = here()
    emit(jr('ra')); emit(addiu('v0', 'zero', 1))
    for i, op, rs, rt, target in fix:
        code[i] = I(op, rs, rt, (lbl[target] - (at + 4 * i) - 4) >> 2)
    return code


def jal(target): return (0x03 << 26) | ((target >> 2) & 0x3FFFFFF)
def lw(rt, off, rs): return I(0x23, rs, rt, off)
def sw(rt, off, rs): return I(0x2B, rs, rt, off)


def page_reset(at, idx='s3', cnt='s2', loop=0x088E8768):
    """tail of the text layout loop (0x088E88D4..0x088E8948): after a line, y += line height,
    x = x0, line count + 1 -- and, new, when the line ended with a page token (%P), y and the line
    count restart at the top of the window, so text after a mid-string %P stays inside the box"""
    code, fix, lbl = [], [], {}

    def here():
        return at + 4 * len(code)

    def emit(w):
        code.append(w)

    def branch(op, rs, rt, target):
        fix.append((len(code), op, rs, rt, target)); code.append(None)
    emit(jal(0x088E5DF4)); emit(addiu('a0', idx, -1))      # token record of the line's last token
    emit(addiu('t7', 'zero', 0))
    branch(0x04, 'v0', 'zero', 'win'); emit(NOP)
    emit(lbu('t7', 0xC, 'v0'))
    lbl['win'] = here()
    emit(lui('t9', 0x09BF)); emit(lbu('a0', -0x123C, 't9'))
    emit(sll('v1', 'a0', 2)); emit(addu('v1', 'v1', 'a0')); emit(sll('v1', 'v1', 4))
    emit(addiu('t8', 't9', -0x123C)); emit(addu('t8', 't8', 'v1'))   # window record
    emit(lw('a1', 0x28, 't8')); emit(lw('a2', 0x34, 't8')); emit(lw('a3', 0x4C, 't8'))
    emit(addiu('v0', 'zero', 4))
    branch(0x05, 't7', 'v0', 'normal'); emit(addu('a1', 'a1', 'a2'))
    emit(addiu('a3', 'a3', 1)); emit(mult('a3', 'a2')); emit(mflo('v1'))
    emit(subu('a1', 'a1', 'v1')); emit(addiu('a3', 'zero', -1))
    lbl['normal'] = here()
    emit(sw('a1', 0x28, 't8')); emit(lw('v1', 0x2C, 't8')); emit(sw('v1', 0x24, 't8'))
    emit(addiu('a3', 'a3', 1))
    branch(0x07, cnt, 'zero', 'loop'); emit(sw('a3', 0x4C, 't8'))
    lbl['loop'] = loop
    for i, op, rs, rt, target in fix:
        code[i] = I(op, rs, rt, (lbl[target] - (at + 4 * i) - 4) >> 2)
    return code


def bne(rs, rt, off): return I(0x05, rs, rt, off)
def beq(rs, rt, off): return I(0x04, rs, rt, off)
def blez(rs, off): return I(0x06, rs, 'zero', off)
def jr_ra(): return Rt(0x08, 'ra')
def sltu(rd, rs, rt): return Rt(0x2B, rs, rt, rd)
def j(addr): return (0x02 << 26) | ((addr >> 2) & 0x3FFFFFF)


CAVE = 0x088F2868      # inside an unreferenced routine (never called; checked at runtime)


def backlog_wordwrap(B):
    """the backlog splits each text row at a pixel width; make the split fall after the last space
    (2-byte space glyphs 0x85A8 / 0x85A9) so English words are not cut in half"""
    code, lbl, fix = [], {}, []

    def here():
        return CAVE + 4 * len(code)

    def br(op, rs, rt, target):
        fix.append((len(code), op, rs, rt, target)); code.append(None)
    E = code.append
    E(addu('t0', 's5', 'a0')); E(lbu('t1', 0, 't0')); E(addiu('t2', 'zero', 0x85))
    br(0x05, 't1', 't2', 'back'); E(lbu('t3', 1, 't0'))
    E(addiu('t4', 'zero', 0xA8)); br(0x04, 't3', 't4', 'consume'); E(addiu('t4', 'zero', 0xA9))
    br(0x04, 't3', 't4', 'consume'); E(NOP)
    lbl['back'] = here()
    E(addu('v0', 'a0', 'zero')); E(addiu('t5', 'a0', -1))
    lbl['loop'] = here()
    br(0x06, 't5', 'zero', 'ret'); E(addu('t0', 's5', 't5'))
    E(lbu('t1', 0, 't0'))
    br(0x05, 't1', 't2', 'next'); E(lbu('t3', 1, 't0'))
    E(addiu('t4', 'zero', 0xA8)); br(0x04, 't3', 't4', 'found'); E(addiu('t4', 'zero', 0xA9))
    br(0x04, 't3', 't4', 'found'); E(NOP)
    lbl['next'] = here()
    br(0x04, 'zero', 'zero', 'loop'); E(addiu('t5', 't5', -1))
    lbl['found'] = here()
    E(jr_ra()); E(addu('v0', 't5', 'zero'))           # piece ends before the space
    lbl['consume'] = here()
    E(jr_ra()); E(addu('v0', 'a0', 'zero'))
    lbl['ret'] = here()
    E(jr_ra()); E(NOP)
    # rest of the row: skip one leading space (s5 = row, s0 = bytes copied)
    lbl['skip'] = here()
    E(addu('v0', 's5', 's0')); E(lbu('t1', 0, 'v0')); E(addiu('t2', 'zero', 0x85))
    br(0x05, 't1', 't2', 'done'); E(lbu('t3', 1, 'v0'))
    E(addiu('t4', 'zero', 0xA8)); br(0x04, 't3', 't4', 'adv'); E(addiu('t4', 'zero', 0xA9))
    br(0x05, 't3', 't4', 'done'); E(NOP)
    lbl['adv'] = here()
    E(addiu('v0', 'v0', 2))
    lbl['done'] = here()
    E(jr_ra()); E(NOP)
    # backlog reflow: the row stripper (0x088C26D0) ends a row at every %N, so each 464 px message row
    # was cut into a 336 px piece plus a short leftover. While it fills the backlog text buffer
    # (0x089EA010, 2 KB) a %N now becomes one space (none at the start or after a space) and the whole
    # message is split by width, i.e. reflowed. Other callers keep the old behaviour.
    lbl['newline'] = here()
    E(addiu('t0', 'zero', 0x4E)); br(0x05, 'a1', 't0', 'nl_ret'); E(NOP)
    E(lui('t0', 0x089F)); E(addiu('t0', 't0', -0x5FF0))
    E(sltu('t1', 's1', 't0')); br(0x05, 't1', 'zero', 'nl_orig'); E(NOP)
    E(addiu('t2', 't0', 0x800)); E(sltu('t1', 's1', 't2')); br(0x04, 't1', 'zero', 'nl_orig'); E(NOP)
    E(lbu('t3', -1, 's1')); br(0x04, 't3', 'zero', 'nl_skip'); E(NOP)
    E(addiu('t4', 'zero', 0xA8)); br(0x04, 't3', 't4', 'nl_chk'); E(NOP)
    E(addiu('t4', 'zero', 0xA9)); br(0x05, 't3', 't4', 'nl_emit'); E(NOP)
    lbl['nl_chk'] = here()
    E(lbu('t3', -2, 's1')); E(addiu('t4', 'zero', 0x85)); br(0x04, 't3', 't4', 'nl_skip'); E(NOP)
    lbl['nl_emit'] = here()
    E(addiu('t4', 'zero', 0x85)); E(sb('t4', 0, 's1')); E(addiu('t4', 'zero', 0xA8)); E(sb('t4', 1, 's1'))
    E(addiu('s1', 's1', 2))
    lbl['nl_skip'] = here()
    E(j(0x088C2970)); E(addiu('s0', 's0', 2))         # next character of the same message
    lbl['nl_orig'] = here()
    E(sb('zero', 0, 's1')); E(j(0x088C279C)); E(NOP)  # original: end the row here
    lbl['nl_ret'] = here()
    E(jr_ra()); E(NOP)
    assert here() <= 0x088F29D4, 'code cave overflow'
    for i, op, rs, rt, target in fix:
        code[i] = I(op, rs, rt, (lbl[target] - (CAVE + 4 * i) - 4) >> 2)
    off = CAVE - BASE_VA + FILE_OFF
    for i, w in enumerate(code):
        struct.pack_into('<I', B, off + 4 * i, w)
    # call site: replaces the Japanese line-break rule check after the width split
    at = 0x088C2AA4 - BASE_VA + FILE_OFF
    assert struct.unpack_from('<I', B, at)[0] == jal(0x088E91A8), 'backlog split moved'
    for i, w in enumerate((jal(CAVE), addu('a0', 's3', 'zero'), addu('s3', 'v0', 'zero'), NOP, NOP)):
        struct.pack_into('<I', B, at + 4 * i, w)
    nl = 0x088C277C - BASE_VA + FILE_OFF                        # stripper: 'beql a1, v0(N), end row'
    assert struct.unpack_from('<2I', B, nl) == (I(0x14, 'a1', 'v0', 7), sb('zero', 0, 's1')), 'stripper moved'
    struct.pack_into('<2I', B, nl, jal(lbl['newline']), NOP)
    ret = 0x088C2B2C - BASE_VA + FILE_OFF                       # 'addu v0, s5, s0' (return remainder)
    assert struct.unpack_from('<I', B, ret)[0] == addu('v0', 's5', 's0'), 'backlog return moved'
    struct.pack_into('<I', B, ret, jal(lbl['skip']))


def backlog_width(B):
    """backlog re-wraps rows wider than 400 px minus the name indent and garbles single-byte text
    when it does; allow beyond the message-box width (464) so it never re-wraps"""
    a = 0x088C0D38 - BASE_VA + FILE_OFF
    assert struct.unpack_from('<I', B, a)[0] == lui('v0', 0x0190), 'backlog width moved'
    struct.pack_into('<I', B, a, lui('v0', 0x0150))   # 336 px minus indent: pieces stay well under the 48-glyph row buffer


def clear_list_slots(B):
    """Clear List: the six page-1 labels take glyph slots 336.. (107 in English, 60 in Japanese) and
    ran into the ending rows at 432; ending names were clamped to 31 characters and scene titles to 27.
    CoZ's longest names are 49 characters. New layout (engine limit 2560 slots; the yes/no dialog
    uses 1392-1711): endings from 448, scene lists from 1700, 49 slots per row, clamps 49."""
    W = 49
    for va, old, new in (
            (0x08860148, addiu('a1', 'zero', 0x1B0), addiu('a1', 'zero', 448)),     # ending list base
            (0x08860188, addiu('a3', 'a3', 0x20), addiu('a3', 'a3', W)),             # ending row stride
            (0x08860158, addiu('a2', 't1', 0x1DC), addiu('a2', 't1', 1700 - 490)),  # list n base: n*490 + 1210
            (0x08860190, addiu('a2', 'a2', 0x1C), addiu('a2', 'a2', W)),             # scene row stride
            (0x088601A4, addiu('t1', 't1', 0x134), addiu('t1', 't1', 10 * W)),       # per-list step (10 rows)
            (0x08860488, addiu('a1', 'zero', 0x1F), addiu('a1', 'zero', W)),         # ending name clamp
            (0x088604D0, addiu('a1', 'zero', 0x1B), addiu('a1', 'zero', W))):        # scene title clamp
        a = va - BASE_VA + FILE_OFF
        assert struct.unpack_from('<I', B, a)[0] == old, 'clear list code moved at %#x' % va
        struct.pack_into('<I', B, a, new)


def config_slots(B):
    """Config screen: 7 rows of 42 glyph slots from 1472 (label, value at +18 or +30), then two
    96-slot help buffers and the sample message. English labels run to 25 glyphs ("Skip at Delusion
    Triggers"), values to 17 and help texts to ~150, so they overwrote each other. New layout: rows
    of 46 (label 28, value 18), help buffers of 160; the sample message ends near slot 2170 (< 2560)."""
    for va, old, new in (
            (0x088B971C, addiu('v0', 's1', 0x12), addiu('v0', 's1', 28)),    # value slot (type 1)
            (0x088B9728, addiu('v0', 's1', 0x1E), addiu('v0', 's1', 28)),    # value slot (type 2)
            (0x088B9744, addiu('s1', 's1', 0x2A), addiu('s1', 's1', 46)),    # row stride
            (0x088B9758, addiu('v0', 's1', 0x60), addiu('v0', 's1', 160)),   # second help buffer
            (0x088B9788, addiu('v0', 's1', 0xC0), addiu('v0', 's1', 320))):  # sample message
        a = va - BASE_VA + FILE_OFF
        assert struct.unpack_from('<I', B, a)[0] == old, 'config code moved at %#x' % va
        struct.pack_into('<I', B, a, new)


def apply(B):
    clear_list_slots(B)
    config_slots(B)
    backlog_width(B)
    backlog_wordwrap(B)
    # the three text layout loops (whole string / line range / typewriter): page token resets y
    for start, end, idx, cnt, loop in ((0x088E88D4, 0x088E894C, 's3', 's2', 0x088E8768),
                                      (0x088E8DFC, 0x088E8E74, 's4', 's3', 0x088E8C7C)):
        off = start - BASE_VA + FILE_OFF
        assert struct.unpack_from('<I', B, end - 8 - BASE_VA + FILE_OFF)[0] >> 26 == 0x07, 'layout loop moved'
        code = page_reset(start, idx, cnt, loop)
        assert len(code) == (end - start) // 4, len(code)
        for i, w in enumerate(code):
            struct.pack_into('<I', B, off + 4 * i, w)
    if UNDERLINE:
        return
    at = 0x088E4F68
    end = 0x088E501C                           # next routine
    off = at - BASE_VA + FILE_OFF
    # sanity: original routine starts with lui v0,0x9BF / lhu a3,-0x16F6(v0)
    assert struct.unpack_from('<2I', B, off) == (lui('v0', 0x09BF), lhu('a3', -0x16F6, 'v0')), 'glyph routine moved'
    code = glyph_copy(at)
    assert at + 4 * len(code) <= end, len(code)
    for i, w in enumerate(code):
        struct.pack_into('<I', B, off + 4 * i, w)
    for a in range(at + 4 * len(code), end, 4):
        struct.pack_into('<I', B, a - BASE_VA + FILE_OFF, NOP)
