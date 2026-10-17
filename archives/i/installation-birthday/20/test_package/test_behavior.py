#!/usr/bin/env python3
"""installation-birthday/20 行为探针（本机/真机通用，纯标准库）。

argv[1] = 包内 bin/installation-birthday 脚本路径。
对被测脚本做 6 项运行语义断言：
  1. 语法完整性：py_compile 副本通过（不 import，无副作用）
  2. --help 退出码 0 且 usage 含 --puppet/--force
  3. --verbosity 5 退出码 2（argparse invalid choice，确定性断言）
  4. --force --puppet 全跑：rc ∈ {0,1}；rc==0 → stdout 恰一行
     installation_date=YYYY-MM-DD；rc==1 → stdout 为空（真机无任何
     候选时间戳文件时上游语义即静默退出 1）
  5. --verbosity=2 复刻上游 debian/tests/0001-smoketest 语义：rc ∈ {0,1}
  6. 负向：截断副本 --help 退出码非 0（检出，随后清理）

说明：脚本顶层 `import distro`，本机（Windows 开发机）无 python3-distro
时自动注入桩模块（仅影响子进程 import，不改被测脚本本体）；真机
python3 3.12.9 自带 distro，走真实路径。脚本需要 python3 ≥ 3.11
（datetime.UTC），本机 3.14 / 真机 3.12 均满足。
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

DATE_RE = re.compile(r"^installation_date=\d{4}-\d{2}-\d{2}$")

_fail = 0


def say(ok, what):
    global _fail
    print("[%s] %s" % ("OK" if ok else "FAIL", what))
    if not ok:
        _fail += 1


def mktmp():
    try:
        return tempfile.mkdtemp(prefix="ib_behave_", dir=os.getcwd())
    except OSError:
        return tempfile.mkdtemp(prefix="ib_behave_")


def run(python, args, env_extra=None):
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    return subprocess.run([python] + args, capture_output=True,
                          text=True, env=env, timeout=60)


def main():
    script = os.path.abspath(sys.argv[1])

    python = shutil.which("python3") or shutil.which("python") or sys.executable

    # 本机无 distro 时注入桩模块（真机自带 distro，走真实路径）
    probe = subprocess.run([python, "-c", "import distro"],
                           capture_output=True, timeout=60)
    extra = None
    if probe.returncode != 0:
        stubdir = mktmp()
        with open(os.path.join(stubdir, "distro.py"), "w", encoding="utf-8") as f:
            f.write('def id(*a, **k):\n    return "StubDistro"\n')
        extra = {"PYTHONPATH": stubdir + os.pathsep + os.environ.get("PYTHONPATH", "")}

    tmp = mktmp()

    # 1. 语法完整性（副本上 py_compile，__pycache__ 落在临时目录）
    copy_ok = os.path.join(tmp, "installation-birthday.py")
    shutil.copyfile(script, copy_ok)
    r = subprocess.run([python, "-m", "py_compile", copy_ok],
                       capture_output=True, cwd=tmp, timeout=60)
    say(r.returncode == 0, "py_compile 语法完整性通过")

    # 2. --help
    r = run(python, [script, "--help"], extra)
    say(r.returncode == 0 and "--puppet" in r.stdout and "--force" in r.stdout,
        "--help 退出码 0 且 usage 含 --puppet/--force")

    # 3. --verbosity 5（invalid choice，确定性退出码 2）
    r = run(python, [script, "--verbosity", "5"], extra)
    say(r.returncode == 2 and "invalid choice" in r.stderr,
        "--verbosity 5 退出码 2（argparse 拒绝）")

    # 4. --force --puppet 全跑（真实 main() 路径）
    r = run(python, [script, "--force", "--puppet"], extra)
    ok = r.returncode in (0, 1)
    if ok and r.returncode == 0:
        lines = [x for x in r.stdout.splitlines() if x.strip()]
        ok = len(lines) == 1 and DATE_RE.match(lines[0].strip()) is not None
        say(ok, "--force --puppet rc=0 且输出 installation_date=YYYY-MM-DD")
    else:
        say(ok and r.stdout.strip() == "",
            "--force --puppet rc=1 且 stdout 为空（无候选时间戳）")

    # 5. 上游 autopkgtest 语义复刻（debian/tests/0001-smoketest）
    r = run(python, [script, "--verbosity=2"], extra)
    say(r.returncode in (0, 1), "--verbosity=2 复刻上游 smoke 测试语义 rc∈{0,1}")

    # 6. 负向：截断副本
    trunc = os.path.join(tmp, "truncated.py")
    with open(script, "rb") as f:
        data = f.read()
    with open(trunc, "wb") as f:
        f.write(data[: len(data) // 2])
    r = run(python, [trunc, "--help"], extra)
    say(r.returncode != 0, "截断副本 --help 退出码非 0（检出损坏）")

    shutil.rmtree(tmp, ignore_errors=True)
    if extra:
        shutil.rmtree(extra["PYTHONPATH"].split(os.pathsep)[0], ignore_errors=True)

    if _fail == 0:
        print("test_behavior: all checks passed")
        return 0
    print("test_behavior: %d check(s) FAILED" % _fail)
    return 1


if __name__ == "__main__":
    sys.exit(main())
