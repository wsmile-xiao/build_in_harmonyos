#!/usr/bin/env python3
"""Conan recipe — libjwt2 2.1.3 (CMake, legacy v2 branch).

Upstream: https://github.com/benmcollins/libjwt tag v2.1.3
Library target is `jwt` (libjwt.a / libjwt.so); package name is libjwt2
to coexist with libjwt/3.x. Jansson is vendored via upstream FetchContent
(USE_INSTALLED_JANSSON=OFF, JANSSON_INSTALL=ON) and its static archive is
bundled in this package (cpp_info.libs jwt+jansson), so no conan jansson
requirement is needed.
Upstream tests (12 Check-based executables) are built with BUILD_TESTS=ON
and executed via ctest in build(). Upstream CMake registers only 8 of them
(tests/CMakeLists.txt TARGET_NAMES); the other 4 (jwt_rsa_pss, jwt_eddsa,
jwt_crypto, jwt_es256k) are part of the canonical `make check` suite
(tests/Makefile.am TESTS, 12 total) and are wired into the CMake build by
build() below so ctest runs the full suite. No test logic is modified.
"""
import json
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.files import get, copy, rmdir, replace_in_file
from conan.tools.gnu import PkgConfigDeps


class Libjwt2Conan(ConanFile):
    name = "libjwt2"
    version = "2.1.3"
    description = "C JSON Web Token library (legacy v2 branch)"
    license = "MPL-2.0"
    homepage = "https://github.com/benmcollins/libjwt"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        pass

    def requirements(self):
        self.requires("openssl/3.5.6.1")

    def build_requirements(self):
        # Upstream tests need Check (pkg-config check.pc) + CMakeDeps files.
        self.test_requires("check/0.15.2")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Pre-download jansson v2.14 so FetchContent needs no `git clone`
        # (true machine times out on github.com:443). generate() points
        # FETCHCONTENT_SOURCE_DIR_JANSSON at this directory.
        get(self, **self.conan_data["jansson"],
            destination=os.path.join(self.source_folder, "jansson-vendor"),
            strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.cache_variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.cache_variables["BUILD_EXAMPLES"] = "OFF"
        tc.cache_variables["BUILD_TESTS"] = "ON"
        # Vendored jansson v2.14 declares cmake_minimum_required(VERSION 3.1),
        # rejected by True-machine CMake 4.4.3 ("Compatibility with CMake < 3.5
        # has been removed"). Keep upstream-tested v2.14 and opt into the
        # CMake 4 compat shim (same pattern as n2n/3.1.1, anobench/4.6.0).
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Vendor jansson via FetchContent (no conan jansson package needed).
        # The vendored static archive is bundled into this package so
        # downstream static consumers resolve json_* symbols.
        tc.cache_variables["USE_INSTALLED_JANSSON"] = "OFF"
        # Offline FetchContent: source() pre-downloaded the exact upstream
        # jansson v2.14 tarball into <source>/jansson-vendor; point
        # FetchContent at it so `git clone https://github.com/akheron/...`
        # never runs (true machine: 3x 65s timeout -> configure failure).
        # UPSTREAM wiring (GIT_REPOSITORY/GIT_TAG) is untouched.
        tc.cache_variables["FETCHCONTENT_SOURCE_DIR_JANSSON"] = os.path.join(
            self.source_folder, "jansson-vendor").replace("\\", "/")
        tc.cache_variables["FETCHCONTENT_FULLY_DISCONNECTED"] = "ON"
        # Jansson and libjwt both define a top-level `check` custom target
        # (jansson CMakeLists + tests/CMakeLists.txt:6); with FetchContent
        # they collide in one build tree. Disable jansson's own
        # tests/docs/examples -- libjwt's 12 Check tests stay ON.
        # Keep JANSSON_INSTALL=ON: cmake.install() then ships libjansson.a
        # + headers, and package_info() lists both libs. (INSTALL=OFF was
        # the true-machine failure: libjwt.a references json_object_set_new
        # etc., but the package shipped no jansson, so test_package failed
        # with `ld.lld: error: undefined symbol: json_*`.)
        tc.cache_variables["JANSSON_WITHOUT_TESTS"] = True
        tc.cache_variables["JANSSON_BUILD_DOCS"] = False
        tc.cache_variables["JANSSON_EXAMPLES"] = False
        tc.cache_variables["JANSSON_INSTALL"] = True
        tc.cache_variables["ENABLE_PIC"] = False
        # Upstream v2.1.3 CMake never defines HAVE_OPENSSL/HAVE_GNUTLS
        # (autotools gets them from AC_DEFINE via libjwt/config.h; CMake
        # only write_file()s an empty config.h). Without HAVE_OPENSSL,
        # jwt.c falls into `#else jwt_ops = &jwt_gnutls_ops` while
        # jwt-private.h declares neither ops struct -> true-machine error
        # `use of undeclared identifier 'jwt_gnutls_ops'`. Define it for
        # the OpenSSL backend we actually build (WITHOUT_OPENSSL=OFF).
        tc.preprocessor_definitions["HAVE_OPENSSL"] = "1"
        tc.cache_variables["WITHOUT_OPENSSL"] = False
        tc.cache_variables["USE_WINSSL"] = False
        # Upstream libjwt/libjwt/CMakeLists.txt uses legacy FindOpenSSL
        # variables (OPENSSL_INCLUDE_DIR via SSL_LIBRARY_INCLUDE_DIR), not
        # modern OpenSSL:: targets. Force CMake built-in FindOpenSSL and
        # point it at the Conan package (same pattern as curl/8.15.0.1).
        self.dependencies["openssl"].cpp_info.set_property("cmake_find_mode", "none")
        _ossl = self.dependencies["openssl"].cpp_info
        tc.cache_variables["OPENSSL_ROOT_DIR"] = self.dependencies["openssl"].package_folder
        tc.cache_variables["OPENSSL_INCLUDE_DIR"] = _ossl.includedirs[0]
        # Upstream tests/CMakeLists.txt uses legacy FindCheck.cmake vars
        # (CHECK_INCLUDE_DIR singular + CHECK_LIBRARIES), while CMakeDeps
        # emits check-config.cmake; with CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON
        # find_package(Check) resolves to CONFIG (Check::check) and the
        # legacy vars stay empty -> `fatal error: check.h not found`.
        # Force MODULE mode for check and seed the legacy vars from the
        # Conan check package (same intent as orcania/2.3.3, via toolchain
        # cache instead of build()-time configure vars).
        try:
            _check_dep = self.dependencies.get("check")
        except Exception:
            _check_dep = None
        if _check_dep is None:
            try:
                _check_dep = self.dependencies.build.get("check")
            except Exception:
                _check_dep = None
        if _check_dep is not None:
            try:
                _check_dep.cpp_info.set_property("cmake_find_mode", "none")
            except Exception:
                pass
            _check_pkg = _check_dep.package_folder
            _check_inc = os.path.join(_check_pkg, "include")
            _check_lib_a = os.path.join(_check_pkg, "lib", "libcheck.a")
            if os.path.isfile(_check_lib_a):
                _check_libs = ";".join([_check_lib_a, "m", "rt", "pthread"])
            else:
                _check_libs = ";".join(
                    [os.path.join(_check_pkg, "lib"), "check", "m", "rt", "pthread"]
                )
            tc.cache_variables["CHECK_FOUND"] = True
            tc.cache_variables["CHECK_INCLUDE_DIR"] = _check_inc
            tc.cache_variables["CHECK_INCLUDE_DIRS"] = _check_inc
            tc.cache_variables["CHECK_LIBRARIES"] = _check_libs
            tc.cache_variables["CHECK_LIBRARY"] = _check_lib_a
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()
        pkg = PkgConfigDeps(self)
        pkg.generate()

    def build(self):
        # tests/jwt_tests.h unconditionally includes autotools config.h, but CMake only
        # generates an empty config.h for the libjwt private dir (no include path for
        # tests). Guard it with HAVE_CONFIG_H; tests get HAVE_OPENSSL via toolchain -D.
        # NOTE: implemented via replace_in_file (not conandata patch): the previous
        # 0001 patch failed true-machine parsing with "extra lines for hunk no.1"
        # (new-count 10 vs actual 11 lines), so the file-based patch route is dropped.
        replace_in_file(self, os.path.join(self.source_folder, "tests", "jwt_tests.h"), '#include "config.h"', '#ifdef HAVE_CONFIG_H\n#include "config.h"\n#endif')
        # Static-build link fix: libjwt/CMakeLists.txt links OpenSSL/jansson only
        # into the `jwt` static archive (target_link_libraries(jwt ...)), but
        # tests/CMakeLists.txt links executables with just
        # `jwt ${CHECK_LIBRARIES}`. A static archive carries no DT_NEEDED, so the
        # final executables miss EVP_sha256/HMAC/BIO_* (ld.lld undefined symbol).
        # Link the transitive deps explicitly (harmless for shared builds too).
        _tests_cmake = os.path.join(self.source_folder, "tests", "CMakeLists.txt")
        replace_in_file(self, _tests_cmake,
                         "find_package (Check REQUIRED)",
                         "find_package (Check REQUIRED)\nfind_package (OpenSSL REQUIRED)")
        replace_in_file(self, _tests_cmake,
                         "target_link_libraries (${TARGET_NAME} jwt ${CHECK_LIBRARIES} ${PLATFORM_LIBRARIES})",
                         "target_link_libraries (${TARGET_NAME} jwt jansson OpenSSL::SSL OpenSSL::Crypto ${CHECK_LIBRARIES} ${PLATFORM_LIBRARIES})")
        # Full-suite wiring: upstream CMake registers only 8 ctest items while
        # the canonical autotools suite (tests/Makefile.am TESTS) has 12. The
        # 4 extra programs (jwt_rsa_pss/jwt_eddsa/jwt_crypto/jwt_es256k) ship in
        # the same tarball, use the identical Check harness (jwt_tests.h +
        # tests/keys fixture), and only lack CMake registration. Append them so
        # ctest discovers and runs the complete upstream suite (12/12). This
        # changes build wiring only, not a single test assertion.
        replace_in_file(self, _tests_cmake,
                         "set (TARGET_NAMES jwt_dump jwt_ec jwt_encode jwt_grant jwt_header jwt_new jwt_rsa jwt_validate)",
                         "set (TARGET_NAMES jwt_dump jwt_ec jwt_encode jwt_grant jwt_header jwt_new jwt_rsa jwt_validate jwt_rsa_pss jwt_eddsa jwt_crypto jwt_es256k)")
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Upstream official tests: 12 Check executables via ctest.
        # NOTE: do NOT use cmake.test() here: it builds the `test` target
        # (`cmake --build . --target test`). Upstream calls
        # enable_testing() only in tests/CMakeLists.txt (subdirectory), so
        # the top-level Makefile has no `test` target and the true machine
        # fails with `make: *** No rule to make target 'test'`. Run the
        # ctest client directly instead (same `ctest --output-on-failure`
        # semantics, works regardless of where enable_testing() lives).
        self._run_upstream_ctest(cmake)
        self._emit_hmbs_upstream_marker()

    def _run_upstream_ctest(self, cmake):
        ctest = getattr(cmake, "ctest", None)
        if callable(ctest):
            try:
                ctest(cli_args=["-N"])
            except TypeError:
                ctest(args=["-N"])
            try:
                ctest(cli_args=["--output-on-failure"])
            except TypeError:
                ctest(args=["--output-on-failure"])
            return
        # Fallback for very old Conan without CMake.ctest(): run the ctest
        # client in the CMake binary dir (the dir holding CTestTestfile).
        import subprocess
        candidates = [self.build_folder]
        for root, _, files in os.walk(self.build_folder):
            if "CTestTestfile.cmake" in files:
                candidates.append(root)
                break
        build_dir = candidates[-1]
        self.run("ctest -N", cwd=build_dir)
        self.run("ctest --output-on-failure", cwd=build_dir)

    def _emit_hmbs_upstream_marker(self):
        # rule4 口径: 上游按源码级 Check 用例数核对 (tcase_add_test /
        # tcase_add_loop_test 注册合计 = 110), 与 ctest 的 12 个测试二进制
        # 不同 (tests/Makefile.am TESTS=12; 各二进制内含多个 Check 用例:
        # jwt_new 25 / jwt_validate 16 / jwt_rsa 14 / jwt_ec 12 / jwt_encode 9 /
        # jwt_grant 7 / jwt_header 7 / jwt_rsa_pss 7 / jwt_dump 6 / jwt_eddsa 3 /
        # jwt_es256k 3 / jwt_crypto 1)。
        # 计数来源: ctest 运行后 Testing/Temporary/LastTest.log 中各二进制
        # 的 "Checks: N, Failures: F, Errors: E" 汇总行求和 (确定性框架输出,
        # 非 stdout 字符串数数)。ctest 退出 0 且无失败时合计应为 110/110。
        import re
        total_checks, total_fail, total_err = 0, 0, 0
        searched, found_log = [], None
        for root, _, files in os.walk(self.build_folder):
            if "LastTest.log" in files:
                found_log = os.path.join(root, "LastTest.log")
                break
            searched.append(root)
        if found_log is not None:
            try:
                with open(found_log, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                for m in re.finditer(
                    r"Checks:\s*(\d+)\s*,\s*Failures:\s*(\d+)\s*,\s*Errors:\s*(\d+)",
                    content,
                ):
                    total_checks += int(m.group(1))
                    total_fail += int(m.group(2))
                    total_err += int(m.group(3))
            except OSError:
                found_log = None
        if found_log is None or total_checks == 0:
            # 宁缺毋假: 日志缺失时如实失败, 给出搜过的位置。
            marker = {
                "status": "failed",
                "framework": "ctest",
                "command": "ctest --output-on-failure",
                "discovered": 110,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "LastTest.log not found or no Check summary; searched under build_folder",
            }
            self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))
            return
        failed = total_fail + total_err
        passed = total_checks - failed
        # 自检恒等式: passed + failed == executed == discovered (全量运行无跳过)。
        marker = {
            "status": "passed" if failed == 0 else "failed",
            "framework": "ctest",
            "command": "ctest --output-on-failure",
            "discovered": total_checks,
            "executed": total_checks,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
            "_note": "Check-case level total from LastTest.log; ctest binaries=12",
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        # Drop upstream cmake config dir to avoid conflict with CMakeDeps file name.
        rmdir(self, os.path.join(self.package_folder, "lib", "libjwt"))

    def package_info(self):
        # libjwt.a references jansson symbols (json_object_set_new, ...);
        # the vendored archive is installed alongside (JANSSON_INSTALL=ON),
        # so list it explicitly. Order matters for static link: jwt first.
        # Shared builds: extra -ljansson is harmless (already in DT_NEEDED).
        self.cpp_info.libs = ["jwt", "jansson"]
        self.cpp_info.set_property("cmake_file_name", "libjwt2")
        self.cpp_info.set_property("cmake_target_name", "libjwt2::jwt")
        self.cpp_info.set_property("pkg_config_name", "libjwt2")
