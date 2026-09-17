#!/usr/bin/env python3
"""Conan test_package for inih-inireader 62.

Layer 1 (upstream official tests): the pinned r62 tarball is fetched and the
official suite is reproduced byte-for-byte —
  * tests/unittest.sh: 15 compile/run cases compared with baseline_*.txt
  * examples/INIReaderExample.cpp + INIReaderExampleErrors.cpp compared with
    cpptest.txt / cpptesterrors.txt

Layer 2 (consumer): test_inih_inireader.cpp includes <ini.h> and
<INIReader.h> through the installed package and asserts real parser behaviour
(R34).

Both layers print HMBS evidence markers consumed by CI preflight.
"""
import json
import os
import shutil
import shlex

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import download, mkdir, unzip

_UPSTREAM_URL = "https://github.com/benhoyt/inih/archive/refs/tags/r62.tar.gz"
_UPSTREAM_SHA256 = "9c15fa751bb8093d042dae1b9f125eb45198c32c6704cd5481ccde460d4f8151"

# tests/unittest.sh / tests/meson.build: (name, source, defines, baseline)
_C_CASES = (
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

# examples/cpptest.sh: (name, source, baseline)
_CPP_CASES = (
    ("INIReaderExample", "INIReaderExample.cpp", "cpptest.txt"),
    ("INIReaderExampleErrors", "INIReaderExampleErrors.cpp", "cpptesterrors.txt"),
)


class InihInireaderTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        # CMake on OHOS has no Platform/HarmonyOS.cmake.
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])

    # ── helpers ──────────────────────────────────────────────────────────
    def _bash(self):
        for candidate in (
            os.environ.get("CONFIG_SHELL"),
            shutil.which("bash"),
            "/storage/Users/currentUser/.harmonybrew/bin/bash",
            "/data/service/hnp/bin/bash",
            "/bin/bash",
        ):
            if candidate and os.path.isfile(candidate):
                return candidate
        return "bash"

    def _run_binary(self, binary):
        direct = shlex.quote(binary)
        if self.settings.os == "OHOS":
            bash = self._bash()
            wrapped = f"{shlex.quote(bash)} -c {shlex.quote(direct)}"
            rc = self.run(wrapped, env="conanrun", ignore_errors=True)
            if rc == 0:
                return rc
        return self.run(direct, env="conanrun", ignore_errors=True)

    def _upstream_source(self):
        root = os.path.join(self.build_folder, "upstream-r62")
        if not os.path.isfile(os.path.join(root, "ini.c")):
            mkdir(self, root)
            tarball = os.path.join(self.build_folder, "upstream-r62.tar.gz")
            download(self, url=_UPSTREAM_URL, filename=tarball,
                     sha256=_UPSTREAM_SHA256, verify=True)
            unzip(self, tarball, destination=root, strip_root=True)
        return root

    def _emit_upstream(self, status, executed, passed, failed, skipped, reason=None):
        result = {
            "status": status,
            "framework": "inih r62 unittest.sh + INIReader examples baseline suite",
            "command": "reproduce 15 unittest.sh cases and 2 INIReader examples; compare against baselines",
            "discovered": len(_C_CASES) + len(_CPP_CASES),
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        if reason:
            result["reason"] = reason
        print(f"\nHMBS_UPSTREAM_TEST_RESULT={json.dumps(result)}")

    def _compare(self, actual, expected_path, label, name):
        with open(expected_path, "rb") as handle:
            expected = handle.read()
        with open(actual, "rb") as handle:
            observed = handle.read()
        if not expected or observed != expected:
            raise ConanException(f"upstream case {name} output differs from {label}")

    def _run_upstream_tests(self):
        root = self._upstream_source()
        tests_dir = os.path.join(root, "tests")
        examples_dir = os.path.join(root, "examples")
        output_dir = os.path.join(self.build_folder, "upstream-results")
        mkdir(self, output_dir)
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = str(executables.get("c") or "clang")
        cxx = str(executables.get("cpp") or "clang++")
        note_script = ""

        def run_in(cwd, exe, actual):
            redirect = f"{shlex.quote(exe)} > {shlex.quote(actual)}"
            if self.settings.os == "OHOS":
                bash = self._bash()
                self.run(f"{shlex.quote(bash)} -c {shlex.quote(redirect)}", cwd=cwd)
            else:
                self.run(redirect, cwd=cwd)

        total = len(_C_CASES) + len(_CPP_CASES)
        passed = 0
        try:
            for name, source, defines, baseline in _C_CASES:
                exe = os.path.join(output_dir, f"unittest_{name}")
                actual = os.path.join(output_dir, f"actual_{name}.txt")
                flags = " ".join(f"-D{d}" for d in defines)
                self.run(" ".join(filter(None, [
                    shlex.quote(cc), "-Wall", flags,
                    shlex.quote(os.path.join(root, "ini.c")),
                    shlex.quote(os.path.join(tests_dir, source)),
                    "-o", shlex.quote(exe),
                ])))
                run_in(tests_dir, exe, actual)
                self._compare(actual, os.path.join(tests_dir, baseline), baseline, name)
                passed += 1

            for name, source, baseline in _CPP_CASES:
                exe = os.path.join(output_dir, f"example_{name}")
                actual = os.path.join(output_dir, f"actual_{name}.txt")
                self.run(" ".join([
                    shlex.quote(cxx), "-Wall", "-std=c++11",
                    "-I", shlex.quote(root), "-I", shlex.quote(os.path.join(root, "cpp")),
                    shlex.quote(os.path.join(root, "cpp", "INIReader.cpp")),
                    shlex.quote(os.path.join(root, "ini.c")),
                    shlex.quote(os.path.join(examples_dir, source)),
                    "-o", shlex.quote(exe),
                ]))
                run_in(examples_dir, exe, actual)
                self._compare(actual, os.path.join(examples_dir, baseline), baseline, name)
                passed += 1
        except Exception as exc:  # noqa: BLE001 - surface as upstream failure
            self._emit_upstream("failed", passed + 1, passed, 1, total - passed - 1,
                                reason=str(exc)[:400])
            raise

        self._emit_upstream("passed", total, passed, 0, 0)

    # ── consumer layer ───────────────────────────────────────────────────
    def test(self):
        binary = os.path.join(self.cpp.build.bindirs[0], "test_inih_inireader")
        rc = self._run_binary(binary)
        passed = (rc == 0)
        print("\nHMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": passed,
            "command": "test_inih_inireader",
        }))
        if not passed:
            raise ConanException(f"consumer test failed, rc={rc}")

        self._run_upstream_tests()
