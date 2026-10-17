#!/usr/bin/env python3
"""Conan recipe template — Autotools projects (configure + make).

Usage: Replace Gperftools, gperftools, perftools-1.6, gperftools perftools-1.6, MIT, 
       Fill in requires(), configure_args, and cpp_info.libs as needed.

This template enforces R26: static linking for system-name libraries.
"""
import os

from conan import ConanFile
from conan.tools.files import (get, copy, apply_conandata_patches,
                              export_conandata_patches)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class GperftoolsConan(ConanFile):
    name = "gperftools"
    version = "perftools-1.6"
    description = "gperftools perftools-1.6"
    license = "MIT"
    homepage = ""
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)
        # New-source-file additions are carried via exports_sources: refresh-patch
        # regenerates patches/ from the orig/work diff and drops untracked new
        # files, so a git-style new-file patch would be wiped on every finish.
        copy(self, "atomicops-internals-arm64.h",
             src=os.path.join(self.recipe_folder, "extra"),
             dst=self.export_sources_folder)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Install the OHOS/AArch64 atomic-ops header provided by this recipe.
        copy(self, "atomicops-internals-arm64.h",
             src=self.export_sources_folder,
             dst=os.path.join(self.source_folder, "src", "base"))

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # OHOS clang defaults __thread to emulated TLS; emutls lazily allocates
        # the TLS block via malloc() on first access, which recurses into
        # tcmalloc's own allocator.  Force real TLS for the whole build.
        # (extra_*flags land in the toolchain CXXFLAGS/CFLAGS line directly.)
        tc.extra_cxxflags.append("-fno-emulated-tls")
        tc.extra_cflags.append("-fno-emulated-tls")
        # Add project-specific configure args here:
        # tc.configure_args.append("--without-bash-malloc")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # gperftools 1.6 builds libtcmalloc_minimal / libtcmalloc (plus _debug
        # variants).  Default to the minimal allocator to keep link lines small;
        # consumers can opt into the full lib via cpp_info for tcmalloc.
        cxx_runtime = ["c++_shared"] if str(self.settings.os) in ("OHOS",) else []
        self.cpp_info.components["tcmalloc_minimal"].libs = ["tcmalloc_minimal"]
        self.cpp_info.components["tcmalloc_minimal"].system_libs = cxx_runtime
        self.cpp_info.components["tcmalloc"].libs = ["tcmalloc"]
        self.cpp_info.components["tcmalloc"].system_libs = cxx_runtime
