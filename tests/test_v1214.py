# -*- coding: utf-8 -*-
"""v12.14 平台反馈 0829 测试：CI 修复循环 + pr_url 规范 + loop_pending 信号"""
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
    from ohc.submission import (_ci_repair_round, _ci_repair_reset,
                                MAX_CI_REPAIR_ROUNDS, CI_REPAIR_STATE)

    tmp = Path(tempfile.mkdtemp(prefix="v1214_"))
    proj = tmp / "proj"
    ver_dir = proj / "archives" / "t" / "tsw" / "1.0"
    ver_dir.mkdir(parents=True)
    proj.joinpath("SKILL.md").write_text("# stub", encoding="utf-8")

    # ── F-1: 修复轮次计数 ──
    r1 = _ci_repair_round(ver_dir, 123)
    r2 = _ci_repair_round(ver_dir, 123)
    check("F1a 轮次递增 1→2", (r1, r2) == (1, 2), (r1, r2))
    state = json.loads((ver_dir / CI_REPAIR_STATE).read_text(encoding="utf-8"))
    check("F1b 状态持久化", state.get("rounds") == 2 and state.get("last_pr_number") == 123,
          state)

    # ── F-2: 停损阈值 ──
    check("F2a 停损阈值=2", MAX_CI_REPAIR_ROUNDS == 2)
    # 模拟第 2 轮后 reset 再来一轮 → 应重新从 1 计
    _ci_repair_reset(ver_dir)
    check("F2b reset 清零", not (ver_dir / CI_REPAIR_STATE).exists())
    r3 = _ci_repair_round(ver_dir, 123)
    check("F2c reset 后重新计数", r3 == 1, r3)
    # reset 对不存在文件不炸
    _ci_repair_reset(ver_dir)
    check("F2d reset 幂等", True)

    # ── F-3: pr_url 规范 /merge_requests/（源码层）──
    src = (REPO / "scripts" / "ohc" / "submission.py").read_text(encoding="utf-8")
    src2 = (REPO / "scripts" / "ohc" / "result_report.py").read_text(encoding="utf-8")
    check("F3a submission.py 无 /pull/ 残留", "/pull/" not in src)
    check("F3b result_report.py 无 /pull/ 残留", "/pull/" not in src2)
    check("F3c submission.py 用 /merge_requests/",
          src.count("/merge_requests/") == 2, src.count("/merge_requests/"))
    check("F3d result_report.py 用 /merge_requests/",
          "/merge_requests/" in src2)

    # ── F-4: result 上报 pr_url 走 merge_requests 格式（端到端）──
    os.environ["OHC_PROJECT_DIR"] = str(proj)
    os.environ["OHC_RESULT_OUT"] = str(tmp / "out")
    # 模拟 .submit-state.json（_maybe_upgrade 的数据源同族）
    (ver_dir / ".submit-state.json").write_text(
        json.dumps({"pr_number": 42, "branch_name": "feat/tsw-1.0.0"}), encoding="utf-8")
    # 写终态 failed 带 pr 字段自动补齐（走 _attach_pr_meta 补 pr_url）
    from ohc.result_report import result_cli
    rc = result_cli(["tsw", "1.0", "--status", "build_failed",
                     "--failed-reason", "F4 pr_url 检查", "--force"])
    out = json.loads((tmp / "out" / "result.json").read_text(encoding="utf-8"))
    check("F4a 上报成功", rc == 0, rc)
    pr_url = out.get("pr_url") or ""
    check("F4b pr_url 为 /merge_requests/ 格式", "/merge_requests/42" in pr_url, pr_url)

    # ── F-5: HANDOFF acts 指引正确性（源码层静态断言）──
    check("F5a 无『CI 自动重跑』错误指引残留", "CI 自动重跑" not in src)
    check("F5b 含 push 不触发 CI 警示", "push 本身不会触发 CI" in src)
    check("F5c 含停损上报指引", "停损" in src and "build_failed" in src)
    check("F5d loop_pending 写入 CI 失败分支", src.count('loop_pending') >= 4,
          src.count("loop_pending"))

    print(f"\n=== {PASS} passed, {FAIL} failed ===")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
