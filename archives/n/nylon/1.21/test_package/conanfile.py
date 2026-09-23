#!/usr/bin/env python3
"""Test package — nylon 1.21 (OHOS PC arm64)."""
import os, subprocess
from conan import ConanFile
from conan.tools.build import cross_building


class TestNylon(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Build the consumer test source.
        test_src = os.path.join(os.path.dirname(__file__), "test_nylon.c")
        if os.path.exists(test_src):
            out_path = os.path.join(self.build_folder, "test_nylon")
            self.run("clang -o '%s' '%s'" % (out_path, test_src))

    def _nylon_binary(self):
        # The installed nylon binary lives in the requires's package_folder/bin.
        dep = self.dependencies[self.tested_reference_str]
        return os.path.join(dep.package_folder, "bin", "nylon")

    def test(self):
        bin_path = self._nylon_binary()
        if not os.path.exists(bin_path):
            # Fallback: search bindirs (may be empty for application type).
            bindir = self.cpp.build.bindirs[0] if self.cpp.build.bindirs else None
            if bindir:
                bin_path = os.path.join(bindir, "nylon")
        assert os.path.exists(bin_path), \
            "nylon binary not found at %s" % bin_path

        if cross_building(self):
            # Cross-build: existence is enough.
            return

        # Native: run --help to verify the binary launches.
        r = subprocess.run([bin_path, "-h"], capture_output=True, text=True)
        output = r.stdout + r.stderr
        assert "nylon" in output.lower() or r.returncode in (0, 1), \
            "nylon binary failed to run: %s" % output

        # Run the consumer test binary (built by build() above).
        test_bin = os.path.join(self.build_folder, "test_nylon")
        if os.path.exists(test_bin):
            self.run(test_bin)
