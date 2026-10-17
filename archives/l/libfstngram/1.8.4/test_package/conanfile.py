#!/usr/bin/env python3
"""Conan test_package - libfstngram 1.8.4."""
import os
import shlex
import tempfile

from conan import ConanFile
from conan.tools.build import can_run


class LibfstngramTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    # 上游 src/test/ 用例面（N=10，口径见 ../notes.md）：7 个注册用例 + 3 个同源
    # algo_test.cc 未注册宏分支，配方 build() 已全部编译并随包安装到 _ohos_tests/。
    upstream_tests = [
        "fst_test",
        "weight_test",
        "algo_test_log",
        "algo_test_tropical",
        "algo_test_minmax",
        "algo_test_lexicographic",
        "algo_test_power",
        "algo_test_left_string",
        "algo_test_right_string",
        "algo_test_gallic",
    ]

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _build_and_run_consumer(self, dep):
        """链接并运行 ngram_consumer.cc（对着已安装的产物，不是构建树）。"""
        cxx = os.environ.get("CXX") or "clang++"
        pkg = dep.package_folder
        lib_dir = os.path.join(pkg, "lib")
        core = next(
            (os.path.join(lib_dir, n) for n in ("libfst.a", "libfst.so", "libfst.dylib")
             if os.path.exists(os.path.join(lib_dir, n))),
            None,
        )
        if core is None:
            raise Exception(f"Missing packaged core library in {lib_dir}")
        ext = next(
            (os.path.join(lib_dir, n)
             for n in ("libfstngram.a", "libfstngram.so", "libfstngram.so.26",
                       "libfstngram.dylib")
             if os.path.exists(os.path.join(lib_dir, n))),
            None,
        )
        if ext is None:
            raise Exception(f"Missing packaged libfstngram in {lib_dir}")
        src = os.path.join(self.source_folder, "ngram_consumer.cc")
        # 编译产物落 TMPDIR（= $WORKSPACE_ROOT/tmp），不落 worktree，避免未跟踪垃圾。
        workdir = tempfile.mkdtemp(prefix="libfstngram-consumer-")
        out = os.path.join(workdir, "ngram_consumer")
        cmd = " ".join(
            shlex.quote(w) for w in [
                cxx,
                f"-I{os.path.join(pkg, 'include')}",
                "-stdlib=libc++",
                "-std=c++17",
                "-fno-exceptions",
                "-Wno-deprecated-declarations",
                "-O2",
                src,
                ext,
                core,
                "-lm",
                "-ldl",
                "-o",
                out,
            ]
        )
        self.output.info(f"Building libfstngram consumer: {cxx}")
        self.run(cmd, env="conanrun")
        self.run(shlex.quote(out), env="conanrun")

    def test(self):
        dep = self.dependencies["libfstngram"]
        lib_dir = os.path.join(dep.package_folder, "lib")
        header = os.path.join(
            dep.package_folder, "include", "fst", "extensions", "ngram", "ngram-fst.h"
        )
        lib_candidates = [
            os.path.join(lib_dir, name)
            for name in (
                "libfstngram.so",
                "libfstngram.so.26",
                "libfstngram.dylib",
                "libfstngram.a",
            )
        ]
        libfstngram = next((p for p in lib_candidates if os.path.exists(p)), lib_candidates[0])

        if not can_run(self):
            for path in (header, libfstngram):
                if not os.path.exists(path):
                    raise Exception(f"Missing packaged artifact: {path}")
            self.output.info("Cross-building; file layout check completed")
            print("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,\"command\":\"file layout check\"}")
            return

        script = os.path.join(self.source_folder, "check_libfstngram.sh")
        # E087/E182: HMDFS 不支持 chmod，脚本文件无执行位，直接执行会被 shell 拒绝 (Error 126)。
        # 用 `sh <script>` 显式调解释器执行，绕过执行位检查。
        self.run(
            f"sh {shlex.quote(script)} {shlex.quote(libfstngram)} {shlex.quote(header)}",
            env="conanrun",
        )

        # 真跑消费者：把 ngram_consumer.cc 链接到**已安装**的 libfstngram 产物上并运行。
        # BitmapIndex::Rank1/Select1 的实现在 bitmap-index.o、NGramFst 的注册在 ngram-fst.o
        # （头文件只是 inline 模板），因此链接 + 运行才算真的验证了交付的库文件。
        self._build_and_run_consumer(dep)

        # 上游测试接入（src/test/Makefile.am 的 check_PROGRAMS + 同源未注册宏分支）。
        # 配方 build() 已编译 10 个测试程序并随包安装到 _ohos_tests/。
        # 真机逐个执行，按退出码统计通过/失败，最后输出 HMBS_UPSTREAM_TEST_RESULT 标记。
        # 用 try/except 捕获 self.run 异常（非 0 退出码），失败计 failed 继续循环，确保标记总是打印。
        tests_dir = os.path.join(dep.package_folder, "_ohos_tests")
        discovered = len(self.upstream_tests)
        executed = 0
        passed = 0
        failed = 0
        skipped = 0
        commands = []
        for name in self.upstream_tests:
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
