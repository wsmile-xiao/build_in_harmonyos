# -*- coding: utf-8 -*-
"""v12.15/16/17 反馈 0831 + 心愿单 0902 测试：预算三件套 + budget_exhausted + registry 重试
v12.17 S3 语义：仅平台 env（OHC_TASK_DEADLINE/OHC_TASK_BUDGET_SEC）存在时判定。"""
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


def mk_task(tmp, name, started_minutes_ago, events_extra=()):
    proj = tmp / name
    ver_dir = proj / "archives" / "t" / "tsw" / "1.0"
    ver_dir.mkdir(parents=True)
    proj.joinpath("SKILL.md").write_text("# stub", encoding="utf-8")
    fb = proj / ".ohc" / "feedback-state" / "t" / "tsw"
    fb.mkdir(parents=True)
    ts = (datetime.now() - timedelta(minutes=started_minutes_ago)) \
        .isoformat(timespec="seconds")
    events = [{"ts": ts, "event": "task_started", "detail": "init"}]
    for ev, dt in events_extra:
        events.append({"ts": ts, "event": ev, "detail": dt})
    fb.joinpath("1.0.json").write_text(
        json.dumps({"software": "tsw", "version": "1.0", "events": events},
                   ensure_ascii=False), encoding="utf-8")
    return proj, ver_dir


def run_cli(argv, env):
    return subprocess.run(
        [sys.executable, "-X", "utf8", str(REPO / "scripts" / "ohc-run.py")] + argv,
        capture_output=True, text=True, env=env, cwd=str(REPO), timeout=120)


def main():
    tmp = Path(tempfile.mkdtemp(prefix="v1215_"))
    for k in ("OHC_TASK_DEADLINE", "OHC_TASK_BUDGET_SEC",
              "OHPCD_BUDGET_MINUTES"):
        os.environ.pop(k, None)

    from ohc.budget import budget_status, write_budget_exhausted_result, \
        get_budget_minutes, ERROR_CODE

    proj1, _ = mk_task(tmp, "t_ok", 60)                       # 1h 前 → ok
    proj2, _ = mk_task(tmp, "t_near", 200)                    # 3h20 前 → near
    proj3, _ = mk_task(tmp, "t_dead", 245,
                       [("recipe_generated", "x"), ("conan_verify_passed", "y"),
                        ("lang_checked", "z")])              # 4h05 前 → exhausted

    # ── B-1: BUDGET_SEC 平台口径下的三态（S3: 无 env 恒 ok 见 v1217 套件）──
    os.environ["OHC_TASK_BUDGET_SEC"] = "14400"               # 240min
    s1 = budget_status("tsw", "1.0", proj1)
    s2 = budget_status("tsw", "1.0", proj2)
    s3 = budget_status("tsw", "1.0", proj3)
    check("B1a 1h 前 ok", not s1["exhausted"] and not s1["near_limit"], s1)
    check("B1b 3h20 前 near_limit", s2["near_limit"] and not s2["exhausted"],
          (s2.get("remaining_min"),))
    check("B1c 4h05 前 exhausted", s3["exhausted"], s3.get("remaining_min"))
    check("B1d 里程碑提取",
          "recipe_generated" in s3["milestones"]
          and "conon_verify_passed" in s3["milestones"] or
          "conan_verify_passed" in s3["milestones"], s3["milestones"])

    # ── B-2: OHPCD_BUDGET_MINUTES 已退役（S3: 停止自行判定）──
    os.environ.pop("OHC_TASK_BUDGET_SEC", None)
    os.environ["OHPCD_BUDGET_MINUTES"] = "30"
    s = budget_status("tsw", "1.0", proj1)   # 1h 前起点 + 自造 30min → 不判定
    check("B2a 自造 env 不再生效（恒 ok）", not s["exhausted"]
          and s["budget_source"] == "none", s)
    check("B2b get_budget_minutes 自造 env → None", get_budget_minutes() is None)
    os.environ["OHC_TASK_BUDGET_SEC"] = "1800"                # 平台 30min
    check("B2c BUDGET_SEC 秒转分", get_budget_minutes() == 30)
    s = budget_status("tsw", "1.0", proj1)                    # 1h > 30min → 耗尽
    check("B2d 平台 30min 生效（1h 前 → 耗尽）", s["exhausted"]
          and s["budget_source"] == "budget_sec", s)
    os.environ.pop("OHC_TASK_BUDGET_SEC")
    os.environ.pop("OHPCD_BUDGET_MINUTES")
    # OHC_TASK_DEADLINE 绝对时刻（最准，覆盖起点计时）
    os.environ["OHC_TASK_DEADLINE"] = \
        (datetime.now().astimezone() + timedelta(minutes=10)).isoformat()
    s = budget_status("tsw", "1.0", proj1)                    # 距 deadline 10min
    check("B2e deadline 优先（剩余≈10min → near_limit）",
          s["budget_source"] == "deadline" and s["near_limit"]
          and not s["exhausted"], (s.get("budget_source"), s.get("remaining_min")))
    os.environ["OHC_TASK_DEADLINE"] = \
        (datetime.now().astimezone() - timedelta(minutes=1)).isoformat()
    s = budget_status("tsw", "1.0", proj3)
    check("B2f 已过期 deadline → exhausted", s["exhausted"]
          and s["budget_source"] == "deadline", s.get("remaining_min"))
    os.environ.pop("OHC_TASK_DEADLINE")

    # ── B-3: budget_exhausted 终态格式（平台 retry_context 对齐）──
    os.environ["OHC_TASK_BUDGET_SEC"] = "14400"
    out3 = tmp / "out3"
    os.environ["OHC_RESULT_OUT"] = str(out3)
    rc = write_budget_exhausted_result("tsw", "1.0", s3, proj3)
    d3 = json.loads((out3 / "result.json").read_text(encoding="utf-8"))
    check("B3a status=failed + draft:false", d3.get("status") == "failed"
          and d3.get("draft") is False, (d3.get("status"), d3.get("draft")))
    check("B3b error_code=budget_exhausted", d3.get("error_code") == "budget_exhausted")
    check("B3c error_type 同值（平台归一化读法）", d3.get("error_type") == "budget_exhausted")
    cps = d3.get("checkpoint_steps")
    check("B3d checkpoint_steps 结构化数组含里程碑",
          isinstance(cps, list) and "recipe_generated" in cps
          and "conan_verify_passed" in cps, cps)
    det = d3.get("error_detail", "")
    check("B3e error_detail 含续跑命令", "finish tsw 1.0 --resume" in det)

    # ── B-4: budget-check CLI 三态 ──
    env = os.environ.copy()
    env["OHC_PROJECT_DIR"] = str(proj1)
    env["OHC_RESULT_OUT"] = str(tmp / "out_ok")
    r = run_cli(["budget-check", "tsw", "1.0"], env)
    check("B4a ok exit 0", r.returncode == 0, r.returncode)
    env["OHC_PROJECT_DIR"] = str(proj2); env["OHC_RESULT_OUT"] = str(tmp / "out_near")
    r = run_cli(["budget-check", "tsw", "1.0"], env)
    check("B4b near_limit exit 0 + 收尾提示", r.returncode == 0
          and "收尾" in (r.stdout + r.stderr), "")
    env["OHC_PROJECT_DIR"] = str(proj3); env["OHC_RESULT_OUT"] = str(tmp / "out_cli3")
    r = run_cli(["budget-check", "tsw", "1.0"], env)
    dc = json.loads((tmp / "out_cli3" / "result.json").read_text(encoding="utf-8"))
    check("B4c exhausted exit 3 + budget_exhausted 终态", r.returncode == 3
          and dc.get("error_code") == "budget_exhausted"
          and dc.get("status") == "failed",
          (r.returncode, dc.get("status"), dc.get("error_code")))

    # ── B-5: write_lifecycle_draft 预算兜底 ──
    os.environ["OHC_PROJECT_DIR"] = str(proj3)
    os.environ["OHC_RESULT_OUT"] = str(tmp / "out5")
    from ohc.result_report import write_lifecycle_draft
    ok = write_lifecycle_draft("tsw", "1.0", "pr_created", pr_number=99,
                               summary="兜底测试")
    d5 = json.loads((tmp / "out5" / "result.json").read_text(encoding="utf-8"))
    check("B5a 超预算草稿被升级 budget_exhausted", not ok
          and d5.get("status") == "failed"
          and d5.get("error_code") == "budget_exhausted",
          (ok, d5.get("status"), d5.get("error_code")))
    os.environ["OHC_PROJECT_DIR"] = str(proj1)
    os.environ["OHC_RESULT_OUT"] = str(tmp / "out6")
    ok2 = write_lifecycle_draft("tsw", "1.0", "pr_created", pr_number=99,
                                summary="正常草稿")
    d6 = json.loads((tmp / "out6" / "result.json").read_text(encoding="utf-8"))
    check("B5b 正常草稿不受影响", ok2 and d6.get("draft") is True
          and d6.get("milestone") == "pr_created", (ok2, d6.get("milestone")))
    # S3: 平台 env 全撤 → 草稿兜底不再触发（恒 ok）
    os.environ["OHC_PROJECT_DIR"] = str(proj3)
    os.environ["OHC_RESULT_OUT"] = str(tmp / "out7")
    os.environ.pop("OHC_TASK_BUDGET_SEC", None)
    ok3 = write_lifecycle_draft("tsw", "1.0", "pr_created", pr_number=99,
                                summary="无平台 env 不自裁")
    d7 = json.loads((tmp / "out7" / "result.json").read_text(encoding="utf-8"))
    check("B5c 无平台 env 草稿正常（不自裁）", ok3 and d7.get("draft") is True,
          (ok3, d7.get("status")))

    # ── B-6: resume 刷新计时 ──
    proj7, _ = mk_task(tmp, "t_stale", 245)                   # 旧起点 4h05 前
    from ohc.feedback import record_event
    vd7 = proj7 / "archives" / "t" / "tsw" / "1.0"
    record_event(vd7, "task_started", "submit --resume 重启计时")
    os.environ["OHC_TASK_BUDGET_SEC"] = "14400"
    s7 = budget_status("tsw", "1.0", proj7)
    check("B6a resume 后新 task_started 生效（不再误判耗尽）",
          not s7["exhausted"], (s7.get("started"), s7.get("remaining_min")))
    os.environ.pop("OHC_TASK_BUDGET_SEC")

    # ── B-7: registry git 重试 ──
    from ohc import dependency_resolver as dr
    calls = {"n": 0}

    class FakeResult:
        def __init__(self, rc):
            self.returncode = rc
            self.stdout, self.stderr = "", "network glitch"

    def fake_run_git(cmd_args, cwd=None):
        calls["n"] += 1
        return FakeResult(0 if calls["n"] >= 3 else 1)

    orig = dr._run_git
    dr._run_git = fake_run_git
    try:
        res = dr._run_git_retry(["fetch", "origin"], attempts=3, backoff=(0, 0, 0))
        check("B7a 前两次失败第三次成功 → 0", res.returncode == 0
              and calls["n"] == 3, (res.returncode, calls["n"]))
        calls["n"] = 0

        def always_fail(cmd_args, cwd=None):
            calls["n"] += 1
            return FakeResult(1)
        dr._run_git = always_fail
        res = dr._run_git_retry(["fetch", "origin"], attempts=3, backoff=(0, 0, 0))
        check("B7b 三次全失败 → 非零 + 恰好 3 次", res.returncode != 0
              and calls["n"] == 3, (res.returncode, calls["n"]))
    finally:
        dr._run_git = orig
    src = (REPO / "scripts" / "ohc" / "dependency_resolver.py").read_text(encoding="utf-8")
    check("B7c fetch 走重试版", src.count("_run_git_retry") >= 3,
          src.count("_run_git_retry"))

    # ── B-8: 校验器豁免规则 ──
    envv = os.environ.copy()
    envv["OHC_PROJECT_DIR"] = str(proj1); envv["OHC_RESULT_OUT"] = str(tmp / "out8")
    for k in ("OHC_TASK_DEADLINE", "OHC_TASK_BUDGET_SEC", "OHPCD_BUDGET_MINUTES"):
        envv.pop(k, None)
    r = run_cli(["result", "tsw", "1.0", "--status", "failed",
                 "--error-code", "budget_exhausted",
                 "--failed-reason", "x", "--force"], envv)
    check("B8a 缺 checkpoint_steps 被拒", r.returncode != 0, r.returncode)
    r = run_cli(["result", "tsw", "1.0", "--status", "success",
                 "--error-code", "budget_exhausted",
                 "--checkpoint-steps", "task_started",
                 "--summary", "x"], envv)
    check("B8b success+error-code 被拒", r.returncode != 0, r.returncode)

    print(f"\n=== {PASS} passed, {FAIL} failed ===")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
