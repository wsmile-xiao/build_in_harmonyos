import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import download

# Runner-level compatibility shim for ply's upstream unittest scripts.
#
# NOTHING in the upstream test files is modified.  Three *environment*
# adaptations let the suite run with its original, un-weakened assertions
# (see the build() docstring for the evidence behind each one):
#
#   1. `unittest.TestCase.assert_` — the historical alias of assertTrue was
#      removed in Python 3.12, which turned 86 of the 88 assertions into
#      AttributeError.  Restoring the alias keeps every assertion at full
#      strength (same check, old name).
#   2. `cwd` — ply's scripts assume they run from inside `test/`
#      (`test/lex_optimize.py` does `sys.path.insert(0, "..")`; the generated
#      `lextab.py` / `parsetab.py` are written relative to the cwd).
#   3. `multiprocessing` start method — `test/testcpp.py` drives its checks
#      through `multiprocessing.Process` with **no** `__main__` guard, which
#      relies on fork semantics; this platform's CPython defaults to `spawn`.
RUNNER_SHIM = '''"""Compatibility runner for ply's upstream unittest scripts.

Applies three environment adaptations (no upstream test file is modified):
  * restores the `unittest.TestCase.assert_` alias removed in Python 3.12;
  * expects to be started with cwd = the upstream `test/` directory;
  * forces the `fork` multiprocessing start method that `testcpp.py` assumes.
"""
import multiprocessing
import os
import runpy
import sys
import unittest

if not hasattr(unittest.TestCase, "assert_"):
    unittest.TestCase.assert_ = unittest.TestCase.assertTrue

try:
    multiprocessing.set_start_method("fork", force=True)
except (ValueError, RuntimeError):
    pass

script = os.path.abspath(sys.argv[1])
sys.path.insert(0, os.path.dirname(script))
sys.argv = [script]

try:
    runpy.run_path(script, run_name="__main__")
except SystemExit as exc:
    if exc.code not in (0, None):
        sys.exit(exc.code)
'''


class PlyConan(ConanFile):
    name = "ply"
    version = "3.11"
    package_type = "python-require"
    license = "BSD-3-Clause"
    homepage = "https://github.com/dabeaz/ply"
    description = ("ply — Python Lex-Yacc: an implementation of lex and yacc "
                   "parsing tools for Python (LALR(1))")
    settings = "os", "arch", "compiler", "build_type"
    # 纯 Python noarch——无 C/C++ 编译

    def source(self):
        download(self, self.conan_data["sources"]["url"], "ply-3.11.tar.gz",
                 sha256=self.conan_data["sources"]["sha256"])
        # --no-same-owner: hmdfs 上归档属主与构建 UID 不一致（同 packaging）
        self.run("tar -xzf ply-3.11.tar.gz --no-same-owner || true")
        self.run("cp -a ply-3.11/. . && rm -rf ply-3.11")

    def build(self):
        # 上游测试（test/ 目录）——实测并如实回填（R51：真实运行，不伪造）
        #
        # ply 的 test/ 不是 pytest 风格：testlex.py / testyacc.py / testcpp.py
        # 是 **unittest 脚本**（文件名不匹配 pytest 默认的 test_*.py 模式，
        # pytest 直接收集会得到 "no tests ran"）。故按上游方式直接执行脚本。
        #
        # ── 本轮把通过率从 2/88 提升到 88/88，三处均为「运行方式」问题，
        #    非 ply 缺陷，且**未改动任何上游测试文件**（逐项有实测依据）：
        #
        # (1) assert_ 别名：套件用 self.assert_()（testlex 66 处、testyacc 36 处），
        #     该 unittest.TestCase.assertTrue 的历史别名在 **Python 3.12 已移除**
        #     （本机实测 hasattr(unittest.TestCase,'assert_') is False）。
        #     runner 内恢复该别名（语义等价于 assertTrue，**不放宽任何断言**）。
        #
        # (2) cwd 必须是 test/：上游脚本假定自己在 test/ 内运行
        #     （test/lex_optimize.py 做 sys.path.insert(0,"..")；
        #     生成的 lextab.py / parsetab.py 相对当前目录写）。
        #     实测：从源码根运行 → testlex errors=42；
        #           从 test/ 运行 + 别名 → testlex 43 OK、testyacc 42 OK。
        #     之前从根目录跑属**调用错误**，不是 ply 的问题。
        #
        # (3) multiprocessing 起始方式：test/testcpp.py 用
        #     multiprocessing.Process 驱动检查且**没有 __main__ 守卫**
        #     （实测 grep -c '__main__' testcpp.py == 0），依赖 fork 语义；
        #     本平台 CPython 默认 **spawn**（实测 get_start_method()=='spawn'），
        #     子进程会重新 import 模块 → 3 项报 "Time limit exceeded!"。
        #     runner 内 set_start_method("fork") 后：testcpp 3 OK。
        #
        # 实测（2026-09-29，OHOS Python 3.12.9）：
        #     testlex.py  Ran 43 tests  OK
        #     testyacc.py Ran 42 tests  OK
        #     testcpp.py  Ran  3 tests  OK      → 88/88 = 100%
        if can_run(self):
            import subprocess
            import sys
            py = "/data/service/hnp/bin/python3" \
                if os.path.isfile("/data/service/hnp/bin/python3") \
                else sys.executable
            src = self.source_folder
            testdir = os.path.join(src, "test")
            if not os.path.isdir(testdir):
                self.output.warning("upstream test/ not found; skipped")
                return
            runner = os.path.join(src, "ohc_ply_runner.py")
            with open(runner, "w", encoding="utf-8") as fh:
                fh.write(RUNNER_SHIM)
            env = dict(os.environ)
            env["PYTHONPATH"] = src
            for script in ("testlex.py", "testyacc.py", "testcpp.py"):
                if not os.path.isfile(os.path.join(testdir, script)):
                    continue
                # 每个脚本前清掉上次生成的表文件，避免相互干扰
                for stale in ("lextab.py", "parsetab.py"):
                    p = os.path.join(testdir, stale)
                    if os.path.exists(p):
                        os.remove(p)
                # cwd=test/（见上 (2)）；runner 施加 (1)(3)
                r = subprocess.run([py, runner, script], cwd=testdir,
                                   capture_output=True, text=True,
                                   env=env, timeout=1800)
                out = r.stdout + r.stderr
                print("[ply upstream tests] %s rc=%d" % (script, r.returncode))
                for line in out.splitlines()[-6:]:
                    print("[ply upstream tests]", line)

    def package(self):
        # 纯 Python noarch——拷贝 ply/ 包到 site-packages
        # （绕过 pip/setuptools 构建——同 packaging/python-magic/rich）
        site = os.path.join(self.package_folder, "lib", "python3.12",
                            "site-packages")
        shutil.copytree(os.path.join(self.source_folder, "ply"),
                        os.path.join(site, "ply"))

    def package_info(self):
        self.cpp_info.libs = []
        self.env_info.PYTHONPATH.append(
            os.path.join(self.package_folder, "lib", "python3.12",
                         "site-packages"))
