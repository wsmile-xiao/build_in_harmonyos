#!/usr/bin/env python3
"""Conan test_package - libfstlookahead 1.8.4."""
import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class LibfstlookaheadTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _artifact_paths(self, dep):
        lib_dir = os.path.join(dep.package_folder, "lib")
        lib_names = ("libfstlookahead.so", "libfstlookahead.dylib", "libfstlookahead.a")
        lib = next(
            (os.path.join(lib_dir, n) for n in lib_names if os.path.exists(os.path.join(lib_dir, n))),
            os.path.join(lib_dir, lib_names[0]),
        )
        include_dir = os.path.join(dep.package_folder, "include")
        return lib, os.path.join(include_dir, "fst", "lookahead-matcher.h"), \
            os.path.join(include_dir, "fst", "matcher-fst.h"), lib_dir

    def _compile_and_run_consumer(self, lib, lib_dir, include_dir):
        # 鸿蒙侧消费者用例：用**包内已安装**的头文件与静态库现场编译，真机执行。
        # 链接用 --whole-archive 包夹：LookAheadFst 注册器是 libfstlookahead.a 里的静态对象，
        # 无强引用会被链接器剔除，注册表查不到 arc_lookahead/ilabel_lookahead/olabel_lookahead。
        cxx = os.environ.get("CXX") or shutil.which("clang++") or "/data/service/hnp/bin/clang++"
        src = os.path.join(self.source_folder, "lookahead_consumer.cc")
        out = os.path.join(self.build_folder, "lookahead_consumer")
        out_fst = os.path.join(self.build_folder, "lookahead_consumer_roundtrip.fst")

        static_libs = [p for p in (lib, os.path.join(lib_dir, "libfst.a")) if p.endswith(".a") and os.path.exists(p)]
        if static_libs:
            ldflags = ["-Wl,--whole-archive"] + static_libs + ["-Wl,--no-whole-archive", "-lm", "-ldl"]
        else:
            ldflags = [f"-L{lib_dir}", "-lfstlookahead", "-lfst", "-lm", "-ldl"]

        cmd = [cxx, f"-I{include_dir}", "-DHAVE_CONFIG_H", "-stdlib=libc++", "-std=c++17",
               "-fno-exceptions", "-Wno-deprecated-declarations", "-O2", src] + ldflags + ["-o", out]
        self.output.info(f"Compiling HarmonyOS consumer test: {cxx}")
        self.run(" ".join(shlex.quote(w) for w in cmd), env="conanrun")
        self.run(f"{shlex.quote(out)} {shlex.quote(out_fst)}", env="conanrun")

    def _run_upstream_tests(self, dep):
        # 上游测试接入（src/test/Makefile.am 定义 7 个 check_PROGRAMS，TESTS = $(check_PROGRAMS)）。
        # 配方 build() 已编译 7 个测试程序并随包安装到 _ohos_tests/。
        # 真机逐个执行，按退出码统计通过/失败，最后输出 HMBS_UPSTREAM_TEST_RESULT 标记。
        # fst_test 的 TestIO 会向 FST_FLAGS_tmpdir 写文件（flags.cc 默认读 TMPDIR，回落 /tmp），
        # 设备 /tmp 只读；这里显式传 --tmpdir=<可写目录>，不依赖继承环境。
        tests_dir = os.path.join(dep.package_folder, "_ohos_tests")
        tmpdir = os.path.join(self.build_folder, "upstream-test-tmp")
        os.makedirs(tmpdir, exist_ok=True)
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
            cmd = f"{tp} --tmpdir={tmpdir}"
            commands.append(cmd)
            try:
                # 退出码 0 = 通过；CHECK 失败会 abort（非 0）。
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

    def test(self):
        dep = self.dependencies["libfstlookahead"]
        lib, matcher_header, matcher_fst_header, lib_dir = self._artifact_paths(dep)
        include_dir = os.path.join(dep.package_folder, "include")

        if not can_run(self):
            for path in (lib, matcher_header, matcher_fst_header):
                if not os.path.exists(path):
                    raise Exception(f"Missing packaged artifact: {path}")
            self.output.info("Cross-building; file layout check completed")
            print("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,"
                  "\"command\":\"file layout check\"}")
            return

        script = os.path.join(self.source_folder, "check_libfstlookahead.sh")
        # E087/E182: HMDFS 不支持 chmod，脚本文件无执行位，直接执行会被 shell 拒绝 (Error 126)。
        # 用 `sh <script>` 显式调解释器执行，绕过执行位检查。
        self.run(
            f"sh {shlex.quote(script)} {shlex.quote(lib)} {shlex.quote(matcher_header)} "
            f"{shlex.quote(matcher_fst_header)}",
            env="conanrun",
        )

        self._compile_and_run_consumer(lib, lib_dir, include_dir)
        self._run_upstream_tests(dep)
