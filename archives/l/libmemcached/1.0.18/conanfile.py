#!/usr/bin/env python3
"""Conan recipe — libmemcached 1.0.18 for HarmonyOS (arm64)."""
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.files import apply_conandata_patches, get, copy, rm, rmdir, export_conandata_patches, save
from conan.tools.layout import basic_layout
import os
import glob


class LibmemcachedConan(ConanFile):
    name = "libmemcached"
    version = "1.0.18"
    description = "libmemcached is a C client library for interfacing to a memcached server"
    license = "BSD-3-Clause"
    homepage = "https://libmemcached.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False], "sasl": [True, False]}
    default_options = {"shared": False, "fPIC": True, "sasl": False}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def layout(self):
        basic_layout(self, src_folder="src")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS", "FreeBSD"):
            raise ConanInvalidConfiguration(f"{self.ref} is not supported on {self.settings.os}.")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True, destination=self.source_folder)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-dependency-tracking")
        if not self.options.sasl:
            tc.configure_args.append("--disable-sasl")
        tc.generate()
        AutotoolsDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        compile_script = os.path.join(self.source_folder, "build-aux", "compile")
        if not os.path.exists(compile_script):
            save(self, compile_script, "#! /bin/sh\nscriptversion=2018-03-07.03\ncompiler=$1; shift\nsrc=; dest=\nwhile test $# -gt 0; do\n  case $1 in\n    -o) shift; dest=$1 ;;\n    -c) ;;\n    *) if test -z \"$src\"; then src=$1; fi ;;\n  esac\n  shift\ndone\nif test -z \"$src\" || test -z \"$dest\"; then exec $compiler \"$@\"; fi\ndest_dir=$(dirname \"$dest\") && mkdir -p \"$dest_dir\"\ntmpfile=./tmp$$\n$compiler -c \"$src\" -o \"$tmpfile\" || exit $?\nmv \"$tmpfile\" \"$dest\" || exit $?\nexit 0\n")
        autotools = Autotools(self)
        autotools.configure()
        for f in ["aclocal.m4", "configure", "Makefile.in", "config.h.in"]:
            p = os.path.join(self.source_folder, f)
            if os.path.exists(p):
                os.utime(p, None)
        for p in glob.glob(os.path.join(self.source_folder, "**", "Makefile.in"), recursive=True):
            os.utime(p, None)
        autotools.make(args=["-j1"])

    def package(self):
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        for pc_file in glob.glob(os.path.join(self.package_folder, "lib", "pkgconfig", "*.pc")):
            with open(pc_file, "r") as f:
                content = f.read()
            content = content.replace("prefix=/", "prefix=${pcfiledir}/../..")
            with open(pc_file, "w") as f:
                f.write(content)
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.libs = ["memcached"]
        self.cpp_info.system_libs = ["m", "c++"]
        self.cpp_info.set_property("pkg_config_name", "libmemcached")
