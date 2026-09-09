#!/usr/bin/env python3
"""Conan recipe for clips 6.3 — CLIPS rule-based expert system (upstream 6.30).

CLIPS ("C" Language Integrated Production System) is NASA's public-domain
forward-chaining rule engine. This packages the 6.30 core source (the 6.3
series release; the task/request version label is "6.3", the upstream file is
clips_core_source_630.zip from SourceForge).

Build system is a plain set of makefiles: `makefiles/makefile.lib` compiles
core/*.c (all sources except main.c) with -DALLOW_ENVIRONMENT_GLOBALS=0 into
libclips.a. The interactive `clips` binary is then linked from main.c against
that library — exactly the usage the makefile itself documents:
`gcc -o clips main.c -L. -lm -lclips`.

Zero external dependencies: pure C, libc + libm only.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class ClipsConan(ConanFile):
    name = "clips"
    version = "6.3"
    description = "CLIPS: NASA rule-based expert system shell and embeddable C library (6.3 series / 6.30 core source)"
    license = "Public Domain"  # upstream "CLIPS License Information" — MIT-style permission notice
    homepage = "https://www.clipsrules.net/"
    url = ""

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def validate(self):
        # R32: OHOS platform compatibility
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def configure(self):
        # Upstream makefile.lib produces a static library only (ar cq); the
        # sources are not prepared for a shared build (no visibility control,
        # upstream ships no .so). Keep the option surface honest and refuse
        # shared instead of silently packaging a static lib.
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "clips 6.3 is static-only: upstream makefile.lib builds libclips.a via ar")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # zero dependencies: pure C, libc + libm only

    def layout(self):
        # In-source makefile build (objects land in core/, like upstream).
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
        # LINUX selects the POSIX branch in core/sysdep.c (sys/time.h,
        # gettimeofday/clock_gettime for gentime) and reports "LINUX" from
        # the (operating-system) function — same flag Debian uses. OHOS is a
        # Linux kernel, so this branch applies directly. -fPIC keeps the
        # static archive usable from shared-library consumers.
        return "-DLINUX -fPIC"

    def build(self):
        apply_conandata_patches(self)

        cc, ar, ranlib = self._cc(), self._ar(), self._ranlib()
        cflags = self._cflags()

        # 1) libclips.a from all core sources except main.c (makefile.lib).
        #    Pure compile + ar + ranlib — no build-time execution of built
        #    binaries, so it is cross-compile safe. R9: -j1.
        # 2) interactive `clips` binary from main.c + the library, per the
        #    usage documented inside makefile.lib itself.
        env = Environment()
        # HarmonyOS workers keep /tmp read-only; clang needs a writable temp dir
        env.define("TMPDIR", self.build_folder)
        with env.vars(self).apply():
            self.run(
                f"make -C core -f ../makefiles/makefile.lib "
                f"CC=\"{cc}\" AR=\"{ar}\" RANLIB=\"{ranlib}\" "
                f"CFLAGS=\"{cflags}\" -j1 libclips.a")
            self.run(
                f"\"{cc}\" {cflags} -o clips main.c libclips.a -lm",
                cwd=os.path.join(self.build_folder, "core"))

    def package(self):
        copy(self, "libclips.a", src=os.path.join(self.source_folder, "core"),
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "clips", src=os.path.join(self.source_folder, "core"),
             dst=os.path.join(self.package_folder, "bin"))
        # clips.h is the umbrella header but pulls in the whole family
        # (setup.h/evaluatn.h/envrnmnt.h/... via #include "..."); install all
        # public headers flat, as upstream/Debian do.
        copy(self, "*.h", src=os.path.join(self.source_folder, "core"),
             dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["clips"]
        self.cpp_info.bindirs = ["bin"]
