#!/usr/bin/env python3
"""Conan recipe for esniper 2.35.0 — Autotools project (configure + make).

esniper is a command-line auction sniper tool for eBay.
It depends on libcurl and builds a single bin_PROGRAMS binary.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, save
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class EsniperConan(ConanFile):
    name = "esniper"
    version = "2.35.0"
    description = "esniper is a lightweight console-based tool for sniping eBay auctions"
    license = "BSD-2-Clause"
    homepage = "https://sourceforge.net/projects/esniper/"
    url = "https://sourceforge.net/projects/esniper/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("curl/8.15.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)

        # The curl-config script shipped with the curl dependency package has
        # a hardcoded prefix pointing to the build folder, not the installed
        # package folder, so the -L path it returns does not exist.
        # Create a wrapper script that returns the correct package paths.
        dep = self.dependencies["curl"]  # curl dependency
        curl_pkg_folder = dep.package_folder
        wrapper_path = os.path.join(self.generators_folder, "curl-config-wrapper")
        wrapper_content = f"""#!/bin/sh
# Wrapper around curl-config that fixes the prefix to point to the
# actual Conan package folder rather than the stale build folder.
REAL_CURL_CONFIG="{curl_pkg_folder}/bin/curl-config"
REAL_PREFIX="{curl_pkg_folder}"
output=$("$REAL_CURL_CONFIG" "$@" 2>/dev/null)
# The build prefix is baked into the script; replace it with the real prefix
BUILD_PREFIX=$(grep '^prefix=' "$REAL_CURL_CONFIG" | head -1 | sed "s/prefix=//; s/'//g")
echo "$output" | sed "s|$BUILD_PREFIX|$REAL_PREFIX|g"
"""
        save(self, wrapper_path, wrapper_content)
        os.chmod(wrapper_path, 0o755)

        tc.configure_args.append(f"--with-curl-config={wrapper_path}")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
