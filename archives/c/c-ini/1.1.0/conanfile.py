#!/usr/bin/env python3
"""Conan recipe — c-ini 1.1.0 (c-util, Ini-File Handling).

C11 + meson；产物：头文件 c-ini.h + 库 cini-1（静态/共享）。
依赖 c-list（header-only）、c-rbtree、c-stdaux、c-utf8（上游 pkg-config 名
libclist-3/libcrbtree-3/libcstdaux-1/libcutf8-1）。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, save, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import MesonToolchain
from conan.tools.layout import basic_layout


class CIniConan(ConanFile):
    name = "c-ini"
    version = "1.1.0"
    description = "c-ini — Ini-File Handling (c-util)"
    license = "Apache-2.0"
    homepage = "https://github.com/c-util/c-ini"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("c-list/3.1.0")
        self.requires("c-rbtree/3.2.0")
        self.requires("c-stdaux/1.6.0")
        self.requires("c-utf8/1.1.0")

    def build_requirements(self):
        self.tool_requires("meson/1.11.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # 上游 meson.build 以 dependency('libclist-3'/'libcrbtree-3'/'libcstdaux-1'/
        # 'libcutf8-1') 消费同族依赖。conan 依赖名与上游 pkg-config 名不同：
        # PkgConfigDeps 生成的 .pc 无法命中，因此手写 4 个同名 shim
        # （仓库先例：abiword-plugin-* 对 glib-2.0，同族 c-* 1.1.0/3.2.0 同款）。
        # c-stdaux 侧提供上游读取的 pc 变量 cflags 与 version_scripts；c-utf8/
        # c-rbtree 是真库需 Libs；c-list 3.1.0 上游为 header-only（无编译产物）。
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

        clist = self.dependencies["c-list"]
        pcl = "\n".join([
            "prefix=" + clist.package_folder,
            "includedir=" + clist.cpp_info.includedirs[0],
            "",
            "Name: libclist",
            "Description: c-list Circular Intrusive Double Linked List Collection (conan shim)",
            "URL: https://github.com/c-util/c-list",
            "Version: " + str(clist.ref.version),
            "Libs:",
            "Cflags: " + " ".join("-I" + d for d in clist.cpp_info.includedirs),
            "",
        ])
        save(self, os.path.join(self.generators_folder, "libclist-3.pc"), pcl)

        for dep_name, pc_name, lib_base in (("c-rbtree", "libcrbtree-3", "crbtree-3"),
                                            ("c-utf8", "libcutf8-1", "cutf8-1")):
            dep = self.dependencies[dep_name]
            libdirs = " ".join("-L" + d for d in dep.cpp_info.libdirs)
            pcd = "\n".join([
                "prefix=" + dep.package_folder,
                "includedir=" + dep.cpp_info.includedirs[0],
                "libdir=" + dep.cpp_info.libdirs[0],
                "",
                "Name: " + pc_name.lstrip("lib"),
                "Description: " + dep_name + " (conan shim)",
                "URL: https://github.com/c-util/" + dep_name,
                "Version: " + str(dep.ref.version),
                "Libs: " + libdirs + " -l" + lib_base,
                "Cflags: " + " ".join("-I" + d for d in dep.cpp_info.includedirs),
                "",
            ])
            save(self, os.path.join(self.generators_folder, pc_name + ".pc"), pcd)

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
        # 上游测试套件（3 项：API Symbol Visibility / Basic API Behavior /
        # Parser Capabilities）
        self.run(
            "PATH=/data/service/hnp/bin:$PATH meson test -C %s --print-errorlogs" % self.build_folder,
            env="conanbuild",
        )

    def package(self):
        # HMDFS 上不做 meson install（符号链接链易碎），按产物实体拷贝
        # （上游 install_headers 在 src/ 子目录，头文件随 src/ 平铺安装）
        copy(self, "c-ini.h", src=os.path.join(self.source_folder, "src"),
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
        self.cpp_info.libs = ["cini-1"]
        self.cpp_info.set_property("cmake_file_name", "c-ini")
        self.cpp_info.set_property("cmake_target_name", "c-ini::c-ini")
        self.cpp_info.set_property("pkg_config_name", "libcini-1")
