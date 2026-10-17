#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""conanfile.py — rhonabwy 1.1.13 (HarmonyOS PC / OHOS aarch64 adaptation).

Recipes the upstream CMake project of babelouest/rhonabwy (the JOSE/JWK/JWS/JWE/
JWT C library of the ulfius family) for OHOS aarch64 device-native builds, runs
its libcheck CTest programs inside ``build()`` and ships both the shared library
and the ``rnbyc`` command line tool.
"""

import json
import os
import re
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rmdir

required_conan_version = ">=1.52.0"

# Upstream test programs that embed an Ulfius HTTP server in order to serve the
# generated `cert/` TLS fixtures over loopback. Ulfius is a test-only dependency
# here; the portability patch adds these programs to the CTest set only when
# Ulfius is actually found.
ULFIUS_TESTS = ("jwk_export", "jwk_import", "jwks_core", "jws_core", "jwe_core", "jwt_core")

# The upstream CTest set (CMakeLists.txt `set(TESTS ...)`, 25 programs) minus the
# Ulfius-backed ones above. These 19 programs are self-contained (all fixtures are
# literals inside the .c files) and are the ones built and executed on OHOS.
RUNNABLE_TESTS = (
    "misc", "cookbook", "jwk_core",
    "jws_hmac", "jws_ecdsa", "jws_rsa", "jws_rsapss", "jws_json",
    "jwe_rsa", "jwe_aesgcm", "jwe_dir", "jwe_kw", "jwe_rsa_oaep",
    "jwe_ecdh", "jwe_pbes2", "jwe_json",
    "jwt_encrypt", "jwt_sign", "jwt_nested",
)

# tcase_add_test() registrations counted in the sources of RUNNABLE_TESTS (source
# audit: misc 6, cookbook 3, jwk_core 9, jws_hmac 13, jws_ecdsa 15, jws_rsa 13,
# jws_rsapss 12, jws_json 25, jwe_rsa 8, jwe_aesgcm 7, jwe_dir 8, jwe_kw 9,
# jwe_rsa_oaep 14, jwe_ecdh 21, jwe_pbes2 9, jwe_json 23, jwt_encrypt 11,
# jwt_sign 13, jwt_nested 34). The 6 Ulfius-backed programs add another 126.
_UPSTREAM_CASES_IN_RUNNABLE_TESTS = 253


class RhonabwyConan(ConanFile):
    name = "rhonabwy"
    version = "1.1.13"
    description = "C library to handle JOSE (JWK/JWS/JWE/JWT) and OAuth2/OIDC flows"
    homepage = "https://github.com/babelouest/rhonabwy"
    topics = ("jose", "jwt", "jws", "jwe", "jwk", "oauth2", "openid")
    license = "LGPL-2.1-or-later"
    url = "https://github.com/babelouest/rhonabwy"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_curl": [True, False],
    }
    default_options = {
        # Upstream only ever installs the shared library (`set(TARGETS rhonabwy)`
        # in CMakeLists.txt); BUILD_STATIC builds rhonabwy_static but nothing
        # installs it. The package is therefore shared-only.
        "shared": True,
        "fPIC": True,
        # WITH_CURL: fetch remote JWKS / JWT content over HTTP(S) with libcurl.
        "with_curl": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if not self.options.shared:
            raise ConanInvalidConfiguration(
                "rhonabwy/1.1.13 upstream installs only its shared library; "
                "build with -o rhonabwy/*:shared=True")
        # Pure C library: neither libcxx nor cppstd takes part in the package id.
        for setting in ("libcxx", "cppstd"):
            try:
                delattr(self.settings.compiler, setting)
            except Exception:
                pass

    def requirements(self):
        # Hard build/link dependencies of the library itself (CMakeLists.txt
        # lines 90-125). Every one of them is published for OHOS/aarch64 on the
        # ohpcd registry (W0 preflight checked).
        self.requires("gnutls/3.8.10")     # JWS/JWE crypto primitives
        self.requires("nettle/3.10.2.1")   # find_package(Nettle) is called directly
        self.requires("jansson/2.15.1.1")  # JSON parsing
        self.requires("zlib/1.3.1.1")      # find_package(ZLIB) is called directly
        self.requires("curl/8.15.0")       # optional remote content (WITH_CURL)
        self.requires("orcania/2.3.3")     # sibling babelouest library
        self.requires("libyder/1.4.20")    # sibling babelouest logging library
        # gnutls/nettle want gmp/6.3.0, but the OHOS/aarch64 binary of 6.3.0 is not
        # usable from this environment; the published 6.3.0.1 is the pin the other
        # OHOS adaptations of this family use (see ulfius 2.7.15). Only the version
        # is overridden, the recipe is untouched.
        self.requires("gmp/6.3.0.1", override=True)

    def build_requirements(self):
        # check/0.15.2 builds and runs the upstream CTest suite. Test-only: never
        # propagated to consumers and not part of the package_id. Same pattern as
        # the repo precedents orcania 2.3.3 / libyder 1.4.20 / ulfius 2.7.15.
        self.test_requires("check/0.15.2")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            destination=self.source_folder, strip_root=True)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_STATIC"] = False
        tc.variables["BUILD_RHONABWY_DOCUMENTATION"] = False
        tc.variables["BUILD_RNBYC"] = True
        tc.variables["INSTALL_HEADER"] = True
        tc.variables["WITH_CURL"] = self.options.with_curl
        tc.variables["BUILD_RHONABWY_TESTING"] = False  # toggled in build()
        # Orcania and Yder are consumed through the CMakeDeps CONFIG packages,
        # which do not define the `<NAME>_VERSION_STRING` module variables the
        # upstream version gates read (CMakeLists.txt lines 198 and 214). Seed
        # them from the versions actually resolved in the graph so the gates stay
        # meaningful instead of being bypassed.
        tc.variables["ORCANIA_VERSION_STRING"] = self._dep_version("orcania")
        tc.variables["YDER_VERSION_STRING"] = self._dep_version("libyder")
        # The published gmp package reports no include directory (the generated
        # gmp-release-*-data.cmake has an empty gmp_INCLUDE_DIRS_RELEASE), so the
        # <gmp.h> that nettle's public headers pull in never reaches the compile
        # command. Hand the directory the package installs it in to the build; the
        # portability patch appends it to the Nettle target.
        gmp_inc = os.path.join(self._dep_folder("gmp"), "include")
        if os.path.isfile(os.path.join(gmp_inc, "gmp.h")):
            tc.variables["GMP_INCLUDE_DIR"] = gmp_inc
        tc.generate()

    def _dep_version(self, name):
        try:
            return str(self.dependencies[name].ref.version)
        except Exception:
            return ""

    def _dep_folder(self, name):
        try:
            dep = self.dependencies.get(name)
        except Exception:
            dep = None
        return dep.package_folder if dep else ""

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        check_pkg = self._dep_folder("check")
        run_tests = bool(check_pkg)
        cfg_vars = {"BUILD_RHONABWY_TESTING": "ON" if run_tests else "OFF"}
        if run_tests:
            # Seed rhonabwy's bundled cmake-modules/FindCheck.cmake. The
            # portability patch forces find_package(Check MODULE) so the bundled
            # module (CHECK_FOUND / Check::Check) runs even though the conan
            # toolchain sets CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON. Paths come from
            # the private build prefix of the conan dependency, never from a host
            # /usr same-name library.
            cfg_vars["CHECK_INCLUDE_DIR"] = os.path.join(check_pkg, "include")
            cfg_vars["CHECK_LIBRARY"] = os.path.join(check_pkg, "lib", "libcheck.a")
        cmake.configure(variables=cfg_vars)
        cmake.build()
        if run_tests:
            self._run_upstream_ctests()

    def _dep_lib_dirs(self):
        dirs = []
        for dep in self.dependencies.host.values():
            pkg = dep.package_folder
            if not pkg:
                continue
            lib = os.path.join(pkg, "lib")
            if os.path.isdir(lib):
                dirs.append(lib)
        return dirs

    def _run_upstream_ctests(self):
        bdir = self.build_folder
        env = dict(os.environ)
        ld = [bdir] + self._dep_lib_dirs()
        if env.get("LD_LIBRARY_PATH"):
            ld.append(env["LD_LIBRARY_PATH"])
        env["LD_LIBRARY_PATH"] = ":".join(ld)
        # libcheck forks per test case and needs a writable TMPDIR; OHOS /tmp is
        # read-only, so keep it inside the build folder.
        test_tmp = os.path.join(bdir, ".test-tmp")
        os.makedirs(test_tmp, exist_ok=True)
        env["TMPDIR"] = test_tmp
        env["TMP"] = test_tmp
        env["TEMP"] = test_tmp

        # The upstream test executables are add_executable(... EXCLUDE_FROM_ALL),
        # so they are not produced by the default target; build them explicitly.
        # -j1: the OHOS make cannot create the jobserver fifo (Operation not
        # permitted), which GNU make only tolerates in non-parallel mode.
        self.output.info(
            "[rhonabwy] build %d upstream test programs (EXCLUDE_FROM_ALL)"
            % len(RUNNABLE_TESTS))
        cmd = 'cmake --build "{b}" --target {t} -- -j1'.format(
            b=bdir, t=" ".join(RUNNABLE_TESTS))
        r = subprocess.run(cmd, shell=True, env=env, cwd=bdir,
                           capture_output=True, text=True, timeout=1800)
        if r.stdout:
            self.output.info(r.stdout[-4000:] if len(r.stdout) > 4000 else r.stdout)
        if r.stderr:
            self.output.info("[stderr] " + r.stderr[-2000:])
        if r.returncode != 0:
            raise RuntimeError(
                "building the upstream rhonabwy test programs failed (%d)" % r.returncode)

        self.output.info(
            "[rhonabwy] run upstream CTest (%d of the 25 programs registered by "
            "CMakeLists.txt; the 6 Ulfius-backed ones are skipped, see the "
            "portability patch)" % len(RUNNABLE_TESTS))
        c = subprocess.run(
            'ctest --test-dir "{b}" -V --output-on-failure'.format(b=bdir),
            shell=True, env=env, cwd=bdir, capture_output=True, text=True, timeout=1800)
        out = c.stdout or ""
        # libcheck prints a per-program "Checks: N, Failures: M" summary; that sum is
        # the authoritative number of upstream test cases actually executed, so it is
        # surfaced as a single line that can be quoted as-is in the PR body.
        checks = re.findall(r"Checks: (\d+), Failures: (\d+)", out)
        if checks:
            executed = sum(int(n) for n, _ in checks)
            failures = sum(int(f) for _, f in checks)
            self.output.info(
                "[rhonabwy] upstream libcheck cases executed=%d failures=%d over %d "
                "programs" % (executed, failures, len(checks)))
            # Source audit (tcase_add_test registrations) of the 19 upstream test
            # programs that are buildable here: 253 registrations. libcheck's
            # per-program summary reports 252 executed check functions; the +-1
            # difference is NOT explained by the summary format (the per-program
            # "Checks: N" values match the registrations 1:1 elsewhere), so it is
            # kept visible as `skipped: 1` instead of being papered over.
            # Attribution (verified in the pristine tree): the source-level count
            # 253 includes the EPHEMERAL/secp256k1 case
            # test_rhonabwy_es256k_serialize_verify_ok in test/jws_ecdsa.c, whose
            # definition AND its tcase_add_test() call both sit inside `#if 0`
            # (START_TEST at jws_ecdsa.c:373 under `#if 0` at :372; tcase_add_test at :427 under `#if 0` at :426), so libcheck never registers it and the
            # deficit is an upstream-conditional case, not a test disabled by
            # this adaptation.
            upstream = {"discovered": _UPSTREAM_CASES_IN_RUNNABLE_TESTS,
                        "executed": executed, "passed": executed - failures,
                        "failed": failures,
                        "skipped": _UPSTREAM_CASES_IN_RUNNABLE_TESTS - executed,
                        "status": "passed" if failures == 0 else "failed"}
            self.output.info(
                "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))
        if out:
            self.output.info(out[-20000:] if len(out) > 20000 else out)
        if c.stderr:
            self.output.info("[stderr] " + c.stderr[-2000:])
        if c.returncode != 0:
            raise RuntimeError("upstream rhonabwy CTest failed (%d)" % c.returncode)

    def package(self):
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        for extra in ("README.md", "COPYING"):
            copy(self, extra, self.source_folder,
                 os.path.join(self.package_folder, "licenses"),
                 keep_path=False)
        cmake = CMake(self)
        cmake.install()
        # Drop the upstream CMake package config and the pkg-config file: the
        # consumers in this repository resolve the package through the
        # CMakeDeps/CMakeConfigDeps generator of the conan recipe instead.
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Rhonabwy")
        self.cpp_info.set_property("cmake_target_name", "Rhonabwy::Rhonabwy")
        self.cpp_info.set_property("pkg_config_name", "librhonabwy")
        self.cpp_info.libs = ["rhonabwy"]
        # The upstream project also installs its CLI (`rnbyc`) into bin/, so the
        # package is a library + tool package: bindirs is declared for consumers
        # that want to call the executable, and archives/r/rhonabwy/commands.json
        # describes it (R38).
        self.cpp_info.bindirs = ["bin"]
        # include/rhonabwy.h is a "fat" public header: it unconditionally includes
        # <jansson.h>, <gnutls/gnutls.h> and <nettle/version.h>, and the upstream
        # test programs additionally include <check.h>, <yder.h> and <orcania.h>
        # while linking nothing but Rhonabwy::Rhonabwy. Because rhonabwy is a shared
        # library, linking alone does not forward a dependency's usage requirements.
        # This package therefore deliberately does NOT declare `cpp_info.requires`:
        # per the two repo precedents that probed the same situation (ulfius/2.7.15
        # test_package and dwarves/1.30 test_package), a library's cpp_info.requires
        # is not expanded into the consumer's CMake graph, so consumers must declare
        # the public-header dependencies in their own requirements() anyway. A bare
        # consumer that only requires rhonabwy/1.1.13 and includes <rhonabwy.h> still
        # fails to compile (`jansson.h: file not found`) -- verified locally with a
        # throwaway consumer package on 2026-09-26, see notes.md/PR body.
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
