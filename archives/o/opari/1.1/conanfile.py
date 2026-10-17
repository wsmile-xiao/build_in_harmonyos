#!/usr/bin/env python3
"""Conan recipe for opari 1.1 — OPARI: OpenMP Pragma And Region Instrumentor.

OPARI is a *source-to-source* OpenMP instrumentation tool (a C++ command-line
binary) plus the libpomp measurement runtime (a C, static library). The upstream
ships hand-written Makefiles (no autotools / cmake), so this recipe compiles the
tool and the runtime manually with the OHOS clang toolchain.

Build model
-----------
1. Tool  (``opari`` binary): compile the 8 C++ translation units in ``tool/``
   and link them. The tool is platform-independent (no OpenMP runtime needed).
2. Lib   (``libpomp.a``)   : compile ``lib/pomp_lib.c`` with ``-fopenmp``
   (it needs ``omp.h``) and archive it. ``lib/pomp_fwrapper.c`` is excluded:
   it is the Fortran-facing wrapper and depends on an auto-generated
   ``pomp_fwrapper_def.h``; the C runtime only requires ``pomp_lib.o``.
3. Upstream C test suite (R51): run the existing ``tool/Test/c_test.sh`` and
   ``tool/Test/table_test.sh c`` diff-based tests. Fortran tests (f77/f90) are
   excluded because the OHOS SDK provides no gfortran (documented reason).

The consumer side (test_package) instruments a C OpenMP program with the opari
tool, compiles + links it against libpomp and libomp, and runs it on aarch64
OHOS — proving the whole pipeline is feasible on the target platform.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout


class OpariConan(ConanFile):
    name = "opari"
    version = "1.1"
    description = "OPARI: OpenMP Pragma And Region Instrumentor (tool + libpomp runtime)"
    license = "GPL-2.0-or-later"
    homepage = "https://www.fz-juelich.de/ias/jsc/opari/"
    url = ""  # CI fills this

    # Ships both a command-line tool (bin/) and the libpomp static library.
    # libpomp is a measurement runtime that MUST be linked into the
    # instrumented executable (it carries the POMP callbacks), so it is
    # static-only by design — the shared variant is rejected below.
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    # Portability patches shipped alongside the recipe (declared in
    # conandata.yml). Declared explicitly so `conan create` exports them even
    # when the recipe is consumed straight from the cache.
    exports_sources = "patches/*"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("opari supports Linux/OHOS only")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "opari libpomp is static-only (the POMP runtime must be "
                "linked into the instrumented executable)"
            )

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        # Ship the portability patches declared in conandata.yml with the
        # exported recipe, so `apply_conandata_patches` can find them.
        copy(self, "*.patch", self.recipe_folder, self.export_sources_folder)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def _compilers(self):
        comp = self.conf.get(
            "tools.build:compiler_executables", check_type=dict, default={}
        )
        cxx = comp.get("cpp", "clang++")
        cc = comp.get("c", "clang")
        ar = comp.get("ar", "llvm-ar")
        return cxx, cc, ar

    def build(self):
        cxx, cc, ar = self._compilers()
        src = self.source_folder
        tool_dir = os.path.join(src, "tool")
        lib_dir = os.path.join(src, "lib")

        # --- 1. Build the opari instrumentation tool (C++) -------------------
        tool_units = [
            "opari.cc", "process_c.cc", "process_f.cc", "process_omp.cc",
            "ompragma.cc", "ompragma_c.cc", "ompragma_f.cc", "handler.cc",
        ]
        objs = []
        for unit in tool_units:
            obj = os.path.join(self.build_folder, os.path.splitext(unit)[0] + ".o")
            self.run(
                f"{cxx} -O2 -c {os.path.join(tool_dir, unit)} -o {obj}",
                env="conanbuild",
            )
            objs.append(obj)
        opari_bin = os.path.join(self.build_folder, "opari")
        self.run(f"{cxx} -O2 -o {opari_bin} {' '.join(objs)}", env="conanbuild")

        # --- 2. Build libpomp.a (C measurement runtime) ----------------------
        # pomp_lib.c needs omp.h -> compile with -fopenmp. Fortran wrapper
        # (pomp_fwrapper.c) is intentionally excluded (see module docstring).
        pomp_o = os.path.join(self.build_folder, "pomp_lib.o")
        self.run(
            f"{cc} -fopenmp -O2 -I{lib_dir} "
            f"-c {os.path.join(lib_dir, 'pomp_lib.c')} -o {pomp_o}",
            env="conanbuild",
        )
        libpomp = os.path.join(self.build_folder, "libpomp.a")
        self.run(f"{ar} rcs {libpomp} {pomp_o}", env="conanbuild")

        # --- 3. Upstream C test suite (R51) ----------------------------------
        # Copy the freshly built tool next to its own Makefile so the existing
        # upstream shell tests (which reference ../opari) run unchanged.
        copy(self, "opari", self.build_folder, tool_dir)
        test_dir = os.path.join(tool_dir, "Test")
        # Fortran tests (f77/f90) excluded: no gfortran in the OHOS SDK.
        self.run("sh c_test.sh", cwd=test_dir, env="conanbuild")
        self.run("sh table_test.sh c", cwd=test_dir, env="conanbuild")

    def package(self):
        src = self.source_folder
        copy(self, "opari", self.build_folder,
             os.path.join(self.package_folder, "bin"))
        copy(self, "libpomp.a", self.build_folder,
             os.path.join(self.package_folder, "lib"))
        copy(self, "pomp_lib.h", os.path.join(src, "lib"),
             os.path.join(self.package_folder, "include"))
        copy(self, "opari_omp.h", os.path.join(src, "lib"),
             os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libs = ["pomp"]
        # Make the opari tool discoverable on PATH for consumers / tests.
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
