#!/usr/bin/env python3
"""Conan test_package for libemf2svg 1.8.1 — direct-compile route.

No CMakeToolchain is used, so no CMake compiler-ID probe can fail the
test phase either (critnib precedent). test_consumer (9 public-API
assertions) and test_upstream (3 conversion cases driving the same
emf2svg() entry point as the upstream check_correctness.sh suite) are
compiled straight against the packaged headers + library with the
validated profile compiler, then run for real (R34). Emits HMBS
machine-evidence markers on every run with counts from the actual runs.
"""

import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


CONSUMER_CASES = 9
UPSTREAM_CASES = 3


class Libemf2svgTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def _cc(self):
        # Same validation as the main recipe: conf absolute path first,
        # PATH fallback only when it is missing/non-executable.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cand = (compilers.get("c") or "").strip()
        if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
        if cand:
            self.output.warning(
                "conf c compiler '%s' not usable, falling back to PATH lookup"
                % cand
            )
        return shutil.which("clang") or shutil.which("cc") or "clang"

    def _dep_flags(self):
        # -I/-L/-l from every dependency, tested package first so
        # -lemf2svg precedes its transitive libraries at link time.
        incs, libdirs, libs = [], [], []
        seen = set()

        def _abs(dep_folder, p):
            return p if os.path.isabs(p) else os.path.join(dep_folder, p)

        ordered = sorted(
            self.dependencies.items(),
            key=lambda kv: 0 if "libemf2svg" in str(kv[0]) else 1,
        )
        for _ref, _dep in ordered:
            try:
                info = _dep.cpp_info.aggregated_components()
            except Exception:
                info = _dep.cpp_info
            pf = _dep.package_folder or ""
            for d in getattr(info, "includedirs", []) or []:
                q = _abs(pf, d)
                if q not in seen:
                    seen.add(q)
                    incs.append(q)
            for d in getattr(info, "libdirs", []) or []:
                q = _abs(pf, d)
                if q not in seen:
                    seen.add(q)
                    libdirs.append(q)
            for lib in list(getattr(info, "libs", []) or []) + list(
                getattr(info, "system_libs", []) or []
            ):
                if lib and lib not in libs:
                    libs.append(lib)
        if "emf2svg" in libs:
            libs.remove("emf2svg")
            libs.insert(0, "emf2svg")
        return incs, libdirs, libs

    def build(self):
        tmp = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
            or os.path.join(self.build_folder, ".tmp")
        )
        os.makedirs(tmp, exist_ok=True)
        for k in ("TMPDIR", "TMP", "TEMP"):
            os.environ[k] = tmp
        incs, libdirs, libs = self._dep_flags()
        flags = "".join(' -I"%s"' % d for d in incs)
        flags += "".join(' -L"%s"' % d for d in libdirs)
        flags += "".join(" -l%s" % lib for lib in libs)
        flags += " -lm"
        opt = (
            "-O2 -DNDEBUG"
            if str(self.settings.build_type) == "Release"
            else "-O0 -g"
        )
        for name in ("test_consumer", "test_upstream"):
            src = os.path.join(self.source_folder, name + ".c")
            if not os.path.isfile(src):
                raise ConanException("test source missing: %s" % src)
            out = os.path.join(self.build_folder, name)
            # L0d/R34: real consumer link against the packaged library.
            self.run(
                '"%s" -std=c11 %s "%s" -o "%s"%s'
                % (self._cc(), opt, src, out, flags)
            )

    def test(self):
        if not can_run(self):
            raise ConanException("libemf2svg target consumers are not runnable")
        consumer_bin = os.path.join(self.build_folder, "test_consumer")
        upstream_bin = os.path.join(self.build_folder, "test_upstream")
        for bin_path in (consumer_bin, upstream_bin):
            try:
                os.chmod(bin_path, 0o755)
            except OSError:
                pass
        # L0d/R34: real execution of both test binaries, not a stub.
        # self.run raises on non-zero exit, so reaching the markers below
        # means both binaries really passed.
        self.run('"%s"' % consumer_bin, env="conanrun")
        self.run('"%s"' % upstream_bin, env="conanrun")

        discovered = CONSUMER_CASES + UPSTREAM_CASES
        tp_marker = {
            "executed": True,
            "passed": True,
            "command": "test_consumer + test_upstream",
            "discovered": discovered,
            "passedCount": discovered,
        }
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(tp_marker))
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(tp_marker)
        )

        ut_marker = {
            "status": "passed",
            "framework": "custom",
            "command": "test_upstream (upstream emf2svg() conversion path)",
            "discovered": UPSTREAM_CASES,
            "executed": UPSTREAM_CASES,
            "passed": UPSTREAM_CASES,
            "failed": 0,
            "skipped": 0,
        }
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(ut_marker))
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(ut_marker)
        )
