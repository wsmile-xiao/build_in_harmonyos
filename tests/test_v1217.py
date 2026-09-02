# -*- coding: utf-8 -*-
"""v12.17 心愿单报告 0902 测试：S1 pr_url 回执 + S2 回读自检 + S3 停止自行预算判定"""
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta
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


def run_cli(argv, env):
    return subprocess.run(
        [sys.executable, "-X", "utf8", str(REPO / "scripts" / "ohc-run.py")] + argv,
        capture_output=True, text=True, env=env, cwd=str(REPO), timeout=120)


def mk_task(tmp, name, started_minutes_ago=None):
    proj = tmp / name
    ver_dir = proj / "archives" / "t" / "tsw" / "1.0"
    ver_dir.mkdir(parents=True)
    proj.joinpath("SKILL.md").write_text("# stub", encoding="utf-8")
    if started_minutes_ago is not None:
        fb = proj / ".ohc" / "feedback-state" / "t" / "tsw"
        fb.mkdir(parents=True)
        ts = (datetime.now() - timedelta(minutes=started_minutes_ago)) \
            .isoformat(timespec="seconds")
        fb.joinpath("1.0.json").write_text(json.dumps(
            {"software": "tsw", "version": "1.0",
             "events": [{"ts": ts, "event": "task_started", "detail": "init"}]},
            ensure_ascii=False), encoding="utf-8")
    return proj, ver_dir


def main():
    tmp = Path(tempfile.mkdtemp(prefix="v1217_"))
    for k in ("OHC_TASK_DEADLINE", "OHC_TASK_BUDGET_SEC",
              "OHPCD_BUDGET_MINUTES", "OHC_RESULT_OUT", "OHC_PROJECT_DIR"):
        os.environ.pop(k, None)

    # ── S3: 停止自行预算判定（心愿单 6 例 budget 自裁修复）──
    from ohc.budget import budget_status, get_budget_minutes
    proj_old, _ = mk_task(tmp, "t_old", 245)          # 4h05 前起点
    s = budget_status("tsw", "1.0", proj_old)
    check("S3a 无平台 env → 恒 ok（旧起点不再自裁）",
          not s["exhausted"] and not s["near_limit"]
          and s["budget_source"] == "none", s)
    os.environ["OHPCD_BUDGET_MINUTES"] = "30"          # 自造 env 不再生效
    s = budget_status("tsw", "1.0", proj_old)
    check("S3b OHPCD_BUDGET_MINUTES 自造 env 已退役",
          not s["exhausted"], s)
    os.environ.pop("OHPCD_BUDGET_MINUTES")
    check("S3c get_budget_minutes 无 env → None", get_budget_minutes() is None)
    os.environ["OHC_TASK_BUDGET_SEC"] = "14400"        # 240min 平台口径
    s = budget_status("tsw", "1.0", proj_old)
    check("S3d BUDGET_SEC 存在时恢复判定（245min > 240 → 耗尽）",
          s["exhausted"] and s["budget_source"] == "budget_sec", s)
    os.environ.pop("OHC_TASK_BUDGET_SEC")
    os.environ["OHC_TASK_DEADLINE"] = \
        (datetime.now().astimezone() - timedelta(minutes=1)).isoformat()
    s = budget_status("tsw", "1.0", proj_old)
    check("S3e DEADLINE 优先仍生效", s["exhausted"]
          and s["budget_source"] == "deadline")
    os.environ.pop("OHC_TASK_DEADLINE")

    # ── S1: CI 绿自动 success 回执必带 pr_url（208 例空回执修复）──
    # S1a: 无 OHC_RESULT_OUT 时 _maybe_upgrade_result 也落盘（$HOME fallback）
    # 模拟 submit 主流程已存 .submit-state.json（branch_name/commit_hash）
    fake_home = tmp / "fakehome"
    fake_home.mkdir()
    proj1, ver_dir1 = mk_task(tmp, "t_ci")
    ver_dir1.joinpath(".submit-state.json").write_text(json.dumps({
        "pr_number": 42, "branch_name": "feat/tsw-1.0",
        "commit_hash": "abc1234", "review_phase": 1}), encoding="utf-8")
    os.environ["HOME"] = str(fake_home)
    os.environ["USERPROFILE"] = str(fake_home)
    os.environ["OHC_PROJECT_DIR"] = str(proj1)
    os.environ.pop("OHC_RESULT_OUT", None)
    from ohc.submission import _maybe_upgrade_result
    _maybe_upgrade_result("tsw", "1.0", 42,
                          "https://gitcode.com/x/y/-/merge_requests/42")
    f = fake_home / "ohpcd-ai-worker-result.json"
    check("S1a 无 OHC_RESULT_OUT 也落盘（HOME fallback）", f.exists())
    if f.exists():
        d = json.loads(f.read_text(encoding="utf-8"))
        check("S1b status=success + 显式 pr_url 落盘",
              d.get("status") == "success" and "merge_requests/42" in str(d.get("pr_url")),
              (d.get("status"), d.get("pr_url")))
    os.environ.pop("HOME"); os.environ.pop("USERPROFILE")

    # S1c: 草稿也显式带 pr_url（write_lifecycle_draft 新参）
    from ohc.result_report import write_lifecycle_draft
    out = tmp / "out1"
    os.environ["OHC_RESULT_OUT"] = str(out)
    ok = write_lifecycle_draft("tsw", "1.0", "pr_created", pr_number=99,
                               summary="x",
                               pr_url="https://gitcode.com/x/y/-/merge_requests/99")
    d = json.loads((out / "result.json").read_text(encoding="utf-8"))
    check("S1c 草稿 payload 含 pr_url", ok and d.get("draft") is True
          and "merge_requests/99" in str(d.get("pr_url")), d.get("pr_url"))

    # S1d: submission 六个草稿挂点全部传 pr_url（源码级）
    src = (REPO / "scripts" / "ohc" / "submission.py").read_text(encoding="utf-8")
    check("S1d 六挂点 pr_url=pr_url", src.count("pr_url=pr_url") >= 6,
          src.count("pr_url=pr_url"))
    check("S1e _maybe_upgrade_result 显式 --pr-url",
          '"--pr-url", pr_url' in src)
    check("S1f OHC_RESULT_OUT 硬依赖已移除",
          'if not os.environ.get("OHC_RESULT_OUT"' not in src)

    # ── S2: 写后回读自检 ──
    check("S2a result_cli 含回读校验",
          "写后回读自检" in (REPO / "scripts" / "ohc" / "result_report.py")
          .read_text(encoding="utf-8"))
    env = os.environ.copy()
    env["OHC_PROJECT_DIR"] = str(proj1); env["OHC_RESULT_OUT"] = str(tmp / "out2")
    r = run_cli(["result", "tsw", "1.0", "--status", "failed_build",
                 "--failed-reason", "S2 正常写路径不受回读影响", "--force"], env)
    d2 = json.loads((tmp / "out2" / "result.json").read_text(encoding="utf-8"))
    # v12.13 起协议枚举规范化: failed_build → build_failed
    check("S2b 正常写路径 rc=0 且可解析", r.returncode == 0
          and d2.get("status") == "build_failed", (r.returncode, d2.get("status")))

    print(f"\n=== {PASS} passed, {FAIL} failed ===")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
