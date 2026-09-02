# -*- coding: utf-8 -*-
"""v12.13 协议 v0.8 附录 D 测试：语言判定 + 结构化字段 + 校验规则"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
PASS = FAIL = 0


def check(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok  {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name} {extra}")


def mk_tree(base: Path, files: dict):
    for rel, content in files.items():
        p = base / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")


def make_env(tmp, out=None):
    env = os.environ.copy()
    env["OHC_PROJECT_DIR"] = str(tmp / "proj")
    env.pop("OHC_RESULT_OUT", None)
    env.pop("OHPCD_LANG", None)
    if out:
        env["OHC_RESULT_OUT"] = str(out)
    return env


def run_cli(argv, env):
    return subprocess.run(
        [sys.executable, "-X", "utf8", str(REPO / "scripts" / "ohc-run.py")] + argv,
        capture_output=True, text=True, env=env, cwd=str(REPO), timeout=120)


def main():
    from ohc.lang_detect import detect_language

    tmp = Path(tempfile.mkdtemp(prefix="v1213_"))
    proj = tmp / "proj"
    (proj / "archives" / "t" / "tsw" / "1.0").mkdir(parents=True)
    proj.joinpath("SKILL.md").write_text("# stub", encoding="utf-8")

    # ── D-1: 判定场景 ──
    s = tmp / "rust1"; mk_tree(s, {"Cargo.toml": "[package]\nname = \"hyperfine\"\n", "src/main.rs": "fn main(){}"})
    d = detect_language(s)
    check("D1a rust via Cargo.toml", d["detected_language"] == "rust", d)
    check("D1b evidence 三项",
          set(d["language_evidence"]) == {"build_system", "manifest", "source_stats"})

    s = tmp / "py1"; mk_tree(s, {"setup.py": "from setuptools import setup\nsetup(name='x')\n", "x/__init__.py": "", "x/core.py": "a=1"})
    d = detect_language(s)
    check("D1c python via setup.py", d["detected_language"] == "python", d)

    s = tmp / "go1"; mk_tree(s, {"go.mod": "module x\n", "main.go": "package main"})
    d = detect_language(s)
    check("D1d go via go.mod", d["detected_language"] == "go", d)

    # C/C++ 混编 → 按主体判（E13，不算 mixed）
    s = tmp / "cxx"; mk_tree(s, {
        "CMakeLists.txt": "cmake_minimum_required(VERSION 3.10)\nproject(foo CXX)\n",
        "src/a.cpp": "", "src/b.cpp": "", "src/b.h": "", "src/legacy.c": ""})
    d = detect_language(s)
    check("D1e C/C++ 混编判 cpp", d["detected_language"] == "cpp", d)

    s = tmp / "c1"; mk_tree(s, {"configure.ac": "AC_INIT([zlib], [1.3])\n", "src/a.c": "", "src/a.h": ""})
    d = detect_language(s)
    check("D1f 纯 C autotools 判 c", d["detected_language"] == "c", d)

    # 绑定包: setup.py + pybind11 + C++ 主体 → cpp
    s = tmp / "bind"; mk_tree(s, {
        "setup.py": "from setuptools import setup\nsetup(name='pkg', ext_modules=[pybind11])\n",
        "src/binding.cpp": "// pybind11 wrapper", "src/core1.cpp": "", "src/core2.cpp": ""})
    d = detect_language(s)
    check("D1g pybind11 绑定判 cpp", d["detected_language"] == "cpp", d)
    check("D1h 绑定 notes", any("绑定" in n for n in d["notes"]), d["notes"])

    # 冲突: cargo manifest + 95% .c → mixed
    s = tmp / "mix"; mk_tree(s, {"Cargo.toml": "[package]\nname='x'\n",
                                 **{f"src/m{i}.c": "" for i in range(19)}, "src/x.rs": ""})
    d = detect_language(s)
    check("D1i 冲突判 mixed", d["detected_language"] == "mixed", d)

    # 辅助脚本不算主体（bash 不参与占比）
    s = tmp / "aux"; mk_tree(s, {"CMakeLists.txt": "project(foo)\n", "src/a.cpp": "",
                                 "tools/build.sh": "", "scripts/fix.py": ""})
    d = detect_language(s)
    check("D1j 辅助脚本不干扰", d["detected_language"] == "cpp", d)

    # 无 manifest + 无源码 → other
    s = tmp / "empty"; mk_tree(s, {"README.md": "hi"})
    d = detect_language(s)
    check("D1k 无源码判 other", d["detected_language"] == "other", d)

    # ── D-2: lang-preflight CLI 匹配路径（cpp 任务 + cpp 源码）──
    s = tmp / "cpp1"; mk_tree(s, {"CMakeLists.txt": "project(foo CXX)\n", "src/a.cpp": ""})
    out = tmp / "out2"
    r = run_cli(["lang-preflight", "tsw", "1.0", "--src", str(s)],
                make_env(tmp, out))
    check("D2a 匹配 exit 0", r.returncode == 0, r.stdout[-200:] + r.stderr[-200:])
    f2 = out / "result.json"
    d2 = json.loads(f2.read_text(encoding="utf-8")) if f2.exists() else {}
    check("D2b 草稿 milestone=lang_checked",
          d2.get("milestone") == "lang_checked" and d2.get("draft") is True, d2.get("milestone"))

    # OHPCD_LANG 注入 + c/cpp 族兼容
    env3 = make_env(tmp, tmp / "out3")
    env3["OHPCD_LANG"] = "cpp"
    r = run_cli(["lang-preflight", "tsw", "1.0", "--src", str(tmp / "c1")], env3)
    check("D2c c 源码 + cpp 任务族兼容 exit 0", r.returncode == 0,
          r.stdout[-150:] + r.stderr[-150:])

    # ── D-3: mismatch → 终态 env_unsupported + 双字段 ──
    out4 = tmp / "out4"
    env4 = make_env(tmp, out4)
    env4["OHPCD_LANG"] = "cpp"
    r = run_cli(["lang-preflight", "tsw", "1.0", "--src", str(tmp / "rust1")], env4)
    check("D3a mismatch exit 2", r.returncode == 2, r.stdout[-150:])
    f4 = out4 / "result.json"
    d4 = json.loads(f4.read_text(encoding="utf-8")) if f4.exists() else {}
    check("D3b 终态 env_unsupported + draft:false",
          d4.get("status") == "env_unsupported" and d4.get("draft") is False,
          (d4.get("status"), d4.get("draft")))
    check("D3c detected_language=rust", d4.get("detected_language") == "rust")
    ev = d4.get("language_evidence") or {}
    check("D3d evidence 三项且 ≤200",
          set(ev) == {"build_system", "manifest", "source_stats"}
          and all(isinstance(v, str) and 0 < len(v) <= 200 for v in ev.values()), ev)

    # ── D-4: 校验器规则 4/5 ──
    out5 = tmp / "out5"
    env5 = make_env(tmp, out5)
    r = run_cli(["result", "tsw", "1.0", "--status", "env_unsupported",
                 "--failed-reason", "D4 缺语言字段"], env5)
    check("D4a env_unsupported 缺 detected_language 被拒", r.returncode != 0)

    r = run_cli(["result", "tsw", "1.0", "--status", "env_unsupported",
                 "--failed-reason", "D4b 自由文本语言",
                 "--detected-language", "Rust",
                 "--ev-build-system", "cargo", "--ev-manifest", "Cargo.toml",
                 "--ev-source-stats", "20 rs files"], env5)
    check("D4b 自由文本语言被拒", r.returncode != 0)

    r = run_cli(["result", "tsw", "1.0", "--status", "failed_build",
                 "--failed-reason", "D4c",
                 "--detected-language", "cpp"], env5)
    f5 = out5 / "result.json"
    d5 = json.loads(f5.read_text(encoding="utf-8")) if f5.exists() else {}
    check("D4c 非 env 状态带语言字段被拒", r.returncode != 0 or d5.get("status") != "build_failed")

    # enum 规范化: failed_build 输入 → build_failed 输出
    r = run_cli(["result", "tsw", "1.0", "--status", "failed_build",
                 "--failed-reason", "D4d 规范化"], env5)
    d5 = json.loads(f5.read_text(encoding="utf-8")) if f5.exists() else {}
    check("D4d failed_build→build_failed 规范化",
          d5.get("status") == "build_failed" and d5.get("detected_language") is None,
          (d5.get("status"), d5.get("detected_language")))

    # 新枚举值可用
    for st in ("bootstrap_failed", "timeout", "internal_error"):
        r = run_cli(["result", "tsw", "1.0", "--status", st,
                     "--failed-reason", f"D4e {st}", "--force"], env5)
        ok = r.returncode == 0 and json.loads(
            (out5 / "result.json").read_text(encoding="utf-8")).get("status") == st
        check(f"D4e {st} 枚举可用", ok)

    print(f"\n=== {PASS} passed, {FAIL} failed ===")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
