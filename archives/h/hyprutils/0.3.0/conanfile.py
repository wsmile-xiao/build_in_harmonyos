#!/usr/bin/env python3
"""Conan recipe for hyprutils 0.3.0 — CMake (C++23).

Small C++ library for utilities used across the Hypr* ecosystem
(hyprpicker 前置依赖). Requires pixman-1; upstream provides 6 ctest
test cases (Memory/String/Signal/Math/OS/FileDescriptor).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class HyprutilsConan(ConanFile):
    name = "hyprutils"
    version = "0.3.0"
    description = "Small C++ library for utilities used across the Hypr* ecosystem"
    license = "BSD-3-Clause"
    homepage = "https://github.com/hyprwm/hyprutils"
    url = "https://github.com/hyprwm/hyprutils"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}
    # 导出 patches/ 目录（apply_conandata_patches 需要）
    exports_sources = "patches/*"

    def requirements(self):
        # CMakeLists pkg_check_modules(deps pixman-1)
        self.requires("pixman/0.46.4.3")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # CMakeLists pkg_check_modules(deps pixman-1)：pkg-config 读的是
        # 环境变量 PKG_CONFIG_PATH（tc.variables 是 CMake 缓存变量，无效），
        # 用 Environment 脚本注入依赖 pkgconfig 路径
        env = Environment()
        pc_paths = []
        for dep in self.dependencies.values():
            pc = os.path.join(dep.package_folder, "lib", "pkgconfig")
            if os.path.isdir(pc):
                pc_paths.append(pc)
        if pc_paths:
            env.append_path("PKG_CONFIG_PATH", os.pathsep.join(pc_paths))
        # 制品仓 pixman 包的 pixman-1.pc prefix=/ 未修正（Cflags 输出
        # -I//include/pixman-1 根目录）。CMake pkg_check_modules 生成的
        # Imported target 在 generate 阶段校验 include 路径存在性，坏路径
        # 直接报 "includes non-existent path //include/pixman-1"（-isystem
        # 注入无法绕过该检查）。修正方案：复制 .pc 到生成目录并改写 prefix
        # 为包真实路径，让 PKG_CONFIG_PATH 优先命中修正版。
        fixed_pc_dir = os.path.join(self.generators_folder, "fixed_pkgconfig")
        for dep in self.dependencies.values():
            if dep.ref.name != "pixman":
                continue
            base = dep.package_folder
            pc_src = os.path.join(base, "lib", "pkgconfig", "pixman-1.pc")
            if os.path.isfile(pc_src):
                os.makedirs(fixed_pc_dir, exist_ok=True)
                with open(pc_src, "r", encoding="utf-8") as f:
                    content = f.read()
                content = content.replace("prefix=/", f"prefix={base}")
                with open(os.path.join(fixed_pc_dir, "pixman-1.pc"), "w",
                          encoding="utf-8", newline="\n") as f:
                    f.write(content)
                env.prepend_path("PKG_CONFIG_PATH", fixed_pc_dir)
                self.output.info(
                    f"hyprutils: fixed pixman-1.pc prefix -> {base}"
                )
        # OHOS SDK 的 lld 运行时依赖 libxml2.so.16（llvm/lib 目录），
        # CI Worker 上 LD_LIBRARY_PATH 未含该目录导致 clang 调用 lld 时
        # 编译器检测/链接失败（libxkbcommon #6310 同款问题），注入即可
        llvm_lib = (
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/"
            "ohos/native/llvm/lib"
        )
        if os.path.isdir(llvm_lib):
            env.append_path("LD_LIBRARY_PATH", llvm_lib)
        env.vars(self).save_script("conanbuild_env")
        # Region.hpp 用 <pixman-1/pixman.h> 形式引用子目录头，但 pixman-1.pc
        # Cflags 只给 -I${includedir}/pixman-1（缺 include 根目录）——注入
        # pixman include 根目录（-isystem），保证 <pixman-1/pixman.h> 可解析
        for dep in self.dependencies.values():
            if dep.package_folder is None:
                continue
            inc = os.path.join(dep.package_folder, "include")
            if os.path.isdir(inc):
                tc.extra_cxxflags.append(f"-isystem{inc}")
                tc.extra_cflags.append(f"-isystem{inc}")
        # 生成 conanrun.sh：注入依赖（pixman）共享库路径，ctest 运行时
        # 需要 libpixman-1.so.0（否则测试二进制加载失败）
        VirtualRunEnv(self).generate()
        tc.generate()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 应用 conandata.yml 注册的补丁（0001-disable-format-formatter：
        # 条件编译保护 std::format formatter 特化，OHOS libc++ 15 无
        # <format> 头）
        apply_conandata_patches(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # 上游测试：ctest（Memory/String/Signal/Math 4 个用例）
        # 显式注入 LD_LIBRARY_PATH：build 目录（libhyprutils.so）+
        # 依赖 lib 目录（libpixman-1.so.0），否则测试二进制加载库失败
        lib_dirs = [self.build_folder]
        for dep in self.dependencies.values():
            libdir = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(libdir):
                lib_dirs.append(libdir)
        ld_path = ":".join(lib_dirs)
        self.run(
            f"export LD_LIBRARY_PATH=\"{ld_path}:$LD_LIBRARY_PATH\"; "
            "ctest --output-on-failure",
            env=["conanbuild", "conanbuild_env"],
        )

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["hyprutils"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("pkg_config_name", "hyprutils")
