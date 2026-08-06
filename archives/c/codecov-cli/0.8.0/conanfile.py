#!/usr/bin/env python3
"""Conan recipe for codecov-cli 0.8.0 — Node.js/TypeScript CLI tool.

Build system: npm + tsc (TypeScript compiler)
Package type: application (CLI tool with shell wrapper)

The codecov-cli (a.k.a. codecov uploader) is a Node.js/TypeScript project
that compiles TypeScript source into JavaScript (dist/), bundles runtime
node_modules, and installs a shell wrapper script as the entry point.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy


class CodecovCliConan(ConanFile):
    name = "codecov-cli"
    version = "0.8.0"
    description = "Command-line uploader for Codecov code coverage reporting service"
    license = "MIT"
    homepage = "https://github.com/codecov/codecov-cli"

    package_type = "application"

    # R32: Only os and arch needed for Node.js project (no C/C++ compiler)
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        # In-source build: build folder = source folder
        self.folders.source = "."
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # npm install with --ignore-scripts (skip husky/prepare hooks)
        # Use self.source_folder as cwd since build folder == source folder
        self.run("npm install --ignore-scripts", cwd=self.source_folder)
        # Build TypeScript → JavaScript
        self.run("npm run build", cwd=self.source_folder)
        # Prune dev dependencies (keep only runtime deps)
        self.run("npm prune --omit=dev", cwd=self.source_folder)

    def package(self):
        src = self.source_folder
        # Copy compiled dist/
        copy(self, "*", src=os.path.join(src, "dist"),
             dst=os.path.join(self.package_folder, "share", "codecov-cli", "dist"))
        # Copy runtime node_modules/
        copy(self, "*", src=os.path.join(src, "node_modules"),
             dst=os.path.join(self.package_folder, "share", "codecov-cli", "node_modules"))
        # Copy package.json (needed for module resolution)
        copy(self, "package.json", src=src,
             dst=os.path.join(self.package_folder, "share", "codecov-cli"))
        # Create shell wrapper script
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        wrapper_path = os.path.join(bin_dir, "codecov")
        wrapper_content = (
            "#!/bin/sh\n"
            "# codecov wrapper script for HarmonyOS\n"
            'CODECOV_HOME="${CODECOV_HOME:-$(dirname "$(dirname "$0")")/share/codecov-cli}"\n'
            'NODE_PATH="$CODECOV_HOME/node_modules" \\\n'
            '  exec node "$CODECOV_HOME/dist/bin/codecov.js" "$@"\n'
        )
        with open(wrapper_path, "w") as f:
            f.write(wrapper_content)
        os.chmod(wrapper_path, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
