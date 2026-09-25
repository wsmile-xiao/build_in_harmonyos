#!/usr/bin/env python3
"""Conan recipe for libmialm 1.0.9 on Linux and HarmonyOS PC."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    mkdir,
    replace_in_file,
    rm,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibmialmConan(ConanFile):
    name = "libmialm"
    version = "1.0.9"
    description = "Library for loading and storing three-dimensional landmark lists"
    license = "GPL-3.0-or-later"
    homepage = "https://sourceforge.net/projects/mia/files/mialm/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    implements = ["auto_shared_fpic"]

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    generators = "PkgConfigDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib/2.88.3.1", transitive_headers=True)
        self.requires("libxml2/2.15.3.1", transitive_headers=True)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libmialm supports Linux and OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("HarmonyOS PC builds require armv8/aarch64")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.append("--disable-gtk-doc")
        # 上游 Makefile.am 按源码树根目录引用 <mialm/...>；Conan 使用
        # VPATH 构建，因此显式暴露源码根目录，避免回退到源码内构建。
        toolchain.extra_cflags.append("-I{}".format(self.source_folder))
        toolchain.generate()

        runenv = Environment()
        # HarmonyOS PC 的 HMDFS 偶发无法由子进程反查当前目录；bash 与
        # configure 可使用这个经过 Conan 解析的逻辑路径继续工作。
        runenv.define("PWD", self.build_folder)
        for dependency in self.dependencies.values():
            for libdir in dependency.cpp_info.libdirs:
                runenv.prepend_path("LD_LIBRARY_PATH", libdir)
        runenv.vars(self, scope="build").save_script("conanbuild_runpath")

    def _prepare_harmonyos_configure(self):
        if self.settings.os != "OHOS":
            return
        configure = os.path.join(self.source_folder, "configure")
        workdir = os.path.join(self.build_folder, "config-status-work")
        mkdir(self, workdir)
        replace_in_file(
            self,
            configure,
            "ac_tmp=$tmp",
            'ac_tmp="{}"'.format(workdir),
            strict=True,
        )
        replace_in_file(
            self,
            configure,
            'ac_pwd=`pwd` && test -n "$ac_pwd" &&',
            'ac_pwd=`pwd` 2>/dev/null || ac_pwd=$PWD\n'
            'test -n "$ac_pwd" &&',
            strict=True,
        )

    def build(self):
        apply_conandata_patches(self)
        os.environ["PWD"] = self.build_folder
        self._prepare_harmonyos_configure()
        autotools = Autotools(self)
        autotools.configure()
        # gtk-doc 是发布文档工具，不参与库功能；上游顶层 all 无条件进入
        # docs/reference，即使 --disable-gtk-doc 也会调用 gtkdoc-scan。
        # 使用 shell cd 让 PWD 与真实子目录同步；make -C 不更新 PWD，会让
        # 旧版 libtool 在 HMDFS getcwd 失败时误算 .libs 的相对路径。
        mialm_build = os.path.join(self.build_folder, "mialm")
        test_build = os.path.join(self.build_folder, "test")
        self.run('cd "{}" && make -j1'.format(mialm_build))
        self.run('cd "{}" && make check -j1'.format(test_build))

    def package(self):
        mialm_build = os.path.join(self.build_folder, "mialm")
        self.run(
            'cd "{}" && make install DESTDIR="{}" -j1'.format(
                mialm_build, self.package_folder
            )
        )
        copy(
            self,
            "mialm.h",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "mialm.pc",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "lib", "pkgconfig"),
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        rm(self, "*.la", self.package_folder, recursive=True)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libmialm")
        component = self.cpp_info.components["libmialm"]
        component.libs = ["mialm"]
        # 依赖包在当前 OHOS 制品修订中的 CMake 组件没有导出实际库名；
        # requires 继续传播头文件/运行环境，同时显式列出公共 ABI 链接库，
        # 使只链接 libmialm::libmialm 的消费者也能使用公开头中的宏/API。
        component.system_libs = ["gobject-2.0", "glib-2.0", "xml2", "m"]
        component.requires = [
            "glib::glib",
            "glib::gobject",
            "libxml2::libxml2",
        ]
        # 保留全局消费者目标 libmialm::libmialm；组件使用不同内部目标名，
        # 避免 CMakeDeps 把同名全局目标聚合到自身而丢失公共依赖。
        component.set_property("cmake_target_name", "libmialm::mialm")
        component.set_property("pkg_config_name", "mialm")
