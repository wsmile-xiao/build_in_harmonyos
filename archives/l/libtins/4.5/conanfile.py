#!/usr/bin/env python3
"""Conan recipe for libtins 4.5 — high-level C++ network packet crafting/parsing library.

Upstream: https://github.com/mfontanini/libtins (BSD-2-Clause).

OHOS adaptation notes
---------------------
- E092: CMake has no HarmonyOS platform module; CMAKE_SYSTEM_NAME is forced to
  "Linux" so the upstream `if(UNIX)` branches (pkg-config, config install path,
  library naming) behave exactly as they do upstream on Linux.
- Feature options map 1:1 onto the upstream CACHE options
  (PCAP / DOT11 / WPA2 / ACK_TRACKER / TCP_STREAM_CUSTOM_DATA). Disabling an
  optional feature only compiles that feature out, it never silently drops
  registered upstream tests (the ctest entry set follows the same options).
- Upstream test suite: the release tarball does not contain the googletest git
  submodule, so upstream takes its `find_package(GTest QUIET)` branch. The Conan
  gtest package is wired through the GOOGLETEST_INCLUDE / GOOGLETEST_LIBRARY
  cache variables that tests/src/CMakeLists.txt consumes (upstream only sets
  them in the submodule branch). All test binaries are EXCLUDE_FROM_ALL and are
  built through the aggregate `tests` target, then executed with ctest inside
  build() and reported through the HMBS_UPSTREAM_TEST_RESULT marker.
- OHOS: the cross-built test executables are ELF-signed (binary-sign-tool,
  self-sign) before execution, and ctest is launched from the shell in
  CONFIG_SHELL because /system/bin/sh cannot load dynamically linked binaries.
"""
import glob
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run, check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, rm


class LibtinsConan(ConanFile):
    name = "libtins"
    version = "4.5"
    description = ("High-level, multiplatform C++ library for network packet "
                   "crafting, sniffing and interpretation")
    license = "BSD-2-Clause"
    homepage = "https://github.com/mfontanini/libtins"
    url = "https://github.com/mfontanini/libtins"
    topics = ("networking", "packet", "sniffing", "pcap", "pdu")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_pcap": [True, False],
        "with_dot11": [True, False],
        "with_wpa2": [True, False],
        "with_ack_tracker": [True, False],
        "with_tcp_stream_custom_data": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_pcap": True,
        "with_dot11": True,
        "with_wpa2": True,
        "with_ack_tracker": True,
        "with_tcp_stream_custom_data": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS", "FreeBSD", "Macos"):
            raise ConanInvalidConfiguration(f"{self.ref} supports Linux/OHOS only")
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, 11)

    def requirements(self):
        if self.options.with_pcap:
            self.requires("libpcap/1.10.6")
        if self.options.with_wpa2:
            self.requires("openssl/3.5.6")
        if self.options.with_ack_tracker or self.options.with_tcp_stream_custom_data:
            # Header-only usage upstream (boost.icl for the ACK tracker,
            # boost.any for TCP stream custom data).
            self.requires("boost/1.84.0")
        # Upstream tests/src links gtest + gtest_main (find_package(GTest)).
        self.test_requires("gtest/1.17.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    # ── helpers ────────────────────────────────────────────────────────────
    def _dep_paths(self, dep_name, attr):
        """Absolute include/lib dirs of a dependency (test_requires included)."""
        for dep in self.dependencies.values():
            if dep.ref.name != dep_name:
                continue
            rel = getattr(dep.cpp_info, attr)
            return [os.path.join(dep.package_folder, d) for d in rel]
        return []

    def _openssl_link_libs(self):
        """Absolute OpenSSL libraries for the upstream test link.

        tests/src/CMakeLists.txt links only `tins` (+ pcap). That is enough when
        libtins is built shared (the .so records its OpenSSL dependency), but a
        static libtins leaves the EVP_*/HMAC/AES_* symbols of crypto.cpp
        unresolved in every test executable. Feed the OpenSSL package libraries
        to the standard link line so both shared and static builds link.
        """
        libs = []
        for libdir in self._dep_paths("openssl", "libdirs"):
            for name in ("ssl", "crypto"):
                for suffix in (".so", ".a"):
                    candidate = os.path.join(libdir, f"lib{name}{suffix}")
                    if os.path.isfile(candidate):
                        libs.append(candidate)
                        break
        return libs

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: no HarmonyOS platform module in CMake; force the Linux branch.
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # Upstream declares cmake_minimum_required(VERSION 2.8.1); CMake 4.x
        # removed compatibility with < 3.5, so keep the floor explicit.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["LIBTINS_BUILD_SHARED"] = bool(self.options.shared)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["LIBTINS_BUILD_EXAMPLES"] = False
        tc.variables["LIBTINS_BUILD_TESTS"] = True
        tc.variables["LIBTINS_ENABLE_PCAP"] = bool(self.options.with_pcap)
        tc.variables["LIBTINS_ENABLE_DOT11"] = bool(self.options.with_dot11)
        tc.variables["LIBTINS_ENABLE_WPA2"] = bool(self.options.with_wpa2)
        tc.variables["LIBTINS_ENABLE_ACK_TRACKER"] = bool(self.options.with_ack_tracker)
        tc.variables["LIBTINS_ENABLE_TCP_STREAM_CUSTOM_DATA"] = bool(
            self.options.with_tcp_stream_custom_data)
        # tests/src/CMakeLists.txt consumes these two variables directly; they
        # are only set upstream when the bundled googletest submodule exists.
        gtest_inc = self._dep_paths("gtest", "includedirs")
        gtest_lib = self._dep_paths("gtest", "libdirs")
        if gtest_inc:
            tc.variables["GOOGLETEST_INCLUDE"] = gtest_inc[0]
        if gtest_lib:
            tc.variables["GOOGLETEST_LIBRARY"] = gtest_lib[0]
        openssl_libs = self._openssl_link_libs()
        if openssl_libs:
            tc.cache_variables["CMAKE_CXX_STANDARD_LIBRARIES"] = " ".join(openssl_libs)
        tc.generate()
        VirtualRunEnv(self).generate()

    # ── build ──────────────────────────────────────────────────────────────
    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Every upstream test binary is EXCLUDE_FROM_ALL; the aggregate `tests`
        # target builds them all.
        cmake.build(target="tests")
        self._run_upstream_tests()

    def _test_binaries(self):
        pattern = os.path.join(self.build_folder, "tests", "*_test")
        return sorted(p for p in glob.glob(pattern)
                      if os.path.isfile(p) and os.access(p, os.X_OK))

    @staticmethod
    def _ohos_tool(name, fallback):
        found = shutil.which(name)
        return found or (fallback if os.path.isfile(fallback) else None)

    @staticmethod
    def _host_tool_env():
        """Environment for host tools (signer/readelf).

        The OHOS build environment prepends the SDK libc++ directory to
        LD_LIBRARY_PATH; binary-sign-tool is a host binary linked against the
        system libc++ and fails to relocate in that environment
        ("symbol not found", exit 127). Run the host tools without it.
        """
        env = dict(os.environ)
        env.pop("LD_LIBRARY_PATH", None)
        return env

    def _sign_elf(self, path):
        signer = self._ohos_tool("binary-sign-tool", "/data/service/hnp/bin/binary-sign-tool")
        readelf = self._ohos_tool("llvm-readelf", "/data/service/hnp/bin/llvm-readelf")
        if not signer or not readelf:
            raise ConanException("OHOS test execution requires binary-sign-tool and llvm-readelf")
        env = self._host_tool_env()
        signed = path + ".signed"
        subprocess.run([signer, "sign", "-inFile", path, "-outFile", signed,
                        "-selfSign", "1"], check=True, timeout=120, env=env)
        sections = subprocess.run([readelf, "-SW", signed], check=True,
                                  capture_output=True, text=True, timeout=60,
                                  env=env).stdout
        if sections.count(".codesign") != 1:
            raise ConanException(f"invalid .codesign section count for {path}")
        os.chmod(signed, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(signed, path)

    def _run_upstream_tests(self):
        binaries = self._test_binaries()
        if not binaries:
            raise ConanException("upstream test binaries were not built (LIBTINS_BUILD_TESTS=ON)")
        if not can_run(self):
            self.output.warning("target cannot run on this host; upstream tests must be "
                                "executed by the native HarmonyOS validation worker")
            return
        if self.settings.os == "OHOS":
            for binary in binaries:
                self._sign_elf(binary)
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        runenv = os.path.join(self.generators_folder, "conanrun.sh")
        lib_dir = os.path.join(self.build_folder, "lib")
        cmd = (f'. "{runenv}" 2>/dev/null; '
               f'export LD_LIBRARY_PATH="{lib_dir}:{self.build_folder}:$LD_LIBRARY_PATH"; '
               "ctest --output-on-failure -V -j1")
        proc = subprocess.run([bash, "-c", cmd], cwd=self.build_folder,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, timeout=3600)
        output = proc.stdout
        passed = sum(int(m) for m in re.findall(r"\[  PASSED  \] (\d+) tests?", output))
        failed = sum(int(m) for m in re.findall(r"\[  FAILED  \] (\d+) tests?", output))
        executed = passed + failed
        discovered = executed
        if executed == 0:
            m = re.search(r"(\d+) tests out of (\d+)", output)
            if m:
                executed, discovered = int(m.group(1)), int(m.group(2))
                passed = executed - failed
        status = "passed" if proc.returncode == 0 and failed == 0 and executed > 0 else "failed"
        marker = {
            "status": status,
            "framework": "ctest+gtest",
            "command": "ctest --output-on-failure -V -j1",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
            "binaries": len(binaries),
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))
        if status != "passed":
            self.output.error("upstream tests failed; tail:\n" + output[-4000:])
            raise ConanException("upstream tests failed")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        rm(self, "*.pdb", os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libtins")
        self.cpp_info.set_property("cmake_target_name", "tins")
        self.cpp_info.set_property("pkg_config_name", "libtins")
        self.cpp_info.libs = ["tins"]
        if self.settings.os in ("Linux", "OHOS", "FreeBSD"):
            self.cpp_info.system_libs = ["pthread"]
