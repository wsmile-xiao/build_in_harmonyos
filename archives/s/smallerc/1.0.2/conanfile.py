#!/usr/bin/env python3
"""Conan recipe for Smaller C 1.0.2."""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class SmallerCConan(ConanFile):
    name = "smallerc"
    version = "1.0.2"
    description = "Simple single-pass C compiler for x86 and MIPS targets"
    license = "BSD-2-Clause"
    homepage = "https://github.com/alexfru/SmallerC"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        # smlrcc invokes NASM when producing object files and executables.
        self.requires("nasm/2.16.03", run=True)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(
            self,
            **self.conan_data["sources"][self.version],
            filename=f"smallerc-{self.version}.tar.gz",
            strip_root=True,
        )

    def generate(self):
        VirtualBuildEnv(self).generate()
        # NASM is a runtime dependency of the compiler driver and is also used
        # while the native OHOS build regenerates Smaller C's target libraries.
        VirtualRunEnv(self).generate(scope="build")

    def _compiler(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get("c")
        if compiler:
            return compiler
        if cross_building(self):
            raise ConanInvalidConfiguration(
                "cross builds require tools.build:compiler_executables[c]"
            )
        return "cc"

    def _flags(self, conf_name, defaults=()):
        configured = self.conf.get(conf_name, default=[], check_type=list) or []
        return " ".join([*defaults, *(str(value) for value in configured)])

    def _sdk_llvm_libdir(self):
        if str(self.settings.os) != "OHOS":
            return ""
        compiler = os.path.realpath(self._compiler())
        llvm_libdir = os.path.join(
            os.path.dirname(os.path.dirname(compiler)), "lib"
        )
        return llvm_libdir if os.path.isdir(llvm_libdir) else ""

    def build(self):
        build_flags = {
            "Debug": ("-O0", "-g"),
            "Release": ("-O2", "-DNDEBUG"),
            "RelWithDebInfo": ("-O2", "-g", "-DNDEBUG"),
            "MinSizeRel": ("-Os", "-DNDEBUG"),
        }
        cflags = self._flags(
            "tools.build:cflags",
            ("-pipe", "-Wall", *build_flags[str(self.settings.build_type)]),
        )
        ldflags = self._flags("tools.build:exelinkflags")
        makefile = os.path.join(self.source_folder, "GNUmakefile")
        variables = [
            f"CC={shlex.quote(self._compiler())}",
            f"CFLAGS={shlex.quote(cflags)}",
        ]
        if ldflags:
            variables.append(f"LDFLAGS={shlex.quote(ldflags)}")

        # The repository's OHOS profile is a native build/host profile. It can
        # execute the freshly built smlrcc while regenerating all target
        # libraries and dpstub.exe from source.
        build_env = Environment()
        for variable in (
            "CPPFLAGS",
            "LDFLAGS",
            "CPATH",
            "C_INCLUDE_PATH",
            "CPLUS_INCLUDE_PATH",
            "LIBRARY_PATH",
        ):
            build_env.unset(variable)

        # Persistent workers can expose ~/usr/local/lib through LD_LIBRARY_PATH.
        # That directory may contain a libxml2.so.16 incompatible with the SDK
        # lld. Keep the SDK's matching llvm/lib first while retaining any paths
        # needed by the generated Conan environments.
        sdk_llvm_libdir = self._sdk_llvm_libdir()
        if sdk_llvm_libdir:
            build_env.prepend_path("LD_LIBRARY_PATH", sdk_llvm_libdir)

        with build_env.vars(self).apply():
            self.run(
                f"make -f {shlex.quote(makefile)} {' '.join(variables)} all",
                cwd=self.build_folder,
                env=["conanbuild", "conanrun"],
            )

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        smlrc_root = os.path.join(self.package_folder, "smlrc")

        for executable in ("smlrc", "smlrl", "smlrcc", "smlrpp", "n2f"):
            copy(
                self,
                executable,
                src=self.build_folder,
                dst=bin_dir,
                keep_path=False,
            )

        copy(
            self,
            "*",
            src=os.path.join(self.source_folder, "v0100", "include"),
            dst=os.path.join(smlrc_root, "include"),
        )
        copy(
            self,
            "*.a",
            src=self.build_folder,
            dst=os.path.join(smlrc_root, "lib"),
            keep_path=False,
        )
        copy(
            self,
            "dpstub.exe",
            src=self.build_folder,
            dst=os.path.join(smlrc_root, "lib"),
            keep_path=False,
        )
        copy(
            self,
            "*.md",
            src=os.path.join(self.source_folder, "v0100", "doc"),
            dst=os.path.join(self.package_folder, "share", "doc", "smallerc"),
            keep_path=False,
        )
        copy(
            self,
            "license.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

        if os.name != "nt":
            for executable in ("smlrc", "smlrl", "smlrcc", "smlrpp", "n2f"):
                os.chmod(os.path.join(bin_dir, executable), 0o755)

    def package_info(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        smlrc_root = os.path.join(self.package_folder, "smlrc")
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.buildenv_info.prepend_path("PATH", bin_dir)
        self.buildenv_info.define_path("SMLRC", smlrc_root)
        self.runenv_info.prepend_path("PATH", bin_dir)
        self.runenv_info.define_path("SMLRC", smlrc_root)
