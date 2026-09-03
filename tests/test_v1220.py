# -*- coding: utf-8 -*-
"""v12.20 全量 PR 审计落地验证：PF5 扩面/PF7/PF8/PF9/PF3 扩面/R52 行为级测试"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts" / "ohc"))
import preflight  # noqa: E402

PASS = FAIL = 0
GITBIN = "/data/service/hnp/git.org/git_2.45.2/bin/git"

_orig_run = subprocess.run
def _run_shim(args, *a, **kw):
    # 沙箱 posix_spawn 不搜 PATH；生产环境 git 在 PATH 上不受影响
    if args and args[0] == "git":
        args = [GITBIN] + list(args[1:])
    return _orig_run(args, *a, **kw)
preflight.subprocess.run = _run_shim


def check(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok  {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name} {extra}")


def w(root, rel, text=""):
    p = Path(root) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def git(*args, cwd):
    subprocess.run([GITBIN, *args], cwd=cwd, capture_output=True, timeout=60, check=True)


CONAN_FULL = (
    'settings = "os", "arch", "compiler", "build_type"\n'
    'name = "demo"\n'
    'version = "1.0"\n'
)


# ── PF7 源URL闸 ─────────────────────────────────────────────
def test_pf7():
    with tempfile.TemporaryDirectory() as td:
        f = "archives/d/demo/1.0/conandata.yml"
        cases_hit = [
            'sources:\n  url:\n    - "https://gh-proxy.com/https://github.com/x/y/archive/v1.tar.gz"\n',
            'sources:\n  url: "http://example.com/y.tar.gz"\n',
            'sources:\n  url: "file:///home/u/.build-cache/predl_cache/y.tar.gz"\n',
            'sources:\n  url: "/storage/Users/u/y.tar.gz"\n',
            'sources:\n  url: "https://deb.debian.org/debian/pool/main/y/y.tar.gz"\n',
            'sources:\n  url: "https://snapshot.debian.org/archive/y/y+dfsg1.tar.gz"\n',
            'sources:\n  url: "https://gitcode.com/mirror/y/-/archive/v1/y.tar.gz"\n',
        ]
        for i, body in enumerate(cases_hit):
            w(td, f, body)
            r = preflight.check_source_urls(Path(td), [f])
            check(f"PF7 拦#{i}", len(r) == 1 and "R39" in r[0], str(r)[:80])
        w(td, f, 'sources:\n  url: "https://github.com/x/y/archive/v1.tar.gz"\n')
        r = preflight.check_source_urls(Path(td), [f])
        check("PF7 官方源放行", r == [], str(r)[:80])
        mf = "archives/d/demo/1.0/manifest.yaml"
        w(td, mf, 'source:\n  url: "https://github.com/x/y/archive/v1.tar.gz"\n')
        r = preflight.check_source_urls(Path(td), [mf])
        check("PF7 manifest 官方源放行", r == [])
        w(td, mf, 'source:\n  url: "https://ghfast.top/https://github.com/x/y.tar.gz"\n')
        r = preflight.check_source_urls(Path(td), [mf])
        check("PF7 manifest 镜像拦", len(r) == 1)


# ── PF8 配方静态闸 ──────────────────────────────────────────
def test_pf8():
    with tempfile.TemporaryDirectory() as td:
        cf = "archives/d/demo/1.0/conanfile.py"
        files = [cf]
        w(td, cf, CONAN_FULL)
        r = preflight.check_recipe_static(Path(td), files)
        check("PF8 纯库+合规 = 通过", r == [], str(r)[:120])

        w(td, cf, 'settings = "os", "arch"\nname = "demo"\nversion = "1.0"\n')
        r = preflight.check_recipe_static(Path(td), files)
        check("PF8 settings 缺项拦", any("settings" in x for x in r), str(r)[:120])

        files2 = ["archives/d/Demo/1.0/conanfile.py"]
        w(td, files2[0], CONAN_FULL)
        r = preflight.check_recipe_static(Path(td), files2)
        check("PF8 slug 大写拦", any("slug" in x for x in r), str(r)[:120])

        files3 = ["archives/d/demo/2.0/conanfile.py"]
        w(td, files3[0], CONAN_FULL)
        r = preflight.check_recipe_static(Path(td), files3)
        check("PF8 version 不一致拦", any("不一致" in x for x in r), str(r)[:120])

        cli = CONAN_FULL + 'package_type = "application"\n'
        w(td, cf, cli)
        r = preflight.check_recipe_static(Path(td), files)
        check("PF8 CLI 缺 commands.json 拦", any("commands.json" in x for x in r), str(r)[:120])

        w(td, "archives/d/demo/commands.json", json.dumps({
            "name": "demo", "type": "tool",
            "versions": {"1.0": {"ref": "demo/1.0", "binary": True}}}))
        r = preflight.check_recipe_static(Path(td), files)
        check("PF8 CLI 合规 commands.json 通过", r == [], str(r)[:120])

        w(td, "archives/d/demo/commands.json", json.dumps({
            "name": "demo", "type": "library",
            "versions": {"1.0": {"ref": "demo/1.0"}}}))
        r = preflight.check_recipe_static(Path(td), files)
        check("PF8 type!=tool 拦", any("tool" in x for x in r), str(r)[:120])

        w(td, cf, CONAN_FULL)
        w(td, "archives/d/demo/commands.json", "{}")
        r = preflight.check_recipe_static(Path(td), files)
        check("PF8 纯库误加 commands.json 拦", any("纯库" in x for x in r), str(r)[:120])


# ── PF9 分支/路径闸 ─────────────────────────────────────────
def test_pf9():
    with tempfile.TemporaryDirectory() as td:
        r = preflight.check_branch_and_paths(Path(td), ["SKILL.md"])
        check("PF9 非 archives 改动静默", r == [])
        r = preflight.check_branch_and_paths(Path(td), ["archives/d/demo/readme.txt"])
        check("PF9 缺版本目录层拦", any("No packages" in x for x in r), str(r)[:100])

        git("init", "-b", "main", cwd=td)
        git("config", "user.email", "t@t", cwd=td)
        git("config", "user.name", "t", cwd=td)
        w(td, "base.txt", "x")
        git("add", ".", cwd=td)
        git("commit", "-m", "base", cwd=td)
        files = ["archives/d/demo/1.0/conanfile.py"]
        w(td, files[0], CONAN_FULL)
        git("checkout", "-b", "feat/wrong-name-9.9", cwd=td)
        r = preflight.check_branch_and_paths(Path(td), files)
        check("PF9 分支名不匹配拦", any("L0n" in x for x in r), str(r)[:100])
        git("checkout", "-b", "feat/demo-1.0", cwd=td)
        r = preflight.check_branch_and_paths(Path(td), files)
        check("PF9 feat/pkg-ver 放行", r == [], str(r)[:100])
        git("checkout", "main", cwd=td)
        r = preflight.check_branch_and_paths(Path(td), files)
        check("PF9 main 编辑路径豁免", r == [], str(r)[:100])


# ── PF3 扩面 ────────────────────────────────────────────────
def test_pf3x():
    with tempfile.TemporaryDirectory() as td:
        pkg = Path(td) / "archives/d/demo/1.0"
        pkg.mkdir(parents=True)
        (pkg / "test_package").mkdir()
        (pkg / "test_package/conanfile.py").write_text("x = 1")
        r = preflight.check_test_package_files(pkg)
        check("PF3x 无测试源+缺双MANIFEST 拦", len(r) == 3, str(r)[:150])
        (pkg / "test_package/test.sh").write_text("run demo")
        (pkg / "test_package/MANIFEST.yml").write_text("name: t")
        (pkg / "manifest.yaml").write_text("package: demo")
        r = preflight.check_test_package_files(pkg)
        check("PF3x 齐备通过", r == [], str(r)[:150])
        (pkg / "manifest.yaml").write_text("")
        r = preflight.check_test_package_files(pkg)
        check("PF3x 空 manifest 拦", any("manifest.yaml" in x for x in r), str(r)[:120])


# ── PF5 扩面（需 git diff）──────────────────────────────────
def test_pf5x():
    with tempfile.TemporaryDirectory() as td:
        f = "archives/d/demo/1.0/conanfile.py"
        git("init", "-b", "main", cwd=td)
        git("config", "user.email", "t@t", cwd=td)
        git("config", "user.name", "t", cwd=td)
        w(td, f, "name = 'demo'\n")
        git("add", ".", cwd=td)
        git("commit", "-m", "base", cwd=td)
        w(td, f, "name = 'demo'\ntoolchain.defines.append('-D__OHOS__=1')\n")
        git("add", ".", cwd=td)
        git("commit", "-m", "inject", cwd=td)
        r = preflight.check_recipe_macro_injection(Path(td), "HEAD~1", "HEAD", [f])
        check("PF5x -D__OHOS__ 注入拦", len(r) == 1 and "R8" in r[0], str(r)[:100])
        w(td, f, "name = 'demo'\ncontent.replace('__linux__', '__OHOS__')\n")
        git("add", ".", cwd=td)
        git("commit", "-m", "rep", cwd=td)
        r = preflight.check_recipe_macro_injection(Path(td), "HEAD~1", "HEAD", [f])
        check("PF5x replace 注入拦", len(r) == 1, str(r)[:100])
        w(td, f, "name = 'demo'\nif self.settings.os == 'OHOS':\n    pass\n")
        git("add", ".", cwd=td)
        git("commit", "-m", "normal", cwd=td)
        r = preflight.check_recipe_macro_injection(Path(td), "HEAD~1", "HEAD", [f])
        check("PF5x settings.OHOS 正常代码放行", r == [], str(r)[:100])


# ── R52 审计一致性 ──────────────────────────────────────────
def test_r52():
    with tempfile.TemporaryDirectory() as td:
        pkg = Path(td)
        hard = ["PF7 源URL闸: xxx"]
        w(td, ".audit-result.json", json.dumps({"verdict": "pass", "issues": []}))
        r = preflight.check_audit_consistency(pkg, hard)
        check("R52 pass+硬闸命中 → 审计失真", len(r) == 1 and "审计失真" in r[0], str(r)[:80])
        w(td, ".audit-result.json", json.dumps({"verdict": "fail", "issues": []}))
        r = preflight.check_audit_consistency(pkg, hard)
        check("R52 verdict=fail 不追加", r == [])
        (pkg / ".audit-result.json").unlink()
        r = preflight.check_audit_consistency(pkg, hard)
        check("R52 无审计文件不追加", r == [])
        r = preflight.check_audit_consistency(pkg, [])
        check("R52 无硬闸命中不追加", r == [])


if __name__ == "__main__":
    for fn in (test_pf7, test_pf8, test_pf9, test_pf3x, test_pf5x, test_r52):
        print(f"== {fn.__name__} ==")
        fn()
    print(f"\nv12.20 gate tests: {PASS} pass, {FAIL} fail")
    sys.exit(1 if FAIL else 0)
