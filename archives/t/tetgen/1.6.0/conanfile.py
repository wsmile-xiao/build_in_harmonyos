#!/usr/bin/env python3
"""Conan recipe for TetGen 1.6.0.

TetGen is a C++ quality tetrahedral mesh generator and 3D Delaunay triangulator.
The upstream distribution ships a handwritten Makefile (no configure step) plus a
minimal CMakeLists.txt. This recipe uses a direct build driven by the upstream
Makefile rules:

  * ``tetgen``  — CLI executable (tetgen.cxx + predicates.cxx, linked with -lm)
  * ``libtet.a`` — static library (tetgen.cxx compiled with -DTETLIBRARY)

Upstream has no unit-test suite; the bundled ``example.poly`` is used as an
end-to-end smoke test, and the consumer test exercises the public library API.
"""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class TetgenConan(ConanFile):
    name = "tetgen"
    version = "1.6.0"
    description = "A Quality Tetrahedral Mesh Generator and a 3D Delaunay Triangulator"
    license = "AGPL-3.0-only"
    homepage = "https://wias-berlin.de/software/tetgen/"
    url = "https://wias-berlin.de/software/tetgen/"
    topics = ("mesh", "tetrahedralization", "delaunay", "computational-geometry")
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # R33: get the compiler from Conan conf, never from bare shell env vars.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = compilers.get("cpp", "clang++")
        ar = compilers.get("ar") or shutil.which("llvm-ar") or "/data/service/hnp/bin/llvm-ar"

        src = self.source_folder
        build = self.build_folder

        # Upstream compiles J. Shewchuk's geometric predicates at -O0 (the
        # adaptive-precision arithmetic is sensitive to FP optimization).
        self.run(f'"{cxx}" -O0 -c "{src}/predicates.cxx" -o "{build}/predicates.o"', env="conanbuild")

        # Library object: -DTETLIBRARY excludes main() and enables the library
        # interface overloads in tetgen.h.
        self.run(f'"{cxx}" -O3 -DTETLIBRARY -c "{src}/tetgen.cxx" -o "{build}/tetgen.o"', env="conanbuild")

        # Static library libtet.a (upstream "make tetlib").
        self.run(f'"{ar}" rcs "{build}/libtet.a" "{build}/tetgen.o" "{build}/predicates.o"', env="conanbuild")

        # CLI executable: compile tetgen.cxx without TETLIBRARY so main() is built.
        self.run(f'"{cxx}" -O3 -o "{build}/tetgen" "{src}/tetgen.cxx" "{src}/predicates.cxx" -lm', env="conanbuild")

        # HarmonyOS ELF must be signed before it can be executed.
        self._sign(os.path.join(build, "tetgen"))

        # Upstream smoke test: tetrahedralize the bundled 28-point PLC example.
        self.run(f'"{build}/tetgen" "{src}/example.poly"', env="conanrun")

    def package(self):
        copy(self, "libtet.a", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"))
        copy(self, "tetgen.h", src=self.source_folder, dst=os.path.join(self.package_folder, "include"))
        copy(self, "tetgen", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))
        # Upstream 1.6.0 tarball has no standalone LICENSE file; README carries the
        # copyright notice and points at the AGPL-3.0 terms.
        copy(self, "README", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["tet"]
        self.cpp_info.system_libs = ["m"]
        # The CLI executable is packaged for consumers (R38).
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "tetgen")
        self.cpp_info.set_property("cmake_target_name", "tetgen::tetgen")

    @staticmethod
    def _sign(executable):
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(signer):
            raise ConanInvalidConfiguration(
                "binary-sign-tool is required to execute upstream tests on OHOS"
            )
        signed = executable + ".signed"
        if os.path.isfile(objcopy):
            subprocess.run(
                [objcopy, "--remove-section", ".codesign", executable],
                check=False,
            )
        subprocess.run(
            [signer, "sign", "-inFile", executable, "-outFile", signed, "-selfSign", "1"],
            check=True,
        )
        shutil.move(signed, executable)
        os.chmod(executable, 0o755)
