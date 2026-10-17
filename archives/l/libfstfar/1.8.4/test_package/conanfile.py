#!/usr/bin/env python3
"""Conan test_package - libfstfar 1.8.4.

真机消费者测试（不是空壳）：
  1. 用 clang++ 编译并链接一个**真正调用 libfstfar 导出符号**的 C++ 程序
     （fst::IsSTList / fst::IsSTTable 定义在 extensions/far/stlist.cc、sttable.cc），
     再用 FAR 公共 API 做 STList 档案的写入/读回比对；
  2. 跑本包安装的 far* 命令行工具做 端到端 档案往返（fstcompile → farcreate → farinfo →
     farextract → fstprint）；
  3. 跑配方随包安装的 10 个上游测试用例（父 tarball 清点面，见 notes.md）。
三段各自输出机器可读的 HMBS_* 标记。**三段全部执行完再统一判定**：某一段失败不会
掩盖其余段落的证据，但任一段失败都让 test_package 以非零退出。
"""
import os
import shlex
import shutil
import tempfile

from conan import ConanFile
from conan.tools.build import can_run


class LibfstfarTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _layout(self, dep):
        pkg = dep.package_folder
        inc = os.path.join(pkg, "include")
        libdir = os.path.join(pkg, "lib")
        bindir = os.path.join(pkg, "bin")
        headers = [
            os.path.join(inc, "fst", "extensions", "far", name)
            for name in ("far.h", "stlist.h", "sttable.h", "far-class.h", "farlib.h")
        ]
        libs = [
            os.path.join(libdir, name)
            for name in ("libfstfar.so", "libfstfar.dylib", "libfstfar.a")
        ]
        lib = next((p for p in libs if os.path.exists(p)), libs[0])
        return inc, libdir, bindir, headers, lib

    def test(self):
        dep = self.dependencies["libfstfar"]
        inc, libdir, bindir, headers, libfstfar = self._layout(dep)
        section_errors = []

        if not can_run(self):
            missing = [p for p in headers + [libfstfar] if not os.path.exists(p)]
            if missing:
                raise Exception(f"Missing packaged artifact: {missing}")
            self.output.info("Cross-building; file layout check completed")
            print("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,\"command\":\"file layout check\"}")
            return

        # ---- 1) HarmonyOS consumer: compile + link + run against the packaged lib ----
        cxx = shutil.which("clang++") or "clang++"
        src = os.path.join(self.source_folder, "test_libfstfar.cc")
        # 中间产物落地方：**不要**写进 test_package 源目录（conan create 时
        # `build_folder` 就是 test_package 目录本身，写进去会污染被审 worktree）。
        # 优先用 TMPDIR 下的私有临时目录；设备 /tmp 只读，故再回退到 build 目录。
        base = os.environ.get("TMPDIR") or os.environ.get("TEMP") or tempfile.gettempdir()
        try:
            os.makedirs(base, exist_ok=True)
            workdir = tempfile.mkdtemp(prefix="libfstfar-test-", dir=base)
        except OSError:
            workdir = os.path.join(self.build_folder or ".", "_consumer")
            os.makedirs(workdir, exist_ok=True)
        archive = os.path.join(workdir, "consumer.far")
        app = os.path.join(workdir, "test_libfstfar")

        # 静态 libfst.a 必须 whole-archive 包夹，否则 fst-types.o 的 REGISTER_FST 静态
        # registerer 被链接器剔除 -> 注册表空 -> Fst::Read 回退 dlopen 失败（见 conanfile.py 注释）。
        shared = libfstfar.endswith((".so", ".dylib"))
        if shared:
            # 动态形态：直接链 libfstfar/libfst，并给消费者二进制打上**包内** lib 的 rpath
            # （不依赖 conanrun 的 LD_LIBRARY_PATH，也便于事后独立复核该二进制）。
            link = f"-L{shlex.quote(libdir)} -Wl,-rpath,{shlex.quote(libdir)} -lfstfar -lfst"
        else:
            libfst_a = os.path.join(libdir, "libfst.a")
            link = (
                f"-L{shlex.quote(libdir)} -lfstfar "
                f"-Wl,--whole-archive {shlex.quote(libfst_a)} -Wl,--no-whole-archive"
            )
        build_cmd = (
            f"{shlex.quote(cxx)} -std=c++17 -stdlib=libc++ -O2 "
            f"-I{shlex.quote(inc)} {shlex.quote(src)} {link} -lm -ldl -o {shlex.quote(app)}"
        )
        try:
            self.output.info(f"[1/3] Building HarmonyOS consumer: {build_cmd}")
            self.run(build_cmd, env="conanrun")
            self.run(f"{shlex.quote(app)} {shlex.quote(archive)}", env="conanrun")
        except Exception as exc:  # noqa: BLE001 - 收集后统一在末尾判定
            section_errors.append(f"[1/3] consumer build/run failed: {exc}")

        # ---- 2) packaged far* CLI tools: end-to-end archive round trip ----
        # 本包按 `--disable-bin` 构建（子库交付面：只有 libfstfar + FAR 头文件；fst::script
        # 与命令行工具属 openfst 主包）⇒ 包里没有 far*/fst* 可执行文件。此时本段**记为
        # NOT_RUN 并显式打印标记**，不当成通过、也不当成失败（见 MANIFEST.yml 与 notes.md）。
        script = os.path.join(self.source_folder, "check_libfstfar.sh")
        have_cli = os.path.exists(os.path.join(bindir, "farcreate"))
        if not have_cli:
            self.output.info("[2/3] SKIPPED (NOT_RUN): --disable-bin 构建不含命令行工具")
            print(
                'HMBS_CLI_CHECKS_NOT_RUN={"executed":false,"not_run":8,'
                '"reason":"recipe builds with --disable-bin: libfstfar ships no CLI tools '
                '(fst::script / far*/fst* tools are provided by openfst/1.8.4)"}'
            )
        else:
            # E087/E182: HMDFS 不支持 chmod，脚本文件无执行位，直接执行会被 shell 拒绝 (Error 126)。
            # 用 `sh <script>` 显式调解释器执行，绕过执行位检查。
            try:
                self.output.info("[2/3] Running packaged far* CLI round trip")
                self.run(
                    f"sh {shlex.quote(script)} {shlex.quote(libdir)} {shlex.quote(inc)} "
                    f"{shlex.quote(bindir)} {shlex.quote(workdir)}",
                    env="conanrun",
                )
            except Exception as exc:  # noqa: BLE001
                section_errors.append(f"[2/3] far* CLI round trip failed: {exc}")

        # ---- 3) upstream test cases (10) shipped inside the package ----
        # 上游注册面（src/test/Makefile.am）：check_PROGRAMS = fst_test weight_test
        #   + algo_test_{log,tropical,minmax,lexicographic,power}；TESTS = $(check_PROGRAMS) -> 7。
        # 用例分支面（src/test/algo_test.cc:66-89 的 8 个 TEST_* 分支）+ 2 个独立程序 -> 10。
        # 主 N 取最大值 10（3 个未注册分支 left_string/right_string/gallic 也一并执行，见 notes.md）。
        # 配方 build() 已编译并随包安装到 _ohos_tests/。逐个 try/except 捕获非 0 退出码，
        # 失败计 failed 后继续，确保 HMBS_UPSTREAM_TEST_RESULT 标记总是打印。
        self.output.info("[3/3] Running packaged upstream test cases")
        tests_dir = os.path.join(dep.package_folder, "_ohos_tests")
        test_names = [
            "fst_test", "weight_test",
            "algo_test_log", "algo_test_tropical", "algo_test_minmax",
            "algo_test_lexicographic", "algo_test_power",
            "algo_test_left_string", "algo_test_right_string", "algo_test_gallic",
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
            cmd = f"{shlex.quote(tp)} {name}"
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

        # 三段全部跑完后统一判定：任一段失败都让整个 test_package 以非零退出（不许静默放过），
        # 但前面的失败不会阻止后两段执行与标记打印。
        if failed or skipped:
            section_errors.append(f"[3/3] upstream tests failed={failed} skipped={skipped}")
        if section_errors:
            raise Exception("libfstfar test_package failed: " + "; ".join(section_errors))
