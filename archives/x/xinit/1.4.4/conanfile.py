#!/usr/bin/env python3
"""Conan recipe - xinit 1.4.4."""
import os
import subprocess

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class XinitConan(ConanFile):
    name = "xinit"
    version = "1.4.4"
    description = "X.Org initialisation program"
    license = "MIT-open-group"
    homepage = "https://www.x.org/"
    url = "https://www.x.org/"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    _sys_prefix = os.path.join(os.path.expanduser("~"), "usr", "local")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--build=aarch64-unknown-linux-gnu",
            "--host=aarch64-unknown-linux-ohos",
            f"--x-includes={self._sys_prefix}/include",
            f"--x-libraries={self._sys_prefix}/lib",
            f"XINIT_CFLAGS=-I{self._sys_prefix}/include",
            f"XINIT_LIBS=-L{self._sys_prefix}/lib -lX11",
        ])
        tc.extra_ldflags.append(f"-L{self._sys_prefix}/lib")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        Autotools(self).install()
        binary = os.path.join(self.package_folder, "bin", "xinit")
        if os.path.exists(binary):
            self._sign_binary(binary)

    def _sign_binary(self, path):
        os.chmod(path, 0o755)
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if str(self.settings.os) != "OHOS" or not (os.path.exists(sign_tool) and os.path.exists(objcopy)):
            return
        tmp_signed = path + ".signed"
        subprocess.run(
            [objcopy, "--remove-section", ".codesign", path],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            [sign_tool, "sign", "-inFile", path, "-outFile", tmp_signed, "-selfSign", "1"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        os.replace(tmp_signed, path)
        os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
