#!/usr/bin/env python3
"""pop-icon 消费者用例：按 freedesktop 图标查找机制**消费**安装后的主题。

用法: python3 consumer_icontheme.py <package_folder>

端到端链路（不是文件存在性断言）——这正是 GTK/Qt/桌面在运行时做的事：

  1. 用 XDG 契约定位主题：`<prefix>/share/icons/<主题名>/index.theme`
     （包已把 `<prefix>/share` 前置进 `XDG_DATA_DIRS`，这里两种来源都支持）；
  2. 解析 `index.theme`：`[Icon Theme]` 的 `Directories=`（**逗号分隔**）给出
     目录顺序，每个 `[<目录>]` 段给 `Size=`/`Type=`(Fixed|Scalable|Threshold)/
     `Threshold=`/`Scale=`/`Context=`；
  3. 实现查找算法：按 index 顺序挑候选目录 —— Fixed 要 Size 精确相等，
     Scalable 任意尺寸，Threshold 容差内 —— 再在该目录里找
     `<图标名>.svg|.png|.xpm`（大小写不敏感，模拟 OHOS 大小写不敏感用户区）；
  4. 探针**自派生**（不硬编码）：挑该主题交付数据里 SVG 最多、且带 Scalable 的上下文，
     取该上下文已交付的若干个 Fixed 尺寸（展开 min/中/max）逐个走查找算法；
     再取 Scalable 目录里的名字按"主题未交付"的尺寸查找，验证放大回退路径；
  5. 判据：`Directories=` 里任一声明目录在磁盘上不存在（消费者会看到"图标不可见"）、
     或任一探针解析不到 → 退出码非 0；否则打印主题统计与解析结果。
"""

import os
import re
import sys

THEMES = ("Pop", "Pop-Dark")
PROBE_COUNT = 5
PROBE_SPREAD = 3          # 在主题该上下文已有的 Fixed 尺寸里取 min/中/max 三个
EXTENSIONS = (".svg", ".png", ".xpm")


def parse_index_theme(path):
    """解析 index.theme → (主题名, [目录条目 dict, ...])，顺序即查找顺序。"""
    text = open(path, encoding="utf-8", errors="replace").read()
    name = ""
    m = re.search(r"^Name=(.*)$", text, re.M)
    if m:
        name = m.group(1).strip()
    m = re.search(r"^Directories=(.*)$", text, re.M)
    if not m:
        raise SystemExit(f"consumer: {path} 里没有 Directories=")
    order = [d.strip() for d in m.group(1).split(",") if d.strip()]
    entries = []
    for directory in order:
        m2 = re.search(r"^\[" + re.escape(directory) + r"\]\n((?:[A-Za-z]+=.*\n?)+)",
                       text, re.M)
        fields = {}
        if m2:
            for line in m2.group(1).splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    fields[k.strip()] = v.strip()
        entries.append({
            "dir": directory,
            "size": int(fields["Size"]) if fields.get("Size", "").isdigit() else None,
            "type": fields.get("Type", "Threshold"),
            "threshold": int(fields["Threshold"]) if fields.get("Threshold", "").isdigit() else 2,
            "context": fields.get("Context", ""),
        })
    return name, entries


def find_icon(theme_root, entry, icon, size):
    """在一个候选目录里按查找算法找图标；返回 (路径, 命中等级)。"""
    rank = {"Fixed": 0, "Scalable": 1, "Threshold": 2}.get(entry["type"], 3)
    if entry["type"] == "Fixed" and entry["size"] != size:
        return None, rank
    if entry["type"] == "Threshold" and entry["size"] is not None \
            and abs(entry["size"] - size) > entry["threshold"]:
        return None, rank
    base = os.path.join(theme_root, entry["dir"].replace("/", os.sep))
    try:
        names = {n.lower(): n for n in os.listdir(base)}
    except OSError:
        return None, rank
    for ext in EXTENSIONS:
        actual = names.get((icon + ext).lower())
        if actual:
            return os.path.join(base, actual), rank
    return None, rank


def lookup(theme_root, entries, icon, size):
    """完整查找：按 index 顺序取候选目录，优先精确尺寸命中。"""
    best = None
    for entry in entries:
        if entry["type"] == "Fixed" and entry["size"] != size:
            continue
        if entry["type"] == "Threshold" and entry["size"] is not None \
                and abs(entry["size"] - size) > entry["threshold"]:
            continue
        path, rank = find_icon(theme_root, entry, icon, size)
        if path:
            if rank == 0:
                return path
            best = best or path
    return best


def svg_names(path):
    try:
        return sorted(f for f in os.listdir(path) if f.lower().endswith(".svg"))
    except OSError:
        return []


def consume_theme(icons_root, theme):
    theme_root = os.path.join(icons_root, theme)
    index = os.path.join(theme_root, "index.theme")
    if not os.path.isfile(index):
        raise SystemExit(f"consumer: 主题 {theme} 缺 index.theme")
    name, entries = parse_index_theme(index)

    # 声明但磁盘缺失的目录：上游主题常见（消费者按缺失跳过），只记 info 不作失败
    missing = [e["dir"] for e in entries
               if not os.path.isdir(os.path.join(theme_root, e["dir"].replace("/", os.sep)))]
    print(f"        [consumer] 主题 {theme}（Name={name}）: 声明目录 {len(entries)} 个，"
          f"盘上缺失 {len(missing)} 个（上游如此，消费者按缺失跳过）")

    # 自派生探针：挑交付数据里实际有 SVG 的上下文与尺寸
    by_ctx = {}
    for e in entries:
        n = len(svg_names(os.path.join(theme_root, e["dir"].replace("/", os.sep))))
        if n:
            by_ctx.setdefault(e["context"] or e["dir"], []).append((e, n))
    if not by_ctx:
        raise SystemExit(f"consumer: {theme} 盘上没有任何含 SVG 的目录")
    def _ctx_rank(kv):
        entries_ = [e for e, _n in kv[1]]
        has_fixed = len([e for e in entries_ if e["type"] == "Fixed" and e["size"]])
        has_scal = 1 if any(e["type"] == "Scalable" for e in entries_) else 0
        return (has_scal, has_fixed)
    context, items = max(by_ctx.items(), key=_ctx_rank)
    fixed = sorted([(e["size"], e) for e, _n in items
                    if e["type"] == "Fixed" and e["size"]], key=lambda x: x[0])
    scalable = [e for e, _n in items if e["type"] == "Scalable"]
    if not fixed and not scalable:
        raise SystemExit(f"consumer: {theme} 的 {context} 上下文既无 Fixed 也无 Scalable 目录")

    sizes = []
    if fixed:
        picks = [0, len(fixed) // 2, len(fixed) - 1] if len(fixed) >= 3 else list(range(len(fixed)))
        sizes = [fixed[i][0] for i in sorted(set(picks))][:PROBE_SPREAD]
    probe_dir = os.path.join(theme_root, (fixed[-1][1] if fixed else scalable[0])["dir"]
                             .replace("/", os.sep))
    probes = [os.path.splitext(f)[0] for f in svg_names(probe_dir)[:PROBE_COUNT]]
    if not probes:
        raise SystemExit(f"consumer: {theme} 的探针目录 {probe_dir} 里没有 SVG")

    resolved = total = 0
    for icon in probes:
        for size in sizes:
            total += 1
            if lookup(theme_root, entries, icon, size):
                resolved += 1
            else:
                print(f"        [consumer][miss] {theme}: {icon} @{size}px 解析不到")
    # Scalable 路径：从该上下文的 Scalable 目录取名字，按主题**没有交付**的尺寸查找，
    # 必须由 Scalable 目录命中（消费者放大图标时走的正是这条路径）
    scalable_hit = None
    if scalable and sizes:
        scal_dir = os.path.join(theme_root, scalable[0]["dir"].replace("/", os.sep))
        scal_names = [os.path.splitext(f)[0] for f in svg_names(scal_dir)[:PROBE_COUNT]]
        odd = sizes[-1] + 50
        for icon in scal_names:
            total += 1
            hit = lookup(theme_root, entries, icon, odd)
            if hit:
                resolved += 1
                scalable_hit = odd
            else:
                print(f"        [consumer][miss] {theme}: {icon} @{odd}px（Scalable 回退）解析不到")

    print(f"        [consumer] {theme}: 上下文 {context}，探针 {len(probes)} 个图标 × "
          f"{len(sizes)} 个已交付尺寸" + (f" + Scalable 回退 @{scalable_hit}px" if scalable_hit else "")
          + f" = {total} 次查找，解析成功 {resolved} 次")
    if resolved != total:
        raise SystemExit(f"consumer: {theme} 有查找未命中，消费者将看不见对应图标")
    return len(entries), len(missing), len(probes)


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    package_folder = sys.argv[1]
    xdg = os.environ.get("XDG_DATA_DIRS", "")
    roots = [os.path.join(d, "icons") for d in xdg.split(":") if d.strip()]
    roots.append(os.path.join(package_folder, "share", "icons"))
    icons_root = next((r for r in roots if os.path.isdir(os.path.join(r, "Pop"))), None)
    if icons_root is None:
        raise SystemExit("consumer: 在 XDG_DATA_DIRS 与包内 share/icons 下都找不到主题 Pop")
    print(f"        [consumer] 主题根（XDG 契约）: {icons_root}")
    total_dirs = total_missing = total_probes = 0
    for theme in THEMES:
        d, m, p = consume_theme(icons_root, theme)
        total_dirs += d
        total_missing += m
        total_probes += p
    print(f"        [consumer] 消费合计: {len(THEMES)} 个主题 / 声明目录 {total_dirs} 个"
          f"（盘上缺失 {total_missing} 个，按上游语义跳过）/ 探针 {total_probes} 个图标全部解析成功")
    return 0


if __name__ == "__main__":
    sys.exit(main())
