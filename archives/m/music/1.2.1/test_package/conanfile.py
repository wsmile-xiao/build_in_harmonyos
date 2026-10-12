"""Conan test_package — music 1.2.1 consumer test (OHOS, mpich MPI)."""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building


class MusicTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _prefix(self, ref):
        folder = self.dependencies[ref].package_folder
        return {name: os.path.join(folder, name) for name in ("include", "lib", "bin")}

    def _find_cxx(self):
        """R33: the driver comes from the profile, never from a hard-coded device path."""
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        for candidate in (compilers.get("cpp"), shutil.which("clang++"), os.environ.get("CXX")):
            if candidate:
                return candidate
        raise ConanException("no C++ driver: set tools.build:compiler_executables in the profile")

    def build(self):
        music = self._prefix("music")
        mpich = self._prefix("mpich")
        incs = [music["include"], mpich["include"]]
        libs = [music["lib"], mpich["lib"]]
        args = " ".join(
            [f'-I"{path}"' for path in incs]
            + [f'-L"{path}"' for path in libs]
            + ["-lmusic", "-lmpi"]
            + [f'-Wl,-rpath,"{path}"' for path in libs]
        )
        self.run(f'"{self._find_cxx()}" -std=c++14 test_music.cc -o test_music {args}')

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: consumer verified by compile+link only")
            return
        mpiexec = os.path.join(self._prefix("mpich")["bin"], "mpiexec")
        program = os.path.abspath("test_music")
        self.run(f'"{mpiexec}" -n 2 "{program}"', env="conanrun")
