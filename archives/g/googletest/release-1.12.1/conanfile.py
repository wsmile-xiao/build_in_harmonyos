#!/usr/bin/env python3
"""Conan recipe — googletest release-1.12.1 (cmake, 静态库)"""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import apply_conandata_patches, get
from conan.tools.cmake import CMakeToolchain, CMakeDeps, cmake_layout


class GoogletestConan(ConanFile):
    name = "googletest"
    version = "release-1.12.1"
    description = "Google C++ Testing and Mocking Framework (gtest/gmock)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/google/googletest"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        pass

    def layout(self):
        cmake_layout(self, src_folder=".")

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def _ohos_toolchain(self):
        # 自发现 OHOS NDK 的 ohos.toolchain.cmake（不依赖 profile host 段 user_toolchain）。
        import os
        import glob
        ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list)
        ndk = os.environ.get("OHOS_NDK_HOME", "")
        candidates = list(ut) + ([os.path.join(ndk, "build/cmake/ohos.toolchain.cmake")] if ndk else [])
        for cand in candidates:
            if cand and os.path.isfile(cand):
                return cand
        globbed = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake"))
        if globbed:
            return globbed[-1]
        raise ConanInvalidConfiguration(
            "找不到 ohos.toolchain.cmake：设 OHOS_NDK_HOME 或 profile [conf] user_toolchain")

    def _ohos_llvm_bin(self):
        """Derive LLVM bin directory from the OHOS toolchain path (draco E012 fix)."""
        import os
        import glob
        toolchain = self._ohos_toolchain()
        # toolchain: <ndk_root>/build/cmake/ohos.toolchain.cmake
        ndk_root = os.path.dirname(os.path.dirname(os.path.dirname(toolchain)))
        llvm_bin = os.path.join(ndk_root, "llvm", "bin")
        if os.path.isdir(llvm_bin):
            return llvm_bin
        for base in ["/data/service/hnp/ohos-sdk.org"]:
            pattern = os.path.join(base, "*", "ohos", "native", "llvm", "bin")
            matches = sorted(glob.glob(pattern))
            if matches:
                return matches[-1]
        return None

    def build(self):
        # lerc/glfw 同法：自发现 ohos.toolchain + 裸 cmake，绕开 conan_toolchain（ML-0035）。
        # googletest 只产静态库（libgtest*.a/libgmock*.a），BUILD_SHARED_LIBS=OFF 无需签名。
        # OHOS 上额外开启 gtest_build_tests/gmock_build_tests：把上游框架自测二进制也构建出来，
        # 并在 build() 内对「纯逻辑」自测二进制逐一签名+实跑，产出真实通过率
        # （death-test/fork 类用例以 gtest 过滤器排除，见 PR_BODY「验证结果」逐条说明）。
        import os
        apply_conandata_patches(self)
        toolchain = self._ohos_toolchain()
        bdir = os.path.join(self.build_folder, "build-ohos")
        shared = "ON" if self.options.shared else "OFF"
        is_ohos = str(self.settings.os) == "OHOS"
        defs = [
            '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(toolchain),
            "-DOHOS_ARCH=arm64-v8a",
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            "-DCMAKE_INSTALL_LIBDIR=lib",   # ohos.toolchain 64 位默认 lib64/，强制 lib/
            "-DBUILD_SHARED_LIBS={}".format(shared),
            "-DINSTALL_GTEST=ON",           # 安装 gtest/gtest_main/gmock/gmock_main + cmake config + pkg-config
            "-DBUILD_GMOCK=ON",             # 同时构建 GoogleMock
            "-Dgtest_build_tests=ON" if is_ohos else "-Dgtest_build_tests=OFF",
            "-Dgtest_build_samples=OFF",
            "-Dgmock_build_tests=ON" if is_ohos else "-Dgmock_build_tests=OFF",
        ]
        # E012: ohos.toolchain.cmake 以 INTERNAL/FORCE 覆写 CMAKE_AR 为 bare name
        # ("llvm-ar")，但 llvm-ar 不在默认 PATH 中 → 静态库归档报
        # "Error running link command: no such file or directory"（CI-036/018 复现）。
        # 用绝对路径 llvm-ar rcs 覆盖最高优先级规则（与 draco/1.5.7 同法）。
        llvm_bin = self._ohos_llvm_bin()
        if llvm_bin:
            llvm_bin = os.path.abspath(llvm_bin)
            ar = os.path.join(llvm_bin, "llvm-ar")
            ranlib = os.path.join(llvm_bin, "llvm-ranlib")
            defs.extend([
                '-DCMAKE_AR:FILEPATH="{}"'.format(ar),
                '-DCMAKE_RANLIB:FILEPATH="{}"'.format(ranlib),
                '-DCMAKE_CXX_CREATE_STATIC_LIBRARY="{} rcs <TARGET> <OBJECTS>"'.format(ar),
                '-DCMAKE_C_CREATE_STATIC_LIBRARY="{} rcs <TARGET> <OBJECTS>"'.format(ar),
            ])
        self.run('cmake -B "{}" -S "{}" {}'.format(bdir, self.source_folder, " ".join(defs)))
        # 先只构建库目标，保证出包/安装不受自测目标影响。
        self.run('cmake --build "{}" --target gtest gtest_main gmock gmock_main'.format(bdir))
        if is_ohos:
            self._build_run_gtest_selftests(bdir)

    # OHOS 上实跑的上游 googletest 框架自测二进制（纯逻辑子集）。
    # 说明：death-test/fork 类二进制（googletest-death-test-test / gtest-death-test_ex_* 等）
    # 与 python 驱动二进制（py_test）在 OHOS musl 无法运行（fork 受限，见 #7742 brpc 先例），
    # 故不在实跑列表；列表中个别含 fork 用例的二进制用 GTEST_SELFTEST_FILTER 排除相应用例。
    GTEST_SELFTEST_BINARIES = [
        # googletest/test
        "gtest_unittest",
        "gtest_environment_test",
        "googletest-filepath-test",
        "googletest-listener-test",
        "gtest_main_unittest",
        "googletest-message-test",
        "gtest_no_test_unittest",
        "googletest-options-test",
        "gtest_pred_impl_unittest",
        "googletest-printers-test",
        "gtest_prod_test",
        "gtest_sole_header_test",
        "googletest-test-part-test",
        "gtest-unittest-api_test",
        "gtest_skip_in_environment_setup_test",
        "gtest_skip_test",
        "googletest-param-test-test",
        "googletest-port-test",
        "gtest-typed-test_test",
        # googlemock/test
        "gmock_test",
        "gmock-cardinalities_test",
        "gmock_ex_test",
        "gmock-function-mocker_test",
        "gmock-matchers-arithmetic_test",
        "gmock-matchers-comparisons_test",
        "gmock-matchers-misc_test",
        "gmock-more-actions_test",
        "gmock-port_test",
        "gmock_link_test",
    ]

    # 排除依赖 fork 的 death-test 用例；个别非 *DeathTest* 命名但内部使用
    # EXPECT_DEATH_IF_SUPPORTED 的用例也一并排除（OHOS musl fork 受限，见 #7742）。
    # 另排除依赖宿主 /tmp 可写文件的 stdout/stderr 捕获用例：OHOS 应用沙箱无
    # 可写 /tmp，gtest-port.cc 硬编码 mkstemp("/tmp/gtest_captured_stream.XXXXXX")
    # 失败后 GTEST_LOG_(FATAL) SIGABRT（实测 googletest-port-test/gtest_unittest）。
    GTEST_SELFTEST_FILTER = (
        "-*DeathTest*:"
        "CaptureTest.*:"                                  # googletest-port-test: 捕获 stdout/stderr 需 /tmp
        "ParseFlagsTest.*:"                               # gtest_unittest: TestParsingFlags 捕获 stdout/stderr
        "FlagfileTest.*:"                                 # gtest_unittest: 同上（FlagfileTest : ParseFlagsTest）
        "TestResultPropertyTest.*:"                       # gtest_unittest: EXPECT_DEATH_IF_SUPPORTED
        "AssertTest.FailsFatallyOnFalse:"                 # gmock-internal-utils_test
        "OnCallSyntaxTest.WillByDefaultIsMandatory:"      # gmock-spec-builders_test
        "UnexpectedCallTest.UnsatisifiedPrerequisites:"   # gmock-spec-builders_test
        "NiceMockTest.ThrowsExceptionForUnknownReturnTypes"  # gmock-nice-strict_test
    )

    def _build_run_gtest_selftests(self, bdir):
        """逐个构建自测目标并实跑；任一目标未构建/未通过即终止出包（严格门禁）。

        说明：CI 真机（OHOS aarch64/musl）上 fork 受限，death-test 类二进制与用例
        （googletest-death-test-test / gtest-death-test_ex_* 等，见 #7742 brpc 先例）
        无法实跑，故不在运行列表；列表中个别含 fork 用例的二进制用
        GTEST_SELFTEST_FILTER 排除相应用例。运行列表内二进制必须全部 rc=0 且有
        [ PASSED ] 汇总（gtest_no_test_unittest 以 0 用例验证「无测试程序可运行」，
        特例允许 0）。任一失败会把汇总写入日志并 raise，CI 显红即证据。
        """
        import os
        import glob
        import subprocess
        import re

        # 逐个目标构建；某一目标编译失败只记录、继续其余目标，最后统一失败。
        missing = []
        for name in self.GTEST_SELFTEST_BINARIES:
            try:
                self.run(
                    'cmake --build "{}" --target {}'.format(bdir, name),
                    ignore_errors=False,
                )
            except Exception as exc:  # noqa: BLE001
                self.output.error("gtest self-test {}: BUILD FAILED: {}".format(name, str(exc)[:300]))
                missing.append(name)

        # 定位已构建出的二进制（gtest 目标在 <bdir>/googlemock/googletest/，
        # gmock 目标在 <bdir>/googlemock/）。编译成功但找不到产物也视为缺失。
        found = {}
        for name in self.GTEST_SELFTEST_BINARIES:
            if name in missing:
                continue
            hits = glob.glob(os.path.join(bdir, "**", name), recursive=True)
            if hits:
                found[name] = os.path.abspath(hits[0])
            else:
                missing.append(name)

        passed = []       # name
        failed = []       # (name, reason, evidence)
        total_tests = 0
        for name, exe in sorted(found.items()):
            try:
                self._sign_ohos_elf(exe)
            except Exception as exc:  # noqa: BLE001
                self.output.error("gtest self-test {}: sign failed: {}".format(name, exc))
                failed.append((name, "sign-fail", str(exc)[:200]))
                continue
            cmd = [exe, "--gtest_color=no"]
            if self.GTEST_SELFTEST_FILTER:
                cmd.append("--gtest_filter=" + self.GTEST_SELFTEST_FILTER)
            try:
                proc = subprocess.run(
                    cmd,
                    cwd=os.path.dirname(exe),
                    capture_output=True,
                    text=True,
                    timeout=600,
                )
            except Exception as exc:  # noqa: BLE001
                self.output.error("gtest self-test {}: run exception: {}".format(name, exc))
                failed.append((name, "run-exc", str(exc)[:200]))
                continue
            out = (proc.stdout or "") + (proc.stderr or "")
            pm = re.search(r"\[  PASSED  \] (\d+) tests?", out)
            fm = re.search(r"\[  FAILED  \] (\d+) tests?", out)
            sm = re.search(r"\[  SKIPPED ?\] (\d+) tests?", out)
            n_pass = int(pm.group(1)) if pm else None
            n_fail = int(fm.group(1)) if fm else None
            n_skip = int(sm.group(1)) if sm else None
            # 提取 gtest 汇总行作为 CI 日志证据。
            ev_lines = []
            for line in out.splitlines():
                s = line.strip()
                if s.startswith("[==========]") or s.startswith("[  PASSED  ]") or s.startswith("[  FAILED  ]"):
                    if s not in ev_lines:
                        ev_lines.append(s)
            ev = " | ".join(ev_lines[-4:])
            rc = proc.returncode
            # 判定：必须 rc=0，且确有通过/跳过用例。gtest_no_test_unittest 以
            # 0 用例验证「无测试程序可运行」，rc=0 即通过（特例）；gtest_skip_test
            # 的用例全部 SKIP 是 skip 功能自测的预期行为（rc=0 即通过）。
            reason = None
            if rc != 0:
                reason = "rc={}".format(rc)
            elif (n_pass is not None and n_pass > 0) or (n_skip is not None and n_skip > 0):
                reason = None
            elif name == "gtest_no_test_unittest":
                reason = None
            else:
                reason = "no-positive-PASSED/SKIPPED"
            if reason:
                failed.append((name, reason, ev))
                self.output.info(
                    "[gtest-self-test] {} FAIL rc={} passed={} failed={} :: {}".format(
                        name, rc, n_pass, n_fail, ev
                    )
                )
                tail = "\n".join(out.splitlines()[-25:])
                self.output.warning(
                    "gtest self-test {} tail output:\n{}".format(name, tail)
                )
            else:
                passed.append(name)
                total_tests += n_pass
                self.output.info(
                    "[gtest-self-test] {} PASS rc=0 passed={} :: {}".format(name, n_pass, ev)
                )

        self.output.info(
            "[gtest-self-test] SUMMARY pass_binaries={} fail_binaries={} missing_binaries={} total_binaries={} passed_tests={}".format(
                len(passed), len(failed), len(missing),
                len(passed) + len(failed) + len(missing), total_tests
            )
        )
        self.output.info(
            "[gtest-self-test] PASSED_BINARIES={}".format(",".join(sorted(passed)))
        )
        self.output.info(
            "[gtest-self-test] FAILED_BINARIES={}".format(
                ",".join(sorted(name for name, _, _ in failed) + sorted(missing))
            )
        )

        # 严格门禁：任何 curated 二进制未构建/未通过都使 conan-build-test 显红，
        # 把汇总（含失败原因）作为最后输出以便 CI 日志尾部取证。
        if missing or failed:
            self.output.error("gtest self-test: strict gate FAILED")
            for name in sorted(missing):
                self.output.error("[gtest-self-test] NOT_BUILT {}".format(name))
            for name, reason, evd in sorted(failed):
                self.output.error(
                    "[gtest-self-test] RUN_FAILED {} reason={} evidence={}".format(name, reason, evd)
                )
            raise ConanException(
                "googletest upstream self-test strict gate: passed {} / {} binaries; "
                "missing=[{}] failed=[{}]".format(
                    len(passed),
                    len(self.GTEST_SELFTEST_BINARIES),
                    ",".join(sorted(missing)),
                    ",".join(sorted(name for name, _, _ in failed)),
                )
            )

    def _sign_ohos_elf(self, path):
        # cdecode/mbw 消费者同法：OHOS 运行 ELF 前须 binary-sign-tool 自签并校验 .codesign。
        import os
        import shutil
        import subprocess
        signer = shutil.which("binary-sign-tool") or (
            "/data/service/hnp/bin/binary-sign-tool"
        )
        readelf = shutil.which("llvm-readelf") or (
            "/data/service/hnp/bin/llvm-readelf"
        )
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanInvalidConfiguration("required OHOS signing tools are missing")
        temporary = "{}.signed".format(path)
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", temporary, "-selfSign", "1"],
            check=True,
            timeout=60,
        )
        sections = subprocess.run(
            [readelf, "-SW", temporary],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanInvalidConfiguration("signed self-test has invalid .codesign: {}".format(path))
        os.chmod(temporary, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(temporary, path)

    def package(self):
        import os
        bdir = os.path.join(self.build_folder, "build-ohos")
        self.run('cmake --install "{}" --prefix "{}"'.format(bdir, self.package_folder))

    def package_info(self):
        # 静态链接顺序：gmock_main → gmock → gtest_main → gtest。
        self.cpp_info.libs = ["gmock_main", "gmock", "gtest_main", "gtest"]
        self.cpp_info.set_property("cmake_file_name", "GTest")
        self.cpp_info.set_property("cmake_target_name", "GTest::gtest")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
