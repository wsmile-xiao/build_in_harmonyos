# -*- coding: utf-8 -*-
"""v12.12 loop_pending 信号专项测试"""
import json
import os
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


def main():
    from ohc.result_report import write_lifecycle_draft
    from ohc.feedback import record_event, _load_feedback_state

    tmp = Path(tempfile.mkdtemp(prefix="v1212_"))
    proj = tmp / "proj"
    ver_dir = proj / "archives" / "t" / "tsw" / "1.0"
    ver_dir.mkdir(parents=True)
    proj.joinpath("SKILL.md").write_text("# stub", encoding="utf-8")

    out = tmp / "out"
    old = os.environ.get("OHC_RESULT_OUT")
    oldp = os.environ.get("OHC_PROJECT_DIR")
    os.environ["OHC_RESULT_OUT"] = str(out)
    os.environ["OHC_PROJECT_DIR"] = str(proj)
    try:
        # no-wait 路径同构调用：loop_pending + resume 命令
        resume_cmd = (f"python3 scripts/ohc-run.py submit tsw 1.0 --resume")
        ok = write_lifecycle_draft(
            "tsw", "1.0", "loop_pending", pr_number=42,
            summary=(f"PR #42 已创建但 CI/AI 闭环未启动（no-wait 退出）。"
                     f"follow-up 续环: {resume_cmd}"))
        f = out / "result.json"
        d = json.loads(f.read_text(encoding="utf-8"))
        check("L1 loop_pending 草稿落盘", ok and f.exists())
        check("L2 draft:true + milestone=loop_pending",
              d.get("draft") is True and d.get("milestone") == "loop_pending")
        check("L3 summary 含 resume 命令", "--resume" in d.get("summary", ""))
        check("L4 带 PR 字段", d.get("pr_number") == 42 and d.get("pr_url"))

        # feedback 事件
        record_event(ver_dir, "loop_pending",
                     "no-wait 退出，CI/AI 闭环未启动；follow-up: "
                     "submit --resume (PR #42)")
        st = _load_feedback_state(ver_dir)
        evs = st.get("events", [])
        check("L5 feedback 事件记录",
              any(e.get("event") == "loop_pending" for e in evs), str(evs)[-120:])
    finally:
        for k, v in (("OHC_RESULT_OUT", old), ("OHC_PROJECT_DIR", oldp)):
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    print(f"\n=== {PASS} passed, {FAIL} failed ===")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
