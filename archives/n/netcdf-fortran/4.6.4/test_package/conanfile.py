#!/usr/bin/env python3
"""Conan test_package — netcdf-fortran 4.6.4 消费者验证（Conan L1）

真实消费者：用 Fortran 2003 写一个 `use netcdf` 的程序，链接包里的 libnetcdff.so，
跑通「建 netCDF-4 文件 → 定义维度/变量 → 写属性 → 回读校验」全链路，并断言
库自报版本为 4.6.4（nf90_inq_libvers）。

Fortran 编译用与生产包同一工具链 flang-ohos/20.1.0（.mod 是编译器私有接口，
见 manifest 的 knowledge_gained 引用 E242），flag 与 recipe 一致。
"""
import glob
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class NetcdfFortranTestPackage(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        self.tool_requires("flang-ohos/20.1.0", package_id_mode="full_mode")

    def validate(self):
        if str(self.settings.os) != "OHOS":
            raise ConanInvalidConfiguration("test_package 仅在 os=OHOS 下有效")

    def layout(self):
        cmake_layout(self)

    def _sdk_native(self):
        configured = self.conf.get("user.netcdf_fortran:sdk_native", default=None, check_type=str)
        candidates = [configured] if configured else glob.glob(
            "/data/service/hnp/ohos-sdk.org/*/ohos/native")
        valid = []
        for candidate in candidates:
            candidate = os.path.realpath(candidate)
            required = (
                os.path.join(candidate, "sysroot"),
                os.path.join(candidate, "llvm", "lib"),
                os.path.join(candidate, "llvm", "lib", "aarch64-linux-ohos"),
            )
            clang = os.path.join(candidate, "llvm", "bin", "clang")
            if (all(os.path.isdir(p) for p in required)
                    and os.path.isfile(clang) and os.access(clang, os.X_OK)):
                valid.append(candidate)
        valid = sorted(set(valid))
        if len(valid) != 1:
            raise ConanInvalidConfiguration(
                "需要且仅需要一个完整的 OHOS SDK native 根；请设置 "
                "user.netcdf_fortran:sdk_native")
        return valid[0]

    def _fortran_toolchain(self):
        """(flang, 编译 flags, 链接 flags)，与生产包 recipe 保持同一口径。"""
        flang_package = self.dependencies.build["flang-ohos"].package_folder
        flang = os.path.join(flang_package, "bin", "flang")
        flang_lib = os.path.join(flang_package, "lib")
        if not os.path.isfile(flang) or not os.path.isdir(flang_lib):
            raise ConanInvalidConfiguration("flang-ohos 工具包不完整")
        sdk_native = self._sdk_native()
        sdk_clang = os.path.join(sdk_native, "llvm", "bin", "clang")
        runtime_dirs = (os.path.join(sdk_native, "llvm", "lib"), flang_lib)
        probe_env = os.environ.copy()
        probe_env["LD_LIBRARY_PATH"] = os.pathsep.join(runtime_dirs)
        try:
            resource_dir = subprocess.run(
                [sdk_clang, "-print-resource-dir"], check=True, env=probe_env,
                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.strip()
        except (OSError, subprocess.CalledProcessError) as error:
            raise ConanInvalidConfiguration("无法探测 OHOS SDK clang 的 resource-dir") from error
        resource_dir = os.path.realpath(resource_dir)
        compile_flags = " ".join([
            "--target=aarch64-unknown-linux-ohos",
            "--sysroot={}".format(os.path.join(sdk_native, "sysroot")),
            "-resource-dir={}".format(resource_dir),
        ])
        link_flags = "-L{}".format(
            os.path.join(sdk_native, "llvm", "lib", "aarch64-linux-ohos"))
        return flang.replace("\\", "/"), compile_flags, link_flags

    def _tested_package_libdir(self):
        """被测包的 lib 目录绝对路径，作为「库来自被测包」断言的期望前缀。"""
        for _ref, dep in self.dependencies.items():
            if dep.ref.name == "netcdf-fortran" and dep.package_folder:
                return os.path.join(dep.package_folder, "lib")
        raise ConanException("找不到被测包 netcdf-fortran 的 package_folder")

    def generate(self):
        CMakeDeps(self).generate()
        flang, fortran_flags, fortran_link_flags = self._fortran_toolchain()
        toolchain = CMakeToolchain(self)
        toolchain.variables["CMAKE_Fortran_COMPILER"] = flang
        toolchain.variables["CMAKE_Fortran_FLAGS"] = fortran_flags
        toolchain.variables["CMAKE_EXE_LINKER_FLAGS"] = fortran_link_flags
        toolchain.variables["CMAKE_SHARED_LINKER_FLAGS"] = fortran_link_flags
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # Fortran 消费者：真实读写链路
        fortran_test = os.path.join(self.cpp.build.bindirs[0], "test_netcdf_fortran")
        self.run('"{}"'.format(fortran_test), env="conanrun", cwd=self.build_folder)

        # C 侧交付面契约：把被测包 lib 目录传进去，让测试断言「加载到的就是被测包那份」
        abi_test = os.path.join(self.cpp.build.bindirs[0], "test_netcdf_fortran_abi")
        self.run('NETCDFF_PACKAGE_LIBDIR="{}" "{}"'.format(
            self._tested_package_libdir(), abi_test), env="conanrun", cwd=self.build_folder)
