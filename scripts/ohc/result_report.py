"""RESULT — 任务终态 result.json 上报（SKILL_RESULT_PROTOCOL_SPEC）。

每个任务到达终态（无论成败）必须产出 result.json，作为全链路唯一可信结果。
本模块是唯一合法生成器：禁止手写 JSON、禁止直接改字段绕过校验。

Usage:
    python3 ohc-run.py result <software> <version> --status <status> [options]

输出位置（优先级）:
    --out <path>  >  环境变量 OHC_RESULT_OUT  >  不落盘（仅 stdout 输出 JSON）

CLI 参数 → JSON 字段映射（字段名与 ECS 消费端严格对齐，改名=ECS 读不到）:
    --pr-number/--pr-url/--commit-hash/--branch → 同名字段（success 必填）
    --failed-reason  → error_detail        （ECS 失败分支优先取此字段）
    --missing        → missing_dependencies（ECS main.py 从此读依赖缺口）
    --missing-evidence → missing_evidence  （二次验证证据）
    --summary        → summary
    非 success 自动带 error_type = status

exit code: 0 = result.json 有效；2 = 无效（未落盘，输出 HANDOFF 块）
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from .utils import find_project_dir, get_agent_id, log_fail, log_info, log_ok

RESULT_FILENAME = "result.json"
# result.json 输出位置环境变量（--out 未指定时生效；两者都未设置则不落盘仅 stdout）
RESULT_OUT_ENV = "OHC_RESULT_OUT"
REPO_NAME = "OpenHarmonyPCDeveloper/build_in_harmonyos"

STATUS_ENUM = (
    "success", "failed_build", "failed_test", "dependency_missing",
    "env_unsupported", "upstream_issue", "user_cancelled", "partial",
)

# 长度红线（协议 §2）
MAX_PKG = 100
MAX_VER = 32
MAX_AGENT = 16
MAX_REASON = 500
MAX_MSG = 200
MAX_MISSING_PER_DEP = 5

_GIT = "git"


def _archive_ver_dir(software: str, version: str,
                     pdir: str | None = None) -> Path:
    letter = software[0].lower() if software else "_"
    return (Path(pdir or find_project_dir())
            / "archives" / letter / software / version)


def _git_output(args: list[str], cwd: Path | None = None) -> str:
    try:
        r = subprocess.run([_GIT] + args, capture_output=True, text=True,
                           cwd=str(cwd) if cwd else None, timeout=15)
        return r.stdout.strip() if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        return ""


def _gh_pr(cwd: Path | None = None) -> tuple[int | None, str | None]:
    """S3: 从 gh CLI 取当前分支的 PR number/url（未认证/未安装时返回 None）。"""
    try:
        r = subprocess.run(
            ["gh", "pr", "view", "--json", "number,url"],
            capture_output=True, text=True,
            cwd=str(cwd) if cwd else None, timeout=15)
        if r.returncode == 0:
            d = json.loads(r.stdout)
            n = d.get("number")
            return (int(n), d.get("url")) if n else (None, None)
    except (OSError, ValueError, subprocess.SubprocessError, json.JSONDecodeError):
        pass
    return (None, None)


def _load_submit_state(ver_dir: Path) -> dict:
    p = ver_dir / ".submit-state.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _search_evidence_in_logs(project_dir: Path, pkg_names: list[str]) -> list[str]:
    """协议红线：依赖缺失声明前必须在日志中二次验证。
    自动在 .ci_logs/ 日志中搜索每个包名出现行（附加佐证，不替代显式证据）。"""
    hits: list[str] = []
    root = project_dir / ".ci_logs"
    if not root.is_dir():
        return [f"{p}: (no log evidence found in .ci_logs/)" for p in pkg_names]
    log_files = list(root.rglob("*.log"))[:200]  # 界定扫描规模
    for pkg in pkg_names:
        found = False
        for log_file in log_files:
            try:
                text = log_file.read_text(encoding="utf-8",
                                          errors="replace")
            except OSError:
                continue
            for line in text.splitlines():
                if pkg in line:
                    hits.append(f"{pkg}: {line.strip()[:MAX_MSG]}")
                    found = True
                    break
            if found:
                break
        if not found:
            hits.append(f"{pkg}: (no log evidence found in .ci_logs/)")
    return hits


def _validate(result: dict) -> list[str]:
    """按协议逐条校验，返回错误清单（空 = 通过）。"""
    errors: list[str] = []

    # 基础字段长度
    if not result.get("pkg"):
        errors.append("pkg 不能为空")
    if len(result.get("pkg", "")) > MAX_PKG:
        errors.append(f"pkg 长度 > {MAX_PKG}")
    if len(result.get("ver", "")) > MAX_VER:
        errors.append(f"ver 长度 > {MAX_VER}")
    if len(result.get("agent", "")) > MAX_AGENT:
        errors.append(f"agent 长度 > {MAX_AGENT}")

    # status 枚举
    status = result.get("status")
    if status not in STATUS_ENUM:
        errors.append(f"status 非法: {status}（合法值: {', '.join(STATUS_ENUM)}）")

    # ts ISO8601
    if not re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", str(result.get("ts", ""))):
        errors.append("ts 必须是 ISO8601 格式")

    # success 必填字段
    if status == "success":
        for field in ("pr_url", "pr_number", "commit_hash", "branch"):
            if not result.get(field):
                errors.append(f"status=success 时 {field} 必填")

    # dependency_missing 必填 missing_dependencies + missing_evidence
    if status == "dependency_missing":
        missing = result.get("missing_dependencies")
        if not isinstance(missing, list) or not missing:
            errors.append("status=dependency_missing 时 missing_dependencies（裸包名数组）必填")
        else:
            for item in missing:
                if not item or "/" in item:
                    errors.append(f"missing_dependencies 必须是裸包名（不带版本）: {item}")
            if len(missing) > 20:
                errors.append("missing_dependencies 数量异常（>20），请人工复核")
        if not result.get("missing_evidence"):
            errors.append("status=dependency_missing 时 missing_evidence（二次验证证据）必填")
    else:
        if result.get("missing_dependencies"):
            errors.append("仅 status=dependency_missing 允许携带 missing_dependencies")

    # 非 success：error_type 必填且与 status 一致；error_detail 必填（≤500）
    if status != "success":
        if result.get("error_type") != status:
            errors.append(f"非 success 时 error_type 必填且等于 status（当前: {result.get('error_type')}）")
        if not result.get("error_detail"):
            errors.append(f"非 success 时 error_detail 必填")
    if len(result.get("error_detail", "") or "") > MAX_REASON:
        errors.append(f"error_detail 长度 > {MAX_REASON}")

    # summary 长度（可选字段）
    if len(result.get("summary", "") or "") > MAX_REASON:
        errors.append(f"summary 长度 > {MAX_REASON}")

    # checkpoints：最后一条必须是 _ohpcd_result 且 message=cat result.json
    cps = result.get("checkpoints", [])
    if not isinstance(cps, list) or not cps:
        errors.append("checkpoints 不能为空")
    else:
        for i, cp in enumerate(cps):
            msg = str(cp.get("message", ""))
            if len(msg) > MAX_MSG:
                errors.append(f"checkpoints[{i}].message 长度 > {MAX_MSG}")
        last = cps[-1]
        if last.get("message") != RESULT_FILENAME:
            errors.append(f"checkpoints 最后一条必须是 message='{RESULT_FILENAME}' 的 _ohpcd_result")

    return errors


def _emit_handoff(software: str, version: str, errors: list[str],
                  hint: str = "", out: str | None = None) -> None:
    """校验失败时输出标准 HANDOFF 交接块（references/handoff-protocol.md）。

    EXIT_CODE=2（resumable）：修正参数后重跑 result 命令即可，无需回退到更早 step。
    """
    out_arg = f" --out {out}" if out else ""
    print()
    print("╔═══ HANDOFF ══════════════════════════════════╗")
    print("║ EXIT_REASON: result_invalid                  ║")
    print("║ EXIT_CODE: 2 (resumable)                     ║")
    print("║ STEP_FAILED: Step7                           ║")
    print(f"║ PKG: {software}/{version}")
    print("║ RESUME_CMD: python3 $SKILL_ROOT/scripts/ohc-run.py result "
          f"{software} {version} --status <status>{out_arg} [修正后参数]")
    print("║ AI NEXT ACTIONS:                             ║")
    print("║   1. 修复以下校验错误:")
    for e in errors[:5]:
        print(f"║      - {e[:60]}")
    if len(errors) > 5:
        print(f"║      ... 共 {len(errors)} 条错误")
    if hint:
        print(f"║   2. {hint}")
    print("║   3. 重新运行 RESUME_CMD（result.json 未落盘，无残留）")
    print("╚══════════════════════════════════════════════╝")


def result_cli(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="result",
        description="任务终态 result.json 上报（SKILL_RESULT_PROTOCOL_SPEC）")
    parser.add_argument("software")
    parser.add_argument("version")
    parser.add_argument("--status", required=True, choices=STATUS_ENUM)
    parser.add_argument("--pr-number", type=int, default=None)
    parser.add_argument("--pr-url", default=None)
    parser.add_argument("--commit-hash", default=None)
    parser.add_argument("--branch", default=None)
    parser.add_argument("--failed-reason", default=None,
                        help="失败/取消原因（≤500 字符，必填于失败类状态；落到 JSON error_detail）")
    parser.add_argument("--missing", default=None,
                        help="逗号分隔的缺失依赖裸包名列表（仅 dependency_missing；"
                             "落到 JSON missing_dependencies 数组）")
    parser.add_argument("--missing-evidence", default=None,
                        help="依赖缺失二次验证证据：日志行或命令输出（落到 JSON missing_evidence）")
    parser.add_argument("--summary", default=None,
                        help="一句话结果摘要（强烈建议填写，≤500 字符；落到 JSON summary）")
    parser.add_argument("--checkpoint", action="append", default=None,
                        metavar="MSG", help="关键节点 message（可多次）")
    parser.add_argument("--agent", default=None)
    parser.add_argument("--out", "-o", default=None, metavar="PATH",
                        help="result.json 输出位置（目录或完整文件路径）。"
                             "result.json 是跨设备/AI 结果交换文件，不属于 PR 提交内容。"
                             "优先级: --out > 环境变量 OHC_RESULT_OUT > 不落盘（仅 stdout 输出）")
    parser.add_argument("--force", action="store_true",
                        help="允许覆盖已存在的 result.json")
    args = parser.parse_args(argv)

    project_dir = Path(find_project_dir())

    # ── 输出位置：--out 参数 > 环境变量 OHC_RESULT_OUT > 不落盘（仅 stdout） ──
    # result.json 用于与其他设备/AI 交换任务结果，不写入 archives/（不是 PR 提交内容）
    out_target = args.out or os.environ.get(RESULT_OUT_ENV, "").strip() or None
    out_path: Path | None = None
    if out_target:
        out_path = Path(out_target).expanduser()
        # 目录判定：已存在的目录，或无扩展名的路径（如 /shared/results/）→ 目录模式
        if out_path.is_dir() or not out_path.suffix:
            out_path = out_path / RESULT_FILENAME

    if out_path is not None and out_path.exists() and not args.force:
        log_fail(f"{out_path} 已存在；如需重报请加 --force")
        _emit_handoff(args.software, args.version,
                      [f"result.json 已存在: {out_path}"],
                      hint="确认终态已变化后加 --force 覆盖重报",
                      out=out_target)
        return 2

    # ── 自动补齐（archives 目录存在时才读取 .submit-state.json） ──
    # pr_number 来源链: --pr-number > .submit-state.json > gh pr view（未认证则跳过）
    # S3: 全部缺失时 success 校验失败 exit 2（fail-fast），
    #     杜绝"缺 PR 字段的 success"流入 ECS 触发 SUCCESS_NO_PR 降级
    ver_dir = _archive_ver_dir(args.software, args.version, str(project_dir))
    state = _load_submit_state(ver_dir) if ver_dir.is_dir() else {}
    pr_number = args.pr_number or state.get("pr_number")
    pr_url = args.pr_url
    if not pr_number:
        gh_num, gh_url = _gh_pr(cwd=project_dir)
        pr_number, pr_url = gh_num, gh_url or pr_url
    branch = args.branch or state.get("branch_name") \
        or _git_output(["rev-parse", "--abbrev-ref", "HEAD"], cwd=project_dir)
    commit_hash = args.commit_hash \
        or _git_output(["rev-parse", "HEAD"], cwd=project_dir)
    pr_url = pr_url or (
        f"https://gitcode.com/{REPO_NAME}/pull/{pr_number}"
        if pr_number else None)
    agent = args.agent or get_agent_id()

    # ── checkpoints ──
    checkpoints = [{"ts": datetime.now(timezone.utc).isoformat(),
                    "message": m} for m in (args.checkpoint or [])]
    if not checkpoints:
        checkpoints.append({"ts": datetime.now(timezone.utc).isoformat(),
                            "message": f"status={args.status}"})

    missing_list: list[str] = []
    if args.missing:
        missing_list = [m.strip() for m in args.missing.split(",") if m.strip()]

    # ── 协议红线：dependency_missing 必须显式提供二次验证证据 ──
    # （自动搜索的日志行仅作附加佐证，不能替代显式证据）
    if args.status == "dependency_missing" and not args.missing_evidence:
        log_fail("--missing-evidence 对 status=dependency_missing 必填："
                 "提供实际日志行或命令输出（禁止仅凭推断声明依赖缺失）")
        _emit_handoff(args.software, args.version,
                      ["dependency_missing 缺少二次验证证据 --missing-evidence"],
                      hint="证据=实际命令输出或日志行（如 conan download 的 404 报错）",
                      out=out_target)
        return 2

    evidence_parts: list[str] = []
    if args.missing_evidence:
        evidence_parts.append(args.missing_evidence)
    if missing_list:
        evidence_parts.extend(
            _search_evidence_in_logs(project_dir, missing_list))
    evidence = "\n".join(evidence_parts) if evidence_parts else None

    # 失败类状态必须有 failed_reason（协议：terminal state 必须给出非空说明）
    failed_reason = args.failed_reason
    if failed_reason is None and args.status not in ("success",):
        log_fail("--failed-reason 对非 success 终态必填（≤500 字符）")
        _emit_handoff(args.software, args.version,
                      ["非 success 终态缺少 --failed-reason（≤500 字符）"],
                      out=out_target)
        return 2

    result = {
        "schema": "1.0",
        "pkg": args.software,
        "ver": args.version,
        "status": args.status,
        "agent": agent,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    if args.summary:
        result["summary"] = args.summary
    if pr_number:
        result["pr_number"] = pr_number
    if pr_url:
        result["pr_url"] = pr_url
    if commit_hash:
        result["commit_hash"] = commit_hash
    if branch:
        result["branch"] = branch
    # 非 success: --failed-reason 落 error_detail（ECS 失败分支优先取此字段）
    if args.status != "success":
        result["error_type"] = args.status
        result["error_detail"] = failed_reason
    if missing_list:
        # --missing 展开为 missing_dependencies 数组（ECS main.py 从此字段读取）
        result["missing_dependencies"] = missing_list
    if evidence:
        result["missing_evidence"] = evidence
    # 协议 §5：最后一条 checkpoint 为 _ohpcd_result，message 固定为 result.json
    checkpoints.append({"ts": datetime.now(timezone.utc).isoformat(),
                        "message": RESULT_FILENAME})
    result["checkpoints"] = checkpoints

    # ── 校验（红线：不过不落盘） ──
    errors = _validate(result)
    if errors:
        for e in errors:
            log_fail(f"result.json 校验失败: {e}")
        log_info("未落盘。请修正参数后重试（协议: 禁止手写 JSON 绕过校验）")
        _emit_handoff(args.software, args.version, errors, out=out_target)
        return 2

    result_text = json.dumps(result, ensure_ascii=False, indent=2)
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(result_text, encoding="utf-8")
        # 协议红线：退出前自动 cat result.json
        log_ok(f"result.json 已生成: {out_path}")
    else:
        log_info("未指定输出位置（--out / OHC_RESULT_OUT 均未设置），"
                 "仅输出到 stdout，不落盘")
    print(result_text)
    return 0
