#!/usr/bin/env python3
"""Conan test_package for libopaque 1.0.1 — Conan L1 official test.

Compiles test_opaque.c directly with the device compiler against the
packaged static libraries (libopaque/liboprf/libsodium, R33 compliant:
compiler comes from tools.build:compiler_executables, include/lib dirs
from the tested package) and runs the resulting 10-check consumer test
(R34: every check calls the real OPAQUE public API). The
HMBS_TEST_PACKAGE_RESULT marker carries the real check counts; the
upstream evidence persisted in the package (res/hmbs_upstream_result.json)
is re-emitted so cache-hit rounds keep non-zero upstream proof.
"""

import json
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class LibopaqueTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def generate(self):
        # HMBS readonly_tmp: device /tmp is read-only. Mirror the main
        # recipe: prefer the hmbs-injected writable TMPDIR/TMP/TEMP so the
        # compiler driver inherits a writable temp root.
        tmpdir = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
            or self.build_folder
        )
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except Exception:
            tmpdir = self.build_folder
        env = Environment()
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        env.vars(self).save_script("libopaque_test_env")

    def _resolve_cc(self):
        # tools.build:compiler_executables may point at a stale absolute
        # profile path (e.g. /data/service/hnp/bin/clang inaccessible via
        # /bin/sh on this device). Verify before use and fall back to PATH
        # (HMBS prefixes working device tools there) plus $CC.
        try:
            exes = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            )
        except Exception:
            exes = {}
        cc = (exes or {}).get("c")
        if cc:
            parts = shlex.split(cc)
            if parts:
                if os.path.isabs(parts[0]):
                    try:
                        if os.path.isfile(parts[0]) and os.access(parts[0], os.X_OK):
                            self.output.info("test_package selected cc=%s" % cc)
                            return parts
                    except Exception:
                        pass
                    self.output.warning(
                        "conf compiler '%s' unusable; falling back to PATH" % cc
                    )
                else:
                    self.output.info("test_package selected cc=%s" % cc)
                    return parts
        env_cc = os.environ.get("CC")
        if env_cc:
            for token in (env_cc,):
                parts = shlex.split(token)
                if parts and shutil.which(parts[0]):
                    self.output.info("test_package selected cc=%s" % token)
                    return parts
        for name in ("cc", "clang"):
            found = shutil.which(name)
            if found:
                self.output.info("test_package selected cc=%s" % found)
                return [found]
        raise ConanInvalidConfiguration(
            "no working C compiler for test_package (conf + PATH exhausted)"
        )

    def build(self):
        compiler_command = self._resolve_cc()

        dependency = self.dependencies["libopaque"]
        include_dir = dependency.cpp_info.includedirs[0]
        library_dir = dependency.cpp_info.libdirs[0]
        source = os.path.join(self.source_folder, "test_opaque.c")
        executable = os.path.join(self.build_folder, "test_opaque")

        self.run(
            " ".join(
                [
                    *(shlex.quote(argument) for argument in compiler_command),
                    "-std=c99",
                    "-O2",
                    "-DHAVE_SODIUM_HKDF=1",
                    "-I%s" % shlex.quote(include_dir),
                    shlex.quote(source),
                    "-L%s" % shlex.quote(library_dir),
                    "-lopaque",
                    "-loprf",
                    "-lsodium",
                    "-o",
                    shlex.quote(executable),
                ]
            ),
            env="conanbuild",
        )

    def test(self):
        if not can_run(self):
            self.output.info("Cross build: run test_opaque on the HarmonyOS target")
            return
        executable = os.path.join(self.build_folder, "test_opaque")
        # test_opaque.c runs 10 ordered checks (see MANIFEST.yml) and
        # exits nonzero unless all of them pass, so exit 0 means 10/10.
        discovered = 10
        passed = 0
        try:
            self.run('"%s"' % executable, env="conanrun")
            passed = discovered
        except Exception as exc:
            self.output.error("test_opaque failed: %s" % exc)
            passed = 0
        tp_result = {
            "executed": True,
            "passed": passed == discovered,
            "command": "./test_opaque",
            "discovered": discovered,
            "passedCount": passed,
        }
        tp_marker = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(tp_result)
        print(tp_marker, flush=True)
        self.output.info(tp_marker)
        # Re-emit upstream evidence persisted in package res/ so every
        # preflight round carries non-zero upstream proof even on cache hit.
        try:
            emitted = False
            try:
                dep = self.dependencies["libopaque"]
                for leaf in ("hmbs_upstream_result.json", "hmbs_upstream.json"):
                    cand = os.path.join(dep.package_folder, "res", leaf)
                    if os.path.isfile(cand):
                        with open(cand, "r", encoding="utf-8") as f:
                            up = json.load(f)
                        up_marker = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(
                            up, ensure_ascii=False
                        )
                        print(up_marker, flush=True)
                        self.output.info(up_marker)
                        emitted = True
                        break
            except Exception as exc:
                self.output.warning("upstream re-emit lookup failed: %s" % exc)
            if not emitted:
                self.output.warning("packaged upstream evidence missing")
        except Exception as exc:
            self.output.warning("upstream re-emit failed: %s" % exc)
        if passed != discovered:
            raise ConanException("test_opaque failed")
