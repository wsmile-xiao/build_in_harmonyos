#!/usr/bin/env python3
"""Conan recipe — btas 1.0.0 (header-only C++17 tensor algebra library).

BTAS: Basic Tensor Algebra Subprograms by Valeev Group
(https://github.com/ValeevGroup/BTAS). Upstream declares an INTERFACE
(INTERFACE library) CMake target that installs headers only; no compiled
artifact is produced by the library itself.

Packaging notes (OHOS adaptation decisions, evidence in notes.md):

- Upstream's CMake configure unconditionally FetchContent's the
  ValeevGroup/kit-cmake toolkit and (optionally) builds Boost from source,
  i.e. network access at configure time. The Conan package therefore
  packages the header tree directly (same artifact set the upstream
  ``install`` target installs) and reproduces the single generated header
  ``btas/version.h`` from ``btas/version.h.in`` exactly as upstream CMake
  ``configure_file`` does; test_package verifies BTAS_VERSION == "1.0.0".

- Boost is a mandatory dependency (Boost.Container small_vector backs the
  default index type; Boost.Iterator headers are required for usability).
  btas/features.h detects both via ``__has_include`` and btas/defaults.h
  falls back to BTAS_TARGET_MAX_INDEX_RANK=6, so no compile definitions
  need to be propagated: consumers only need the Boost include path, which
  the Conan dependency provides. Serialized-tensor support
  (Boost.Serialization) is optional upstream and not enabled: the registry
  boost/1.91.0 binary ships no libboost_serialization.

- BLAS/LAPACK bindings (upstream option BTAS_USE_BLAS_LAPACK, default ON)
  require blas++/lapack++ which have no recipes in the OHOS registry
  (verified via `conan list "blaspp/*" -r=ohpcd` -> 0 matches); the
  upstream-supported OFF configuration is packaged. The generic fallback
  implementations of gemm/gemv/ger/axpy/scal/dot/contract are fully
  functional; only GESVD (SVD) lacks a generic implementation by upstream
  design (btas/generic/gesvd_impl.h throws).
"""
import os

from conan import ConanFile
from conan.tools.cmake import cmake_layout
from conan.tools.files import (apply_conandata_patches, copy, export_conandata_patches,
                               get, load, save)


class BtasConan(ConanFile):
    name = "btas"
    version = "1.0.0"
    description = ("BTAS: Basic Tensor Algebra Subprograms — header-only "
                   "C++17 tensor algebra library from Valeev Group")
    license = "BSD-3-Clause"
    homepage = "https://github.com/ValeevGroup/BTAS"
    url = "https://github.com/ValeevGroup/BTAS"
    topics = ("tensor", "linear-algebra", "header-only", "cpp17", "quantum-chemistry")

    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        # Boost >= 1.71 required by upstream (external/versions.cmake:
        # BTAS_OLDEST_BOOST_VERSION 1.71). Components needed at header
        # level: container (small_vector default index), iterator.
        # serialization optional upstream, not provided by the registry
        # binary -> BTAS_HAS_BOOST_SERIALIZATION stays undefined.
        self.requires("boost/1.91.0")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # no patches declared for 1.0.0: conandata.yml has no `patches`
        # key, so this is a no-op (kept for G1 recipe completeness)
        apply_conandata_patches(self)

    def build(self):
        # Header-only library: no compilation step. Reproduce the single
        # generated header btas/version.h exactly as upstream CMake does:
        #   configure_file(btas/version.h.in btas/version.h)
        # with BTAS_VERSION "1.0.0", major 1, minor 0, micro 0,
        # prerelease id empty (see CMakeLists.txt version block).
        template = load(self, os.path.join(self.source_folder, "btas",
                                           "version.h.in"))
        version_h = (template
                     .replace("@BTAS_VERSION@", self.version)
                     .replace("@BTAS_MAJOR_VERSION@", "1")
                     .replace("@BTAS_MINOR_VERSION@", "0")
                     .replace("@BTAS_MICRO_VERSION@", "0")
                     .replace("@BTAS_PRERELEASE_ID@", ""))
        save(self, os.path.join(self.build_folder, "generated", "btas",
                                 "version.h"), version_h)

    def package(self):
        # Same artifact set as upstream `install(DIRECTORY btas ...
        # FILES_MATCHING PATTERN "*.h" PATTERN "*.h.in" EXCLUDE)`.
        copy(self, "*.h",
             src=os.path.join(self.source_folder, "btas"),
             dst=os.path.join(self.package_folder, "include", "btas"),
             excludes="*.h.in")
        copy(self, "*.hpp",
             src=os.path.join(self.source_folder, "btas"),
             dst=os.path.join(self.package_folder, "include", "btas"))
        # generated version.h (upstream installs the configured file)
        copy(self, "version.h",
             src=os.path.join(self.build_folder, "generated", "btas"),
             dst=os.path.join(self.package_folder, "include", "btas"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "btas")
        self.cpp_info.set_property("cmake_target_name", "btas::btas")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        # Upstream INTERFACE target would add -DBTAS_HAS_BOOST_ITERATOR=1,
        # -DBTAS_HAS_BOOST_CONTAINER=1 and
        # -DBTAS_DEFAULT_TARGET_MAX_INDEX_RANK=<rank>; btas/features.h
        # re-derives the feature macros via __has_include and
        # btas/defaults.h defaults the rank to 6, so consumers need no
        # extra definitions — only the Boost include path, which the
        # boost/1.91.0 graph dependency propagates to all consumers.
