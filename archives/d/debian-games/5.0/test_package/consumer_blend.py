#!/usr/bin/env python3
r"""Debian Pure Blend 消费者用例：按 tasksel/blends 的方式**消费**已安装的 blend 数据。

用法: python3 consumer_blend.py <package_folder> [out_dir]

端到端消费链路（不是文件存在性断言）：

  1. `share/tasksel/descs/<blend>-tasks.desc` —— **tasksel 的输入**：deb822 段落，
     根任务（无 `Parent:`）用 `Parent:` 挂若干子任务，每个子任务用 `Key:` 指向
     blend 里的任务键；
  2. `share/blends/<blend>/tasks/<键>` —— **blend 任务源文件**（deb822，可重复
     `Depends:` 字段、`\` 续行、`,` 分隔、`|` 备选、`(>= x)` 版本约束、`[arch]` 限定，
     以及 `X-Depends:` 跨任务引用）；
  3. 按上述语义逐层解析、跨任务解析，产出这份 blend 的最终包清单。

探针自适配：blend 名与键名全部从**交付数据本身**推导（desc 的根 `Task:` 即 blend 名；
子任务 `Key: <前缀>-<名字>` 通过"逐段剥前缀"定位 `tasks/<名字>`），不硬编码任何包名。

  <out_dir>/blend-tasks.txt   任务树 + 每任务解析出的包数（人工复核用）
  <out_dir>/packages.txt      最终包清单（去重保序）

不给 out_dir 时只在内存完成整条链路并把结果打到 stdout（CI/测试用这个形态，
**不在源码树落文件**）。退出码：任一 `Key` 解不出任务源文件、或最终清单为空 → 非 0。
"""

import os
import re
import sys

TASKS_REL = os.path.join("share", "blends")
DESCS_REL = os.path.join("share", "tasksel", "descs")


def parse_deb822(text):
    """解析 deb822 文本 → [{字段: [值, ...]}, ...]（保留重复字段与续行）。"""
    stanzas, cur = [], {}
    for raw in text.splitlines():
        if not raw.strip():
            if cur:
                stanzas.append(cur)
                cur = {}
            continue
        if raw[0] in " \t":                       # 续行：接到上一个字段
            if cur:
                cur[list(cur)[-1]][-1] += "\n" + raw.strip()
            continue
        if ":" not in raw:
            continue
        field, value = raw.split(":", 1)
        cur.setdefault(field.strip(), []).append(value.strip())
    if cur:
        stanzas.append(cur)
    return stanzas


def expand_list(value):
    """展开 deb822 列表字段：去续行/反斜杠 → 逗号切分 → 备选取首个 → 剥版本/架构限定。"""
    items = []
    for part in value.replace("\\", " ").replace("\n", " ").split(","):
        part = part.strip()
        if not part:
            continue
        part = part.split("|")[0].strip()
        part = re.sub(r"\s*\([^)]*\)\s*$", "", part)
        part = re.sub(r"\s*\[[^\]]*\]\s*$", "", part)
        part = part.split()[0] if part.split() else ""
        if part:
            items.append(part)
    return items


def find_desc(package_folder, blend):
    """定位 tasksel 描述文件：优先 <blend>-tasks.desc，其次该目录下唯一的 *.desc。"""
    descs_dir = os.path.join(package_folder, DESCS_REL)
    if not os.path.isdir(descs_dir):
        raise SystemExit(f"consumer: 缺少 {DESCS_REL}（tasksel 消费入口）")
    names = sorted(n for n in os.listdir(descs_dir) if n.endswith(".desc"))
    if not names:
        raise SystemExit(f"consumer: {DESCS_REL} 下没有 *.desc")
    for cand in (f"{blend}-tasks.desc", blend + ".desc"):
        if cand in names:
            return os.path.join(descs_dir, cand), cand
    if len(names) == 1:
        return os.path.join(descs_dir, names[0]), names[0]
    raise SystemExit(f"consumer: 无法确定 {blend} 对应的 desc（候选: {names}）")


def detect_blend(package_folder):
    """从交付数据推导 blend 名：share/blends/ 下的目录名（唯一时直接取）。"""
    root = os.path.join(package_folder, TASKS_REL)
    if not os.path.isdir(root):
        raise SystemExit(f"consumer: 缺少 {TASKS_REL}/<blend>/tasks")
    dirs = sorted(d for d in os.listdir(root)
                  if os.path.isdir(os.path.join(root, d, "tasks")))
    if not dirs:
        raise SystemExit(f"consumer: {TASKS_REL} 下没有带 tasks/ 的 blend")
    return dirs[0] if len(dirs) == 1 else dirs


def resolve_task_file(tasks_dir, key):
    """按 `Key:` 定位任务源文件：逐段剥前缀（如 junior-art / gis-data -> art / data）。"""
    cands, k = [key], key
    while "-" in k:
        k = k.split("-", 1)[1]
        cands.append(k)
    for cand in cands:
        p = os.path.join(tasks_dir, cand)
        if os.path.isfile(p):
            return p, cand
    return None, None


def load_task(tasks_dir, key):
    """解析一个任务源文件：返回 (文件名, 包集合, 跨任务引用, Suggests 数)。

    blend 语义：任务的包集合 = `Depends:`（硬依赖）∪ `Recommends:`（默认安装）——
    blends-dev 生成 metapackage 时两者都会进；`Suggests:` 只作可选，单独计数。
    有的 blend（如 debian-junior/debian-astro）整份任务只用 `Recommends:`。
    """
    path, name = resolve_task_file(tasks_dir, key)
    if path is None:
        raise SystemExit(f"consumer: 任务键 {key} 在 tasks/ 下找不到对应任务源文件")
    with open(path, encoding="utf-8", errors="replace") as handle:
        stanzas = parse_deb822(handle.read())
    if not stanzas:
        raise SystemExit(f"consumer: 任务源文件 {name} 解析不出任何 deb822 段落")
    pkgs, xdeps, suggests = [], [], 0
    for st in stanzas:
        for field in ("Depends", "Recommends"):
            for value in st.get(field, []):
                pkgs += expand_list(value)
        for value in st.get("X-Depends", []):
            xdeps += expand_list(value)
        for value in st.get("Suggests", []):
            suggests += len(expand_list(value))
    if not pkgs and not xdeps:
        raise SystemExit(f"consumer: 任务源文件 {name} 既无 Depends/Recommends 也无 X-Depends")
    return name, pkgs, xdeps, suggests


def resolve(package_folder, out_dir=None):
    blend = detect_blend(package_folder)
    if isinstance(blend, list):                    # 多个 blend：逐个消费
        return max(resolve_one(package_folder, b, out_dir) for b in blend)
    return resolve_one(package_folder, blend, out_dir)


def resolve_one(package_folder, blend, out_dir=None):
    desc_path, desc_name = find_desc(package_folder, blend)
    with open(desc_path, encoding="utf-8", errors="replace") as handle:
        stanzas = parse_deb822(handle.read())
    roots = [s for s in stanzas if "Task" in s and "Parent" not in s]
    if not roots:
        raise SystemExit("consumer: 描述文件里没有根任务（缺 Task/Parent 结构）")
    root = roots[0]["Task"][0]
    children = [s for s in stanzas if s.get("Parent", [None])[0] == root]

    tasks_dir = os.path.join(package_folder, TASKS_REL, blend, "tasks")
    tree, final, warnings = [], [], []
    for st in children:
        task = st["Task"][0]
        keys = st.get("Key", [])
        if not keys:
            warnings.append(f"{task}: 描述段无 Key，无法解析包清单")
            continue
        key = keys[0].strip()
        src, deps, xdeps, suggests = load_task(tasks_dir, key)
        for x in xdeps:                    # 跨任务引用：同 blend 内递归展开
            if resolve_task_file(tasks_dir, x)[0] is None:
                warnings.append(f"{task}: X-Depends 引用了本 blend 之外的任务 {x}（跳过）")
                continue
            _n, sub, _x, _s = load_task(tasks_dir, x)
            deps = deps + [p for p in sub if p not in deps]
        tree.append((task, key, src, len(deps), len(xdeps), suggests))
        for pkg in deps:
            if pkg not in final:
                final.append(pkg)
    if not final:
        raise SystemExit("consumer: 解析结果为空清单，blend 数据不可消费")

    lines = [f"# blend: {blend}  描述: {desc_name}  根任务: {root}",
             f"# 子任务 {len(tree)} 个，解析包数合计 {sum(t[3] for t in tree)}，"
             f"去重后 {len(final)}"]
    lines += [f"{task}\tkey={key}\tsource={src}\tpackages={n}"
              f"\tx-deps={xd}\tsuggests={sg}"
              for task, key, src, n, xd, sg in tree]
    lines += [f"warning\t{w}" for w in warnings]

    print(f"        [consumer] blend {blend}: 解析 {len(tree)} 个子任务 → "
          f"最终包清单 {len(final)} 个（去重后）")
    for line in lines:
        print(f"        [consumer] {line}")
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, "blend-tasks.txt"), "w", encoding="utf-8") as h:
            h.write("\n".join(lines) + "\n")
        with open(os.path.join(out_dir, "packages.txt"), "w", encoding="utf-8") as h:
            h.write("\n".join(final) + "\n")
        print(f"        [consumer] 输出: {out_dir}/blend-tasks.txt, packages.txt")
    return 0


def main():
    if len(sys.argv) not in (2, 3):
        print(__doc__)
        return 2
    return resolve(sys.argv[1], sys.argv[2] if len(sys.argv) == 3 else None)


if __name__ == "__main__":
    sys.exit(main())
