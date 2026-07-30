#!/usr/bin/env python3
"""Conan recipe for libchardet 1.0.6.

The requested package name is libchardet; the matching upstream project and
installed library are Joungkyun/libchardet and libchardet.
"""

import glob
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    get,
    replace_in_file,
    rmdir,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibchardetConan(ConanFile):
    name = "libchardet"
    version = "1.0.6"
    description = "C/C++ API for Mozilla's universal charset detector"
    license = "MPL-1.1 OR LGPL-2.1-or-later OR GPL-2.0-or-later"
    homepage = "https://github.com/Joungkyun/libchardet"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }
    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)
        apply_conandata_patches(self)

    def _tool_from_compiler_dir(self, tool_name, fallback):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        compiler = compilers.get("c") or compilers.get("cpp") or ""
        bindir = os.path.dirname(compiler) if os.path.isabs(compiler) else ""
        if bindir:
            candidate = os.path.join(bindir, tool_name)
            if os.path.isfile(candidate):
                return candidate
        return fallback

    def generate(self):
        if self.settings.os == "OHOS":
            configure_path = os.path.join(self.source_folder, "configure")
            replace_in_file(self, configure_path, "#! /bin/sh", "#!/system/bin/sh", strict=False)
            replace_in_file(self, configure_path, "umask 077", "umask 002", strict=False)

        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--prefix=/")
        tc.configure_args.append("--disable-dependency-tracking")
        if self.settings.os == "OHOS":
            tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")

        source_include = os.path.join(self.source_folder, "include").replace("\\", "/")
        tc.extra_cflags.append(f"-I{source_include}")
        tc.extra_cxxflags.append(f"-I{source_include}")

        env = tc.environment()
        env.define("AR", self._tool_from_compiler_dir("llvm-ar", "llvm-ar"))
        env.define("RANLIB", self._tool_from_compiler_dir("llvm-ranlib", "llvm-ranlib"))
        env.define("STRIP", self._tool_from_compiler_dir("llvm-strip", "llvm-strip"))
        env.define("NM", self._tool_from_compiler_dir("llvm-nm", "llvm-nm"))
        env.define("LD", self._tool_from_compiler_dir("ld.lld", "ld.lld"))
        tc.generate(env)

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["-j1"])
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))

        for la_file in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(la_file)

        config_script = os.path.join(self.package_folder, "bin", "chardet-config")
        if os.path.exists(config_script):
            os.remove(config_script)
        rmdir(self, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.libs = ["chardet"]
        self.cpp_info.includedirs = ["include/chardet", "include"]
        self.cpp_info.set_property("cmake_file_name", "libchardet")
        self.cpp_info.set_property("cmake_target_name", "libchardet::libchardet")
        self.cpp_info.set_property("pkg_config_name", "chardet")
