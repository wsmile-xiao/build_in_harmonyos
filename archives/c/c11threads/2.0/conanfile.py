#!/usr/bin/env python3
"""Conan recipe — c11threads 2.0 (header-only C11 threads over pthreads)."""

import json
import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class C11ThreadsConan(ConanFile):
    name = "c11threads"
    version = "2.0"
    description = "Trivial C11 threads.h implementation over POSIX threads (header-only)"
    license = "Public Domain"
    homepage = "https://github.com/jtsiomb/c11threads"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "c11threads pthreads wrapper supports Linux and OHOS only "
                "(the win32 backend c11threads_win32.c is not packaged)")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # The library itself is header-only (static inline wrappers), so the
        # build phase exists to compile and run the upstream test program.
        self._build_and_run_upstream_tests()

    def _build_and_run_upstream_tests(self):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict)
        cc = compiler_executables.get("c", "clang")
        test_dir = os.path.join(self.source_folder, "test")
        # Keep upstream CFLAGS untouched (-std=gnu11 -pedantic -Wall -g -I..):
        # only CC is injected, taken from the Conan toolchain conf (R33).
        command = "make -C {} -j1 CC={}".format(
            shlex.quote(test_dir), shlex.quote(cc))
        self.run(command)
        # Upstream test program: aborts on any failed assertion, exit 0 = pass.
        self.run(os.path.join(test_dir, "test"))
        result = {
            "status": "passed",
            "framework": "makefile-program",
            "command": "make -C test -j1 CC=clang && ./test/test",
            "discovered": 1,
            "executed": 1,
            "passed": 1,
            "failed": 0,
            "skipped": 0,
            "detail": "upstream registers a single test program target (test/Makefile: test); "
                      "the program internally runs 5 functional test groups (thread "
                      "create/join, timed mutex, condvar, TSS, call_once) with 61 "
                      "assertions, each aborting on failure, on the OHOS musl pthreads "
                      "backend",
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False))

    def package(self):
        copy(self, "c11threads.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        # The project ships no separate LICENSE file; the public-domain grant
        # lives in README.md and at the top of the header itself.
        copy(self, "README.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        # Header-only: no build output, single package_id for all profiles.
        self.info.clear()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "c11threads")
        self.cpp_info.set_property("cmake_target_name", "c11threads::c11threads")
