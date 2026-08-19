#!/usr/bin/env python3
"""Conan recipe for argbash 2.11.0 — Bash argument parsing code generator.

Argbash is a pure shell script tool that generates bash argument parsing code
from m4 macros. It uses autom4te (part of autoconf) to bootstrap the main
argbash script from m4 source files.

Build process:
1. make bootstrap — generates bin/argbash from src/*.m4 using autom4te
2. bash bin/argbash src/argbash-init.m4 -o bin/argbash-init
3. bash bin/argbash src/argbash-1to2.m4 -o bin/argbash-1to2
4. Manual install — copies scripts and m4 files to package folder

On HarmonyOS (OHOS):
- autom4te is available at /data/service/hnp/bin/autom4te (autoconf 2.72)
- No C/C++ compilation needed — pure shell/m4 scripts
- chmod +x doesn't work (E046, SELinux), so invoke via bash
- chmod --reference not supported (affects argbash-1to2 only, non-critical)
"""
import os
import re

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class ArgbashConan(ConanFile):
    name = "argbash"
    version = "2.11.0"
    description = "Argbash is an argument parser generator for Bash"
    license = "MIT"
    homepage = "https://argbash.dev"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # R38: argbash is a command-line tool (application), not a library
    package_type = "application"

    # Pure shell script tool — no compiler or build_type needed
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # argbash has no runtime dependencies (pure shell script)

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: settings.os check must include both Linux and OHOS
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"argbash supports only Linux and OHOS, got: {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R33: use self.source_folder for paths, not undefined shell variables
        resources_dir = os.path.join(self.source_folder, "resources")
        bin_dir = os.path.join(self.source_folder, "bin")
        src_dir = os.path.join(self.source_folder, "src")
        argbash = os.path.join(bin_dir, "argbash")

        # Bootstrap: generate argbash script from m4 sources using autom4te
        self.run("make bootstrap", cwd=resources_dir, env="conanbuild")

        # OHOS: chmod +x doesn't work (E046, SELinux restriction), so we
        # invoke argbash via bash instead of direct execution.
        # Build argbash-init from argbash-init.m4
        self.run(f'bash {argbash} {os.path.join(src_dir, "argbash-init.m4")} '
                 f'-o {os.path.join(bin_dir, "argbash-init")}',
                 cwd=resources_dir, env="conanbuild")
        # Build argbash-1to2 from argbash-1to2.m4
        self.run(f'bash {argbash} {os.path.join(src_dir, "argbash-1to2.m4")} '
                 f'-o {os.path.join(bin_dir, "argbash-1to2")}',
                 cwd=resources_dir, env="conanbuild")

    def package(self):
        src = self.source_folder
        pkg = self.package_folder

        # Copy executable scripts to bin/
        copy(self, "argbash", os.path.join(src, "bin"), os.path.join(pkg, "bin"))
        copy(self, "argbash-init", os.path.join(src, "bin"), os.path.join(pkg, "bin"))
        copy(self, "argbash-1to2", os.path.join(src, "bin"), os.path.join(pkg, "bin"))

        # Copy m4 library files to lib/argbash/
        m4_src = os.path.join(src, "src")
        m4_dst = os.path.join(pkg, "lib", "argbash")
        copy(self, "*.m4", m4_src, m4_dst)
        copy(self, "version", m4_src, m4_dst)

        # Patch m4dir in argbash to use relative path from bin/ to lib/argbash/
        argbash_path = os.path.join(pkg, "bin", "argbash")
        if os.path.isfile(argbash_path):
            with open(argbash_path, "r") as f:
                content = f.read()
            content = re.sub(
                r'm4dir=.*',
                'm4dir="$script_dir/../lib/argbash"',
                content,
            )
            with open(argbash_path, "w") as f:
                f.write(content)

    def package_info(self):
        # argbash is a CLI tool — bindirs for executables, libdirs for m4 files
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
