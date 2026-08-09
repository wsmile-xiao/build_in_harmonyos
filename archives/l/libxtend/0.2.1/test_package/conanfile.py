#!/usr/bin/env python3
"""Consumer smoke test for libxtend 0.2.1."""

import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import Environment


class LibxtendTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv", "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "test_libxtend.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _compiler(self):
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        compiler = str(compilers.get("c", "clang"))
        if os.path.isabs(compiler) and os.path.exists(compiler):
            return compiler.replace("\\", "/")
        lookup = os.path.basename(compiler) if os.path.isabs(compiler) else compiler
        found = shutil.which(lookup)
        return (found or "clang").replace("\\", "/")

    def _conf_flags(self, name):
        values = self.conf.get(name, default=[], check_type=list) or []
        return " ".join(str(value) for value in values)

    def generate(self):
        tmp_dir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        env = Environment()
        if os.name == "nt":
            env.prepend_path("PATH", "E:/Git/usr/bin")
            env.prepend_path("PATH", "E:/mingw64/bin")
        env.define("TMP", tmp_dir)
        env.define("TEMP", tmp_dir)
        env.define("TMPDIR", tmp_dir)
        env.vars(self).save_script("libxtend_test_build")

    def build(self):
        dep = self.dependencies["libxtend"].cpp_info
        includes = " ".join(f'-I"{path}"' for path in dep.includedirs)
        libdirs = " ".join(f'-L"{path}"' for path in dep.libdirs)
        libs = " ".join(f"-l{lib}" for lib in dep.libs)
        exe = "test_libxtend.exe" if os.name == "nt" else "test_libxtend"
        self.run(
            f'{self._compiler()} "{os.path.join(self.source_folder, "test_libxtend.c")}" '
            f'{self._conf_flags("tools.build:cflags")} '
            f'-o {exe} {includes} {libdirs} {libs} '
            f'{self._conf_flags("tools.build:exelinkflags")}',
            cwd=self.build_folder,
            env=["conanbuild", "libxtend_test_build"],
        )

    def test(self):
        if not can_run(self):
            self.output.warning("Skipping libxtend consumer smoke because target binaries cannot run")
            return
        exe = "test_libxtend.exe" if os.name == "nt" else "./test_libxtend"
        self.run(exe, cwd=self.build_folder, env="conanrun")
