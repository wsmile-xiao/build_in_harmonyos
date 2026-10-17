#!/usr/bin/env python3
"""检测 OHOS musl libc 的 POSIX 线程取消 API 缺口（pthread_cancel 族）。

背景
----
OHOS 的 musl libc（SDK 26.0.0.18 sysroot）**不导出** pthread_cancel(3) /
pthread_setcancelstate(3) / pthread_setcanceltype(3)，且 sysroot 里的
`libpthread.a` 是**空壳**（0 个定义符号）——因此 `-lpthread` 无法补齐缺口，
必须走源码侧特性宏间接层 + 取消点降级。

本脚本做三级识别：
  A 类（源码侧）：源码是否使用取消点 API（pthread_cancel / setcancelstate /
      setcanceltype / testcancel / PTHREAD_CANCELED）；
  B 类（libc 探针）：目标 libc.so 的动态符号表中这些 API 是否存在；
  C 类（空壳探针）：sysroot 的 libpthread.a 是否有定义符号（能否靠 -lpthread 补齐）。

用法
----
  python3 detect_pthread_cancel_gap.py --src <源码目录> [--libc <libc.so>]
                                       [--sysroot <sysroot>] [--json]

libc/sysroot 自动发现顺序：命令行参数 → 环境变量 OHOS_SDK_SYSROOT →
SDK 常见安装位置（`*/ohos/native/sysroot/usr/lib/aarch64-linux-ohos/libc.so`）。

退出码：0 = 未命中；1 = 命中（按知识条目策略处理）；2 = 参数/环境错误，
或探针不可用（libc 未发现 / nm 缺失）——此时输出 PROBE_UNAVAILABLE，不得据
"未探到符号"判命中，须先用 --libc/--sysroot/OHOS_SDK_SYSROOT 补齐探针环境。
只读脚本，不写任何文件。
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import shutil
import subprocess
import sys

CALL_PATTERNS = {
    "pthread_cancel": re.compile(r"\bpthread_cancel\s*\("),
    "pthread_setcancelstate": re.compile(r"\bpthread_setcancelstate\s*\("),
    "pthread_setcanceltype": re.compile(r"\bpthread_setcanceltype\s*\("),
    "pthread_testcancel": re.compile(r"\bpthread_testcancel\s*\("),
    "PTHREAD_CANCELED": re.compile(r"\bPTHREAD_CANCELED\b"),
}
PROBE_SYMBOLS = [
    "pthread_cancel",
    "pthread_setcancelstate",
    "pthread_setcanceltype",
    "pthread_testcancel",
    "pthread_exit",
    "pthread_detach",
    "pthread_cond_timedwait",
]
SRC_EXT = {".c", ".h", ".cc", ".cpp", ".cxx", ".hpp", ".hh"}
SKIP_DIRS = {".git", ".svn", "build", "_build", "node_modules", ".cache"}


def which_tool(name: str) -> str | None:
    for candidate in (name, f"llvm-{name}"):
        found = shutil.which(candidate)
        if found:
            return found
    return None


def scan_source(root: str) -> dict:
    """A 类：源码侧取消点 API 使用清点。"""
    hits: dict[str, dict] = {k: {"files": [], "count": 0} for k in CALL_PATTERNS}
    scanned = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in filenames:
            if os.path.splitext(fname)[1].lower() not in SRC_EXT:
                continue
            fpath = os.path.join(dirpath, fname)
            scanned += 1
            try:
                with open(fpath, "r", encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
            except OSError:
                continue
            for name, pattern in CALL_PATTERNS.items():
                found = pattern.findall(text)
                if found:
                    hits[name]["count"] += len(found)
                    hits[name]["files"].append(os.path.relpath(fpath, root))
    for entry in hits.values():
        entry["files"] = sorted(set(entry["files"]))[:20]
    return {"files_scanned": scanned, "hits": hits}


def discover_libc(args) -> str | None:
    if args.libc:
        return args.libc if os.path.isfile(args.libc) else None
    roots = []
    if args.sysroot:
        roots.append(args.sysroot)
    if os.environ.get("OHOS_SDK_SYSROOT"):
        roots.append(os.environ["OHOS_SDK_SYSROOT"])
    roots.extend(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/sysroot"))
    roots.extend(glob.glob(os.path.expanduser("~/*/ohos-sdk*/ohos/native/sysroot")))
    for root in roots:
        for pattern in ("usr/lib/aarch64-linux-ohos/libc.so", "usr/lib/*/libc.so", "usr/lib/libc.so"):
            for cand in glob.glob(os.path.join(root, pattern)):
                if os.path.isfile(cand):
                    return cand
    return None


def symbol_probe(libc: str) -> dict:
    """B 类：libc 动态符号表探针（缺 nm 时返回 error 而非崩溃）。"""
    nm = which_tool("nm")
    if not nm:
        return {"error": "nm/llvm-nm not found", "present": {}, "missing": []}
    try:
        proc = subprocess.run([nm, "-D", "--defined-only", libc],
                              capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as exc:
        return {"error": f"{type(exc).__name__}: {exc}", "present": {}, "missing": []}
    if proc.returncode != 0:
        # nm 跑失败（非 ELF / 参数不支持）不是"符号缺失"——按探针不可用处理
        return {"error": f"nm 退出码 {proc.returncode}: {proc.stderr.strip()[:120]}",
                "present": {}, "missing": []}
    out = proc.stdout
    defined = set()
    for line in out.splitlines():
        parts = line.split()
        if parts:
            defined.add(parts[-1].split("@")[0])
    present, missing = {}, []
    for sym in PROBE_SYMBOLS:
        if sym in defined:
            present[sym] = True
        else:
            missing.append(sym)
    return {"error": None, "present": present, "missing": missing}


def find_sysroot(libc: str) -> str | None:
    """从 libc.so 路径向上定位 sysroot：第一个含 `usr/lib` 的祖先目录。

    兼容 `<sysroot>/usr/lib/<triple>/libc.so`（真实 OHOS sysroot 布局）与
    `<sysroot>/usr/lib/libc.so`（无 triple 布局）；固定层数 dirname 只对后者成立。
    """
    cur = os.path.dirname(os.path.abspath(libc))
    while True:
        parent = os.path.dirname(cur)
        if parent == cur:
            return None
        if os.path.isdir(os.path.join(parent, "usr", "lib")):
            return parent
        cur = parent


def find_pthread_shell(libc: str | None) -> dict:
    """C 类：sysroot 中 libpthread.a 是否有定义符号（空壳则无法用 -lpthread 补齐）。"""
    if not libc:
        return {"found": None, "defined": None, "error": "libc not found"}
    sysroot = find_sysroot(libc)
    if not sysroot:
        return {"found": None, "defined": None,
                "error": "未定位到含 usr/lib 的 sysroot 祖先目录"}
    candidates = sorted(glob.glob(os.path.join(sysroot, "usr", "lib", "libpthread.a")))
    candidates += sorted(glob.glob(os.path.join(sysroot, "usr", "lib", "*", "libpthread.a")))
    if not candidates:
        return {"found": None, "defined": None, "error": "sysroot 内未找到 libpthread.a"}
    archives = candidates
    nm = which_tool("nm")
    if not nm:
        return {"found": archives[0], "defined": -1, "error": "nm/llvm-nm not found"}
    try:
        out = subprocess.run([nm, "--defined-only", *archives],
                             capture_output=True, text=True, timeout=120).stdout
    except (OSError, subprocess.SubprocessError):
        return {"found": archives[0], "defined": -1, "error": "nm 执行失败"}
    count = sum(1 for line in out.splitlines() if re.search(r"\b[TDBRWV]\s", line))
    return {"found": archives[0], "defined": count, "error": None}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--src", required=True, help="源码根目录")
    ap.add_argument("--libc", help="libc.so 路径（缺省自动发现）")
    ap.add_argument("--sysroot", help="sysroot 目录（缺省自动发现）")
    ap.add_argument("--json", action="store_true", help="JSON 输出")
    args = ap.parse_args()

    if not os.path.isdir(args.src):
        print(f"error: --src not a directory: {args.src}", file=sys.stderr)
        return 2
    libc = discover_libc(args)
    if args.libc and not libc:
        print(f"error: --libc not a file: {args.libc}", file=sys.stderr)
        return 2

    src_result = scan_source(args.src)
    libc_result = symbol_probe(libc) if libc else {"error": "libc not found", "present": {}, "missing": []}
    shell_result = find_pthread_shell(libc)

    source_uses = {k: v for k, v in src_result["hits"].items() if v["count"] > 0}
    probe_available = bool(libc) and not libc_result.get("error")
    gap = ([s for s in ("pthread_cancel", "pthread_setcancelstate", "pthread_setcanceltype")
            if not libc_result["present"].get(s)] if probe_available else [])
    hit = bool(source_uses) and bool(gap)
    # 探针不可用时 present 为空只是"没探测"，不是"符号缺失"——不得据此判命中
    if hit:
        verdict = "HIT"
    elif source_uses and not probe_available:
        verdict = "PROBE_UNAVAILABLE"
    else:
        verdict = "MISS"

    report = {
        "src": os.path.abspath(args.src),
        "files_scanned": src_result["files_scanned"],
        "source_uses": source_uses,
        "libc": libc,
        "libc_symbols_present": sorted(libc_result["present"]),
        "libc_symbols_missing": libc_result["missing"],
        "gap_symbols": gap,
        "libpthread_archive": shell_result,
        "probe_available": probe_available,
        "probe_error": libc_result.get("error"),
        "verdict": verdict,
    }

    if args.json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"[A] 源码侧取消点 API 使用（扫描 {src_result['files_scanned']} 个源文件）")
        if source_uses:
            for name, info in sorted(source_uses.items()):
                print(f"    - {name}: {info['count']} 处 / {len(info['files'])} 文件"
                      f"（示例: {', '.join(info['files'][:3])}）")
        else:
            print("    - 未发现取消点 API 使用")
        print(f"[B] libc 探针: {libc or '未发现'}")
        if probe_available:
            print(f"    存在: {', '.join(sorted(libc_result['present'])) or '（无）'}")
            print(f"    缺失: {', '.join(libc_result['missing']) or '（无）'}")
        else:
            print(f"    探针不可用（{libc_result.get('error') or '未知原因'}）——不作为判定依据")
        if shell_result["found"]:
            print(f"[C] {shell_result['found']}: 定义符号数 = {shell_result['defined']}"
                  f"{'（空壳，-lpthread 无法补齐）' if shell_result['defined'] == 0 else ''}")
        else:
            print(f"[C] libpthread.a 未探测到（{shell_result.get('error') or '未知原因'}）")
        print(f"[=] 判定: {report['verdict']}")
        if hit:
            print("    → 命中：源码使用取消点 API 且 libc 缺该族符号。")
            print("    → 处置：特性宏间接层（自中止路径回退 pthread_exit）+ 跨线程取消点")
            print("      按语义降级（记录 + 空操作，由后续 stop/join 收管线）；禁止用")
            print("      -lpthread 或弱符号 stub 顶替（空壳库/错误语义）。")
        elif verdict == "PROBE_UNAVAILABLE":
            print("    → 探针不可用：源码确有取消点 API 使用，但 libc 符号表未探到"
                  "（缺 SDK sysroot 或 nm）。")
            print("      请用 --libc/--sysroot 或 OHOS_SDK_SYSROOT 指向 SDK sysroot 后重跑；")
            print("      探针补齐前不得据本结果判命中（防误报）。")

    if hit:
        return 1
    return 2 if verdict == "PROBE_UNAVAILABLE" else 0


if __name__ == "__main__":
    sys.exit(main())
