import os
import shutil
from shlex import quote

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _dep(self):
        return self.dependencies["mpich"]

    def _path(self, name):
        for bindir in self._dep().cpp_info.bindirs:
            candidate = os.path.join(bindir, name)
            if os.path.exists(candidate):
                return candidate
        found = shutil.which(name)
        if found:
            return found
        raise Exception(f"{name} not found in mpich package")

    def build(self):
        dep = self._dep().cpp_info
        mpicc = self._path("mpicc")
        incs = " ".join(f"-I{p}" for p in dep.includedirs)
        libdirs = " ".join(f"-L{p}" for p in dep.libdirs)
        self.run(f'"{mpicc}" test.c -o test_mpi {incs} {libdirs}')

    def test(self):
        mpicc = self._path("mpicc")
        mpiexec = self._path("mpiexec")
        self.run(f'"{mpicc}" -show')
        if not can_run(self):
            self.output.info("cross-building: compile/link smoke only")
            return
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        command = f"MPIEXEC_TIMEOUT=30 {quote(mpiexec)} -n 2 ./test_mpi"
        self.run(f"{quote(bash)} -c {quote(command)}", env="conanrun")
