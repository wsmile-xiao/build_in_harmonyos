#!/usr/bin/env python3
"""Conan test_package for riscemu 2.2.7 — 消费者验证。

对本次配方刚装出来的包跑三件事：

  1. test_riscemu.py（真实测试源，L0c）—— 消费者 API/E2E 测试，输出
     HMBS_TEST_PACKAGE_RESULT 标记。
  2. 上游 pytest 套件（原样复制到 test_package/tests/，9 个文件 49 个用例，
     命令与上游 CI 一致 `pytest -W error`）—— 输出 HMBS_UPSTREAM_SUITE_PYTEST 标记。
  3. 上游 lit + filecheck 套件（原样复制到 test_package/filecheck/，11 个用例，
     命令与上游 CI 一致 `lit --timeout=5 -v`；本平台 psutil 只有 5.9.5 提供
     ohos wheel，故固定 psutil==5.9.5，确实装不上时自动降级为无 --timeout 并
     在标记的 timeout_guard 字段中记录）—— 输出 HMBS_UPSTREAM_SUITE_LIT 标记。

最后把两套上游测试的计数汇总成唯一的 HMBS_UPSTREAM_TEST_RESULT 标记。

PYTHONPATH 注入：riscemu 是纯 Python 包，其运行时闭包（pyelftools /
importlib_resources）已由配方的 build() 用 pip 装进同一个 site-packages，
所以本包自己的 site-packages 就够了；额外把 test_package 目录本身加进
PYTHONPATH，是为了让 lit 的 snitch 用例能 import 到随测试副本一起放在
test_package/snitch/ 的上游 snitch 包（上游 lit.cfg 把工作目录设为
test/filecheck 的上两级，正是为了从源码树里 import snitch——riscemu 的
pyproject 只打包 riscemu/，snitch/ 并不进入 wheel，这一点在 notes.md 中记录）。

lit 环境注意：lit 不转发调用者的环境变量（见 filecheck/lit.local.cfg 注释），
因此 HOME（fibs.asm 的调试器历史文件）与 PYTHONPATH（`python3 -m riscemu`
必须解析到本次验证的包）都由 lit.local.cfg 平台 shim 显式转发，未改动任何
上游测试文件。

测试工具（pytest / lit / psutil / filecheck）缺失时按需安装到临时 prefix
（--prefix，绝不写入解释器目录），并把 <prefix>/bin 与 <prefix> 的
site-packages 追加到子进程的 PATH/PYTHONPATH。psutil 固定 5.9.5（该平台
只有 5.9.5 提供 ohos abi3 wheel）；它不可用时 lit 自动去掉 --timeout，
仍完整跑 11 个用例（标记里的 timeout_guard 字段记录实际情况）。
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

from conan import ConanFile
from conan.errors import ConanException


class RiscemuTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _find_site_packages(self, pkg):
        """site-packages lives under lib/python3.x/site-packages — walk to locate it."""
        for root, _dirs, _files in os.walk(pkg):
            if os.path.basename(root) == "site-packages":
                return root
        return None

    def _child_env(self, sp, pkg):
        """Environment for the child test processes (package importable, tools on PATH)."""
        env = dict(os.environ)
        env["PYTHONPATH"] = os.pathsep.join(
            filter(None, [sp, os.path.dirname(os.path.abspath(__file__)), env.get("PYTHONPATH", "")])
        )
        # `python3` referenced by the upstream lit RUN lines must resolve to the
        # interpreter that has the package under test on PYTHONPATH, and the
        # package bin/ must be on PATH for the `riscemu` console script used by
        # filecheck/p2align.asm (this mirrors package_info()'s runenv_info).
        env["PATH"] = os.pathsep.join(
            filter(
                None,
                [
                    os.path.join(pkg, "bin"),
                    os.path.dirname(sys.executable),
                    env.get("PATH", ""),
                ],
            )
        )
        home = env.get("HOME") or os.path.expanduser("~")
        if os.path.isdir(home):
            env["HOME"] = home
        return env

    # ── test tool provisioning ────────────────────────────────────────────
    #
    # pytest / lit / psutil / filecheck are not part of the riscemu runtime
    # closure: they are only needed to run the copied upstream suites, and the
    # worker does not guarantee them. When one is missing it is installed into a
    # throwaway prefix instead of into the interpreter, because the CI worker's
    # python3 lives in a read-only system location (the CI setup itself falls
    # back to `pip install --user` for that reason) while TMPDIR is writable.
    # The prefix contributes `bin/` to PATH (console scripts: lit, filecheck)
    # and `lib/pythonX.Y/site-packages` to PYTHONPATH (modules: pytest, psutil,
    # lit), so the interpreter itself is never modified.

    def _tools_prefix(self):
        if not hasattr(self, "_tools_prefix_dir"):
            self._tools_prefix_dir = tempfile.mkdtemp(prefix="riscemu-testtools-")
            self.output.info(f"[test_package] test tool prefix: {self._tools_prefix_dir}")
        return self._tools_prefix_dir

    def _tools_site_packages(self, prefix):
        for root, _dirs, _files in os.walk(prefix):
            if os.path.basename(root) == "site-packages":
                return root
        return None

    def _add_tools_to_env(self, env, prefix):
        site = self._tools_site_packages(prefix)
        env["PYTHONPATH"] = os.pathsep.join(
            [p for p in [site, env.get("PYTHONPATH", "")] if p]
        )
        env["PATH"] = os.pathsep.join(
            [p for p in [os.path.join(prefix, "bin"), env.get("PATH", "")] if p]
        )

    def _pip_install_tools(self, env, python, requirements):
        prefix = self._tools_prefix()
        package_list = " ".join(requirements)
        self.output.info(f"[test_package] installing test tool(s) into {prefix}: {package_list}")
        # Second attempt forces binary-only resolution: `pip install --prefix` can
        # select an sdist even when the mirror publishes a compatible wheel
        # (observed with psutil 5.9.5, whose ohos_aarch64 wheel exists while the
        # sdist cannot build here: "platform ohos is not supported").
        attempts = [[], ["--only-binary=:all:"]]
        last_error = ""
        for extra in attempts:
            install = subprocess.run(
                [python, "-m", "pip", "install", "--prefix", prefix, *extra, *requirements],
                env=env,
                capture_output=True,
                timeout=900,
            )
            if install.returncode == 0:
                self._add_tools_to_env(env, prefix)
                return
            last_error = (install.stderr or b"").decode(errors="replace")[-2000:]
            if extra:
                self.output.info(
                    f"[test_package] pip install {package_list} failed with "
                    "--only-binary=:all: as well"
                )
            else:
                self.output.info(
                    f"[test_package] pip install {package_list} failed with sdists allowed, "
                    "retrying with --only-binary=:all:"
                )
        raise ConanException(f"pip install {package_list} failed: {last_error}")

    def _ensure_python_module(self, env, python, module, requirements, optional=False):
        """Import-check a test tool, installing it into the tool prefix when absent.

        Returns True when `import <module>` works, False only for optional tools
        whose installation was impossible on this platform.
        """
        probe = subprocess.run(
            [python, "-c", f"import {module}"], env=env, capture_output=True, timeout=120
        )
        if probe.returncode == 0:
            return True
        try:
            self._pip_install_tools(env, python, requirements)
        except ConanException as exc:
            if not optional:
                raise
            self.output.warning(f"[test_package] optional tool {module} unavailable: {exc}")
            return False
        probe = subprocess.run(
            [python, "-c", f"import {module}"], env=env, capture_output=True, timeout=120
        )
        if probe.returncode != 0:
            message = (
                f"{module} not importable even after installing {requirements}: "
                + (probe.stderr or b"").decode(errors="replace")[-500:]
            )
            if not optional:
                raise ConanException(message)
            self.output.warning(f"[test_package] optional tool: {message}")
            return False
        return True

    def _ensure_cli(self, env, name, requirements, optional=False):
        """PATH-check a console script, installing it into the tool prefix when absent."""
        if shutil.which(name, path=env.get("PATH")):
            return True
        try:
            self._pip_install_tools(env, sys.executable, requirements)
        except ConanException as exc:
            if not optional:
                raise
            self.output.warning(f"[test_package] optional CLI {name} unavailable: {exc}")
            return False
        if not shutil.which(name, path=env.get("PATH")):
            message = f"{name} CLI still not found on PATH after installing {requirements}"
            if not optional:
                raise ConanException(message)
            self.output.warning(f"[test_package] optional CLI: {message}")
            return False
        return True

    def _run_upstream_pytest(self, env, python):
        """Run the copied upstream pytest suite, emit its marker, return its counts."""
        tests_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests")
        if not os.path.isdir(tests_dir):
            raise ConanException(f"upstream tests/ not copied into test_package: {tests_dir}")
        self._ensure_python_module(env, python, "pytest", ["pytest>=7.4,<8"])
        cmd = [
            python,
            "-m",
            "pytest",
            tests_dir,
            "-q",
            "--no-header",
            "-o",
            "addopts=",  # ignore any ambient addopts
            "-p",
            "no:cacheprovider",  # keep the archive tree free of .pytest_cache
            "-W",
            "error",  # same gate as the upstream CI workflow
        ]
        self.output.info("[test_package] running upstream pytest: " + " ".join(cmd))
        res = subprocess.run(cmd, env=env, capture_output=True, timeout=900)
        out = (res.stdout or b"").decode(errors="replace")
        err = (res.stderr or b"").decode(errors="replace")
        self.output.info(out)
        if err.strip():
            self.output.info(err)
        passed = _count(out, r"(\d+) passed")
        failed = _count(out, r"(\d+) failed") + _count(out, r"(\d+) error")
        skipped = _count(out, r"(\d+) skipped")
        marker = {
            "status": (
                "passed" if res.returncode == 0 and failed == 0 and passed > 0 else "failed"
            ),
            "framework": "pytest",
            "command": " ".join(cmd),
            "discovered": passed + failed + skipped,
            "executed": passed + failed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        self.output.info("HMBS_UPSTREAM_SUITE_PYTEST=" + json.dumps(marker, ensure_ascii=False))
        return marker

    def _run_upstream_lit(self, env, python):
        """Run the copied upstream lit/filecheck suite, emit its marker, return its counts."""
        filecheck_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "filecheck")
        if not os.path.isdir(filecheck_dir):
            raise ConanException(f"upstream filecheck/ not copied into test_package: {filecheck_dir}")
        # lit --timeout needs psutil (upstream dev dependency). On this platform
        # only psutil 5.9.5 publishes an abi3 wheel for `ohos`; newer 5.9.x have
        # none and their setup.py aborts with "platform ohos is not supported",
        # so pin it exactly. lit can still run without the timeout guard, hence
        # the optional install: the flag is only added when psutil is really there.
        self._ensure_python_module(env, python, "lit", ["lit>=16,<17"])
        has_psutil = self._ensure_python_module(
            env, python, "psutil", ["psutil==5.9.5"], optional=True
        )
        timeout_args = ["--timeout=5"] if has_psutil else []
        self._ensure_cli(env, "filecheck", ["filecheck==0.0.23"])
        lit_bin = (
            shutil.which("lit", path=env.get("PATH"))
            or os.path.join(os.path.dirname(python), "lit")
        )
        cmd = [lit_bin, *timeout_args, "-v", filecheck_dir]
        self.output.info("[test_package] running upstream lit: " + " ".join(cmd))
        res = subprocess.run(cmd, env=env, capture_output=True, timeout=900)
        out = (res.stdout or b"").decode(errors="replace")
        err = (res.stderr or b"").decode(errors="replace")
        self.output.info(out)
        if err.strip():
            self.output.info(err)
        passed = _count(out, r"Passed:\s*(\d+)")
        failed = (
            _count(out, r"Failed:\s*(\d+)")
            + _count(out, r"Timed Out:\s*(\d+)")
            + _count(out, r"Unresolved:\s*(\d+)")
        )
        marker = {
            "status": (
                "passed" if res.returncode == 0 and failed == 0 and passed > 0 else "failed"
            ),
            "framework": "lit",
            "command": " ".join(cmd),
            "timeout_guard": 5 if has_psutil else None,
            "discovered": passed + failed,
            "executed": passed + failed,
            "passed": passed,
            "failed": failed,
            "skipped": _count(out, r"Unsupported:\s*(\d+)")
            + _count(out, r"Expectedly Failed:\s*(\d+)"),
        }
        self.output.info("HMBS_UPSTREAM_SUITE_LIT=" + json.dumps(marker, ensure_ascii=False))
        return marker

    def test(self):
        pkg = self.dependencies["riscemu"].package_folder
        sp = self._find_site_packages(pkg)
        if not sp or not os.path.isdir(os.path.join(sp, "riscemu")):
            raise ConanException(f"riscemu missing under site-packages (pkg={pkg})")
        env = self._child_env(sp, pkg)
        # child processes of self.run() inherit the conan process environment,
        # so publishing the same values there keeps every path importable
        # (conanrun additionally contributes the package bin/ to PATH).
        os.environ["PYTHONPATH"] = env["PYTHONPATH"]
        if "HOME" in env:
            os.environ["HOME"] = env["HOME"]

        # 1. Consumer check (emits HMBS_TEST_PACKAGE_RESULT).
        test_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_riscemu.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_riscemu.py missing: {test_script}")
        self.run(f"'{sys.executable}' '{test_script}' '{sp}'", env="conanrun")

        # 2. Upstream suites (emit their own markers + one aggregate marker).
        pytest_result = self._run_upstream_pytest(env, sys.executable)
        lit_result = self._run_upstream_lit(env, sys.executable)
        aggregate = {
            "status": (
                "passed"
                if pytest_result["status"] == "passed" and lit_result["status"] == "passed"
                else "failed"
            ),
            "framework": "pytest+lit",
            "command": "python -m pytest test_package/tests/ -q --no-header -o addopts= -W error ; "
            f"lit{' --timeout=5' if lit_result['timeout_guard'] else ''} -v test_package/filecheck",
            "timeout_guard": lit_result["timeout_guard"],
            "discovered": pytest_result["discovered"] + lit_result["discovered"],
            "executed": pytest_result["executed"] + lit_result["executed"],
            "passed": pytest_result["passed"] + lit_result["passed"],
            "failed": pytest_result["failed"] + lit_result["failed"],
            "skipped": pytest_result["skipped"] + lit_result["skipped"],
            "suites": [pytest_result, lit_result],
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(aggregate, ensure_ascii=False))
        if aggregate["status"] != "passed":
            raise ConanException(
                "upstream test suites failed: "
                f"pytest {pytest_result['passed']}/{pytest_result['discovered']}, "
                f"lit {lit_result['passed']}/{lit_result['discovered']}"
            )


def _count(text, pattern):
    """First group of a pytest/lit summary pattern, e.g. '(\\d+) passed'."""
    match = re.search(pattern, text)
    return int(match.group(1)) if match else 0
