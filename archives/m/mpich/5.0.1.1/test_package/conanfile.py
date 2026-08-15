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

    def _shell(self):
        configured = os.environ.get("CONFIG_SHELL")
        if configured and os.path.isfile(configured) and os.access(configured, os.X_OK):
            return configured
        return shutil.which("bash") or shutil.which("sh") or "/system/bin/sh"

    def _prepare_tmp(self):
        # E002: /tmp is a read-only erofs on HarmonyOS; always run under a
        # writable TMPDIR so the MPI runtime and any tooling can create
        # temporary files during test execution.
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMPPREFIX"] = os.path.join(tmpdir, "sh")

    def build(self):
        self._prepare_tmp()
        mpicc = self._path("mpicc")
        source = os.path.join(self.source_folder, "test.c")
        self.run(f'"{mpicc}" "{source}" -o test_mpi')

    def test(self):
        self._prepare_tmp()
        mpicc = self._path("mpicc")
        mpiexec = self._path("mpiexec")
        self.run(f'"{mpicc}" -show')
        if not can_run(self):
            self.output.info("cross-building: compile/link smoke only")
            return
        shell = self._shell()
        # MPIEXEC_TIMEOUT is hydra-only; classic mpiexec (--with-pm=gforker)
        # ignores it, so wrap with an external timeout instead (E002-safe TMPDIR
        # is already prepared by _prepare_tmp).
        command = f'timeout 30 "{mpiexec}" -n 2 ./test_mpi'
        self.run(f'"{shell}" -c {quote(command)}', env="conanrun")
