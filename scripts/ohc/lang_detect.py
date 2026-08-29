# -*- coding: utf-8 -*-
"""语言预检（AI Worker 协议 v0.8 附录 D，2026-08-29 冻结）。

协议要求（无兼容层，缺字段 = PROTOCOL_VIOLATION 拒收）：
  1. 语言探测前置：checkout 源码后、进入适配主流程前完成语言判定；
     判定与任务 lang 不符时立即输出 env_unsupported（不要硬着头皮适配）
  2. 结构化输出：detected_language（§4.6 枚举）+ language_evidence
     （build_system/manifest/source_stats 三项，每项 ≤200 字符）
  3. 判定优先级（§4.6）：manifest 文件 > 构建系统 > 源文件统计（≥70% 单语言）
  4. 边界规则（附录 D.4）：
     - C/C++ 混编 → 按主体判 c 或 cpp（不算 mixed，E13）
     - 绑定类包（pybind11 包装 C++）→ 判 cpp，证据注明绑定关系
     - 辅助脚本（构建脚本是 python 等）不算主体语言
  5. 冲突规则（§4.7）：manifest 与统计矛盾（如 manifest=cargo 但 95% 是 .c）
     → 上报 mixed

用法（Agent 在 Step 1 源码 checkout 后调用）:
    python3 scripts/ohc-run.py lang-preflight <software> <version> \
        --src <源码目录> [--lang cpp]

    --lang/OHPCD_LANG: 任务语言（dispatch 注入 OHPCD_LANG）；默认 cpp。
    本 SKILL 的 conan 流程 c/cpp 通吃，c↔cpp 视为兼容族不做迁移。

输出：
    匹配   → exit 0，stdout JSON（detected_language/language_evidence/notes），
             写 R46 草稿 milestone=lang_checked + feedback 事件
    不匹配 → 写终态 result.json（env_unsupported + 语言两字段，走校验器），
             exit 2，流程应立即终止（协议：不要硬着头皮适配）
"""
from __future__ import annotations

import os
import sys
from collections import Counter
from pathlib import Path

from .utils import find_project_dir, log_fail, log_info, log_ok, log_warn

# 协议 §4.6 枚举（E12: 必须小写枚举值，禁止自由文本）
LANG_ENUM = ("c", "cpp", "rust", "python", "go", "perl", "lua",
             "nodejs", "java", "bash", "mixed", "other")

# 本 SKILL 兼容族：conan 流程 c/cpp 通吃，族内不触发 env_unsupported
_COMPAT_FAMILY = {"c", "cpp"}

# 扩展名 → 语言（.h 中立：归属 c/cpp 族内部再分）
_EXT_LANG = {
    ".rs": "rust", ".py": "python", ".go": "go",
    ".pl": "perl", ".pm": "perl", ".lua": "lua",
    ".js": "nodejs", ".mjs": "nodejs", ".cjs": "nodejs",
    ".java": "java", ".sh": "bash", ".bash": "bash",
}
_C_EXTS = {".c"}
_CPP_EXTS = {".cpp", ".cc", ".cxx", ".C", ".hpp", ".hh", ".hxx", ".inl", ".tpp"}
_H_EXTS = {".h"}

# 统计时跳过的目录（vendored 依赖/构建产物/VCS）
_SKIP_DIRS = {".git", ".svn", ".hg", "node_modules", "vendor",
              "third_party", "thirdparty", "deps", ".ci",
              "build", "_build", "dist", "cmake-build-debug"}

_MAX_EVIDENCE = 200  # 协议 §4.7: 每项 ≤200 字符
_MAX_FILES = 20000


def _iter_files(src: Path):
    n = 0
    for p in src.rglob("*"):
        if n >= _MAX_FILES:
            break
        if not p.is_file():
            continue
        rel_parts = p.relative_to(src).parts
        if any(seg in _SKIP_DIRS for seg in rel_parts[:-1]):
            continue
        n += 1
        yield p


def _read_head(p: Path, limit: int = 4000) -> str:
    try:
        return p.open("r", encoding="utf-8", errors="replace").read(limit)
    except OSError:
        return ""


def _clip(s: str, limit: int = _MAX_EVIDENCE) -> str:
    s = " ".join(s.split())
    return s if len(s) <= limit else s[: limit - 1] + "…"


def _manifest_scan(files, src: Path):
    """优先级 1+2：manifest 文件 + 构建系统。

    返回 (lang_or_None, build_system, manifest_desc)；
    c/cpp 族 manifest 返回 "c/cpp"（族内由源码统计再分）。
    """
    names = {p.name for p in files}
    tops = {p.name: p for p in files if p.parent == src}

    if "Cargo.toml" in names:
        head = _read_head(tops.get("Cargo.toml",
                                   next(p for p in files if p.name == "Cargo.toml")))
        name_line = next((l.strip() for l in head.splitlines()
                          if l.strip().startswith("name")), "")
        return ("rust", "cargo", _clip(f"Cargo.toml {name_line}"))
    if names & {"pyproject.toml", "setup.py", "setup.cfg"}:
        mf = next(n for n in ("pyproject.toml", "setup.py", "setup.cfg")
                  if n in names)
        return ("python", "setuptools", _clip(f"{mf} 存在（python 打包 manifest）"))
    if "go.mod" in names:
        return ("go", "go", _clip("go.mod 存在（module 声明）"))
    if any(n.endswith(".rockspec") for n in names):
        return ("lua", "luarocks", _clip("*.rockspec 存在"))
    if names & {"Makefile.PL", "Build.PL"}:
        return ("perl", "module-build", _clip("Makefile.PL/Build.PL 存在"))
    pj = tops.get("package.json")
    if pj is not None:
        head = _read_head(pj)
        if any(k in head for k in ('"main"', '"scripts"', '"engines"', '"bin"')):
            return ("nodejs", "npm", _clip("package.json 含 main/scripts/engines/bin"))
    if names & {"build.gradle", "build.gradle.kts", "pom.xml"}:
        return ("java", "gradle/maven", _clip("build.gradle*/pom.xml 存在"))
    cmake = tops.get("CMakeLists.txt")
    if cmake is not None:
        proj_line = next((l.strip() for l in _read_head(cmake).splitlines()
                          if "project(" in l.lower()), "")
        return ("c/cpp", "cmake", _clip(f"CMakeLists.txt {proj_line}"))
    if names & {"configure.ac", "Makefile.am"}:
        return ("c/cpp", "autotools", _clip("configure.ac/Makefile.am 存在"))
    meson = tops.get("meson.build")
    if meson is not None:
        proj_line = next((l.strip() for l in _read_head(meson).splitlines()
                          if "project(" in l.lower()), "")
        return ("c/cpp", "meson", _clip(f"meson.build {proj_line}"))
    if "Makefile" in names:
        return ("c/cpp", "make", _clip("顶层 Makefile（无更强 manifest）"))
    return (None, "none", "未发现语言 manifest 文件")


def _source_stats(files):
    """优先级 3：源文件统计。返回 (counts, total)。

    边界规则：bash 一律视为辅助脚本不参与主体占比（D.4）；
    .h 中立头文件不计数（c/cpp 归属由 .c/.cpp 实源决定，E13）。
    """
    counts: Counter = Counter()
    for p in files:
        ext = p.suffix.lower() if p.suffix else ""
        if p.suffix == ".C":  # 大写 .C 是 C++ 惯例
            ext = ".cpp"
        if ext in _EXT_LANG:
            counts[_EXT_LANG[ext]] += 1
        elif ext in _C_EXTS:
            counts["c"] += 1
        elif ext in _CPP_EXTS:
            counts["cpp"] += 1
        # .h 跳过：中立头文件
    total = sum(v for k, v in counts.items() if k != "bash")
    return counts, total


def detect_language(src_dir: str | Path) -> dict:
    """协议 §4.6 判定：返回 detected_language + language_evidence（三项）+ notes。"""
    src = Path(src_dir)
    if not src.is_dir():
        return {"detected_language": "other",
                "language_evidence": _evidence("none", f"源码目录不存在: {src}", "无源码可统计"),
                "notes": ["src 目录无效"]}

    files = list(_iter_files(src))
    m_lang, build_system, manifest_desc = _manifest_scan(files, src)
    counts, total = _source_stats(files)

    # c/cpp 族 manifest：族内由 .c/.cpp 实源再分（E13: 混编按主体判，不算 mixed）
    family_manifest = (m_lang == "c/cpp")
    if family_manifest:
        m_lang = "cpp" if counts.get("cpp", 0) > 0 else "c"

    # 主体占比（≥70% 才可判单语言，§4.6 优先级 3）
    dominant, share = None, 0.0
    if total > 0:
        dominant, dom_n = max(((k, v) for k, v in counts.items() if k != "bash"),
                              key=lambda kv: kv[1], default=(None, 0))
        share = dom_n / total

    stats_desc = _stats_desc(counts, total, share)
    notes = []

    # 边界规则 D.4-2 优先（绑定包按源码主体判，优先级高于冲突规则）：
    # pybind11/boost::python 绑定 + C++ 源码 ≥70% → 判 cpp（即使 manifest 是
    # python 打包；协议附录 D.4-2: "pybind11 包装 C++ 库 → 判 cpp"）
    binding = _detect_binding(files, src)
    binding_override = bool(binding and dominant == "cpp" and share >= 0.70)

    # 冲突规则（§4.7）：manifest 与统计矛盾（具体语言 vs ≥70% 另一具体语言）→ mixed
    # 注: c/cpp 族 manifest 的族内 c/cpp 占比差异不算冲突（E13 按主体判）
    conflict = (m_lang is not None and dominant is not None and share >= 0.70
                and dominant != m_lang
                and (not family_manifest or dominant not in ("c", "cpp")))

    if binding_override:
        detected = "cpp"
        notes.append(f"绑定包: {binding}，C++ 主体 {share:.0%} → 判 cpp")
    elif conflict:
        notes.append(f"冲突: manifest={m_lang} 但统计 {dominant} 占 {share:.0%} → mixed")
        detected = "mixed"
    elif m_lang is not None:
        detected = m_lang
        if dominant and share < 0.70 and dominant != m_lang:
            notes.append(f"统计无 ≥70% 主体（{dominant} {share:.0%}），按 manifest 判 {m_lang}")
    elif dominant is not None and share >= 0.70:
        detected = dominant
    elif dominant is not None:
        detected = "mixed"
        notes.append(f"无 manifest 且主体占比 {share:.0%} < 70% → mixed")
    else:
        detected = "other"
        notes.append("无可统计源文件")

    # 绑定标记存在但未触发覆盖 → 注明即可
    if binding and not binding_override and detected in ("c", "cpp"):
        if detected == "c":
            detected = "cpp"
        notes.append(f"绑定包: {binding}")

    return {"detected_language": detected,
            "language_evidence": _evidence(build_system, manifest_desc, stats_desc),
            "notes": notes}


def _stats_desc(counts: Counter, total: int, share: float) -> str:
    if total == 0:
        return "无源文件可统计"
    top = ", ".join(f"{k}:{v}" for k, v in counts.most_common(4) if v)
    return _clip(f"源文件 {total} 个（{top}），主体占比 {share:.0%}")


def _evidence(build_system: str, manifest: str, source_stats: str) -> dict:
    return {"build_system": _clip(build_system),
            "manifest": _clip(manifest),
            "source_stats": _clip(source_stats)}


def _detect_binding(files, src: Path) -> str:
    """pybind11 / boost::python 绑定检测（D.4-2）。"""
    marks = ("pybind11", "boost_python", "Python_Additions", "find_package(Python")
    for p in files:
        if p.suffix.lower() in (".txt", ".cmake", ".py", ".toml", ".cfg") \
                or p.name in ("setup.py", "pyproject.toml", "CMakeLists.txt"):
            head = _read_head(p, 20000)
            if any(m.lower() in head.lower() for m in marks):
                rel = p.relative_to(src)
                return f"{rel} 含绑定标记"
    return ""


# ────────────────────────── CLI ──────────────────────────

def lang_preflight_cli(argv=None) -> int:
    import argparse
    parser = argparse.ArgumentParser(
        prog="lang-preflight",
        description="协议 v0.8 附录 D: 语言预检（checkout 后、适配主流程前）")
    parser.add_argument("software")
    parser.add_argument("version")
    parser.add_argument("--src", required=True, help="源码 checkout 目录")
    parser.add_argument("--lang", default=None,
                        help="任务语言（默认取 OHPCD_LANG，再默认 cpp）")
    parser.add_argument("--project-dir", default=None)
    args = parser.parse_args(argv)

    expected = (args.lang or os.environ.get("OHPCD_LANG") or "cpp").lower()
    if expected not in LANG_ENUM:
        log_fail(f"非法任务语言 {expected}（合法: {', '.join(LANG_ENUM)}）")
        return 2

    result = detect_language(args.src)
    detected = result["detected_language"]
    ev = result["language_evidence"]

    import json
    print(json.dumps({"expected": expected, **result}, ensure_ascii=False, indent=2))

    pdir = Path(args.project_dir) if args.project_dir else Path(find_project_dir())
    ver_dir = pdir / "archives" / (args.software[0].lower() if args.software else "_") \
        / args.software / args.version

    compatible = (detected == expected
                  or (detected in _COMPAT_FAMILY and expected in _COMPAT_FAMILY))
    if compatible:
        log_ok(f"语言匹配: task={expected}, detected={detected} — 继续适配主流程")
        try:
            from .result_report import write_lifecycle_draft
            write_lifecycle_draft(args.software, args.version, "lang_checked",
                                  summary=f"语言预检通过: detected={detected}")
        except Exception:
            pass
        try:
            from .feedback import record_event
            record_event(ver_dir, "lang_checked",
                         f"detected={detected} 与任务 {expected} 匹配")
        except Exception:
            pass
        return 0

    # 不匹配 → 终态 env_unsupported（协议规则 4/5：语言两字段必填，走校验器）
    reason = (f"任务标记 {expected}，实测源码为 {detected}"
              f"（{ev['build_system']}），无法按 {expected} 适配——"
              f"按协议 v0.8 §7.2 交平台语言迁移")
    log_fail(f"语言不匹配: task={expected}, detected={detected} → env_unsupported")
    log_warn("  协议要求: 不要硬着头皮适配；平台将按 detected_language 迁移/取消")
    try:
        from .result_report import result_cli
        rc = result_cli([
            args.software, args.version,
            "--status", "env_unsupported",
            "--failed-reason", reason,
            "--detected-language", detected,
            "--ev-build-system", ev["build_system"],
            "--ev-manifest", ev["manifest"],
            "--ev-source-stats", ev["source_stats"],
            "--force",
        ])
        if rc != 0:
            log_fail(f"result 上报失败 rc={rc}（语言字段校验未过？）")
            return rc
    except Exception as e:
        log_fail(f"result 上报异常: {e}")
        return 3
    try:
        from .feedback import record_event
        record_event(ver_dir, "lang_mismatch",
                     f"task={expected} detected={detected} → env_unsupported 迁移")
    except Exception:
        pass
    return 2


if __name__ == "__main__":
    sys.exit(lang_preflight_cli())
