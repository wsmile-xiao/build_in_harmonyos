#!/usr/bin/env python3
"""rl-accel 0.9.1 消费者视角 API 测试（R34 真实调用被测包）。

用法: python3 test_rl_accel.py <site-packages-dir>

对被安装到 site-packages 的 ``_rl_accel`` 扩展逐函数真实调用，并与纯 Python
参考实现逐值比对。任一断言失败即 sys.exit(1)。
"""
import base64
import math
import sys

SITE = sys.argv[1]
sys.path.insert(0, SITE)

import _rl_accel  # noqa: E402  (被测包，必须在插入 sys.path 后导入)

CHECKS = []


def check(name, got, want):
    ok = got == want
    CHECKS.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: got={got!r} want={want!r}")


def check_true(name, cond, detail=""):
    CHECKS.append(bool(cond))
    print(f"[{'PASS' if cond else 'FAIL'}] {name}{(' ' + detail) if detail else ''}")


# ── 纯 Python 参考实现 ──────────────────────────────────────────────
def ref_calc_checksum(data):
    """TTF 校验和：按大端 32 位字累加，末尾不足 4 字节左侧补零，取低 32 位。"""
    total = 0
    for i in range(0, len(data) - len(data) % 4, 4):
        total += (data[i] << 24) | (data[i + 1] << 16) | (data[i + 2] << 8) | data[i + 3]
    left = len(data) % 4
    if left:
        tail = data[len(data) - left:]
        n = tail[0] << 24
        if left > 1:
            n += tail[1] << 16
        if left > 2:
            n += tail[2] << 8
        total += n
    return total & 0xFFFFFFFF


def ref_fp_one(d):
    """复刻 _rl_accel.c:_fp_one 的数值格式化（有效小数位随量级自适应 + 去尾零）。"""
    ad = abs(d)
    if ad <= 1.0e-7:
        return "0"
    if ad > 1e20:
        raise ValueError("number too large")
    if ad > 1:
        l = min(max(0, 6 - int(math.log10(ad))), 6)
    else:
        l = 6
    s = "%.*f" % (l, d)
    if l:
        s = s.rstrip("0")
        if s.endswith("."):
            s = s[:-1]
        if s.startswith("0."):
            s = s[1:]
    return s


def ref_escape_pdf(text):
    data = text.encode("latin1") if isinstance(text, str) else text
    out = []
    for c in data:
        if c < 32 or c >= 127:
            out.append("\\%03o" % c)
        else:
            if c in (0x5C, 0x28, 0x29):  # \ ( )
                out.append("\\")
            out.append(chr(c))
    return "".join(out)


class _T1Font:
    fontName = "Helvetica"
    encName = "utf8"
    substitutionFonts = []
    widths = [1000] * 256


class _Face:
    charWidths = {ord("A"): 600}
    defaultWidth = 500


class _TTFFont:
    fontName = "DejaVuSans"
    encName = "utf8"
    substitutionFonts = []
    face = _Face()


class _Frag:
    def __init__(self, **kw):
        self.fontName = "Helvetica"
        self.fontSize = 10
        self.textColor = None
        self.rise = 0
        self.us_lines = 0
        self.link = None
        self.backColor = None
        self.nobr = 0
        for k, v in kw.items():
            setattr(self, k, v)


# ── 模块元信息 ──────────────────────────────────────────────────────
check("version", _rl_accel.version, "0.9.1")
for fn in ("asciiBase85Encode", "asciiBase85Decode", "escapePDF", "fp_str",
           "sameFrag", "calcChecksum", "add32", "hex32", "unicode2T1",
           "instanceStringWidthT1", "instanceStringWidthTTF"):
    check_true(f"has {fn}", callable(getattr(_rl_accel, fn, None)))

# ── calcChecksum ────────────────────────────────────────────────────
for data in (b"", b"abc", b"abcd", b"Hello cruel world!", b"\x00\x00\x00\x00",
             bytes(range(256))):
    check(f"calcChecksum {data[:12]!r}", _rl_accel.calcChecksum(data),
          ref_calc_checksum(data))
check_true("calcChecksum returns unsigned 32-bit",
           _rl_accel.calcChecksum(b"\xff" * 4) == 0xFFFFFFFF)

# ── add32 / hex32 ───────────────────────────────────────────────────
check("add32 wrap", _rl_accel.add32(0xFFFFFFFF, 2), 1)
check("add32 plain", _rl_accel.add32(10, 20), 30)
check("hex32", _rl_accel.hex32(0xDEADBEEF), "0XDEADBEEF")
check("hex32 zero-pad", _rl_accel.hex32(0), "0X00000000")

# ── escapePDF ───────────────────────────────────────────────────────
for s in ("plain", "a\\b(c)", "line\nfeed\x00", "pdf<<>>%", ""):
    check(f"escapePDF {s!r}", _rl_accel.escapePDF(s), ref_escape_pdf(s))
check("escapePDF accepts bytes", _rl_accel.escapePDF(b"a(b)\x0c"),
      ref_escape_pdf("a(b)\x0c"))

# ── fp_str ──────────────────────────────────────────────────────────
for vals in ((1.5, 2.0), (0.0,), (123456789.0, 0.25), (-3.125, -1e-8),
             (1e20,), (0.1,), [1, 2, 3]):
    want = " ".join(ref_fp_one(float(v)) for v in vals)
    check(f"fp_str {tuple(vals)}", _rl_accel.fp_str(*vals), want)

# ── asciiBase85（与 stdlib base64.a85encode 等价，terminator '~>'） ──
for data in (b"", b"a", b"abc", b"abcd", b"Hello cruel world!",
             b"\x00\x00\x00\x00", b"\x00" * 8, bytes(range(64))):
    enc = _rl_accel.asciiBase85Encode(data)
    ref = base64.a85encode(data, adobe=False, pad=False).decode() + "~>"
    check(f"a85 encode {data[:10]!r}", enc, ref)
    check(f"a85 roundtrip {data[:10]!r}", _rl_accel.asciiBase85Decode(enc), data)
check_true("a85 'z' shortcut for zero group",
           _rl_accel.asciiBase85Encode(b"\x00\x00\x00\x00") == "z~>")

# ── unicode2T1 / instanceStringWidth* ───────────────────────────────
font = _T1Font()
pairs = _rl_accel.unicode2T1("AB", [font])
check("unicode2T1 size", len(pairs), 1)
check("unicode2T1 font", pairs[0][0] is font, True)
check("unicode2T1 bytes", pairs[0][1], b"AB")
check("instanceStringWidthT1", _rl_accel.instanceStringWidthT1(font, "AB", 10), 20.0)
check("instanceStringWidthT1 default enc",
      _rl_accel.instanceStringWidthT1(font, "AB", 10, "utf8"), 20.0)
ttf = _TTFFont()
check("instanceStringWidthTTF", _rl_accel.instanceStringWidthTTF(ttf, "AB", 10), 11.0)
check("instanceStringWidthTTF codepoint lookup",
      _rl_accel.instanceStringWidthTTF(ttf, "A", 10), 6.0)

# ── sameFrag ────────────────────────────────────────────────────────
a = _Frag()
check_true("sameFrag identical", _rl_accel.sameFrag(a, _Frag()) is True)
check_true("sameFrag differing", _rl_accel.sameFrag(a, _Frag(fontSize=12)) is False)
check_true("sameFrag cbDefn breaks",
           _rl_accel.sameFrag(a, _Frag(cbDefn=object())) is False)

# ── 参数类型校验 ────────────────────────────────────────────────────
try:
    _rl_accel.calcChecksum(123)
    check_true("calcChecksum rejects int", False, "(no exception)")
except TypeError:
    check_true("calcChecksum rejects int", True)

passed = sum(1 for c in CHECKS if c)
print(f"\nrl-accel 0.9.1 consumer API: {passed}/{len(CHECKS)} passed")
sys.exit(0 if passed == len(CHECKS) else 1)
