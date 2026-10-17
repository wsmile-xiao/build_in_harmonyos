#!/usr/bin/env python3
"""Test package for kubeadm 1.36.2 — runs `kubeadm version`.

The Go binary is CGO_ENABLED=0 static, built for the OHOS target (GOOS=linux
GOARCH=arm64) and self-signed by the recipe. The consumer script asserts it
executes and reports the ldflags-injected v1.36.2 version.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class KubeadmTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        exe_name = "kubeadm.exe" if str(self.settings.os) == "Windows" else "kubeadm"
        bin_path = os.path.join(
            self.dependencies["kubeadm"].package_folder, "bin", exe_name
        )
        if not os.path.isfile(bin_path):
            raise AssertionError(
                "kubeadm binary not found at {}".format(bin_path)
            )
        script = os.path.join(self.source_folder, "test_kubeadm.sh")
        if can_run(self):
            shell = (
                os.environ.get("CONFIG_SHELL")
                or shutil.which("bash")
                or "/data/service/hnp/bin/bash"
            )
            self.run(
                '"{}" "{}" "{}"'.format(shell, script, bin_path),
                env="conanrun",
            )
        else:
            # Cross build: the OHOS target binary cannot run on the host.
            # Verify it is a valid ELF executable instead.
            with open(bin_path, "rb") as f:
                if f.read(4) != b"\x7fELF":
                    raise AssertionError(
                        "kubeadm binary is not an ELF executable: {}".format(bin_path)
                    )
            self.output.info(
                "HMBS_KUBEADM_SKIP: cross build — binary is a valid ELF, "
                "not runnable on host"
            )
