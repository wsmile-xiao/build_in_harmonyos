#!/usr/bin/env python3
"""Conan recipe — libbpp-popgen 2.4.1 (CMake) on HarmonyOS PC.

Bio++ Population Genetics library (Bpp/PopGen): genotype/allele data model
(DataSet / Individual / Group / Locality / LocusInfo / AlleleInfo), monolocus
and multilocus genotypes, Hardy-Weinberg and F-statistics helpers, plus
Genepop / Genetix / Darwin / Popgenlib readers and writers.

Upstream facts (v2.4.1, verified against the release tarball):
  - `CMakeLists.txt` builds `bpp-popgen-static` and `bpp-popgen-shared`
    (OUTPUT_NAME bpp-popgen, PACKAGE_VERSION 8.0.0, SOVERSION 8) and installs
    both, together with its own `bpp-popgen-config.cmake` package.
  - `find_package(bpp-seq 12.0.0 REQUIRED)` uses the Bio++ *API* version
    scheme: bpp-seq reports 12.0.0 while its release tag is 2.4.1. The
    published `libbpp-seq/2.4.1` package ships `bpp-seq-config.cmake`,
    `bpp-core-config.cmake` (API version 4.1.0) and both static archives, so
    nothing has to be vendored — but that upstream config validates a pruned
    `.so` and aborts, so patches/0001 redirects the lookup to the Conan
    target `libbpp-seq::libbpp-seq` (same headers, same archives, same
    transitive bpp-core link).
  - Upstream ships **no test suite** at this version (no tests/ or test/
    directory). Per the platform rule for libraries without upstream tests,
    this recipe ships a real consumer test (test_package/) that exercises the
    public API rather than fabricating upstream cases.

OHOS adaptation:
  - `cmake_minimum_required(VERSION 2.8.11)` -> `CMAKE_POLICY_VERSION_MINIMUM`
    is pinned to 3.5 so modern CMake can still configure the project.
  - Upstream always installs the static *and* shared pair; `package()` prunes
    the variant that was not requested, so consumers of the static package
    cannot accidentally resolve the shared object.
  - The consumer test links the static archives by absolute path, i.e. with
    zero runtime `.so` dependency (see test_package/CMakeLists.txt).
"""
import glob
import json
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class LibbppPopgenConan(ConanFile):
    name = "libbpp-popgen"
    version = "2.4.1"
    description = "Bio++ Population Genetics library (genotype/allele data model and statistics)"
    license = "CECILL-2.1"
    homepage = "https://github.com/BioPP/bpp-popgen"
    url = "https://github.com/BioPP/bpp-popgen"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # Published to the ohpcd registry as a static package; its
        # bpp-seq-config.cmake + bpp-core-config.cmake satisfy the upstream
        # find_package(bpp-seq 12.0.0) / find_package(bpp-core 4.1.0) contract.
        self.requires("libbpp-seq/2.4.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.cache_variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(
            self.options.shared
        ) or bool(self.options.get_safe("fPIC", True))
        # Upstream declares cmake_minimum_required(VERSION 2.8.11); allow
        # modern CMake (>= 4) to configure it in compatibility mode.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Shipped static+shared pair lives side by side in package lib/.
        tc.cache_variables["CMAKE_INSTALL_RPATH"] = "$ORIGIN"
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._emit_upstream_evidence()

    def _emit_upstream_evidence(self):
        """Record that upstream ships no test suite at v2.4.1.

        The JSON is printed as an evidence marker and persisted into the build
        folder so package() can ship it under res/ (it then survives package
        cache hits, matching the libbpp-seq / libbpp-core family convention).
        """
        upstream = {
            "status": "no_upstream_tests",
            "framework": "none",
            "command": "",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "upstream bpp-popgen 2.4.1 has no tests/ directory; API coverage "
                "is provided by test_package/ consumer tests"
            ),
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
        )
        try:
            with open(
                os.path.join(self.build_folder, "upstream_test_result.json"),
                "w",
                encoding="utf-8",
                newline="\n",
            ) as fh:
                json.dump(upstream, fh, ensure_ascii=False, indent=2)
                fh.write("\n")
        except OSError as exc:
            self.output.warning("cannot persist upstream result: %s" % exc)

    def package(self):
        copy(
            self,
            "COPYING.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        cmake = CMake(self)
        cmake.install()
        self._prune_unrequested_variant()
        copy(
            self,
            "upstream_test_result.json",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "res"),
            keep_path=False,
        )

    def _prune_unrequested_variant(self):
        """Drop the library variant that was not requested.

        Upstream unconditionally installs bpp-popgen-static *and*
        bpp-popgen-shared. Shipping both would let a consumer of the static
        package resolve the shared object instead, which is not what the
        package options promise.
        """
        patterns = ("*.a",) if self.options.shared else ("*.so", "*.so.*")
        for libdir in (
            os.path.join(self.package_folder, "lib"),
            os.path.join(self.package_folder, "lib64"),
        ):
            if not os.path.isdir(libdir):
                continue
            for pattern in patterns:
                for victim in glob.glob(os.path.join(libdir, pattern)):
                    try:
                        os.remove(victim)
                        self.output.info("package: pruned %s" % victim)
                    except OSError as exc:
                        self.output.warning(
                            "package: cannot prune %s (%s)" % (victim, exc)
                        )

    def package_info(self):
        self.cpp_info.libs = ["bpp-popgen"]
        # Keep Conan's generated config under the libbpp-popgen name so it does
        # not shadow the upstream bpp-popgen-config.cmake that future Bio++
        # modules (bpp-phyl-omics) look up by its upstream name.
        self.cpp_info.set_property("cmake_file_name", "libbpp-popgen")
        self.cpp_info.set_property("cmake_target_name", "libbpp-popgen::libbpp-popgen")
        self.cpp_info.set_property("pkg_config_name", "libbpp-popgen")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs.append("m")
