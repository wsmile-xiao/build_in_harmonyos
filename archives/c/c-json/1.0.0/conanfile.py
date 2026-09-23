#!/usr/bin/env python3
"""Conan recipe — c-json 1.0.0 (c-util, Streaming-capable JSON Implementation).

C11 + meson；产物：头文件 c-json.h + 库 cjson-1（静态/共享）+ json-validate 工具（测试用）。
依赖 c-stdaux >=（无版本约束，实测 1.6.0）与 c-utf8（pkg-config 名 libcstdaux-1/libcutf8-1）。
上游 src/test-reader 为 python 脚本测试（317 个 JSON 数据文件），运行约 55s，
conanfile 的 meson test 以 --timeout-multiplier=20 放宽 meson 默认 30s 超时。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, save, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import MesonToolchain
from conan.tools.layout import basic_layout


class CJsonConan(ConanFile):
    name = "c-json"
    version = "1.0.0"
    description = "c-json — Streaming-capable JSON Implementation (c-util)"
    license = "Apache-2.0"
    homepage = "https://github.com/c-util/c-json"
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
        # 注意 c-json 读的是连字符形式 'version-scripts'，两个拼写都提供。
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
            "version-scripts=yes",
            "",
        ])
        save(self, os.path.join(self.generators_folder, "libcstdaux-1.pc"), pc)

        # c-utf8 头文件库 shim：头文件 + 静态归档（cpp_info 无 libs 也可能存在 .a）
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
        # 上游测试套件（2 项：test-basic / test-reader）。test-reader 为脚本测试，
        # 遍历 test/ 下 317 个 JSON 样例（本平台实测约 55s），放宽 meson 默认 30s 超时。
        self.run(
            "PATH=/data/service/hnp/bin:$PATH meson test -C %s --print-errorlogs --timeout-multiplier=20" % self.build_folder,
            env="conanbuild",
        )

    def package(self):
        # HMDFS 上不做 meson install（符号链接链易碎），按产物实体拷贝
        # （上游 install_headers 在 src/ 子目录，头文件随 src/ 平铺安装）
        copy(self, "c-json.h", src=os.path.join(self.source_folder, "src"),
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
        self.cpp_info.libs = ["cjson-1"]
        self.cpp_info.set_property("cmake_file_name", "c-json")
        self.cpp_info.set_property("cmake_target_name", "c-json::c-json")
        self.cpp_info.set_property("pkg_config_name", "libcjson-1")
