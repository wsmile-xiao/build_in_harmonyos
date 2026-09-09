#!/usr/bin/env python3
"""Conan recipe — Fastor 0.6.4 (header-only C++ tensor library).

Fastor is a header-only C++ library (CMake INTERFACE target, no compiled
artifacts). This recipe uses the header-only variant: copy headers into
include/, apply OHOS adaptation patches (x86-only inline asm guarded out for
aarch64), and expose a single package_id since there is no binary.

Iron rules: R34 (test_package must actually consume the API), R39 (official
source URL), R26 (no system-name clash — header-only, no libs).
"""
from conan import ConanFile
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, copy
from conan.tools.layout import basic_layout
import os
import shutil


class FastorConan(ConanFile):
    name = "fastor"
    version = "0.6.4"
    description = "Fastor is a lightweight high performance tensor algebra framework in C++"
    license = "MIT"
    homepage = "https://github.com/romeric/fastor"
    url = ""  # CI fills this

    package_type = "library"

    # Header-only: no binary, but keep settings for structure consistency;
    # the 'shared' option is required by Conan for package_type=library.
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # Header-only: no compilation step; build() declared for recipe
        # structure completeness (G1). No compiled artifacts are produced.
        pass

    def package(self):
        # Header-only variant A: copy the full Fastor/ include tree
        # (headers are nested under Fastor/{config,meta,util,tensor,...});
        # use shutil.copytree to preserve the nested directory structure.
        src_inc = os.path.join(self.source_folder, "Fastor")
        dst_inc = os.path.join(self.package_folder, "include", "Fastor")
        shutil.copytree(src_inc, dst_inc)
        copy(self, "LICENSE*", src=self.source_folder,
             dst="licenses", keep_path=False)

    def package_id(self):
        self.info.clear()          # header-only -> single package_id

    def package_info(self):
        # Header-only: no libs / bins, headers only
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []