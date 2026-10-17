#!/usr/bin/env python3
"""Conan recipe for cdb — DJB constant database tools and library (20251021 release).

cdb creates and reads constant databases: an associative array on disk with
fixed-time lookups. This is the 2025-10-21 maintained release from
https://cdb.cr.yp.to/ (adds cdb64, a 64-bit hash/offset variant).

Build system is djbware: `conf-cc`/`conf-ld`/`conf-home` first-line config
files plus generated ./compile/./load/./makelib wrappers. There is no
configure compile-probe, so the build is cross-friendly: `make prog` builds
all tools and static libraries without running any built binary.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save


class CdbConan(ConanFile):
    name = "cdb"
    version = "20251021"
    description = "cdb: creates and reads constant databases (DJB cdb, 2025 maintained release, with cdb64)"
    license = "Public Domain"
    homepage = "https://cdb.cr.yp.to/"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def validate(self):
        # R32: OHOS platform compatibility
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # zero dependencies: pure C, libc only

    def layout(self):
        self.folders.build = "."
        self.folders.generators = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # R33: compiler/tool paths come from Conan conf, never bare shell env.
    def _cc(self):
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        return compilers.get("c", "clang")

    def _ar(self):
        cc = self._cc()
        if os.sep in cc:
            return os.path.join(os.path.dirname(cc), "llvm-ar")
        return "ar"

    def _ranlib(self):
        ar = self._ar()
        if os.sep in ar:
            return os.path.join(os.path.dirname(ar), "llvm-ranlib")
        return "ranlib"

    def _cflags(self):
        flags = ["-fPIC", "-O2"]
        if self.settings.os in ("Linux", "OHOS"):
            # pkgsrc parity: expose POSIX prototypes (mmap, lseek) under -std=c99
            flags.append("-D_XOPEN_SOURCE=500")
        return " ".join(flags)

    def _ldflags(self):
        # R33: linker selection via Conan conf only. No override by default —
        # the OHOS clang default linker works on devices and CI workers; some
        # workers needed GNU ld to avoid an lld/libxml2.so.16 issue, in which
        # case set user.cdb:ld (name or absolute path) in the profile.
        ld = self.conf.get("user.cdb:ld", default=None)
        return f"-fuse-ld={ld}" if ld else ""

    def build(self):
        apply_conandata_patches(self)

        # djbware config: only the first line of each conf-* file matters
        save(self, "conf-cc",
             f"{self._cc()} {self._cflags()}\n\n"
             "This will be used to compile .c files.\n")
        ld_line = self._cc()
        if self._ldflags():
            ld_line += f" {self._ldflags()}"
        save(self, "conf-ld",
             f"{ld_line}\n\n"
             "This will be used to link .o files into an executable.\n")
        # cdbmake-12/cdbmake-sv scripts bake <conf-home>/bin/<tool> paths;
        # the Conan cache package folder is stable, so point there.
        save(self, "conf-home",
             f"{self.package_folder}\n\n"
             "This is the cdb home directory. Programs will be installed in .../bin.\n")

        # `make prog` builds all binaries + static libraries but, unlike the
        # default `it`/`setup` targets, never runs DJB's instcopy/instcheck
        # (which would execute freshly built binaries and copy into
        # conf-home); packaging is done in package() instead. R9: -j1.
        env = Environment()
        env.define("AR", self._ar())
        env.define("RANLIB", self._ranlib())
        # HarmonyOS workers keep /tmp read-only; clang needs a writable temp dir
        env.define("TMPDIR", self.build_folder)
        with env.vars(self).apply():
            self.run("make prog -j1")

    def package(self):
        # Binaries (from `prog` target; mirrors upstream hier.c install list)
        bins = ["cdbget", "cdbmake", "cdbdump", "cdbstats", "cdbtest",
                "cdbmake-12", "cdbmake-sv",
                "cdb64get", "cdb64make", "cdb64dump", "cdb64stats",
                "cdb64test", "cdb64make-12", "cdb64make-sv"]
        for b in bins:
            copy(self, b, src=self.build_folder,
                 dst=os.path.join(self.package_folder, "bin"))

        # Public headers: cdb.h/cdb_make.h pull in num.h/outbuf.h
        for h in ["cdb.h", "cdb_make.h", "num.h", "outbuf.h"]:
            copy(self, h, src=self.build_folder,
                 dst=os.path.join(self.package_folder, "include"))

        # Upstream installs only the commands; consumers also need the
        # library (pkgsrc installs cdb.a/cdb64.a the same way). Linking a
        # binary requires cdb.a + buffer.a + unix.a + byte.a together, so
        # merge all archive members into one self-contained libcdb.a.
        # cdb64_* symbols are macro-renamed (no clash with cdb_*).
        ar, ranlib = self._ar(), self._ranlib()
        merge = os.path.join(self.build_folder, "libmerge")
        os.makedirs(merge, exist_ok=True)
        for archive in ["cdb.a", "cdb64.a", "buffer.a", "unix.a", "byte.a"]:
            self.run(f'{ar} x "{os.path.join(self.build_folder, archive)}"', cwd=merge)
        objs = sorted(f for f in os.listdir(merge) if f.endswith(".o"))
        self.run(f'{ar} cr libcdb.a {" ".join(objs)}', cwd=merge)
        self.run(f"{ranlib} libcdb.a", cwd=merge)
        copy(self, "libcdb.a", src=merge,
             dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["cdb"]
        self.cpp_info.bindirs = ["bin"]
