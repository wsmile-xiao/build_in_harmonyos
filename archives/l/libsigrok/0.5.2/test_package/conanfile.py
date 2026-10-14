"""Installed libsigrok consumer test."""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment, VirtualRunEnv
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class LibsigrokTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def generate(self):
        PkgConfigDeps(self).generate()
        VirtualRunEnv(self).generate()

    def build(self):
        compiler = self.conf.get("tools.build:compiler_executables", default={}).get("c", "cc")
        env = Environment()
        env.define("PKG_CONFIG_PATH", self.generators_folder)
        with env.vars(self).apply():
            self.run('"{}" -o consumer "{}" $(pkg-config --cflags --libs libsigrok)'.format(
                compiler, os.path.join(self.source_folder, "consumer.c")))
        if str(self.settings.os) == "OHOS":
            signer = shutil.which("binary-sign-tool")
            readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
            if not signer or not readelf:
                raise ConanInvalidConfiguration("OHOS ELF signer/readelf missing")
            subprocess.run([signer, "sign", "-inFile", "consumer",
                            "-outFile", "consumer.signed", "-selfSign", "1"],
                           check=True, capture_output=True, text=True, timeout=40)
            sections = subprocess.run([readelf, "-S", "consumer.signed"],
                                      check=True, capture_output=True, text=True, timeout=20)
            if ".codesign" not in sections.stdout:
                raise ConanException("signed consumer has no .codesign")
            os.chmod("consumer.signed", os.stat("consumer").st_mode)
            os.replace("consumer.signed", "consumer")

    def test(self):
        if can_run(self):
            self.run("./consumer", env="conanrun")
            self.output.info("CONSUMER_1_OF_1_PASS")
