# -*- coding: utf-8 -*-
"""preflight — PR 创建前置硬闸（harness 咽喉点，v12.9）

背景（goblinrs 744 PR 采样审计 2026-08-26）:
  open PR 中 CI 失败率 45%，其中 test() 空壳(L0c) ~20%、多包捎带 ~被 JC6 拦但
  浪费一轮 CI、压缩包入库已被 JC3 拦（历史遗留 167 文件）。
  共性根因: 机器人可绕过 ohc submit 的本地闸门直接 push + create-pr。
  本模块挂在 gitcode_pr.py create-pr（所有建 PR 路径的唯一咽喉），
  把失败拦截在 CI 之前。

检查项（编号与 CI 侧 JC 门禁对齐，同名同义）:
  PF1 单包闸   —— 一个 PR 只允许动一个 archives/<字母>/<包> 目录（JC6 前置）
  PF2 制品闸   —— 禁止提交压缩包/二进制归档（JC3 前置）
  PF3 测试闸   —— test_package/conanfile.py 的 test() 必须有 self.run 等实际
                  执行逻辑，空壳/print-only/do_nothing 直接拦（L0c 前置）
  PF4 依赖闸   —— conanfile 的 requires/tool_requires 必须已在制品仓存在；
                  缺失 = dependency_missing 上报终止，禁止捎带适配（W1 前置）

逃生口（与其他 OHC 闸门命名一致）: --no-preflight 或 OHC_PREFLIGHT=0
"""
from __future__ import annotations

import ast
import json
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

DEFAULT_REGISTRY = "https://conan.cnb.cool/OpenHarmonyPCDeveloper/Conan/-/packages"

# 压缩包/归档扩展（与 ci/scripts/junk_check.sh JC3 口径一致）
_ARCHIVE_EXT = re.compile(
    r"\.(tar\.gz|tar\.xz|tar\.bz2|tar\.zst|tgz|zip|7z|rar|gz|bz2|xz)$", re.I)
# requires 提取: 类属性 requires = (...) 与 self.requires("...") 两种形态
_REQ_CALL = re.compile(r"""(?:self\.)?(?:tool_)?requires\(\s*["']([^"'/]+/[^"']+)["']""")
_REQ_TUPLE = re.compile(r"""["']([A-Za-z0-9_+.-]+/[A-Za-z0-9_+.*!-]+)["']""")


def log_fail(msg: str) -> None:
    print(f"\033[31m✗ {msg}\033[0m")


def log_ok(msg: str) -> None:
    print(f"\033[32m✓ {msg}\033[0m")


# ── 变更文件采集 ──────────────────────────────────────────────

def changed_files(repo_dir: Path, base: str, head: str) -> list[str]:
    """base...head 三点 diff 的变更文件清单。"""
    r = subprocess.run(
        ["git", "-C", str(repo_dir), "diff", "--name-only", f"{base}...{head}"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=120)
    if r.returncode != 0:
        raise RuntimeError(f"git diff 失败: {(r.stderr or '').strip()[:200]}")
    return [ln.strip() for ln in (r.stdout or "").splitlines() if ln.strip()]


def _pkg_dirs(files: list[str]) -> set[str]:
    """archives/<字母>/<包> 目录集合。"""
    out = set()
    for f in files:
        m = re.match(r"^archives/([a-z0-9])/([^/]+)/", f)
        if m:
            out.add(f"archives/{m.group(1)}/{m.group(2)}")
    return out


# ── PF1 单包闸（JC6 前置）────────────────────────────────────

def check_single_package(files: list[str]) -> list[str]:
    dirs = _pkg_dirs(files)
    if len(dirs) > 1:
        return [f"PF1 单包闸: 本 PR 改动涉及 {len(dirs)} 个软件包目录，"
                "一个 PR 只允许一个包（JC6 同口径前置拦截）: "
                + ", ".join(sorted(dirs))]
    return []


# ── PF2 制品闸（JC3 前置）────────────────────────────────────

def check_no_binaries(files: list[str]) -> list[str]:
    hits = [f for f in files if _ARCHIVE_EXT.search(f)]
    if hits:
        return ["PF2 制品闸: 禁止提交压缩包/归档文件（源码仓只收源码与配方，"
                "JC3 同口径前置拦截）: " + ", ".join(hits[:5])
                + (" ..." if len(hits) > 5 else "")]
    return []


# ── PF3 测试闸（L0c 前置）────────────────────────────────────

def _test_method_calls(tree: ast.Module, method: str = "test") -> list[ast.Call]:
    """收集 <method>() 方法体内的所有函数调用 AST 节点。"""
    calls: list[ast.Call] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == method:
            for sub in ast.walk(node):
                if isinstance(sub, ast.Call):
                    calls.append(sub)
    return calls


def _strip_docstring(body: list[ast.stmt]) -> list[ast.stmt]:
    if (body and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)):
        return body[1:]
    return body


def check_test_substance(pkg_dir: Path) -> list[str]:
    """test_package/conanfile.py 的 test() 必须实际执行被测物。

    口径与 CI L0c 一致: test() 需调用 self.run（或等效 self.run_command）
    执行测试程序；空壳/pass-only/print-only/do_nothing 一律拦。
    """
    tp = pkg_dir / "test_package" / "conanfile.py"
    if not tp.exists():
        # 结构问题由 W2/L0 闸负责，这里不重复报
        return []
    try:
        tree = ast.parse(tp.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError as e:
        return [f"PF3 测试闸: {tp.name} 语法错误: {e}"]
    for node in ast.walk(tree):
        if not (isinstance(node, ast.FunctionDef) and node.name == "test"):
            continue
        body = _strip_docstring(node.body)
        if not body or all(isinstance(s, ast.Pass) for s in body):
            return [f"PF3 测试闸: test_package/conanfile.py 的 test() 为空壳"
                    "（pass/无实现）——CI L0c 必拦，先补测试逻辑再提 PR"]
        ran = any(
            isinstance(c.func, ast.Attribute)
            and c.func.attr in ("run", "run_command")
            and isinstance(c.func.value, ast.Name)
            and c.func.value.id == "self"
            for c in _test_method_calls(tree))
        prints_only = all(
            isinstance(c.func, ast.Attribute) and c.func.attr == "print"
            for c in _test_method_calls(tree)) and _test_method_calls(tree)
        if not ran and prints_only:
            return ["PF3 测试闸: test_package/conanfile.py 的 test() 只有 print，"
                    "未执行被测程序——需 self.run(...) 真实运行（CI L0c 口径）"]
        if not ran:
            return ["PF3 测试闸: test_package/conanfile.py 的 test() 未调用 "
                    "self.run()/run_command() 执行测试程序——空壳测试 CI L0c "
                    "必拦，参考 docs/ADAPTATION_GUIDE.md#5-test_package"]
    return []


# ── PF4 依赖闸（W1 前置）─────────────────────────────────────

def parse_requires(conanfile: Path) -> list[tuple[str, str]]:
    """返回 [(name, version), ...]；跳过 conan 内置与占位版本。"""
    if not conanfile.exists():
        return []
    text = conanfile.read_text(encoding="utf-8", errors="replace")
    out: list[tuple[str, str]] = []
    for m in _REQ_CALL.finditer(text):
        name, _, ver = m.group(1).partition("/")
        out.append((name.strip(), ver.strip()))
    # 类属性 requires = ("a/1.0", "b/2.0") / requires = "a/1.0", "b/2.0"
    # 两种形态兜底（conan 2 允许无括号元组）
    if not out:
        blocks = re.findall(r"^\s*(?:tool_)?requires\s*=\s*[\(\{\[].*?[\)\}\]]",
                            text, re.M | re.S)
        blocks += re.findall(r"^\s*(?:tool_)?requires\s*=(?!\s*[\(\{\[]).+$",
                             text, re.M)
        for blk in blocks:
            for t in _REQ_TUPLE.finditer(blk):
                name, _, ver = t.group(1).partition("/")
                out.append((name.strip(), ver.strip()))
    builtin = {"conan"}
    return [(n, v) for n, v in out
            if n and n.lower() not in builtin and v not in ("", "*")]


def probe_registry(name: str, registry: str = DEFAULT_REGISTRY) -> set[str]:
    """查询制品仓某包的全部版本 refs（公开 API）。

    注意: 该 API 的 q 需通配符形态（实测 bare name 返回 0，name/* 才命中）。
    异常时返回空集=按缺失处理（fail-closed）。
    """
    try:
        req = urllib.request.Request(
            f"{registry}/v2/conans/search?q={urllib.parse.quote(name + '/*', safe='')}",
            headers={"User-Agent": "Conan/2.9.1"})
        with urllib.request.urlopen(req, timeout=25) as r:
            refs = json.loads(r.read().decode("utf-8", "replace")).get("results", [])
        return {x for x in refs if x.split("/")[0] == name}
    except Exception:
        return set()


def check_deps_in_registry(pkg_dir: Path,
                           registry: str = DEFAULT_REGISTRY) -> list[str]:
    conanfile = pkg_dir / "conanfile.py"
    reqs = parse_requires(conanfile)
    findings: list[str] = []
    for name, ver in reqs:
        refs = probe_registry(name, registry)
        if not refs:
            findings.append(
                f"PF4 依赖闸: requires '{name}/{ver}' 在制品仓查无此包——"
                "禁止捎带适配依赖！正确动作: 立即上报 "
                f"`ohc-run.py result <pkg> <ver> --status dependency_missing` "
                "终止本任务，由调度侧先建依赖任务")
            continue
        if not any(r.startswith(f"{name}/{ver}") for r in refs):
            vers = sorted({r.split("/", 1)[1] for r in refs})[:8]
            findings.append(
                f"PF4 依赖闸: requires '{name}/{ver}' 版本不在制品仓"
                f"（在仓版本: {', '.join(vers)}）——改用在仓版本，或上报 "
                "dependency_missing 由依赖任务先行")
    return findings


# ── 总入口 ───────────────────────────────────────────────────

def check_patch_platform_macro(repo_dir: Path, files: list[str]) -> list[str]:
    """PF5 补丁平台宏闸（R8，v12.17）：patches/ 中默认禁止引入平台宏。

    只检查本次 PR 变更的补丁文件（历史存量不拦），只命中补丁新增行
    （'+' 开头，排除 '+++' 文件头）——上下文行里的 __OHOS__ 属上游源码，
    R8 不管辖。
    """
    findings: list[str] = []
    for f in files:
        if "patches/" not in f or not f.endswith((".patch", ".diff")):
            continue
        pf = repo_dir / f
        if not pf.is_file():
            continue
        try:
            text = pf.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if line.startswith("+") and not line.startswith("+++") \
                    and "__OHOS__" in line:
                findings.append(
                    f"PF5 补丁平台宏闸(R8): {f}:{lineno} 新增 `__OHOS__`——"
                    "patches/ 默认禁止平台宏（口径 iron-rules.md R8），"
                    "优先 POSIX 兼容写法。确属例外（如识别 libc 的探针程序）"
                    "须在 PR 说明理由，并 --no-preflight 显式跳过")
                break
    return findings


_PF6_SHARED_PREFIX = re.compile(
    r'environ\.get\(\s*["\']SYS_PREFIX|'
    r'environ\[\s*["\']SYS_PREFIX["\']\s*\]|'
    r'["\']/usr/local["\']')


def check_recipe_shared_prefix(repo_dir: Path, files: list[str]) -> list[str]:
    """PF6 依赖注入前缀闸（R49/E524，v12.17）：禁止注入共享系统前缀。

    命中模式：环境变量读取 SYS_PREFIX、引号包裹的 /usr/local 字面量。
    合法形态不拦：os.environ.get("DEFAULT_PREFIX")（可覆盖）、
    os.path.join(expanduser("~"), "usr", "local")（用户级前缀）、
    文档字符串中裸写的 /usr/local（无引号）。参考实现：
    archives/a/asterisk-srtp/22.10.1/conanfile.py。
    """
    findings: list[str] = []
    for f in files:
        if not f.endswith("conanfile.py") or "/patches/" in f:
            continue
        pf = repo_dir / f
        if not pf.is_file():
            continue
        try:
            text = pf.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith("#"):        # 注释行不拦
                continue
            if _PF6_SHARED_PREFIX.search(line):
                findings.append(
                    f"PF6 依赖注入前缀闸(R49/E524): {f}:{lineno} 注入共享系统前缀——"
                    "CI worker 与本地共享文件系统会互相污染（E524: 19 轮 CI 全挂根因）。"
                    "改用 build_folder 私有 prefix（CPPFLAGS/LDFLAGS/PKG_CONFIG_PATH "
                    "三链指向），参考 archives/a/asterisk-srtp/22.10.1/conanfile.py")
                break
    return findings


def run_preflight(repo_dir, base: str, head: str,
                  registry: str = DEFAULT_REGISTRY) -> tuple[bool, list[str]]:
    """执行 PF1-PF6。返回 (通过?, 全部问题清单)。任何异常 fail-closed。"""
    # 调用方可能传 str（gitcode_pr._git_toplevel 返回 str），
    # 统一包装为 Path，避免下方 repo_dir / d 抛 str/str TypeError（PF0 假故障）
    repo_dir = Path(repo_dir)
    findings: list[str] = []
    try:
        files = changed_files(repo_dir, base, head)
    except Exception as e:
        return False, [f"PF0 环境闸: 无法计算变更文件（{e}）——"
                       "fail-closed 拦截；确认本地分支与 base 后重试，"
                       "或 --no-preflight 显式跳过"]
    findings += check_single_package(files)
    findings += check_no_binaries(files)
    findings += check_patch_platform_macro(repo_dir, files)
    findings += check_recipe_shared_prefix(repo_dir, files)
    dirs = sorted(_pkg_dirs(files))
    for d in dirs:                      # PF1 已保证最多 1 个
        pkg = repo_dir / d
        findings += check_test_substance(pkg)
        findings += check_deps_in_registry(pkg, registry)
    return (not findings), findings


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="PR 创建前置硬闸（调试入口）")
    ap.add_argument("repo_dir", type=Path)
    ap.add_argument("base")
    ap.add_argument("head")
    ap.add_argument("--registry", default=DEFAULT_REGISTRY)
    a = ap.parse_args()
    ok, probs = run_preflight(a.repo_dir, a.base, a.head, a.registry)
    for p in probs:
        log_fail(p)
    if ok:
        log_ok("preflight PF1-PF6 全部通过")
    sys.exit(0 if ok else 1)
