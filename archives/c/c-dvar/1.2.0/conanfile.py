#!/usr/bin/env python3
"""Conan recipe — c-dvar 1.2.0 (c-util, D-Bus Variant Type-System).

C11 + meson；产物：头文件 c-dvar.h/c-dvar-type.h + 库 cdvar-1（静态/共享）。
依赖 c-stdaux >= 1.5.0 与 c-utf8（上游 pkg-config 名 libcstdaux-1/libcutf8-1）。
可选依赖 libdbus-typenum（required: false）不提供：上游默认套件为 4 项测试，
条件注册的 Enumerated Types 测试随之不启用。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, save, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import MesonToolchain
from conan.tools.layout import basic_layout


class CDvarConan(ConanFile):
    name = "c-dvar"
    version = "1.2.0"
    description = "c-dvar — D-Bus Variant Type-System (c-util)"
    license = "Apache-2.0"
    homepage = "https://github.com/c-util/c-dvar"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("c-stdaux/1.6.0")
        self.requires("c-utf8/1.1.0")

    def build_requirements(self):
        self.tool_requires("meson/1.11.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # 上游 meson.build 以 dependency('libcstdaux-1'/'libcutf8-1') 消费依赖。
        # conan 依赖名与上游 pkg-config 名不同：PkgConfigDeps 生成的 .pc 无法命中，
        # 因此在 generate() 手写同名 shim（仓库先例：abiword-plugin-* 对 glib-2.0，
        # 同族 c-siphash/c-shquote/c-rbtree/c-utf8 1.1.0 同款）。
        # c-stdaux 侧需提供上游读取的 pc 变量 cflags 与 version_scripts；
        # cflags 取 c-stdaux 上游 get_supported_arguments 在本平台 clang 15 的
        # 实测生效集合（与 meson 子项目直接构建的 build.ninja 一致）。
        stdaux = self.dependencies["c-stdaux"]
        includes = " ".join("-I" + d for d in stdaux.cpp_info.includedirs)
        cflags = (
            "-D_GNU_SOURCE"
            " -Wno-gnu-alignof-expression -Wno-unknown-warning-option"
            " -Wno-unused-parameter -Wno-error=type-limits"
            " -Wno-error=missing-field-initializers -Wdate-time"
            " -Wdeclaration-after-statement -Wmissing-include-dirs"
            " -Wmissing-noreturn -Wnested-externs -Wredundant-decls"
            " -Wshadow -Wundef -Wwrite-strings"
        )
        pc = "\n".join([
            "prefix=" + stdaux.package_folder,
            "includedir=" + stdaux.cpp_info.includedirs[0],
            "",
            "Name: libcstdaux",
            "Description: c-stdaux auxiliary macros for ISO-C11 (conan shim)",
            "URL: https://github.com/c-util/c-stdaux",
            "Version: " + str(stdaux.ref.version),
            "Libs:",
            "Cflags: " + includes,
            "cflags=" + cflags,
            "version_scripts=yes",
            "",
        ])
        save(self, os.path.join(self.generators_folder, "libcstdaux-1.pc"), pc)

        # c-utf8：c-dvar 消费其头文件与静态归档
        cutf8 = self.dependencies["c-utf8"]
        libdirs = " ".join("-L" + d for d in cutf8.cpp_info.libdirs)
        pc8 = "\n".join([
            "prefix=" + cutf8.package_folder,
            "includedir=" + cutf8.cpp_info.includedirs[0],
            "libdir=" + cutf8.cpp_info.libdirs[0],
            "",
            "Name: libcutf8",
            "Description: c-utf8 UTF-8 Handling in Standard ISO-C11 (conan shim)",
            "URL: https://github.com/c-util/c-utf8",
            "Version: " + str(cutf8.ref.version),
            "Libs: " + libdirs + " -lcutf8-1",
            "Cflags: " + " ".join("-I" + d for d in cutf8.cpp_info.includedirs),
            "",
        ])
        save(self, os.path.join(self.generators_folder, "libcutf8-1.pc"), pc8)

        tc = MesonToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        env_prefix = (
            "PATH=/data/service/hnp/bin:$PATH "
            "CC=/data/service/hnp/bin/clang "
            "AR=/data/service/hnp/bin/llvm-ar "
            "PKG_CONFIG_PATH=%s:$PKG_CONFIG_PATH " % self.generators_folder
        )
        # Meson 工具类不加载自定义 env，按 account-utils 1.4.0 先例手动执行
        self.run(
            env_prefix +
            "meson setup %s %s --buildtype=release" % (self.build_folder, self.source_folder),
            cwd=self.build_folder,
            env="conanbuild",
        )
        self.run(
            "PATH=/data/service/hnp/bin:$PATH meson compile -C %s -j1" % self.build_folder,
            env="conanbuild",
        )
        # 上游测试套件（4 项：API Symbol Visibility / Basic API Behavior /
        # D-Bus String Restrictions / Type and Signature Parser；
        # Enumerated Types 测试需可选依赖 libdbus-typenum，上游默认 required:false）
        self.run(
            "PATH=/data/service/hnp/bin:$PATH meson test -C %s --print-errorlogs" % self.build_folder,
            env="conanbuild",
        )

    def package(self):
        # HMDFS 上不做 meson install（符号链接链易碎），按产物实体拷贝
        # （上游 install_headers 在 src/ 子目录，头文件随 src/ 平铺安装）
        copy(self, "c-dvar*.h", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "*.a", src=os.path.join(self.build_folder, "src"),
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        if self.options.shared:
            # .so / .so.0 符号链接按内容实体化拷贝，链接器可用
            copy(self, "*.so", src=os.path.join(self.build_folder, "src"),
                 dst=os.path.join(self.package_folder, "lib"), keep_path=False)
            copy(self, "*.so.*", src=os.path.join(self.build_folder, "src"),
                 dst=os.path.join(self.package_folder, "lib"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["cdvar-1"]
        self.cpp_info.set_property("cmake_file_name", "c-dvar")
        self.cpp_info.set_property("cmake_target_name", "c-dvar::c-dvar")
        self.cpp_info.set_property("pkg_config_name", "libcdvar-1")
