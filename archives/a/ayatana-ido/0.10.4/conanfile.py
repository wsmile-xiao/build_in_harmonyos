#!/usr/bin/env python3
"""Conan recipe — ayatana-ido 0.10.4 (CMake).

Ayatana Indicator Display Objects — GTK3 菜单项组件库。
HarmonyOS PC (aarch64) 适配要点：
  - 构建系统: CMake (upstream CMakeLists.txt; conan-init 的 autotools 检测不适用)
  - 依赖: glib-2.0>=2.58 + gtk+-3.0>=3.24（pkg_check_modules），对齐 ohpcd
    已发布的 gtk/3.24.43 依赖图（glib/2.84.0.1，避免与 gtk 依赖图版本冲突）
  - 无 X11/窗口系统：库本身只提供菜单项构件，无显示后端依赖；运行时由
    消费方决定 GDK 后端（broadway 已验证可实例化）
  - 构建产物: libayatana-ido3-0.4.so + libayatana-ido3-0.4.pc + 公共头
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps


class AyatanaidoConan(ConanFile):
    name = "ayatana-ido"
    version = "0.10.4"
    description = "Ayatana Indicator Display Objects (GTK3 menu item widgets)"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/AyatanaIndicators/ayatana-ido"
    url = "https://github.com/AyatanaIndicators/ayatana-ido"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # gtk/3.24.43 的 recipe pin glib/2.84.0.1（pango/atk/cairo-gobject 同图），
        # 顶层必须对齐同一版本避免图内版本冲突（R36）。
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        self.requires("gtk/3.24.43", transitive_headers=True, transitive_libs=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["ENABLE_TESTS"] = "OFF"
        tc.variables["ENABLE_WERROR"] = "OFF"
        # 上游 src/CMakeLists.txt 用 target_link_libraries(${PROJECT_DEPS_LIBRARIES})
        # 但未用 PROJECT_DEPS_LIBRARY_DIRS，pkg_check_modules 的 -L 路径不会
        # 进入链接行。手动构建同样缺 -L（ld 报 unable to find library -ljpeg 等）。
        # 遍历依赖图全部包注入 libdir（含传递依赖：cairo-gobject/jpeg/turbojpeg/
        # zstd/webp/tiff 等被 gtk 依赖图拉入，其 .pc 的 -L 均未进 CMake 缓存变量）。
        link_dirs = set()
        for dep_name, dep in self.dependencies.items():
            if dep.package_folder:
                libdir = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(libdir):
                    link_dirs.add(f"-L{libdir}")
        flags = " ".join(sorted(link_dirs))
        tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = flags
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = flags
        # W4/L5 门禁: 上游 CMake 的 VERSION 0.0.0 SOVERSION 0 未产出 DT_SONAME,
        # L5 soname_gate 拦截。显式注入 soname, 与 SOVERSION 0 对齐
        # (libayatana-ido3-0.4.so.0)。
        tc.variables["CMAKE_SHARED_LINKER_FLAGS"] = (
            flags + " -Wl,-soname,libayatana-ido3-0.4.so.0"
        )
        # 上游 src/CMakeLists.txt 用 find_program(GLIB_MKENUMS glib-mkenums) 生成
        # idotypebuiltins。CI bundle 的 /data/service/hnp/bin/glib-mkenums 是
        # 指向阐库 glib_2.38.2 的符号链接（断链/版本陈旧），find_program 会
        # 优先缓存该路径导致 "No such file or directory"。显式注入 glib 包内
        # 真实脚本绝对路径，绕过坏符号链接（E540 同类 runner-path 问题）。
        glib_bin = os.path.join(self.dependencies["glib"].package_folder, "bin")
        glib_mkenums = os.path.join(glib_bin, "glib-mkenums")
        tc.variables["GLIB_MKENUMS"] = glib_mkenums
        env = Environment()
        env.prepend_path("PATH", glib_bin)
        env.vars(self).save_script("glib_tools_env")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        with Environment().vars(self).apply():
            cmake.configure()
            cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # W4/L5: 上游 CMake VERSION 0.0.0 未产出版本化文件名, 仅安装裸 .so;
        # 注入的 SONAME 为 libayatana-ido3-0.4.so.0, 下游按 SONAME 寻址需
        # 该文件名存在 (HMDFS 软链接不可靠, 用复制保证运行时可达)。
        libdir = os.path.join(self.package_folder, "lib")
        soname_target = os.path.join(libdir, "libayatana-ido3-0.4.so.0")
        if not os.path.exists(soname_target):
            shutil.copy2(os.path.join(libdir, "libayatana-ido3-0.4.so"), soname_target)

    def package_info(self):
        self.cpp_info.libs = ["ayatana-ido3-0.4"]
        self.cpp_info.includedirs = ["include/libayatana-ido3-0.4", "include"]
        self.cpp_info.set_property("cmake_file_name", "ayatana-ido3")
        self.cpp_info.set_property("cmake_target_name", "ayatana-ido3::ayatana-ido3-0.4")
        self.cpp_info.set_property("pkg_config_name", "libayatana-ido3-0.4")
        self.cpp_info.requires = ["glib::glib", "gtk::gtk"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
