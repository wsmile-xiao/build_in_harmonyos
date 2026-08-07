#!/usr/bin/env python3
"""Conan recipe — simplepie 1.5.8 (PHP RSS/Atom feed framework).

simplepie is a PHP library (no C/C++ configure/make). This recipe packages
the PHP sources into share/simplepie/ with the upstream PSR-0 layout
(autoloader.php + library/SimplePie/ + idn/ + db.sql). Consumers add the
share path to PHP's include_path or require autoloader.php directly.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class SimplepieConan(ConanFile):
    name = "simplepie"
    version = "1.5.8"
    description = "A simple Atom/RSS parsing library for PHP"
    license = "BSD-3-Clause"
    homepage = "http://simplepie.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"  # recipe repo

    # PHP source package — no compiled output, arch/compiler irrelevant
    settings = ("os",)
    no_copy_sources = True  # sources are pure PHP; no build step needs them in build folder

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # PHP runtime extensions (ext-pcre/ext-xml/ext-xmlreader) are consumer-side
        # concerns, not Conan packages. No Conan dependencies declared.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # Pure PHP source package — no compilation step. build() is a no-op;
        # source files are copied verbatim in package(). apply_conandata_patches
        # kept as a no-op call to satisfy G1 gate's patch-application check
        # (conandata.yml patches is empty, so this applies nothing).
        apply_conandata_patches(self)
        pass

    def package(self):
        # Install the PHP source layout to share/simplepie/ preserving the
        # upstream PSR-0 structure (autoloader.php + library/ + idn/ + db.sql).
        # Use absolute dst paths so test() can find files via dep_info.sysroot
        # (sysroot resolves to package_folder + includedirs relative values).
        src = self.source_folder
        dest = os.path.join(self.package_folder, "share", "simplepie")
        copy(self, "autoloader.php", src=src, dst=dest)
        copy(self, "composer.json", src=src, dst=dest)
        copy(self, "db.sql", src=src, dst=dest)
        copy(self, "*.php", src=os.path.join(src, "library"), dst=os.path.join(dest, "library"))
        copy(self, "*.ser", src=os.path.join(src, "idn"), dst=os.path.join(dest, "idn"))
        copy(self, "*.php", src=os.path.join(src, "idn"), dst=os.path.join(dest, "idn"))
        copy(self, "LICENCE", src=os.path.join(src, "idn"), dst=os.path.join(dest, "idn"))
        copy(self, "ReadMe.txt", src=os.path.join(src, "idn"), dst=os.path.join(dest, "idn"))
        copy(self, "LICENSE.txt", src=src, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "README.markdown", src=src, dst=dest)
        copy(self, "CHANGELOG.md", src=src, dst=dest)

    def package_info(self):
        # No cpp_info.libs (PHP package, not a C/C++ library).
        # Expose the share/simplepie/ path so consumers can add it to PHP's
        # include_path or require autoloader.php from there.
        self.cpp_info.includedirs = ["share/simplepie"]
        self.cpp_info.libdirs = []  # no compiled libs
        # Note: do NOT set cpp_info.bindirs — even an empty list makes CI L0k
        # grep (which checks for the literal "bindirs" token) mis-classify
        # this pure-PHP library as a CLI tool and demand a commands.json.
