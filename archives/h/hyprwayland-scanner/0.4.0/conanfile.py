#!/usr/bin/env python3
"""Conan recipe for hyprwayland-scanner 0.4.0 — CMake (C++23).

A hyprland version of wayland-scanner in and for C++ (hyprpicker 前置
依赖，代码生成工具). Requires pugixml; upstream no test target.
"""
import os
import re

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class HyprwaylandScannerConan(ConanFile):
    name = "hyprwayland-scanner"
    version = "0.4.0"
    description = "A hyprland version of wayland-scanner in and for C++"
    license = "BSD-3-Clause"
    homepage = "https://github.com/hyprwm/hyprwayland-scanner"
    url = "https://github.com/hyprwm/hyprwayland-scanner"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    # 导出 patches/ 目录（apply_conandata_patches 需要）
    exports_sources = "patches/*"

    def requirements(self):
        # CMakeLists pkg_check_modules(deps pugixml)；fmt 替代 std::format
        self.requires("pugixml/1.15-r0")
        self.requires("fmt/8.1.1")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # pkg_check_modules(deps pugixml)：pkg-config 读环境变量
        # PKG_CONFIG_PATH，用 Environment 脚本注入依赖 pkgconfig 路径
        env = Environment()
        pc_paths = []
        for dep in self.dependencies.values():
            pc = os.path.join(dep.package_folder, "lib", "pkgconfig")
            if os.path.isdir(pc):
                pc_paths.append(pc)
        if pc_paths:
            env.append_path("PKG_CONFIG_PATH", os.pathsep.join(pc_paths))
        # 制品仓 pugixml/fmt 包的 .pc prefix 指向 build 路径
        # （/conan2/p/b/pugix.../p），实际安装在 /conan2/p/pugix.../p，
        # CMake Imported target 校验 include 路径存在性直接报
        # "includes non-existent path"。复制 .pc 到生成目录改写 prefix
        # 为包真实路径，置顶 PKG_CONFIG_PATH（hyprutils/pixman 同款）。
        fixed_pc_dir = os.path.join(self.generators_folder, "fixed_pkgconfig")
        for dep in self.dependencies.values():
            if dep.ref.name not in ("pugixml", "fmt"):
                continue
            base = dep.package_folder
            pc_name = "pugixml.pc" if dep.ref.name == "pugixml" else "fmt.pc"
            pc_src = os.path.join(base, "lib", "pkgconfig", pc_name)
            if os.path.isfile(pc_src):
                os.makedirs(fixed_pc_dir, exist_ok=True)
                with open(pc_src, "r", encoding="utf-8") as f:
                    content = f.read()
                # prefix 可能是 prefix=/ 或完整 build 路径，统一替换为包真实路径
                content = re.sub(r"(?m)^prefix=.*$", f"prefix={base}", content)
                with open(os.path.join(fixed_pc_dir, pc_name), "w",
                          encoding="utf-8", newline="\n") as f:
                    f.write(content)
                env.prepend_path("PKG_CONFIG_PATH", fixed_pc_dir)
                self.output.info(
                    f"hyprwayland-scanner: fixed {pc_name} prefix -> {base}"
                )
        # CMakeLists 未声明 fmt 依赖（pkg_check_modules 仅 pugixml），
        # 但 main.cpp #include <fmt/format.h>，需把 fmt 的真实 include/lib
        # 注入编译与链接参数（否则 fmt/format.h not found / -lfmt 未链接）
        for dep in self.dependencies.values():
            if dep.ref.name != "fmt":
                continue
            base = dep.package_folder
            inc = os.path.join(base, "include")
            libdir = os.path.join(base, "lib")
            if os.path.isdir(inc):
                tc.extra_cxxflags.append(f"-isystem{inc}")
                tc.extra_cflags.append(f"-isystem{inc}")
            if os.path.isdir(libdir):
                tc.variables["CMAKE_EXE_LINKER_FLAGS"] = (
                    f"-L{libdir} -lfmt "
                    f"{tc.variables.get('CMAKE_EXE_LINKER_FLAGS', '')}"
                )
        env.vars(self).save_script("conanbuild_env")
        tc.generate()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # 应用 conandata.yml 注册的补丁（0001-use-fmt：std::format 改用
        # fmt::format，OHOS libc++ 15 无 <format> 头）
        apply_conandata_patches(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
