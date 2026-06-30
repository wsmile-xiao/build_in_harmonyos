#!/usr/bin/env python3
"""Conan recipe template — Autotools projects (configure + make).

Usage: Replace Ocaml, ocaml, 4.14.3, ocaml 4.14.3, MIT,
       Fill in requires(), configure_args, and cpp_info.libs as needed.

This template enforces R26: static linking for terminal tools.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class OcamlConan(ConanFile):
    name = "ocaml"
    version = "4.14.3"
    description = "General purpose programming language in the ML family"
    license = "LGPL-2.1-only WITH OCaml-LGPL-linking-exception"
    homepage = "https://ocaml.org/"
    url = ""  # CI fills this

    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)
        self.folders.build = "."  # OCaml requires in-source build

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: Terminal tools must be statically linked
        tc.extra_ldflags.append("-static")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # Fix umask 077 in generated config.status (HarmonyOS SELinux restriction E046)
        if os.path.exists("config.status"):
            with open("config.status", "r") as f:
                content = f.read()
            content = content.replace("umask 077", "umask 002")
            with open("config.status", "w") as f:
                f.write(content)
            self.run("bash config.status", env="conanbuild")
        # Fix ASM detection: configure picks llvm-as which doesn't support GNU asm
        if os.path.exists("Makefile.config"):
            with open("Makefile.config", "r") as f:
                content = f.read()
            content = content.replace("ASM=llvm-as", "ASM=as")
            with open("Makefile.config", "w") as f:
                f.write(content)
        # Fix secure_getenv: detected by configure but not declared in HarmonyOS headers
        s_h = "runtime/caml/s.h"
        if os.path.exists(s_h):
            with open(s_h, "r") as f:
                lines = f.readlines()
            new_lines = []
            for line in lines:
                if "HAS_SECURE_GETENV" in line and "#undef" not in line:
                    new_lines.append("/* #undef HAS_SECURE_GETENV */\n")
                else:
                    new_lines.append(line)
            with open(s_h, "w") as f:
                f.writelines(new_lines)
        # Remove boot/ocamlrun to avoid cp permission error during coldstart
        if os.path.exists("boot/ocamlrun"):
            os.remove("boot/ocamlrun")
        # OCaml requires -j1 (jobserver mkfifo fails on HarmonyOS E046)
        self.run("make -j1", env="conanbuild")

    def package(self):
        # DESTDIR redirects install to Conan package folder (prefix=/ from configure)
        self.run(f"make install DESTDIR={self.package_folder}", env="conanbuild")

    def package_info(self):
        # OCaml installs headers to lib/caml/ and libraries to lib/
        self.cpp_info.includedirs = ["lib"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["camlrun", "asmrun", "unix", "threads"]
