#!/usr/bin/env python3
"""Conan recipe for lfanew — MS-DOS MZ stub tool plus a small C support library.

Upstream: https://gitlab.com/tkchia/lfanew (tag 20230825, TK Chia).
Payload: the `lfanew` CLI (add .e_lfanew to an MZ stub / stubify / unstubify),
the static library `libfanew.a` and the headers <lfanew/*.h>, <nexgen/*.h>.

HarmonyOS PC (aarch64) adaptation points:
  - The shipped config.sub (2016) rejects the conan triplet aarch64-linux-ohos,
    so configure gets --host=aarch64-unknown-linux-musl (OHOS libc is musl);
    the shipped config.guess (2016) cannot identify a native HarmonyOS build
    machine, so on OHOS builders --build gets the same triplet (E007).
  - configure creates its config.status scratch dir under `umask 077`, which
    HMDFS turns into an unwritable setgid dir; relaxed to 022 (E129).
  - a/direntdup.c uses NAME_MAX without including <limits.h>; glibc pulls it in
    via <dirent.h>, OHOS musl does not (patches/0001-a-direntdup.c.patch).
  - AR/RANLIB come from the llvm directory of the profile compiler: the OHOS
    SDK ships llvm-ar but no llvm-ranlib, so RANLIB is "llvm-ar s".
  - lfanew only needs libc, so it is linked with -static (knowledge E544):
    no dependency on the musl loader path at run time.
  - Only `make install` targets (program, headers, library) are built; the
    default target would also build Takeda's MS-DOS player with a MinGW
    cross compiler, 7z and upx, which is test tooling, not package payload.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches, get,
                               replace_in_file)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LfanewConan(ConanFile):
    name = "lfanew"
    version = "0-20230825"
    description = ("Tool to add .e_lfanew to MS-DOS MZ stubs and to (un)stubify "
                   "PE programs, with a small C portability library")
    license = ("MPL-2.0", "BSD-3-Clause")
    homepage = "https://gitlab.com/tkchia/lfanew"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("mz", "pe", "msdos", "executable", "stub")

    # Ships a static library + headers for consumers and a CLI in bin/.
    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        # Pure C project.
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _c_compiler(self):
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        return compilers.get("c", "clang")

    @staticmethod
    def _llvm_ar(cc):
        cc_path = shutil.which(cc) or cc
        candidate = os.path.join(os.path.dirname(os.path.realpath(cc_path)), "llvm-ar")
        if os.path.isfile(candidate):
            return candidate
        return shutil.which("llvm-ar") or "ar"

    def generate(self):
        VirtualBuildEnv(self).generate()
        tc = AutotoolsToolchain(self)
        if self.settings.os == "OHOS":
            # config.sub from 2016 does not know "ohos"; OHOS libc is musl.
            tc.update_configure_args({"--host": "aarch64-unknown-linux-musl"})
        if self.settings_build.os == "OHOS":
            # config.guess from 2016 cannot identify `uname -s` = HarmonyOS
            # ("cannot guess build type") on native OHOS builders; name the
            # build machine with the same musl triplet (build == host, so
            # configure keeps its native, non-cross semantics).
            tc.update_configure_args({"--build": "aarch64-unknown-linux-musl"})
        # libc-only CLI: link statically (E544).
        tc.extra_ldflags.append("-static")
        cc = self._c_compiler()
        ar = self._llvm_ar(cc)
        env = tc.environment()
        env.define("CC", cc)
        env.define("AR", ar)
        env.define("RANLIB", f"{ar} s")
        tc.generate(env)

    def build(self):
        apply_conandata_patches(self)
        # E129: on HMDFS a `umask 077` directory gets setgid and is not even
        # owner-writable, so config.status cannot write ./confXXXXXX/subs1.awk.
        replace_in_file(self, os.path.join(self.source_folder, "configure"),
                        "umask 077", "umask 022")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(target="lfanew a/libfanew.a", args=["-j1"])

    def package(self):
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["fanew"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "lfanew")
        self.cpp_info.set_property("cmake_target_name", "lfanew::lfanew")
        self.cpp_info.set_property("pkg_config_name", "lfanew")
