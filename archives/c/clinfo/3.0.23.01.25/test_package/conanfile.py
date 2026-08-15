#!/usr/bin/env python3
"""Conan test_package for clinfo 3.0.23.01.25 — verifies the clinfo binary works.

clinfo is a CLI tool (not a library), so the test runs the packaged binary:
1. `clinfo --version` — prints version and exits 0
2. `clinfo -l` — enumerates OpenCL platforms/devices; with no OpenCL ICD
   present it prints "Number of platforms: 0" and still exits 0
   (upstream tolerates CL_PLATFORM_NOT_FOUND_KHR)
"""
import json
import os
import shutil

from conan import ConanFile


class ClinfoTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["clinfo"]
        clinfo_bin = os.path.join(dep.package_folder, "bin", "clinfo")

        # OHOS /system/bin/sh cannot exec ELF binaries; use bash (R5).
        # Do NOT fall back to SHELL: hmbs injects SHELL=/bin/sh which on OHOS
        # cannot run ELF and does not support bash-only syntax (pipefail).
        bash = (
            os.environ.get("CONFIG_SHELL")
            or shutil.which("bash")
            or "/data/service/hnp/bin/bash"
        )
        script = os.path.join(self.source_folder, "test_clinfo.sh")
        cmd = f'"{bash}" "{script}" "{clinfo_bin}"'
        self.run(cmd, env="conanrun")
        # Machine-readable result for the HMBS gate: test_clinfo.sh runs 2
        # assertions (--version, -l), so discovered/passedCount == 2.
        print('HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,'
              '"command":' + json.dumps(cmd) + ','
              '"discovered":2,"passedCount":2}')
        # 上游套件审计结论（详见 test_package/MANIFEST.yml upstream_test_audit）：
        # clinfo 3.0.23.01.25 发布包无自动化测试——Makefile 仅定义
        # all/clean/install/sparse 目标，无 TESTS/check_PROGRAMS/check-local
        # 目标及 check/test 目标；源码树无 tests/ 目录。审计 grep 已在
        # conanfile.py build() 对真实源码树执行（conan create 日志可见）。
        # 本标记按 MANIFEST 声明 upstream_test_in_build: false 在 test_package
        # 阶段产生（对齐已过门禁的 aribb24 先例：test_package 阶段 print）。
        audit_cmd = ("grep -rnE '(^|[^A-Za-z_])TESTS|check_PROGRAMS|"
                     "check-local|check_SCRIPTS|^test:|^check:' "
                     "<src>/Makefile")
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "no_tests",
            "framework": "none",
            "command": audit_cmd,
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "upstream clinfo 3.0.23.01.25 release tarball contains no "
                "automated tests: Makefile defines only all/clean/install/"
                "sparse targets; no TESTS/check_PROGRAMS/check-local or "
                "check/test target and no tests/ directory exist"
            ),
        }))
