#!/usr/bin/env python3
"""Conan recipe — shine 3.1.1 (autotools, fixed-point MP3 encoder)

Shine is a fixed-point MP3 encoding library (libshine) plus a CLI encoder
(shineenc).  The GitHub archive tarball contains no generated `configure`
(only configure.ac + Makefile.am), so build() bootstraps with autoreconf.

OHOS adaptations:
  - tool_requires automake/1.18 + libtool/2.5.4: the OHOS build host has
    only the autoconf suite; automake/aclocal/libtoolize are pulled in as
    build-time tools (same approach as argp-standalone).
  - explicit --build/--host triplet (aarch64-unknown-linux-ohos): the
    generated config.guess cannot identify HarmonyOS (E007); config.sub
    supports *-linux-ohos natively (same approach as argp-standalone).
  - E114: HMDFS turns the `umask 077 && mktemp -d` temp dir created by
    configure/config.status into drwx--S--- which is not writable; the
    generated configure is post-processed to use umask 022 instead.
"""
from conan import ConanFile
from conan.tools.files import apply_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ShineConan(ConanFile):
    name = "shine"
    version = "3.1.1"
    description = "Fast fixed-point MP3 encoding library and shineenc CLI encoder"
    license = "LGPL-2.0-only"
    homepage = "https://github.com/toots/shine"
    url = "https://github.com/toots/shine"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        pass

    def requirements(self):
        pass

    def build_requirements(self):
        # Only configure.ac ships in the archive: autoreconf is required.
        # The OHOS build host has no automake/libtool, so provide them as
        # tool_requires (resolved with the build profile).
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        # In-source build: Makefile.am uses source-relative include paths
        # (-Isrc/lib); any out-of-source build folder breaks them.
        self.folders.source = "."
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # E007: config.guess cannot detect HarmonyOS; config.sub natively
        # supports *-linux-ohos, so pin the triplet (like argp-standalone).
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        import glob
        import os
        autotools = Autotools(self)
        # GitHub archive tarballs never ship `configure`; bootstrap it.
        if not os.path.isfile(os.path.join(self.source_folder, "configure")):
            self.output.info("No configure in source tree, running autoreconf")
            self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        # E114: HMDFS cannot honor umask 077 for configure's mktemp dir
        # (drwx--S--- is not writable); switch it to umask 022.
        for _cfg in glob.glob(os.path.join(self.source_folder, "**", "configure"), recursive=True):
            try:
                with open(_cfg, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            if "umask 077" in text:
                with open(_cfg, "w", encoding="utf-8") as f:
                    f.write(text.replace("umask 077", "umask 022"))
                self.output.info(f"Patched umask in {_cfg}")
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["shine"]
        self.cpp_info.bindirs = ["bin"]  # shineenc CLI (R38: commands.json)
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("pkg_config_name", "shine")
