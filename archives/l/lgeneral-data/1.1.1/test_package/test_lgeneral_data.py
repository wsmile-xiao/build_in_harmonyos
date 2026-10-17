#!/usr/bin/env python3
"""lgeneral-data 数据包验证脚本。

用法: python3 test_lgeneral_data.py <data_dir> <package_folder>

验证的是**数据本体**而不是"文件存在"：
  * 上游 README 点名的 7 个数据目录必须齐全，且每个目录都有实质内容；
  * `scenlist` 里的 22 个剧本名必须逐条能在 `scenarios/kukgen/` 里找到 ——
    少一个剧本 = 游戏里那一场战役直接打不开；
  * `scenarios/kukgen/.order`（点开头文件）必须被拷贝出来 —— 这是 Conan
    `copy(self, "*", ...)` 的经典坑，丢了它剧本顺序就没了；
  * gfx/ 下 59 个地图/单位贴图必须都是合法 BMP（`BM` 魔数 + 位图头）；
  * sounds/ 下 8 个音效必须都是合法 RIFF/WAVE；
  * 单位表 / 国家表必须是可解析的 LGeneral 文本表（`@` 起始、`key<TAB>value` 行）；
  * 安装目录里不能混进构建产物或打包脚本。

任一断言失败 → 退出码 1（Conan test_package 随之失败）。
"""

import os
import struct
import sys

DATA_DIRS = ("campaigns", "gfx", "maps", "nations",
             "scenarios", "sounds", "units")
EXPECTED_SCENARIOS = 22
EXPECTED_BMP = 59
EXPECTED_WAV = 8
EXPECTED_MAPS = 61
EXPECTED_TERRAIN_BMP = 53
EXPECTED_UNIT_BMP = 5

_results = []


def check(ok, label) -> bool:
    _results.append((bool(ok), label))
    print(f"        [{'ok' if ok else 'FAIL'}] {label}")
    return bool(ok)


def walk_files(root, suffix):
    found = []
    for base, _dirs, files in os.walk(root):
        for name in files:
            if name.endswith(suffix):
                found.append(os.path.join(base, name))
    return sorted(found)


def is_bmp(path):
    with open(path, "rb") as handle:
        head = handle.read(18)
    if len(head) < 18 or head[:2] != b"BM":
        return False
    size, _r1, _r2, offset = struct.unpack("<IHHI", head[2:14])
    return size > 0 and offset > 0


def is_wave(path):
    with open(path, "rb") as handle:
        head = handle.read(12)
    return len(head) == 12 and head[:4] == b"RIFF" and head[8:12] == b"WAVE"


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: test_lgeneral_data.py <data_dir> <package_folder>")
        return 2

    data_dir, package_folder = sys.argv[1], sys.argv[2]
    print(f"[test] data_dir = {data_dir}")
    check(os.path.isdir(data_dir), f"share/games/lgeneral 目录存在 ({data_dir})")

    # ── 1. 上游 README 点名的 7 个数据目录 ───────────────────────────────
    for name in DATA_DIRS:
        path = os.path.join(data_dir, name)
        entries = os.listdir(path) if os.path.isdir(path) else []
        check(bool(entries), f"{name}/ 目录存在且非空（{len(entries)} 项）")

    # ── 2. scenlist 与剧本目录必须对得上 ────────────────────────────────
    scenlist = os.path.join(data_dir, "scenlist")
    check(os.path.isfile(scenlist) and os.path.getsize(scenlist) > 0,
          "scenlist 存在且非空")

    with open(scenlist, encoding="utf-8", errors="replace") as handle:
        listed = [line.strip().rstrip("*").strip() for line in handle
                  if line.strip()
                  and not line.startswith("Scenarios")
                  and not line.startswith("*")]
    check(len(listed) == EXPECTED_SCENARIOS,
          f"scenlist 列出 {EXPECTED_SCENARIOS} 个剧本（实际 {len(listed)}）")

    scen_dir = os.path.join(data_dir, "scenarios", "kukgen")
    entries = sorted(os.listdir(scen_dir)) if os.path.isdir(scen_dir) else []
    absent = [name for name in listed if name not in entries]
    check(not absent,
          f"scenlist 的每个剧本在 scenarios/kukgen/ 里都存在（缺 {absent[:5]}）")
    check(".order" in entries,
          "scenarios/kukgen/.order 点文件被保留（Conan copy('*') 的经典坑）")
    check(len(entries) == EXPECTED_SCENARIOS + 1,
          f"scenarios/kukgen/ 条目数 == {EXPECTED_SCENARIOS} 个剧本 + .order"
          f"（实际 {len(entries)}）")

    # ── 3. 贴图：59 个 BMP，全部合法 ────────────────────────────────────
    bmps = walk_files(os.path.join(data_dir, "gfx"), ".bmp")
    check(len(bmps) == EXPECTED_BMP,
          f"gfx/ 下 BMP 数量 == {EXPECTED_BMP}（实际 {len(bmps)}）")
    bad = [os.path.relpath(p, data_dir) for p in bmps if not is_bmp(p)]
    check(not bad, f"全部 BMP 都有合法 BM 魔数与位图头（异常 {bad[:3]}）")

    terrain = walk_files(os.path.join(data_dir, "gfx", "terrain"), ".bmp")
    check(len(terrain) == EXPECTED_TERRAIN_BMP,
          f"gfx/terrain/kukgen/ 地形贴图 == {EXPECTED_TERRAIN_BMP}（实际 {len(terrain)}）")
    units = walk_files(os.path.join(data_dir, "gfx", "units"), ".bmp")
    check(len(units) == EXPECTED_UNIT_BMP,
          f"gfx/units/kukgen/ 单位贴图 == {EXPECTED_UNIT_BMP}（实际 {len(units)}）")

    flag = os.path.join(data_dir, "gfx", "flags", "kukgen.bmp")
    check(os.path.isfile(flag) and is_bmp(flag), "gfx/flags/kukgen.bmp 存在且为合法 BMP")

    # ── 4. 音效：8 个 WAV，全部合法 ─────────────────────────────────────
    wavs = walk_files(os.path.join(data_dir, "sounds"), ".wav")
    check(len(wavs) == EXPECTED_WAV,
          f"sounds/ 下 WAV 数量 == {EXPECTED_WAV}（实际 {len(wavs)}）")
    bad_wav = [os.path.relpath(p, data_dir) for p in wavs if not is_wave(p)]
    check(not bad_wav, f"全部 WAV 都是合法 RIFF/WAVE（异常 {bad_wav[:3]}）")
    check(os.path.isfile(os.path.join(data_dir, "sounds", "LICENSE.sounds")),
          "sounds/LICENSE.sounds 随数据一起发布")

    # ── 5. 地图与战役 ──────────────────────────────────────────────────
    maps = os.path.join(data_dir, "maps", "kukgen")
    map_files = sorted(os.listdir(maps)) if os.path.isdir(maps) else []
    check(len(map_files) == EXPECTED_MAPS,
          f"maps/kukgen/ 地图文件数 == {EXPECTED_MAPS}（实际 {len(map_files)}）")
    check(os.path.isfile(os.path.join(data_dir, "maps", "kukgen.tdb")),
          "maps/kukgen.tdb 地面表存在")

    campaign = os.path.join(data_dir, "campaigns", "kukgen")
    check(os.path.isfile(campaign) and os.path.getsize(campaign) > 0,
          f"campaigns/kukgen 战役定义存在且非空"
          f"（{os.path.getsize(campaign) if os.path.isfile(campaign) else 0} 字节）")

    # ── 6. 单位表 / 国家表是可解析的 LGeneral 文本表 ────────────────────
    # LGeneral 的 .ndb/.udb 是自定义文本表：首行 '@'，字段行用 0xBB（»）分隔
    # key 与 value，段落用 '<name' 开始、单独一行 '>' 结束。
    for rel in ("nations/kukgen.ndb", "units/kukgen.udb"):
        path = os.path.join(data_dir, rel)
        if not check(os.path.isfile(path), f"{rel} 存在"):
            continue
        # 以 latin-1 读：分隔符是单字节 0xBB，用 UTF-8 读会被替换成 U+FFFD
        with open(path, encoding="latin-1") as handle:
            text = handle.read()
        lines = [ln for ln in text.splitlines() if ln.strip()]
        check(lines and lines[0].strip() == "@",
              f"{rel} 以 '@' 开头（LGeneral 表头约定）")
        fields = [ln for ln in lines if "\xbb" in ln]
        check(len(fields) >= 10
              and all(ln.split("\xbb", 1)[0].strip() and ln.split("\xbb", 1)[1].strip()
                      for ln in fields),
              f"{rel} 字段行用 0xBB 分隔 key/value 且两侧非空（{len(fields)} 行）")
        sections = [ln for ln in lines if ln.startswith("<")]
        check(len(sections) >= 5 and ">" in lines,
              f"{rel} 含 '<section' 段落标记与 '>' 段结束符"
              f"（{len(sections)} 个段落）")

    # ── 7. 文档与安装纯净性 ────────────────────────────────────────────
    docs = os.path.join(package_folder, "share", "doc", "lgeneral-data")
    doc_files = sorted(os.listdir(docs)) if os.path.isdir(docs) else []
    check(len(doc_files) == 5, f"docs/ 随包发布（{len(doc_files)} 个文件）")

    leaked = sorted(e for e in os.listdir(data_dir)
                    if e not in DATA_DIRS + ("scenlist",))
    check(not leaked,
          f"安装目录只含 7 个数据目录 + scenlist（发现 {leaked}）")

    lic_dir = os.path.join(package_folder, "licenses")
    lic_files = sorted(os.listdir(lic_dir)) if os.path.isdir(lic_dir) else []
    check(lic_files == ["COPYING", "LICENSE", "LICENSE.sounds"],
          f"licenses/ 含 COPYING + LICENSE + LICENSE.sounds（实际 {lic_files}）")

    passed = sum(1 for ok, _ in _results if ok)
    total = len(_results)
    print(f"\n        [test] {passed}/{total} assertions passed")
    if passed != total:
        print("FAILED assertions:")
        for ok, label in _results:
            if not ok:
                print(f"  - {label}")
        return 1
    print("All tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
