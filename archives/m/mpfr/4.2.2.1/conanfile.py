#!/usr/bin/env python3
"""Conan recipe for MPFR 4.2.2.1."""

import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class MpfrConan(ConanFile):
    name = "mpfr"
    version = "4.2.2.1"
    description = "GNU Multiple Precision Floating-Point Reliable Library"
    license = "LGPL-3.0-or-later"
    homepage = "https://www.mpfr.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "mpfr/4.2.2.1 is validated only for Linux and OHOS"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("gmp/6.3.0")

    def layout(self):
        basic_layout(self, src_folder="src")

    def _ohos_tool(self, name):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        c_compiler = compiler_executables.get("c")
        if c_compiler and os.path.isabs(c_compiler):
            return os.path.join(os.path.dirname(c_compiler), name)
        return name

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        gmp = self.dependencies["gmp"]
        gmp_include = os.path.join(gmp.package_folder, "include")
        gmp_libdir = os.path.join(gmp.package_folder, "lib")

        toolchain = AutotoolsToolchain(self)
        if self.options.shared:
            toolchain.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            toolchain.configure_args.extend(["--disable-shared", "--enable-static"])
            if self.options.get_safe("fPIC"):
                toolchain.configure_args.append("--with-pic")
        toolchain.configure_args.extend(
            [
                f"--with-gmp-include={gmp_include}",
                f"--with-gmp-lib={gmp_libdir}",
            ]
        )
        if self.settings.os == "OHOS":
            toolchain.configure_args.extend(
                [
                    f"AR={self._ohos_tool('llvm-ar')}",
                    f"LD={self._ohos_tool('ld.lld')}",
                    f"RANLIB={self._ohos_tool('llvm-ranlib')}",
                    f"NM={self._ohos_tool('llvm-nm')}",
                    f"OBJDUMP={self._ohos_tool('llvm-objdump')}",
                    f"STRIP={self._ohos_tool('llvm-strip')}",
                ]
            )
        toolchain.generate()

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        if can_run(self):
            autotools.make(target="check", args=["-j1"])
        else:
            self.output.info("Skipping make check because this is a cross build")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # 删掉 libtool 的 .la —— 4.2.2 未删，是下游链接失败的根因。
        # conan 按 prefix=/ 构建，libmpfr.la 里的 dependency_libs 因此被烤成
        #   dependency_libs=' -L<gmp libdir> //lib/libgmp.la'
        # 下游用 libtool 链接时会顺着它递归解析那个根本不存在的路径：
        #   libtool: error: cannot find the library '//lib/libgmp.la'
        # （linbox 1.7.0 实撞；把生成的 libtool 里 link_all_deplibs 关掉也挡不住，
        #  因为 libtool 是在读取 -lmpfr 命中的 .la 时就去解析它的 dependency_libs。）
        # 依赖的真实链接信息 conan 已通过 .pc 与 cpp_info 完整提供，.la 无用。
        for _la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(_la)
        copy(
            self,
            "COPYING*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["mpfr"]
        self.cpp_info.requires = ["gmp::gmp"]
        self.cpp_info.set_property("cmake_file_name", "mpfr")
        self.cpp_info.set_property("cmake_target_name", "mpfr::mpfr")
        self.cpp_info.set_property("pkg_config_name", "mpfr")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
