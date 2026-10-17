#!/usr/bin/env python3
"""Conan recipe for jenkins-debian-glue 0.23.6.

jenkins-debian-glue is a collection of shell/ruby helper scripts for
building Debian packages from Jenkins CI (by Michael Prokop). It has
no compiled code: the build is a pure install of scripts/* and tap/*
into bin/, plus examples/ and pbuilder-hookdir/ data files.

OHOS adaptation (see patches/0001-ohos-portability.patch):
  1. Shebangs `#!/bin/bash` -> `#!/usr/bin/env bash` (OHOS has no
     /bin/bash; bash is resolved through PATH).
  2. tap/* helper scripts: `file -Pbytes=32 -b -i` -> `file -b` and
     mimetype match `/x-shellscript/i` -> `/script/i` (the OHOS
     file(1) implementation supports neither -Pbytes nor -i; the
     `/script/i` match is behaviour-equivalent on both Debian and
     OHOS, so the upstream tests keep their semantics).
"""
import os
import shutil
import stat

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class JenkinsDebianGlueConan(ConanFile):
    name = "jenkins-debian-glue"
    version = "0.23.6"
    description = "Continuous Integration for Debian packages made easy (Jenkins glue scripts)"
    license = "MIT"
    homepage = "https://github.com/mika/jenkins-debian-glue"
    url = "https://github.com/mika/jenkins-debian-glue"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        self.output.info("No compilation needed: shell/ruby script tool")

    def _install_executables(self, src_subdir, bindir):
        src_dir = os.path.join(self.source_folder, src_subdir)
        if not os.path.isdir(src_dir):
            raise ConanException(f"source directory missing: {src_dir}")
        entries = sorted(
            e for e in os.listdir(src_dir)
            if os.path.isfile(os.path.join(src_dir, e))
        )
        if not entries:
            raise ConanException(f"no executables found in {src_dir}")
        for entry in entries:
            dest = os.path.join(bindir, entry)
            shutil.copy2(os.path.join(src_dir, entry), dest)
            os.chmod(dest, os.stat(dest).st_mode
                     | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        return entries

    def _install_data(self, src_subdir, datadir):
        src_dir = os.path.join(self.source_folder, src_subdir)
        if not os.path.isdir(src_dir):
            raise ConanException(f"source directory missing: {src_dir}")
        os.makedirs(datadir, exist_ok=True)
        for entry in sorted(os.listdir(src_dir)):
            shutil.copy2(os.path.join(src_dir, entry),
                         os.path.join(datadir, entry))

    def package(self):
        pkg = self.package_folder
        bindir = os.path.join(pkg, "bin")
        os.makedirs(bindir, exist_ok=True)

        # Makefile install semantics: scripts/* + tap/* -> $(PREFIX)/bin
        self._install_executables("scripts", bindir)
        self._install_executables("tap", bindir)

        # examples/ + pbuilder-hookdir/ -> share/jenkins-debian-glue/
        share = os.path.join(pkg, "share", "jenkins-debian-glue")
        self._install_data("examples", os.path.join(share, "examples"))
        self._install_data("pbuilder-hookdir",
                           os.path.join(share, "pbuilder-hookdir"))

        license_file = os.path.join(self.source_folder, "LICENSE")
        if os.path.isfile(license_file):
            licdir = os.path.join(pkg, "licenses")
            os.makedirs(licdir, exist_ok=True)
            shutil.copy2(license_file, os.path.join(licdir, "LICENSE"))

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
