#!/usr/bin/env python3
"""Conan recipe for GNU source-highlight 3.1.9 (HarmonyOS PC adaptation).

Builds the source-highlight CLI tools (source-highlight, chklang, check-regexp)
plus the static srchilite library, linking against the conan boost package
(boost::regex is a hard configure dependency via AX_BOOST_BASE/AX_BOOST_REGEX).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class SrcHighliteConan(ConanFile):
    name = "src-highlite"
    version = "3.1.9"
    description = "GNU source-highlight: converts source code to syntax-highlighted documents (HTML, LaTeX, etc.)"
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/src-highlite/"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("source-highlight supports Linux and OHOS")

    def requirements(self):
        # boost::regex is a hard requirement of the 3.1.9 configure (AX_BOOST_REGEX).
        # The published boost/1.85.0 binary is the hand-compiled 4-library variant
        # that ships libboost_regex.a; later versions (1.90.0.x) publish no regex.
        self.requires("boost/1.85.0", transitive_headers=True, transitive_libs=True)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def generate(self):
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        if self.settings.os == "OHOS":
            # config.guess/config.sub are taught the OHOS triplet by
            # patches/0001 (E007), so configure detects the host natively and
            # no --build/--host bypass (E007 forbid_1) is needed.
            # OHOS sysroot pthread.h does not declare pthread_setcancelstate
            # (E507 mechanism, current macro name in boost >=1.85): gate only
            # the cancellation-state calls, keeping the nanosleep path.
            tc.extra_cxxflags.append("-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE")
            # 2015-era C++ uses dynamic exception specifications (throw(X)),
            # which are hard errors under the profile's cppstd=17; appending
            # -std=c++14 after the profile's -std makes clang take this one.
            tc.extra_cxxflags.append("-std=c++14")
        # AX_BOOST_BASE honours --with-boost=<root> (expects <root>/include and
        # <root>/lib). Derive the package root from the dependency's include dir
        # instead of injecting any shared system prefix.
        boost = self.dependencies["boost"]
        boost_root = os.path.dirname(boost.cpp_info.includedirs[0])
        tc.configure_args.extend(
            [
                "--with-boost=%s" % boost_root,
                "--enable-static",
                "--disable-shared",
            ]
        )
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        if can_run(self):
            # Upstream test suite (tests/Makefile.am) is a custom `check:`
            # target: it runs the freshly built source-highlight binary over
            # the shipped language corpus and diffs against the expected
            # outputs (incl. tests/output_dir).  Scoped to the tests subtree
            # like the exploration run; the binary is statically linked so it
            # runs without extra library paths.  Non-executed subsets
            # (doc/ example generation, src/ --check-lang loop) are accounted
            # for in notes.md.
            self.run(
                "make -C tests check -j1; status=$?; "
                "if [ $status -ne 0 ]; then "
                "find tests -maxdepth 3 -type f \\( -name '*.log' -o -name '*.html' \\) "
                "-print | tail -40; fi; exit $status",
                env="conanbuild",
            )

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        # libsource-highlight (static) + boost::regex for direct linkers.
        self.cpp_info.libs = ["source-highlight"]
        self.cpp_info.resdirs = ["share", "share/source-highlight"]
        self.cpp_info.set_property("cmake_file_name", "srchilite")
        self.cpp_info.set_property("cmake_target_name", "srchilite::srchilite")
