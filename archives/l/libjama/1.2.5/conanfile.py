#!/usr/bin/env python3
"""Conan recipe for libjama 1.2.5 - JAMA/C++ linear algebra templates.

JAMA/C++ is a public-domain C++ library that provides template classes for the
classical matrix decompositions (LU, QR, Cholesky, SVD) and for the
eigenvalues/eigenvectors of a symmetric or general real matrix.

The upstream source tree ships five headers only; the storage templates they
build on (``Array1D``/``Array2D``) come from TNT, published separately as
``libtnt``.

OHOS notes
----------
* Header-only: ``package()`` installs ``include/jama/*.h`` and ``package_id()``
  is cleared; nothing is compiled into the package.
* The headers target a pre-C++11 toolchain: they pull both ``TNT`` and ``std``
  into scope and call an unqualified ``min``/``max`` that is ambiguous under a
  modern standard library (Debian carries the same fix).  A small portability
  patch qualifies those calls as ``std::min``/``std::max`` and drops the
  header-level ``using namespace std;``.
* The relative ``#include "tnt_*.h"`` lines are kept as-is: the published
  ``libtnt/1.2.6`` Conan package installs the TNT headers flat into
  ``include/``, so no extra include path is required beyond the dependency.
* No upstream test suite exists; ``build()`` compiles a translation unit that
  instantiates every public header as build evidence, and ``test_package``
  checks the numeric results of each decomposition.
"""
import os
import textwrap

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"

_SMOKE = textwrap.dedent(
    """
    // Compile-only evidence that every public header is usable together.
    #include <jama/jama_cholesky.h>
    #include <jama/jama_eig.h>
    #include <jama/jama_lu.h>
    #include <jama/jama_qr.h>
    #include <jama/jama_svd.h>

    void jama_headers_smoke()
    {
        TNT::Array2D<double> a(2, 2);
        a[0][0] = 2.0; a[0][1] = 1.0;
        a[1][0] = 1.0; a[1][1] = 2.0;
        JAMA::LU<double> lu(a);
        JAMA::QR<double> qr(a);
        JAMA::SVD<double> svd(a);
        JAMA::Cholesky<double> chol(a);
        JAMA::Eigenvalue<double> eig(a);
        (void)lu; (void)qr; (void)svd; (void)chol; (void)eig;
    }
    """
)


class LibjamaConan(ConanFile):
    name = "libjama"
    version = "1.2.5"
    description = ("JAMA/C++: templates for the LU, QR, Cholesky and SVD matrix "
                   "decompositions and for eigenvalues/eigenvectors")
    license = "LicenseRef-Public-Domain"
    homepage = "https://math.nist.gov/tnt/"
    url = ""

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"

    no_copy_source = True

    def requirements(self):
        # JAMA's storage types (Array1D/Array2D) live in TNT.
        self.requires("libtnt/1.2.6")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libjama OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def package_id(self):
        self.info.clear()

    def _compiler(self, name, fallback):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        return executables.get(name) or fallback

    def build(self):
        apply_conandata_patches(self)
        smoke = os.path.join(self.build_folder, "jama_headers_smoke.cpp")
        save(self, smoke, _SMOKE)
        dependency = self.dependencies["libtnt"]
        include_dir = dependency.cpp_info.includedirs[0] if dependency.cpp_info.includedirs \
            else "include"
        self.run(
            '"{}" -std=c++17 -I"{}" -I"{}" -c "{}" -o "{}"'.format(
                self._compiler("cpp", "clang++"),
                os.path.join(self.source_folder, "src"),
                os.path.join(dependency.package_folder, include_dir),
                smoke, smoke + ".o"))

    def package(self):
        copy(self, "*.h", src=os.path.join(self.source_folder, "src", "jama"),
             dst=os.path.join(self.package_folder, "include", "jama"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "jama")
        self.cpp_info.set_property("cmake_target_name", "jama::jama")
