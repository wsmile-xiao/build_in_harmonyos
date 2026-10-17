#!/usr/bin/env python3
"""Conan test_package for infamousplugins 0.3.2 — runs two test programs.

1. test_lv2_plugins  — consumer test (R34): every installed LV2 bundle is
   dlopen()ed, its lv2_descriptor() list checked and its DSP executed through a
   full instantiate/connect/activate/run/deactivate/cleanup cycle with a 440 Hz
   sine on the audio inputs; audio outputs must stay finite.
2. ohos_specific_test — HarmonyOS specific test: AArch64 LP64 / ELF identity of
   every plug-in, dlopen(RTLD_NOW) from the Conan package, dladdr() image origin,
   resolution of the Conan shared dependency chain (libzita-resampler) and a scan
   proving no plug-in binary carries a shared worker-prefix path.
"""
import json
import os
from io import StringIO

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.gnu import PkgConfigDeps

TEST_PROGRAMS = ("test_lv2_plugins", "ohos_specific_test")

UPSTREAM_TEST_REASON = (
    "infamousPlugins 0.3.2 ships no automated test suite: no enable_testing()/"
    "add_test() in any CMakeLists.txt, `make test` reports \"No rule to make "
    "target 'test'\", ctest reports \"No test configuration file found!\". The "
    "test/ directory contains only developer scratch (octave .m scripts and "
    "standalone .c/.cxx sources) that no build file compiles or runs."
)


class InfamousPluginsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # header-only LV2 headers are needed to compile the two test programs
        self.requires("lv2/1.18.11-git")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # CMake has no "OHOS" platform name; OHOS is Linux-based (R32)
        if self.settings.os in ("Linux", "OHOS"):
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        package_folder = self.dependencies["infamousplugins"].package_folder
        bundle_root = os.path.join(package_folder, "lib", "lv2")
        if not os.path.isdir(bundle_root):
            raise ConanException(f"LV2 bundle root missing: {bundle_root}")

        results = {}
        for program in TEST_PROGRAMS:
            executable = os.path.join(self.build_folder, program)
            log_file = os.path.join(self.build_folder, f"{program}.log")
            captured = StringIO()
            self.run(f'"{executable}" "{bundle_root}"', env="conanrun", stdout=captured)
            output = captured.getvalue()
            with open(log_file, "w", encoding="utf-8") as handle:
                handle.write(output)
            # echo the raw per-case log so the CI transcript carries the evidence
            for line in output.splitlines():
                self.output.info(f"| {line}")

            result = self._parse_result(output)
            if result is None:
                raise ConanException(f"{program}: no TEST_RESULT line in {log_file}")
            self.output.info(
                f"{program}: {result['passed']}/{result['discovered']} checks passed "
                f"(log: {log_file})")
            results[program] = result

        failed = {name: r for name, r in results.items() if r["failed"]}
        if failed:
            raise ConanException(
                "test failure: " + ", ".join(f"{n} ({r['failed']} checks)" for n, r in failed.items()))

        discovered = sum(r["discovered"] for r in results.values())
        passed = sum(r["passed"] for r in results.values())
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "test_lv2_plugins <bundle_root>; ohos_specific_test <bundle_root>",
            "discovered": discovered,
            "passedCount": passed,
        }, ensure_ascii=False))
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "no_tests",
            "framework": "cmake-ctest",
            "command": "make test",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": UPSTREAM_TEST_REASON,
        }, ensure_ascii=False))

    @staticmethod
    def _parse_result(output: str):
        for line in output.splitlines():
            line = line.strip()
            if line.startswith("TEST_RESULT="):
                return json.loads(line[len("TEST_RESULT="):])
        return None
