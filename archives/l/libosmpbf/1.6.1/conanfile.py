#!/usr/bin/env python3
"""Conan recipe for libosmpbf 1.6.1 (CMake).

libosmpbf is the C++ library of openstreetmap/OSM-binary for reading and
writing OpenStreetMap PBF files (Protocol buffer Binary Format). Upstream
builds a static lib (osmpbf), a shared lib (osmpbf_shared, OUTPUT_NAME
osmpbf) and the osmpbf-outline demo tool. This recipe packages the
libraries; the demo tool is installed alongside but the package stays a
pure library (no bindirs declaration, R38/L0k).

Upstream C++ has no test suite (no enable_testing/add_test, no tests/
directory; only Java has ReadFileTest), so build() runs no ctest and
test_package reports HMBS_UPSTREAM_TEST_RESULT status no_tests with a
source-tree audit (c10t precedent).
"""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, replace_in_file, rm, rmdir


def _is_usable_compiler(path):
    if not path:
        return False
    path = str(path)
    if not os.path.isabs(path):
        return True
    return os.path.isfile(path) and os.access(path, os.X_OK)


def _probe_compiler(path):
    # True when the binary actually runs (filters Error 127 / inaccessible
    # toolchain paths that exist but cannot execute on this runner).
    try:
        p = subprocess.run([str(path), "--version"],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           timeout=15)
        return p.returncode == 0
    except Exception:
        return False


class LibosmpbfConan(ConanFile):
    name = "libosmpbf"
    version = "1.6.1"
    description = "C++ library for reading/writing OpenStreetMap PBF files"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/openstreetmap/OSM-binary"
    url = "https://github.com/openstreetmap/OSM-binary"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libosmpbf supports Linux and OHOS targets, got {}".format(self.settings.os)
            )
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        # protobuf 33.x (via abseil) requires C++17 at consumer level.
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, 17)

    def requirements(self):
        # Etcd/brpc precedent: protobuf 33.6 is the registry standard.
        # zlib MUST be 1.3.1.1 (ohpcd Makefile, static -fPIC), not 1.3.1:
        # E533 forbid_3 + E541 — plain 1.3.1 libz.a is non-PIC and breaks
        # AArch64 shared links (R_AARCH64_ADR_PREL_PG_HI21); preflight
        # 2026-09-15 proves the conancenter 1.3.1 CMake recipe also fails
        # on OHOS ("System is unknown to cmake" + CMAKE_C_COMPILER sanity
        # failure under readonly /tmp). override=True aligns protobuf's
        # transitive zlib/1.3.1 to the OHOS closure (c10t precedent).
        self.requires("protobuf/33.6", transitive_headers=True, transitive_libs=True)
        self.requires("zlib/1.3.1.1", transitive_libs=True, override=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _usable_compiler(self, key, fallbacks):
        # Conf absolute path first (healthy runners: zero change); when it
        # is missing/not executable/fails --version probe, fall back to
        # PATH lookup (HMBS prepends real tool dirs to PATH).
        try:
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict) or {}
        except Exception:
            compilers = {}
        cand = compilers.get(key)
        if _is_usable_compiler(cand) and os.path.isabs(str(cand)):
            if _probe_compiler(cand):
                return str(cand)
            self.output.warning(
                "conf compiler '{}' unusable; falling back to PATH".format(cand))
        for name in fallbacks:
            found = shutil.which(name)
            if found and os.path.isfile(found) and _probe_compiler(found):
                return found
        if _is_usable_compiler(cand):
            return str(cand)
        return fallbacks[0]

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()

        tc = CMakeToolchain(self)
        # E092 precedent (brpc/barrier): device cmake ships no HarmonyOS
        # platform module, so force the upstream Linux branches.
        if str(self.settings.os) == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # Registry protobuf exports cmake_find_mode=none: point CONFIG-mode
        # find_package at the installed config files (grpc/brpc wiring).
        protobuf = self.dependencies["protobuf"]
        protobuf_pkg = protobuf.package_folder.replace("\\", "/")
        tc.variables["Protobuf_DIR"] = os.path.join(
            protobuf_pkg, "lib", "cmake", "protobuf"
        )
        tc.variables["utf8_range_DIR"] = os.path.join(
            protobuf_pkg, "lib", "cmake", "utf8_range"
        )
        try:
            abseil_pkg = self.dependencies["abseil-cpp"].package_folder.replace("\\", "/")
            tc.variables["absl_DIR"] = os.path.join(abseil_pkg, "lib", "cmake", "absl")
        except KeyError:
            self.output.warning("abseil-cpp not in dependency graph; skipping absl_DIR")
        # Pin the codegen binary: under the OHOS toolchain CMake treats the
        # build as cross-compiled and FindProtobuf would otherwise search a
        # PATH that does not carry the registry protoc.
        protoc = os.path.join(protobuf_pkg, "bin", "protoc")
        tc.variables["Protobuf_PROTOC_EXECUTABLE"] = protoc
        tc.variables["PROTOBUF_PROTOC_EXECUTABLE"] = protoc
        # Compiler fallback (preflight 2026-09-15: conan_toolchain.cmake bakes
        # profile /data/service/hnp/bin/clang which fails identification on
        # some runners). Resolve usable compilers now so the baked toolchain
        # never carries a dangling path; healthy runners keep conf values.
        _cc = self._usable_compiler("c", ["clang", "cc"])
        _cxx = self._usable_compiler("cpp", ["clang++", "c++", "g++"])
        self.output.info("libosmpbf CC={} CXX={}".format(_cc, _cxx))
        tc.variables["CMAKE_C_COMPILER"] = _cc
        tc.variables["CMAKE_CXX_COMPILER"] = _cxx
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # E002/readonly_tmp: guarantee cmake/clang child processes see a
        # writable temp root even under conan buildenv isolation. HMBS
        # injects TMPDIR, but fall back to a build-local dir when unset.
        _tmp = os.environ.get("TMPDIR") or os.environ.get("TMP") or os.environ.get("TEMP")
        if not (_tmp and os.path.isdir(_tmp)):
            _tmp = os.path.join(self.build_folder, "hmbs-tmp")
            try:
                os.makedirs(_tmp, exist_ok=True)
            except Exception:
                pass
            os.environ["TMPDIR"] = _tmp
            os.environ["TMP"] = _tmp
            os.environ["TEMP"] = _tmp
        # Toolchain-file patch (generate-then-patch: CMakeToolchain bakes the
        # profile compiler path; replace only the exact stale substring when
        # it is not executable, preserving sysroot/flags). Plus CC/CXX env
        # fallback so bare cmake probes never embed a dangling path.
        _cc = self._usable_compiler("c", ["clang", "cc"])
        _cxx = self._usable_compiler("cpp", ["clang++", "c++", "g++"])
        try:
            _toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
            if os.path.isfile(_toolchain):
                for _stale, _good in (("/data/service/hnp/bin/clang++", _cxx),
                                      ("/data/service/hnp/bin/clang", _cc)):
                    try:
                        if not _is_usable_compiler(_stale) or not _probe_compiler(_stale):
                            replace_in_file(self, _toolchain, _stale, _good)
                    except Exception:
                        pass
        except Exception:
            pass
        os.environ["CC"] = _cc
        os.environ["CXX"] = _cxx
        cmake = CMake(self)
        cmake.configure(variables={"CMAKE_C_COMPILER": _cc,
                                   "CMAKE_CXX_COMPILER": _cxx})
        cmake.build()
        # No upstream C++ test suite exists (no enable_testing/add_test in
        # any CMakeLists, no tests/ directory), so no ctest is run here.
        # The no_tests audit is emitted by test_package (c10t precedent).

    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        # Upstream always builds both variants; keep the selected one.
        if self.options.shared:
            rm(self, "*.a", os.path.join(self.package_folder, "lib"))
        else:
            rm(self, "*.so*", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["osmpbf"]
        self.cpp_info.set_property("cmake_file_name", "libosmpbf")
        self.cpp_info.set_property("cmake_target_name", "libosmpbf::libosmpbf")
        # No cpp_info.requires (brpc/grpc precedent): the registry protobuf
        # package exports cmake_find_mode=none, so CMakeDeps generates no
        # config/target for it; any requires on protobuf::libprotobuf fails
        # test_package generate() with "Component 'protobuf::libprotobuf'
        # not found" (preflight 2026-09-15 proof). Upstream osmpbf lib links
        # only protobuf; consumers find protobuf via their own
        # find_package(Protobuf CONFIG) (Protobuf_DIR wiring below) and link
        # protobuf::libprotobuf explicitly (see test_package/CMakeLists.txt).
        # zlib reaches consumers transitively via protobuf, not here.
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs.append("pthread")
