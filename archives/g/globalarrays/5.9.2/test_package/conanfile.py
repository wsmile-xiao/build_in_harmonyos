"""Conan test_package — globalarrays 5.9.2 consumer test (OHOS, mpich MPI)."""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class GlobalArraysTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            arch_map = {"armv8": "aarch64", "x86_64": "x86_64"}
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = arch_map.get(
                str(self.settings.arch), str(self.settings.arch)
            )
            # mpich 依赖为 shared 库，不追加 -static，由 conanrun 提供运行时库路径。
        # mpich recipe 的 package_info 未设 includedirs → CMakeDeps 的
        # MPI::MPI_C target 无 include 路径，ga.h 的 #include <mpi.h> 会失败；
        # 这里显式把 mpich include 目录注入编译（不改基线 mpich 配方）。
        mpich_inc = os.path.join(
            self.dependencies["mpich"].package_folder, "include"
        )
        tc.extra_cflags.append(f"-I{mpich_inc}")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        # HMDFS 不支持 mkfifo：make jobserver 会失败（preflight F4），必须 -j1
        cmake.build(cli_args=["-j1"])

    def test(self):
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_ga")
        if cross_building(self):
            qemu = shutil.which("qemu-aarch64")
            if not qemu:
                raise ConanInvalidConfiguration(
                    "qemu-aarch64 is required to run the OHOS test package"
                )
            self.run(f'"{qemu}" "{bin_path}"', env="conanrun")
        else:
            # 单进程 consumer 测试
            self.run(bin_path, env="conanrun")
        # 上游单元测试：真 MPI（mpich 依赖）提供 mpicc/mpiexec，
        # 用 mpiexec -n 1 单进程运行 68 个验证 PASS 的上游单文件测试
        # （-n 2 会 MA_init 重复初始化冲突超时），任一失败即整体失败；
        # 12 个已知 FAIL 已在 MANIFEST.yml 记录原因。
        pkg_folder = self.dependencies["globalarrays"].package_folder
        mpich_folder = self.dependencies["mpich"].package_folder
        self.run(
            f'/bin/sh {os.path.join(self.source_folder, "run_upstream_tests.sh")} '
            f'"{pkg_folder}" "{mpich_folder}"',
            env="conanrun",
        )
