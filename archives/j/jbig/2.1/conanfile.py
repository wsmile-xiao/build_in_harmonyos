#!/usr/bin/env python3
"""Conan recipe for jbig 2.1 (JBIG-KIT) — bi-level image compression library.

Pure C, Makefile build (libjbig + pbmtools). Self-contained, no external
deps. Produces libjbig.a (static) + jbig/pbm tools.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout


class JbigConan(ConanFile):
    name = "jbig"
    version = "2.1"
    description = "JBIG-KIT — lossless bi-level image compression (JBIG1)"
    license = "GPL-2.0"
    homepage = "https://www.cl.cam.ac.uk/~mgk25/jbigkit/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # Makefile build: libjbig (static lib). The Makefile defaults to
        # CC=gcc (not on OHOS) and `export CC CFLAGS` re-exports its own
        # value to sub-makes — pass CC/AR as make command-line args (highest
        # priority, propagates to sub-makes).
        self.run(
            'make lib CC=/data/service/hnp/bin/clang '
            'AR=/data/service/hnp/bin/llvm-ar',
            cwd=self.source_folder,
        )

    def package(self):
        # Copy static lib + public headers
        copy(self, "libjbig.a",
             src=os.path.join(self.source_folder, "libjbig"),
             dst=os.path.join(self.package_folder, "lib"))
        for h in ("jbig.h", "jbig85.h", "jbig_ar.h"):
            copy(self, h,
                 src=os.path.join(self.source_folder, "libjbig"),
                 dst=os.path.join(self.package_folder, "include"))
        # Verify artifacts
        lib = os.path.join(self.package_folder, "lib", "libjbig.a")
        hdr = os.path.join(self.package_folder, "include", "jbig.h")
        if not os.path.isfile(lib):
            raise ConanException(f"libjbig.a missing: {lib}")
        if not os.path.isfile(hdr):
            raise ConanException(f"jbig.h missing: {hdr}")

    def package_info(self):
        self.cpp_info.libs = ["jbig"]
