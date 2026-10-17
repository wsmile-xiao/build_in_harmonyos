#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""适配前置风险扫描器 (OpenHarmony PC / aarch64)

在把三方库交给 Conan 交叉编译流水线**之前**，静态扫描源码树里三类
可机械识别、且必然导致 CI 失败（或静默错链）的风险：

  R1  cmake-min-version   构建脚本声明的最低 CMake 版本 < 3.5
                          → CMake 4.x 起**硬拒绝**配置（不是警告）
  R2  submodule-missing   上游 release tarball 里 .gitmodules 声明的
                          子模块目录为空/缺失 → 源码不完整，构建必失败
  R3  hardcoded-syspath   构建脚本把系统库探测路径写死成
                          /usr/local、/usr/include、/opt/homebrew 等
                          → 交叉编译时探测不到 Conan 提供的依赖
                          （或错链宿主库，产物不可移植）

只读扫描、纯标准库、无写死绝对路径：可在构建机、CI worker、OHOS
aarch64 设备原生 python3 上直接运行。

用法:
    python3 prescan_risks.py <源码目录>            # 人类可读报告
    python3 prescan_risks.py <源码目录> --json     # 机器可读
    python3 prescan_risks.py <源码目录> --rules R1,R3
    python3 prescan_risks.py <源码目录> --quiet    # 只输出结论行

退出码: 0 = 未发现风险; 1 = 发现风险; 2 = 用法/路径错误
"""

import argparse
import json
import os
import re
import sys

# ── 规则元数据（策略摘要与完整处理策略见同目录 STRATEGY.md） ──────────
RULES = {
    "R1": {
        "id": "cmake-min-version",
        "title": "最低 CMake 版本 < 3.5（CMake 4.x 硬拒绝）",
        "severity": "high",
        "strategy": (
            "优先把 cmake_minimum_required 抬到 3.10（补丁，兼容 cmake 3.x 与 4.x）；"
            "临时绕行可用 -DCMAKE_POLICY_VERSION_MINIMUM=3.5"
        ),
    },
    "R2": {
        "id": "submodule-missing",
        "title": "上游发布包缺 git submodule 源码",
        "severity": "high",
        "strategy": (
            "从 .gitmodules 取仓库与路径，用 git ls-tree <tag> 读出固定 commit，"
            "按 commit 下载官方 archive（不可变 URL）并校 sha256，"
            "写进 conandata.yml 多源清单，由 recipe 的 source() 落位"
        ),
    },
    "R3": {
        "id": "hardcoded-syspath",
        "title": "构建脚本硬编码系统库探测路径",
        "severity": "medium",
        "strategy": (
            "补丁改为尊重 CMAKE_PREFIX_PATH / pkg-config；"
            "recipe 里用 CMakeToolchain 注入依赖前缀，禁止写死 /usr/local"
        ),
    },
}

# 需要跳过的目录（版本控制/构建产物/依赖缓存）
SKIP_DIRS = {
    ".git", ".svn", ".hg", "node_modules", "__pycache__", ".cache",
    "build", "_build", "cmake-build-debug", "cmake-build-release",
    "target", ".conan", "autom4te.cache",
}

# R1: cmake_minimum_required(VERSION 3.0 [FATAL_ERROR])
RE_CMAKE_MIN = re.compile(
    r"cmake_minimum_required\s*\(\s*VERSION\s+(\d+)\.(\d+)(?:\.(\d+))?", re.I
)
# CMake 4 起：3.5 以下视为不兼容
MIN_SUPPORTED_MAJOR, MIN_SUPPORTED_MINOR = 3, 5

# R3: 写死的系统前缀
RE_SYSTEM_PREFIX = re.compile(
    r"(?<![\w./-])/(?:usr/local|usr/include|usr/lib\w*|opt/homebrew|opt/local)(?:/[\w.+-]*)*"
)
# 命中行里出现这些关键字才判定为「探测/链接路径」，避免误伤注释里的示例路径
PATH_HINT_WORDS = (
    "paths", "hints", "find_path", "find_library", "find_package",
    "include_directories", "link_directories", "link_libraries",
    "target_include_directories", "target_link_directories",
    "cflags", "cxxflags", "ldflags", "cppflags", "prefix", "sysroot",
    "pkg_config_path", "ac_", "-i", "-l", "-rpath",
)
BUILD_FILE_GLOBS = (
    "CMakeLists.txt", "configure.ac", "configure.in", "Makefile.am",
    "meson.build", "Makefile.PL",
)

MAX_EVIDENCE = 200  # 单条证据截断长度，避免报告臃肿


def _iter_files(root):
    """遍历源码树，返回相对路径列表（跳过 SKIP_DIRS）。"""
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            full = os.path.join(dirpath, name)
            out.append(os.path.relpath(full, root))
    return out


def _is_build_script(rel):
    base = os.path.basename(rel)
    return base in BUILD_FILE_GLOBS or base.endswith(".cmake")


def _clip(text):
    text = " ".join(text.split())
    return text if len(text) <= MAX_EVIDENCE else text[: MAX_EVIDENCE - 3] + "..."


def _read(path):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            return fh.read().splitlines()
    except OSError:
        return []


def scan_r1(root, files):
    """R1: cmake_minimum_required 版本过低。"""
    findings = []
    for rel in files:
        if os.path.basename(rel) != "CMakeLists.txt":
            continue
        for idx, line in enumerate(_read(os.path.join(root, rel)), 1):
            m = RE_CMAKE_MIN.search(line)
            if not m:
                continue
            major, minor = int(m.group(1)), int(m.group(2))
            if (major, minor) >= (MIN_SUPPORTED_MAJOR, MIN_SUPPORTED_MINOR):
                continue
            findings.append({
                "rule": "R1",
                "id": RULES["R1"]["id"],
                "severity": RULES["R1"]["severity"],
                "file": rel,
                "line": idx,
                "evidence": _clip(line),
                "detail": (
                    "声明最低 CMake %d.%d < %d.%d；CMake 4.x 起该声明 "
                    "直接 FATAL_ERROR（Compatibility with CMake < 3.5 has "
                    "been removed）"
                    % (major, minor, MIN_SUPPORTED_MAJOR, MIN_SUPPORTED_MINOR)
                ),
            })
    return findings


def scan_r2(root, files):
    """R2: .gitmodules 声明的子模块目录缺失或为空。"""
    findings = []
    for rel in files:
        if os.path.basename(rel) != ".gitmodules":
            continue
        base_dir = os.path.dirname(rel)
        section = {}
        for line in _read(os.path.join(root, rel)) + ["[eof]"]:
            stripped = line.strip()
            if stripped.startswith("[") and section:
                _emit_submodule_finding(root, base_dir, section, findings)
                section = {}
                continue
            if "=" in stripped:
                key, _, val = stripped.partition("=")
                section[key.strip()] = val.strip()
        return findings
    return findings


def _emit_submodule_finding(root, base_dir, section, findings):
    path = section.get("path")
    if not path:
        return
    sub_rel = os.path.normpath(os.path.join(base_dir, path)) if base_dir else path
    sub_abs = os.path.join(root, sub_rel)
    exists = os.path.isdir(sub_abs)
    empty = (not exists) or not any(
        name for name in os.listdir(sub_abs) if name not in (".", "..")
    )
    if not empty:
        return
    findings.append({
        "rule": "R2",
        "id": RULES["R2"]["id"],
        "severity": RULES["R2"]["severity"],
        "file": os.path.join(base_dir, ".gitmodules") if base_dir else ".gitmodules",
        "line": 0,
        "evidence": _clip(
            "path = %s (url = %s) -> %s"
            % (sub_rel, section.get("url", "?"),
               "目录不存在" if not exists else "目录为空")
        ),
        "detail": (
            "上游 release/archive tarball 不含子模块源码：该目录在 git 树里是 "
            "gitlink，不是普通文件。构建脚本 add_subdirectory/%s 必然失败"
            % sub_rel
        ),
    })


def scan_r3(root, files):
    """R3: 构建脚本里写死的系统库探测路径。"""
    findings = []
    for rel in files:
        if not _is_build_script(rel):
            continue
        for idx, line in enumerate(_read(os.path.join(root, rel)), 1):
            stripped = line.strip()
            if stripped.startswith("#") and "find_" not in stripped.lower():
                continue  # 纯注释行不算
            m = RE_SYSTEM_PREFIX.search(line)
            if not m:
                continue
            lowered = line.lower()
            if not any(word in lowered for word in PATH_HINT_WORDS):
                continue
            findings.append({
                "rule": "R3",
                "id": RULES["R3"]["id"],
                "severity": RULES["R3"]["severity"],
                "file": rel,
                "line": idx,
                "evidence": _clip(line),
                "detail": (
                    "探测/链接路径写死为 %s：交叉编译时 Conan 依赖不在该前缀下，"
                    "轻则 find_* 返回 NOTFOUND（编译缺头文件），重则错链宿主库"
                    % m.group(0)
                ),
            })
    return findings


SCANNERS = {"R1": scan_r1, "R2": scan_r2, "R3": scan_r3}


def run(root, rules):
    files = _iter_files(root)
    findings = []
    for rule in rules:
        findings.extend(SCANNERS[rule](root, files))
    findings.sort(key=lambda f: (f["rule"], f["file"], f["line"]))
    return findings, len(files)


def render_text(root, findings, n_files, rules):
    lines = []
    lines.append("=" * 68)
    lines.append("适配前置风险扫描 (OpenHarmony PC / aarch64)")
    lines.append("源码目录: %s" % root)
    lines.append("扫描文件: %d 个    规则: %s" % (n_files, ",".join(rules)))
    lines.append("=" * 68)
    if not findings:
        lines.append("[OK] 未发现风险（R1/R2/R3）")
        return "\n".join(lines)
    for f in findings:
        lines.append("")
        lines.append("[%s] %s  (%s)" % (f["rule"], RULES[f["rule"]]["title"], f["severity"]))
        lines.append("  位置: %s%s" % (f["file"], (":%d" % f["line"]) if f["line"] else ""))
        lines.append("  证据: %s" % f["evidence"])
        lines.append("  影响: %s" % f["detail"])
        lines.append("  策略: %s" % RULES[f["rule"]]["strategy"])
    lines.append("")
    lines.append("-" * 68)
    lines.append("合计 %d 项风险；处理策略详见 tools/STRATEGY.md" % len(findings))
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="适配前置风险扫描器（CMake 最低版本 / 子模块缺失 / 写死系统路径）"
    )
    ap.add_argument("source_dir", help="待扫描的上游源码目录")
    ap.add_argument("--rules", default="R1,R2,R3", help="启用规则，逗号分隔（默认全部）")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--quiet", action="store_true", help="只输出结论行")
    args = ap.parse_args(argv)

    root = args.source_dir
    if not os.path.isdir(root):
        sys.stderr.write("错误: 不是目录: %s\n" % root)
        return 2

    rules = [r.strip().upper() for r in args.rules.split(",") if r.strip()]
    unknown = [r for r in rules if r not in SCANNERS]
    if unknown:
        sys.stderr.write("错误: 未知规则 %s（可选 R1,R2,R3）\n" % ",".join(unknown))
        return 2

    findings, n_files = run(root, rules)

    if args.json:
        print(json.dumps({
            "source_dir": root,
            "scanned_files": n_files,
            "rules": rules,
            "risk_count": len(findings),
            "findings": findings,
            "strategies": {r: RULES[r]["strategy"] for r in rules},
        }, ensure_ascii=False, indent=2))
    elif args.quiet:
        print("PRESCAN risk_count=%d rules=%s" % (len(findings), ",".join(rules)))
    else:
        print(render_text(root, findings, n_files, rules))

    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
