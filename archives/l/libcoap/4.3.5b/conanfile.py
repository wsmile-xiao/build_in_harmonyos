#!/usr/bin/env python3
"""Conan recipe — libcoap 4.3.5b (CMake).

libcoap is a C implementation of the Constrained Application Protocol
(RFC 7252) with DTLS (OpenSSL backend), TCP/TLS, WebSockets, OSCORE and
example binaries (coap-client / coap-server / coap-rd).

OHOS adaptation notes:
- CMake build (no autoreconf needed on the GitHub tag tarball).
- DTLS via Conan openssl (DTLS_BACKEND=openssl, OPENSSL_ROOT_DIR pinned to
  the Conan package to avoid host shadowing).
- Upstream tests need CUnit (Conan cunit/2.1.3); ENABLE_TESTS=ON builds the
  `testdriver` CUnit binary which build() runs and reports.
- Docs disabled (ENABLE_DOCS=OFF) to avoid doxygen/a2x requirements.
- Shared library keeps upstream `coap-3` ABI; not a system same-name lib
  (R26 does not apply).
"""

import json
import os
import re
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rmdir, save


class LibcoapConan(ConanFile):
    name = "libcoap"
    version = "4.3.5b"
    description = "C implementation of the Constrained Application Protocol (RFC 7252)"
    license = "BSD-2-Clause"
    homepage = "https://libcoap.net/"
    url = "https://github.com/obgm/libcoap"
    topics = ("coap", "iot", "constrained", "dtls")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libcoap supports Linux and OHOS targets, got {self.settings.os}"
            )
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def requirements(self):
        self.requires("openssl/3.5.6.1")

    def build_requirements(self):
        # Upstream testdriver links CUnit (-lcunit); test-only, must not
        # propagate to consumers (dcap 2.47.14 precedent).
        self.test_requires("cunit/2.1.3")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        # Keep Conan's OpenSSL find module from shadowing; use CMake native
        # FindOpenSSL against the Conan package paths (curl 8.15.0 pattern).
        self.dependencies["openssl"].cpp_info.set_property("cmake_find_mode", "none")
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)

        if self.settings.os == "OHOS":
            rules = os.path.join(self.generators_folder, "ohos-cmake-rules.cmake")
            save(
                self,
                rules,
                "\n".join(
                    (
                        'set(CMAKE_SHARED_LIBRARY_SONAME_C_FLAG "-Wl,-soname,")',
                        'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG "-Wl,-rpath,")',
                        'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG_SEP ":")',
                        "set(CMAKE_SHARED_LIBRARY_RPATH_LINK_C_FLAG "
                        '"-Wl,-rpath-link,")',
                        'set(CMAKE_SHARED_LIBRARY_RPATH_ORIGIN_TOKEN "$ORIGIN")',
                    )
                )
                + "\n",
            )
            tc.cache_variables["CMAKE_USER_MAKE_RULES_OVERRIDE_C"] = rules

        openssl = self.dependencies["openssl"].cpp_info
        tc.cache_variables["OPENSSL_ROOT_DIR"] = self.dependencies["openssl"].package_folder
        tc.cache_variables["OPENSSL_INCLUDE_DIR"] = openssl.includedirs[0]
        tc.cache_variables["OPENSSL_SSL_LIBRARY"] = os.path.join(openssl.libdirs[0], "libssl.a")
        tc.cache_variables["OPENSSL_CRYPTO_LIBRARY"] = os.path.join(
            openssl.libdirs[0], "libcrypto.a"
        )

        # testdriver links `-lcunit` directly (no find_package). Feed the
        # Conan CUnit headers/libs via compiler/linker flags.
        cunit = self.dependencies["cunit"]
        cunit_inc = cunit.cpp_info.includedirs[0]
        cunit_lib = cunit.cpp_info.libdirs[0]
        if not os.path.isabs(cunit_inc):
            cunit_inc = os.path.join(cunit.package_folder, cunit_inc)
        if not os.path.isabs(cunit_lib):
            cunit_lib = os.path.join(cunit.package_folder, cunit_lib)
        tc.variables["CMAKE_C_FLAGS"] = f"-I{cunit_inc}"
        tc.variables["CMAKE_EXE_LINKER_FLAGS"] = f"-L{cunit_lib}"

        shared = bool(self.options.shared)
        tc.cache_variables["BUILD_SHARED_LIBS"] = shared
        tc.cache_variables["ENABLE_DTLS"] = True
        tc.cache_variables["DTLS_BACKEND"] = "openssl"
        tc.cache_variables["ENABLE_TESTS"] = True
        tc.cache_variables["ENABLE_EXAMPLES"] = True
        tc.cache_variables["ENABLE_DOCS"] = False
        tc.cache_variables["CMAKE_POSITION_INDEPENDENT_CODE"] = shared or bool(
            self.options.get_safe("fPIC", True)
        )

        if shared:
            tc.cache_variables["CMAKE_BUILD_RPATH_USE_ORIGIN"] = True
            tc.cache_variables["CMAKE_BUILD_WITH_INSTALL_RPATH"] = False
            origin = "$ORIGIN"
            if str(self.settings_build.os) != "Windows":
                origin = r"\$ORIGIN"
            tc.cache_variables["CMAKE_INSTALL_RPATH"] = f"{origin}/../lib;{origin}"
            tc.cache_variables["CMAKE_INSTALL_RPATH_USE_LINK_PATH"] = False
        tc.generate()

    def _host_libdirs(self):
        libdirs = []
        for dep in self.dependencies.host.values():
            pf = getattr(dep, "package_folder", None)
            if not pf:
                continue
            try:
                agg = dep.cpp_info.aggregated_components()
            except Exception:
                continue
            for libdir in agg.libdirs:
                libdirs.append(libdir if os.path.isabs(libdir) else os.path.join(pf, libdir))
        return list(dict.fromkeys(libdirs))

    def _find_testdriver(self):
        for root, _dirs, files in os.walk(self.build_folder):
            if "testdriver" in files:
                cand = os.path.join(root, "testdriver")
                if os.path.isfile(cand):
                    return cand
        return None

    def _parse_cunit_summary(self, output):
        discovered = executed = passed = failed = skipped = 0
        # CUnit Basic verbose prints a Run Summary table, e.g.
        # "Run Summary: Type Total Ran Passed Failed Inactive"
        # "suites 11 11 11 0 0" / "tests 200 200 200 0 0" / "asserts ..."
        m_tests = re.search(
            r"^\s*tests\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)",
            output,
            re.MULTILINE | re.IGNORECASE,
        )
        if m_tests:
            discovered = int(m_tests.group(1))
            executed = int(m_tests.group(2))
            passed = int(m_tests.group(3))
            failed = int(m_tests.group(4))
            skipped = int(m_tests.group(5))
            return discovered, executed, passed, failed, skipped
        # Fallback: count per-test PASS/FAIL lines.
        passes = len(re.findall(r":\s*passed\b", output, re.IGNORECASE))
        fails = len(re.findall(r":\s*FAILED\b", output))
        if passes or fails:
            discovered = executed = passes + fails
            passed = passes
            failed = fails
            return discovered, executed, passed, failed, skipped
        return discovered, executed, passed, failed, skipped

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        if not can_run(self):
            self.output.info("cross-building: libcoap built, target tests cannot run")
            return

        testdriver = self._find_testdriver()
        if not testdriver:
            raise ConanInvalidConfiguration("libcoap testdriver binary not found after build")
        # HMDFS truth machine has no chmod capability (HMBS_CAP_CHMOD=0);
        # a hard chmod failure must not block the build.
        try:
            os.chmod(testdriver, 0o755)
        except OSError as e:
            self.output.info(f"chmod testdriver skipped (no chmod capability): {e}")

        libpath = ":".join(self._host_libdirs())
        env = os.environ.copy()
        if libpath:
            prev = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = f"{libpath}:{prev}" if prev else libpath
        # HMBS readonly_tmp: /tmp is read-only on the truth machine; reuse
        # the injected writable TMPDIR for any harness temp files, falling
        # back to a writable dir under the build folder when TMPDIR is
        # unset or points at the readonly /tmp.
        _tmp = (
            os.environ.get("TMPDIR") or os.environ.get("TMP") or os.environ.get("TEMP")
        )
        if not _tmp or _tmp == "/tmp":
            _tmp = os.path.join(self.build_folder, "tmp")
        try:
            os.makedirs(_tmp, exist_ok=True)
        except OSError as e:
            self.output.info(f"tmpdir setup skipped: {e}")
        for _key in ("TMPDIR", "TMP", "TEMP"):
            env[_key] = _tmp

        proc = subprocess.run(
            [testdriver],
            cwd=os.path.dirname(testdriver),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env=env,
            text=True,
            timeout=600,
        )
        output = proc.stdout or ""
        # Keep the raw harness output in the log for evidence, then falsify:
        # a stub binary printing nothing must not count as passed.
        self.output.info("libcoap testdriver output (tail):\n" + output[-4000:])
        if not output.strip():
            raise ConanInvalidConfiguration("libcoap testdriver produced no output")
        if proc.returncode != 0:
            raise ConanInvalidConfiguration(
                f"libcoap testdriver failed with exit code {proc.returncode}"
            )

        discovered, executed, passed, failed, skipped = self._parse_cunit_summary(output)
        if discovered <= 0 or executed != discovered or failed != 0:
            raise ConanInvalidConfiguration(
                f"libcoap upstream tests incomplete: "
                f"discovered={discovered} executed={executed} "
                f"passed={passed} failed={failed} skipped={skipped}"
            )
        marker = {
            "status": "passed",
            "framework": "cunit",
            "command": "./testdriver",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))
        # Persist for test_package re-emit (build cache hits skip build()).
        res_dir = os.path.join(self.build_folder, "libcoap_res")
        os.makedirs(res_dir, exist_ok=True)
        with open(os.path.join(res_dir, "upstream_test_result.json"), "w", encoding="utf-8") as f:
            json.dump(marker, f)

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        # Remove upstream CMake exports so downstream find_package(libcoap)
        # resolves only to the CMakeDeps-generated config (curl/cnats precedent);
        # otherwise the upstream libcoapTargets.cmake pulls its own OpenSSL
        # imported targets without Conan's search paths.
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        # Persist upstream evidence alongside the package for test_package.
        res_src = os.path.join(self.build_folder, "libcoap_res", "upstream_test_result.json")
        if os.path.isfile(res_src):
            copy(
                self,
                "upstream_test_result.json",
                src=os.path.join(self.build_folder, "libcoap_res"),
                dst=os.path.join(self.package_folder, "res"),
            )

    def package_info(self):
        self.cpp_info.libs = ["coap-3"]
        # DTLS backend links OpenSSL symbols; propagate so CMakeDeps emits
        # find_dependency(openssl) for consumers. Registry openssl is a
        # package-level target (no components), hence openssl::openssl
        # (cnats 3.13.0 precedent). Without this, libcoap_DEPS_TARGET
        # references openssl::openssl with no defining target and
        # test_package configure fails.
        self.cpp_info.requires = ["openssl::openssl"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include", os.path.join("include", "coap3")]
        self.cpp_info.set_property("cmake_file_name", "libcoap")
        self.cpp_info.set_property("cmake_target_name", "libcoap::coap-3")
        self.cpp_info.set_property("pkg_config_name", "libcoap-3")
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
