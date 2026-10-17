#!/usr/bin/env python3
"""HarmonyOS consumer test for the packaged xwininfo executable."""

import os
import shutil

from conan import ConanFile


class XwininfoTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _find_so(self, dependency, soname_prefix):
        hits = []
        for root, _dirs, files in os.walk(dependency.package_folder):
            for filename in sorted(files):
                if filename.startswith(soname_prefix):
                    hits.append(os.path.join(root, filename))
        if not hits:
            return None
        for path in hits:
            if not os.path.islink(path):
                return path
        return hits[0]

    def _runtime_preload(self):
        # Device loader lookup can ignore LD_LIBRARY_PATH for Conan cache paths.
        # Preload the package's concrete runtime ELF files in dependency order.
        found = []
        for name, prefix in (
            ("libxau", "libXau.so.6"),
            ("libxdmcp", "libXdmcp.so.6"),
            ("libxcb", "libxcb.so.1"),
            ("libxcb", "libxcb-shape.so.0"),
            ("libx11", "libX11.so.6"),
        ):
            try:
                dependency = self.dependencies[name]
            except KeyError:
                continue
            path = self._find_so(dependency, prefix)
            if path:
                found.append(path)
        return ":".join(found)

    def test(self):
        package = self.dependencies["xwininfo"]
        binary = os.path.join(package.package_folder, "bin", "xwininfo")
        shell = (
            os.environ.get("SHELL")
            or os.environ.get("CONFIG_SHELL")
            or shutil.which("bash")
            or "/bin/sh"
        )
        script = os.path.join(self.source_folder, "test_xwininfo.sh")
        preload = self._runtime_preload()
        if preload:
            self.output.info("runtime LD_PRELOAD=%s" % preload)
        self.run(f'"{shell}" "{script}" "{binary}" "{preload}"', env="conanrun")

        self.output.info(
            'HMBS_UPSTREAM_TEST_RESULT={"status":"no_tests",'
            '"framework":"Automake/Meson",'
            '"command":"make check",'
            '"discovered":0,"executed":0,"passed":0,"failed":0,'
            '"skipped":0,'
            '"reason":"xwininfo 1.1.7 release sources define no upstream tests"}'
        )
