#!/usr/bin/env python3
"""Conan recipe for juman 7.0 — Japanese morphological analysis system.

juman (Kyoto University) ships a C library (`libjuman`), the `juman` command and
the dictionary conversion tools (`makeint`/`makemat`/`makepat`, installed under
libexec).  It builds with autotools plus libtool and the release tarball already
contains a generated `configure`, so no autoreconf is involved.

Two portability patches are applied (see `patches/`): the bundled 2009
`config.sub` predates aarch64 and does not know the ohos OS, and the generated
`configure` creates its config.status scratch directory with `umask 077`, which
HMDFS turns into an unusable directory (E129/E011).
"""
import os

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class JumanConan(ConanFile):
    name = "juman"
    version = "7.0"
    package_type = "library"
    description = ("Japanese morphological analysis system: libjuman, the juman "
                   "command and its dictionaries")
    license = "BSD-3-Clause"
    homepage = "https://nlp.ist.i.kyoto-u.ac.jp/EN/index.php?JUMAN"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        # The autotools tree builds in source (config.h and the Makefiles are
        # produced next to the sources).
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # 2012-era code defines the same globals (CurPath/JumanPath) in both
        # makeint.c and lib/grammar.c as tentative definitions; clang defaults
        # to -fno-common, which turns those into duplicate-symbol link errors
        # (knowledge E491/E163). -fcommon restores the merging behaviour the
        # upstream build relies on (same handling as ant-phone/0.2.1).
        tc.extra_cflags.append("-fcommon")
        if self.settings.os == "OHOS":
            # AutotoolsToolchain does not inject OHOS triplets for this profile
            # and the bundled config.guess cannot derive one (E007); the triplet
            # is declared explicitly and config.sub is patched to accept it.
            tc.configure_args.extend([
                "--build=aarch64-linux-ohos",
                "--host=aarch64-linux-ohos",
            ])
        tc.generate()
        AutotoolsDeps(self).generate()
        VirtualBuildEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        # HMDFS: libtool computes relative paths from `cd $dir && pwd`, which
        # fails when getcwd() cannot resolve the build directory (E114/E386).
        os.environ["PWD"] = self.build_folder
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        self._audit_upstream_tests()

    def _audit_upstream_tests(self):
        # juman ships no test suite: no Automake TESTS/check_PROGRAMS is
        # registered anywhere in the tree.
        self.run("grep -nE 'check_PROGRAMS|^TESTS|check-local|^check:' "
                 "Makefile.in lib/Makefile.in juman/Makefile.in dic/Makefile.in || true")
        self.run("find . -maxdepth 2 -iname '*test*' | head || true")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["juman"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "juman")
        self.cpp_info.set_property("cmake_target_name", "juman::juman")
