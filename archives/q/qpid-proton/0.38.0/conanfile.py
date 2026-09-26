#!/usr/bin/env python3
"""Conan recipe — qpid-proton 0.38.0 (CMake).

Apache Qpid Proton is a lightweight, high-performance AMQP 1.0 messaging
library.  The C library ships three shared objects: the core
(types/codecs/engine/connection-driver/framing), the legacy "qpid-proton"
library (messenger + reactor + IO) and the proactor
(epoll/IO, non-blocking multi-thread event loop).

OHOS (HarmonyOS PC, aarch64) adaptation notes
--------------------------------------------
1. CMake 4.1 ships no `Platform/HarmonyOS.cmake`, so on HarmonyOS the platform
   file is not loaded at all: `UNIX` stays unset, no `DT_SONAME` is emitted for
   shared libraries and the linker records build-tree paths in `DT_NEEDED`.
   Forcing `CMAKE_SYSTEM_NAME=Linux` selects the platform-validated Linux
   branch (repo-wide E092 pattern, same as amqp-cpp/arpack-ng/...).
2. With the Linux branch `FIND_LIBRARY_USE_LIB64_PATHS` is TRUE and upstream
   would install into `lib64/`; `LIB_SUFFIX` is cleared so the package keeps the
   conan-standard `lib/` layout.
3. `CMAKE_PLATFORM_NO_VERSIONED_SONAME=TRUE` keeps the unversioned ELF
   `DT_SONAME` (CI L5 SONAME gate) but skips `.so.N` symlink chains, which
   HMDFS does not resolve reliably.  Without it upstream's exported
   `ProtonTargets-release.cmake` also carries `IMPORTED_NO_SONAME` (CI L5c).
4. `patches/0001`: HarmonyOS epoll ignores `EPOLLONESHOT`, which livelocks the
   proactor poller — see notes.md for the full diagnosis.
5. Optional components: OpenSSL (registry `openssl/3.5.8.1`, static) is
   enabled so TLS works and the SSL part of the upstream suite can run.  SASL
   (`SASL_IMPL=none`, upstream-supported) and libuv (the epoll proactor is the
   upstream default on Linux) are not required; jsoncpp is only used by the C++
   binding, which is not built here.
"""

import json
import os
import re
import shutil
import ssl as _ssl
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get

# Upstream ctest entries, for the machine-readable marker below (measured).
CTEST_TIMEOUT_S = 120


class QpidProtonConan(ConanFile):
    name = "qpid-proton"
    version = "0.38.0"
    description = ("Qpid Proton - lightweight AMQP 1.0 messaging library "
                   "(C core, messenger, reactor, epoll proactor)")
    license = "Apache-2.0"
    homepage = "https://qpid.apache.org/proton/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "shared-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # TLS: the registry ships openssl static-only (R26), which is exactly
        # what a shared lib wants here (no extra runtime dependency).
        self.requires("openssl/3.5.8.1")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "qpid-proton 0.38.0 is adapted for Linux/OHOS only")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # E092: no Platform/HarmonyOS module -> force the Linux branch.
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # keep the conan-standard lib/ layout (Linux branch would pick lib64/).
        tc.variables["LIB_SUFFIX"] = ""
        # Keep DT_SONAME, skip versioned symlink chains (CI L5a/L5b/L5c).
        tc.variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "TRUE"

        # Upstream build options.  BUILD_EXAMPLES is required because
        # tests/examples registers the c-example-tests entry against the
        # `c-broker` example target (BUILD_TESTING+!BUILD_EXAMPLES fails to
        # configure).  Bindings (C++/Go/Python/Ruby) are out of scope.
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_EXAMPLES"] = "ON"
        tc.variables["BUILD_CPP"] = "OFF"
        tc.variables["BUILD_GO"] = "OFF"
        tc.variables["BUILD_STATIC_LIBS"] = "OFF"
        tc.variables["BUILD_TLS"] = "OFF"
        tc.variables["ENABLE_FUZZ_TESTING"] = "ON"
        # Upstream enables -Werror by default.  Proton 0.38.0 is gnu99-era code
        # and clang 15 diagnoses its old-style `f()` definitions with
        # -Wstrict-prototypes (14 sites) plus Catch2 warnings in the test
        # suite; upstream itself turns this off for Darwin.  Disabled so the
        # shipped sources stay untouched.
        tc.variables["ENABLE_WARNING_ERROR"] = "OFF"
        # SASL is optional upstream; no test requires it (the bundled test
        # suite runs SASL-less).  TLS is provided by the OpenSSL static build.
        tc.variables["SASL_IMPL"] = "none"
        tc.variables["SSL_IMPL"] = "openssl"
        tc.variables["OPENSSL_ROOT_DIR"] = self.dependencies["openssl"].package_folder
        tc.generate()

    def build(self):
        cmake = CMake(self)
        # Upstream declares cmake_minimum_required(2.8.12); CMake 4.x refuses
        # anything below 3.5 unless the policy minimum is raised.  It must be
        # passed on the configure command line (the cache variable is read too
        # late for the cmake_minimum_required() check).
        cmake.configure(variables={"CMAKE_POLICY_VERSION_MINIMUM": "3.5"})
        cmake.build()
        # The upstream suite is executed unconditionally: this recipe only
        # targets Linux/OHOS (see validate()), the binaries were produced by the
        # host toolchain, and the CI workers set
        # tools.build.cross_building:can_run=False globally, which would
        # otherwise silently skip the very evidence this package must report.
        # A host/platform mismatch surfaces as a reported failure (rc=-1)
        # instead of an exception, so it can never break the build.
        self._run_upstream_tests()

    # ── upstream test suite (ctest) ────────────────────────────────────────
    def _run_upstream_tests(self):
        """Run the upstream ctest suite and record real, parseable counts.

        The suite is reported, not enforced: two of its entries fail because
        upstream's own bundled test certificates expired on 2025-11-24 (see
        notes.md).  Failing the recipe for that would hide a pre-existing,
        platform-independent fixture defect, so the counts and the certificate
        evidence are emitted as machine-readable lines instead.
        """
        log_path = os.path.join(self.build_folder, "upstream-ctest.log")
        self.output.info("upstream test command: ctest -V --timeout %d (cwd=%s)"
                         % (CTEST_TIMEOUT_S, self.build_folder))
        try:
            with open(log_path, "w") as log:
                proc = subprocess.run(
                    ["ctest", "-V", "--timeout", str(CTEST_TIMEOUT_S)],
                    cwd=self.build_folder, stdout=log,
                    stderr=subprocess.STDOUT, timeout=1800)
            rc = proc.returncode
        except Exception as exc:  # pragma: no cover - environment failure
            self.output.warning("ctest could not be executed: %s" % exc)
            rc = -1
        output = ""
        try:
            with open(log_path, "r", errors="replace") as log:
                output = log.read()
        except OSError:
            pass

        marker = self._summarize_ctest(output, rc)
        print("QPID_PROTON_UPSTREAM_TEST_RESULT=" + json.dumps(marker), flush=True)
        self.output.info("QPID_PROTON_UPSTREAM_TEST_RESULT=" + json.dumps(marker))
        for line in marker["failed_tests"]:
            self.output.info("upstream ctest FAILED: %s" % line)
        cert = self._ssl_certificate_evidence()
        if cert:
            print("QPID_PROTON_SSL_TEST_CERT=" + json.dumps(cert), flush=True)
            self.output.info("QPID_PROTON_SSL_TEST_CERT=" + json.dumps(cert))
        self.output.info("full upstream ctest log: %s" % log_path)

    @staticmethod
    def _summarize_ctest(output, rc):
        summary = {"status": "passed" if rc == 0 else "failed",
                   "framework": "ctest",
                   "command": "ctest -V --timeout %d" % CTEST_TIMEOUT_S,
                   "return_code": rc,
                   "registered": 0, "passed": 0, "failed": 0,
                   "catch2_test_cases": 0, "catch2_test_cases_passed": 0,
                   "catch2_assertions": 0, "catch2_assertions_passed": 0,
                   "failed_tests": []}
        for raw in output.splitlines():
            # ctest -V prefixes the output of the test process with "<n>: ".
            prefix = re.match(r"^\d+:\s?(.*)$", raw)
            line = (prefix.group(1) if prefix else raw).strip()
            if "tests passed," in line and "out of" in line:
                counts = re.search(
                    r"(\d+)%\s+tests passed,\s+(\d+) tests? failed out of (\d+)",
                    line)
                if counts:
                    summary["failed"] = int(counts.group(2))
                    summary["registered"] = int(counts.group(3))
            elif line.startswith("test cases:"):
                nums = [int(x) for x in line.replace("|", " ").split()
                        if x.isdigit()]
                if len(nums) >= 3:
                    summary["catch2_test_cases"] += nums[0]
                    summary["catch2_test_cases_passed"] += nums[1]
            elif line.startswith("assertions:") and "passed" in line:
                nums = [int(x) for x in line.replace("|", " ").split()
                        if x.isdigit()]
                if len(nums) >= 3:
                    summary["catch2_assertions"] += nums[0]
                    summary["catch2_assertions_passed"] += nums[1]
            elif "assertions in" in line and "test case" in line:
                # "All tests passed (N assertions in M test case[s])"
                nums = [int(x) for x in line.replace("(", " ").replace(")", " ")
                        .split() if x.isdigit()]
                if len(nums) >= 2:
                    summary["catch2_assertions"] += nums[0]
                    summary["catch2_assertions_passed"] += nums[0]
                    summary["catch2_test_cases"] += nums[1]
                    summary["catch2_test_cases_passed"] += nums[1]
            elif "***Failed" in line or "***Timeout" in line:
                summary["failed_tests"].append(line)
        if summary["registered"]:
            summary["passed"] = summary["registered"] - summary["failed"]
        return summary

    def _ssl_certificate_evidence(self):
        """notAfter of the two bundled test certificates (best effort).

        Used to document why the SSL ctest entries fail on any host today,
        independent of the OHOS port.
        """
        evidence = {}
        for rel in ("c/tests/ssl-certs/tserver-certificate.pem",
                    "c/tests/ssl-certs/tclient-certificate.pem"):
            path = os.path.join(self.source_folder, rel)
            try:
                evidence[rel] = _ssl._ssl._test_decode_cert(path)["notAfter"]
            except Exception as exc:
                evidence[rel] = "unreadable: %s" % exc
        return evidence

    def package(self):
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        self._drop_python_bytecode()
        self._resign_installed_libraries()

    def _drop_python_bytecode(self):
        """Drop __pycache__ created by the upstream Python test harnesses.

        Upstream installs its test helpers into share/proton; running the suite
        makes CPython write byte-code caches inside those directories, which
        would otherwise be packaged as build residue.
        """
        removed = 0
        for root, dirs, _ in os.walk(self.package_folder):
            for name in list(dirs):
                if name == "__pycache__":
                    shutil.rmtree(os.path.join(root, name), ignore_errors=True)
                    dirs.remove(name)
                    removed += 1
        if removed:
            self.output.info("removed %d __pycache__ directories" % removed)

    def _ohos_tool(self, name):
        """Locate one of the OHOS SDK tools shipped next to the compiler."""
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        compiler = compilers.get("c", "") or compilers.get("cpp", "")
        candidates = (
            os.path.join(os.path.dirname(compiler), name) if compiler else "",
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        )
        return next((path for path in candidates
                     if path and os.path.isfile(path)), "")

    def _resign_installed_libraries(self):
        """Re-sign the installed shared objects.

        HarmonyOS verifies the ELF `.codesign` section on load: a library whose
        bytes change after linking is refused with "Permission denied".  CMake's
        install step rewrites the RPATH of libraries that depend on other
        in-tree libraries (libqpid-proton-proactor.so -> libqpid-proton-core.so)
        and drops the build-tree RPATH, which invalidates the signature the
        linker embedded, so the packaged copy cannot be dlopen'ed or resolved
        through DT_NEEDED.  Sign the installed copies again (same step the
        openmama recipe uses for its consumers).
        """
        objcopy = self._ohos_tool("llvm-objcopy")
        signer = self._ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanException(
                "OHOS llvm-objcopy/binary-sign-tool not found: the installed "
                "shared objects would keep an invalidated .codesign section "
                "and could not be loaded")
        libraries = []
        for root, _, files in os.walk(os.path.join(self.package_folder, "lib")):
            for name in files:
                if ".so" in name:
                    libraries.append(os.path.join(root, name))
        for path in libraries:
            unsigned = path + ".unsigned"
            try:
                shutil.copy2(path, unsigned)
                self.run('env -u LD_LIBRARY_PATH %s --remove-section .codesign "%s" '
                         '2>/dev/null || true' % (objcopy, unsigned))
                self.run('env -u LD_LIBRARY_PATH %s sign -inFile "%s" -outFile "%s" '
                         '-selfSign 1' % (signer, unsigned, path))
            finally:
                if os.path.exists(unsigned):
                    os.remove(unsigned)
        self.output.info("re-signed %d installed shared object(s)" % len(libraries))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Proton")
        self.cpp_info.set_property("cmake_target_name", "Proton::qpid-proton")
        self.cpp_info.set_property("pkg_config_name", "libqpid-proton")
        # libqpid-proton.so already embeds the core/proactor objects; listing
        # the three upstream libraries keeps the target usable either way.
        self.cpp_info.libs = ["qpid-proton", "qpid-proton-core",
                              "qpid-proton-proactor"]
        self.cpp_info.system_libs = ["m", "dl", "pthread"]
