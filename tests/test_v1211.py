# -*- coding: utf-8 -*-
"""R46 v12.11 测试：生命周期草稿 / $HOME 兜底 / draft 标记 / 手写检测"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
PASS, FAIL = 0, 0


def check(name, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ok  {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name} {extra}")


def run_result(argv, env):
    r = subprocess.run(
        [sys.executable, "-X", "utf8", str(REPO / "scripts" / "ohc-run.py"), "result"] + argv,
        capture_output=True, text=True, env=env, cwd=str(REPO), timeout=120)
    return r


def make_env(tmp, use_env_var=None):
    env = os.environ.copy()
    env["OHC_PROJECT_DIR"] = str(tmp / "proj")
    env.pop("OHC_RESULT_OUT", None)
    if use_env_var:
        env["OHC_RESULT_OUT"] = use_env_var
    return env


def setup_project(tmp):
    proj = tmp / "proj"
    (proj / "archives" / "t" / "tsw" / "1.0").mkdir(parents=True)
    proj.joinpath("SKILL.md").write_text("# stub", encoding="utf-8")
    return proj


def main():
    from ohc.result_report import (_home_fallback_path, _looks_tool_generated,
                                   _resolve_draft_target, write_lifecycle_draft,
                                   write_pr_draft)

    tmp = Path(tempfile.mkdtemp(prefix="v1211_"))
    setup_project(tmp)

    # ── T1: $HOME 兜底 —— OHC_RESULT_OUT/--out 均缺失时写 $HOME/ohpcd-ai-worker-result.json
    fake_home = tmp / "fakehome"
    fake_home.mkdir()
    env = make_env(tmp)
    env["HOME"] = str(fake_home)
    env["USERPROFILE"] = str(fake_home)
    r = run_result(["tsw", "1.0", "--status", "failed_build",
                    "--failed-reason", "T1"], env)
    home_file = fake_home / "ohpcd-ai-worker-result.json"
    check("T1a result 命令 $HOME 兜底落盘", home_file.exists(),
          r.stdout[-300:] + r.stderr[-300:])
    if home_file.exists():
        d = json.loads(home_file.read_text(encoding="utf-8"))
        check("T1b 终态 draft:false", d.get("draft") is False)
        check("T1c tool-generated checkpoints", _looks_tool_generated(d))

    # ── T2: 生命周期草稿 basic（进程内调用需设置 os.environ）
    out_dir = tmp / "out2"
    old2 = os.environ.get("OHC_RESULT_OUT")
    os.environ["OHC_RESULT_OUT"] = str(out_dir)
    try:
        ok = write_lifecycle_draft("tsw", "1.0", "task_started")
        # 里程碑推进覆盖（同 env 块内执行）
        write_lifecycle_draft("tsw", "1.0", "recipe_generated")
    finally:
        if old2 is None:
            os.environ.pop("OHC_RESULT_OUT", None)
        else:
            os.environ["OHC_RESULT_OUT"] = old2
    f2 = out_dir / "result.json"
    check("T2a task_started 草稿落盘后已推进", ok and f2.exists())
    d2 = json.loads(f2.read_text(encoding="utf-8"))
    check("T2b draft:true + milestone", d2.get("draft") is True
          and d2.get("milestone") == "recipe_generated", d2.get("milestone"))
    check("T2c status=partial", d2.get("status") == "partial")

    # ── T3: 防降级 —— 终态写入后草稿跳过（result 命令走 env，进程内草稿走 os.environ）
    old3 = os.environ.get("OHC_RESULT_OUT")
    os.environ["OHC_RESULT_OUT"] = str(out_dir)
    try:
        r3 = run_result(["tsw", "1.0", "--status", "failed_build",
                         "--failed-reason", "T3 终态", "--force"],
                        {**os.environ, "OHC_PROJECT_DIR": str(tmp / "proj")})
        check("T3a 终态写入 rc=0", r3.returncode == 0, r3.stderr[-200:])
        d3 = json.loads(f2.read_text(encoding="utf-8"))
        check("T3b 终态 draft:false", d3.get("draft") is False)
        skipped = write_lifecycle_draft("tsw", "1.0", "pr_created")
    finally:
        if old3 is None:
            os.environ.pop("OHC_RESULT_OUT", None)
        else:
            os.environ["OHC_RESULT_OUT"] = old3
    d3b = json.loads(f2.read_text(encoding="utf-8"))
    check("T3c 终态后草稿不降级", skipped is False
          and d3b.get("draft") is False
          and d3b.get("status") == "build_failed")  # v12.13 起协议枚举规范化

    # ── T4: 手写/残留覆盖
    out4 = tmp / "out4"
    out4.mkdir()
    f4 = out4 / "result.json"
    f4.write_text(json.dumps({"pr_url": "", "status": "success", "junk": 1}),
                  encoding="utf-8")
    env4 = make_env(tmp, use_env_var=str(out4))
    # write_lifecycle_draft 内部读 env
    old = os.environ.get("OHC_RESULT_OUT")
    os.environ["OHC_RESULT_OUT"] = str(out4)
    try:
        ok4 = write_lifecycle_draft("tsw", "1.0", "task_started")
    finally:
        if old is None:
            os.environ.pop("OHC_RESULT_OUT", None)
        else:
            os.environ["OHC_RESULT_OUT"] = old
    d4 = json.loads(f4.read_text(encoding="utf-8"))
    check("T4 手写文件被草稿覆盖", ok4 and d4.get("draft") is True
          and "junk" not in d4)

    # ── T5: draft:true + status=success 被校验器拒绝
    env5 = make_env(tmp, use_env_var=str(tmp / "out5"))
    r5 = run_result(["tsw", "1.0", "--status", "success",
                     "--pr-url", "https://x/1", "--pr-number", "1",
                     "--commit-hash", "a" * 40, "--branch", "tsw-1.0",
                     "--draft-milestone", "pr_created", "--force"], env5)
    f5 = tmp / "out5" / "result.json"
    d5 = json.loads(f5.read_text(encoding="utf-8")) if f5.exists() else {}
    check("T5 draft+success 拒绝", r5.returncode != 0
          or d5.get("status") != "success",
          f"rc={r5.returncode} status={d5.get('status')}")

    # ── T6: write_pr_draft 保留 R42 语义（pr_created 里程碑）
    out6 = tmp / "out6"
    old = os.environ.get("OHC_RESULT_OUT")
    os.environ["OHC_RESULT_OUT"] = str(out6)
    try:
        ok6 = write_pr_draft("tsw", "1.0", 42, "https://gitcode/x/42")
    finally:
        if old is None:
            os.environ.pop("OHC_RESULT_OUT", None)
        else:
            os.environ["OHC_RESULT_OUT"] = old
    f6 = out6 / "result.json"
    d6 = json.loads(f6.read_text(encoding="utf-8"))
    check("T6 pr_created 草稿带 PR 字段", ok6 and f6.exists()
          and d6.get("milestone") == "pr_created"
          and d6.get("pr_number") == 42 and d6.get("pr_url"))

    # ── T7: 解析函数
    check("T7a _resolve_draft_target 目录模式",
          _resolve_draft_target() is not None)
    h = _home_fallback_path()
    check("T7b $HOME 兜底路径", h is not None
          and h.name == "ohpcd-ai-worker-result.json", str(h))

    # ── T8: 环境变量目录模式仍兼容（OHC_RESULT_OUT 指目录 → dir/result.json）
    out8 = tmp / "out8d"
    env8 = make_env(tmp, use_env_var=str(out8))
    r8 = run_result(["tsw", "1.0", "--status", "failed_build",
                     "--failed-reason", "T8"], env8)
    check("T8 目录模式 dir/result.json",
          (out8 / "result.json").exists(), r8.stderr[-200:])

    print(f"\n=== {PASS} passed, {FAIL} failed ===")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
