#!/usr/bin/env python3
"""Imake/xmkmf 遗产 X11 库适配检测 — 知识库拓展（OHOS aarch64；样例库 xli 1.17.0-20061110）

共性问题
--------
1990s-2000s 的一批 X11 客户端/工具以 Imake/xmkmf 为构建系统（Imakefile +
X11/Imake.rules），而 OHOS SDK 的 native 工具链**不含 imake/xmkmf**（CI 亦无，
制品仓无对应 tool_requires 包）：直接 `make` 找不到 Makefile，构建在入口即死。
同一批老代码还常调用 BSD 遗留 libc 函数（rindex/index/bcopy/bzero/bcmp），
其中 `rindex` 在 musl 上**不存在**（实测 OHOS SDK 26.0.0.18 的 libc.so 无该符号，
其余四个存在）——启用上游 `-DSYSV` 总开关会连带牵出 F_FREESP/stropts.h/poll
等更多缺口，因此正确做法是逐函数做最小定向替换。

本脚本做两级识别
----------------
A. 构建系统特征：源码树含 Imakefile / xmkmf、imake 提及；
   并给出是否自带非 imake 回退构建路径（Makefile.std / Makefile.noimake /
   Buildfile / Makefile.orig）——有回退则 S1 直编可行，无回退则需 S2 手工重建。
B. libc 缺口特征：源码调用 BSD 遗留函数；并对目标 libc 做符号探针
   （--libc 指定，或 OHOS_SDK_SYSROOT 环境变量，缺省不探测）。

输出与退出码
------------
0 = 未命中（非 Imake 遗产库，无需本策略）
1 = 命中（按 README 的 S1/S2/S3 策略处理）
2 = 参数/环境错误
默认输出人读摘要；--json 输出结构化结果（供 harness 消费）。
约束：仅标准库；无注入用途的硬编码路径（SDK 探测优先 --libc / OHOS_SDK_SYSROOT，
另含 /data/service/hnp 与 ~/ohos-sdk 两个只读兜底探测根）；输出只进 stdout（调用方重定向到文件，
规避 SIGPIPE——本脚本自身不接管道）。

用法
----
python3 detect_imake_legacy.py --src <源码目录> [--libc <libc.so>] [--json]
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys

IMake_MAKERS = ("Imakefile", "Imakefile.in", "Imakefile.std")
FALLBACK_MAKEFILES = ("Makefile.std", "Makefile.noimake", "Buildfile", "Makefile.orig",
                      "makefile.std", "makefile.noimake")
MODERN_BUILD = ("configure", "CMakeLists.txt", "meson.build", "Makefile.am", "Makefile.PL")

BSDS_FUNCS = ("rindex", "index", "bcopy", "bzero", "bcmp")
BSD_CALL_RE = re.compile(r"\b(" + "|".join(BSDS_FUNCS) + r")\s*\(")
BSD_SRC_EXT = (".c", ".h", ".cc", ".cpp", ".cxx", ".hpp")
IMAKE_DOC_RE = re.compile(r"\b(xmkmf|imake)\b", re.IGNORECASE)
SKIP_DIRS = {".git", ".svn", ".hg", "node_modules", "__pycache__"}
MAX_BYTES = 2 * 1024 * 1024  # 单文件扫描上限，防误读巨型产物


def walk_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            yield os.path.join(dirpath, fn)


def read_text(path, limit=MAX_BYTES):
    try:
        if os.path.getsize(path) > limit:
            return ""
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            return fh.read()
    except OSError:
        return ""


def scan_build_system(root):
    """A 类：Imake 构建特征 + 回退构建路径。"""
    res = {"imakefile": [], "fallback_makefiles": [], "modern_build": [],
           "doc_mentions": [], "imake_in_scripts": []}
    for path in walk_files(root):
        base = os.path.basename(path)
        rel = os.path.relpath(path, root)
        if base in IMake_MAKERS:
            res["imakefile"].append(rel)
            continue
        if base in FALLBACK_MAKEFILES:
            res["fallback_makefiles"].append(rel)
            continue
        if base in MODERN_BUILD:
            res["modern_build"].append(rel)
            continue
        if base.upper().startswith(("README", "INSTALL", "NEWS")) or base.endswith(".spec"):
            txt = read_text(path, 256 * 1024)
            if txt and IMAKE_DOC_RE.search(txt):
                res["doc_mentions"].append(rel)
        elif base.startswith("Makefile") or base.endswith(".sh"):
            txt = read_text(path, 512 * 1024)
            if txt and IMAKE_DOC_RE.search(txt):
                res["imake_in_scripts"].append(rel)
    return res


def scan_bsd_funcs(root):
    """B 类：源码中的 BSD 遗留 libc 函数调用。"""
    hits = {}
    for path in walk_files(root):
        if not path.endswith(BSD_SRC_EXT):
            continue
        txt = read_text(path)
        if not txt:
            continue
        found = sorted({m.group(1) for m in BSD_CALL_RE.finditer(txt)})
        if found:
            hits[os.path.relpath(path, root)] = found
    return hits


def probe_libc(libc_path):
    """对目标 libc 做符号探针：返回 {func: 'present'|'missing'|'unknown'}。"""
    out = {f: "unknown" for f in BSDS_FUNCS}
    if not libc_path:
        return out, "not-probed (use --libc or OHOS_SDK_SYSROOT)"
    if not os.path.exists(libc_path):
        return out, "libc not found: %s" % libc_path
    nm = shutil.which("nm") or shutil.which("llvm-nm")
    if not nm:
        return out, "nm/llvm-nm not available"
    try:
        proc = subprocess.run([nm, "-D", "--defined-only", libc_path],
                              capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as exc:
        return out, "probe failed: %s" % exc
    defined = set()
    for line in proc.stdout.splitlines():
        parts = line.split()
        if parts:
            defined.add(parts[-1].split("@")[0])
    for f in BSDS_FUNCS:
        out[f] = "present" if f in defined else "missing"
    return out, "nm -D --defined-only %s" % libc_path


def detect_sdk_libc():
    """探测 OHOS SDK sysroot 下的 libc.so（--libc/env 优先；/data/service/hnp、~/ohos-sdk 为只读兜底探测根）。"""
    candidates = []
    env_root = os.environ.get("OHOS_SDK_SYSROOT")
    if env_root:
        candidates.append(os.path.join(env_root, "usr", "lib", "aarch64-linux-ohos", "libc.so"))
        candidates.append(os.path.join(env_root, "usr", "lib", "libc.so"))
    for base in ("/data/service/hnp", os.path.expanduser("~/ohos-sdk")):
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            if dirpath.count(os.sep) - base.count(os.sep) > 6:
                dirnames[:] = []
                continue
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            if "libc.so" in filenames and "aarch64-linux-ohos" in dirpath:
                candidates.append(os.path.join(dirpath, "libc.so"))
    for cand in candidates:
        if os.path.exists(cand):
            return cand
    return ""


def decide(build, bsd_hits, libc_probe):
    """给出 S1/S2/S3 策略建议。"""
    has_imake = bool(build["imakefile"] or build["doc_mentions"] or build["imake_in_scripts"])
    has_fallback = bool(build["fallback_makefiles"])
    missing = [f for f, st in libc_probe.items() if st == "missing"]
    if not has_imake:
        return 0, "S0", "未发现 Imake/xmkmf 特征，非本策略适用对象"
    if has_fallback:
        strategy = "S1"
        detail = ("S1（首选）：使用源码自带的非 imake 回退构建文件 %s 直编；"
                  "把 Imake 的 -I/-L/-l 解析替换为 Conan 依赖注入（见样例库 "
                  "archives/x/xli/1.17.0-20061110/conanfile.py 的 _dependency_flags）"
                  % ", ".join(sorted(build["fallback_makefiles"])[:3]))
    else:
        strategy = "S2"
        detail = ("S2（次选）：无回退构建文件，需按 Imakefile 语义手工重建最小 Makefile"
                  "（INCLUDES/LIBS/SRCS → 显式 CFLAGS/LIBS）")
    if missing:
        detail += ("；同时命中 musl libc 缺口 %s → 逐函数最小定向替换（样例："
                   "-Drindex=strrchr），禁用上游 -DSYSV 总开关" % ", ".join(missing))
    return 1, strategy, detail


def main(argv=None):
    ap = argparse.ArgumentParser(description="Imake/xmkmf 遗产 X11 库适配检测（OHOS）")
    ap.add_argument("--src", required=True, help="源码目录")
    ap.add_argument("--libc", default="", help="目标 libc.so 路径（缺省读 OHOS_SDK_SYSROOT）")
    ap.add_argument("--json", action="store_true", help="输出结构化 JSON")
    args = ap.parse_args(argv)

    if not os.path.isdir(args.src):
        print("ERROR: --src 不是目录: %s" % args.src, file=sys.stderr)
        return 2

    libc_path = args.libc or detect_sdk_libc()
    build = scan_build_system(args.src)
    bsd_hits = scan_bsd_funcs(args.src)
    libc_probe, probe_note = probe_libc(libc_path)
    rc, strategy, detail = decide(build, bsd_hits, libc_probe)

    payload = {
        "src": args.src,
        "hit": rc == 1,
        "strategy": strategy,
        "strategy_detail": detail,
        "imakefile": build["imakefile"],
        "fallback_makefiles": build["fallback_makefiles"],
        "modern_build": build["modern_build"],
        "doc_mentions": build["doc_mentions"],
        "imake_in_scripts": build["imake_in_scripts"],
        "bsd_funcs_in_src": bsd_hits,
        "libc_probe": libc_probe,
        "libc_probe_note": probe_note,
    }
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return rc

    print("=" * 68)
    print("Imake/xmkmf 遗产 X11 库适配检测")
    print("=" * 68)
    print("A. 构建系统特征")
    print("   Imakefile           : %s" % (", ".join(build["imakefile"]) or "(none)"))
    print("   回退构建文件        : %s" % (", ".join(build["fallback_makefiles"]) or "(none)"))
    print("   现代构建文件        : %s" % (", ".join(build["modern_build"]) or "(none)"))
    print("   文档提及 imake/xmkmf: %s" % (", ".join(build["doc_mentions"]) or "(none)"))
    print("   脚本提及 imake/xmkmf: %s" % (", ".join(build["imake_in_scripts"]) or "(none)"))
    print("B. libc 缺口特征")
    if bsd_hits:
        for rel, funcs in sorted(bsd_hits.items())[:12]:
            print("   %-46s %s" % (rel, ", ".join(funcs)))
        if len(bsd_hits) > 12:
            print("   ... 其余 %d 个文件" % (len(bsd_hits) - 12))
    else:
        print("   (源码中未发现 BSD 遗留函数调用)")
    print("   目标 libc 探针      : %s" % probe_note)
    for f in BSDS_FUNCS:
        print("     %-6s -> %s" % (f, libc_probe[f]))
    print("-" * 68)
    print("判定: %s" % ("命中（需按策略处理）" if rc == 1 else "未命中"))
    print("策略: %s" % detail)
    print("=" * 68)
    return rc


if __name__ == "__main__":
    sys.exit(main())
