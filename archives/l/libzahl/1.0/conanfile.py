#!/usr/bin/env python3
"""Conan recipe — libzahl 1.0 (Makefile)"""

import json
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class LibzahlConan(ConanFile):
    name = "libzahl"
    version = "1.0"
    description = "Suckless big integer library for arbitrary size integers"
    license = "ISC"
    homepage = "https://git.suckless.org/libzahl"
    url = "https://github.com/maandree/libzahl"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler_tools(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return (
            executables.get("c", "clang"),
            executables.get("ar", "llvm-ar"),
            executables.get("ranlib", "llvm-ranlib"),
        )

    def validate(self):
        if self.options.shared:
            raise ConanInvalidConfiguration("libzahl 1.0 supports only static builds")

    def build(self):
        apply_conandata_patches(self)
        cc, ar, ranlib = self._compiler_tools()
        # Upstream config.mk pins `-O3`. On HarmonyOS aarch64 (clang 15) the
        # Karatsuba multiply miscomputes: `./test` aborts with
        # `Failure at line 953: zcmp(c, d), expected == 0, but got -1`
        # (1e9 * 1e18 != 1e27) while earlier narrower asserts pass — a codegen
        # symptom, not an algorithmic one (same sources pass with gcc/x86_64).
        # `-O2 -fno-strict-aliasing -fwrapv` still failed the same assert in
        # the 2026-09-16 preflight, so drop to strictly unoptimised `-O0`
        # (keeping -fno-strict-aliasing -fwrapv for the hand-written carry
        # chains); no test is weakened.
        cflags = "-std=c99 -O0 -Wall -pedantic -fno-strict-aliasing -fwrapv"
        make_args = (
            f"CC={shlex.quote(cc)} AR={shlex.quote(ar)} "
            f"RANLIB={shlex.quote(ranlib)} "
            f"CFLAGS={shlex.quote(cflags)} -j1"
        )
        # Ensure flag changes take effect even if conan reuses the source
        # tree: drop stale objects built with older optimisation levels.
        self.run("make clean", cwd=self.source_folder, ignore_errors=True)
        # Generate the random-test companion explicitly with the HMBS python
        # instead of relying on the script's shebang + exec bit (HMDFS
        # reports chmod as unsupported). Same generator, same content.
        python3 = os.environ.get("HMBS_PYTHON3") or "python3"
        self.run(
            f"{shlex.quote(python3)} test-generate.py > test-random.c",
            cwd=self.source_folder,
        )
        generated = os.path.join(self.source_folder, "test-random.c")
        if os.path.getsize(generated) == 0:
            raise ConanException(
                "test-random.c is empty: upstream random suite would be "
                "silently skipped; refusing to continue"
            )
        # 1. Build the static library (upstream `all` target is libzahl.a only).
        self.run(f"make {make_args} libzahl.a", cwd=self.source_folder)
        # 2. Upstream official test suite: `make check` builds `test`
        # (test.c + generated test-random.c) and runs ./test.
        self.run(f"make {make_args} test", cwd=self.source_folder)
        self.run("./test", cwd=self.source_folder)
        upstream_result = {
            "status": "passed",
            "framework": "make",
            "command": f"make {make_args} test && ./test",
            "discovered": 1,
            "executed": 1,
            "passed": 1,
            "failed": 0,
            "skipped": 0,
        }
        marker = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_result)
        self.output.info(marker)
        print(marker, flush=True)

    def package(self):
        copy(self, "zahl.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "libzahl.a", src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["zahl"]
