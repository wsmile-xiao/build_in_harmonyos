#!/usr/bin/env python3
"""Conan recipe — dockerfile-language-server 0.0.24

A language server for Dockerfiles powered by NodeJS, TypeScript, and VSCode
technologies.  This is a Node.js application (not a C/C++ library), so the
build uses npm + TypeScript compiler instead of autotools/cmake.

Build process:
  1. npm install  — installs 232 npm dependencies, triggers prepublish script
  2. prepublish  — tsc -p ./src  compiles TypeScript to lib/server.js

Packaged output:
  - bin/docker-langserver  — Node.js entry point (#!/usr/bin/env node)
  - lib/server.js          — compiled LSP server
  - node_modules/          — runtime dependencies
  - package.json           — npm manifest
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class DockerfileLanguageServerConan(ConanFile):
    name = "dockerfile-language-server"
    version = "0.0.24"
    description = "A language server for Dockerfiles powered by NodeJS, TypeScript, and VSCode technologies"
    license = "MIT"
    homepage = "https://github.com/rcjsuen/dockerfile-language-server-nodejs"
    url = ""  # CI fills this

    package_type = "application"

    # Node.js is platform-independent; we still need os+arch for binary layout
    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Node.js runtime dependencies are bundled in node_modules/
        # No Conan-level C/C++ dependencies
        pass

    def layout(self):
        basic_layout(self)

    # R32: OHOS platform compatibility
    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Apply patches if any (R6: patches via apply_conandata_patches)
        apply_conandata_patches(self)
        # npm install installs dependencies and triggers prepublish (tsc -p ./src)
        # which compiles TypeScript source to lib/server.js
        self.run("npm install --ignore-scripts", cwd=self.source_folder)
        self.run("npm run prepublish", cwd=self.source_folder)

    def package(self):
        # Package the compiled application
        # bin/ — executable entry point
        copy(self, "docker-langserver", src=os.path.join(self.source_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"))
        # Make the entry point executable (source tarball has 0640)
        bin_path = os.path.join(self.package_folder, "bin", "docker-langserver")
        os.chmod(bin_path, 0o755)
        # lib/ — compiled JavaScript
        copy(self, "*", src=os.path.join(self.source_folder, "lib"),
             dst=os.path.join(self.package_folder, "lib"))
        # node_modules/ — runtime npm dependencies
        copy(self, "*", src=os.path.join(self.source_folder, "node_modules"),
             dst=os.path.join(self.package_folder, "node_modules"))
        # package.json — npm manifest (needed by node for module resolution)
        copy(self, "package.json", src=self.source_folder,
             dst=self.package_folder)

    def package_info(self):
        # Command-line tool, not a library
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
