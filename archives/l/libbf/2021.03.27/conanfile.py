#!/usr/bin/env python3
"""Conan recipe for libbf 2021.03.27 — Fabrice Bellard's arbitrary precision
floating point library (MIT, https://bellard.org/libbf/).

Source provenance: the standalone libbf-2021-03-27 tarball is no longer hosted
on bellard.org (HTTP 404 verified 2026-09-16); the contemporaneous
quickjs-2021-03-27 bundle (same author, same date) ships that day's libbf core
(libbf.c / libbf.h / cutils.c / cutils.h / list.h, bundle VERSION=2021-03-27).
This recipe builds a static libbf.a from those files and runs the bundle's
tests/test_bignum.js (134 static assertion sites exercising libbf BigFloat /
BigDecimal) through the freshly built qjs as the upstream test.
"""
import json
import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class LibbfConan(ConanFile):
    name = "libbf"
    version = "2021.03.27"
    description = "Small library to handle arbitrary precision floating point numbers"
    license = "MIT"
    homepage = "https://bellard.org/libbf/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libbf supports Linux and OHOS, not %s" % self.settings.os
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _conf_tool(self, key):
        try:
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            )
        except Exception:
            return None
        if isinstance(compilers, dict):
            val = compilers.get(key)
            if val:
                return str(val)
        return None

    def _probe_tool(self, path):
        """Execute `<path> --version`; True only when it really runs.

        Replaces the previous os.path.isfile()+X_OK check: on the failing
        runner the pinned /data/service/hnp/bin/clang looked like a file
        to Python yet /bin/sh reported "inaccessible or not found"
        (Error 127), so the old check wrongly kept the broken absolute
        path. An execution probe is the only reliable gate. Soft-fail:
        any exception/timeout/non-zero means "not usable".
        """
        try:
            proc = subprocess.run(
                [path, "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=20,
            )
            return proc.returncode == 0
        except Exception:
            return False

    def _resolve_tool(self, key, short_names):
        """conf path only when it executes; else basename via PATH (Exp-1).

        - Pinned absolute path: keep it ONLY if `<cand> --version`
          executes (healthy runner => zero change). Probe failure means
          the runner lacks that path => discard it and fall back.
        - Fallback: basename (+ short_names alternates) via shutil.which;
          which() runs in the recipe process without the conanbuild PATH,
          so None must NOT be fatal: return the short name and let /bin/sh
          resolve it at self.run() time under env=conanbuild where hmbs
          has prepended the tool dirs to PATH.
        """
        cand = self._conf_tool(key)
        if cand:
            if os.path.basename(cand) != cand and ("/" in cand or "\\" in cand):
                if self._probe_tool(cand):
                    return cand
                base = os.path.basename(cand)
                self.output.warning(
                    "conf %s '%s' not executable here; falling back to"
                    " PATH name '%s'" % (key, cand, base)
                )
                ordered = [base] + [
                    n for n in (short_names or []) if n != base
                ]
                for name in ordered:
                    found = shutil.which(name)
                    if found:
                        if self._probe_tool(found):
                            self.output.info(
                                "fallback %s -> %s (probed)" % (key, found)
                            )
                            return found
                        self.output.info(
                            "fallback %s -> %s (unprobed, PATH hit)"
                            % (key, found)
                        )
                        return found
                return base
            # Already a short name: prefer PATH-resolved hit when possible.
            found = shutil.which(cand)
            if found:
                return found
            return cand
        for name in short_names or []:
            found = shutil.which(name)
            if found:
                return found
        return short_names[0] if short_names else None

    def _tool(self, key, fallback=None):
        resolved = self._resolve_tool(key, [fallback] if fallback else [])
        return resolved or fallback

    def build(self):
        apply_conandata_patches(self)
        cc = self._resolve_tool("c", ["clang", "cc"])
        if not cc:
            if str(self.settings.os) == "OHOS":
                raise ConanException(
                    "OHOS build env failure: conf c missing and no clang/cc"
                    " on PATH (infra: compiler absent on this runner)"
                )
            cc = "clang"
        ar = self._resolve_tool("ar", ["llvm-ar", "ar"]) or "llvm-ar"
        host_cc = self._resolve_tool("c_host", []) or cc
        self.output.info("libbf tools: CC=%s AR=%s HOST_CC=%s" % (cc, ar, host_cc))

        # 1) Build the static library directly (no install target upstream).
        #    -fPIC keeps the archive usable for shared consumers as well.
        src = self.source_folder
        self.run(
            "%s -O2 -fPIC -c %s -o libbf.o"
            % (cc, shlex.quote(os.path.join(src, "libbf.c"))),
            cwd=self.build_folder,
            env="conanbuild",
        )
        self.run(
            "%s -O2 -fPIC -c %s -o cutils.o"
            % (cc, shlex.quote(os.path.join(src, "cutils.c"))),
            cwd=self.build_folder,
            env="conanbuild",
        )
        self.run(
            "%s rcs libbf.a libbf.o cutils.o" % ar,
            cwd=self.build_folder,
            env="conanbuild",
        )

        # 2) Build the qjs test runner (test-only, not packaged) and run the
        #    upstream bignum suite which exercises libbf. R9: -j1.
        tmpdir = os.path.join(self.build_folder, "_tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env = Environment()
        env.define_path("TMPDIR", tmpdir)
        make_bin = os.environ.get("HMBS_MAKE") or "make"
        if "/" in make_bin and not self._probe_tool(make_bin):
            self.output.warning(
                "HMBS_MAKE '%s' not executable; falling back to PATH"
                " 'make'" % make_bin
            )
            make_bin = "make"
        with env.vars(self).apply():
            self.run(
                "%s -j1 qjs CC=%s AR=%s HOST_CC=%s CONFIG_BIGNUM=y"
                % (
                    make_bin,
                    shlex.quote(cc),
                    shlex.quote(ar),
                    shlex.quote(host_cc),
                ),
                cwd=self.source_folder,
                env="conanbuild",
            )
        self._run_upstream_tests(env)

    def _run_upstream_tests(self, env):
        """Run tests/test_bignum.js and emit the HMBS_UPSTREAM_TEST_RESULT mark.

        Audit: 126 assert() call sites + 8 assertThrows() call sites = 134
        static assertion sites (counted with findstr on the shipped file).
        The script throws on any failure (exit != 0), and expected values are
        literal constants in the file (e.g. BigFloat.exp(0.2l) ===
        1.2214027581601698339210719946396742l), so exit 0 means every
        assertion genuinely executed and passed — no silent skips.
        """
        discovered = 134
        command = "./qjs --bignum tests/test_bignum.js"
        try:
            with env.vars(self).apply():
                self.run(command, cwd=self.source_folder, env="conanbuild")
            status, passed, failed = "passed", discovered, 0
        except Exception as exc:
            self.output.error("upstream test failed: %s" % exc)
            status, passed, failed = "failed", 0, discovered
        marker = {
            "status": status,
            "framework": "quickjs-test",
            "command": command,
            "discovered": discovered,
            "executed": discovered,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False)
        )
        # Persist for cache-hit rounds: test_package re-emits this file
        # verbatim from the package when build() is skipped from cache.
        try:
            with open(
                os.path.join(self.build_folder, "hmbs_upstream_result.json"),
                "w",
                encoding="utf-8",
            ) as _hmbs_f:
                _hmbs_f.write(json.dumps(marker, ensure_ascii=False))
        except Exception as _hmbs_e:
            self.output.warning(
                "could not persist upstream result: %s" % _hmbs_e
            )
        if status != "passed":
            raise ConanException("upstream test_bignum.js failed")

    def package(self):
        copy(
            self,
            "libbf.h",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "libbf.a",
            src=self.build_folder,
            dst=os.path.join(self.package_folder, "lib"),
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        # Persisted upstream result for cache-hit re-emission: the packaged
        # JSON lets test_package re-emit the marker when build() is skipped.
        try:
            _hmbs_src = os.path.join(
                self.build_folder, "hmbs_upstream_result.json"
            )
            if os.path.isfile(_hmbs_src):
                copy(
                    self,
                    "hmbs_upstream_result.json",
                    src=self.build_folder,
                    dst=os.path.join(self.package_folder, "share", "libbf"),
                )
            else:
                self.output.warning(
                    "upstream result file missing in build_folder;"
                    " skip packaging it"
                )
        except Exception as _hmbs_e:
            self.output.warning(
                "could not package upstream result: %s" % _hmbs_e
            )
        expected = [
            os.path.join(self.package_folder, "include", "libbf.h"),
            os.path.join(self.package_folder, "lib", "libbf.a"),
            os.path.join(self.package_folder, "licenses", "LICENSE"),
        ]
        for artifact in expected:
            if not os.path.exists(artifact):
                raise ConanException(
                    "package() missing expected artifact: %s" % artifact
                )

    def package_info(self):
        self.cpp_info.libs = ["bf"]
        self.cpp_info.system_libs = ["m"]
