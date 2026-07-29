#!/usr/bin/env python3
"""Conan test_package for inih r58 — Conan L1 official test.

Uses CMake (CMakeDeps + CMakeToolchain) so the compiler is handled
by Conan toolchain, not raw shell env vars (R33).

Emits HMBS evidence markers for preflight verification:
  - HMBS_TEST_PACKAGE_RESULT: test_package consumer-side test results
  - HMBS_UPSTREAM_TEST_RESULT: official r58 upstream baseline suite status
"""
import json
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import download, mkdir, unzip


class InihTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    _upstream_url = "https://github.com/benhoyt/inih/archive/refs/tags/r58.tar.gz"
    _upstream_sha256 = "e79216260d5dffe809bda840be48ab0eec7737b2bb9f02d2275c1b46344ea7b7"
    # Official tests/unittest.sh contains these 15 compile/run/baseline cases.
    _upstream_cases = (
        ("multi", "unittest.c", (), "baseline_multi.txt"),
        ("multi_max_line", "unittest.c", ("INI_MAX_LINE=20",), "baseline_multi_max_line.txt"),
        ("single", "unittest.c", ("INI_ALLOW_MULTILINE=0",), "baseline_single.txt"),
        ("disallow_inline_comments", "unittest.c", ("INI_ALLOW_INLINE_COMMENTS=0",), "baseline_disallow_inline_comments.txt"),
        ("stop_on_first_error", "unittest.c", ("INI_STOP_ON_FIRST_ERROR=1",), "baseline_stop_on_first_error.txt"),
        ("handler_lineno", "unittest.c", ("INI_HANDLER_LINENO=1",), "baseline_handler_lineno.txt"),
        ("string", "unittest_string.c", ("INI_MAX_LINE=20",), "baseline_string.txt"),
        ("heap", "unittest.c", ("INI_USE_STACK=0",), "baseline_heap.txt"),
        ("heap_max_line", "unittest.c", ("INI_USE_STACK=0", "INI_MAX_LINE=20", "INI_INITIAL_ALLOC=20"), "baseline_heap_max_line.txt"),
        ("heap_realloc", "unittest.c", ("INI_USE_STACK=0", "INI_ALLOW_REALLOC=1", "INI_INITIAL_ALLOC=5"), "baseline_heap_realloc.txt"),
        ("heap_realloc_max_line", "unittest.c", ("INI_USE_STACK=0", "INI_MAX_LINE=20", "INI_ALLOW_REALLOC=1", "INI_INITIAL_ALLOC=5"), "baseline_heap_realloc_max_line.txt"),
        ("heap_string", "unittest_string.c", ("INI_USE_STACK=0", "INI_MAX_LINE=20", "INI_INITIAL_ALLOC=20"), "baseline_heap_string.txt"),
        ("call_handler_on_new_section", "unittest.c", ("INI_CALL_HANDLER_ON_NEW_SECTION=1",), "baseline_call_handler_on_new_section.txt"),
        ("allow_no_value", "unittest.c", ("INI_ALLOW_NO_VALUE=1",), "baseline_allow_no_value.txt"),
        ("alloc", "unittest_alloc.c", ("INI_CUSTOM_ALLOCATOR=1", "INI_USE_STACK=0", "INI_ALLOW_REALLOC=1", "INI_INITIAL_ALLOC=12"), "baseline_alloc.txt"),
    )

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.generate()
        # Generate LD_LIBRARY_PATH for shared library runtime
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _upstream_source(self):
        root = os.path.join(self.build_folder, "upstream-r58")
        if not os.path.isfile(os.path.join(root, "ini.c")):
            mkdir(self, root)
            tarball = os.path.join(self.build_folder, "upstream-r58.tar.gz")
            download(self, url=self._upstream_url, filename=tarball,
                     sha256=self._upstream_sha256, verify=True)
            unzip(self, tarball, destination=root, strip_root=True)
        return root

    def _emit_upstream(self, status, executed, passed, failed, skipped, reason=None):
        result = {
            "status": status,
            "framework": "inih unittest.sh baseline suite",
            "command": "compile and run the 15 official tests/unittest.sh variants; compare official baseline_*.txt",
            "discovered": len(self._upstream_cases),
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        if reason:
            result["reason"] = reason
        print(f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(result)}")

    def _run_upstream_tests(self):
        root = self._upstream_source()
        tests_dir = os.path.join(root, "tests")
        output_dir = os.path.join(self.build_folder, "upstream-results")
        mkdir(self, output_dir)
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compiler_executables.get("c", "clang")
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        passed = 0

        for index, (name, source, defines, baseline) in enumerate(self._upstream_cases, start=1):
            executable = os.path.join(output_dir, f"upstream_{name}")
            actual = os.path.join(output_dir, f"actual_{name}.txt")
            flags = " ".join(f"-D{item}" for item in defines)
            compile_cmd = " ".join(filter(None, [
                shlex.quote(str(cc)), "-Wall", flags,
                shlex.quote(os.path.join(root, "ini.c")),
                shlex.quote(os.path.join(tests_dir, source)),
                "-o", shlex.quote(executable),
            ]))
            try:
                self.run(compile_cmd)
                # NOTE: OHOS kernel cwd handling is fragile — avoid shell `cd`
                # in subprocesses; use Conan's built-in cwd parameter instead.
                run_cmd = f"{shlex.quote(executable)} > {shlex.quote(actual)}"
                if self.settings.os == "OHOS":
                    self.run(f"{shlex.quote(bash)} -c {shlex.quote(run_cmd)}", cwd=tests_dir)
                else:
                    self.run(run_cmd, cwd=tests_dir)
                with open(os.path.join(tests_dir, baseline), "rb") as expected_file:
                    expected = expected_file.read()
                with open(actual, "rb") as actual_file:
                    observed = actual_file.read()
                if not expected or observed != expected:
                    raise ConanException(
                        f"official upstream case {name} output differs from {baseline}"
                    )
                passed += 1
            except Exception as exc:
                self._emit_upstream(
                    "failed", index, passed, 1,
                    len(self._upstream_cases) - index,
                    f"{name}: {exc}",
                )
                raise

        self._emit_upstream("passed", len(self._upstream_cases), passed, 0, 0)

    def test(self):
        # OHOS: /system/bin/sh (mksh) cannot exec ELF binaries.
        # Use bash to wrap binary execution.
        if self.settings.os == "OHOS":
            bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
            cmd = f"{bash} -c './test_inih'"
        else:
            cmd = "./test_inih"

        rc = self.run(cmd, env="conanrun")
        passed = (rc == 0)

        # Emit HMBS evidence markers for preflight verification
        test_package_result = {
            "executed": True,
            "passed": passed,
            "command": cmd,
        }
        print(f"\nHMBS_TEST_PACKAGE_RESULT={json.dumps(test_package_result)}")

        if not passed:
            raise ConanException(f"consumer test failed, rc={rc}")

        self._run_upstream_tests()
