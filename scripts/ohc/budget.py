# -*- coding: utf-8 -*-
"""预算感知收尾（SKILL 优化反馈 0831 P0-1，76 例 4h 耗尽上报 unknown）。

问题：agent 跑满平台 4h 硬顶被 SIGKILL——result.json 停在 draft:true 草稿
（平台视为非终态）或根本没写 → 归一化为 unknown，成果不可见、不可续跑。

三件套（分工边界：预算上限/硬杀在平台侧；SKILL 侧负责"预算内主动收尾"）：
  1. budget-check 命令——agent 在每个长阶段（W3 编译/CI 监控/重试循环）前调用：
       ok          exit 0   继续当前工作
       near_limit  exit 0   剩余 < 40min（R41）：停止提交新编译，收尾写 checkpoint
       exhausted   exit 3   预算已耗尽：本工具自动写终态 timeout result
                            （含已完成里程碑摘要 + 续跑命令），agent 应立即停止
  2. write_lifecycle_draft 内嵌兜底——每个 R46 里程碑写草稿前自动检查，
     超预算即升级为终态 timeout（即使 agent 忘调 budget-check 也有兜底）
  3. timeout 终态内容——status=timeout（协议 §4.5 枚举），error_detail 带
     已完成 checkpoint_steps + 续跑命令（reset-rerun / submit --resume），
     平台按 retry_context 续跑而非重新从头

预算来源：OHPCD_BUDGET_MINUTES env（平台注入）> 默认 240（4h 硬顶）。
任务起点：feedback 时间线首事件 ts（init-archive 即写入）；缺失时回退
result.json 草稿 mtime。
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from .utils import find_project_dir, log_fail, log_info, log_ok, log_warn

DEFAULT_BUDGET_MINUTES = 240  # 平台 4h 硬顶（反馈 0831: 76 例跑满被杀）
SAFETY_MARGIN_MINUTES = 40    # R41: 剩余 < 40min 停止提交新编译

RESUME_HINT = ("续跑: python3 scripts/ohc-run.py finish {sw} {ver} --resume "
               "（已登记的 checkpoints 不丢）或 reset-rerun 重开")


def get_budget_minutes() -> int:
    raw = os.environ.get("OHPCD_BUDGET_MINUTES", "").strip()
    try:
        v = int(raw)
        if v > 0:
            return v
    except ValueError:
        pass
    return DEFAULT_BUDGET_MINUTES


def _ver_dir(software: str, version: str, project_dir=None) -> Path | None:
    pdir = Path(project_dir) if project_dir else Path(find_project_dir())
    ver_dir = pdir / "archives" / (software[0].lower() if software else "_") \
        / software / version
    return ver_dir if ver_dir.is_dir() else None


def _task_started_at(ver_dir: Path) -> datetime | None:
    """任务起点 = feedback 时间线中**最后一条** task_started 事件 ts。

    取最后一条而非第一条：reset-rerun/重试场景旧时间线不清零，init-archive
    会写入新的 task_started——以最新起点计时，防止重跑任务被旧时间线误判
    为预算耗尽（v12.15 测试中实际踩到的跨任务污染）。
    不做 result.json mtime 回退——该文件可能是上一任务残留。
    """
    try:
        from .feedback import _load_feedback_state
        events = (_load_feedback_state(ver_dir) or {}).get("events") or []
    except Exception:
        return None
    last = None
    for ev in events:
        if str(ev.get("event", "")) != "task_started":
            continue
        ts = str(ev.get("ts", ""))
        if not ts:
            continue
        try:
            t = datetime.fromisoformat(ts)
        except ValueError:
            continue
        if last is None or t > last:
            last = t
    return last


def _milestones(ver_dir: Path) -> list[str]:
    """已完成里程碑（R46 草稿 checkpoint 摘要，供 timeout 上报保成果）。"""
    try:
        from .feedback import _load_feedback_state
        events = (_load_feedback_state(ver_dir) or {}).get("events") or []
        seen, out = set(), []
        for ev in events:
            name = str(ev.get("event", ""))
            if name and name not in seen and not name.startswith("handoff"):
                seen.add(name)
                out.append(name)
        return out[-12:]
    except Exception:
        return []


def budget_status(software: str, version: str, project_dir=None) -> dict:
    st = {"started": None, "elapsed_min": 0.0, "budget_min": get_budget_minutes(),
          "remaining_min": None, "exhausted": False, "near_limit": False,
          "milestones": []}
    ver_dir = _ver_dir(software, version, project_dir)
    if ver_dir is None:
        st["note"] = "ver_dir 不存在（任务未 init）——按 ok 处理"
        return st
    st["milestones"] = _milestones(ver_dir)
    started = _task_started_at(ver_dir)
    if started is None:
        st["note"] = "无任务起点记录——按 ok 处理"
        return st
    st["started"] = started.isoformat(timespec="seconds")
    elapsed = (datetime.now() - started).total_seconds() / 60.0
    st["elapsed_min"] = round(elapsed, 1)
    st["remaining_min"] = round(st["budget_min"] - elapsed, 1)
    st["exhausted"] = st["remaining_min"] <= 0
    st["near_limit"] = 0 < st["remaining_min"] <= SAFETY_MARGIN_MINUTES
    return st


def write_timeout_result(software: str, version: str,
                         status: dict | None = None,
                         project_dir=None) -> int:
    """写终态 timeout（协议 §4.5）：保成果 + 续跑命令，供平台 retry_context。"""
    st = status or budget_status(software, version, project_dir)
    ms = st.get("milestones") or []
    ms_text = "、".join(ms) if ms else "无（早期耗尽）"
    reason = (f"预算耗尽（{st.get('budget_min')}min 上限，已用 "
              f"{st.get('elapsed_min')}min）——非任务失败。已完成里程碑: {ms_text}。"
              f"{RESUME_HINT.format(sw=software, ver=version)}")
    from .result_report import result_cli
    rc = result_cli([software, version, "--status", "timeout",
                     "--failed-reason", reason, "--force"])
    if rc == 0:
        log_ok("已写终态 timeout（含里程碑摘要 + 续跑命令）")
    else:
        log_fail(f"timeout 终态写入失败 rc={rc}")
    return rc


def budget_check_cli(argv=None) -> int:
    import argparse
    import json as _json
    parser = argparse.ArgumentParser(
        prog="budget-check",
        description="反馈 0831 P0-1: 预算检查（长阶段前调用；耗尽自动写 timeout 终态）")
    parser.add_argument("software")
    parser.add_argument("version")
    parser.add_argument("--project-dir", default=None)
    args = parser.parse_args(argv)

    st = budget_status(args.software, args.version, args.project_dir)
    print(_json.dumps(st, ensure_ascii=False, indent=2))

    if st.get("exhausted"):
        log_fail(f"⏱ 预算已耗尽（剩余 {st.get('remaining_min')}min）——立即收尾")
        rc = write_timeout_result(args.software, args.version, st,
                                  args.project_dir)
        return 3 if rc == 0 else rc
    if st.get("near_limit"):
        log_warn(f"⏱ 剩余 {st.get('remaining_min')}min ≤ {SAFETY_MARGIN_MINUTES}min"
                 f"（R41）——停止提交新编译/新 PR，优先收尾: 写 checkpoint + 必要时"
                 f" result --status partial（loop_pending 由 submit 处理）")
        return 0
    log_ok(f"预算充足（剩余 {st.get('remaining_min')}min / {st.get('budget_min')}min）")
    return 0


if __name__ == "__main__":
    raise SystemExit(budget_check_cli())
