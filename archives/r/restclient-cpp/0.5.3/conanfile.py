#!/usr/bin/env python3
"""Conan recipe for restclient-cpp 0.5.3 on Linux and HarmonyOS PC."""

import json
import os
import re
import subprocess
import sys
import time

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, get, load, rmdir


# test/test_restclient.cc 26 + test/test_connection.cc 22 + test/test_helpers.cc 3
UPSTREAM_GTEST_CASES = 51
# Negotiates HTTP/2 against a public host; no loopback stand-in can serve it.
PUBLIC_NETWORK_CASES = ("RestClientTest.TestRestClientGETHTTP2Code",)
LOOPBACK_READY_TIMEOUT = 30


class RestclientCppConan(ConanFile):
    name = "restclient-cpp"
    version = "0.5.3"
    description = "REST client for C++"
    license = "MIT"
    homepage = "https://github.com/mrtazz/restclient-cpp"
    url = "https://github.com/mrtazz/restclient-cpp"
    topics = ("rest", "http", "client", "libcurl")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    exports_sources = "patches/*", "files/*"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "restclient-cpp is supported only on Linux/OHOS"
            )

    def requirements(self):
        # include/restclient-cpp/connection.h exposes <curl/curl.h>, so consumers
        # compile against curl headers and link curl through us.
        self.requires("curl/8.15.0", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        self.test_requires("gtest/1.17.0")
        self.test_requires("jsoncpp/1.9.8")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)
        # Our own test assets ship in files/ rather than as "/dev/null" patches:
        # conan's patch pipeline materialises new-file hunks at the source root
        # whatever target path the header carries, so they are copied here to sit
        # next to the test sources that reference them.
        copy(self, "*",
             src=os.path.join(self.export_sources_folder, "files"),
             dst=os.path.join(self.source_folder, "test"))

    def generate(self):
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        tc.cache_variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.cache_variables["CMAKE_DEBUG_POSTFIX"] = ""
        # Discovery at build time would execute test-program in the build step.
        tc.cache_variables["CMAKE_GTEST_DISCOVER_TESTS_DISCOVERY_MODE"] = "PRE_TEST"
        for dep, subdir in (("gtest", "GTest"), ("jsoncpp", "jsoncpp")):
            package_folder = self.dependencies[dep].package_folder.replace("\\", "/")
            tc.cache_variables["%s_DIR" % subdir] = os.path.join(
                package_folder, "lib", "cmake", subdir
            ).replace("\\", "/")
        tc.generate()

        # PRE_TEST discovery makes "ctest -N" execute test-program from the CMake
        # binary dir. musl's loader ignores the build-tree DT_RUNPATH, so the
        # freshly linked librestclient-cpp.so is unreachable without LD_LIBRARY_PATH.
        env = Environment()
        for path in reversed(self._test_lib_paths()):
            env.prepend_path("LD_LIBRARY_PATH", path)
        env.vars(self, scope="build").save_script("restclient-test-ldpath")

    def _test_lib_paths(self):
        # test-program links the runtime library plus the test requirements it is
        # built against, so every direct dependency contributes its libdir.
        paths = [self.build_folder]
        for dep in self.dependencies.filter({"build": False, "direct": True}).values():
            for libdir in dep.cpp_info.libdirs:
                paths.append(os.path.join(dep.package_folder, libdir).replace("\\", "/"))
        unique = []
        for path in paths:
            if path not in unique:
                unique.append(path)
        return unique

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        if not can_run(self):
            self.output.info(
                "Cross-building: upstream test-program was compiled; "
                "execution belongs to the OHOS device run"
            )
            return

        server = _LoopbackStandIn(self)
        server.start()
        try:
            self._run_upstream_suite()
        finally:
            server.stop()

    def _run_upstream_suite(self):
        registered = self._ctest_total()
        if registered != UPSTREAM_GTEST_CASES:
            raise ConanException(
                "expected %d registered upstream cases, ctest listed %d"
                % (UPSTREAM_GTEST_CASES, registered)
            )

        exclude = "|".join(PUBLIC_NETWORK_CASES)
        log = os.path.join(self.build_folder, "ctest-upstream.log")
        self.run(
            'ctest --test-dir "%s" -E "%s" --timeout 60 --output-on-failure '
            '> "%s" 2>&1' % (self.build_folder, exclude, log),
            env=["conanbuild", "conanrun"],
            ignore_errors=True,
        )
        report = _parse_ctest_summary(load(self, log))
        report["source_declared_total"] = UPSTREAM_GTEST_CASES
        report["registered"] = registered
        report["excluded_public_network"] = len(PUBLIC_NETWORK_CASES)
        report["framework"] = "gtest+ctest"
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(report))
        if report["failed"]:
            raise ConanException(
                "upstream suite failed: see %s (%s)" % (log, json.dumps(report))
            )

    def _ctest_total(self):
        listing = os.path.join(self.build_folder, "ctest-listing.txt")
        self.run(
            'ctest --test-dir "%s" -N > "%s" 2>&1' % (self.build_folder, listing),
            env=["conanbuild", "conanrun"],
        )
        found = re.findall(r"Total Tests:\s*(\d+)", load(self, listing))
        if not found:
            raise ConanException("ctest -N produced no total for %s" % listing)
        return int(found[-1])

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Upstream installs its own CMake package files, which would be picked up
        # instead of the ones Conan generates and they carry no curl interface.
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "restclient-cpp")
        self.cpp_info.set_property("cmake_target_name", "restclient-cpp::restclient-cpp")
        self.cpp_info.libs = ["restclient-cpp"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]


def _parse_ctest_summary(text):
    # ctest's own line is "<pct>% tests passed, <failed> tests failed out of <run>"
    match = re.search(r"(\d+)% tests? passed, (\d+) tests? failed out of (\d+)", text)
    if not match:
        raise ConanException("ctest summary is missing from the log:\n%s" % text[-2000:])
    _, failed, executed = (int(value) for value in match.groups())
    skipped = len(re.findall(r"^\s+\d+ - .*\(Skipped\)$", text, flags=re.MULTILINE))
    return {
        "status": "passed" if failed == 0 else "failed",
        "executed": executed,
        "passed": executed - failed,
        "failed": failed,
        "skipped_by_upstream": skipped,
    }


class _LoopbackStandIn:
    """Runs test/loopback_httpbin.py for the duration of the upstream suite."""

    def __init__(self, conanfile):
        self._conanfile = conanfile
        self._process = None
        self._handle = None

    def start(self):
        test_dir = os.path.join(self._conanfile.source_folder, "test")
        self._log_path = os.path.join(self._conanfile.build_folder, "loopback-server.log")
        self._handle = open(self._log_path, "w", encoding="utf-8")
        self._process = subprocess.Popen(
            [sys.executable, os.path.join(test_dir, "loopback_httpbin.py"),
             "--ready-file", os.path.join(self._conanfile.build_folder, "loopback-ready.txt")],
            cwd=test_dir, stdout=self._handle, stderr=self._handle,
        )
        self._conanfile.output.info("Started loopback stand-in pid=%d" % self._process.pid)
        self._wait_until_ready()

    def _wait_until_ready(self):
        ready = os.path.join(self._conanfile.build_folder, "loopback-ready.txt")
        deadline = time.time() + LOOPBACK_READY_TIMEOUT
        while not os.path.isfile(ready):
            if self._process.poll() is not None:
                raise ConanException(
                    "loopback stand-in exited with %s; see %s"
                    % (self._process.returncode, self._log_path)
                )
            if time.time() > deadline:
                self.stop()
                raise ConanException(
                    "loopback stand-in did not become ready in %ds; see %s"
                    % (LOOPBACK_READY_TIMEOUT, self._log_path)
                )
            time.sleep(0.2)

    def stop(self):
        if self._process is not None and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait()
        if self._handle is not None:
            self._handle.close()
            self._handle = None
