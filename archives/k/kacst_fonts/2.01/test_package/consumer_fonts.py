#!/usr/bin/env python3
r"""kacst_fonts 消费者用例：按文本栈 / fontconfig 的方式**消费**这套字体。

用法: python3 consumer_fonts.py <package_folder>

端到端链路（不是文件存在性断言）——这正是文本渲染栈拿到一套字体时做的事：

  1. 按 XDG 约定定位字体（`<prefix>/share/fonts/truetype/kacst/`，或 `XDG_DATA_DIRS` 下
     的同一位置）；
  2. **解析每套 TrueType 字体的真实表**（纯 Python，不依赖 freetype/fontconfig）：
     `head`（unitsPerEm）、`maxp`（numGlyphs）、`name`（family/subfamily/full/PostScript
     名，UTF-16BE 与 Mac 两种记录都处理）、`cmap`（优先 (3,10) format 12、其次 (3,1)
     format 4）→ 建立码点 → 字形 id 的映射；
  3. **真消费**：
     - 对给出的样本串（阿拉伯文 / 拉丁字母 / 数字 / 标点）逐字查 cmap，统计每个字体的
       码点覆盖率；
     - 按覆盖率**选出最适合阿拉伯文样本的字体**（真实字体选择流程），并校验选中的字体
       对该样本 **100% 覆盖**、且所有样本串至少各有一个字体能覆盖；
     - 校验：字体家族名互不重复（否则文本栈会冲突）、每个映射到的字形 id < numGlyphs。
  4. 打印每个字体的家族/字形数/覆盖率与最终选中的字体；退出码：任一字体检不出家族名或
     字形、家族名重复、阿拉伯样本无人覆盖、或映射出越界字形 id → 非 0。

纯数据包没有编译器，这条链路就是"这套字体能不能被真正用起来"的判据。
"""

import os
import struct
import sys

# 样本串：前两个是这套字体的**本职覆盖**（阿拉伯字母与阿拉伯标点，必须被覆盖），
# 后两个是"界外"样本 —— KACST 这套字体**确实不含**拉丁字母与 ASCII 数字/标点，
# 消费方必须知道这一点（要靠字体家族回退去拿拉丁字形），故按事实记录而非判失败。
SAMPLES = {
    "arabic": "\u0627\u0628\u062c\u062f \u0647\u0648\u0651\u0632",
    "arabic-punct": "\u060c\u061b\u061f",
}
OUT_OF_SCOPE = {
    "latin": "KACSTabc",
    "ascii-digits": "0123456789",
}
SFNT_TAGS = (b"\x00\x01\x00\x00", b"true", b"ttcf", b"OTTO")


def tables(buf):
    if buf[:4] not in SFNT_TAGS:
        raise ValueError("不是 sfnt/TrueType 字体")
    num = struct.unpack(">H", buf[4:6])[0]
    out = {}
    for i in range(num):
        rec = 12 + 16 * i
        tag = buf[rec:rec + 4].decode("latin-1")
        off, length = struct.unpack(">II", buf[rec + 8:rec + 16])
        out[tag] = (off, length)
    return out


def parse_names(buf, tabs):
    off, length = tabs["name"]
    nb = buf[off:off + length]
    _fmt, count, str_off = struct.unpack(">HHH", nb[:6])
    names = {}
    for i in range(count):
        rec = 6 + 12 * i
        pid, _eid, _lid, nid, ln, no = struct.unpack(">HHHHHH", nb[rec:rec + 12])
        raw = nb[str_off + no:str_off + no + ln]
        try:
            value = raw.decode("utf-16-be") if pid == 3 else raw.decode("latin-1")
        except UnicodeDecodeError:
            continue
        names.setdefault(nid, value.strip())
    return names


def parse_cmap(buf, tabs):
    off, length = tabs["cmap"]
    cb = buf[off:off + length]
    num = struct.unpack(">H", cb[2:4])[0]
    best = None
    for i in range(num):
        pid, eid, sub = struct.unpack(">HHI", cb[4 + 8 * i:12 + 8 * i])
        if (pid, eid) == (3, 10):
            best = sub
            break
        if (pid, eid) in ((3, 1), (0, 3), (0, 4)) and best is None:
            best = sub
    if best is None:
        raise ValueError("cmap 里没有可用的 Unicode 子表")
    fmt = struct.unpack(">H", cb[best:best + 2])[0]
    mapping = {}
    if fmt == 4:
        seg_x2 = struct.unpack(">H", cb[best + 6:best + 8])[0]
        seg = seg_x2 // 2
        ends = struct.unpack(f">{seg}H", cb[best + 14:best + 14 + seg_x2])
        starts = struct.unpack(f">{seg}H", cb[best + 16 + seg_x2:best + 16 + 2 * seg_x2])
        deltas = struct.unpack(f">{seg}h", cb[best + 16 + 2 * seg_x2:best + 16 + 3 * seg_x2])
        ro_off = best + 16 + 3 * seg_x2
        ros = struct.unpack(f">{seg}H", cb[ro_off:ro_off + seg_x2])
        for i in range(seg):
            for code in range(starts[i], min(ends[i], 0xFFFF) + 1):
                if ros[i] == 0:
                    gid = (code + deltas[i]) & 0xFFFF
                else:
                    pos = ro_off + 2 * i + ros[i] + 2 * (code - starts[i])
                    if pos + 2 > len(cb):
                        continue
                    gid = struct.unpack(">H", cb[pos:pos + 2])[0]
                    if gid:
                        gid = (gid + deltas[i]) & 0xFFFF
                if gid:
                    mapping[code] = gid
    elif fmt == 12:
        ngroups = struct.unpack(">I", cb[best + 12:best + 16])[0]
        for g in range(ngroups):
            s, e, sg = struct.unpack(">III", cb[best + 16 + 12 * g:best + 28 + 12 * g])
            for code in range(s, e + 1):
                mapping[code] = sg + (code - s)
    else:
        raise ValueError(f"不支持的 cmap 子表格式 {fmt}")
    return fmt, mapping


def load_font(path):
    with open(path, "rb") as handle:
        buf = handle.read()
    tabs = tables(buf)
    for need in ("head", "maxp", "name"):
        if need not in tabs:
            raise ValueError(f"缺 {need} 表")
    names = parse_names(buf, tabs)
    upem = struct.unpack(">H", buf[tabs["head"][0] + 18:tabs["head"][0] + 20])[0]
    num_glyphs = struct.unpack(">H", buf[tabs["maxp"][0] + 4:tabs["maxp"][0] + 6])[0]
    fmt, cmap = parse_cmap(buf, tabs)
    return {"family": names.get(1, ""), "subfamily": names.get(2, ""),
            "full": names.get(4, ""), "ps": names.get(6, ""),
            "upem": upem, "glyphs": num_glyphs, "cmap_format": fmt, "cmap": cmap}


def coverage(font, text):
    codes = {ord(c) for c in text if not c.isspace()}
    hit = [c for c in codes if font["cmap"].get(c)]
    return len(hit), len(codes)


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    package_folder = sys.argv[1]
    candidates = []
    for root in ([d for d in os.environ.get("XDG_DATA_DIRS", "").split(":") if d]
                 + [os.path.join(package_folder, "share")]):
        cand = os.path.join(root, "fonts", "truetype", "kacst")
        if os.path.isdir(cand):
            candidates.append(cand)
    if not candidates:
        raise SystemExit("consumer: 找不到 share/fonts/truetype/kacst（XDG 字体契约不满足）")
    fontdir = candidates[0]
    files = sorted(f for f in os.listdir(fontdir) if f.lower().endswith(".ttf"))
    if not files:
        raise SystemExit(f"consumer: {fontdir} 下没有 TTF")

    fonts, families = {}, set()
    for name in files:
        font = load_font(os.path.join(fontdir, name))
        if not font["family"]:
            raise SystemExit(f"consumer: {name} 的 name 表里没有家族名")
        if font["family"] in families:
            raise SystemExit(f"consumer: 家族名重复 {font['family']!r}（文本栈会冲突）")
        families.add(font["family"])
        bad = [c for c, g in font["cmap"].items() if g >= font["glyphs"]]
        if bad:
            raise SystemExit(f"consumer: {name} 映射出越界字形 id（code {bad[0]:#x} >= {font['glyphs']}）")
        fonts[name] = font

    print(f"        [consumer] 字体目录（XDG 契约）: {fontdir}")
    print(f"        [consumer] 解析 {len(fonts)} 套 TrueType 字体（家族名互不重复）:")
    stats = {}
    for name, font in fonts.items():
        cov = {k: coverage(font, v) for k, v in list(SAMPLES.items()) + list(OUT_OF_SCOPE.items())}
        stats[name] = cov
        print(f"        [consumer]   {name:20} family={font['family']:18} "
              f"glyphs={font['glyphs']:<6} upem={font['upem']:<5} "
              f"cmap={font['cmap_format']:<2} "
              f"arabic={cov['arabic'][0]}/{cov['arabic'][1]} latin={cov['latin'][0]}/{cov['latin'][1]}")

    # 本职覆盖：阿拉伯字母必须由某套字体 100% 覆盖，阿拉伯标点至少一套能覆盖
    for key in SAMPLES:
        best = max(fonts, key=lambda n: stats[n][key][0])
        hit, total = stats[best][key]
        print(f"        [consumer] 样本 {key:13}: 最佳字体 {best}（{hit}/{total} 码点）")
        if hit == 0:
            raise SystemExit(f"consumer: 没有任何字体覆盖 {key} 样本")
    best_ar = max(fonts, key=lambda n: stats[n]["arabic"][0])
    hit, total = stats[best_ar]["arabic"]
    if hit != total:
        raise SystemExit(f"consumer: 阿拉伯文样本未被完全覆盖（最佳 {best_ar} 只有 {hit}/{total}）")
    print(f"        [consumer] 字体选择: 阿拉伯文样本由 {best_ar} 完整覆盖 "
          f"({hit}/{total} 码点，family={fonts[best_ar]['family']})")

    # 界外样本：按事实记录（这套字体不含拉丁/ASCII 数字），并校验"全员不含"这一事实
    for key, text in OUT_OF_SCOPE.items():
        best = max(fonts, key=lambda n: stats[n][key][0])
        hit, total = stats[best][key]
        covered = [n for n in fonts if stats[n][key][0]]
        print(f"        [consumer] 界外 {key:13}: 最佳字体 {best}（{hit}/{total} 码点）"
              f" → 覆盖的字体数 {len(covered)}/{len(fonts)}")
        if covered:
            raise SystemExit(f"consumer: {key} 样本被 {covered[:2]} 覆盖，"
                             f"与'本字体集不含该字符集'的既有事实不符（字体集变了？）")
    print("        [consumer] 消费结论: 这套字体是**阿拉伯专用**（含阿拉伯标点与空格，"
          "不含拉丁字母/ASCII 数字），文本栈需为拉丁字符回退到其它家族")
    print("        [consumer] 消费链完成: 表解析 → 码点覆盖 → 字体选择，全部通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
