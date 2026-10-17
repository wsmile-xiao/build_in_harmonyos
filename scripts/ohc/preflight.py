# -*- coding: utf-8 -*-
"""preflight — PR 创建前置硬闸（harness 咽喉点，v12.9；v12.20 扩至 PF1-PF9+R52）

背景（goblinrs 744 PR 采样审计 2026-08-26）:
  open PR 中 CI 失败率 45%，其中 test() 空壳(L0c) ~20%、多包捎带 ~被 JC6 拦但
  浪费一轮 CI、压缩包入库已被 JC3 拦（历史遗留 167 文件）。
  共性根因: 机器人可绕过 ohc submit 的本地闸门直接 push + create-pr。
  本模块挂在 gitcode_pr.py create-pr（所有建 PR 路径的唯一咽喉），
  把失败拦截在 CI 之前。

检查项（编号与 CI 侧 JC 门禁对齐，同名同义；v12.20 扩至 PF1-PF9+R52 交叉校验）:
  PF1 单包闸   —— 一个 PR 只允许动一个 archives/<字母>/<包> 目录（JC6 前置）
  PF2 制品闸   —— 禁止提交压缩包/二进制归档（JC3 前置）
  PF3 测试闸   —— test_package/conanfile.py 的 test() 必须有 self.run 等实际
                  执行逻辑，空壳/print-only/do_nothing 直接拦（L0c 前置）；
                  v12.20 扩面：test_package 必须有测试源文件（.c/.cpp/.sh/.py，
                  conanfile.py 除外）+ test_package/MANIFEST.yml 与包级
                  manifest.yaml 存在且非空（L0c/L0e 前置）
  PF4 依赖闸   —— conanfile 的 requires/tool_requires 必须已在制品仓存在；
                  缺失 = dependency_missing 上报终止，禁止捎带适配（W1 前置）
  PF5 平台宏闸 —— patches/*.patch 新增行禁 __OHOS__（R8）；v12.20 扩面堵
                  绕道形态：conanfile.py 新增行的 -D__OHOS__ 注入与
                  replace() 动态注入（64+27 例，R8 High 占比 61%）
  PF6 前缀闸   —— 禁注入共享系统前缀 SYS_PREFIX//usr/local（R49/E524）
  PF7 源URL闸  —— conandata.yml/manifest.yaml 的源 URL 必须 https 官方源：
                  镜像域名黑名单/明文 http/file:///绝对路径/Debian 重打包
                  一律拦；gitcode/gitee 搬运源拦（例外须 PR 说明，
                  R39 1,061 条违规的 90%+ 静态可判）
  PF8 配方闸   —— settings 四项齐全（L0p）；目录 slug 小写规范（L0m）；
                  version 与版本目录一致；CLI 包（package_type=application
                  或 bindirs 非空）必须有 commands.json 且 name/type=tool/
                  versions.ref 全对齐，纯库包必须无（R38 705 条）
  PF9 分支闸   —— 变更路径必须落在单一 archives/<字母>/<包>/<版本>/ 目录
                  （防 "No packages to build" 490 条）；分支名须为
                  pkg-version 或 feat|fix/pkg-version（L0n ~550 条）
  R52 交叉校验 —— .audit-result.json verdict=pass 但上述硬闸命中 → 追加
                  "审计失真"发现（一票否决档，#2204/#4237/#4321 教训）

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



# ── PF5 扩面：配方平台宏注入（v12.20，R8 绕道形态）────────────

def _added_lines(repo_dir: Path, base: str, head: str, path: str) -> list[str]:
    """取某文件在 base...head diff 中的新增行（'+' 且非 '+++'）。"""
    r = subprocess.run(
        ["git", "-C", str(repo_dir), "diff", f"{base}...{head}", "--", path],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=60)
    return [ln[1:] for ln in (r.stdout or "").splitlines()
            if ln.startswith("+") and not ln.startswith("+++")]


def check_recipe_macro_injection(repo_dir: Path, base: str, head: str,
                                 files: list[str]) -> list[str]:
    """PF5 扩面：conanfile.py 新增行禁止 -D__OHOS__ 注入与 replace 注入。

    绕道形态（语料实证 64+27 例）：不写进 patches/ 而在配方里用
    cppflags/defines 注入 -D__OHOS__，或 replace_in_file 源码时动态塞
    __OHOS__。存量行豁免（只看本 PR 新增行，与 PF5 补丁闸口径一致）。
    """
    findings: list[str] = []
    for f in files:
        if not f.endswith("conanfile.py") or not f.startswith("archives/"):
            continue
        for lineno, ln in enumerate(_added_lines(repo_dir, base, head, f), 1):
            hit = None
            if "-D__OHOS__" in ln:
                hit = "-D__OHOS__ 注入"
            elif "__OHOS__" in ln and "replace" in ln:
                hit = "replace() 动态注入 __OHOS__"
            if hit:
                findings.append(
                    f"PF5 平台宏闸(R8): {f} 新增行 {hit}——绕开 patches/ 禁令"
                    "的等价违规（语料 64+27 例），改走 POSIX 兼容写法或规范"
                    "patches/+PR 说明例外；确属例外 --no-preflight 显式跳过")
                break
    return findings


# ── PF7 源 URL 闸（v12.20，R39 前置）─────────────────────────

_PF7_MIRROR_HOSTS = (
    "gh-proxy.com", "ghfast.top", "ghproxy.net", "ghproxy.com",
    "mirror.ghproxy.com", "gitclone.com", "kkgithub.com", "gh-proxy.xyz",
    "moeyy.cn", "moeyy.xyz", "fastgit.org", "hub.fastgit.org",
    "gh.api.99988866.xyz", "cnb.cool")
_PF7_DEBIAN_HOSTS = ("deb.debian.org", "snapshot.debian.org",
                     "security.debian.org", "archive.debian.org")
_PF7_VALUE = re.compile(r'["\']([^"\']+)["\']')
_PF7_URL_ITEM = re.compile(r'^\s*-\s*["\']([^"\']+)["\']')


def _pf7_classify(url: str) -> str | None:
    low = url.lower()
    if low.startswith("file://"):
        return "file:// 本机缓存泄漏（CI 预下载改写未还原，71 例）"
    if low.startswith("http://"):
        return "明文 http 源（R39 要求 https）"
    if url.startswith("/"):
        return "绝对本地路径"
    m = re.match(r"https?://([^/]+)", low)
    host = m.group(1) if m else ""
    if any(host == h or host.endswith("." + h) for h in _PF7_MIRROR_HOSTS):
        return f"镜像前缀 {host}（CI 自动加镜像回退，手写即 R39 违规 579 例）"
    if any(host == h or host.endswith("." + h) for h in _PF7_DEBIAN_HOSTS) \
            or "+dfsg" in low:
        return "Debian 下游重打包源"
    return None


def check_source_urls(repo_dir: Path, files: list[str]) -> list[str]:
    """PF7 源 URL 闸（R39，v12.20）：只扫本 PR 变更的 conandata/manifest。

    conandata.yml 额外拦 gitcode/gitee 搬运源（上游官方确在此二平台的
    须 PR 说明登记后 --no-preflight 跳过）；manifest.yaml 不拦（可能含
    本仓/配方仓库链接）。
    """
    findings: list[str] = []
    for f in files:
        if not f.startswith("archives/"):
            continue
        if not f.endswith(("conandata.yml", "manifest.yaml")):
            continue
        pf = repo_dir / f
        if not pf.is_file():
            continue
        try:
            text = pf.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            urls: list[str] = []
            if re.search(r'url\s*:', line):
                urls = [m.group(1) for m in _PF7_VALUE.finditer(line)]
            else:
                m = _PF7_URL_ITEM.match(line)
                if m and ("//" in m.group(1) or m.group(1).startswith("/")):
                    urls = [m.group(1)]
            for u in urls:
                why = _pf7_classify(u)
                if not why and f.endswith("conandata.yml"):
                    m2 = re.match(r"https?://([^/]+)", u.lower())
                    if m2 and m2.group(1).endswith(
                            ("gitcode.com", "gitee.com")):
                        why = f"gitcode/gitee 搬运源 {m2.group(1)}"
                if why:
                    findings.append(
                        f"PF7 源URL闸(R39): {f}:{lineno} {why}——"
                        "conandata 只写上游官方源 URL，镜像回退由 CI 自动"
                        "处理；确属官方托管例外须 PR 说明并 --no-preflight 跳过")
                    break
    return findings


# ── PF3 扩面：test_package 结构闸（v12.20，L0c/L0e 前置）──────

_PF3_SRC_EXT = (".c", ".cpp", ".cc", ".cxx", ".sh", ".py")


def check_test_package_files(pkg_dir: Path) -> list[str]:
    """PF3 扩面：test_package 必须有测试源文件 + MANIFEST 齐全非空。

    口径与 CI L0c/L0e 对齐（语料：缺测试源 ~550、缺 MANIFEST 314 条）。
    test_package 目录不存在时不报（结构性缺失由 W2/L0 闸管辖）。
    """
    tp = pkg_dir / "test_package"
    if not tp.is_dir():
        return []
    findings: list[str] = []
    srcs = [p.name for p in tp.iterdir()
            if p.is_file() and p.suffix in _PF3_SRC_EXT
            and p.name != "conanfile.py"]
    if not srcs:
        findings.append(
            "PF3 测试闸: test_package/ 无测试源文件（.c/.cpp/.cc/.cxx/.sh/.py）"
            "——CI L0c 必拦；测试程序必须真实编译执行被测物 API")
    for man in (tp / "MANIFEST.yml", pkg_dir / "manifest.yaml"):
        if not man.is_file() or man.stat().st_size == 0:
            findings.append(
                f"PF3 测试闸: {man.name} 缺失或为空——CI L0e 必拦"
                "（六件套完整性）")
    return findings


# ── PF8 配方静态闸（v12.20，R38/L0p/L0m 前置）─────────────────

_PF8_CLI_TYPE = re.compile(r'package_type\s*=\s*["\']application["\']')
_PF8_BINDIRS = re.compile(r'bindirs\s*=\s*\[[^\]]*[^\s\]][^\]]*\]')
_PF8_SLUG = re.compile(r'^[a-z0-9][a-z0-9._+-]*$')


def _version_dirs(files: list[str]) -> set[str]:
    out: set[str] = set()
    for f in files:
        m = re.match(r"^archives/([a-z0-9])/([^/]+)/([^/]+)/", f)
        if m:
            out.add(m.group(3))
    return out


def check_recipe_static(repo_dir: Path, files: list[str]) -> list[str]:
    """PF8 配方静态闸（v12.20）：settings/slug/version/commands.json。

    全部为机械可判项（R38 705 条 + L0p 193 + L0m 族），历史存量不拦
    ——只查本 PR 变更的包目录。
    """
    dirs = sorted(_pkg_dirs(files))
    if len(dirs) != 1:
        return []                    # PF1 已拦多包；无包改动不适用
    pkg_dir = repo_dir / dirs[0]
    findings: list[str] = []
    vdirs = sorted(_version_dirs(files))
    texts: dict[str, str] = {}
    for vd in vdirs:
        cf = pkg_dir / vd / "conanfile.py"
        if cf.is_file():
            try:
                texts[vd] = cf.read_text(encoding="utf-8", errors="replace")
            except OSError:
                pass
    if not texts:
        return []                 # 无 conanfile 变更（纯 manifest/notes 等）
    for vd, text in texts.items():
        m = re.search(r"^\s*settings\s*=\s*(.+)$", text, re.M)
        if m:
            missing = [s for s in ("os", "arch", "compiler", "build_type")
                       if f'"{s}"' not in m.group(1) and f"'{s}'" not in m.group(1)]
            if missing:
                findings.append(
                    f"PF8 配方闸[{vd}]: settings 缺 {','.join(missing)}——"
                    "四项齐全是交叉编译矩阵前提（L0p 193 例）")
        mv = re.search(r'^\s*version\s*=\s*["\']([^"\']+)["\']', text, re.M)
        if mv and mv.group(1) != vd:
            findings.append(
                f"PF8 配方闸: conanfile version={mv.group(1)} 与版本目录 "
                f"{vd} 不一致——CI 找不到包（L0m/No packages 族）")
    if not _PF8_SLUG.match(pkg_dir.name):
        findings.append(
            f"PF8 配方闸: 包目录名 {pkg_dir.name} 不符 slug 规范"
            "（小写 [a-z0-9._+-]，L0m 口径）")
    is_cli = any(_PF8_CLI_TYPE.search(t) or _PF8_BINDIRS.search(t)
                 for t in texts.values())
    is_cli = bool(_PF8_CLI_TYPE.search(text) or _PF8_BINDIRS.search(text))
    cj = pkg_dir / "commands.json"
    if is_cli and not cj.is_file():
        findings.append(
            "PF8 配方闸: CLI 包（application/bindirs 非空）缺 commands.json"
            "——R38 必拦；参照 archives/a/abx/commands.json 补齐")
    if not is_cli and cj.is_file():
        findings.append(
            "PF8 配方闸: 纯库包不应有 commands.json（R38：库误加）")
    if cj.is_file():
        try:
            data = json.loads(cj.read_text(encoding="utf-8", errors="replace"))
        except (json.JSONDecodeError, OSError):
            findings.append("PF8 配方闸: commands.json 不是合法 JSON")
        else:
            if data.get("name") != pkg_dir.name:
                findings.append(
                    f'PF8 配方闸: commands.json name={data.get("name")!r}'
                    f" != 包名 {pkg_dir.name}")
            if data.get("type") != "tool":
                findings.append(
                    f'PF8 配方闸: commands.json type={data.get("type")!r}'
                    ' 必须为 "tool"')
            vers = data.get("versions")
            if not isinstance(vers, dict):
                findings.append(
                    "PF8 配方闸: commands.json versions 必须为对象"
                    '（{"<ver>": {"ref": "<name>/<ver>", ...}}）')
            else:
                for vd in vdirs:
                    if vd not in vers:
                        findings.append(
                            f"PF8 配方闸: commands.json 缺版本 {vd}")
                    elif vers[vd].get("ref") != f"{pkg_dir.name}/{vd}":
                        findings.append(
                            f"PF8 配方闸: commands.json versions[{vd}].ref "
                            f'须为 "{pkg_dir.name}/{vd}"')
    return findings


# ── PF9 分支/路径闸（v12.20，L0n/No-packages 前置）────────────

def check_branch_and_paths(repo_dir: Path, files: list[str]) -> list[str]:
    """PF9 分支/路径闸：变更须落在单一 包/版本 目录，分支名对齐包版本。

    L0n（~550 条）与 "No packages to build"（490 条）的提交前形态。
    仅当 PR 改动 archives/ 时生效；main/master/detached 豁免（编辑直推
    路径不经 create-pr，不适用本闸）。
    """
    arch = [f for f in files if f.startswith("archives/")]
    if not arch:
        return []
    findings: list[str] = []
    bad = [f for f in arch if len(f.split("/")) < 5]
    if bad:
        findings.append(
            "PF9 分支/路径闸: 变更路径缺版本目录层（须 "
            "archives/<字母>/<包>/<版本>/<文件>）——CI 将报 No packages to "
            f"build（490 例）: {', '.join(bad[:3])}")
        return findings
    r = subprocess.run(
        ["git", "-C", str(repo_dir), "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
        timeout=30)
    branch = (r.stdout or "").strip()
    if branch in ("main", "master", "HEAD", ""):
        return findings
    dirs = sorted(_pkg_dirs(files))
    if len(dirs) != 1:
        return findings            # PF1 处理多包
    pkg = dirs[0].split("/")[2]
    expected = set()
    for vd in _version_dirs(files):
        expected |= {f"{pkg}-{vd}", f"feat/{pkg}-{vd}", f"fix/{pkg}-{vd}"}
    if expected and branch not in expected:
        findings.append(
            f"PF9 分支/路径闸: 分支名 {branch!r} 与包版本不匹配（L0n ~550 例）"
            f"——应为 {' 或 '.join(sorted(expected))}")
    return findings


# ── R52 审计一致性交叉校验（v12.20）──────────────────────────

def check_audit_consistency(pkg_dir: Path, hard_findings: list[str]) -> list[str]:
    """R52 审计证据一致性：审计 pass 与硬闸命中矛盾 → 审计失真标记。

    语义：.audit-result.json verdict=pass 允许携带 P2/P3 警告，但本闸
    命中的都是 P0/P1 级问题——pass 结论与之矛盾即审计失真（#2204/#4237/
    #4321：审计文件可被伪造或自审走样），一票否决档。
    """
    if not hard_findings:
        return []
    ar = pkg_dir / ".audit-result.json"
    if not ar.is_file():
        return []
    try:
        data = json.loads(ar.read_text(encoding="utf-8", errors="replace"))
    except (json.JSONDecodeError, OSError):
        return []
    if data.get("verdict") == "pass":
        return [
            "R52 审计失真: .audit-result.json 判 pass 但 preflight 硬闸命中 "
            f"{len(hard_findings)} 项——自审文件必须由 W4 工具生成且结论附"
            "被检文件 sha256；本条为欺骗性一票否决档，修复后重跑 W4 审计"]
    return []


def run_preflight(repo_dir, base: str, head: str,
                  registry: str = DEFAULT_REGISTRY) -> tuple[bool, list[str]]:
    """执行 PF1-PF9 与 R52 交叉校验。返回 (通过?, 全部问题清单)。fail-closed。"""
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
    findings += check_branch_and_paths(repo_dir, files)
    findings += check_patch_platform_macro(repo_dir, files)
    findings += check_recipe_macro_injection(repo_dir, base, head, files)
    findings += check_recipe_shared_prefix(repo_dir, files)
    findings += check_source_urls(repo_dir, files)
    findings += check_recipe_static(repo_dir, files)
    dirs = sorted(_pkg_dirs(files))
    for d in dirs:                      # PF1 已保证最多 1 个
        pkg = repo_dir / d
        findings += check_test_substance(pkg)
        findings += check_test_package_files(pkg)
        findings += check_deps_in_registry(pkg, registry)
    # R52 交叉校验放最后：审计 pass 与硬闸命中矛盾 → 审计失真
    for d in dirs:
        findings += check_audit_consistency(repo_dir / d, list(findings))
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
        log_ok("preflight PF1-PF9+R52 全部通过")
    sys.exit(0 if ok else 1)
