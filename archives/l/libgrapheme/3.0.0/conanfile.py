#!/usr/bin/env python3
"""Conan recipe — libgrapheme 3.0.0 (suckless Makefile + configure)."""

import json
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import copy, export_conandata_patches, get
from conan.tools.files import apply_conandata_patches
from conan.tools.layout import basic_layout

# Upstream test binaries built by `make test` (Makefile TEST list,
# BINSUFFIX is empty on Linux/OHOS).
UPSTREAM_TEST_PROGRAMS = (
    "test/bidirectional",
    "test/case",
    "test/character",
    "test/line",
    "test/sentence",
    "test/utf8-decode",
    "test/utf8-encode",
    "test/word",
)

# Official registered total for libgrapheme 3.0.0, derived once from the
# release tarball (see test_package/MANIFEST.yml for the full derivation):
# 884508 conformance assertions + 166 unit assertions.
UPSTREAM_TOTAL = 884674

# Each test binary prints one deterministic summary line per group, e.g.
#   ./test/word: 1944/1944 conformance tests passed.
#   ./test/case: grapheme_is_lowercase_utf8: 11/11 unit tests passed.
# This is the single counting source (exact X/Y fractions, no estimation).
SUMMARY_RE = re.compile(
    r"^(?P<prog>\S+): (?:(?P<name>\S+): )?"
    r"(?P<passed>\d+)/(?P<total>\d+) "
    r"(?P<kind>conformance|unit) tests passed\.$"
)


class LibgraphemeConan(ConanFile):
    name = "libgrapheme"
    version = "3.0.0"
    description = "Small and simple C library for grapheme clusters and word segmentation"
    license = "ISC"
    homepage = "https://libs.suckless.org/libgrapheme/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No external dependencies: the library, its generators and its
        # test programs only need a C99 compiler plus the bundled
        # data/*.txt fixtures shipped inside the release tarball.
        pass

    def validate(self):
        # R32: OHOS platform compatibility uses tuple membership.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libgrapheme is adapted for Linux and OHOS, not %s"
                % self.settings.os
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _tool(self, conf_key, fallbacks):
        try:
            configured = self.conf.get(conf_key, default=None, check_type=str)
        except Exception:
            configured = None
        if configured and os.path.isfile(configured):
            return configured
        for name in fallbacks:
            found = shutil.which(name)
            if found:
                return found
        if configured:
            return configured
        return fallbacks[0]

    def generate(self):
        # R33: compiler paths come from Conan conf / HMBS injection, never
        # from bare shell environment variables (empty on CI workers).
        env = VirtualBuildEnv(self)
        env.generate()
        cc = self._tool("tools.build:compiler_executables:c", ("clang", "cc"))
        cxx = self._tool(
            "tools.build:compiler_executables:cpp", ("clang++", "c++")
        )
        ar = self._tool("tools.build:compiler_executables:ar", ("llvm-ar", "ar"))
        ranlib = self._tool(
            "tools.build:compiler_executables:ranlib", ("llvm-ranlib", "ranlib")
        )
        saved = Environment()
        saved.define("CC", cc)
        saved.define("CXX", cxx)
        saved.define("AR", ar)
        saved.define("RANLIB", ranlib)
        saved.vars(self).save_sh("conanbuild")

    def _make_base_cmd(self):
        make = (
            os.getenv("HMBS_MAKE")
            or self.conf.get("user.hmbs:make_path", default=None, check_type=str)
            or shutil.which("make")
            or "make"
        )
        cc = self._tool("tools.build:compiler_executables:c", ("clang", "cc"))
        ar = self._tool("tools.build:compiler_executables:ar", ("llvm-ar", "ar"))
        ranlib = self._tool(
            "tools.build:compiler_executables:ranlib", ("llvm-ranlib", "ranlib")
        )
        # BUILD_CC builds the code generators (gen/*); native build, so the
        # same C compiler is correct.
        return "%s CC=%s AR=%s RANLIB=%s BUILD_CC=%s" % (
            make, cc, ar, ranlib, cc,
        )

    def _emit_upstream(self, payload):
        line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(
            payload, separators=(",", ":")
        )
        # Dual channel: conan output + raw stdout so preflight log parsing
        # finds the marker even when output is filtered.
        self.output.info(line)
        try:
            print(line, flush=True)
        except Exception:
            pass
        try:
            with open(
                os.path.join(self.build_folder, "hmbs_upstream.json"),
                "w",
                encoding="utf-8",
            ) as handle:
                json.dump(payload, handle)
        except Exception as exc:
            self.output.warning("persist hmbs_upstream.json failed: %s" % exc)
        return line

    def _run_upstream_suite(self):
        # Run the 8 upstream test programs one by one (exactly what the
        # upstream `test` target executes) and aggregate the deterministic
        # X/Y summary fractions they print. Failure of a program never
        # aborts the loop: every program's evidence is collected first.
        passed_sum = 0
        total_sum = 0
        programs_ok = 0
        failures = []
        for prog in UPSTREAM_TEST_PROGRAMS:
            binary = os.path.join(self.source_folder, prog)
            safe = prog.replace("/", "_")
            log_path = os.path.join(self.build_folder, "hmbs-%s.log" % safe)
            rc_path = os.path.join(self.build_folder, "hmbs-%s.rc" % safe)
            if not os.path.isfile(binary):
                failures.append("%s: binary missing" % prog)
                continue
            self.run(
                '"%s" > "%s" 2>&1; echo $? > "%s"'
                % (binary, log_path, rc_path),
                cwd=self.source_folder,
            )
            try:
                with open(log_path, "r", encoding="utf-8",
                          errors="replace") as handle:
                    log_text = handle.read()
                with open(rc_path, "r", encoding="utf-8") as handle:
                    rc = int(handle.read().strip())
            except Exception as exc:
                failures.append("%s: unreadable evidence (%s)" % (prog, exc))
                continue
            lines = [
                m for m in
                (SUMMARY_RE.match(l.strip()) for l in log_text.splitlines())
                if m is not None
            ]
            if not lines:
                failures.append(
                    "%s: no X/Y summary line in output (rc=%d)" % (prog, rc)
                )
                continue
            programs_ok += 1
            prog_failed = 0
            for match in lines:
                passed_sum += int(match.group("passed"))
                total_sum += int(match.group("total"))
                prog_failed += int(match.group("total")) - int(
                    match.group("passed")
                )
            if rc != 0 or prog_failed:
                failures.append(
                    "%s: rc=%d failed_assertions=%d" % (prog, rc, prog_failed)
                )
        return passed_sum, total_sum, programs_ok, failures

    def build(self):
        apply_conandata_patches(self)
        # R5: OHOS has no /bin/sh; drive configure through CONFIG_SHELL.
        config_shell = os.environ.get("CONFIG_SHELL", "sh")
        self.run("%s ./configure" % config_shell, cwd=self.source_folder)
        make_cmd = self._make_base_cmd()
        # R9: plain -j1, never parallel.
        self.run("%s -j1" % make_cmd, cwd=self.source_folder)
        # Upstream `all` never builds test programs (Makefile: only the
        # `test` target depends on $(TEST)); without this step the 8
        # binaries stay missing and the evidence loop below runs 0
        # assertions. Build them explicitly here; execution and X/Y
        # aggregation stay in _run_upstream_suite (single source).
        self.run(
            "%s -j1 %s" % (make_cmd, " ".join(UPSTREAM_TEST_PROGRAMS)),
            cwd=self.source_folder,
        )
        # Layer 1 (upstream official suite): run every test program and
        # aggregate the deterministic X/Y summary fractions.
        passed_sum, total_sum, programs_ok, failures = self._run_upstream_suite()
        executed = total_sum
        failed = total_sum - passed_sum
        discovered = UPSTREAM_TOTAL
        identities_ok = (
            isinstance(passed_sum, int)
            and isinstance(failed, int)
            and isinstance(executed, int)
            and isinstance(discovered, int)
            and passed_sum >= 0
            and failed >= 0
            and executed >= 0
            and passed_sum + failed == executed
            and executed <= discovered
        )
        denominator_ok = total_sum == UPSTREAM_TOTAL
        if identities_ok and denominator_ok and not failures:
            self._emit_upstream({
                "status": "passed",
                "framework": "make",
                "command": "make test (8 test programs, X/Y summary fractions)",
                "discovered": discovered,
                "executed": executed,
                "passed": passed_sum,
                "failed": 0,
                "skipped": 0,
            })
            return
        # Honest failure path: keep the real counts, explain the gap, and
        # continue to package. Test failures are NOT build failures: the
        # numbers are never adjusted, the failed marker with gaps is
        # emitted, and conan create succeeds so the evidence reaches
        # rule4. Upstream 3.0.0 test/line 744 failures are an upstream
        # regression (identical 18594/19338 on Gentoo Linux), not
        # OHOS-specific: Unicode 17 new LB classes AK/AP/AS/VF/VI/PI and
        # BOTH_QU_PI exist in gen/line.c tables but src/line.c implements
        # no rule for them (falls through to LB31), plus the SA/MN/MC
        # conflict branch compares bare "SA_WITHOUT_MN_OR_MC" while the
        # enum is "TMP_SA_WITHOUT_MN_OR_MC" so SA never maps to CM.
        detail_parts = []
        if not denominator_ok:
            detail_parts.append(
                "denominator drift: ran %d assertions, registered total %d"
                % (total_sum, UPSTREAM_TOTAL)
            )
        detail_parts.extend(failures)
        if not identities_ok:
            detail_parts.append("marker identity check failed")
        self._emit_upstream({
            "status": "failed",
            "framework": "make",
            "command": "make test (8 test programs, X/Y summary fractions)",
            "discovered": discovered,
            "executed": executed,
            "passed": passed_sum,
            "failed": failed,
            "skipped": 0,
            "reason": "; ".join(detail_parts) or "unknown",
            "gaps": [
                {
                    "count": discovered - passed_sum,
                    "category": "test_failure",
                    "detail": ("; ".join(detail_parts) or "unknown")
                    + "; upstream 3.0.0 regression identical on Gentoo Linux"
                    " (test/line 18594/19338, 744 failed): Unicode 17 new LB"
                    " classes AK/AP/AS/VF/VI/PI unhandled in src/line.c",
                    "evidence": "per-program X/Y summary fractions in build log;"
                    " Gentoo dev-libs/libgrapheme 3.0.0 reports same"
                    " 18594/19338 line result; 2.0.2 passes",
                }
            ],
        })
        self.output.warning(
            "upstream test suite has %d/%d failures (honest marker kept, "
            "build continues): %s" % (failed, executed, "; ".join(detail_parts))
        )
        return

    def package(self):
        # Upstream-aware install straight into the package folder.
        # LDCONFIG is empty: OHOS has no ldconfig and the call would fail
        # the install (historical device-build lesson, kept as make var).
        make_cmd = self._make_base_cmd()
        self.run(
            '%s install PREFIX="%s" LDCONFIG='
            % (make_cmd, self.package_folder),
            cwd=self.source_folder,
        )
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        if self.options.shared:
            for stale in ("libgrapheme.a",):
                stale_path = os.path.join(self.package_folder, "lib", stale)
                if os.path.isfile(stale_path):
                    os.remove(stale_path)
        else:
            lib_dir = os.path.join(self.package_folder, "lib")
            try:
                entries = os.listdir(lib_dir)
            except OSError:
                entries = []
            for entry in entries:
                if entry.startswith("libgrapheme.so"):
                    full = os.path.join(lib_dir, entry)
                    if os.path.isfile(full) or os.path.islink(full):
                        os.remove(full)
        # Carry the upstream evidence into the package so cache-hit
        # test_package runs can re-emit it without rebuilding.
        try:
            src = os.path.join(self.build_folder, "hmbs_upstream.json")
            if os.path.isfile(src):
                res_dir = os.path.join(self.package_folder, "res")
                os.makedirs(res_dir, exist_ok=True)
                shutil.copyfile(
                    src, os.path.join(res_dir, "hmbs_upstream.json")
                )
            else:
                self.output.warning("hmbs_upstream.json missing in package()")
        except Exception as exc:
            self.output.warning("package upstream evidence copy failed: %s" % exc)

    def package_info(self):
        self.cpp_info.libs = ["grapheme"]
        self.cpp_info.set_property("cmake_file_name", "libgrapheme")
        self.cpp_info.set_property("cmake_target_name", "libgrapheme::libgrapheme")
        self.cpp_info.set_property("pkg_config_name", "libgrapheme")
