#!/usr/bin/env python3
"""Conan recipe — espeak-ng 1.51 (Autotools).

The 1.51 release tarball is missing internal headers and data source files.
This recipe includes the missing headers in extra_headers/ and builds only
the library and executables (not the data files).
"""
import os
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class EspeakngConan(ConanFile):
    name = "espeak-ng"
    version = "1.51"
    description = "eSpeak NG is an open source speech synthesizer that supports 100+ languages and accents"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/espeak-ng/espeak-ng"
    url = ""

    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "patches/*", "extra_headers/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        # In-tree build: espeak-ng Makefile uses relative -I paths
        self.folders.source = "."
        self.folders.build = "."

    def source(self):
        local_tarball = os.path.expanduser("~/tmp/builds/espeak-ng-1.51.tar.gz")
        try:
            get(self, **self.conan_data["sources"], strip_root=True)
        except Exception:
            if os.path.exists(local_tarball):
                from conan.tools.files import unzip
                unzip(self, local_tarball, destination=self.source_folder, strip_root=True)
            else:
                raise

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Disable speechPlayer (C++ ambiguity error with clang 15)
        tc.configure_args.append("--without-speechplayer")
        tc.configure_args.append("--without-klatt")
        tc.configure_args.append("--without-mbrola")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # Fix umask 077 -> 022 for HMDFS compatibility
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.exists(configure_path):
            import re
            with open(configure_path, 'r') as f:
                c = f.read()
            c = c.replace('umask 077', 'umask 022')
            with open(configure_path, 'w') as f:
                f.write(c)

        # Fix CONFIG_SHELL and compiler paths: profile sets non-existent paths.
        build_env = os.path.join(self.generators_folder, "conanbuild.sh")
        if os.path.exists(build_env):
            with open(build_env, "a") as f:
                f.write("\nunset CONFIG_SHELL\n")
                f.write("export SHELL=/bin/sh\n")
                # Override compiler executables (profile paths don't exist)
                clang = "/storage/Users/currentUser/.harmonybrew/bin/clang"
                clangxx = "/storage/Users/currentUser/.harmonybrew/bin/clang++"
                if os.path.exists(clang):
                    f.write(f"export CC={clang}\n")
                if os.path.exists(clangxx):
                    f.write(f"export CXX={clangxx}\n")

        # Copy missing internal headers from exported sources
        for sub, dest_sub in [
            ("extra_headers/libespeak-ng", "src/libespeak-ng"),
            ("extra_headers/speechPlayer", "src/speechPlayer/src"),
        ]:
            src_dir = os.path.join(self.source_folder, sub)
            dest_dir = os.path.join(self.source_folder, dest_sub)
            if os.path.isdir(src_dir):
                os.makedirs(dest_dir, exist_ok=True)
                for h in os.listdir(src_dir):
                    if h.endswith(".h"):
                        dest_file = os.path.join(dest_dir, h)
                        if not os.path.exists(dest_file):
                            copy(self, h, src=src_dir, dst=dest_dir)

        # Create placeholder in espeak-ng-data
        data_dir = os.path.join(self.source_folder, "espeak-ng-data")
        os.makedirs(data_dir, exist_ok=True)
        placeholder = os.path.join(data_dir, "README.txt")
        if not os.path.exists(placeholder):
            with open(placeholder, "w") as f:
                f.write("espeak-ng data files\n")

        autotools = Autotools(self)
        autotools.configure()
        # Build only library and executables (skip all-local which needs data files)
        autotools.make(target="src/libespeak-ng.la")
        autotools.make(target="src/espeak-ng")
        autotools.make(target="src/speak-ng")

    def package(self):
        autotools = Autotools(self)
        autotools.install(target="install-exec")
        autotools.install(target="install-data")
        # Copy public headers manually
        copy(self, "*.h",
             src=os.path.join(self.source_folder, "src", "include"),
             dst=os.path.join(self.package_folder, "include"))
        # Remove libtool .la files
        lib_dir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(lib_dir):
            for f in os.listdir(lib_dir):
                if f.endswith(".la"):
                    os.remove(os.path.join(lib_dir, f))

    def package_info(self):
        self.cpp_info.libs = ["espeak-ng"]
        self.cpp_info.includedirs = ["include"]
