#!/usr/bin/env python3
"""Conan recipe for hyprpicker 0.4.7 — CMake (C++23).

A wlroots-compatible Wayland color picker that does not suck.
Requires wayland-client/xkbcommon/cairo/pango/libjpeg/hyprutils/
hyprwayland-scanner; upstream no test target.
"""
import os
import re
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class HyprpickerConan(ConanFile):
    name = "hyprpicker"
    version = "0.4.7"
    description = "A wlroots-compatible Wayland color picker that does not suck"
    license = "BSD-3-Clause"
    homepage = "https://github.com/hyprwm/hyprpicker"
    url = "https://github.com/hyprwm/hyprpicker"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "patches/*"

    def requirements(self):
        # CMakeLists pkg_check_modules(deps ...)
        self.requires("wayland/1.22.0")
        self.requires("wayland-protocols/1.36")
        self.requires("libxkbcommon/1.6.0")
        self.requires("cairo/1.18.4")
        self.requires("pango/1.56.4")
        self.requires("libjpeg-turbo/3.2.0")
        self.requires("hyprutils/0.3.0")
        self.requires("hyprwayland-scanner/0.4.0")
        self.requires("fmt/8.1.1")
        # 传递依赖 .pc 被 pkg_check_modules 间接引用（wayland-client.pc
        # Requires libffi、cairo.pc Requires zlib、glib-2.0.pc Requires
        # libpcre2-8、harfbuzz.pc Requires graphite2、hyprutils 用 pugixml），
        # conan 会把纯传递依赖标为 "Skipped binaries" 不装二进制，导致
        # pkg-config 找不到这些 .pc——提升为直接 requires 强制安装
        self.requires("libffi/3.4.4")
        self.requires("zlib/1.3.1.1")
        self.requires("pcre2/10.45")
        self.requires("graphite2/1.3.14")
        self.requires("pugixml/1.15-r0")
        # pixman 版本冲突：hyprutils requires pixman/0.46.4.3，cairo
        # requires pixman/0.46.4——override 统一为 cairo 用的 0.46.4
        #（hyprutils 仅 pkg-config 查 pixman-1，API 兼容）
        self.requires("pixman/0.46.4", override=True)
        # expat 版本冲突：wayland requires expat/2.8.2，其他依赖链用
        # expat/2.8.2.1——override 统一为 2.8.2（API 兼容）
        self.requires("expat/2.8.2", override=True)
        # fontconfig 版本冲突：cairo 依赖链用 fontconfig/2.18.1.1，
        # 其他依赖用 2.18.1——override 统一为 2.18.1（API 兼容）
        self.requires("fontconfig/2.18.1", override=True)
        # harfbuzz：pango requires 14.2.0.1，本仓库已适配 14.2.0.1.1
        # 且制品仓有匹配二进制（patch 级兼容）——override 避免本地
        # 全量构建 499 个目标（构建超时）
        self.requires("harfbuzz/14.2.0.1.1", override=True)

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        env = Environment()
        # pkg_check_modules(deps ...) 经 pkg-config 查找，注入全部依赖
        # pkgconfig 路径；制品仓依赖 .pc prefix 可能指向 build 路径，
        # 复制改写 prefix 置顶（hyprutils/wayland 同款）
        fixed_pc_dir = os.path.join(self.generators_folder, "fixed_pkgconfig")
        pc_paths = []
        for dep in self.dependencies.values():
            if dep.package_folder is None:
                self.output.info(f"WARN: dep {dep.ref} has no package_folder, skip pc injection")
                continue
            for pc_dir in ("lib", "share"):
                pc = os.path.join(dep.package_folder, pc_dir, "pkgconfig")
                if os.path.isdir(pc):
                    pc_paths.append(pc)
                    for pc_name in os.listdir(pc):
                        if not pc_name.endswith(".pc"):
                            continue
                        pc_src = os.path.join(pc, pc_name)
                        base = dep.package_folder
                        os.makedirs(fixed_pc_dir, exist_ok=True)
                        with open(pc_src, "r", encoding="utf-8") as f:
                            content = f.read()
                        # 制品仓 .pc 的 prefix/exec_prefix/libdir/includedir
                        # 可能硬编码为 / 或旧路径，统一改写为实际包目录
                        #（freetype2 先例：libdir=//lib → {base}/lib）
                        content = re.sub(
                            r"(?m)^prefix=.*$", f"prefix={base}", content
                        )
                        content = re.sub(
                            r"(?m)^exec_prefix=.*$", f"exec_prefix={base}", content
                        )
                        content = re.sub(
                            r"(?m)^libdir=.*$", f"libdir={base}/lib", content
                        )
                        content = re.sub(
                            r"(?m)^includedir=.*$", f"includedir={base}/include", content
                        )
                        # 制品仓 .pc 硬编码的是构建机 build 缓存路径
                        #（.../p/b/<hash>/p），前缀可能与当前缓存目录不一致
                        #（如制品仓 .conon2 vs CI Worker .cache/conon2），
                        # 用推导的 build_roots 精确前缀匹配会漏替换——改为
                        # 匹配任意前缀的完整路径（/开头，保留 -L/-I 选项）
                        # 统一替换为实际包目录（graphite2 先例）
                        content = re.sub(
                            r"/[^\"\s]*/p/b/[^/\s]+/p",
                            base, content,
                        )
                        with open(os.path.join(fixed_pc_dir, pc_name), "w",
                                  encoding="utf-8", newline="\n") as f:
                            f.write(content)
        if pc_paths:
            env.append_path(
                "PKG_CONFIG_PATH",
                os.pathsep.join([fixed_pc_dir] + pc_paths),
            )
        # 工具路径：hyprwayland-scanner 命令 + wayland-protocols pkgdatadir
        for dep in self.dependencies.values():
            if dep.package_folder is None:
                continue
            if dep.ref.name == "hyprwayland-scanner":
                bin_dir = os.path.join(dep.package_folder, "bin")
                if os.path.isdir(bin_dir):
                    env.append_path("PATH", bin_dir)
        # hyprwayland-scanner 是 fmt 链接的共享库可执行（OHOS 沙箱隔离），
        # 运行生成协议头文件时需 LD_LIBRARY_PATH 含依赖 lib 目录
        lib_paths = [
            os.path.join(dep.package_folder, "lib")
            for dep in self.dependencies.values()
            if dep.package_folder
            and os.path.isdir(os.path.join(dep.package_folder, "lib"))
        ]
        if lib_paths:
            env.append_path("LD_LIBRARY_PATH", os.pathsep.join(lib_paths))
        # 0001-use-fmt.patch 把 std::format 改用 fmt::format，但上游
        # CMakeLists 未声明 fmt 依赖（pkg_check_modules 无 fmt），需注入
        # fmt 真实 include/lib 到编译与链接参数（hyprwayland-scanner 同款）
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
        # includes.hpp 用 <cairo/cairo.h> 形式引用子目录头，但 cairo.pc
        # Cflags 只给 -I${includedir}/cairo（缺 include 根目录）——统一为
        # 每个依赖注入 include 根目录（-isystem），保证 <pkg/pkg.h> 可解析
        for dep in self.dependencies.values():
            if dep.package_folder is None:
                continue
            inc = os.path.join(dep.package_folder, "include")
            if os.path.isdir(inc):
                tc.extra_cxxflags.append(f"-isystem{inc}")
                tc.extra_cflags.append(f"-isystem{inc}")
        # CMakeLists target_link_libraries 直接裸链接 wayland-cursor
        #（不走 pkg-config），需注入 wayland 的 lib 目录到链接参数
        for dep in self.dependencies.values():
            if dep.ref.name != "wayland":
                continue
            libdir = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(libdir):
                tc.variables["CMAKE_EXE_LINKER_FLAGS"] = (
                    f"-L{libdir} "
                    f"{tc.variables.get('CMAKE_EXE_LINKER_FLAGS', '')}"
                )
        env.vars(self).save_script("conanbuild_env")
        tc.generate()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)
        # OHOS 文件系统大小写不敏感：源码根 VERSION 文件会被 <version>
        # 标准头误解析（-I. 命中），重命名为 VERSION.txt（配合
        # 0002-rename-version.patch 改读 VERSION.txt）
        version_src = os.path.join(self.source_folder, "VERSION")
        version_dst = os.path.join(self.source_folder, "VERSION.txt")
        if os.path.isfile(version_src) and not os.path.exists(version_dst):
            os.rename(version_src, version_dst)
            self.output.info("hyprpicker: renamed VERSION -> VERSION.txt")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
