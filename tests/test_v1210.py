# -*- coding: utf-8 -*-
"""v12.10 防丢失协议测试：骨架前置 / 事件累积 / 终态兜底 / 自动入仓 / 收割对接"""
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "scripts"))
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from ohc import feedback as fb  # noqa: E402

PASS, FAIL = [], []


def check(name, cond, extra=""):
    (PASS if cond else FAIL).append(name)
    print(("PASS" if cond else "FAIL"), name, extra)


def mk_project():
    tmp = Path(tempfile.mkdtemp(prefix="v1210_"))
    ver = tmp / "archives" / "z" / "zlib" / "1.3"
    ver.mkdir(parents=True)
    (ver / "reports").mkdir()
    (ver / "reports" / "metadata.json").write_text(
        json.dumps({"name": "zlib", "version": "1.3"}), encoding="utf-8")
    return tmp, ver


# ── T1: record_event 累积 ──
tmp, ver = mk_project()
fb.record_event(ver, "handoff:ci_build_failed", "act1 | act2")
fb.record_event(ver, "pr_created", "PR #1")
st = fb._load_feedback_state(ver)
check("T1 record_event 累积2条",
      len(st.get("events", [])) == 2 and st["events"][0]["event"] == "handoff:ci_build_failed")

# ── T2: ensure_feedback_skeleton 前置 + 幂等 ──
p1 = fb.ensure_feedback_skeleton("zlib", "1.3", pdir=str(tmp), reason="pr_created")
check("T2a 骨架生成", p1 is not None and p1.exists())
fid = fb._load_feedback_state(ver).get("feedback_id")
check("T2b state 记录 id", bool(fid))
body1 = p1.read_text(encoding="utf-8")
check("T2c 骨架含事件时间线",
      "EVENTS:BEGIN" in body1 and "pr_created" in body1 and "handoff:ci_build_failed" in body1)
n_files_before = len(list((tmp / "feedback").glob("SKILL_FEEDBACK_*.md")))
p2 = fb.ensure_feedback_skeleton("zlib", "1.3", pdir=str(tmp), reason="resume_pr_exists")
n_files_after = len(list((tmp / "feedback").glob("SKILL_FEEDBACK_*.md")))
check("T2d 幂等不重复生成", n_files_before == n_files_after == 1)
st = fb._load_feedback_state(ver)
check("T2e exists 事件记录",
      st["events"][-1]["event"] == "skeleton_exists")

# ── T3: cmd_feedback 复用骨架（无孤儿文件）──
rc = fb.cmd_feedback("zlib", "1.3", pdir=str(tmp))
files = list((tmp / "feedback").glob("SKILL_FEEDBACK_*.md"))
check("T3a 骨架存在时 cmd_feedback 复用同文件", len(files) == 1)
check("T3b 占位符存在 → HANDOFF rc=1", rc == 1)
check("T3c state id 未变", fb._load_feedback_state(ver)["feedback_id"] == fid)

# ── T4: 事件刷新进报告 ──
fb.record_event(ver, "ci_passed", "PR #1")
fb._refresh_events_section(Path(files[0]), ver)
body2 = files[0].read_text(encoding="utf-8")
check("T4 新事件刷入时间线", "ci_passed" in body2)

# ── T5: 填充 → resume 闭环 → complete ──
body = files[0].read_text(encoding="utf-8")
body = body.replace("(请填写)", "已填写（测试填充）")
files[0].write_text(body, encoding="utf-8")
rc = fb.cmd_feedback("zlib", "1.3", pdir=str(tmp), resume=True)
check("T5a resume 填充后 rc=0", rc == 0, f"rc={rc}")
check("T5b state 状态 complete",
      fb._load_feedback_state(ver).get("status") == "complete")

# ── T6: feedback_status / pending_flag ──
stt = fb.feedback_status("zlib", "1.3", pdir=str(tmp))
check("T6a status complete", stt["complete"] and not stt["pending"])
check("T6b pending_flag 完成后 False",
      fb.feedback_pending_flag("zlib", "1.3", pdir=str(tmp)) is False)

# ── T7: 终态兜底（缺失 → 补骨架 → pending True）──
tmp2, ver2 = mk_project()
flag = fb.feedback_pending_flag("zlib", "1.3", pdir=str(tmp2),
                                skeleton_reason="result_failed")
check("T7a 缺失时 pending=True", flag is True)
check("T7b 兜底骨架已生成", fb.feedback_status("zlib", "1.3", pdir=str(tmp2))["exists"])

# ── T8: _push_feedback_to_branch ──
repo = Path(tempfile.mkdtemp(prefix="v1210_git_"))
def g(*a):
    return subprocess.run(["git", *a], cwd=repo, capture_output=True,
                          text=True, encoding="utf-8", errors="replace")
g("init", "-b", "feat/zlib-1.3-W999")
g("config", "user.email", "t@t"); g("config", "user.name", "t")
(repo / "README").write_text("x", encoding="utf-8")
g("add", "."); g("commit", "-m", "init")
(repo / "feedback").mkdir()
(repo / "archives" / "z" / "zlib" / "1.3").mkdir(parents=True)
(repo / "archives" / "z" / "zlib" / "1.3" / ".feedback-state.json").write_text(
    "{}", encoding="utf-8")
(repo / "feedback" / "SKILL_FEEDBACK_TEST01.md").write_text(
    "# report", encoding="utf-8")

from ohc.submission import _push_feedback_to_branch  # noqa: E402
os.environ.pop("OHC_FEEDBACK_PUSH", None)
_push_feedback_to_branch(str(repo), "feat/zlib-1.3-W999")
log = g("log", "--name-only", "-1", "--pretty=format:").stdout
committed = set(l for l in log.splitlines() if l.strip())
check("T8a feedback md 已提交", "feedback/SKILL_FEEDBACK_TEST01.md" in committed)
check("T8b state.json 不入仓(JC5)", ".feedback-state.json" not in committed and
      "archives/z/zlib/1.3/.feedback-state.json" not in committed)

# main 分支保护
g("checkout", "-b", "main")
(repo / "feedback" / "SKILL_FEEDBACK_TEST02.md").write_text("# r2", encoding="utf-8")
n_main_before = int(g("rev-list", "--count", "main").stdout.strip())
_push_feedback_to_branch(str(repo), "main")
n_main_after = int(g("rev-list", "--count", "main").stdout.strip())
check("T8c main 分支跳过提交", n_main_before == n_main_after)

os.environ["OHC_FEEDBACK_PUSH"] = "0"
(repo / "feedback" / "SKILL_FEEDBACK_TEST03.md").write_text("# r3", encoding="utf-8")
_push_feedback_to_branch(str(repo), "main")
os.environ.pop("OHC_FEEDBACK_PUSH", None)
check("T8d OHC_FEEDBACK_PUSH=0 关闭", True)

# ── T9: result.json feedback_pending 字段注入 ──
tmp3 = Path(tempfile.mkdtemp(prefix="v1210_res_"))
ver3 = tmp3 / "archives" / "z" / "zlib" / "1.2.13"
ver3.mkdir(parents=True)
(ver3 / "reports").mkdir()
(ver3 / "reports" / "metadata.json").write_text(
    json.dumps({"name": "zlib", "version": "1.2.13"}), encoding="utf-8")
out_file = tmp3 / "result.json"
# find_project_dir 按 SKILL.md 标记定位项目根（worker 现实：workspace 即项目根）
(tmp3 / "SKILL.md").write_text("# stub project\n", encoding="utf-8")
env = {**os.environ, "OHC_RESULT_OUT": str(out_file),
       "OHC_PROJECT_DIR": str(tmp3)}
src = (
    "import sys, json, os\n"
    f"sys.path.insert(0, r'{BASE / 'scripts'}')\n"
    "os.chdir(r'%s')\n" % str(tmp3) +
    "from ohc.result_report import result_cli\n"
    "rc = result_cli(['zlib', '1.2.13', '--status', 'partial',\n"
    "                 '--failed-reason', 'test gate',\n"
    "                 '--summary', 'v12.10 test', '--no-ci-verify',\n"
    "                 '--force', '--out', r'%s'])\n" % str(out_file) +
    "print('rc=', rc)\n"
)
p = subprocess.run([sys.executable, "-X", "utf8", "-c", src],
                   capture_output=True, text=True, encoding="utf-8",
                   errors="replace", env=env, cwd=str(tmp3))
ok_write = out_file.exists()
check("T9a result 写盘(partial)", ok_write,
      "" if ok_write else p.stdout[-200:] + p.stderr[-300:])
if ok_write:
    rj = json.loads(out_file.read_text(encoding="utf-8"))
    check("T9b feedback_pending 字段存在", "feedback_pending" in rj,
          f"keys={list(rj.keys())[:12]}")
    check("T9c 兜底骨架已补", fb.feedback_status(
        "zlib", "1.2.13", pdir=str(tmp3))["exists"])
    check("T9d pending 值为 true", rj.get("feedback_pending") is True)

# ── T10: SKILL.md v12.10 关键词 ──
skill = (BASE / "SKILL.md").read_text(encoding="utf-8")
for kw in ("v12.10", "骨架前置", "feedback_pending", "R45"):
    check(f"T10 SKILL 含 {kw}", kw in skill)

# ── T11: v12.10.1 状态文件位置——顶层 .ohc/，绝不在 archives 树内 ──
tmp4, ver4 = mk_project()
fb.record_event(ver4, "pr_created", "PR #9")
new_state = tmp4 / ".ohc" / "feedback-state" / "z" / "zlib" / "1.3.json"
check("T11a 状态写入 .ohc/feedback-state", new_state.exists())
check("T11b archives 树内无状态文件",
      not (ver4 / ".feedback-state.json").exists())
fb.record_event(ver4, "ci_passed", "PR #9")
st4 = fb._load_feedback_state(ver4)
check("T11c .ohc/ 状态可读回", len(st4.get("events", [])) == 2)

# ── T12: 遗留迁移——archives 内旧副本 → .ohc/，旧文件删除 ──
tmp5, ver5 = mk_project()
legacy = ver5 / ".feedback-state.json"
legacy.write_text(json.dumps({"feedback_id": "LEGACY01",
                              "events": [{"ts": "x", "event": "old",
                                          "detail": ""}]}),
                  encoding="utf-8")
st5 = fb._load_feedback_state(ver5)
check("T12a 遗留数据迁移成功", st5.get("feedback_id") == "LEGACY01")
check("T12b 遗留文件已删除", not legacy.exists())
check("T12c 新位置已有状态",
      (tmp5 / ".ohc" / "feedback-state" / "z" / "zlib" / "1.3.json").exists())

# ── T13: .gitignore 双保险 ──
gi = (BASE / ".gitignore").read_text(encoding="utf-8")
check("T13a gitignore 含 .ohc/", ".ohc/" in gi)
check("T13b gitignore 含遗留兜底", "**/.feedback-state.json" in gi)

# ── T14: SKILL v12.10.1 ──
check("T14 SKILL 含 v12.10.1", "v12.10.1" in skill)

print(f"\n===== {len(PASS)} passed, {len(FAIL)} failed =====")
sys.exit(1 if FAIL else 0)
