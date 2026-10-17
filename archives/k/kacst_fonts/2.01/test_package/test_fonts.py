#!/usr/bin/env python3
"""kacst_fonts 2.01 适配自检（M，非上游用例）。

用法: python3 test_fonts.py <package_folder>

字体集齐备性、字体文件合法性、许可与安装纯净性。上游 N=0（无测试目录、无
autopkgtest，Debian 源包只有 dh + fontconfig 片段），故这些断言是**适配自检**，
与消费者用例（consumer_fonts.py）分列申报。
"""

import os
import struct
import sys

FONT_REL = os.path.join("share", "fonts", "truetype", "kacst")
EXPECTED = (
    "KacstArt", "KacstBook", "KacstDecorative", "KacstDigital", "KacstFarsi",
    "KacstLetter", "KacstNaskh", "KacstOffice", "KacstPen", "KacstPoster",
    "KacstQurn", "KacstScreen", "KacstTitle", "KacstTitleL",
)
SFNT_TAGS = (b"\x00\x01\x00\x00", b"true", b"OTTO")
FORBIDDEN = ("Makefile", "debian", "configure", "CMakeLists.txt", "README.md.deb")

_results = []


def check(ok, label) -> bool:
    _results.append((bool(ok), label))
    print(f"        [{'ok' if ok else 'FAIL'}] {label}")
    return bool(ok)


def family_of(path):
    with open(path, "rb") as handle:
        buf = handle.read()
    if buf[:4] not in SFNT_TAGS:
        return None
    num = struct.unpack(">H", buf[4:6])[0]
    tabs = {}
    for i in range(num):
        rec = 12 + 16 * i
        tag = buf[rec:rec + 4].decode("latin-1")
        off, length = struct.unpack(">II", buf[rec + 8:rec + 16])
        tabs[tag] = (off, length)
    if "name" not in tabs:
        return None
    off, length = tabs["name"]
    nb = buf[off:off + length]
    _fmt, count, str_off = struct.unpack(">HHH", nb[:6])
    for i in range(count):
        rec = 6 + 12 * i
        pid, _eid, _lid, nid, ln, no = struct.unpack(">HHHHHH", nb[rec:rec + 12])
        if nid != 1:
            continue
        raw = nb[str_off + no:str_off + no + ln]
        try:
            return (raw.decode("utf-16-be") if pid == 3 else raw.decode("latin-1")).strip()
        except UnicodeDecodeError:
            continue
    return None


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    pkg = sys.argv[1]
    fontdir = os.path.join(pkg, FONT_REL)

    check(os.path.isdir(fontdir), f"{FONT_REL}/ 存在（XDG 字体目录契约）")
    files = sorted(f for f in os.listdir(fontdir)) if os.path.isdir(fontdir) else []
    ttfs = [f for f in files if f.lower().endswith(".ttf")]
    check(len(ttfs) == len(EXPECTED), f"TrueType 字体数 == {len(EXPECTED)}（实际 {len(ttfs)}）")
    check(sorted(os.path.splitext(f)[0] for f in ttfs) == sorted(EXPECTED),
          "字体文件名集合与上游一致（KacstArt…KacstTitleL 共 14 套）")

    families = [family_of(os.path.join(fontdir, f)) for f in ttfs]
    check(all(families), "每套字体都能解析出 name 表的家族名（sfnt 表目录合法）")
    check(len(set(f for f in families if f)) == len([f for f in families if f]),
          "家族名互不重复（文本栈按家族名索引，重复会冲突）")

    check(os.path.isfile(os.path.join(pkg, "licenses", "LICENSE"))
          and all(os.path.isfile(os.path.join(pkg, "share", "doc", "kacst_fonts", n))
                  for n in ("README", "Copyright")),
          "LICENSE 与 README/Copyright 已交付")

    leaked = [e for e in FORBIDDEN if os.path.exists(os.path.join(pkg, FONT_REL, e))]
    check(not leaked, f"字体目录未混入上游维护/构建文件（发现 {leaked}）")

    passed = sum(1 for ok, _ in _results if ok)
    total = len(_results)
    print(f"\n        [test] {passed}/{total} assertions passed")
    if passed != total:
        for ok, label in _results:
            if not ok:
                print(f"  - {label}")
        return 1
    print("All tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
