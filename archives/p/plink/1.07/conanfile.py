#!/usr/bin/env python3
"""Conan recipe for PLINK 1.07 — whole-genome association analysis toolset.

Upstream ships a single hand-written Makefile (no configure, no test target).
The only build-time adaptation required for a modern toolchain is a
three-file variable-shadowing fix (see patches/0001); everything else is
compiler/sysroot supplied.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class PlinkConan(ConanFile):
    name = "plink"
    version = "1.07"
    description = (
        "PLINK is a whole-genome association analysis toolset: it filters and "
        "summarises genotype data, tests SNP-by-disease associations, and "
        "converts between PED/PLINK text formats and the binary BED format."
    )
    license = ("GPL-2.0-only", "LGPL-2.1-only")  # Rconnection.* (Rserve client) is LGPL-2.1
    homepage = "http://pngu.mgh.harvard.edu/purcell/plink/"
    url = ""  # CI fills this
    topics = ("genetics", "gwas", "association", "bioinformatics", "plink", "ped", "bed")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"plink 1.07 only supports Linux and OHOS, got {self.settings.os}"
            )

    def layout(self):
        # PLINK 1.07 is an in-tree hand-written Makefile build: every object is
        # compiled with -I. next to the sources and linked from the source dir.
        # Keeping source and build in one folder is what makes
        # apply_conandata_patches() and make operate on the same tree — with
        # basic_layout() Conan copies the sources into a separate build folder
        # first, so the patches land in the copy's *source* folder while make
        # runs in the unpatched *build* folder and the shadowing error resurfaces.
        self.folders.source = "src"
        self.folders.build = "src"

    def requirements(self):
        # Upstream Makefile: WITH_ZLIB=1 -> LIB += -lz, compiled from zfstream.cpp.
        self.requires("zlib/1.3.1")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Patches MUST be applied here, not in build(): source() runs in the
        # export tree and only afterwards does Conan copy the sources into the
        # build tree, so patching in build() would modify the export tree while
        # make() compiles the untouched copy (the shadowing error reappears).
        apply_conandata_patches(self)

    def _cxx(self):
        """Resolve the C++ compiler from the profile conf, never from the shell.

        R33: build() must not rely on shell variables (${CXX}/${CXXFLAGS}); on a
        release worker those are empty and the build silently degrades.
        """
        conf = self.conf.get("tools.build:compiler_executables", default={})
        cxx = conf.get("cpp") if isinstance(conf, dict) else None
        if cxx and os.path.isfile(cxx) and os.access(cxx, os.X_OK):
            return cxx
        for name in ("aarch64-unknown-linux-ohos-clang++", "clang++", "g++"):
            found = shutil.which(name)
            if found:
                return found
        raise ConanException("no usable C++ compiler found (conf path dead, none on PATH)")

    def _zlib_flags(self):
        """Include/link flags for the zlib dependency, taken from the dependency itself."""
        dep = self.dependencies["zlib"].cpp_info.aggregated_components()
        includes = " ".join(f"-isystem {os.path.normpath(d)}" for d in dep.includedirs)
        libdirs = " ".join(f"-L{os.path.normpath(d)}" for d in dep.libdirs)
        libs = " ".join(f"-l{name}" for name in dep.libs)
        return includes, f"{libdirs} {libs}".strip()

    def build(self):
        cxx = self._cxx()
        zlib_inc, zlib_link = self._zlib_flags()

        # Upstream Makefile knobs that matter:
        #   SYS=UNIX         -> CXXFLAGS += -DUNIX, CXX = $(CXX_UNIX)
        #   (default)        -> CXXFLAGS += -static
        #   WITH_R_PLUGINS=1 -> LIB += -ldl -lcrypt   (Rserve client, r.cpp/Rconnection.cpp)
        #   WITH_ZLIB=1      -> LIB += -lz            (zfstream.cpp)
        # CXX and LIB are passed on the make command line on purpose: the Makefile
        # only ever appends to CXXFLAGS, and a command-line CXXFLAGS would suppress
        # those in-Makefile appends (make command-line vars override Makefile ones).
        # Injecting the zlib paths through CXX/LIB therefore keeps every upstream
        # -DUNIX/-static/-DWITH_R_PLUGINS/-DWITH_ZLIB decision intact.
        # -lcrypt/-ldl resolve to the empty stub archives in the OHOS NDK sysroot;
        # the symbols themselves live in musl libc.a.
        make_cmd = (
            f'make SYS=UNIX CXX="{cxx} {zlib_inc}" '
            f'LIB="-ldl -lcrypt {zlib_link} -lpthread -lm"'
        )

        # Upstream 1.07 registers no test target. Run the conventional one once
        # anyway so the build log carries the verbatim reason instead of an
        # assumption (T009: never infer "no tests" from `make -n`).
        self.run(f"{make_cmd} check", cwd=self.build_folder, env=None, ignore_errors=True)

        # PLINK 1.07 has a few very large single-file translation units
        # (elf.cpp, model.cpp, sets.cpp) that -O3 turns into multi-hundred-MB
        # clang processes. Uncapped parallelism (a 32-core build host asks for
        # -j32) risks OOM on a smaller CI worker, so cap it.
        jobs = self.conf.get("tools.build:jobs", default=0)
        try:
            jobs = int(jobs)
        except (TypeError, ValueError):
            jobs = 0
        if jobs <= 0:
            jobs = os.cpu_count() or 1
        jobs = max(1, min(jobs, 4))

        self.run(f"{make_cmd} -j{jobs}", cwd=self.build_folder, env=None)

    def package(self):
        src = self.source_folder
        copy(self, "plink", self.build_folder, os.path.join(self.package_folder, "bin"))
        # Upstream ships these two example files; the test package analyses them,
        # so they travel with the binary instead of being duplicated in the recipe.
        share = os.path.join(self.package_folder, "share", "plink")
        copy(self, "test.ped", src, share)
        copy(self, "test.map", src, share)
        copy(self, "README.txt", src, share)
        copy(self, "COPYING.txt", src, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
