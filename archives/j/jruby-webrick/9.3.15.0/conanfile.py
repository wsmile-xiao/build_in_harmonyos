#!/usr/bin/env python3
"""
conanfile.py — jruby-webrick 9.3.15.0

WEBrick HTTP server toolkit (Ruby stdlib library bundled with JRuby).
Pure Ruby library — no C/C++ compilation needed.

JRuby 9.3.15.0 bundles the webrick gem v1.7.0 from the ruby/webrick repo.
The .rb files are packaged as-is into the Conan package.
"""

import os

from conan import ConanFile
from conan.tools.files import copy, get, export_conandata_patches
from conan.tools.layout import basic_layout


class JrubyWebrickConan(ConanFile):
    name = "jruby-webrick"
    version = "9.3.15.0"
    description = "JRuby WEBrick HTTP server toolkit (Ruby stdlib library bundled with JRuby)"
    license = "BSD-2-Clause"
    homepage = "https://github.com/jruby/jruby"
    url = "https://github.com/ruby/webrick"

    # Pure Ruby content package — no compiled binary
    package_type = "header-library"

    # Pure Ruby — only os/arch needed (no compiler/build_type)
    settings = "os", "arch"

    # No generators needed for a pure Ruby content package
    generators = ()

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No dependencies — WEBrick is part of Ruby stdlib
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        # Download the webrick gem v1.7.0 source (bundled with JRuby 9.3.15.0)
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        # Pure Ruby library — no compilation needed
        pass

    def package(self):
        # Copy WEBrick library files (.rb) from the webrick gem source
        webrick_src = os.path.join(self.source_folder, "lib", "webrick")
        if os.path.isdir(webrick_src):
            copy(
                self,
                "*.rb",
                webrick_src,
                os.path.join(self.package_folder, "lib", "ruby", "stdlib", "webrick"),
            )

        # Copy the main webrick.rb entry point
        main_webrick = os.path.join(self.source_folder, "lib", "webrick.rb")
        if os.path.isfile(main_webrick):
            copy(
                self,
                "webrick.rb",
                os.path.dirname(main_webrick),
                os.path.join(self.package_folder, "lib", "ruby", "stdlib"),
            )

        # Copy LICENSE if present
        copy(self, "LICENSE*", self.source_folder, os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "COPYING*", self.source_folder, os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = ["lib/ruby/stdlib"]
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
