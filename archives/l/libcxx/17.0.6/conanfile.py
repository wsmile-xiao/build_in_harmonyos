#!/usr/bin/env python3
"""Conan recipe for libcxx 17.0.6 — LLVM libc++ adapted for HarmonyOS PC.

Builds libc++ 17.0.6 for aarch64-unknown-linux-ohos with the OHOS SDK clang 15,
including three HarmonyOS adaptations:
  1. `-D_LIBCPP_PROVIDES_DEFAULT_RUNE_TABLE` — OHOS musl-based libc provides no
     ctype rune-table macros (no _ISSPACE/_ISALPHA or _S/_P), so libc++'s
     ctype_base must use its built-in default rune table.
  2. `ohos_libc_compat.h` shim — OHOS musl lacks the POSIX-2008 locale-aware
     conversion functions (strtoll_l / strtod_l / ...) that libc++ <locale>
     uses; they are mapped to the plain (locale-ignoring) versions.
  3. `construct_at` is_aggregate dispatch — clang 15 does not implement C++20
     parenthesized aggregate initialization, which libc++17's construct_at
     relies on. Aggregates use brace-init (works on clang 15), non-aggregates
     keep paren-init (preserves e.g. nlohmann::basic_json from json_ref).

Only the static libc++.a is produced (the shared link needs a shared libc++abi
build that the OHOS SDK does not provide); consumers link libc++.a against the
SDK's libc++abi.a. Verified against aevol 9.4.0: builds and passes its full
78-test suite.
"""
import glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout


class LibcxxConan(ConanFile):
    name = "libcxx"
    version = "17.0.6"
    description = ("LLVM libc++ 17.0.6 C++ standard library adapted for "
                   "HarmonyOS PC (aarch64, clang 15)")
    license = "Apache-2.0 WITH LLVM-exception"
    homepage = "https://libcxx.llvm.org/"
    url = "https://github.com/llvm/llvm-project"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    exports_sources = "patches/*"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "libcxx 17.0.6 for OHOS provides only the static library "
                "(libc++.so would require a shared libc++abi that the OHOS "
                "SDK does not provide)")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        self._write_compat_shim()
        libcxx_src = os.path.join(self.source_folder, "libcxx")
        libcxxabi_src = os.path.join(self.source_folder, "libcxxabi")
        build_dir = os.path.join(self.build_folder, "libcxx-build")
        os.makedirs(build_dir, exist_ok=True)
        compat = os.path.join(self.build_folder, "ohos_libc_compat.h")
        cc = self._ohos_cc()
        cxx = self._ohos_cxx()
        cxxflags = (
            f"-D_LIBCPP_PROVIDES_DEFAULT_RUNE_TABLE "
            f"-include {compat} -isystem {libcxxabi_src}/include"
        )
        cmake = self._find_cmake()
        configure = [
            cmake, "-S", libcxx_src, "-B", build_dir,
            f"-DCMAKE_C_COMPILER={cc}",
            f"-DCMAKE_CXX_COMPILER={cxx}",
            "-DCMAKE_BUILD_TYPE=Release",
            "-DCMAKE_CROSSCOMPILING=ON",
            "-DCMAKE_SYSTEM_NAME=OHOS",
            "-DCMAKE_SYSTEM_PROCESSOR=aarch64",
            "-DCMAKE_INSTALL_PREFIX=" + os.path.join(self.build_folder, "install"),
            f"-DCMAKE_C_FLAGS={cxxflags}",
            f"-DCMAKE_CXX_FLAGS={cxxflags}",
            "-DLIBCXX_CXX_ABI=libcxxabi",
            f"-DLIBCXX_CXX_ABI_INCLUDE_PATHS={libcxxabi_src}/include",
            "-DLIBCXX_ENABLE_SHARED=OFF",
            "-DLIBCXX_ENABLE_STATIC=ON",
            "-DLIBCXX_INCLUDE_BENCHMARKS=OFF",
            "-DLIBCXX_INCLUDE_TESTS=OFF",
        ]
        subprocess.run(configure, check=True)
        subprocess.run([cmake, "--build", build_dir, "--target", "cxx_static", "-j2"],
                       check=True)

    # ── helpers ─────────────────────────────────────────────────────

    def _write_compat_shim(self):
        src = os.path.join(self.export_sources_folder, "patches", "ohos_libc_compat.h")
        dst = os.path.join(self.build_folder, "ohos_libc_compat.h")
        shutil.copy2(src, dst)

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

    def _sdk_libcxxabi(self):
        candidates = glob.glob(
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib/"
            "aarch64-linux-ohos/libc++abi.a")
        if candidates:
            return sorted(candidates)[-1]
        raise ConanInvalidConfiguration("OHOS SDK libc++abi.a not found")

    # ── package ─────────────────────────────────────────────────────

    def package(self):
        inc_src = os.path.join(self.build_folder, "libcxx-build", "include", "c++", "v1")
        if os.path.isdir(inc_src):
            copy(self, "*", src=inc_src,
                 dst=os.path.join(self.package_folder, "include"),
                 keep_path=True)
        copy(self, "libc++.a",
             src=os.path.join(self.build_folder, "libcxx-build", "lib"),
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "ohos_libc_compat.h", src=self.build_folder,
             dst=os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "libc++abi.a", src=os.path.dirname(self._sdk_libcxxabi()),
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["c++", "c++abi"]
        # Consumers must prefer the packaged libc++17 headers over the OHOS
        # SDK's libc++15 and carry the two compile adaptations.
        self.cpp_info.cxxflags = [
            "-nostdinc++",
            "-isystem", os.path.join(self.package_folder, "include"),
            "-D_LIBCPP_PROVIDES_DEFAULT_RUNE_TABLE",
            "-include", "ohos_libc_compat.h",
        ]
