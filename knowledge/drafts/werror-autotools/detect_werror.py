#!/usr/bin/env python3
"""Werror-autotools 知识库拓展 — 检测脚本（Step2）

共性问题：上游 autotools / CMake 工程在构建脚本中硬编码注入 `-Werror`
（或逐项 `-Werror=<flag>`），gcc 下正常，clang/OHOS 交叉编译下告警升级为错误导致编译失败。

本脚本自动识别两类特征：
  A. 源码特征：构建脚本（configure / configure.ac / configure.in / Makefile.am /
     CMakeLists.txt）中存在 Werror 注入点 —— 规则按文件名分派，各文件类型只套用
     适用规则，避免空白列表式正则跨类型误报
  B. 编译报错特征：构建日志中存在 "-Werror" 触发的
     "error: ... [-Werror,...]" 行

输出与退出码：
  0 = 未命中（无需处理）
  1 = 命中（需应用 patches/ 模板或 no-werror 处理策略）
  2 = 参数/环境错误
  默认输出人读摘要；加 --json 输出完整 JSON（含 rule_counts / detail / detail_truncated）

用法（OHOS aarch64 适配流程内）：
  python3 detect_werror.py --src <源码目录> [--log <构建日志>] [--json]

约束：无本地绝对路径依赖、无终端缓存依赖；仅用标准库；日志重定向由调用方负责
（本脚本不写 tty 管道，规避 SIGPIPE——输出只进 stdout 缓冲，调用方重定向到文件）。
"""
import argparse
import json
import os
import re
import sys

# A 类特征：构建脚本中的 Werror 注入模式 —— 按文件名分派
SRC_RULES = {
    "configure": [
        # configure 脚本（shell）：CFLAGS="$CFLAGS -Werror" / project_CFLAGS="... -Werror"
        (re.compile(r'^\s*[A-Za-z_]+\s*=\s*"[^"]*\s-Werror(\s|$)'),
         "configure 脚本注入总 -Werror"),
        (re.compile(r'^\s*[A-Za-z_]+\s*=\s*"[^"]*\s-Werror=[A-Za-z0-9-]+'),
         "configure 脚本注入逐项 -Werror=<flag>"),
        (re.compile(r'-Werror\b'),
         "configure 脚本含 -Werror 字面量（如 --enable-werror 分支 / AC_SUBST）"),
    ],
    "configure.ac": [
        (re.compile(r'-Werror\b'), "configure.ac（m4）含 -Werror 注入"),
    ],
    "configure.in": [
        (re.compile(r'-Werror\b'), "configure.in（m4）含 -Werror 注入"),
    ],
    "Makefile.am": [
        (re.compile(r'-Werror\b'), "Makefile.am（automake）含 -Werror 注入"),
    ],
    "CMakeLists.txt": [
        (re.compile(r'-Werror\b'), "CMakeLists.txt 含 -Werror 注入"),
    ],
}
SCAN_FILES = tuple(SRC_RULES.keys())

# B 类特征：构建日志中的 Werror 报错
LOG_PATTERNS = [
    (re.compile(r'error:.*\[-Werror(=[a-z-]+)?\]'),
     "构建日志出现 [-Werror] 升级报错"),
    (re.compile(r'error:.*\[-Werror[,\]]'),
     "构建日志出现 [-Werror,...] 升级报错"),
    # clang 把未知告警选项升级为错误的变体
    (re.compile(r'error: unknown warning option.*-Werror'),
     "clang unknown warning option + Werror"),
]

MAX_FILE_BYTES = 8 * 1024 * 1024   # 8MB 防护
DETAIL_CAP = 50


def scan_source(src_dir):
    hits = []
    for root, dirs, files in os.walk(src_dir):
        # 跳过 .git / 第三方子树，控制扫描量
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules")]
        for fn in files:
            rules = SRC_RULES.get(fn)
            if not rules:
                continue
            path = os.path.join(root, fn)
            try:
                if os.path.getsize(path) > MAX_FILE_BYTES:
                    continue
                with open(path, "r", errors="ignore") as f:
                    for i, line in enumerate(f, 1):
                        for pat, desc in rules:
                            if pat.search(line):
                                hits.append({
                                    "kind": "source",
                                    "file": os.path.relpath(path, src_dir),
                                    "line": i,
                                    "rule": desc,
                                    "excerpt": line.strip()[:160],
                                })
            except OSError:
                continue
    return hits


def scan_log(log_path):
    hits = []
    try:
        if os.path.getsize(log_path) > 64 * 1024 * 1024:
            return hits
        with open(log_path, "r", errors="ignore") as f:
            for i, line in enumerate(f, 1):
                for pat, desc in LOG_PATTERNS:
                    if pat.search(line):
                        hits.append({
                            "kind": "log",
                            "file": log_path,
                            "line": i,
                            "rule": desc,
                            "excerpt": line.strip()[:160],
                        })
    except OSError:
        pass
    return hits


def rule_counts(hits):
    counts = {}
    for h in hits:
        counts[h["rule"]] = counts.get(h["rule"], 0) + 1
    return counts


def main():
    ap = argparse.ArgumentParser(description="Werror-autotools 共性问题检测")
    ap.add_argument("--src", required=True, help="源码目录")
    ap.add_argument("--log", help="可选：构建日志文件（B 类特征）")
    ap.add_argument("--json", action="store_true",
                    help="输出完整 JSON（默认输出人读摘要）")
    args = ap.parse_args()

    if not os.path.isdir(args.src):
        print(json.dumps({"error": f"src not a dir: {args.src}"}))
        return 2

    hits = scan_source(args.src)
    if args.log:
        hits.extend(scan_log(args.log))

    # 汇总判定：A 类（源码）命中即视为必修；B 类（日志）命中视为已复现证据
    src_hits = [h for h in hits if h["kind"] == "source"]
    log_hits = [h for h in hits if h["kind"] == "log"]
    verdict = "hit" if (src_hits or log_hits) else "clean"
    patches = ["0003-disable-Werror-clang-strict.patch",
               "0004-remove-per-flag-Werror.patch"] if verdict == "hit" else []

    out = {
        "skill": "werror-autotools",
        "verdict": verdict,
        "src_dir": os.path.basename(os.path.normpath(args.src)),
        "src_hits": len(src_hits),
        "log_hits": len(log_hits),
        "rule_counts": rule_counts(hits),
        "detail": hits[:DETAIL_CAP],
        "detail_truncated": len(hits) > DETAIL_CAP,
        "strategy": "patch-template" if verdict == "hit" else None,
        "patches": patches,
    }

    if args.json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
    else:
        print(f"[werror-autotools] verdict={verdict} "
              f"src_hits={len(src_hits)} log_hits={len(log_hits)}")
        for rule, n in sorted(out["rule_counts"].items(), key=lambda kv: -kv[1]):
            print(f"  {n:>4}  {rule}")
        if verdict == "hit":
            print(f"  strategy=patch-template  patches={' '.join(patches)}")
            print(f"  前 {min(DETAIL_CAP, len(hits))} 处命中（完整清单用 --json）：")
            for h in hits[:10]:
                print(f"    {h['file']}:{h['line']}  [{h['rule']}] {h['excerpt']}")
            if out["detail_truncated"]:
                print(f"  ...（共 {len(hits)} 处，仅列出前 10）")
        else:
            print("  （未命中：无需 Werror 处理）")
    return 1 if verdict == "hit" else 0


if __name__ == "__main__":
    sys.exit(main())
