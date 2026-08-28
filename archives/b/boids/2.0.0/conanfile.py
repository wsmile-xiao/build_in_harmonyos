#!/usr/bin/env python3
"""Conan recipe — boids 2.0.0

boids is a lightweight JavaScript implementation of Craig Reynolds'
flocking algorithm (https://github.com/hughsk/boids).  It is a pure Node.js
library with no native code, so this recipe downloads the official v2.0.0
source tarball, resolves its single runtime dependency (`inherits`) with
`npm install`, and packages the module for Node.js consumers.

Package layout (NODE_PATH=<prefix> -> `require('boids')` works):
  <prefix>/boids/index.js      — module entry point
  <prefix>/boids/package.json  — npm manifest for module resolution
  <prefix>/boids/LICENSE.md    — MIT license text
  <prefix>/boids/README.md     — upstream documentation
  <prefix>/boids/benchmark.js  — upstream performance benchmark script
  <prefix>/node_modules/inherits/** — bundled runtime dependency

Versioning note (R37): version 2.0.0 is the upstream npm/Git tag version.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class BoidsConan(ConanFile):
    name = "boids"
    version = "2.0.0"
    description = "Lightweight JavaScript implementation of the boids flocking algorithm"
    license = "MIT"
    homepage = "https://github.com/hughsk/boids"
    url = "https://github.com/hughsk/boids"
    topics = ("boids", "flocking", "simulation", "emergent-behavior", "nodejs")

    # Platform-independent (pure JS) package; settings kept aligned with the
    # OHOS profile (L0p requires os/compiler/build_type/arch).
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # R6: patches via conandata (none for this package)
        apply_conandata_patches(self)
        # Resolve the only runtime dependency (inherits) into node_modules/.
        # --omit=dev keeps the install minimal; --ignore-scripts prevents
        # upstream prepublish (browserify bundle) from running.
        self.run(
            "npm install --ignore-scripts --no-audit --no-fund --omit=dev",
            cwd=self.source_folder,
        )

    def package(self):
        # Module root: <prefix>/boids/ (consumers set NODE_PATH=<prefix>)
        module_root = os.path.join(self.package_folder, "boids")
        for f in ("index.js", "package.json", "LICENSE.md", "README.md", "benchmark.js"):
            copy(self, f,
                 src=self.source_folder,
                 dst=module_root)
        # Bundle the runtime dependency so consumers need no extra npm step
        copy(self, "*",
             src=os.path.join(self.source_folder, "node_modules"),
             dst=os.path.join(self.package_folder, "node_modules"))

    def package_info(self):
        # Node.js library: expose module resolution path to consumers
        self.runenv_info.prepend_path("NODE_PATH", self.package_folder)
        # No native library artifacts
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []