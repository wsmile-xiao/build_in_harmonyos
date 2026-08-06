#!/usr/bin/env python3
"""Conan test_package for esbuild 0.25.12

Tests:
1. L1: Run esbuild --version to verify the binary works
2. L1: Bundle a simple JavaScript file to verify functionality
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class EsbuildTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualBuildEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def generate(self):
        pass

    def build(self):
        pass

    def test(self):
        # Find the esbuild binary from the package's bindirs
        esbuild = None
        dep = self.dependencies.get("esbuild")
        if dep:
            for bindir in dep.cpp_info.bindirs:
                candidate = os.path.join(bindir, "esbuild")
                if os.path.exists(candidate):
                    esbuild = candidate
                    break

        if esbuild:
            self.run(f'"{esbuild}" --version')
        else:
            # Try using the binary from PATH (conan runenv)
            self.run("esbuild --version", env=["conanrun"])

        # Test bundling: create a simple JS file and bundle it
        test_js = os.path.join(self.build_folder, "test.js")
        with open(test_js, "w") as f:
            f.write("const x = 42; console.log(x);\n")

        out_js = os.path.join(self.build_folder, "out.js")
        if esbuild:
            self.run(f'"{esbuild}" "{test_js}" --bundle --outfile="{out_js}"')
        else:
            self.run(f'esbuild "{test_js}" --bundle --outfile="{out_js}"', env=["conanrun"])

        # Verify output exists
        if not os.path.exists(out_js):
            raise Exception("esbuild did not produce output file")
