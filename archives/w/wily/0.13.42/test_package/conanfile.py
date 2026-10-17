#!/usr/bin/env python3
"""Consumer startup/load test for packaged wily 0.13.42.

wily calls xtbinit() before parsing its own arguments, so invoking --help or
--version would still require an X server.  The test runs the real packaged
binary against a deliberately invalid DISPLAY and requires the expected X
connection failure.  This validates loading and Xt startup without claiming a
GUI functional test.
"""

import json
import os
import shutil

from conan import ConanFile


class WilyTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "test_wily.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _find_so(self, dependency, prefix):
        candidates = []
        for root, _directories, files in os.walk(dependency.package_folder):
            for name in sorted(files):
                if name.startswith(prefix):
                    candidates.append(os.path.join(root, name))
        if not candidates:
            return None
        for candidate in candidates:
            if not os.path.islink(candidate):
                return candidate
        return candidates[0]

    def _runtime_preload(self):
        ordered = (
            ("libice", "libICE.so.6"),
            ("libsm", "libSM.so.6"),
            ("libxau", "libXau.so.6"),
            ("libxdmcp", "libXdmcp.so.6"),
            ("libxcb", "libxcb.so.1"),
            ("libx11", "libX11.so.6"),
            ("libxt", "libXt.so.6"),
        )
        paths = []
        for name, soname in ordered:
            try:
                dependency = self.dependencies[name]
            except KeyError:
                continue
            library = self._find_so(dependency, soname)
            if library:
                paths.append(library)
        return os.pathsep.join(paths)

    def test(self):
        dependency = self.dependencies["wily"]
        binary = os.path.join(dependency.package_folder, "bin", "wily")
        script = os.path.join(self.source_folder, "test_wily.sh")
        shell = (
            os.environ.get("SHELL")
            or os.environ.get("CONFIG_SHELL")
            or shutil.which("sh")
            or "/bin/sh"
        )
        preload = self._runtime_preload()
        if preload:
            self.output.info(f"runtime LD_PRELOAD={preload}")
        self.run(
            f'"{shell}" "{script}" "{binary}" "{preload}"',
            env="conanrun",
        )

        upstream = {
            "status": "no_tests",
            "framework": "none",
            "command": "",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": (
                "wily 0.13.42 has no automated upstream test suite: no "
                "TESTS/check target, no test harness, and its test-named files "
                "are interactive demos."
            ),
        }
        print(f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(upstream)}")
