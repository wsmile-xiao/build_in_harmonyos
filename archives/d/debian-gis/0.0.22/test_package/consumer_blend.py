#!/usr/bin/env python3
"""debian-gis 消费者用例：按 tasksel/blends 的方式**消费**已安装的 blend 数据。

用法: python3 consumer_blend.py <package_folder> [out_dir]

不给 out_dir 时只在内存里完成整条链路并把结果打到 stdout（CI/测试用这个
形态，**不在源码树里落任何文件**）；给了 out_dir 才会额外写出
blend-tasks.txt / packages.txt（人工复核用）。

这是一条端到端的消费链路（不是文件存在性断言）：消费者只拿到安装后的
prefix，凭 Debian 生态既有的两份产物把 blend 解出来——

  1. `share/tasksel/descs/debian-gis-tasks.desc` —— **tasksel 的输入**：
     deb822 段落，根任务 `debian-gis` 用 `Parent:` 挂 8 个子任务，
     每个子任务用 `Key:` 指向 blend 里的任务键；
  2. `share/blends/debian-gis/tasks/<键>` —— **blend 任务源文件**：
     `Key: gis-gps` → 任务文件 `gps`，包清单在（可重复出现的）
     `Depends:` 字段里，支持 `\\` 续行、`,` 分隔、`|` 备选、`(>= x)` 版本约束；
     另有 `X-Depends:` 做**跨任务引用**（如 `gis-osm` 引到别的任务）。

消费者按上述语义逐层解析、跨任务解析，产出这份 blend 的最终包清单：

  <out_dir>/blend-tasks.txt   任务树 + 每任务解析出的包数（供人核对）
  <out_dir>/packages.txt      最终包清单（去重保序，一行一个）

退出码：任一 `Key` 找不到对应任务源文件、或最终清单为空 → 非 0（CI 据此判定）；
`X-Depends` 指向本 blend 之外的任务键只记入 `blend-tasks.txt` 的 warning 行，
不作为失败（那是上游数据的已知跨 blend 引用）。
"""

import os
import re
import sys

DESC_REL = os.path.join("share", "tasksel", "descs", "debian-gis-tasks.desc")
TASKS_REL = os.path.join("share", "blends", "debian-gis", "tasks")
KEY_PREFIX = "gis-"


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
    """展开 deb822 列表字段：去续行 → 按 `,` 切分 → 备选取首个 → 剥版本/架构限定。"""
    items = []
    # 先吃掉所有续行反斜杠：`a, \\` + 换行 + `\\` + 换行 这种连写会切出孤立 "\"
    for part in value.replace("\\", " ").replace("\n", " ").split(","):
        part = part.strip()
        if not part:
            continue
        part = part.split("|")[0].strip()                    # `a | b` 取 a
        part = re.sub(r"\s*\([^)]*\)\s*$", "", part)          # 去 (>= x)
        part = re.sub(r"\s*\[[^\]]*\]\s*$", "", part)         # 去 [arch]
        part = part.split()[0] if part.split() else ""        # 去 arch 后缀
        if part:
            items.append(part)
    return items


def load_task(tasks_dir, key):
    """按 `Key:` 找到 blend 任务源文件并解析出 Depends / X-Depends。"""
    name = key[len(KEY_PREFIX):] if key.startswith(KEY_PREFIX) else key
    path = None
    for cand in (name, key):
        p = os.path.join(tasks_dir, cand)
        if os.path.isfile(p):
            path = p
            break
    if path is None:
        raise SystemExit(f"consumer: 任务键 {key} 在 {TASKS_REL} 下无对应任务源文件")
    with open(path, encoding="utf-8", errors="replace") as handle:
        stanzas = parse_deb822(handle.read())
    deps, xdeps = [], []
    for st in stanzas:
        for value in st.get("Depends", []):
            deps += expand_list(value)
        for value in st.get("X-Depends", []):
            xdeps += expand_list(value)
    if not deps:
        raise SystemExit(f"consumer: 任务源文件 {os.path.basename(path)} 未解析出任何 Depends")
    return os.path.basename(path), deps, xdeps


def resolve(package_folder, out_dir=None):
    desc_path = os.path.join(package_folder, DESC_REL)
    if not os.path.isfile(desc_path):
        raise SystemExit(f"consumer: tasksel 描述文件缺失: {DESC_REL}")
    with open(desc_path, encoding="utf-8", errors="replace") as handle:
        stanzas = parse_deb822(handle.read())

    roots = [s for s in stanzas if "Task" in s and "Parent" not in s]
    if not roots:
        raise SystemExit("consumer: 描述文件里没有根任务（缺 Task/Parent 结构）")
    root = roots[0]["Task"][0]
    children = [s for s in stanzas if s.get("Parent", [None])[0] == root]

    tasks_dir = os.path.join(package_folder, TASKS_REL)
    tree, final, warnings = [], [], []
    for st in children:
        task = st["Task"][0]
        keys = st.get("Key", [])
        if not keys:
            warnings.append(f"{task}: 描述段无 Key，无法解析包清单")
            continue
        key = keys[0].strip()
        src, deps, xdeps = load_task(tasks_dir, key)
        for x in xdeps:
            xn = x[len(KEY_PREFIX):] if x.startswith(KEY_PREFIX) else x
            if not os.path.isfile(os.path.join(tasks_dir, xn)):
                warnings.append(f"{task}: X-Depends 引用了本 blend 之外的任务 {x}（跳过）")
        tree.append((task, key, src, len(deps)))
        for pkg in deps:
            if pkg not in final:
                final.append(pkg)

    if not final:
        raise SystemExit("consumer: 解析结果为空清单，blend 数据不可消费")

    lines = [f"# blend 根任务: {root}",
             f"# 子任务 {len(tree)} 个，解析包数合计 {sum(t[3] for t in tree)}，"
             f"去重后 {len(final)}"]
    lines += [f"{task}\tkey={key}\tsource={src}\tpackages={count}"
              for task, key, src, count in tree]
    lines += [f"warning\t{w}" for w in warnings]

    print(f"        [consumer] blend {root}: 解析 {len(tree)} 个子任务 → "
          f"最终包清单 {len(final)} 个（去重后）")
    for line in lines:
        print(f"        [consumer] {line}")

    if out_dir:                       # 只做人工复核时才落盘（默认不写源码树）
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, "blend-tasks.txt"), "w", encoding="utf-8") as handle:
            handle.write("\n".join([l for l in lines if not l.startswith("warning")]) + "\n")
        with open(os.path.join(out_dir, "packages.txt"), "w", encoding="utf-8") as handle:
            handle.write("\n".join(final) + "\n")
        print(f"        [consumer] 输出: {out_dir}/blend-tasks.txt, packages.txt")
    if warnings:
        for w in warnings:
            print(f"        [consumer][warn] {w}")
    return 0


def main():
    if len(sys.argv) not in (2, 3):
        print(__doc__)
        return 2
    return resolve(sys.argv[1], sys.argv[2] if len(sys.argv) == 3 else None)


if __name__ == "__main__":
    sys.exit(main())
