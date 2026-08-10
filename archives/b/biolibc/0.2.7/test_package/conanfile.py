#!/usr/bin/env python3
"""Consumer smoke test for biolibc 0.2.7."""

import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import Environment


class BiolibcTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv", "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "test_biolibc.c"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("libxtend/0.2.1")

    def generate(self):
        tmp_dir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        env = Environment()
        env.define("TMP", tmp_dir)
        env.define("TEMP", tmp_dir)
        env.define("TMPDIR", tmp_dir)
        env.vars(self).save_script("biolibc_test_build")

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

    def _dependency_flags(self):
        includes = []
        libdirs = []
        libs = []
        defines = []
        for name in ("biolibc", "libxtend"):
            cpp_info = self.dependencies[name].cpp_info
            includes.extend(f'-I"{path}"' for path in cpp_info.includedirs)
            libdirs.extend(f'-L"{path}"' for path in cpp_info.libdirs)
            libs.extend(f"-l{lib}" for lib in cpp_info.libs)
            defines.extend(f"-D{define}" for define in cpp_info.defines)
        if str(self.settings.os) == "OHOS":
            defines.extend(["-Dstrlcpy=xt_strlcpy", "-Dstrlcat=xt_strlcat"])
        return " ".join(defines + includes + libdirs + libs)

    def build(self):
        exe = "test_biolibc.exe" if os.name == "nt" else "test_biolibc"
        self.run(
            f'{self._compiler()} "{os.path.join(self.source_folder, "test_biolibc.c")}" '
            f'{self._conf_flags("tools.build:cflags")} '
            f'-o {exe} {self._dependency_flags()} '
            f'{self._conf_flags("tools.build:exelinkflags")}',
            cwd=self.build_folder,
            env=["conanbuild", "biolibc_test_build"],
        )

    def test(self):
        if not can_run(self):
            self.output.info("Skipping biolibc consumer smoke because target binaries cannot run")
            return
        exe = "test_biolibc.exe" if os.name == "nt" else "./test_biolibc"
        self.run(exe, cwd=self.build_folder, env="conanrun")
