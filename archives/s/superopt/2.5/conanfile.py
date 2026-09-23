import os
import shutil

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"

# upstream Makefile builds one binary per target CPU macro
MACHINES = [
    ("superopt-sparc", "SPARC"),
    ("superopt-power", "POWER"),
    ("superopt-powerpc", "POWERPC"),
    ("superopt-m88000", "M88000"),
    ("superopt-am29k", "AM29K"),
    ("superopt-mc68000", "MC68000"),
    ("superopt-mc68020", "MC68020"),
    ("superopt-i386", "I386"),
    ("superopt-i960a", "I960"),
    ("superopt-i960b", "I960B"),
    ("superopt-pyr", "PYR"),
    ("superopt-alpha", "ALPHA"),
    ("superopt-sh", "SH"),
    ("superopt-hppa", "HPPA"),
]


class SuperoptConan(ConanFile):
    name = "superopt"
    version = "2.5"
    description = ("GNU superoptimizer - finds the shortest instruction "
                   "sequence for a given function on a target CPU")
    license = "GPL-1.0-or-later"
    homepage = "https://www.gnu.org/software/superopt/"
    url = "https://ftp.gnu.org/gnu/superopt/superopt-2.5.tar.gz"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()

    def _compiler(self):
        # R33: compiler from the toolchain conf, never from bare PATH
        exe = self.conf.get("tools.build:compiler_executables", default={}) or {}
        return exe.get("c") or exe.get("cpp") or "clang"

    def build(self):
        apply_conandata_patches(self)
        cc = self._compiler()
        dist = os.path.join(self.source_folder, "dist")
        if not os.path.isdir(dist):
            os.makedirs(dist)
        # no configure in this 1993 tarball: compile each target variant
        # directly, mirroring the upstream Makefile rules (CFLAGS -DSPARC..)
        for name, macro in MACHINES:
            out = os.path.join(dist, name)
            cmd = '{} -O2 -D{} -o "{}" superopt.c'.format(cc, macro, out)
            self.run(cmd, cwd=self.source_folder)

    def package(self):
        from conan.tools.files import copy
        dist = os.path.join(self.source_folder, "dist")
        copy(self, "*", src=dist,
             dst=os.path.join(self.package_folder, "bin"))
        for name, _macro in MACHINES:
            os.chmod(os.path.join(self.package_folder, "bin", name), 0o755)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
