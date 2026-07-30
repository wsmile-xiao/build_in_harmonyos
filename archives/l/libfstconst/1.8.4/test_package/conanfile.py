#!/usr/bin/env python3
"""Conan test_package - libfstconst 1.8.4."""
import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run


class LibfstconstTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["libfstconst"]
        lib_dir = os.path.join(dep.package_folder, "lib")
        header = os.path.join(dep.package_folder, "include", "fst", "const-fst.h")
        lib_candidates = [
            os.path.join(lib_dir, name)
            for name in ("libfstconst.so", "libfstconst.dylib", "libfstconst.a")
        ]
        libfstconst = next((p for p in lib_candidates if os.path.exists(p)), lib_candidates[0])

        if not can_run(self):
            for path in (header, libfstconst):
                if not os.path.exists(path):
                    raise Exception(f"Missing packaged artifact: {path}")
            self.output.info("Cross-building; file layout check completed")
            print("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,\"command\":\"file layout check\"}")
            return

        script = os.path.join(self.source_folder, "check_libfstconst.sh")
        # E087/E182: HMDFS 不支持 chmod，脚本文件无执行位，直接执行会被 shell 拒绝 (Error 126)。
        # 用 `sh <script>` 显式调解释器执行，绕过执行位检查。
        self.run(
            f"sh {shlex.quote(script)} {shlex.quote(libfstconst)} {shlex.quote(header)}",
            env="conanrun",
        )

        # 上游测试接入（src/test/Makefile.am 定义 7 个 check_PROGRAMS）。
        # 配方 build() 已编译 7 个测试程序并随包安装到 _ohos_tests/。
        # 真机逐个执行，按退出码统计通过/失败，最后输出 HMBS_UPSTREAM_TEST_RESULT 标记。
        # 用 try/except 捕获 self.run 异常（非 0 退出码），失败计 failed 继续循环，确保标记总是打印。
        tests_dir = os.path.join(dep.package_folder, "_ohos_tests")
        test_names = [
            "fst_test", "weight_test",
            "algo_test_log", "algo_test_tropical", "algo_test_minmax",
            "algo_test_lexicographic", "algo_test_power",
        ]
        discovered = len(test_names)
        executed = 0
        passed = 0
        failed = 0
        skipped = 0
        commands = []
        for name in test_names:
            tp = os.path.join(tests_dir, name)
            if not os.path.exists(tp):
                skipped += 1
                continue
            cmd = f"{tp} {name}"
            commands.append(cmd)
            try:
                # 测试程序需参数（SET_FLAGS 解析 argv[0]），传名字即可。退出码 0 = 通过。
                self.run(cmd, env="conanrun")
                executed += 1
                passed += 1
            except Exception:
                executed += 1
                failed += 1
        status = "passed" if failed == 0 and skipped == 0 else ("partial" if passed > 0 else "failed")
        command_str = "; ".join(commands) if commands else "make check"
        print(
            'HMBS_UPSTREAM_TEST_RESULT={"status":"%s","framework":"autotools",'
            '"command":"%s","discovered":%d,"executed":%d,"passed":%d,'
            '"failed":%d,"skipped":%d}'
            % (status, command_str, discovered, executed, passed, failed, skipped)
        )
