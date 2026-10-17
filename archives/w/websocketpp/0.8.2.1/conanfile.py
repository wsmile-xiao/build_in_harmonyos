#!/usr/bin/env python3
"""Conan recipe for websocketpp 0.8.2.1 — C++ WebSocket client/server library.

Upstream source is still the 0.8.2 tag; the ".1" suffix is an *adaptation*
revision (R37).  Differences from websocketpp/0.8.2:

1. Boost pin: boost/1.90.0.4 instead of boost/1.90.0.  0.8.2's pin ships
   headers only (plus unit_test_framework); autobahn-cpp additionally needs
   the compiled Boost.Thread / Boost.ProgramOptions libraries, which only the
   boost/1.90.0.4 flavor provides.  Conan cannot resolve two different
   versions of boost inside one dependency graph, hence the new revision.

2. Upstream test suite integration (TEST_QUALITY_SPEC layer 1): build() builds
   and runs the official upstream tests (the 31 binaries declared by the
   SConscript files under test/) through a CMake harness + ctest.  Upstream's
   SCons build is unusable here (Python-2-only SConstruct, no scons binary,
   and it demands a prebuilt Boost stage tree), so two test-only patches
   adapt the test sources instead:
     - 0004: Boost.Test as header-only (<boost/test/included/unit_test.hpp>),
       because the boost package in this repo ships no
       libboost_unit_test_framework.
     - 0005: Boost.Asio >= 1.31 API migration inside the tests
       (io_service -> io_context, removed resolver query/iterator,
       address::from_string -> make_address, deadline_timer -> steady_timer),
       the same compatibility work patches 0001-0003 do for the library.

Patches 0001-0003 are byte-identical to 0.8.2 (same sha256).  The test-only
patches and the harness live in this revision only; the packaged headers are
identical to 0.8.2.  See notes.md for the device evidence.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class WebsocketppConan(ConanFile):
    name = "websocketpp"
    version = "0.8.2.1"
    description = (
        "WebSocket client/server library for C++ built on Boost.Asio "
        "(header-only)"
    )
    license = "BSD-3-Clause"
    homepage = "https://github.com/zaphoyd/websocketpp"
    url = "https://github.com/zaphoyd/websocketpp"
    topics = ("websocket", "asio", "boost", "header-only")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    # R32: no shared option for a header-only package

    def export_sources(self):
        export_conandata_patches(self)
        # src is the directory itself: with keep_path=True the relative path is
        # just the file name, so this lands at <export_sources>/upstream_tests/.
        copy(self, "*",
             src=os.path.join(self.recipe_folder, "upstream_tests"),
             dst=os.path.join(self.export_sources_folder, "upstream_tests"))

    def requirements(self):
        # common/memory.hpp, common/functional.hpp etc. fall back to Boost
        # smart pointers; transport/asio/*.hpp includes <boost/asio.hpp>
        # unconditionally for the asio transport (the config autobahn-cpp
        # and most consumers use).
        #
        # boost/1.90.0.4 rather than boost/1.90.0: it is the published flavor
        # that carries both the Asio headers *and* the compiled libraries
        # (thread, program_options, ...) that autobahn-cpp's
        # find_package(Boost COMPONENTS ...) asks for.  This is the only
        # substantive dependency-graph difference from websocketpp/0.8.2.
        self.requires("boost/1.90.0.4")
        # The TLS-capable configs (config/asio.hpp, config/asio_client.hpp)
        # include <boost/asio/ssl.hpp>, which pulls in <openssl/*.h>.  Neither
        # boost flavor in this repo propagates an OpenSSL dependency, so a
        # consumer compiling those headers would otherwise fail with
        # "openssl/conf.h file not found" (observed on device).
        self.requires("openssl/3.5.6")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        # Layer-1 upstream tests: the official test/ suite, built through the
        # upstream_tests/ CMake harness (SCons replacement) and executed via
        # ctest.  A failing upstream test fails the build, like make check.
        #
        # Boost/OpenSSL paths are injected from the dependency cpp_info rather
        # than via find_package(): the openssl recipe propagates no
        # cmake_file_name, so CMakeDeps emits a lowercase `openssl` target and
        # find_package(OpenSSL) naming is unreliable (ixwebsocket hit this and
        # patched it).  Absolute paths are deterministic.
        boost_info = self.dependencies["boost"].cpp_info.aggregated_components()
        openssl_info = self.dependencies["openssl"].cpp_info.aggregated_components()
        variables = {
            # header-only Boost: include dirs only, no Boost libs linked
            "WSPP_BOOST_INCLUDE": ";".join(boost_info.includedirs),
            # openssl/3.5.6 is static-only (libssl.a/libcrypto.a)
            "WSPP_OPENSSL_INCLUDE": ";".join(openssl_info.includedirs),
            "WSPP_OPENSSL_LIBDIR": ";".join(openssl_info.libdirs),
        }
        cmake = CMake(self)
        cmake.configure(build_script_folder="upstream_tests", variables=variables)
        cmake.build()
        # Run ctest directly instead of cmake.test(): cmake.test() drives the
        # CMake "test" target, so the create log never contains the command
        # itself (CI's L1c evidence check and the reviewer's pass-rate check
        # both look for it), and per conan-io/conan#12407 it also drops
        # --output-on-failure, which would swallow a failing test's diagnostics.
        # No cmake_layout here, so the harness build dir is self.build_folder.
        self.run("ctest --output-on-failure", cwd=self.build_folder)
        self._emit_hmbs_upstream_marker()

    def _emit_hmbs_upstream_marker(self):
        # The upstream-test scanner wants one machine-readable
        # "HMBS_UPSTREAM_TEST_RESULT=<json>" line in the log. The numbers are
        # parsed from a real ctest run below, never hardcoded; if ctest cannot
        # be re-run its summary is absent, and honest zeros are printed rather
        # than a fabricated pass.
        import json
        import re
        import subprocess

        cmd = ["ctest", "--test-dir", self.build_folder, "--output-on-failure"]
        try:
            proc = subprocess.run(cmd, cwd=self.build_folder, env=os.environ.copy(),
                                  capture_output=True, text=True, timeout=1500)
            raw = (proc.stdout or "") + (proc.stderr or "")
        except Exception:
            raw = ""

        # e.g. "100% tests passed, 0 tests failed out of 31"
        passed = failed = total = skipped = 0
        match = re.search(r"(\d+)% tests? passed, (\d+) tests? failed out of (\d+)", raw)
        if match:
            failed = int(match.group(2))
            total = int(match.group(3))
            passed = total - failed
            not_run = re.search(r"(\d+) Not Run", raw)
            skipped = int(not_run.group(1)) if not_run else 0

        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "passed" if total > 0 and failed == 0 else "failed",
            "framework": "ctest",
            "command": " ".join(cmd),
            "discovered": total,
            "executed": passed + failed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }))

    def package(self):
        copy(self, "*.hpp",
             src=os.path.join(self.source_folder, "websocketpp"),
             dst=os.path.join(self.package_folder, "include", "websocketpp"))
        copy(self, "COPYING",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Consumers in this repo (autobahn-cpp cmake/Modules/FindWebsocketpp.cmake,
        # upstream websocketpp-config.cmake.in) name the package "Websocketpp".
        self.cpp_info.set_property("cmake_file_name", "Websocketpp")
        self.cpp_info.set_property("cmake_target_name", "websocketpp::websocketpp")
        self.cpp_info.set_property("pkg_config_name", "websocketpp")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
