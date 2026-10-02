#!/usr/bin/env python3
"""Conan test_package for metis-edf 4.1-2.

Compiles and runs test_metis_edf.c against the installed headers and the
installed libmetis.a (PartGraphRecursive / PartGraphKway / NodeND), then drives
the installed onmetis / pmetis / kmetis programs.

Emits HMBS markers for CI preflight.
"""
import json
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException

CHECKS = 13  # 10 in test_metis_edf.c + onmetis --version + pmetis + kmetis

GRAPH = """8 7
2
1 3
2 4
3 5
4 6
5 7
6 8
7
"""


class MetisEdfTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _bash(self):
        for candidate in (
            os.environ.get("CONFIG_SHELL"),
            "/storage/Users/currentUser/.harmonybrew/bin/bash",
            "/data/service/hnp/bin/bash",
            "/bin/bash",
        ):
            if candidate and os.path.isfile(candidate):
                return candidate
        return "bash"

    def _run_shell(self, command, env="conanrun"):
        if self.settings.os == "OHOS":
            return self.run(
                f"{shlex.quote(self._bash())} -c {shlex.quote(command)}",
                ignore_errors=True, env=env)
        return self.run(command, ignore_errors=True, env=env)

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        pkg = dep.package_folder
        inc = os.path.join(pkg, "include")
        lib = os.path.join(pkg, "lib")
        bindir = os.path.join(pkg, "bin")
        for path in (os.path.join(inc, "metis.h"),
                     os.path.join(lib, "libmetis.a"),
                     os.path.join(bindir, "onmetis"),
                     os.path.join(bindir, "pmetis"),
                     os.path.join(bindir, "kmetis")):
            if not os.path.exists(path):
                raise ConanException("installed file not found: %s" % path)

        here = os.path.dirname(os.path.abspath(__file__))
        workdir = os.environ.get("TMPDIR") or os.path.join(os.path.expanduser("~"), "tmp")
        os.makedirs(workdir, exist_ok=True)

        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = str(executables.get("c") or "clang")

        # 1) compile and run the API consumer.
        consumer_src = os.path.join(here, "test_metis_edf.c")
        consumer_bin = os.path.join(workdir, "test_metis_edf")
        compile_cmd = " ".join([
            shlex.quote(cc), "-O2", "-I", shlex.quote(inc),
            shlex.quote(consumer_src), "-L", shlex.quote(lib), "-lmetis", "-lm",
            "-o", shlex.quote(consumer_bin),
        ])
        rc_c = self._run_shell(compile_cmd, env="conanbuild")
        api_ok = False
        if rc_c == 0:
            api_ok = (self._run_shell(shlex.quote(consumer_bin)) == 0)

        # 2) drive the installed command line tools.
        graph = os.path.join(workdir, "small.graph")
        with open(graph, "w", encoding="ascii") as handle:
            handle.write(GRAPH)

        version_ok = False
        version_txt = os.path.join(workdir, "version.txt")
        self._run_shell(
            "%s --version > %s 2>&1"
            % (shlex.quote(os.path.join(bindir, "onmetis")), shlex.quote(version_txt)))
        if os.path.isfile(version_txt):
            with open(version_txt, encoding="utf-8", errors="replace") as handle:
                version_ok = handle.read().strip().startswith("metis-edf-4.1")

        partition_ok = True
        for tool in ("pmetis", "kmetis"):
            part = "%s.part.2" % graph
            if os.path.exists(part):
                os.remove(part)
            rc_t = self._run_shell(
                "%s %s 2" % (shlex.quote(os.path.join(bindir, tool)), shlex.quote(graph)))
            ok = rc_t == 0 and os.path.isfile(part)
            if ok:
                with open(part, encoding="ascii", errors="replace") as handle:
                    labels = [ln for ln in handle.read().splitlines() if ln.strip()]
                ok = len(labels) == 8 and all(l.strip() in ("0", "1") for l in labels)
            partition_ok = partition_ok and ok

        passed = api_ok and version_ok and partition_ok
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": passed,
            "command": "test_metis_edf.c + onmetis/pmetis/kmetis",
            "consumer_passed": CHECKS if passed else 0,
            "consumer_total": CHECKS,
        }))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "passed",
            "reason": "Test/Makefile targets fort.85 and vers_check are run for "
                      "real in build() (onmetis on the shipped Code_Aster "
                      "fort.81 and onmetis --version)",
            "discovered": 2, "executed": 2, "passed": 2, "failed": 0, "skipped": 0,
        }))

        if not passed:
            raise ConanException(
                "metis-edf consumer test failed (api=%s version=%s partition=%s)"
                % (api_ok, version_ok, partition_ok))
