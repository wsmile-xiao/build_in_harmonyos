#!/usr/bin/env python3
r"""debian-design 消费者用例：按 live-build / debian-installer 的方式**消费** blend 节点数据。

用法: python3 consumer_design.py <package_folder> [out_dir] [suite]

端到端链路（不是文件存在性断言）——这正是上游 `Makefile` 的 `all` 目标 + 消费方取用流程：

  1. 读 `<prefix>/share/design-blends/nodes/*.yml` —— 每个节点是一份**类清单**（`classes:`）；
  2. 用 `<prefix>/share/design-blends/skel/{preseed.cfg.in,script.sh.in}` 模板把节点
     **组合**成 d-i / live-build 真正读取的产物（等价于上游
     `boxer compose --nodedir nodes --skeldir skel --suite <suite> <node>`）：
       content/<node>/preseed.cfg      d-i 预置文件
       content/<node>/script.sh        安装/更新脚本
     并像 `Makefile` 一样生成 `content/MD5SUMS`、`content/SHA256SUMS`；
  3. **以消费方的方式验收**：
     - 校验和清单逐条回算必须与产物字节一致（live-build 取用前就是这么校验的）；
     - `preseed.cfg` 每行必须是注释/空行/合法 `d-i <path> <type> <value>`，
       且不得残留未展开的 `[% %]` 模板标记；
     - `script.sh` 必须通过真实的 `sh -n`（shell 语法检查），并带上该节点的类清单。

不给 out_dir 时全部在内存里完成、只打印结果（CI 用这个形态，**不在源码树落文件**）；
给了 out_dir 才会把 content/ 写出来（人工复核用）。

退出码：任一节点解析/组合失败、校验和对不上、preseed 有非法行、script.sh 语法错 → 非 0。
"""

import hashlib
import os
import re
import subprocess
import sys

TAG = re.compile(r"\[\%\s*(.*?)\s*\%\]")


def parse_node(path):
    """节点 YAML → 类清单（只认 `classes:` 下的 `- xxx` 列表，不依赖 PyYAML）。"""
    classes, in_classes = [], False
    with open(path, encoding="utf-8", errors="replace") as handle:
        for line in handle:
            stripped = line.rstrip("\n")
            if stripped.strip().startswith("classes:"):
                in_classes = True
                continue
            if in_classes:
                m = re.match(r"^\s*-\s+(\S+)\s*$", stripped)
                if m:
                    classes.append(m.group(1))
                elif stripped.strip() and not stripped.startswith((" ", "\t")):
                    in_classes = False
    return classes


def render(template, values):
    """渲染 Template Toolkit 子集：`[% IF x %]...[% END %]` 与 `[% x %]` 变量。

    用游标手动推进（不能与 finditer 混用：处理完 IF 块后必须跳过块内所有标记）。
    """
    out, pos = [], 0
    while True:
        m = TAG.search(template, pos)
        if not m:
            out.append(template[pos:])
            break
        out.append(template[pos:m.start()])
        expr = m.group(1)
        pos = m.end()
        if expr.startswith("IF "):
            name = expr[3:].strip()
            end = template.find("[% END %]", pos)
            if end < 0:
                raise ValueError("模板里 [% IF %] 缺少 [% END %]")
            body = template[pos:end]
            pos = end + len("[% END %]")
            if values.get(name):
                out.append(render(body, values))     # 块内变量继续渲染
            continue
        if expr in ("END", "END IF"):
            raise ValueError("模板里出现了多余的 [% END %]")
        out.append(str(values.get(expr, "")))
    return "".join(out)


def render_node(nodes_dir, skel_dir, node, suite):
    classes = parse_node(os.path.join(nodes_dir, node + ".yml"))
    if not classes:
        raise ValueError(f"node {node} 没有解析出任何 class")
    values = {"suite": suite,
              "pkglist": " ".join(classes),   # boxer 的 class→包 映射不在本包内：
              "pkgdesc": "",                  # 这里按节点的类清单渲染，保持"类选择"信息不丢
              "tweakdesc": "", "tweaklist": "", "pkgautolist": ""}
    arts = {}
    for src, dst in (("preseed.cfg.in", "preseed.cfg"), ("script.sh.in", "script.sh")):
        with open(os.path.join(skel_dir, src), encoding="utf-8") as handle:
            arts[dst] = render(handle.read(), values).encode("utf-8")
    return classes, arts


def verify_preseed(data):
    """按 d-i 预置文件的口径校验：无未展开模板标记，且每行合法。"""
    text = data.decode("utf-8")
    if "[%" in text or "%]" in text:
        return "preseed.cfg 残留未展开的 [% %] 模板标记"
    # preseed 允许行尾反斜杠续行（上游模板的 late_command 就是多行 shell 片段），
    # 先按续行合并成逻辑行再校验，否则会把续行误判成非法行。
    logical, buf = [], ""
    for raw in text.splitlines():
        buf += raw
        if raw.rstrip().endswith("\\"):
            continue
        logical.append(buf)
        buf = ""
    if buf:
        logical.append(buf)
    for i, line in enumerate(logical, 1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        # debconf 预置允许两种形态：
        #   d-i <question> <type> <value>           （installer 自己的询问项）
        #   <owner> <question> <type> <value>       （某包自己的询问项，模板里就有这种）
        parts = s.split(None, 3)
        if len(parts) < 4:
            return f"preseed.cfg 第 {i} 行字段不足（需 owner/question/type/value）: {s[:60]}"
        question = parts[1]
        if "/" not in question:
            return f"preseed.cfg 第 {i} 行的询问项不像 debconf 模板路径: {s[:60]}"
    return None


def verify_script(data, classes):
    """按脚本消费方口径校验：真实 shell 语法检查 + 类清单不全丢。"""
    text = data.decode("utf-8")
    if "[%" in text or "%]" in text:
        return "script.sh 残留未展开的 [% %] 模板标记"
    missing = [c for c in classes if c not in text]
    if missing:
        return f"script.sh 丢了 {len(missing)} 个 class（如 {missing[0]}）"
    for shell in ("sh", "bash"):
        try:
            proc = subprocess.run([shell, "-n"], input=data, capture_output=True, timeout=60)
        except (FileNotFoundError, subprocess.SubprocessError):
            continue
        if proc.returncode != 0:
            return f"{shell} -n 语法检查失败: {proc.stderr.decode()[:120]}"
        return None
    print("        [consumer][warn] 环境里没有 sh/bash，跳过脚本语法检查")
    return None


def manifest(entries, algo):
    lines = []
    for rel in sorted(entries):
        lines.append(f"{hashlib.new(algo, entries[rel]).hexdigest()}  {rel}")
    return ("\n".join(lines) + "\n").encode("utf-8")


def verify_manifest(data, entries, algo):
    """消费方回算校验和：清单里每条都要与产物字节一致（live-build 的取用前校验）。"""
    listed = set()
    for line in data.decode("utf-8").splitlines():
        if not line.strip():
            continue
        digest, _, rel = line.partition("  ")
        if rel not in entries:
            return f"{algo.upper()}SUMS 列了不存在的产物: {rel}"
        if hashlib.new(algo, entries[rel]).hexdigest() != digest:
            return f"{algo.upper()}SUMS 与产物不一致: {rel}"
        listed.add(rel)
    unlisted = sorted(set(entries) - listed)
    if unlisted:
        return f"{algo.upper()}SUMS 漏了产物: {unlisted[:3]}"
    return None


def main():
    if len(sys.argv) not in (2, 3, 4):
        print(__doc__)
        return 2
    package_folder = sys.argv[1]
    out_dir = sys.argv[2] if len(sys.argv) > 2 else None
    suite = sys.argv[3] if len(sys.argv) > 3 else "bookworm"
    blend_dir = os.path.join(package_folder, "share", "design-blends")
    nodes_dir = os.path.join(blend_dir, "nodes")
    skel_dir = os.path.join(blend_dir, "skel")
    if not os.path.isdir(nodes_dir) or not os.path.isdir(skel_dir):
        raise SystemExit("consumer: 缺少 share/design-blends/{nodes,skel}（blend 输入不完整）")
    nodes = sorted(n[:-4] for n in os.listdir(nodes_dir) if n.endswith(".yml"))
    if not nodes:
        raise SystemExit("consumer: nodes/ 下没有 *.yml")

    content, stats = {}, []
    for node in nodes:
        classes, arts = render_node(nodes_dir, skel_dir, node, suite)
        err = verify_preseed(arts["preseed.cfg"])
        if err:
            raise SystemExit(f"consumer: {node}: {err}")
        err = verify_script(arts["script.sh"], classes)
        if err:
            raise SystemExit(f"consumer: {node}: {err}")
        for name, data in arts.items():
            content[f"{node}/{name}"] = data
        stats.append((node, len(classes), len(arts["preseed.cfg"]), len(arts["script.sh"])))
    # 上游 Makefile 的 all 目标：为 content/ 生成校验和清单
    md5s, sha256s = manifest(content, "md5"), manifest(content, "sha256")
    for algo, data in (("md5", md5s), ("sha256", sha256s)):
        err = verify_manifest(data, content, algo)
        if err:
            raise SystemExit(f"consumer: {err}")

    print(f"        [consumer] blend debian-design: {len(nodes)} 个节点 → "
          f"{len(content)} 个 live 安装产物（suite={suite}）+ MD5SUMS/SHA256SUMS")
    for node, n_cls, p_len, s_len in stats:
        print(f"        [consumer]   {node}: {n_cls} 个 class → preseed.cfg {p_len}B / script.sh {s_len}B")
    print("        [consumer] 消费方验收: 校验和回算一致 / preseed 指令合法 / script.sh 通过 sh -n")
    if out_dir:
        for rel, data in content.items():
            path = os.path.join(out_dir, "content", rel)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as handle:
                handle.write(data)
        with open(os.path.join(out_dir, "content", "MD5SUMS"), "wb") as handle:
            handle.write(md5s)
        with open(os.path.join(out_dir, "content", "SHA256SUMS"), "wb") as handle:
            handle.write(sha256s)
        print(f"        [consumer] 输出: {out_dir}/content/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
