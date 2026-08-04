#!/usr/bin/env python3
"""Conan recipe for tektoncd-cli 0.45.0."""

import os
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, download
from conan.tools.layout import basic_layout


class TektoncdCliConan(ConanFile):
    name = "tektoncd-cli"
    version = "0.45.0"
    description = "Command-line interface for interacting with Tekton"
    license = "Apache-2.0"
    homepage = "https://github.com/tektoncd/cli"
    url = "https://github.com/tektoncd/cli"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")
        if str(self.settings.arch) not in ("armv8", "arm64", "aarch64"):
            raise ConanInvalidConfiguration(
                "The upstream pre-built Tekton CLI package used for OHOS PC is linux/arm64 only"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        sources = self.conan_data["sources"]
        download(self, sources["url"], sources["filename"], sha256=sources["sha256"])
        self.run(f'tar xzf "{sources["filename"]}"')

    def build(self):
        self.output.info(
            "Using upstream pre-built Tekton CLI linux/arm64 release package; "
            "the OHOS CI worker currently does not provide a Go toolchain."
        )

    def package(self):
        binary = self.conan_data["build"]["binary"]
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        tarball = os.path.join(self.source_folder, self.conan_data["sources"]["filename"])
        self.run(f'tar xzf "{tarball}" -C "{bin_dir}" "{binary}"')
        binary_path = os.path.join(bin_dir, binary)
        os.chmod(binary_path,
                 stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |
                 stat.S_IRGRP | stat.S_IXGRP |
                 stat.S_IROTH | stat.S_IXOTH)
        self._sign_ohos_binary(binary_path)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "README.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "tektoncd-cli"),
             keep_path=False)

    def _sign_ohos_binary(self, binary_path):
        if str(self.settings.os) != "OHOS":
            return

        signer = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(signer):
            self.output.warning(
                "binary-sign-tool is unavailable; the OHOS release worker must sign tkn"
            )
            return

        signed_path = binary_path + ".signed"
        if os.path.isfile(objcopy):
            self.run(
                f'"{objcopy}" --remove-section .codesign "{binary_path}" || true',
                quiet=True,
            )
        self.run(
            f'"{signer}" sign -inFile "{binary_path}" '
            f'-outFile "{signed_path}" -selfSign 1',
            quiet=True,
        )
        os.replace(signed_path, binary_path)
        os.chmod(binary_path,
                 stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |
                 stat.S_IRGRP | stat.S_IXGRP |
                 stat.S_IROTH | stat.S_IXOTH)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
