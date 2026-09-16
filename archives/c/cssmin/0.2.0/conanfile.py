#!/usr/bin/env python3
"""Conan recipe — cssmin 0.2.0 (pure Python CSS minifier)."""

import os
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class CssminConan(ConanFile):
    name = "cssmin"
    version = "0.2.0"
    description = "A Python port of the YUI CSS compression algorithm (pure Python)"
    license = "MIT"
    homepage = "https://github.com/zacharyvoase/cssmin"
    url = "https://github.com/zacharyvoase/cssmin"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "conandata.yml"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "cssmin %s only supports Linux and OHOS, got os=%s" % (self.version, self.settings.os)
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _py_ver(self):
        return "python%d.%d" % (sys.version_info.major, sys.version_info.minor)

    def build(self):
        apply_conandata_patches(self)
        src_mod = os.path.join(self.source_folder, "src", "cssmin.py")
        if not os.path.isfile(src_mod):
            raise ConanException("cssmin source module missing: %s" % src_mod)
        self.run("%s -m py_compile \"%s\"" % (sys.executable, src_mod))
        self.output.info("cssmin upstream: no test suite in sdist (audited, see test_package/MANIFEST.yml)")

    def package(self):
        src_mod = os.path.join(self.source_folder, "src", "cssmin.py")
        if not os.path.isfile(src_mod):
            raise ConanException("cssmin source module missing: %s" % src_mod)
        site = os.path.join(self.package_folder, "lib", self._py_ver(), "site-packages")
        os.makedirs(site, exist_ok=True)
        shutil.copyfile(src_mod, os.path.join(site, "cssmin.py"))
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        site = os.path.join(self.package_folder, "lib", self._py_ver(), "site-packages")
        self.output.info("PYTHONPATH += %s" % site)
        self.env_info.PYTHONPATH.append(site)
