#!/usr/bin/env python3
"""Conan recipe — ulfius 2.7.15 (CMake).

A C web framework to build REST APIs, webservices or any HTTP endpoint. Upstream
uses CMake and exposes a CTest suite (5 official test programs built with the
Check framework: core/u_map/framework/example_callbacks/websocket).

OHOS notes:
  * WITH_YDER is disabled: no yder recipe exists in this tree and ulfius ships
    internal mock yder_* functions when U_DISABLE_YDER is defined (src/ulfius.c),
    so the framework's own logging stubs are used instead.
  * The dependency chain includes shared libraries (gnutls is shipped as libgnutls.so
    and curl defaults to shared), so the recipe builds ulfius as a shared library and
    relies on the Conan runenv (LD_LIBRARY_PATH) when running the upstream CTest suite.
  * Subunit (Debian-era default of the upstream test tree) is made optional by a
    portability patch; the Conan libcheck (check/0.15.2) is self-contained.
  * HTTPS test-capability limitation (documented-blocked in the harness): ulfius's
    own compile links GnuTLS, but actually running the HTTPS server endpoints requires
    libmicrohttpd to have been built with GnuTLS/HTTPS support. The published ohpcd
    libmicrohttpd/1.0.1 is built with HTTPS DISABLED (its own notes: "HTTPS 可选，
    默认禁用 gnutls"), so MHD_start_daemon(MHD_USE_SSL, ...) returns NULL and ulfius
    maps it to U_ERROR_LIBMHD (4). Three upstream Check functions that hard-require
    MHD HTTPS therefore cannot pass on OHOS and are treated as documented-blocked
    (not run / audited below): core:test_ulfius_start_instance (it starts an HTTPS
    daemon with a fixed PEM and asserts U_OK), framework:test_ulfius_server_ca_trust
    and test_ulfius_client_certificate (both call ulfius_start_secure_ca_trust_framework
    and assert U_OK). The harness still runs the full upstream suite on-device, verifies
    that these are the ONLY failures, excludes them as audited-blocked, and reports an
    honest pass count over the runnable checks.
"""
import json
import os
import re
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rmdir


class UlfiusConan(ConanFile):
    name = "ulfius"
    version = "2.7.15"
    package_type = "library"

    description = ("Web Framework to build REST APIs, Webservices or any HTTP endpoint in C "
                   "language. Can stream large amount of data, integrate JSON data with Jansson, "
                   "and create websocket services")
    homepage = "https://github.com/babelouest/ulfius"
    license = "LGPL-2.1-or-later"
    url = "https://github.com/babelouest/ulfius"
    topics = ("http", "rest", "webservice", "websocket", "framework")

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libmicrohttpd/1.0.1")
        # ulfius's public CMake target (Ulfius::Ulfius) links Orcania::Orcania
        # (the SHARED target, see CMakeLists.txt). Force the sibling library to
        # shared so that target exists when ulfius is built shared.
        self.requires("orcania/2.3.3", options={"shared": True})
        self.requires("curl/8.15.0")
        self.requires("gnutls/3.8.10")
        self.requires("jansson/2.15.1.1")
        self.requires("zlib/1.3.1.1")
        # Publish-sanity pin of gmp. The published, OHOS-verified gmp in this
        # archive is 6.3.0.1 (merged feat/gmp-6.3.0.1, with config.guess/sub
        # OHOS recognition, explicit --build/--host and the configure umask-077
        # hmdfs fix baked in). gnutls/3.8.10 and nettle/3.10.2.1 both still
        # require gmp/6.3.0; because gmp/6.3.0 has no binary on ohpcd for the
        # OHOS aarch64 config, Conan falls back to the conan-center gmp/6.3.0
        # recipe, whose tool_require m4/1.4.19 fails to configure on OHOS
        # (config.guess "unable to guess system type" --- readonly /tmp plus
        # config.guess's umask-077 tempdirs are EACCES on hmdfs, and conan-center
        # config.sub has no linux-ohos branch). Overriding to the published
        # 6.3.0.1 pulls the working binary instead of rebuilding the broken
        # toolchain from source.
        self.requires("gmp/6.3.0.1", override=True)

    def build_requirements(self):
        # check/0.15.2 builds and runs the upstream CTest suite (5 official test
        # programs). Test-only requirement: available while building/running the
        # upstream tests but never propagated to consumers / not part of package_id.
        self.test_requires("check/0.15.2")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            destination=self.source_folder, strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_STATIC"] = "OFF" if self.options.shared else "ON"
        # Feature flags: all capabilities are enabled (HTTPS via GnuTLS, JSON via
        # Jansson, HTTP client via CURL, websocket via MHD+ZLIB). Yder logging is
        # disabled (mock yder functions are provided internally by ulfius).
        tc.variables["WITH_CURL"] = "ON"
        tc.variables["WITH_JANSSON"] = "ON"
        tc.variables["WITH_GNUTLS"] = "ON"
        tc.variables["WITH_WEBSOCKET"] = "ON"
        tc.variables["WITH_WEBSOCKET_MESSAGE_LIST"] = "ON"
        tc.variables["WITH_YDER"] = "OFF"
        tc.variables["BUILD_UWSC"] = "OFF"
        tc.variables["BUILD_ULFIUS_DOCUMENTATION"] = "OFF"
        tc.variables["INSTALL_HEADER"] = "ON"
        # ulfius ships its own FindMHD/FindGnuTLS/FindJansson/FindCheck modules in
        # cmake-modules/ and gates its testing tree on CHECK_FOUND. The OHOS Conan
        # toolchain prefers CONFIG mode (CMAKE_FIND_PACKAGE_PREFER_CONFIG=ON), which
        # would resolve these to the CMakeDeps *-config.cmake and never set the module
        # variables (CHECK_FOUND etc.) -> the CTest tree would be silently skipped.
        # Force module-mode-first so the bundled modules run, then CONFIG mode still
        # resolves Orcania (no bundled FindOrcania) and CURL/ZLIB via CMake's own
        # modules + the conan packages on CMAKE_PREFIX_PATH.
        tc.variables["CMAKE_FIND_PACKAGE_PREFER_CONFIG"] = "OFF"
        # ulfius's CMakeLists checks ORCANIA_VERSION_STRING >= 2.3.3; the conan
        # Orcania config (CMakeDeps) does not set that module variable, so seed it.
        tc.variables["ORCANIA_VERSION_STRING"] = "2.3.3"
        tc.generate()

    def _dep_folder(self, name):
        try:
            dep = self.dependencies.get(name)
        except Exception:
            return ""
        return dep.package_folder if dep else ""

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # BUILD_ULFIUS_TESTING is toggled at configure time and drives the upstream
        # CTest tree; it is deliberately always ON here so the upstream suite runs.
        cmake.configure(variables={"BUILD_ULFIUS_TESTING": "ON"})
        cmake.build()
        self._run_upstream_ctests()

    def _find_test_dir(self):
        # The CTest WORKING_DIRECTORY is ${CMAKE_CURRENT_SOURCE_DIR}/test, i.e. the
        # cert/ fixtures are read relative to <source>/test. create-cert.sh must run
        # there (its DEST=./cert) so the generated .crt/.key land next to the tests.
        return os.path.join(self.source_folder, "test")

    def _dep_lib_dirs(self):
        dirs = []
        for dep in self.dependencies.host.values():
            pkg = dep.package_folder
            if pkg:
                lib = os.path.join(pkg, "lib")
                if os.path.isdir(lib):
                    dirs.append(lib)
        return dirs

    def _run_upstream_ctests(self):
        test_dir = self._find_test_dir()
        gnutls_pkg = self._dep_folder("gnutls")
        bdir = self.build_folder

        env = dict(os.environ)
        # Build the test-time LD_LIBRARY_PATH: ulfius build dir + all dependency lib dirs.
        lib_dirs = _unique([bdir] + self._dep_lib_dirs())
        env["LD_LIBRARY_PATH"] = ":".join(lib_dirs + [env.get("LD_LIBRARY_PATH", "")])
        # Writable temp dir for libcheck fork IPC (TMPDIR may be read-only elsewhere).
        test_tmp = os.path.join(self.build_folder, ".test-tmp")
        os.makedirs(test_tmp, exist_ok=True)
        env["TMPDIR"] = test_tmp
        env["TMP"] = test_tmp
        env["TEMP"] = test_tmp
        # certtool (gnutls) + ctest/cmake must be on PATH to generate TLS fixtures.
        if gnutls_pkg:
            env["PATH"] = "{}:{}".format(os.path.join(gnutls_pkg, "bin"), env.get("PATH", ""))

        # Generate the TLS test certificates (cert/server.crt, root1.crt, client*.crt)
        # required by test/framework.c (test_ulfius_server_ca_trust,
        # test_ulfius_client_certificate). The upstream create-cert.sh invokes
        # gnutls certtool; the cert dir starts empty in the tarball.
        cert_script = os.path.join(test_dir, "cert", "create-cert.sh")
        if os.path.isfile(cert_script):
            self.output.info("[ulfius] generating TLS test certificates (create-cert.sh)")
            r = subprocess.run(["sh", cert_script], shell=False, env=env, cwd=test_dir,
                               capture_output=True, text=True, timeout=1200)
            if r.stdout:
                self.output.info(r.stdout[-3000:] if len(r.stdout) > 3000 else r.stdout)
            if r.stderr:
                self.output.info("[stderr] " + r.stderr[-2000:])
            if r.returncode != 0:
                raise RuntimeError("ulfius cert generation failed (%d)" % r.returncode)

        # ── Upstream official CTest suite (5 programs) ──
        # ulfius's own compile links GnuTLS, but running HTTPS server endpoints needs
        # libmicrohttpd built with GnuTLS/HTTPS. The published ohpcd libmicrohttpd/1.0.1
        # is built WITHOUT HTTPS ("HTTPS 可选，默认禁用 gnutls" per its notes), so
        # MHD_start_daemon(MHD_USE_SSL, ...) returns NULL -> U_ERROR_LIBMHD (4).
        # Three upstream Check functions that hard-require MHD HTTPS therefore cannot
        # pass on OHOS. We still run the whole suite on-device, verify these are the
        # ONLY failures, exclude them as documented-blocked (audited below) and report
        # an honest pass count over the runnable checks.
        BLOCKED_HTTPS_CHECKS = {
            "test_ulfius_server_ca_trust",     # framework.c: needs MHD HTTPS + CA trust
            "test_ulfius_client_certificate",  # framework.c: needs MHD HTTPS + client cert
            "test_ulfius_start_instance",      # core.c: ulfius_start_secure_framework()==U_OK
        }
        self.output.info("[ulfius] run upstream CTest (5 official test programs)")
        # -V (verbose) is required: with plain --output-on-failure, ctest only echoes
        # the output of FAILING tests, so the libcheck "Checks:" summaries of the 3
        # passing programs (u_map/example_callbacks/websocket) would be suppressed and
        # the discovered count under-reported. -V echoes each program's stdout.
        c = subprocess.run(
            'ctest --test-dir "{b}" -V --output-on-failure'.format(b=bdir),
            shell=True, env=env, cwd=self.build_folder,
            capture_output=True, text=True, timeout=1800)
        out = c.stdout or ""
        if out:
            self.output.info(out[-6000:] if len(out) > 6000 else out)
        if c.stderr:
            self.output.info("[stderr] " + c.stderr[-3000:])

        # ── Deterministic per-program libcheck summary parsing ──
        # libcheck 0.15.x `sr_stat_str()` emits exactly ONE summary line per
        # program that calls `srunner_run_all(sr, CK_VERBOSE)`, in the form
        #   "N%: Checks: X, Failures: Y, Errors: Z"
        # (see check_str.c sr_stat_str, check_log.c stdout_lfun CLEND_SR, and the
        # captured E571 probe output "100%: Checks: 1, Failures: 0, Errors: 0").
        # Each ulfius program registers a single suite via tcase_add_test and
        # check_run.c increments `sr->stats->n_checked` exactly once per executed
        # test function (srunner_add_failure), so `Checks:` == number of executed
        # test cases, NOT the number of assertion macros.
        #
        # We parse these per-program summaries from ctest's Testing/Temporary/LastTest.log
        # (the deterministic source explicitly recommended by the HMBS guardrails).
        # ctest writes each test's RAW captured stdout into LastTest.log exactly once,
        # WITHOUT the "N: " console prefix that -V adds when streaming to the terminal.
        # Parsing the console stdout instead is unreliable: the passing programs'
        # summary line is prefixed ("5: 100%: Checks: 13, ...") so the anchor regex
        # skips it, while the FAILING programs' summary also appears BARE (no prefix)
        # in ctest's failure re-report, so only the 2 failing programs (core 12,
        # framework 28) were ever seen -> sum 40. Conversely, allowing the "N: "
        # prefix double-counts the failing programs (bare + prefixed) -> sum 127.
        # LastTest.log has neither problem: one raw copy of each program's summary.
        lasttest = os.path.join(bdir, "Testing", "Temporary", "LastTest.log")
        per_program = []
        if os.path.isfile(lasttest):
            with open(lasttest, "r", errors="replace") as fh:
                for line in fh:
                    m = re.search(r"^\s*(\d+)%:\s*Checks:\s*(\d+),\s*Failures:\s*(\d+)", line)
                    if m:
                        per_program.append((int(m.group(2)), int(m.group(3))))
        if not per_program:
            raise RuntimeError(
                "upstream ulfius CTest parsed no libcheck per-program summary lines from "
                "'Testing/Temporary/LastTest.log' (%s, isfile=%s); raw ctest stdout had "
                "no usable summary either" % (lasttest, os.path.isfile(lasttest)))
        total_checks = sum(c for c, _ in per_program)
        total_failures = sum(f for _, f in per_program)

        # The audited official total (== MANIFEST.yml upstream_test_total, derived
        # from the registered tcase_add_test count in the 5 source files:
        # core 12 + u_map 9 + framework 28 + example_callbacks 25 + websocket 13).
        # Our per-program summary sum must equal it. If it does not, the device
        # output differs from the audited structure: fail honestly with the raw
        # per-program breakdown as evidence instead of emitting a contradictory count.
        UPSTREAM_OFFICIAL_TOTAL = 87
        if total_checks != UPSTREAM_OFFICIAL_TOTAL:
            raise RuntimeError(
                "upstream ulfius CTest per-program summary sum (%d) != audited official "
                "total (%d); per-program (checks, failures)=%s -- do not fabricate counts"
                % (total_checks, UPSTREAM_OFFICIAL_TOTAL, per_program))

        # Failing check names from libcheck per-test failure lines
        # "path:line:F:suite:check:N:msg" (check_print.c tr_str, tr_type_str "F").
        failed_checks = []
        for line in out.splitlines():
            m = re.search(r":F:[^:]*:([^:]+):\d+:", line)
            if m and m.group(1) not in failed_checks:
                failed_checks.append(m.group(1))

        # Never hide a genuine regression: any failing check outside the documented
        # HTTPS-blocked set is a real failure.
        unexpected = sorted(n for n in failed_checks if n not in BLOCKED_HTTPS_CHECKS)
        if unexpected:
            raise RuntimeError("upstream ulfius CTest has unexpected failures: %s" % unexpected)
        if len(failed_checks) != total_failures:
            self.output.warning("[ulfius] parsed F-lines (%d) != check-summary Failures (%d); "
                                "using the parsed F-line set" % (len(failed_checks), total_failures))
            total_failures = len(failed_checks)

        # Honest, full-total reporting: `discovered` reflects the whole registered
        # upstream count that ctest ran (== MANIFEST upstream_test_total), not the
        # runnable subset. Any non-passing checks (the known MHD-HTTPS ones, if they
        # fail on this device) are reported via failed + gaps so the identities
        # passed+failed==executed and executed+skipped<=discovered always hold, and
        # the pass-rate is what was truly observed on-device.
        if total_checks == 0:
            raise RuntimeError("upstream ulfius CTest ran no checks (checks=0)")
        blocked = [n for n in failed_checks if n in BLOCKED_HTTPS_CHECKS]
        passed = total_checks - total_failures
        if passed < 0:
            raise RuntimeError("upstream ulfius CTest failure count (%d) exceeds "
                               "checks (%d)" % (total_failures, total_checks))
        result = {
            "status": "passed" if total_failures == 0 else "failed",
            "framework": "ctest",
            "command": "ctest --test-dir {b} -V --output-on-failure".format(b=bdir),
            "discovered": total_checks,
            "executed": total_checks,
            "passed": passed,
            "failed": total_failures,
            "skipped": 0,
        }
        if total_failures > 0:
            result["gaps"] = [{
                "count": total_failures,
                "category": "ohos_feature",
                "detail": "libmicrohttpd (published ohpcd 1.0.1) built without "
                          "GnuTLS/HTTPS when the failing check requires an HTTPS "
                          "server endpoint; affected: %s" % ", ".join(sorted(blocked)),
                "evidence": "ulfius ctest -V libcheck failure lines for: %s"
                            % ", ".join(sorted(blocked)),
            }]
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False))

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        # The CMake install ships the docs/examples; only the library artifact matters.
        rmdir(self, os.path.join(self.package_folder, "share"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))

    def package_info(self):
        self.cpp_info.libs = ["ulfius"]
        self.cpp_info.set_property("cmake_file_name", "Ulfius")
        self.cpp_info.set_property("cmake_target_name", "Ulfius::Ulfius")
        self.cpp_info.set_property("pkg_config_name", "libulfius")
        self.cpp_info.names["cmake_find_package"] = "Ulfius"
        self.cpp_info.names["cmake_find_package_multi"] = "Ulfius"
        self.cpp_info.filenames["cmake_find_package"] = "Ulfius"
        self.cpp_info.filenames["cmake_find_package_multi"] = "Ulfius"

        # The public header include/ulfius.h is a "fat" header: with all feature
        # flags enabled it unconditionally includes <gnutls/gnutls.h>/<gnutls/x509.h>,
        # <jansson.h>, <zlib.h>, <microhttpd.h> and <orcania.h> (see ulfius.h
        # top-of-file; zlib/microhttpd are pulled in unconditionally, without any
        # U_DISABLE_* guard). Consumers compiling against ulfius.h therefore need
        # those dependency include dirs on the compile command. Because ulfius is a
        # shared library, these are not transitively propagated by linking alone --
        # CMakeDeps only forwards a dependency's usage requirements (include dirs /
        # compile defs) when it is declared as a `requires` of the consumer target.
        # Declare them as public `cpp_info.requires` so the CMakeDeps-generated
        # Ulfius target carries the include paths of gnutls/jansson/zlib/
        # libmicrohttpd/orcania. Otherwise compiling a consumer (e.g. test_package)
        # fails with `<gnutls/gnutls.h> file not found` even though linking succeeds.
        # curl is included below even though ulfius.h does not include any curl
        # header directly — curl backs the public ulfius_send_http_request API.
        # Cross-package requires must use the "<pkgname>::<component>" form. All of
        # these dependencies expose a single root component named after the package
        # itself (gnutls/jansson/orcania/libmicrohttpd/zlib/curl), so they are
        # referenced as "pkg::pkg". Bare package names would be interpreted as
        # references to internal components of this package and rejected.
        #
        # All SIX direct requirements must appear here: Conan 2 rejects a direct
        # dependency that is not referenced by any (cpp_info/components).requires
        # ("The direct dependency 'curl' is not used by any ... requires"). curl is
        # included even though ulfius.h does not include curl headers, both to satisfy
        # this rule and because curl backs the public ulfius_send_http_request API.
        self.cpp_info.requires = [
            "gnutls::gnutls",
            "jansson::jansson",
            "orcania::orcania",
            "libmicrohttpd::libmicrohttpd",
            "zlib::zlib",
            "curl::curl",
        ]


def _unique(seq):
    seen = set()
    result = []
    for item in seq:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result
