#!/usr/bin/env python3
"""Conan recipe — letter-shell 3.1.2 (custom clang build).

letter-shell is an embedded shell library written in C99.  The upstream
repository ships raw C sources without a build system (copy-into-project
style, see demo/x86-gcc).  Sources are compiled directly with the Conan
toolchain compiler and archived with llvm-ar.  Static by default; consumers
link the shellCommand section through the provided linker fragment.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class LetterShellConan(ConanFile):
    name = "letter-shell"
    version = "3.1.2"
    description = "A small, powerful embedded shell for C projects"
    license = "MIT"
    homepage = "https://github.com/NevermindZZT/letter-shell"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    exports = "shellcmds.lds"

    def export_sources(self):
        export_conandata_patches(self)
        # ship the linker fragment into the source tree so package() can copy it
        copy(self, "shellcmds.lds", src=self.recipe_folder,
             dst=self.export_sources_folder)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c") or "clang"
        ar = compilers.get("ar") or "llvm-ar"
        src = self.source_folder
        cflags = "-fPIC -O2 -Isrc"
        objs = []
        for f in ("shell.c", "shell_cmd_list.c", "shell_companion.c", "shell_ext.c"):
            o = os.path.join(src, f.replace(".c", ".o"))
            self.run(f"{cc} {cflags} -c {os.path.join('src', f)} -o {o}",
                     cwd=src)
            objs.append(o)
        if self.options.shared:
            self.run(f"{cc} -shared {' '.join(objs)} -o libletter-shell.so",
                     cwd=src)
        else:
            self.run(f"{ar} rcs libletter-shell.a {' '.join(objs)}",
                     cwd=src)

    def package(self):
        copy(self, "shell.h", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "shell_ext.h", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "shell_cfg.h", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "libletter-shell.a", src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "libletter-shell.so", src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # Linker fragment defining the shellCommand section symbols
        # (equivalent to the upstream demo's shell.lds KEEP(*shellCommand)).
        copy(self, "shellcmds.lds", src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["letter-shell"]
        self.cpp_info.set_property("cmake_target_name", "letter-shell::letter-shell")