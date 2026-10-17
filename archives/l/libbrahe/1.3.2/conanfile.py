#!/usr/bin/env python3
"""Conan recipe for libbrahe — a heterogenous C library of numeric functions."""
import io
import json
import os
import re

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rm, rmdir
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

# "value = A (should be B)" comparison lines printed by the upstream test programs.
_COMPARISON = re.compile(r"=\s*(-?[\d.]+)\s*\(should be\s+(-?[\d.]+)\)")
_SELF_CHECK = re.compile(r"found (\d+) error\(s\)", re.I)


class LibbraheConan(ConanFile):
    name = "libbrahe"
    version = "1.3.2"
    description = ("Heterogenous collection of numeric tools written in Standard C: "
                   "PRNGs (Mersenne Twister, KISS, CMWC4096, MWC1038, ISAAC), hyperbolic "
                   "trigonometry, rounding and significant digits, GCF/LCM, array "
                   "statistics, moving average, simple FFT, sinusoid synthesis and "
                   "integer pretty-printing")
    license = "BSD-2-Clause"
    homepage = ("https://web.archive.org/web/20191102085924/"
                "http://coyotegulch.scottrobertladd.net/products/brahe/index.html")
    url = ""
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("libbrahe is adapted for Linux/OHOS only")
        if self.settings.os == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def requirements(self):
        # Upstream needs nothing beyond libc and libm: see src/*.c includes
        # (stdlib/stdio/string/stddef/math/limits/unistd/fcntl/time/stdbool/stdint).
        pass

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
        # Doxygen API docs are opt-in upstream and need the doxygen tool; the
        # library build does not depend on them.
        tc.configure_args.append("--disable-docgen")
        tc.generate()
        # E386: the OHOS profile exports the hnp bash as CONFIG_SHELL/SHELL, and that
        # binary cannot resolve getcwd() inside HMDFS build trees, which makes the
        # libtool install step lose its own path ("bash: /libtool: No such file").
        # /bin/sh is the capability-tested shell (its `pwd` returns 0 with no
        # diagnostics from the real build directory); reassert it after conanbuild.
        env = Environment()
        env.define("CONFIG_SHELL", "/bin/sh")
        env.define("SHELL", "/bin/sh")
        env.vars(self).save_script("libbrahe_shell")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j2"])
        self._run_upstream_tests()

    # ------------------------------------------------------------------ tests

    def _upstream_test_inventory(self):
        """Programs registered by upstream test/Makefile.am (bin_PROGRAMS).

        Read from the source instead of being hardcoded, so the reported
        denominator is the upstream list itself.
        """
        path = os.path.join(self.source_folder, "test", "Makefile.am")
        with open(path, encoding="utf-8", errors="replace") as handle:
            text = handle.read()
        text = re.sub(r"\\\n\s*", " ", text)
        match = re.search(r"^bin_PROGRAMS\s*=\s*(.+)$", text, re.M)
        if not match:
            raise ConanException("upstream test inventory not found in test/Makefile.am")
        return match.group(1).split()

    def _verdict_from_output(self, text):
        """Return (ok, reason) derived from what the program itself printed.

        Three of the six upstream programs (prng/trig/pretty) contain no
        assertion and print no verdict line, so for those the observable
        evidence is a non-empty table plus a zero exit status; that has to be
        reported as such rather than dressed up as a passing assertion suite.
        """
        if not text.strip():
            return False, "program produced no output"
        compared = _COMPARISON.findall(text)
        mismatched = [(got, want) for got, want in compared if got != want]
        if mismatched:
            got, want = mismatched[0]
            return False, ("%d/%d printed comparisons disagree, e.g. %s vs %s"
                           % (len(mismatched), len(compared), got, want))
        self_check = _SELF_CHECK.search(text)
        if self_check and int(self_check.group(1)) != 0:
            return False, "upstream self-check reported %s errors" % self_check.group(1)
        if re.search(r"\bERROR\b|wrong data", text):
            return False, "upstream program printed an error verdict"
        lines = len([ln for ln in text.splitlines() if ln.strip()])
        if compared:
            return True, "%d printed comparisons, 0 mismatch" % len(compared)
        if self_check:
            return True, "self-check reports 0 errors (%d output lines)" % lines
        if "success" in text.lower():
            return True, "program prints its own success verdict (%d output lines)" % lines
        return True, ("exit 0 with %d output lines; this upstream program has no "
                      "assertion and prints tables only" % lines)

    def _run_upstream_tests(self):
        names = self._upstream_test_inventory()
        libdir = os.path.join(self.build_folder, "src", ".libs")
        executed = passed = failed = 0
        reasons = []
        evidence = []
        for name in names:
            program = os.path.join(self.build_folder, "test", name)
            command = 'LD_LIBRARY_PATH="%s" "%s"' % (libdir, program)
            self.output.info("upstream test command: %s" % command)
            stream = io.StringIO()
            try:
                self.run(command, cwd=self.build_folder, stdout=stream, stderr=stream)
            except ConanException as error:
                failed += 1
                reasons.append("%s: exit != 0 (%s)" % (name, str(error).splitlines()[0][:120]))
                continue
            executed += 1
            output = stream.getvalue()
            for line in output.splitlines():
                if "should be" in line or "error" in line.lower() or "success" in line.lower():
                    self.output.info("  | %s" % line)
            ok, reason = self._verdict_from_output(output)
            evidence.append("%s: %s" % (name, reason))
            if ok:
                passed += 1
            else:
                failed += 1
                reasons.append("%s: %s" % (name, reason))
            self.output.info("upstream test %s: %s" % (name, reason))
        status = "passed" if (names and failed == 0 and passed == len(names)) else "failed"
        marker = {
            "status": status,
            "framework": "autotools",
            "command": " && ".join(
                'LD_LIBRARY_PATH="src/.libs" ./test/%s' % n for n in names),
            "discovered": len(names),
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
            "evidence": "; ".join(evidence)[:700],
        }
        if reasons:
            marker["reason"] = "; ".join(reasons)[:400]
        print("HMBS_UPSTREAM_TEST_RESULT=%s" % json.dumps(marker, separators=(",", ":")))
        if status != "passed":
            raise ConanException("upstream test suite did not pass: %s"
                                 % marker.get("reason", marker["evidence"]))

    # ---------------------------------------------------------------- package

    def package(self):
        autotools = Autotools(self)
        # SUBDIRS=src: the six programs in test/ are upstream's own console
        # comparisons, not deliverables. They are built and executed by build()
        # above and deliberately not packaged, so this stays a library package
        # (no bin/, hence no commands.json per R38).
        autotools.install(args=["SUBDIRS=src"])
        copy(self, "LicenseOpenSource.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "LicenseClosedSource.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        # Upstream libtool names the shared object libbrahe-1.3.so.<v> (the
        # 2011 build passes -release 1.3) and keeps libbrahe.so / libbrahe.a as
        # the development names, so consumers link -lbrahe.
        self.cpp_info.libs = ["brahe"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.includedirs = ["include", os.path.join("include", "libbrahe")]
        self.cpp_info.set_property("pkg_config_name", "libbrahe")
