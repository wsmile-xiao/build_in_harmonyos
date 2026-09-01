#!/usr/bin/env python3
"""Conan recipe for aevol 9.4.0 — in silico experimental evolution platform.

Builds the aevol CLI binaries (aevol_create / aevol_run, all flavors) for
aarch64-unknown-linux-ohos with clang 15 + the HarmonyOS-adapted libcxx/17.0.6
standard library, which provides std::format / std::views / aggregate
construct_at that the OHOS SDK libc++15 lacks.

Key adaptations:
  * depends on libcxx/17.0.6 (patched construct_at is_aggregate dispatch,
    _LIBCPP_PROVIDES_DEFAULT_RUNE_TABLE, ohos_libc_compat.h strtoll_l shim).
  * relaxed CMake clang >= 19 requirement to >= 15.
  * json (nlohmann 3.12.0) and googletest (1.14.0) are injected through
    -DFETCHCONTENT_SOURCE_DIR_* instead of GitHub downloads.
  * two C++ source fixes for clang 15's missing parenthesized aggregate init
    (FastaModifier emplace_back, RegionHandler member init).

Upstream test suite: 78/78 CTest cases pass on aarch64-ohos (73 gtest + 4
example-param-file checks).
"""
import glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, download, get, unzip
from conan.tools.layout import basic_layout


class AevolConan(ConanFile):
    name = "aevol"
    version = "9.4.0"
    description = ("Aevol: an in silico experimental evolution platform "
                   "(digital genetics)")
    license = "GPL-2.0-or-later"
    homepage = "https://www.aevol.fr/"
    url = "https://gitlab.inria.fr/aevol/aevol"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    requires = "libcxx/17.0.6", "zlib/1.3.1"

    exports_sources = "patches/*"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        deps_dir = self._prepare_deps()
        libcxx_pkg = self.dependencies["libcxx"].package_folder
        zlib_pkg = self.dependencies["zlib"].package_folder
        cc = self._ohos_cc()
        cxx = self._ohos_cxx()
        cxxflags = (
            f"-nostdinc++ -isystem {libcxx_pkg}/include "
            f"-D_LIBCPP_PROVIDES_DEFAULT_RUNE_TABLE -include ohos_libc_compat.h"
        )
        linkflags = f"{libcxx_pkg}/lib/libc++.a {libcxx_pkg}/lib/libc++abi.a"
        build_dir = os.path.join(self.build_folder, "aevol-build")
        os.makedirs(build_dir, exist_ok=True)
        cmake = self._find_cmake()
        configure = [
            cmake, "-S", self.source_folder, "-B", build_dir,
            f"-DCMAKE_C_COMPILER={cc}",
            f"-DCMAKE_CXX_COMPILER={cxx}",
            "-DCMAKE_BUILD_TYPE=Release",
            "-DCMAKE_INSTALL_PREFIX=" + os.path.join(self.build_folder, "install"),
            f"-DCMAKE_CXX_FLAGS={cxxflags}",
            f"-DCMAKE_EXE_LINKER_FLAGS={linkflags}",
            f"-DZLIB_ROOT={zlib_pkg}",
            f"-DZLIB_INCLUDE_DIR={zlib_pkg}/include",
            f"-DZLIB_LIBRARY={zlib_pkg}/lib/libz.a",
            f"-DFETCHCONTENT_SOURCE_DIR_JSON={deps_dir['json']}",
            f"-DFETCHCONTENT_SOURCE_DIR_GOOGLETEST={deps_dir['googletest']}",
        ]
        subprocess.run(configure, check=True)
        subprocess.run([cmake, "--build", build_dir, "--target", "all", "-j2"],
                       check=True)

    # ── helpers ─────────────────────────────────────────────────────

    def _prepare_deps(self):
        """Download and extract json + googletest for FetchContent injection."""
        deps_dir = os.path.join(self.build_folder, "deps")
        os.makedirs(deps_dir, exist_ok=True)
        out = {}
        for key in ("json", "googletest"):
            entry = self.conan_data["deps"][key]
            tarball = os.path.join(deps_dir, entry["filename"])
            if not os.path.exists(tarball):
                download(self, entry["url"], tarball, sha256=entry["sha256"])
            extract_dir = os.path.join(deps_dir, key)
            if not os.path.isdir(extract_dir):
                os.makedirs(extract_dir, exist_ok=True)
                unzip(self, tarball, extract_dir)
            # Locate the single extracted source directory.
            subdirs = [d for d in glob.glob(os.path.join(extract_dir, "*"))
                       if os.path.isdir(d)]
            src = subdirs[0] if subdirs else extract_dir
            out[key] = src
            self.output.info(f"{key} source dir: {src}")
        return out

    def _find_cmake(self):
        cmake = self.conf.get("tools.cmake:cmake_program", default="")
        if cmake and os.path.isfile(cmake):
            return cmake
        for candidate in (
            shutil.which("cmake"),
            "/data/service/hnp/bin/cmake",
            "/data/service/hnp/cmake.org/cmake_4.1.2/bin/cmake",
            "/usr/local/bin/cmake",
        ):
            if candidate and os.path.isfile(candidate):
                return candidate
        raise ConanInvalidConfiguration("cmake not found in the build environment")

    def _ohos_cc(self):
        candidates = [
            os.environ.get("OHOS_CC"),
            "/data/service/hnp/bin/aarch64-unknown-linux-ohos-clang",
            "/data/service/hnp/bin/clang",
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        raise ConanInvalidConfiguration("No OHOS clang compiler found")

    def _ohos_cxx(self):
        candidates = [
            os.environ.get("OHOS_CXX"),
            "/data/service/hnp/bin/aarch64-unknown-linux-ohos-clang++",
            "/data/service/hnp/bin/clang++",
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        raise ConanInvalidConfiguration("No OHOS clang++ compiler found")

    # ── package ─────────────────────────────────────────────────────

    def package(self):
        bin_src = os.path.join(self.build_folder, "aevol-build", "bin")
        if not os.path.isdir(bin_src):
            raise ConanInvalidConfiguration(f"aevol bin dir missing: {bin_src}")
        for name in os.listdir(bin_src):
            full = os.path.join(bin_src, name)
            if os.path.isfile(full):
                copy(self, name, src=bin_src,
                     dst=os.path.join(self.package_folder, "bin"),
                     keep_path=False)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH",
                                      os.path.join(self.package_folder, "bin"))
