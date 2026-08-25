#!/usr/bin/env python3
"""Conan recipe — yara 4.5.5 (pattern matching tool for malware research).

YARA is a tool for identifying and classifying malware samples by pattern
matching. It provides libyara (C library) and two CLI tools: yara and yarac.

Build system: autotools (configure.ac + Makefile.am + bootstrap.sh).
The release tarball ships NO pre-generated configure script — we ship
pre-generated autotools files in patches/autotools/ because the CI Worker
has no automake/libtoolize.

Dependencies:
  - openssl (for crypto/hash/pe modules — authenticode, hash, etc.)
  - pthread, m (system libs)

R32: Supports both Linux and OHOS platforms.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, replace_in_file, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class YaraConan(ConanFile):
    name = "yara"
    version = "4.5.5"
    description = "Pattern matching tool for malware identification and classification"
    license = "Apache-2.0"
    homepage = "https://github.com/VirusTotal/yara"
    url = ""  # CI fills this
    topics = ("yara", "malware", "security", "pattern-matching", "reverse-engineering")
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)
        # patches/autotools/ contains pre-generated autoreconf products
        # (configure, aclocal.m4, Makefile.in, m4/*.m4, build-aux/*).
        # The CI Worker has no automake/libtoolize, so build() copies
        # these into the source folder instead of invoking autoreconf.
        autotools_src = os.path.join(self.recipe_folder, "patches", "autotools")
        if os.path.isdir(autotools_src):
            autotools_dst = os.path.join(self.export_sources_folder,
                                         "patches", "autotools")
            for root, _, files in os.walk(autotools_src):
                rel = os.path.relpath(root, autotools_src)
                dst = os.path.join(autotools_dst, rel) if rel != "." else autotools_dst
                os.makedirs(dst, exist_ok=True)
                for f in files:
                    copy(self, f, root, dst)

    def requirements(self):
        self.requires("openssl/1.1.1w", transitive_headers=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][0], strip_root=True)
        # Copy pre-generated autotools files into the freshly-extracted
        # source tree RIGHT HERE in source() — before Conan caches the
        # source folder. This bakes the correct configure (with expanded
        # PKG_CHECK_MODULES, umask 022 fix) into the cached source.
        autotools_src = os.path.join(self.export_sources_folder, "patches", "autotools")
        if not os.path.isdir(autotools_src):
            autotools_src = os.path.join(self.recipe_folder, "patches", "autotools")
        if os.path.isdir(autotools_src):
            for root, _, files in os.walk(autotools_src):
                rel = os.path.relpath(root, autotools_src)
                dest = os.path.join(self.source_folder, rel) if rel != "." else self.source_folder
                os.makedirs(dest, exist_ok=True)
                for f in files:
                    shutil.copy2(os.path.join(root, f), os.path.join(dest, f))
            self.output.info("Copied pre-generated autotools files from patches/autotools/")

    def generate(self):
        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")

        # Propagate OpenSSL include/lib paths to configure via env vars
        cppflags = []
        ldflags = []
        pkgconfig_dirs = []

        for _ref, dep in self.dependencies.items():
            for inc in dep.cpp_info.includedirs:
                cppflags.append("-I{}".format(inc))
            for lib in dep.cpp_info.libdirs:
                ldflags.append("-L{}".format(lib))
                pc_dir = os.path.join(lib, "pkgconfig")
                if os.path.isdir(pc_dir):
                    pkgconfig_dirs.append(pc_dir)

        if cppflags:
            os.environ["CPPFLAGS"] = (
                " ".join(cppflags) + " " + os.environ.get("CPPFLAGS", "")
            )
        if ldflags:
            os.environ["LDFLAGS"] = (
                " ".join(ldflags) + " " + os.environ.get("LDFLAGS", "")
            )
        if pkgconfig_dirs:
            os.environ["PKG_CONFIG_PATH"] = (
                ":".join(pkgconfig_dirs) + ":" + os.environ.get("PKG_CONFIG_PATH", "")
            )

        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # The upstream release tarball ships NO pre-generated configure script
        # (only configure.ac + Makefile.am). Pre-generated autotools files were
        # copied in source() right after get() extracts the tarball.
        # Fallback for local builds with automake installed: run autoreconf.
        if not os.path.isfile(os.path.join(self.source_folder, "configure")):
            self.run("autoreconf -fi", cwd=self.source_folder)

        # E011: Fix umask 077 -> 022 in generated files (HMDFS permission issue)
        for fname in ["configure", "Makefile.in"]:
            fpath = os.path.join(self.source_folder, fname)
            if os.path.isfile(fpath):
                with open(fpath, "r") as f:
                    content = f.read()
                    if "umask 077" in content:
                        replace_in_file(self, fpath, "umask 077", "umask 022")

        # Prevent make from trying to regenerate autotools files (CI has no automake)
        os.environ["ACLOCAL"] = ":"
        os.environ["AUTOMAKE"] = ":"
        os.environ["AUTOCONF"] = ":"
        os.environ["AUTOHEADER"] = ":"
        os.environ["AUTOM4TE"] = ":"

        # Prevent flex/bison regeneration (source ships pre-generated .c files)
        os.environ["LEX"] = ":"
        os.environ["YACC"] = ":"

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.libs = ["yara"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_target_name", "yara::yara")
        self.cpp_info.set_property("pkg_config_name", "yara")
        # System libs linked by libyara
        self.cpp_info.system_libs = ["pthread", "m"]
