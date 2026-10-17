#!/usr/bin/env python3
"""Conan recipe for raft-cowsql 0.22.1 — cowsql Raft consensus library (C/autotools).

raft-cowsql is an asynchronous C implementation of the Raft consensus protocol,
forked by the cowsql project (Canonical). The GitHub tarball does not include
generated autotools files; 17 patches vendor the autoreconf -i output so that
CI workers without aclocal/automake can build from source.

Build system: autotools (configure + make). No third-party dependencies
(libuv/lz4 are optional and disabled when not installed).
R32: settings.os check covers Linux and OHOS.
R33: compiler flags come from AutotoolsToolchain, not bare shell variables.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class RaftCowsqlConan(ConanFile):
    name = "raft-cowsql"
    version = "0.22.1"
    description = "Asynchronous C implementation of the Raft consensus protocol, forked by the cowsql project"
    license = "LGPL-3.0"
    homepage = "https://github.com/cowsql/raft"
    url = ""
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"raft-cowsql is supported only on Linux/OHOS, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # E011: HMDFS umask 077 → 022 (configure generates temp scripts
        # that fail with Permission denied under HMDFS cross-user 0700 dirs)
        configure = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure):
            content = open(configure).read()
            if "umask 077" in content:
                open(configure, "w").write(content.replace("umask 077", "umask 022"))
        # Fix execute permission for autotools scripts created by patches
        # (HarmonyOS patch command creates files without +x bit)
        import stat
        for script in ["configure", "ac/compile", "ac/config.guess",
                        "ac/config.sub", "ac/depcomp", "ac/install-sh",
                        "ac/ltmain.sh", "ac/missing", "ac/test-driver"]:
            script_path = os.path.join(self.source_folder, script)
            if os.path.isfile(script_path):
                mode = os.stat(script_path).st_mode
                os.chmod(script_path, mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        autotools = Autotools(self)
        autotools.configure()
        # AutotoolsToolchain creates a build-release subdirectory (VPATH build),
        # but source files use #include "../include/raft.h" (relative to src/)
        # which requires the generated header in the source include/ directory.
        # Copy generated headers from build subdirectory to source directory.
        import shutil
        for subdir in ["build-release", "build-Release"]:
            build_include = os.path.join(self.source_folder, subdir, "include")
            source_include = os.path.join(self.source_folder, "include")
            if os.path.isdir(build_include):
                for f in os.listdir(build_include):
                    src_path = os.path.join(build_include, f)
                    dst_path = os.path.join(source_include, f)
                    if os.path.isfile(src_path) and not os.path.exists(dst_path):
                        shutil.copy2(src_path, dst_path)
                break
        # Override autotools regeneration tools with 'true' so make does not
        # fail when it tries to rebuild aclocal.m4 / Makefile.in / configure.
        # (aclocal-1.16 / automake-1.16 / autoconf are not installed on
        # HarmonyOS; the vendored patches already contain the generated
        # files, so regeneration is unnecessary.)
        _no_regen = ["AUTOMAKE=true", "ACLOCAL=true",
                      "AUTOCONF=true", "AUTOHEADER=true"]
        autotools.make(args=["-j1"] + _no_regen)
        # Upstream test suite: make check
        # 3 tests: test/unit/core, test/integration/core, test/fuzzy/core
        autotools.make(target="check", args=["-j1"] + _no_regen)

    def package(self):
        autotools = Autotools(self)
        _no_regen = ["AUTOMAKE=true", "ACLOCAL=true",
                      "AUTOCONF=true", "AUTOHEADER=true"]
        autotools.install(args=["-j1"] + _no_regen)

    def package_info(self):
        self.cpp_info.libs = ["raft"]
