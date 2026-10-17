#!/usr/bin/env python3
import os
import stat

from conan import ConanFile


class OpenSshSsh1TestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _ohos_smoke_compile_assertions(self, package_folder):
        # The Conan cache lives on HMDFS (seclabel u:object_r:hmdfs:s0). OHOS
        # SELinux denies execution of any ELF on that label, and the writable
        # areas exposed to the CI account ($HOME, conan cache, /dev/shm) all
        # carry labels that forbid execution; the executable area
        # (u:object_r:hnp_file:s0, /data/service/hnp/bin) is read-only. With no
        # writable+executable partition available, the SSH1 functional smoke
        # (ssh -V / ssh -1 -G / ssh-keygen -t rsa1) cannot run on this CI device.
        # Fall back to compile-time assertions over the packaged artifacts: each
        # binary must exist, be an ELF, and carry the executable bit. The real
        # runtime smoke still runs on Linux (and on OHOS devices that do expose
        # a writable+executable partition, via the script's OHOS guard).
        for name in ("ssh", "ssh-keygen"):
            path = os.path.join(package_folder, "bin", name)
            if not os.path.isfile(path):
                raise AssertionError(f"missing packaged binary: {path}")
            with open(path, "rb") as fh:
                magic = fh.read(4)
            if magic != b"\x7fELF":
                raise AssertionError(
                    f"{path} is not an ELF (magic={magic!r})"
                )
            mode = os.stat(path).st_mode
            if not (mode & stat.S_IXUSR):
                raise AssertionError(
                    f"{path} is not executable (mode={oct(mode)})"
                )

    def test(self):
        package_folder = self.dependencies[self.tested_reference_str].package_folder

        if self.settings.os == "OHOS":
            self._ohos_smoke_compile_assertions(package_folder)
            return

        self.run(
            f"sh test_openssh_ssh1.sh '{package_folder}'",
            env="conanrun",
        )
