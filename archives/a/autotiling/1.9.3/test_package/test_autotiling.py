#!/usr/bin/env python3
"""autotiling 1.9.3 消费者测试 — 真实调用被测包 API（R34）。

不依赖 i3/sway 窗口管理器即可验证的路径：
  1. import autotiling，__version__ == "1.9.3"
  2. autotiling.main.get_parser() 构造 argparse.ArgumentParser
  3. parser 解析 -w/-sr 等真实参数，校验默认值与解析结果
  4. autotiling.main.save_string() 文件写入往返
  5. autotiling.main.temp_dir() 返回非空
  6. bin/autotiling --version（argparse version 动作，不连 i3）
  7. bin/autotiling -h（help 动作，不连 i3）

输出 hmbs 硬门禁标记（数字来自真实执行计数）：
  - HMBS_TEST_PACKAGE_RESULT：discovered/passedCount = 实际检查数
  - HMBS_UPSTREAM_TEST_RESULT：status=no_tests（上游无测试套件，审计见
    test_package/MANIFEST.yml 的 upstream_test_audit）
"""
import argparse
import json
import os
import subprocess
import sys


def main():
    cli = sys.argv[1] if len(sys.argv) > 1 else None
    checks = []  # (name, ok, detail)

    # 1. import + version
    try:
        import autotiling
        checks.append(("import autotiling + __version__",
                       autotiling.__version__ == "1.9.3",
                       f"__version__={autotiling.__version__!r}"))
    except Exception as exc:
        checks.append(("import autotiling + __version__", False, repr(exc)))

    # 2. get_parser constructs an ArgumentParser
    try:
        from autotiling.main import get_parser
        parser = get_parser()
        checks.append(("get_parser() constructs ArgumentParser",
                       isinstance(parser, argparse.ArgumentParser), ""))
    except Exception as exc:
        checks.append(("get_parser() constructs ArgumentParser", False, repr(exc)))

    # 3. real arg parsing with -w / -sr
    try:
        from autotiling.main import get_parser
        args = get_parser().parse_args(["-w", "1", "3", "-sr", "1.61"])
        ok = (args.workspaces == ["1", "3"]
              and abs(args.splitratio - 1.61) < 1e-9
              and args.events == ["WINDOW", "MODE"])
        checks.append(("parse_args workspaces/splitratio/events", ok,
                       f"workspaces={args.workspaces}, "
                       f"splitratio={args.splitratio}, events={args.events}"))
    except Exception as exc:
        checks.append(("parse_args workspaces/splitratio/events", False, repr(exc)))

    # 4. save_string file write roundtrip
    try:
        from autotiling.main import save_string
        tmp = os.path.join(os.environ.get("TMPDIR", "/tmp"),
                           "autotiling_save_string_test.txt")
        save_string("1,2,3", tmp)
        with open(tmp, "rt") as fh:
            content = fh.read()
        os.remove(tmp)
        checks.append(("save_string file write", content == "1,2,3",
                       f"content={content!r}"))
    except Exception as exc:
        checks.append(("save_string file write", False, repr(exc)))

    # 5. temp_dir non-empty
    try:
        from autotiling.main import temp_dir
        tdir = temp_dir()
        checks.append(("temp_dir non-empty", bool(tdir), f"temp_dir={tdir!r}"))
    except Exception as exc:
        checks.append(("temp_dir non-empty", False, repr(exc)))

    # 6. CLI --version (argparse version action, no i3 connection)
    if cli:
        try:
            r = subprocess.run([cli, "--version"], capture_output=True,
                               text=True, timeout=60)
            out = (r.stdout or "") + (r.stderr or "")
            checks.append(("CLI --version exits 0 & prints 1.9.3",
                           r.returncode == 0 and "1.9.3" in out,
                           f"rc={r.returncode} out={out.strip()[:60]!r}"))
        except Exception as exc:
            checks.append(("CLI --version exits 0 & prints 1.9.3", False, repr(exc)))

    # 7. CLI -h (help action, no i3 connection)
    if cli:
        try:
            r = subprocess.run([cli, "-h"], capture_output=True,
                               text=True, timeout=60)
            out = (r.stdout or "") + (r.stderr or "")
            checks.append(("CLI -h exits 0 & prints usage",
                           r.returncode == 0 and "usage" in out,
                           f"rc={r.returncode}"))
        except Exception as exc:
            checks.append(("CLI -h exits 0 & prints usage", False, repr(exc)))

    discovered = len(checks)
    passed = sum(1 for _n, ok, _d in checks if ok)
    for name, ok, detail in checks:
        print(f"[{'PASS' if ok else 'FAIL'}] {name} {detail}")
    print(f"total: {passed}/{discovered}")

    marker = {
        "executed": True,
        "passed": passed == discovered,
        "command": "python3 test_autotiling.py <bin/autotiling>",
        "discovered": discovered,
        "passedCount": passed,
    }
    print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))

    upstream = {
        "status": "no_tests",
        "framework": "setuptools",
        "command": "make check (n/a)",
        "discovered": 0,
        "executed": 0,
        "passed": 0,
        "failed": 0,
        "skipped": 0,
        "reason": ("autotiling 1.9.3 上游无测试套件：PyPI sdist 仅含 autotiling/ 包与 "
                   "setup.py/setup.cfg/pyproject.toml/README/LICENSE；GitHub v1.9.3 "
                   "源码树无 tests/ 目录；Makefile 仅有 upload/tag/publish/clean/"
                   "format/lint 目标，无 check/test 目标；main.py 无 assert 断言"),
    }
    print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))

    return 0 if passed == discovered else 1


if __name__ == "__main__":
    sys.exit(main())
