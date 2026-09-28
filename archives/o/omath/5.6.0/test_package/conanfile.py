#!/usr/bin/env python3
"""Conan test_package for omath 5.6.0 — 真实消费者构建 + 运行（R34/PF3）。

消费者通过 CMakeDeps 的 ``omath::omath`` 目标链接打包好的 libomath.a，并真实调用
omath 的公开 API（浮点 NTTP 的 Angle、Vector3::angle_between、base64、std::format
formatter）——删掉包内 lib/include 任一件都会断链/断编译，满足反空壳（L1e 可复跑做负对照）。

工具链与主配方一致（omath 头需要 clang≥18 的浮点 NTTP 支持）：
``tool_requires("clang/22.1.8")`` + SDK libc++15 的显式 include/lib 路径。
"""

import glob
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


def _ohos_sdk_root() -> str:
    roots = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native"))
    if not roots:
        raise RuntimeError("OHOS SDK not found under /data/service/hnp/ohos-sdk.org")
    return roots[-1]


class OmathTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        self.tool_requires("clang/22.1.8")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        self.conf.define("tools.build:jobs", 4)

        clang = self.dependencies.build["clang"]
        self.conf.update(
            "tools.build:compiler_executables",
            {
                "c": os.path.join(clang.package_folder, "bin", "clang"),
                "cpp": os.path.join(clang.package_folder, "bin", "clang++"),
            },
        )

        sdk = _ohos_sdk_root()
        sysroot = os.path.join(sdk, "sysroot")
        sysroot_lib = os.path.join(sysroot, "usr", "lib", "aarch64-linux-ohos")
        libcxx_include = os.path.join(sdk, "llvm", "include", "libcxx-ohos", "include", "c++", "v1")
        libcxx_lib = os.path.join(sdk, "llvm", "lib", "aarch64-linux-ohos")

        tc = CMakeToolchain(self)
        tc.variables["CMAKE_CXX_FLAGS"] = " ".join(
            [
                "-stdlib=libc++",
                "-fexperimental-library",
                "-isystem {}".format(libcxx_include),
                "-isystem {}".format(os.path.join(sysroot, "usr", "include", "aarch64-linux-ohos")),
                "-isystem {}".format(os.path.join(sysroot, "usr", "include")),
            ]
        )
        # -lc++experimental 由 omath 包的 cpp_info.system_libs 提供（进 LINK_LIBRARIES，顺序正确）
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = " ".join(
            ["-stdlib=libc++", "-B{}".format(sysroot_lib), "-L{}".format(libcxx_lib), "-L{}".format(sysroot_lib)]
        )
        tc.variables["CMAKE_CXX_STANDARD"] = 23
        tc.generate()

    def _strip_tool_libdir_from_buildenv(self):
        """与主配方同款：从生成的 buildenv 里摘掉 tool_requires(clang/22.1.8) 的 lib/。

        原因见主配方同名方法（CI worker 上该目录里的 libc++_shared.so 会让系统 cmake 重定位缺符号）。
        消费者测试也要跑，同样不能让 tool 的 lib/ 抢在系统库前面。
        """
        import glob as _glob
        gens = self.generators_folder
        if not gens:
            return
        libdir = os.path.join(self.dependencies.build["clang"].package_folder, "lib")
        for path in _glob.glob(os.path.join(_glob.escape(gens), "conanbuildenv*.sh")):
            with open(path, "r", encoding="utf-8") as fh:
                lines = fh.readlines()
            changed = False
            out = []
            for line in lines:
                if line.startswith("export LD_LIBRARY_PATH=") or line.startswith("export DYLD_LIBRARY_PATH="):
                    fixed = line.replace(libdir + ":", "").replace(libdir, "")
                    changed = changed or fixed != line
                    line = fixed
                out.append(line)
            if changed:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.writelines(out)
                self.output.info("test_package buildenv 已剥离 tool libdir: %s" % os.path.basename(path))

    def build(self):
        self._strip_tool_libdir_from_buildenv()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self._strip_tool_libdir_from_buildenv()
        if not can_run(self):
            self.output.info("cross-building: consumer linked but cannot run on this host")
            return
        exe = os.path.join(self.cpp.build.bindirs[0], "test_omath")
        # 静态库 + 全部依赖来自系统（libc++_shared.so 由加载器解析），无需 VirtualRunEnv
        self.run(exe)
