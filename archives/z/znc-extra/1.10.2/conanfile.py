#!/usr/bin/env python3
"""znc-extra —— ZNC 1.10.2 的 11 个模块（对应 Alpine community/znc 的 znc-extra 子包）。

这些模块是 CMake 的 MODULE 类型 .so（PREFIX "" / NO_SONAME / hidden visibility），
运行时由 znc 宿主进程 dlopen 加载：模块对 ZNC 核心符号的引用由宿主可执行文件
（src/CMakeLists.txt 中 ENABLE_EXPORTS true）在装载时解析。因此本配方只打包
模块本身，znc 主程序、核心库、基础模块与头文件归 znc 主包，不在本子包内。
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    rm,
    rmdir,
)

# 与 Alpine community/znc 的 extra() 子包一致（11 个模块）
EXTRA_MODULES = (
    "autovoice",
    "block_motd",
    "clearbufferonmsg",
    "ctcpflood",
    "flooddetach",
    "imapauth",
    "listsockets",
    "log",
    "notify_connect",
    "send_raw",
    "shell",
)


class ZncExtraConan(ConanFile):
    name = "znc-extra"
    version = "1.10.2"
    description = (
        "Extra ZNC 1.10.2 modules (autovoice, block_motd, clearbufferonmsg, "
        "ctcpflood, flooddetach, imapauth, listsockets, log, notify_connect, "
        "send_raw, shell) loaded by the znc host at runtime"
    )
    license = "Apache-2.0"
    homepage = "https://znc.in"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "shared-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.6")
        self.requires("zlib/1.3.1.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # 只保留模块所需的组件；Perl/Python/TCL 模块语言绑定与 i18n 均不打包
        tc.variables["WANT_OPENSSL"] = "YES"
        tc.variables["WANT_ZLIB"] = "YES"
        tc.variables["WANT_CYRUS"] = "NO"
        tc.variables["WANT_ICU"] = "NO"
        tc.variables["WANT_ARGON"] = "NO"
        tc.variables["WANT_I18N"] = "NO"
        tc.variables["WANT_PERL"] = "OFF"
        tc.variables["WANT_PYTHON"] = "OFF"
        tc.variables["WANT_SWIG"] = "NO"
        # 只构建本子包交付的 11 个模块（modules/CMakeLists.txt 支持 moddisable_<模块>）；
        # 其余模块归 znc 主包，其中 savebuff 使用 OHOS libc 未提供的 getpass()
        for entry in sorted(os.listdir(os.path.join(self.source_folder, "modules"))):
            if entry.endswith(".cpp") and entry[: -len(".cpp")] not in EXTRA_MODULES:
                tc.variables["moddisable_{}".format(entry[: -len(".cpp")])] = "true"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

        # 只保留 znc-extra 的 11 个模块，其余产物（znc 主程序、核心库、
        # 基础模块、头文件）属于 znc 主包
        mod_dir = os.path.join(self.package_folder, "lib", "znc")
        keep = {"{}.so".format(mod) for mod in EXTRA_MODULES}
        for entry in sorted(os.listdir(mod_dir)):
            if entry not in keep:
                rm(self, entry, mod_dir)
        for sub in ("bin", "include", "share", "etc", "data"):
            rmdir(self, os.path.join(self.package_folder, sub))
        lib_dir = os.path.join(self.package_folder, "lib")
        for entry in sorted(os.listdir(lib_dir)):
            if entry == "znc":
                continue
            path = os.path.join(lib_dir, entry)
            if os.path.isdir(path):
                rmdir(self, path)
            else:
                rm(self, entry, lib_dir)

    def package_info(self):
        # 模块由 znc 宿主 dlopen 加载，不作为可链接库/可执行文件暴露
        self.cpp_info.bindirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "znc-extra")
