#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""dep_binary_probe.py — 依赖二进制可用性预检（依赖断链诊断）

为什么需要它
------------
Conan 制品仓里「配方存在」不等于「二进制存在」。仓里存在大量
"配方已合并、release 流水线未跑过" 的包，其表现是：

  * ``conan list`` / 制品仓检索会说「有」——搜到的是*配方*不是*二进制*；
  * 只有 ``conan install`` 才会暴露 ``Missing binary: <ref>:<package_id>``；
  * 更隐蔽的是 ``--build=missing`` 源码兜底往往同样不通：兜底要先从源码构建
    工具链（如 cmake），而该工具在制品仓同样没有可用二进制，于是编译在很深
    的位置失败，几十分钟后才暴露真正原因（见 examples/wev-1.1.0）。

本工具把上述判定收敛为一次廉价探测，输出三态结论 + 可直接复用的证据串，
使「依赖未发布」在动手适配之前就被拦下（对齐铁律 R35 探测方式、R36 发布顺序）。

用法示例
--------
    python3 dep_binary_probe.py \\
        --requires wayland/1.24.0 wayland-protocols/1.47 \\
        --profile-host ci/conan/profiles/ohos-aarch64 \\
        --profile-build ci/conan/profiles/ohos-aarch64 \\
        --remote-name ohpcd \\
        --remote-url https://conan.cnb.cool/OpenHarmonyPCDeveloper/Conan/-/packages/ \\
        --check-fallback --json

判定状态
--------
===============  ==========================================================
BINARY_OK        制品仓有可用二进制，可继续适配
RECIPE_ONLY      配方在仓、二进制缺失（最隐蔽：检索界面显示「存在」）
RECIPE_MISSING   配方都没有（依赖尚未适配）
REMOTE_ERROR     远端/通道故障（按 R41 重试；不可据此判定依赖缺失）
UNKNOWN          输出无法归类，附原始片段供人工判读
ENV_ERROR        工具/环境错误（conan 不可执行、无可写临时目录等）——本次结论无效
BUILD_TOOL_GAP   --check-fallback 命中：兜底工具链自身无二进制，
                 源码兜底（--build=missing）不可行
===============  ==========================================================

退出码
------
0  全部 BINARY_OK（可以继续）
2  存在缺失/工具缺口（先发布依赖，或按 dependency_missing 止损上报）
3  工具或环境错误（conan 不可用、无法建立隔离 home 等）
"""

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

VERSION = "1.0.0"

# ---------------------------------------------------------------- 状态常量
BINARY_OK = "BINARY_OK"
RECIPE_ONLY = "RECIPE_ONLY"
RECIPE_MISSING = "RECIPE_MISSING"
REMOTE_ERROR = "REMOTE_ERROR"
UNKNOWN = "UNKNOWN"
ENV_ERROR = "ENV_ERROR"
BUILD_TOOL_GAP = "BUILD_TOOL_GAP"

EXIT_OK = 0
EXIT_BLOCKED = 2
EXIT_TOOL_ERROR = 3

# 判定优先级：RECIPE_MISSING(配方都没有) > RECIPE_ONLY(配方在、二进制缺) >
#             REMOTE_ERROR(通道故障) > BINARY_OK(rc=0) > UNKNOWN
_MISSING_BINARY_RE = re.compile(r"Missing\s+(?:binary|prebuilt package)[^\n]*", re.I)
_PACKAGE_ID_RE = re.compile(r"Missing binary:\s*[^:\s]+:[0-9a-f]{20,}", re.I)
_RECIPE_MISSING_RES = (
    re.compile(r"Unable to find package[^\n]*", re.I),
    # 实测形态（conan 2.29 / ohpcd）：
    # ERROR: Package 'dssi/1.0.0' not resolved: Unable to find 'dssi/1.0.0' in remotes.
    re.compile(r"Unable to find '[^']+' in remotes[^\n]*", re.I),
    re.compile(r"not resolved:[^\n]*Unable to find[^\n]*", re.I),
    # 版本区间无候选：cmake/[>=3.18] -> "Version range '>=3.18' ... could not be resolved"
    re.compile(r"[^\n]*could not be resolved[^\n]*", re.I),
    re.compile(r"Recipe not found[^\n]*", re.I),
    re.compile(r"ERROR: Package '[^']+' not found[^\n]*", re.I),
    re.compile(r"no such recipe[^\n]*", re.I),
)
_REMOTE_ERROR_RES = (
    re.compile(r"remote not available[^\n]*", re.I),
    re.compile(r"Connection\s*(?:Error|reset|refused)[^\n]*", re.I),
    re.compile(r"SSLError|SSL certificate|TLS[^\n]*", re.I),
    re.compile(r"timed?\s*out[^\n]*", re.I),
    re.compile(r"Temporary failure in name resolution[^\n]*", re.I),
    re.compile(r"unreachable[^\n]*", re.I),
    re.compile(r"\b5\d\d\b[^\n]*Server Error[^\n]*", re.I),
    # cnb.cool 制品仓检索接口未开通时的固定报错：属通道限制而非依赖缺失
    re.compile(r"system acceleration policy not enabled[^\n]*", re.I),
)

# conanfile.py 中直接依赖的启发式提取（仅取字面量，不做图求解）
_REQ_CALL_RE = re.compile(
    r"""(?:self\.)?(requires|tool_requires|build_requires)\s*\(\s*["']([^"']+)["']""",
    re.I,
)
_REQ_ASSIGN_RE = re.compile(r"""^\s*(requires|tool_requires)\s*=\s*["']([^"']+)["']""", re.M)


# ---------------------------------------------------------------- 数据结构
class ProbeResult(object):
    """单个依赖的探测结论。"""

    def __init__(self, ref, status, evidence="", package_id="", detail=""):
        self.ref = ref
        self.status = status
        self.evidence = evidence
        self.package_id = package_id
        self.detail = detail

    def as_dict(self):
        return {
            "ref": self.ref,
            "status": self.status,
            "package_id": self.package_id,
            "evidence": self.evidence,
            "detail": self.detail,
        }


# ---------------------------------------------------------------- 纯函数（离线可测）
def _clip(text, limit=280):
    text = re.sub(r"\s+", " ", (text or "").strip())
    return text[:limit]


def classify_output(rc, text):
    """把 conan 子进程输出归类为三态之一。

    返回 ``(status, package_id, evidence)``。纯函数，便于离线单测。
    """
    text = text or ""
    package_id = ""
    m = _PACKAGE_ID_RE.search(text)
    if m:
        package_id = m.group(0).split(":")[-1]

    m = _MISSING_BINARY_RE.search(text)
    if m:
        return RECIPE_ONLY, package_id, _clip(m.group(0))

    for rx in _RECIPE_MISSING_RES:
        m = rx.search(text)
        if m:
            return RECIPE_MISSING, package_id, _clip(m.group(0))

    if rc == 127:
        lines = [ln for ln in text.splitlines() if ln.strip()]
        return ENV_ERROR, package_id, _clip(lines[-1] if lines else "conan 不可执行")

    if rc == 0:
        return BINARY_OK, package_id, "conan install rc=0（二进制可解析）"

    for rx in _REMOTE_ERROR_RES:
        m = rx.search(text)
        if m:
            return REMOTE_ERROR, package_id, _clip(m.group(0))

    last_err = ""
    for line in reversed([ln for ln in text.splitlines() if ln.strip()]):
        last_err = line
        break
    return UNKNOWN, package_id, _clip(last_err)


def extract_requires(conanfile_text):
    """从 conanfile.py 文本中提取直接依赖（启发式，不求解依赖图）。

    仅识别字面量 ``self.requires("name/ver")`` / ``self.tool_requires(...)`` /
    ``requires = "name/ver"``；条件分支内的依赖全部收入（宁多勿漏），
    版本表达式（如 ``cmake/[>=3.18]``）原样返回，由调用方确认可用版本。
    """
    text = conanfile_text or ""
    hits = []
    for rx in (_REQ_CALL_RE, _REQ_ASSIGN_RE):
        for match in rx.finditer(text):
            hits.append((match.start(), match.group(2).strip()))
    refs = [ref for _pos, ref in sorted(hits)]
    seen, out = set(), []
    for ref in refs:
        if ref and ref not in seen:
            seen.add(ref)
            out.append(ref)
    return out


def summarize(results, tool_gaps=None, env_error=None):
    """汇总探测结论，给出 verdict 与可执行建议。"""
    tool_gaps = list(tool_gaps or [])
    missing, recipe_missing, remote_errors, unknown = [], [], [], []
    for r in results:
        if r.status == RECIPE_ONLY:
            missing.append(r.ref)
        elif r.status == RECIPE_MISSING:
            recipe_missing.append(r.ref)
        elif r.status == REMOTE_ERROR:
            remote_errors.append(r.ref)
        elif r.status == UNKNOWN:
            unknown.append(r.ref)

    if env_error:
        verdict = "ENV_ERROR"
    elif tool_gaps:
        verdict = "BLOCKED"
    elif missing or recipe_missing:
        verdict = "BLOCKED"
    elif remote_errors or unknown:
        verdict = "NEEDS_REVIEW"
    else:
        verdict = "OK"

    return {
        "verdict": verdict,
        "binary_missing": missing,
        "recipe_missing": recipe_missing,
        "remote_errors": remote_errors,
        "unknown": unknown,
        "build_tool_gaps": tool_gaps,
        "env_error": env_error or "",
    }


def build_evidence(results, tool_gaps=None, conan_ref_prefix="conan install --requires="):
    """生成可直接塞进 ``ohc-run.py result --missing-evidence`` 的一行证据。"""
    parts = []
    for r in results:
        if r.status in (RECIPE_ONLY, RECIPE_MISSING):
            parts.append("%s%s -> %s" % (conan_ref_prefix, r.ref, r.evidence or r.status))
    for tool in tool_gaps or []:
        parts.append("tool_requires %s 无可用二进制 -> --build=missing 兜底不可行" % tool)
    return _clip(" ; ".join(parts), 900)


def suggested_result_command(package, version, summary, skill_root="$SKILL_ROOT"):
    """生成止损上报命令（dependency_missing），供直接复制执行。"""
    bare = sorted(set([_bare_name(r) for r in summary["binary_missing"] + summary["recipe_missing"]]))
    evidence = summary.get("evidence", "")
    cmd = [
        "python3 %s/scripts/ohc-run.py result %s %s" % (skill_root, package, version),
        "--status dependency_missing",
        '--missing "%s"' % ",".join(bare),
        '--missing-evidence "%s"' % evidence.replace('"', "'"),
    ]
    if summary.get("build_tool_gaps"):
        cmd.append('--failed-reason "依赖二进制未发布且源码兜底工具链缺失：%s"' % ",".join(summary["build_tool_gaps"]))
    else:
        cmd.append('--failed-reason "依赖未发布到制品仓（配方在仓但二进制缺失）"')
    return " ".join(cmd)


def _bare_name(ref):
    return ref.split("/")[0].split("[")[0].strip()


# ---------------------------------------------------------------- 环境准备
def resolve_work_root():
    """挑选可写的临时根目录（鸿蒙 PC 上 ``/tmp`` 常为只读）。

    顺序：``$OHC_TMPDIR`` > ``$TMPDIR`` > 系统默认 > ``$HOME/.cache/dep-binary-probe``。
    每一级都实际试写，试写失败即降级——避免把只读 ``/tmp`` 当成可用目录。
    """
    candidates = []
    for key in ("OHC_TMPDIR", "TMPDIR"):
        val = os.environ.get(key)
        if val:
            candidates.append(val)
    candidates.append(tempfile.gettempdir())
    candidates.append(os.path.join(os.path.expanduser("~"), ".cache", "dep-binary-probe"))

    for cand in candidates:
        try:
            probe_dir = os.path.join(cand, "dep-binary-probe")
            os.makedirs(probe_dir, exist_ok=True)
            probe_file = os.path.join(probe_dir, ".write-test")
            with open(probe_file, "w") as fh:
                fh.write("ok")
            os.unlink(probe_file)
            return cand
        except Exception:
            continue
    raise RuntimeError("找不到可写临时目录（已尝试 $OHC_TMPDIR/$TMPDIR/%s/$HOME/.cache）" % tempfile.gettempdir())


def conan_env(conan_home, extra=None):
    """构造干净的 conan 运行环境（不继承调用方的 CONAN_HOME/CONAN_USER_HOME）。"""
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", "/root"),
        "CONAN_HOME": conan_home,
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
    }
    for key in ("SSL_CERT_FILE", "REQUESTS_CA_BUNDLE", "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY"):
        if os.environ.get(key):
            env[key] = os.environ[key]
    if extra:
        env.update(extra)
    return env


def run_cmd(cmd, env, timeout):
    """执行外部命令，返回 ``(rc, 合并输出)``。"""
    try:
        proc = subprocess.run(
            cmd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
        return proc.returncode, proc.stdout.decode("utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        return 124, "TIMEOUT: %s 超过 %ss 未返回" % (" ".join(cmd), timeout)
    except OSError as exc:
        return 127, "OSError: %s (%s)" % (exc, " ".join(cmd))


def conan_cmd(ctx):
    """conan 命令前缀（首段解析为绝对路径）。

    支持 ``--conan conan`` 这样的裸命令，也支持 ``--conan "python3 shim.py"``
    这类带参数的写法（本项目离线测试即依赖后者注入 stub）。

    ⚠ 鸿蒙 HMDFS 上权限位与实际可执行性不一致：``-rwxrwx---`` 的文件由 shell
    或 ``shutil.which`` 能找到，但子进程用**裸名**经 PATH 查找会失败
    （``OSError: [Errno 2] No such file or directory``），而直接执行绝对路径
    正常。因此这里统一解析成绝对路径再交给 subprocess。
    """
    parts = shlex.split(ctx.conan) or ["conan"]
    resolved = shutil.which(parts[0]) or (parts[0] if os.path.isfile(parts[0]) else None)
    if resolved:
        parts[0] = resolved
    return parts


def discover_source_home(ctx):
    """用**调用方原样环境**询问 conan 自身的 home，作为隔离 home 的模板来源。

    必须刻意保留调用方的 CONAN_HOME/环境：若此时注入刚要建的空隔离 home，
    conan 会回报这个空目录本身，settings.yml/global.conf 无从继承，后续所有
    探测都会因缺少 settings 而失败（本工具在 1.0.0 实现期间踩过此坑）。
    """
    rc, out = run_cmd(conan_cmd(ctx) + ["config", "home"], os.environ.copy(), 60)
    if rc == 0 and out.strip():
        return out.strip().splitlines()[-1].strip()
    return ""


def make_isolated_home(ctx, work_root):
    """建立隔离 CONAN_HOME 并注册远端，返回 (home, env, notes)。

    隔离是判定可信的前提：本地缓存里已存在的二进制会让探测得到假 OK，
    使「同一依赖在 A 机器可用、在 CI 不可用」这种结论漂移无法被发现。
    """
    notes = []
    home = tempfile.mkdtemp(prefix="conan-home-", dir=os.path.join(work_root, "dep-binary-probe"))
    src_home = getattr(ctx, "source_home", "") or discover_source_home(ctx)
    if src_home and os.path.isdir(src_home):
        for fname in ("settings.yml", "global.conf", "remotes.json"):
            src = os.path.join(src_home, fname)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(home, fname))
        notes.append("已从 %s 复制 settings.yml/global.conf/remotes.json" % src_home)
    else:
        notes.append(
            "警告：未能定位源 CONAN_HOME（%s），隔离 home 可能缺少 settings.yml"
            % (src_home or "conan config home 无输出")
        )

    env = conan_env(home)
    if ctx.remote_url:
        rc, out = run_cmd(
            conan_cmd(ctx) + ["remote", "add", "--force", ctx.remote_name, ctx.remote_url], env, 60
        )
        if rc != 0:
            notes.append("警告：注册远端失败：%s" % _clip(out, 160))
        else:
            notes.append("已注册远端 %s" % ctx.remote_name)
    return home, env, notes


def _profile_args(ctx, role):
    path = ctx.profile_host if role == "h" else ctx.profile_build
    if not path:
        return []
    return ["-pr:%s=%s" % (role, path)]


def probe_ref(ref, ctx, work_root, env, timeout=None):
    """探测单个引用的二进制可用性。"""
    timeout = timeout or ctx.timeout
    work = tempfile.mkdtemp(prefix="probe-", dir=os.path.join(work_root, "dep-binary-probe"))
    cmd = conan_cmd(ctx) + ["install", "--requires=%s" % ref, "--output-folder=%s" % work]
    cmd += _profile_args(ctx, "h") + _profile_args(ctx, "b")
    if ctx.remote_name:
        cmd += ["-r", ctx.remote_name]
    rc, out = run_cmd(cmd, env, timeout)
    status, package_id, evidence = classify_output(rc, out)
    detail = "" if status == BINARY_OK else _clip(out, 600)
    return ProbeResult(ref, status, evidence, package_id, detail)


def parse_json_payload(text):
    """从可能混有日志的 conan 输出中提取 JSON 对象。

    本工具合并了 stderr，而 profile 回显里的 ``{'c': '/path'}'`` 这类日志也含花括号，
    因此不能简单取第一个 ``{``。做法：候选起点 = 输出开头 + 每个以 ``{`` 开头的行，
    用 ``raw_decode`` 解析（容忍尾部混入的日志行），第一个成功的即为结果。
    """
    text = (text or "").strip()
    if not text:
        return None, "输出为空"

    candidates = [text]
    offset = 0
    for raw_line in text.splitlines(True):
        stripped = raw_line.lstrip()
        if stripped.startswith("{"):
            # 必须按行偏移切片：conan 的 JSON 首行是裸的 "{"
            # （pretty-print），用 text.find("{") 会命中日志行里的花括号
            # （如 compiler_executables={'c': ...}）导致解析错位。
            candidates.append(text[offset + (len(raw_line) - len(stripped)):])
        offset += len(raw_line)

    decoder = json.JSONDecoder()
    last_err = ""
    for cand in candidates:
        try:
            data, _ = decoder.raw_decode(cand)
            return data, ""
        except ValueError as exc:
            last_err = str(exc)
    return None, last_err


def check_fallback(ref, ctx, env, probed, work_root):
    """判断 ``--build=missing`` 源码兜底是否可行。

    做法：用 ``conan graph info --build=missing`` 求出会走源码构建的节点，
    再逐个探测其二进制可用性；构建上下文（context=build）的工具若没有二进制，
    兜底路径同样断裂 —— 此时应立即止损，而不是等几十分钟后的深层编译错误。
    """
    cmd = conan_cmd(ctx) + ["graph", "info", "--requires=%s" % ref, "--build=missing", "--format=json"]
    cmd += _profile_args(ctx, "h") + _profile_args(ctx, "b")
    if ctx.remote_name:
        cmd += ["-r", ctx.remote_name]
    rc, out = run_cmd(cmd, env, ctx.timeout)

    data, err = parse_json_payload(out)
    if data is None:
        if rc != 0:
            return [], "graph info 失败：%s" % _clip(out, 200)
        return [], "graph info 输出非 JSON：%s" % err

    nodes = (data.get("graph") or {}).get("nodes") or {}
    candidates = []
    for node in nodes.values():
        node_ref = node.get("ref") or ""
        if not node_ref or node_ref == ref or node.get("context") != "build":
            continue
        if node.get("binary") == "Download" or node.get("binary") == "Cache":
            continue
        if node_ref in probed or node_ref in candidates:
            continue
        candidates.append(node_ref)

    gaps, notes = [], []
    for cand in candidates[: ctx.max_probes]:
        res = probe_ref(cand, ctx, work_root, env)
        probed.add(cand)
        notes.append("%s -> %s" % (cand, res.status))
        if res.status in (RECIPE_ONLY, RECIPE_MISSING):
            gaps.append(cand)
    if len(candidates) > ctx.max_probes:
        notes.append("（其余 %d 个构建依赖未探测，受 --max-probes 限制）" % (len(candidates) - ctx.max_probes))
    return gaps, "; ".join(notes)


# ---------------------------------------------------------------- 输出
_STATUS_LABEL = {
    BINARY_OK: "可用",
    RECIPE_ONLY: "配方在仓、二进制缺失",
    RECIPE_MISSING: "配方缺失（未适配）",
    REMOTE_ERROR: "远端故障（需重试）",
    UNKNOWN: "无法归类（需人工判读）",
    BUILD_TOOL_GAP: "兜底工具链无二进制",
}


def render_human(payload, notes):
    lines = []
    lines.append("=" * 78)
    lines.append("依赖二进制可用性预检  dep-binary-probe v%s" % VERSION)
    lines.append("=" * 78)
    lines.append("隔离 CONAN_HOME : %s" % payload["conan_home"])
    lines.append("远端            : %s" % (payload["remote"] or "(默认)"))
    lines.append("profile         : host=%s build=%s" % (payload["profile"]["host"] or "-", payload["profile"]["build"] or "-"))
    lines.append("-" * 78)
    for item in payload["results"]:
        lines.append("[%-14s] %-38s %s" % (item["status"], item["ref"], _STATUS_LABEL.get(item["status"], "")))
        if item["evidence"]:
            lines.append("                  └─ %s" % item["evidence"])
    if payload["build_tool_gaps"]:
        lines.append("-" * 78)
        lines.append("源码兜底（--build=missing）不可行，缺失工具链：")
        for tool in payload["build_tool_gaps"]:
            lines.append("  * %s" % tool)
    lines.append("-" * 78)
    lines.append("verdict: %s" % payload["verdict"])
    if payload["summary"]["binary_missing"]:
        lines.append("  二进制缺失：%s" % ", ".join(payload["summary"]["binary_missing"]))
    if payload["summary"]["recipe_missing"]:
        lines.append("  配方缺失  ：%s" % ", ".join(payload["summary"]["recipe_missing"]))
    if payload["evidence"]:
        lines.append("证据串    ：%s" % payload["evidence"])
    if payload["suggested_result_command"]:
        lines.append("止损命令  ：%s" % payload["suggested_result_command"])
    if notes:
        lines.append("-" * 78)
        for note in notes:
            lines.append("· %s" % note)
    lines.append("=" * 78)
    return "\n".join(lines)


# ---------------------------------------------------------------- CLI
def build_parser():
    p = argparse.ArgumentParser(
        prog="dep-binary-probe",
        description="依赖二进制可用性预检：区分「配方在仓」与「二进制在仓」，并判断源码兜底是否可行。",
    )
    p.add_argument("--requires", nargs="+", default=[], help="要探测的依赖，形如 name/version（可多个）")
    p.add_argument("--from-conanfile", help="从 conanfile.py 提取直接依赖（启发式）")
    p.add_argument("--package", help="当前适配的包名（用于生成止损命令）")
    p.add_argument("--version", dest="pkg_version", help="当前适配的包版本（用于生成止损命令）")
    p.add_argument("--conan", default=os.environ.get("OHC_CONAN", "conan"), help="conan 可执行文件（默认取 PATH 中的 conan）")
    p.add_argument("--profile-host", default=os.environ.get("OHC_PROFILE_HOST"), help="host profile 路径（-pr:h）")
    p.add_argument("--profile-build", default=os.environ.get("OHC_PROFILE_BUILD"), help="build profile 路径（-pr:b）")
    p.add_argument("--remote-name", default="ohpcd", help="远端名（默认 ohpcd）")
    p.add_argument("--remote-url", default="", help="远端地址；给定则写入隔离 home")
    p.add_argument("--timeout", type=int, default=300, help="单次探测超时秒数（默认 300）")
    p.add_argument("--check-fallback", action="store_true", help="额外判断 --build=missing 源码兜底是否可行")
    p.add_argument("--max-probes", type=int, default=6, help="兜底探测时最多再探多少个构建依赖（默认 6）")
    p.add_argument("--no-isolate", action="store_true", help="使用当前 CONAN_HOME（会受本地缓存影响，不推荐）")
    p.add_argument("--source-conan-home", default="", help="隔离 home 的模板来源（默认由 conan config home 询问）")
    p.add_argument("--json", action="store_true", help="仅输出 JSON")
    p.add_argument("--out", help="JSON 落盘路径")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    notes = []

    refs = list(args.requires)
    if args.from_conanfile:
        try:
            with open(args.from_conanfile, "r", encoding="utf-8") as fh:
                refs += extract_requires(fh.read())
        except IOError as exc:
            print("无法读取 conanfile：%s" % exc, file=sys.stderr)
            return EXIT_TOOL_ERROR
    seen, ordered = set(), []
    for ref in refs:
        if ref not in seen:
            seen.add(ref)
            ordered.append(ref)
    if not ordered:
        print("未指定任何依赖：请用 --requires 或 --from-conanfile", file=sys.stderr)
        return EXIT_TOOL_ERROR

    class Ctx(object):
        pass

    ctx = Ctx()
    ctx.conan = args.conan
    ctx.remote_name = args.remote_name
    ctx.remote_url = args.remote_url
    ctx.profile_host = args.profile_host
    ctx.profile_build = args.profile_build
    ctx.timeout = args.timeout
    ctx.max_probes = args.max_probes
    ctx.source_home = args.source_conan_home

    conan_exe = conan_cmd(ctx)[0]
    if not (shutil.which(conan_exe) or os.path.isfile(conan_exe)):
        print(
            "找不到 conan 可执行文件（%s）：请用 --conan 指定绝对路径" % conan_exe,
            file=sys.stderr,
        )
        return EXIT_TOOL_ERROR

    try:
        work_root = resolve_work_root()
    except RuntimeError as exc:
        print("环境错误：%s" % exc, file=sys.stderr)
        return EXIT_TOOL_ERROR

    if args.no_isolate:
        home = os.environ.get("CONAN_HOME", "")
        env = conan_env(home) if home else os.environ.copy()
        notes.append("警告：--no-isolate 使用当前 CONAN_HOME，本地缓存可能造成假阳性")
    else:
        home, env, home_notes = make_isolated_home(ctx, work_root)
        notes.extend(home_notes)

    results = []
    for ref in ordered:
        res = probe_ref(ref, ctx, work_root, env)
        results.append(res)
        if not args.json:
            print("· 探测 %-38s -> %s" % (ref, res.status), file=sys.stderr)

    probed = set(ordered)
    tool_gaps, fallback_note = [], ""
    if args.check_fallback:
        for res in list(results):
            gaps, note = check_fallback(res.ref, ctx, env, probed, work_root)
            if note:
                fallback_note = "%s: %s" % (res.ref, note) if not fallback_note else fallback_note
            tool_gaps.extend([g for g in gaps if g not in tool_gaps])
        if fallback_note:
            notes.append("兜底探测：%s" % fallback_note)

    env_error = ""
    for res in results:
        if res.status == ENV_ERROR:
            env_error = "%s: %s" % (res.ref, res.evidence)
            break

    summary = summarize(results, tool_gaps, env_error=env_error)
    summary["evidence"] = build_evidence(results, tool_gaps)
    payload = {
        "tool": "dep-binary-probe",
        "version": VERSION,
        "conan_home": home,
        "remote": args.remote_name,
        "profile": {"host": args.profile_host or "", "build": args.profile_build or ""},
        "results": [r.as_dict() for r in results],
        "summary": summary,
        "verdict": summary["verdict"],
        "build_tool_gaps": tool_gaps,
        "evidence": summary["evidence"],
        "suggested_result_command": "",
        "notes": notes,
    }
    if summary["verdict"] == "BLOCKED" and args.package and args.pkg_version:
        payload["suggested_result_command"] = suggested_result_command(
            args.package, args.pkg_version, summary
        )

    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, ensure_ascii=False, indent=2)

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(render_human(payload, notes))

    if summary["verdict"] in ("BLOCKED",):
        return EXIT_BLOCKED
    if summary["verdict"] in ("NEEDS_REVIEW", "ENV_ERROR"):
        return EXIT_TOOL_ERROR
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
