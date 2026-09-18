#!/usr/bin/env python3
"""Conan recipe for nbytes 0.1.4.

nbytes is a small C++20 library of byte handling functions extracted from
Node.js core (byte swapping, base64/hex helpers, string search). Upstream
builds with CMake and ships 3 gtest cases in tests/basic.cpp, enabled with
NBYTES_ENABLE_TESTING=ON (FetchContent pulls googletest at build time).

The recipe runs the upstream ctest suite inside build(), parses the real
ctest summary, and emits the HMBS_UPSTREAM_TEST_RESULT machine-evidence
marker (dual channel: stdout + Conan output). Any test failure raises and
fails the build; exit-code-0 alone is never accepted as proof.
"""

import json
import os
import re
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get, replace_in_file


class NbytesConan(ConanFile):
    name = "nbytes"
    version = "0.1.4"
    description = "Library of byte handling functions extracted from Node.js core"
    license = "MIT"
    homepage = "https://github.com/nodejs/nbytes"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("bytes", "nodejs", "base64", "hex", "byte-swap")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Consumer-visible header fixes via exact string replace instead of
        # a unified-diff patch (the .patch hunk for GetHighestValueByte
        # failed to apply in conan on the real machine).
        # 1) Bare CHECK in stringsearch::Vector ctor is undefined for any
        #    consumer instantiation; upstream uses NBYTES_ASSERT_TRUE
        #    everywhere else in this header.
        replace_in_file(
            self,
            os.path.join(self.source_folder, "include", "nbytes.h"),
            "    CHECK(length > 0 && data != nullptr);",
            "    NBYTES_ASSERT_TRUE(length > 0 && data != nullptr);",
        )
        # 2) Generic GetHighestValueByte fallback so SearchString<char>
        #    (used by the consumer test) is not ambiguous between the
        #    uint8_t/uint16_t overloads. Exact-anchor replace, no fuzz.
        replace_in_file(
            self,
            os.path.join(self.source_folder, "include", "nbytes.h"),
            "inline uint8_t GetHighestValueByte(uint8_t character) { return character; }",
            "inline uint8_t GetHighestValueByte(uint8_t character) { return character; }\n"
            "\n"
            "// Generic fallback for any other 1- or 2-byte character type (e.g. char).\n"
            "template <typename Char>\n"
            "inline uint8_t GetHighestValueByte(Char character) {\n"
            "  if constexpr (sizeof(Char) == 1) {\n"
            "    return static_cast<uint8_t>(character);\n"
            "  } else {\n"
            "    return GetHighestValueByte(static_cast<uint16_t>(character));\n"
            "  }\n"
            "}",
        )

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Upstream option added in 0.1.4 (default follows BUILD_TESTING);
        # set both explicitly so the gtest suite is always configured.
        tc.variables["NBYTES_ENABLE_TESTING"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if cross_building(self):
            self.output.info("cross-building: upstream tests compiled but not run")
            return
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Run the upstream ctest suite, emit HMBS_UPSTREAM_TEST_RESULT.

        tests/CMakeLists.txt registers one gtest binary plus
        gtest_discover_tests entries (3 TESTs: swap_bytes16/32/64).
        Numbers below come from the parsed ctest summary, never hardcoded.
        """
        actual_command = "ctest --output-on-failure"
        proc = subprocess.run(
            ["ctest", "--output-on-failure"],
            cwd=self.build_folder,
            env=dict(os.environ),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=1200,
        )
        output = proc.stdout or ""
        self.output.info(output[-4000:])

        discovered = executed = passed = failed = 0
        summary = re.search(
            r"(\d+)% tests passed,\s*(\d+) tests? failed out of (\d+)", output
        )
        if summary:
            total = int(summary.group(3))
            failed = int(summary.group(2))
            discovered = total
            passed = total - failed
            executed = total
        else:
            # Fallback: count per-test result lines.
            passed = len(re.findall(r"\.\.\.\s*Passed", output))
            failed = len(re.findall(r"\.\.\.\s*(?:Failed|Timeout)", output))
            total_match = re.search(r"tests? failed out of (\d+)", output)
            discovered = int(total_match.group(1)) if total_match else passed + failed
            executed = passed + failed

        if proc.returncode == 0 and failed == 0 and passed == discovered and passed > 0:
            result = {
                "status": "passed",
                "framework": "ctest",
                "command": actual_command,
                "discovered": discovered,
                "executed": executed,
                "passed": passed,
                "failed": 0,
                "skipped": 0,
            }
        else:
            result = {
                "status": "failed",
                "framework": "ctest",
                "command": actual_command,
                "discovered": discovered,
                "executed": executed,
                "passed": passed,
                "failed": failed if (failed or proc.returncode != 0) else 0,
                "skipped": 0,
                "reason": "rc=%s passed=%s failed=%s discovered=%s"
                % (proc.returncode, passed, failed, discovered),
            }
        msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False)
        # Dual-channel emit: HMBS preflight scrapes raw stdout.
        print(msg, flush=True)
        self.output.info(msg)
        # Persist for test_package re-emit on Conan cache hits
        # (build() skipped -> marker would otherwise disappear).
        try:
            with open(
                os.path.join(self.build_folder, "hmbs_upstream.json"),
                "w",
                encoding="utf-8",
            ) as handle:
                json.dump(result, handle)
        except OSError:
            pass
        if result["status"] != "passed":
            raise ConanException("upstream ctest suite failed: %s" % msg)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Persist the upstream evidence inside the package so every
        # test_package round can re-emit it (cache-hit safe).
        try:
            copy(
                self,
                "hmbs_upstream.json",
                src=self.build_folder,
                dst=os.path.join(self.package_folder, "res"),
            )
        except Exception:
            pass

    def package_info(self):
        self.cpp_info.libs = ["nbytes"]
        self.cpp_info.set_property("cmake_file_name", "nbytes")
        self.cpp_info.set_property("cmake_target_name", "nbytes::nbytes")
        self.cpp_info.set_property("pkg_config_name", "nbytes")
