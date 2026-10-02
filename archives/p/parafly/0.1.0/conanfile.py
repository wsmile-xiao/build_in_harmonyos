#!/usr/bin/env python3
"""Conan recipe for ParaFly 0.1.0 built with Autotools."""

import re
import shlex
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ParaflyConan(ConanFile):
    name = "parafly"
    version = "0.1.0"
    description = "Parallel command processing utility using OpenMP"
    license = "BSD-3-Clause"
    homepage = "https://github.com/ParaFly/ParaFly"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, filename="parafly-0.1.0.tar.gz", **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsToolchain(self).generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        # The upstream Git snapshot contains a stale generated config.status;
        # Autoconf rejects it when Conan performs the out-of-tree build.
        for folder in (Path(self.source_folder), Path(self.build_folder)):
            (folder / "config.status").unlink(missing_ok=True)
        autotools.configure()

        # The upstream Makefile hard-codes -m64. Also locate the OpenMP header
        # beside the sysroot selected by Conan's configured C++ compiler.
        compiler_executables = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cxx = compiler_executables.get("cpp", "clang++")
        compiler_path = Path(shutil.which(cxx) or cxx).resolve()
        sdk_llvm = compiler_path.parent.parent
        omp_include = sdk_llvm / "include"
        if not (omp_include / "omp.h").is_file():
            probe = subprocess.run(
                [cxx, "-v", "-E", "-x", "c++", "/dev/null"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False
            )
            sysroot_match = re.search(r"-isysroot\s+(\S+)", probe.stdout + probe.stderr)
            if not sysroot_match:
                raise RuntimeError("Unable to find the OHOS SDK sysroot from the configured C++ compiler")
            sdk_llvm = Path(sysroot_match.group(1)).parent / "llvm"
            omp_include = sdk_llvm / "include"
        if not (omp_include / "omp.h").is_file():
            raise RuntimeError(f"OpenMP header not found at {omp_include / 'omp.h'}")

        # Override upstream -m64 and provide the SDK's OpenMP header/runtime;
        # Conan's CXXFLAGS still supply the configured target and sysroot.
        am_cxxflags = f"AM_CXXFLAGS=-fopenmp -I{omp_include} -L{sdk_llvm / 'lib'}"
        autotools.make(args=["-j1", shlex.quote(am_cxxflags)])

        # The upstream manual test points at a checked-in x86_64 binary.
        # Run its original test files against the rebuilt OHOS executable.
        build_root = Path(self.build_folder)
        test_root = build_root / "test"
        bin_root = build_root / "bin"
        test_root.mkdir(parents=True, exist_ok=True)
        bin_root.mkdir(parents=True, exist_ok=True)
        # Replace the snapshot's bundled x86_64 binary in Conan's build copy;
        # the upstream test Makefile resolves ../bin/ParaFly from test/.
        shutil.copy2(Path(self.build_folder) / "src" / "ParaFly", bin_root / "ParaFly")
        for filename in ("Makefile", "cmds.txt", "rand_exit.pl"):
            shutil.copy2(Path(self.source_folder) / "test" / filename, test_root / filename)
        self.run("make test", cwd=str(test_root))

    def package(self):
        Autotools(self).install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", str(Path(self.package_folder) / "bin"))
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
