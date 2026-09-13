#!/usr/bin/env python3
from conan import ConanFile
from conan.tools.files import copy, mkdir, apply_conandata_patches
import os

class ChaosmarmosetsConan(ConanFile):
    name = "chaos-marmosets"
    version = "0.2.0"
    description = "Collection of misbehaving programs for chaos engineering"
    license = "GPL-2"
    homepage = "https://packages.debian.org/sid/chaos-marmosets"
    url = ""

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    exports_sources = "*.c", "*.h", "Makefile", "*.md", "LICENSE", "README.md", "NEWS", "noinline.h"

    def source(self):
        pass

    def export_sources(self):
        pass

    def build(self):
        apply_conandata_patches(self)
        # 只编译三个二进制文件，不生成文档（跳过 pandoc）
        self.run("make divide-by-zero leak-memory seg-fault")

    def package(self):
        mkdir(self, os.path.join(self.package_folder, "bin"))
        for exe in ["divide-by-zero", "leak-memory", "seg-fault"]:
            copy(self, exe, src=self.build_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
