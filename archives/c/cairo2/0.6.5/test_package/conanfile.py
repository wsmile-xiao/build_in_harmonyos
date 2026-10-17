#!/usr/bin/env python3
"""Conan test_package — cairo2 0.6.5

Compiles a small OCaml program against the packaged cairo2 library and runs
it: creates an image surface, draws, writes/reads back a PNG.
This exercises the real OCaml API + C stubs (not a print-only shell test).
See test_smoke.sh for the actual test logic.
"""
import os

from conan import ConanFile
from conan.tools.layout import basic_layout


class Cairo2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        self.tool_requires("ocaml/4.14.1.1.4")

    def layout(self):
        basic_layout(self)

    def _dep_libdirs(self, name):
        try:
            dep = self.dependencies[name]
        except KeyError:
            return []
        if dep.package_folder is None:
            return []
        return [os.path.join(dep.package_folder, d)
                for d in (dep.cpp_info.libdirs or [])]

    def test(self):
        pkg = self.dependencies["cairo2"]
        pkg_lib = os.path.join(pkg.package_folder, "lib", "cairo2")
        ocaml_inc = ('OCAMLLIB="$(d=$(dirname "$(realpath "$(which ocamlc)")"); '
                     'echo "$(dirname "$d")/lib/ocaml")"')
        ld = []
        for name in ("cairo", "freetype", "fontconfig", "pixman", "expat",
                     "libpng", "zlib", "brotli", "bzip2"):
            for d in self._dep_libdirs(name):
                if d not in ld:
                    ld.append(d)
        ldpath = ":".join(ld)
        self.run(
            f"export LD_LIBRARY_PATH={ldpath}:$LD_LIBRARY_PATH; export {ocaml_inc}; "
            f'export PKG_LIB="{pkg_lib}"; '
            f'sh "{os.path.join(os.path.dirname(__file__), "test_smoke.sh")}"',
            env="conanbuild",
        )
