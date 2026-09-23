#!/usr/bin/env python3
"""Conan test_package for libopenaptx 0.2.0 — L1 consumer test.

test.c compiles against the packaged library (include <openaptx.h>, link
-lopenaptx) and asserts the codec contracts documented in openaptx.h:
4:1 byte ratio per 24-byte stereo frame, deterministic encode, frame-aligned
decode minus the documented 23-frame encoder latency, and round-trip
fidelity within 1% of the signal amplitude.

The include/library paths are passed explicitly from the tested package's
cpp_info (absolute) instead of relying on the generated AutotoolsDeps
environment, which is not applied to the test_package build() shell here.
"""
import os

from conan import ConanFile


class LibopenaptxTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # runtime env: LD_LIBRARY_PATH for the packaged shared library
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies[self.tested_reference_str]
        cpp = dep.cpp_info.aggregated_components()
        inc_dirs = cpp.includedirs or [os.path.join(dep.package_folder, "include")]
        lib_dirs = cpp.libdirs or [os.path.join(dep.package_folder, "lib")]
        inc = " ".join(f'-I"{d}"' for d in inc_dirs)
        lib = " ".join(f'-L"{d}"' for d in lib_dirs)
        cc = os.environ.get("CC", "clang")
        self.run(f'{cc} test.c -o test_libopenaptx {inc} {lib} -lopenaptx -lm')

    def test(self):
        # The shared library comes from the package.  The loader must be
        # pointed at the package libdir with an absolute path: cpp_info libdirs
        # are relative and OHOS musl ignores DT_RUNPATH, so the generated
        # conanrun LD_LIBRARY_PATH alone is not enough (§12.38③).
        # OHOS: wrap binary execution with bash (mksh cannot execute ELF).
        dep = self.dependencies[self.tested_reference_str]
        libdir = os.path.join(dep.package_folder, "lib")
        bash = os.environ.get("CONFIG_SHELL") or next(
            (p for p in (
                "/data/service/hnp/bin/bash",
                "/bin/bash",
                "/usr/bin/bash",
            ) if os.path.exists(p)),
            "bash",
        )
        self.run(f'LD_LIBRARY_PATH="{libdir}:$LD_LIBRARY_PATH" '
                 f'{bash} -c "./test_libopenaptx"', env="conanrun")
