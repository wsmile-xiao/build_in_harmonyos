# -*- coding: utf-8 -*-
"""v12.18 自审加固测试：H1 原子写 / H2 conan 网络重试 / H3 串扰自检"""
import json
import os
import subprocess
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
    tmp = Path(tempfile.mkdtemp(prefix="v1218_"))
    for k in ("OHC_PROJECT_DIR", "OHC_RESULT_OUT", "OHC_TASK_DEADLINE",
              "OHC_TASK_BUDGET_SEC", "OHPCD_BUDGET_MINUTES"):
        os.environ.pop(k, None)

    # ── H1: result.json 原子写 ──
    proj = tmp / "proj"
    (proj / "archives" / "t" / "tsw" / "1.0").mkdir(parents=True)
    proj.joinpath("SKILL.md").write_text("# stub", encoding="utf-8")
    out = tmp / "out_h1"
    os.environ["OHC_PROJECT_DIR"] = str(proj)
    os.environ["OHC_RESULT_OUT"] = str(out)
    r = subprocess.run(
        [sys.executable, "-X", "utf8", str(REPO / "scripts" / "ohc-run.py"),
         "result", "tsw", "1.0", "--status", "build_failed",
         "--failed-reason", "H1 原子写", "--force"],
        capture_output=True, text=True, cwd=str(REPO), timeout=120)
    d = json.loads((out / "result.json").read_text(encoding="utf-8"))
    check("H1a 正常写 + 无 .tmp 残留", r.returncode == 0
          and d.get("status") == "build_failed"
          and not list(out.glob("*.tmp")), list(out.glob("*")))
    src = (REPO / "scripts" / "ohc" / "result_report.py").read_text(encoding="utf-8")
    check("H1b os.replace 原子替换在位", "os.replace(tmp_path, out_path)" in src)
    check("H1c 回读自检仍在", "写后回读自检" in src)

    # ── H2: conan 网络特征重试 ──
    from ohc.conan_verify import ConanVerifier
    v = ConanVerifier.__new__(ConanVerifier)   # 不跑 __init__（避免环境探测）
    import ohc.conan_verify as cv
    # H2a: 特征正则命中各类网络错误
    net_re = ConanVerifier._NET_ERR_RE
    hits = ["Connection reset by peer", "SSL handshake failed",
            "502 Bad Gateway", "Failed to connect: 503",
            "Connection timed out", "unreachable network",
            "Temporary failure in name resolution"]
    misses = ["ERROR: Package 'zlib/1.2.13' not found",
              "ConanException: Recipe not found",
              "Invalid configuration"]
    check("H2a 网络特征全部命中", all(net_re.search(h) for h in hits), hits)
    check("H2b 非网络错误不命中（不盲目重试）",
          not any(net_re.search(m) for m in misses), misses)
    # H2c: 重试路径行为（网络错误 2 次 → 第 3 次成功）
    calls = {"n": 0}

    class FakeR:
        def __init__(self, rc, out):
            self.returncode, self.stdout, self.stderr = rc, out, ""

    def fake_run(cmd, **kw):
        calls["n"] += 1
        if calls["n"] < 3:
            return FakeR(1, "Connection reset by peer")
        return FakeR(0, "ok")
    orig_run = cv.subprocess.run
    orig_sleep = cv.time.sleep
    cv.subprocess.run = fake_run
    cv.time.sleep = lambda s: None
    try:
        rc, out2 = v._run(["conan", "download", "zlib/1.2.13"], timeout=10)
        check("H2c conan 网络错误重试后成功", rc == 0 and calls["n"] == 3,
              (rc, calls["n"]))
        calls["n"] = 0

        def always_pkg_missing(cmd, **kw):
            calls["n"] += 1
            return FakeR(1, "ERROR: Package 'zlib/1.2.13' not found")
        cv.subprocess.run = always_pkg_missing
        rc, _ = v._run(["conan", "download", "zlib/1.2.13"], timeout=10)
        check("H2d 缺包错误不重试（1 次）", rc == 1 and calls["n"] == 1,
              (rc, calls["n"]))
        calls["n"] = 0

        def always_net_fail(cmd, **kw):
            calls["n"] += 1
            return FakeR(1, "502 Bad Gateway")
        cv.subprocess.run = always_net_fail
        rc, _ = v._run(["conan", "download", "zlib/1.2.13"], timeout=10)
        check("H2e 持续网络错误恰重试 3 次", rc == 1 and calls["n"] == 3,
              (rc, calls["n"]))
    finally:
        cv.subprocess.run = orig_run
        cv.time.sleep = orig_sleep

    # ── H3: 串扰自检 ──
    os.environ["OHC_PROJECT_DIR"] = str(tmp)          # 指向假目录（含 SKILL.md? 不含）
    # tmp 无 SKILL.md → find_project_dir 不吃 env → 警告路径
    fake_proj = tmp / "fakeproj"
    fake_proj.mkdir()
    (fake_proj / "SKILL.md").write_text("# x", encoding="utf-8")
    os.environ["OHC_PROJECT_DIR"] = str(fake_proj)    # 有效 env 指向别处
    r = subprocess.run(
        [sys.executable, "-X", "utf8", str(REPO / "scripts" / "ohc-run.py"),
         "result", "tsw", "1.0", "--status", "build_failed",
         "--failed-reason", "H3", "--force"],
        capture_output=True, text=True, cwd=str(REPO), timeout=120)
    check("H3a env 指向异项目时 stderr 出警告",
          "OHC_PROJECT_DIR" in r.stderr and "不一致" in r.stderr,
          r.stderr[-200:])
    os.environ["OHC_PROJECT_DIR"] = str(REPO)         # 指回脚本所在项目 → 无警告
    r = subprocess.run(
        [sys.executable, "-X", "utf8", str(REPO / "scripts" / "ohc-run.py"),
         "result", "tsw", "1.0", "--status", "build_failed",
         "--failed-reason", "H3b", "--force"],
        capture_output=True, text=True, cwd=str(REPO), timeout=120)
    check("H3b 一致时无警告", "不一致" not in r.stderr, r.stderr[-200:])

    print(f"\n=== {PASS} passed, {FAIL} failed ===")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
