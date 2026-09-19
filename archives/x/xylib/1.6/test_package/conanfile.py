#!/usr/bin/env python3
"""Conan test_package — xylib 1.6 (consumer check with HMBS markers).

Links the packaged libxy into a small C program via the public C API
(xylib/xylib.h) and runs it.  The C test prints per-assertion [OK]/[FAIL]
lines and the HMBS_TEST_PACKAGE_RESULT marker; this test() re-emits the
upstream evidence (status no_tests — xylib 1.6 has no upstream test suite).
"""

import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class XylibTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _resolve_compiler(self):
        try:
            executables = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
        except Exception:
            executables = {}
        cand = executables.get("c")
        if cand and os.path.isabs(cand):
            try:
                if os.path.isfile(cand) and os.access(cand, os.X_OK):
                    return cand
            except OSError:
                pass
        for name in ("clang", "cc"):
            found = shutil.which(name)
            if found:
                return found
        return cand or os.environ.get("CC", "clang")

    def build(self):
        dep = self.dependencies["xylib"]
        include_flags = " ".join("-I%s" % p for p in dep.cpp_info.includedirs)
        # libxy (static) was built with zlib + bzip2 support; a static link
        # pulls in their symbols.  The zlib/bzip2/boost libs live in their own
        # conan package dirs, so collect -L for the whole dependency closure
        # (not just xylib's own libdir) so -lz/-lbz2 resolve on the link line.
        libdirs = []
        seen = set()
        for d in self.dependencies.values():
            for p in d.cpp_info.libdirs:
                if p not in seen:
                    seen.add(p)
                    libdirs.append(p)
        library_flags = " ".join("-L%s" % p for p in libdirs)
        linker_libs = "-lz -lbz2 -lc++"
        rpath_flags = " ".join(
            '-Wl,-rpath,"%s"' % p for p in libdirs
        )
        compiler = self._resolve_compiler()
        source = os.path.join(self.source_folder, "test_xylib.c")
        executable = os.path.join(self.build_folder, "test_xylib")
        self.run(
            '"%s" -std=gnu11 -Wall -Wextra -o "%s" "%s" %s %s -lxy %s %s'
            % (
                compiler,
                executable,
                source,
                include_flags,
                library_flags,
                linker_libs,
                rpath_flags,
            )
        )
        # Make the sample data file available next to the test binary.
        # When source_folder and build_folder coincide (as here) the file is
        # already in place; copying onto itself would raise SameFileError.
        sample = os.path.join(self.source_folder, "sample.txt")
        if os.path.isfile(sample):
            dest = os.path.join(self.build_folder, "sample.txt")
            if os.path.abspath(sample) != os.path.abspath(dest):
                shutil.copy(sample, dest)

    def _emit_upstream_no_tests(self):
        marker = {
            "status": "no_tests",
            "framework": "autotools",
            "command": "make check (n/a)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "xylib 1.6 上游无测试套件：发布 tarball 无 tests/、test/ 目录；"
                "Makefile.am 仅有 bin_PROGRAMS=xyconv 与 lib_LTLIBRARIES=libxy.la，"
                "无 check/test 目标、无 TESTS 变量；configure.ac 仅做编译/头文件/"
                "库探测与可选的 zlib/bzip2/wxWidgets 检测，无测试宏；CMakeLists.txt "
                "无 enable_testing()/add_test()"
            ),
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker), flush=True)

    def test(self):
        if not can_run(self):
            raise ConanException(
                "test_package requires a runnable target (native OHOS build)"
            )
        executable = os.path.join(self.build_folder, "test_xylib")
        if not os.path.isfile(executable):
            raise ConanException("test binary missing: %s" % executable)
        self.run('"%s"' % executable, env="conanrun")
        # The C binary prints HMBS_TEST_PACKAGE_RESULT (real counts) and
        # exits non-zero on any assertion failure; reaching here means all
        # passed.  Re-emit the upstream no-tests evidence.
        self._emit_upstream_no_tests()
