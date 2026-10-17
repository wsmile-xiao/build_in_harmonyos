#!/usr/bin/env python3
"""Conan test_package — libbf 2021.03.27 consumer check.

Compiles test_libbf.c against the packaged static library and runs it.
The program performs 5 real libbf API checks (add / mul / div / sqrt /
decimal atof round-trip) with TAP-style output; any failure exits non-zero.
"""
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment


class LibbfTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _reemit_upstream_result(self):
        """Re-emit the packaged upstream result verbatim (cache-hit rounds).

        build() is skipped when the binary is Already installed, so the
        HMBS_UPSTREAM_TEST_RESULT marker would be lost. The main recipe
        persists the marker JSON into share/libbf/ at package() time;
        re-emit it here unchanged every round. Missing/invalid file only
        warns, never forges a result.
        """
        try:
            dep = self.dependencies["libbf"]
            src = os.path.join(
                dep.package_folder, "share", "libbf",
                "hmbs_upstream_result.json",
            )
        except Exception as exc:
            self.output.warning("upstream result re-emit skipped: %s" % exc)
            return
        try:
            with open(src, "r", encoding="utf-8") as f:
                text = f.read().strip()
            payload = json.loads(text)
            for key in ("status", "discovered", "executed", "passed", "failed"):
                if key not in payload:
                    raise ValueError("missing key %s" % key)
            self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + text)
        except Exception as exc:
            self.output.warning(
                "packaged upstream result missing or invalid: %s" % exc
            )

    def test(self):
        # Writable temp root: /tmp is read-only on the runner. Mirror the
        # main recipe (build_folder/_tmp) so the compiler and the POSIX sh
        # test script never touch /tmp. HMBS also injects TMPDIR; our value
        # takes precedence inside this scope.
        tmpdir = os.path.join(self.build_folder, "_tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env = Environment()
        env.define_path("TMPDIR", tmpdir)
        env.define_path("TMP", tmpdir)
        env.define_path("TEMP", tmpdir)

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        raw_cc = compilers.get("c") if isinstance(compilers, dict) else None
        if raw_cc:
            raw_cc = str(raw_cc)
            probed_ok = False
            if "/" in raw_cc or "\\" in raw_cc:
                # Execution probe, not isfile: the pinned absolute path
                # looked like a file yet failed at exec (Error 127).
                try:
                    proc = subprocess.run(
                        [raw_cc, "--version"],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        timeout=20,
                    )
                    probed_ok = proc.returncode == 0
                except Exception:
                    probed_ok = False
            else:
                found_short = shutil.which(raw_cc)
                probed_ok = found_short is not None
                if probed_ok:
                    os.environ["CC"] = found_short
                    raw_cc = None
            if raw_cc:
                if probed_ok:
                    os.environ["CC"] = raw_cc
                else:
                    base = os.path.basename(raw_cc)
                    found = shutil.which(base) or shutil.which("clang")
                    if found:
                        self.output.warning(
                            "conf c '%s' not executable; using PATH '%s'"
                            % (raw_cc, found)
                        )
                        os.environ["CC"] = found
                    else:
                        # Short name: let /bin/sh resolve it at run time
                        # under the conanrun/conanbuild PATH hmbs injects.
                        self.output.warning(
                            "conf c '%s' not executable; falling back to"
                            " PATH name '%s'" % (raw_cc, base)
                        )
                        os.environ["CC"] = base
        elif not os.environ.get("CC"):
            os.environ["CC"] = shutil.which("clang") or "clang"
        dep = self.dependencies["libbf"]
        include = os.path.join(dep.package_folder, "include")
        lib = os.path.join(dep.package_folder, "lib")

        # 5 real consumer assertions live in test_libbf.c / test_libbf.sh.
        # Pure POSIX sh: no bash dependency (/bin/sh is the HMBS shell).
        discovered = 5
        passed = 0
        command = "/bin/sh test_libbf.sh"
        try:
            with env.vars(self).apply():
                self.run(
                    "%s %s %s" % (command, include, lib), env="conanrun"
                )
            passed = discovered
        except Exception as exc:
            self.output.error("test_libbf.sh failed: %s" % exc)

        tp_result = {
            "executed": True,
            "passed": passed == discovered,
            "command": command,
            "discovered": discovered,
            "passedCount": passed,
        }
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(tp_result)
        )
        self._reemit_upstream_result()

        if passed != discovered:
            raise ConanException("test_package consumer checks failed")
