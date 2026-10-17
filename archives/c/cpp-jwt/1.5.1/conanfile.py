#!/usr/bin/env python3
"""Conan recipe — cpp-jwt 1.5.1 (CMake header-only INTERFACE library).

Downstream expects:
  find_package(cpp-jwt REQUIRED)
  target_link_libraries(... PRIVATE cpp-jwt::cpp-jwt)

Upstream builds its GTest suite when CPP_JWT_BUILD_TESTS=ON; this recipe
enables it and runs ctest during build() so the native HarmonyOS worker
executes the full upstream suite. Consumers only get headers + OpenSSL + nlohmann_json.
"""
import json
import os
import re
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run, check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, replace_in_file


class CppJwtConan(ConanFile):
    name = "cpp-jwt"
    version = "1.5.1"
    description = "A C++14 library for JSON Web Tokens (JWT)"
    license = "MIT"
    homepage = "https://github.com/arun11299/cpp-jwt"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("jwt", "auth", "header-only")

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("openssl/3.5.8.1")
        self.requires("nlohmann_json/3.12.0")

    def build_requirements(self):
        self.test_requires("gtest/1.17.0")

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, "14")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "cpp-jwt %s is validated only for Linux and OHOS, not %s"
                % (self.version, self.settings.os)
            )

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CPP_JWT_BUILD_EXAMPLES"] = False
        tc.variables["CPP_JWT_BUILD_TESTS"] = True
        tc.variables["CPP_JWT_USE_VENDORED_NLOHMANN_JSON"] = False
        tc.variables["CPP_JWT_INSTALL"] = True
        # Local openssl/3.5.8.1 is a flat package (libs ssl+crypto, no CMake
        # properties) and gtest/1.17.0 only declares gtest::gtest, so
        # CMakeDeps cannot provide upstream's OpenSSL::SSL / GTest::GTest +
        # GTest::Main targets (proven by preflight "Target declared
        # 'gtest::gtest'"). Follow the cpu_features/broker precedent instead:
        # resolve both deps through their native CMake configs, no CMakeDeps.
        openssl_pkg = self.dependencies["openssl"].package_folder
        tc.cache_variables["OPENSSL_ROOT_DIR"] = openssl_pkg.replace("\\", "/")
        tc.cache_variables["OPENSSL_USE_STATIC_LIBS"] = True
        gtest_pkg = self.dependencies["gtest"].package_folder
        candidates = [
            os.path.join(gtest_pkg, "lib", "cmake", "GTest"),
            os.path.join(gtest_pkg, "lib64", "cmake", "GTest"),
            os.path.join(gtest_pkg, "lib", "cmake", "gtest"),
            os.path.join(gtest_pkg, "lib64", "cmake", "gtest"),
        ]
        gtest_dir = None
        for cand in candidates:
            if os.path.isfile(os.path.join(cand, "GTestConfig.cmake")) or \
               os.path.isfile(os.path.join(cand, "gtest-config.cmake")):
                gtest_dir = cand
                break
        if gtest_dir is None:
            gtest_dir = candidates[0]
        tc.variables["GTest_DIR"] = gtest_dir.replace("\\", "/")
        self.output.info("cpp-jwt: GTest_DIR=%s (package_folder=%s)"
                         % (gtest_dir, gtest_pkg))
        # External nlohmann_json (VENDORED=OFF): upstream does
        # find_package(nlohmann_json REQUIRED). Resolve via native config
        # like GTest above; no CMakeDeps so OpenSSL/GTest mapping stays intact.
        nlohmann_pkg = self.dependencies["nlohmann_json"].package_folder
        nl_candidates = [
            os.path.join(nlohmann_pkg, "lib", "cmake", "nlohmann_json"),
            os.path.join(nlohmann_pkg, "lib64", "cmake", "nlohmann_json"),
            os.path.join(nlohmann_pkg, "share", "cmake", "nlohmann_json"),
        ]
        nlohmann_dir = None
        for cand in nl_candidates:
            if os.path.isfile(os.path.join(cand, "nlohmann_jsonConfig.cmake")):
                nlohmann_dir = cand
                break
        if nlohmann_dir is None:
            nlohmann_dir = nl_candidates[0]
        tc.variables["nlohmann_json_DIR"] = nlohmann_dir.replace("\\", "/")
        self.output.info("cpp-jwt: nlohmann_json_DIR=%s (package_folder=%s)"
                         % (nlohmann_dir, nlohmann_pkg))
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # CMake's FindOpenSSL module has no SSL component; the component form
        # fails against the conan openssl package. Drop it (broker precedent);
        # linking OpenSSL::SSL still pulls crypto transitively.
        replace_in_file(self, os.path.join(self.source_folder, "CMakeLists.txt"),
                        "find_package(OpenSSL REQUIRED SSL)",
                        "find_package(OpenSSL REQUIRED)", strict=False)
        # Upstream googletest >=1.12 exports GTest::gtest / GTest::gtest_main
        # (ALIAS ${cmake_package_name}::${name}); the legacy GTest::GTest and
        # GTest::Main aliases no longer exist, so find_package succeeds but
        # the link targets are missing. Map to the real exported targets;
        # no test logic is changed.
        replace_in_file(self, os.path.join(self.source_folder, "tests", "CMakeLists.txt"),
                        "GTest::GTest", "GTest::gtest", strict=False)
        replace_in_file(self, os.path.join(self.source_folder, "tests", "CMakeLists.txt"),
                        "GTest::Main", "GTest::gtest_main", strict=False)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            cmake.test()
            self._emit_upstream_marker()

    def _emit_upstream_marker(self):
        # HMBS hard gate: one machine-readable
        # "HMBS_UPSTREAM_TEST_RESULT=<json>" line is required in the log.
        # Numbers are parsed from a real ctest run below, never hardcoded.
        # Upstream audit (v1.5.1, pinned by sha256): tests/ registers 7 ctest
        # programs containing 59 GTest TESTs in total (13+12+1+12+13+4+4).
        # PR-level N is counted at GTest granularity, so discovered/executed
        # count individual GTest TESTs (59), not ctest programs (7). A passing
        # ctest program implies all its inner GTests passed; any single TEST
        # failure fails its program. cmake.test() above already gates pass/fail;
        # this re-run only parses the counts. Verbose mode is required:
        # `ctest --output-on-failure` hides passing programs' stdout, so the
        # GTest footers would be missing.
        raw = ""
        try:
            proc = subprocess.run(
                ["ctest", "-V", "--output-on-failure"],
                cwd=self.build_folder, capture_output=True,
                text=True, timeout=1200)
            raw = (proc.stdout or "") + (proc.stderr or "")
        except Exception as exc:
            self.output.warning("cpp-jwt: ctest re-run for marker failed: %s" % exc)
        # Per-program GTest footers, e.g.:
        #   [==========] 13 tests from 1 test suite ran. (5 ms total)
        #   [  PASSED  ] 13 tests.
        ran = sum(int(n) for n in re.findall(
            r"\[=+\]\s+(\d+)\s+tests?\s+from\s+\S+\s+test (?:suite|case)s?\s+ran\.", raw))
        passed = sum(int(n) for n in re.findall(
            r"\[\s*PASSED\s*\]\s+(\d+)\s+tests?\.", raw))
        total = ran
        failed = total - passed if total else 0
        if total <= 0:
            # GTest footer parse missed (unexpected output format): fall back
            # to ctest-level counts so the gate never breaks silently.
            self.output.warning(
                "cpp-jwt: no GTest footers parsed, falling back to ctest counts")
            m = re.search(
                r"(\d+)% tests? passed, (\d+) tests? failed out of (\d+)", raw)
            if m:
                failed = int(m.group(2))
                total = int(m.group(3))
            else:
                m2 = re.search(r"tests passed out of (\d+)", raw)
                if m2:
                    total = int(m2.group(1))
            passed = total - failed if total else 0
        elif total != 59:
            # Upstream is pinned (sha256), so 59 is fixed; a mismatch means the
            # parse is incomplete and the reported N would be wrong again.
            self.output.warning(
                "cpp-jwt: parsed %d GTest TESTs, expected 59 (v1.5.1 audit); "
                "reporting parsed numbers" % total)
        skipped_m = re.search(r"(\d+) Not Run", raw)
        skipped = int(skipped_m.group(1)) if skipped_m else 0
        status = "passed" if total > 0 and failed == 0 and skipped == 0 else "failed"
        marker = {
            "status": status,
            "framework": "ctest",
            "command": "ctest -V --output-on-failure (GTest-level counting)",
            "discovered": total,
            "executed": passed + failed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))
        # Persist for test_package re-emission on cache hits (build() skipped
        # when the package is "Already installed", marker would go missing).
        try:
            with open(os.path.join(self.build_folder, "hmbs_upstream_result.json"),
                      "w", encoding="utf-8") as fh:
                fh.write(json.dumps(marker, ensure_ascii=False))
        except OSError as exc:
            self.output.warning("cpp-jwt: cannot persist upstream marker: %s" % exc)
        if status != "passed":
            raise subprocess.CalledProcessError(1, "ctest", output=raw[-4000:])

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # Ship the upstream-test evidence so test_package can re-emit
        # HMBS_UPSTREAM_TEST_RESULT on cache hits (build() skipped).
        try:
            if os.path.isfile(os.path.join(self.build_folder, "hmbs_upstream_result.json")):
                copy(self, "hmbs_upstream_result.json", src=self.build_folder,
                     dst=os.path.join(self.package_folder, "res"))
        except Exception as exc:
            self.output.warning("cpp-jwt: cannot ship upstream marker: %s" % exc)

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "cpp-jwt")
        self.cpp_info.set_property("cmake_target_name", "cpp-jwt::cpp-jwt")
        self.cpp_info.requires = ["openssl::openssl", "nlohmann_json::nlohmann_json"]
