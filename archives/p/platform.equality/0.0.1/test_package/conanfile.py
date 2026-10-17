#!/usr/bin/env python3
"""Conan test_package — platform.equality 0.0.1 (header-only).

消费者视角：find_package(platform.equality) + 真实调用公共 API。
"""
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
import os


class PlatformEqualityTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        # 注意：这里**不再**自己硬编码 -D_LIBCPP_ENABLE_EXPERIMENTAL。
        # 该宏已由主配方 package_info() 通过 cpp_info.defines 导出，会经
        # CMakeDeps 自动带到本消费者目标上。若在此重复硬编码，就会掩盖
        # "宏没随包导出"这一真实缺陷 —— 本 test_package 必须能验证导出是否生效。
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 交叉编译（ohos-aarch64）下 can_run() 恒为 False：宿主是 x86_64 Linux，
        # target 是 OHOS/aarch64，Conan 据此判定"不能运行"。
        #
        # ⚠ 这里刻意【不】把 `if can_run(self):` 当作整个 test() 的守卫 ——
        # 那会让 test() 在进入任何校验前就返回，conan create 报成功而
        # **产物布局没校验、断言也没执行**（静默放行）。
        # 正确做法：先定位产物并校验其确实存在 + 校验 4 个公共头确实被
        # 打包，这些在任何宿主上都必须为真；之后才判断能否执行。
        # 不能执行时打可见 WARNING 记录跳过（见下方分支），不静默通过。
        bindirs = self.cpp.build.bindirs
        if not bindirs:
            raise Exception("No bindirs found")
        bin_path = os.path.join(bindirs[0], "test_platform_equality")
        if not os.path.isfile(bin_path):
            raise Exception(f"Test binary not found: {bin_path}")

        # P2：无论能否执行，"绿"都至少要意味着产物布局被校验过。
        pkg_inc = os.path.join(
            self.dependencies["platform.equality"].package_folder, "include")
        for hdr in ("Platform.Equality.h", "Platform.Equality.Any.h",
                    "Platform.Equality.Range.h",
                    "Platform.Equality.EqualityComparerFunctionType.h"):
            if not os.path.isfile(os.path.join(pkg_inc, hdr)):
                raise Exception(f"Missing public header in package: {hdr}")
        self.output.info(f"package layout OK: 4 public headers under {pkg_inc}")

        if not can_run(self):
            # 交叉编译（宿主 x86_64 / 目标 OHOS-aarch64）下 can_run() 为 False：
            # 宿主无法直接执行 aarch64 产物。CI 的 OHOS worker 是**原生**构建
            # （ci/conan/profiles/ohos-aarch64，无 qemu、无 emulator conf），
            # 在那里 can_run() 为 True，本用例会真实执行。
            #
            # 不用静默 `return`（那会造成"全绿但零验证"）；也不 raise
            # （那会在无法执行的宿主上把 CI 弄红，而 CI 是原生 OHOS worker，
            # 本分支在那里根本不会走到）。
            # 用 warning 明确记录"本机跳过、跳过的是什么"——跳过可见，
            # 且上面已完成的产物布局校验仍然生效。
            self.output.warning(
                "SKIPPED consumer test: cannot execute the OHOS aarch64 binary "
                f"on this host ({bin_path}). No assertion was run here. "
                "Local verification must use the 'ohos-aarch64-run' profile "
                "(qemu CROSSCOMPILING_EMULATOR + binfmt_misc); CI runs natively "
                "on the OHOS worker and does execute it."
            )
            return

        self.run(bin_path, env="conanrun")
