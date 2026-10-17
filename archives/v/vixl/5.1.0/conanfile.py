#!/usr/bin/env python3
"""Conan recipe — vixl 5.1.0 (SCons).

VIXL is ARM's AArch32/AArch64 runtime code generation library: assemblers,
disassemblers and an AArch64 simulator.  It is a pure C++ static library
built with the upstream SCons build system and has no external runtime
dependencies.
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class VixlConan(ConanFile):
    name = "vixl"
    version = "5.1.0"
    description = "VIXL: AArch32 and AArch64 runtime code generation library"
    license = "BSD-3-Clause"
    homepage = "https://github.com/Linaro/vixl"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    # SCons is installed into an isolated prefix during generate() (same
    # approach as gpsd / dxx-rebirth): it is not a Conan package, and
    # installing it here keeps build() free of network/pip calls (R33).
    _SCONS_VERSION = "4.10.1"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def layout(self):
        # SCons is an in-source build (obj/ lives next to SConstruct), so keep
        # source and build folders identical.
        basic_layout(self)
        self.folders.build = "."

    def generate(self):
        scons_prefix = os.path.join(self.build_folder, "_scons_env")
        os.makedirs(scons_prefix, exist_ok=True)

        # Install SCons into the isolated prefix (offline-friendly: pip uses
        # the configured community index; no system-wide pollution).
        self.run(
            f"python3 -m pip install --quiet --no-input "
            f"--target={scons_prefix} scons=={self._SCONS_VERSION}",
            env="build",
        )

        # OHOS has no /bin/sh — point SCons' POSIX shell at the system shell.
        self.run(
            f"PYTHONPATH={scons_prefix} python3 -c \""
            r"import SCons.Platform.posix as m;"
            r"f=m.__file__;"
            r"s=open(f).read();"
            r"old=r\"env['SHELL']          = 'sh'\";"
            r"new=r\"env['SHELL']          = '/system/bin/sh'\";"
            r"open(f,'w').write(s.replace(old,new) if old in s else s);"
            r"print('scons-shell-patched')"
            "\"",
            env="build",
        )

        VirtualBuildEnv(self).generate()

        env = Environment()
        env.define_path("PYTHONPATH", scons_prefix)
        env.vars(self).save_script("scons_env")

    def build(self):
        apply_conandata_patches(self)

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang")
        cxx = compilers.get("cpp", "clang++")

        ccflags = "-fPIC" if self.options.get_safe("fPIC", False) else ""

        # OHOS clang toolchain ships llvm-ar / llvm-ranlib next to clang;
        # plain `ar`/`ranlib` are not on PATH (SConstruct reads AR/RANLIB
        # from the environment via RetrieveEnvironmentVariables).
        bindir = os.path.dirname(str(cc))
        ar = os.path.join(bindir, "llvm-ar") if bindir else "llvm-ar"
        ranlib = os.path.join(bindir, "llvm-ranlib") if bindir else "llvm-ranlib"

        # Upstream default target is auto (a64+a32+t32 on a 64-bit host).
        # simulator=aarch64 keeps the simulator component compiled on an
        # AArch64 host too, so the shipped static library exposes all three
        # components (assembler / disassembler / simulator) and the upstream
        # test suite can exercise the simulator tests.
        #
        # VIXL's SConstruct reads CC/CXX/AR/RANLIB/CCFLAGS from the environment
        # (RetrieveEnvironmentVariables), NOT as scons command-line options —
        # passing them on the command line trips "Unknown build options".
        self.run(
            f"CC=\"{cc}\" CXX=\"{cxx}\" AR=\"{ar}\" RANLIB=\"{ranlib}\" "
            f"CCFLAGS=\"{ccflags}\" "
            f"python3 -m SCons -j1 std=c++14 mode=release simulator=aarch64"
        )

    def package(self):
        # Headers keep their upstream subdirectory layout (src/*.h plus
        # src/aarch32/*.h and src/aarch64/*.h); consumers include e.g.
        # "aarch64/macro-assembler-aarch64.h".
        copy(self, "*.h",
             src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "*.h",
             src=os.path.join(self.source_folder, "src", "aarch32"),
             dst=os.path.join(self.package_folder, "include", "aarch32"))
        copy(self, "*.h",
             src=os.path.join(self.source_folder, "src", "aarch64"),
             dst=os.path.join(self.package_folder, "include", "aarch64"))

        # SCons places the static archive under obj/<variant>/libvixl.a and
        # symlinks obj/latest to it.  Locate it robustly via glob (the symlink
        # may be unavailable on HMDFS).
        candidates = glob.glob(
            os.path.join(self.source_folder, "obj", "**", "libvixl.a"),
            recursive=True,
        )
        if not candidates:
            raise ConanException("libvixl.a not found under obj/")
        copy(self, "libvixl.a",
             src=os.path.dirname(candidates[0]),
             dst=os.path.join(self.package_folder, "lib"))

        copy(self, "LICENCE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["vixl"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "vixl")
        self.cpp_info.set_property("cmake_target_name", "VIXL::vixl")
