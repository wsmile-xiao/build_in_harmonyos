#!/usr/bin/env python3
"""Conan recipe — libsigc++ 2.10.8 (Meson)

libsigc++ implements a typesafe callback system (signals and slots) for
standard C++. The 2.10.8 tarball is produced by `meson dist` and ships no
configure script, so the recipe drives the upstream meson build.
"""
import os

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibsigcConan(ConanFile):
    name = "libsigc"
    version = "2.10.8"
    description = "Typesafe callback system for standard C++ (signals and slots)"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/libsigcplusplus/libsigcplusplus"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # libsigc++ is self-contained: it links only against libc++ and libc.
        pass

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # Tarball build (not a git checkout): the generated sources under untracked/
        # are already shipped, so m4 / mm-common are not needed.
        tc.project_options["maintainer-mode"] = "false"
        # doxygen / dot / xsltproc / dblatex are absent on the HarmonyOS PC worker.
        tc.project_options["build-documentation"] = "false"
        tc.project_options["validation"] = "false"
        tc.project_options["build-pdf"] = "false"
        # Examples and the google-benchmark based benchmark are not part of the package.
        tc.project_options["build-examples"] = "false"
        tc.project_options["benchmark"] = "false"
        # docs/reference probes mm-common through dependency(); forbid meson from
        # silently fetching subprojects/mm-common.wrap (CI build stage has no network).
        tc.project_options["wrap_mode"] = "nodownload"
        tc.generate()
        self._inject_meson_archiver()

    def _inject_meson_archiver(self):
        """Write ar/ranlib full paths into the meson native file.

        MesonToolchain only maps the c/cpp entries of tools.build:compiler_executables,
        so meson probes the archiver by bare name (llvm-ar). The clang toolchain lives
        in /data/service/hnp/bin, which is not on PATH during `conan create`, and the
        probe fails. Deriving the paths from the compiler keeps PATH untouched.
        """
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        ar = executables.get("ar")
        ranlib = executables.get("ranlib")
        if not ar:
            compiler = executables.get("cpp") or executables.get("c") or ""
            bindir = os.path.dirname(compiler)
            candidate = os.path.join(bindir, "llvm-ar") if bindir else ""
            if candidate and os.path.isfile(candidate):
                ar = candidate
                candidate_ranlib = os.path.join(bindir, "llvm-ranlib")
                if os.path.isfile(candidate_ranlib):
                    ranlib = candidate_ranlib
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not ar or not os.path.isfile(native_file):
            return
        with open(native_file) as handle:
            content = handle.read()
        if "\nar =" in content or "[binaries]" not in content:
            return
        binaries = "[binaries]\nar = '%s'\n" % ar
        if ranlib:
            binaries += "ranlib = '%s'\n" % ranlib
        with open(native_file, "w") as handle:
            handle.write(content.replace("[binaries]\n", binaries, 1))

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()
        # Upstream test suite: 32 programs under tests/, built by default.
        meson.test()

    def package(self):
        Meson(self).install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["sigc-2.0"]
        # sigc++config.h is installed below libdir, not below includedir.
        self.cpp_info.includedirs = [
            os.path.join("include", "sigc++-2.0"),
            os.path.join("lib", "sigc++-2.0", "include"),
        ]
        self.cpp_info.set_property("pkg_config_name", "sigc++-2.0")
