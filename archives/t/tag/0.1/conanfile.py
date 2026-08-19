#!/usr/bin/env python3
"""Conan recipe — tag 0.1 (Makefile)

mafintosh/tag — a small C program that tags messages piped to stdin:
prefixes every line with a stamp (message, %d date, %h hostname, %l line
number). A single `tag` executable is built from src/tag.c by the upstream
Makefile; there is no library output.

Upstream test audit: the 0.1.0 archive ships only Makefile (all/install/
uninstall/clean targets — no check/test target), README.md, package.json
(no test script field) and src/tag.c (a single main() program, no test
code). No upstream tests exist, so HMBS_UPSTREAM_TEST_RESULT is reported as
no_tests right after the build (airspy precedent).
"""
import json
import os

from conan import ConanFile
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout


class TagConan(ConanFile):
    name = "tag"
    version = "0.1"
    description = ("Tag streams of data - a small C program that tags "
                   "messages piped to stdin")
    license = "MIT"
    homepage = "https://github.com/mafintosh/tag"
    url = "https://github.com/mafintosh/tag"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: resolve the C compiler from the Conan toolchain, never from
        # bare ${CC} env vars (empty on CI workers). R9: single job.
        # Conan 2: tools.build:compiler_executables is a dict conf — read the
        # whole dict, then pick the "c" entry (sub-key form throws
        # "does not exist in configuration list").
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        # 上游 tag 无 configure 步骤，Makefile 只存在于源码根目录；Conan 2
        # basic_layout 把 build_folder 与 source_folder 分离，必须在 source
        # 目录内 in-source 执行 make（aa3d/accrete 先例）。
        self.run(f"make CC={cc} -j1", cwd=self.source_folder)
        # Upstream ships no test suite (audit in test_package/MANIFEST.yml);
        # report no_tests with the concrete audit conclusion for the HMBS
        # upstream-test evidence gate.
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "no_tests",
            "framework": "makefile",
            "command": "make check (n/a)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "mafintosh/tag 0.1.0 无测试套件：归档仅含 Makefile(all/install/"
                      "uninstall/clean，无 check/test 目标)、README.md、package.json"
                      "(无 test 脚本)与 src/tag.c(单 main() 程序，无测试代码)，无 tests/ 目录",
        }, ensure_ascii=False), flush=True)

    def package(self):
        # Upstream `make install` relies on the `install` utility which may be
        # missing on OHOS; copy the freshly built binary directly instead.
        # Build happens in-source, so the binary lives in source_folder.
        copy(self, "tag", self.source_folder,
             os.path.join(self.package_folder, "bin"))

    def package_info(self):
        # Command-line tool: expose bin/, no libraries.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
