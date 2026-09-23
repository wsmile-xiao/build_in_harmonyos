#!/usr/bin/env python3
"""Conan recipe — c-siphash 1.1.0 (c-util, Streaming-capable SipHash Implementation).

C11 + meson；产物：头文件 c-siphash.h + 库 csiphash-1（静态/共享）。
依赖 c-stdaux >= 1.5.0（头文件库，上游 pkg-config 名 libcstdaux-1）。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, save, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import MesonToolchain
from conan.tools.layout import basic_layout


class CSiphashConan(ConanFile):
    name = "c-siphash"
    version = "1.1.0"
    description = "c-siphash — Streaming-capable SipHash-2-4 pseudo-random function (c-util)"
    license = "Apache-2.0"
    homepage = "https://github.com/c-util/c-siphash"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("c-stdaux/1.6.0")

    def build_requirements(self):
        self.tool_requires("meson/1.11.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # 上游 meson.build 以 dependency('libcstdaux-1') 消费 c-stdaux，并读取
        # pc 变量 cflags / version_scripts。conan 依赖名 (c-stdaux) 与上游
        # pkg-config 名 (libcstdaux-1) 不同：PkgConfigDeps 只能生成 c-stdaux.pc，
        # meson 命中不了，因此手写 libcstdaux-1.pc shim 指向真实依赖包
        # （仓库先例：abiword-plugin-* 3.0.8 对 glib-2.0 的 shim 处理）。
        # cflags 变量取 c-stdaux 上游 get_supported_arguments 在本平台
        # clang 15 的实测生效集合（与 meson 子项目直接构建的 build.ninja 一致）。
        dep = self.dependencies["c-stdaux"]
        includes = " ".join("-I" + d for d in dep.cpp_info.includedirs)
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
            "prefix=" + dep.package_folder,
            "includedir=" + dep.cpp_info.includedirs[0],
            "",
            "Name: libcstdaux",
            "Description: c-stdaux auxiliary macros for ISO-C11 (conan shim)",
            "URL: https://github.com/c-util/c-stdaux",
            "Version: " + str(dep.ref.version),
            "Libs:",
            "Cflags: " + includes,
            "cflags=" + cflags,
            "version_scripts=yes",
            "",
        ])
        save(self, os.path.join(self.generators_folder, "libcstdaux-1.pc"), pc)

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
        # 上游测试套件（2 项：API Symbol Visibility / Basic API Behavior）
        self.run(
            "PATH=/data/service/hnp/bin:$PATH meson test -C %s --print-errorlogs" % self.build_folder,
            env="conanbuild",
        )

    def package(self):
        # HMDFS 上不做 meson install（符号链接链易碎），按产物实体拷贝
        # （上游 install_headers 在 src/ 子目录，头文件随 src/ 平铺安装）
        copy(self, "c-siphash.h", src=os.path.join(self.source_folder, "src"),
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
        self.cpp_info.libs = ["csiphash-1"]
        self.cpp_info.set_property("cmake_file_name", "c-siphash")
        self.cpp_info.set_property("cmake_target_name", "c-siphash::c-siphash")
        self.cpp_info.set_property("pkg_config_name", "libcsiphash-1")
