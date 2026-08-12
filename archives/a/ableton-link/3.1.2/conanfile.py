#!/usr/bin/env python3
"""Conan recipe — ableton-link 3.1.2 (CMake, header-only).

Ableton Link synchronizes musical beat, tempo and phase across apps/devices.
The library itself is header-only (Ableton::Link is an IMPORTED INTERFACE
target); upstream also builds Catch2-based unit tests (LinkCoreTest,
LinkDiscoveryTest) and example apps. On OHOS the GitHub source archive ships
an EMPTY modules/asio-standalone submodule, so the asio headers are fetched
from the standalone asio release and laid out where AsioStandaloneConfig.cmake
expects them (modules/asio-standalone/asio/include).
"""
import json
import os
import re
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class AbletonLinkConan(ConanFile):
    name = "ableton-link"
    version = "3.1.2"
    description = "Synchronizes musical beat, tempo and phase across multiple applications on one or more devices."
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/Ableton/link"
    url = "https://github.com/Ableton/link"
    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # GitHub archives omit submodule content; asio-standalone is required
        # by AsioStandaloneConfig.cmake at modules/asio-standalone/asio/include.
        asio = self.conan_data["asio"]
        get(self, url=asio["url"], sha256=asio["sha256"],
            destination="modules/asio-standalone", strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: CMake has no HarmonyOS platform module; force the Linux branch
        # so upstream selects the Linux platform headers (linux Clock,
        # posix ScanIpIfAddrs, stl Random) and defines LINK_PLATFORM_LINUX.
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # Build upstream unit tests; skip example apps (they link PortAudio
        # which is not available on OHOS).
        tc.variables["LINK_BUILD_TESTS"] = "ON"
        tc.variables["LINK_BUILD_EXAMPLES"] = "OFF"
        # OHOS libc provides pthread symbols and aarch64 has native atomics,
        # so -latomic/-lpthread are neither needed nor present.
        tc.variables["LINK_OHOS"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Run LinkCoreTest + LinkDiscoveryTest and emit the HMBS marker."""
        test_cases_total = 25  # TEST_CASE count in src/ableton (16 core + 9 discovery)
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        bin_dir = self._find_bin_dir()
        if bin_dir is None:
            self.output.error("LinkCoreTest/LinkDiscoveryTest not found in build tree")
            raise RuntimeError("upstream test executables missing")
        executed = 0
        passed = 0
        failed = 0
        results = []
        for exe in ("LinkCoreTest", "LinkDiscoveryTest"):
            exe_path = os.path.join(bin_dir, exe)
            if not os.path.isfile(exe_path):
                raise RuntimeError(f"test executable missing: {exe_path}")
            cmd = f'cd "{bin_dir}" && ./{exe}'
            proc = subprocess.run(
                [bash, "-c", cmd], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, timeout=1800)
            output = proc.stdout
            # Catch2 summary: "All tests passed (N assertions in M test cases)"
            m = re.search(r"All tests passed \(\d+ assertions in (\d+) test cases\)", output)
            if m is not None:
                n = int(m.group(1))
                executed += n
                passed += n
            else:
                m = re.search(r"test cases: (\d+) \| (\d+) passed \| (\d+) failed", output)
                if m is not None:
                    executed += int(m.group(1))
                    passed += int(m.group(2))
                    failed += int(m.group(3))
            results.append({"exe": exe, "exit": proc.returncode,
                            "tail": output[-800:]})
            self.output.info(f"{exe} exit={proc.returncode} executed={executed} passed={passed} failed={failed}")
        if executed == 0:
            raise RuntimeError("upstream tests produced no executable test cases")
        status = "passed" if failed == 0 and executed == passed else "failed"
        upstream = {
            "status": status,
            "framework": "catch2",
            "command": "cd bin && ./LinkCoreTest && ./LinkDiscoveryTest",
            "discovered": test_cases_total,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))
        if status != "passed":
            for r in results:
                self.output.error(f"=== {r['exe']} tail ===\n{r['tail']}")
            raise RuntimeError("upstream tests failed")

    def _find_bin_dir(self):
        for root, _dirs, files in os.walk(self.build_folder):
            if "LinkCoreTest" in files and "LinkDiscoveryTest" in files:
                return root
        return None

    def package(self):
        # Header-only library: ship the Link headers. Conan 2's copy() matches
        # file paths with fnmatch, so a bare directory name matches nothing;
        # glob the directory contents to keep the ableton/ tree structure.
        copy(self, "ableton/*", os.path.join(self.source_folder, "include"),
             os.path.join(self.package_folder, "include"))
        # Consumers of Link.hpp need the asio headers too (AsioWrapper.hpp
        # includes <asio.hpp>), so vendor them into the package.
        asio_inc = os.path.join(self.source_folder, "modules", "asio-standalone",
                                "asio", "include")
        copy(self, "*", asio_inc, os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE.md", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        # Config.hpp selects the Linux platform code from this macro.
        self.cpp_info.defines = ["LINK_PLATFORM_LINUX"]
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
        self.cpp_info.set_property("cmake_file_name", "ableton-link")
        self.cpp_info.set_property("cmake_target_name", "ableton-link::ableton-link")
