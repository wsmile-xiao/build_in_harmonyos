#!/usr/bin/env python3
"""Conan recipe for cloud-utils-ec2metadata 0.34 — EC2 metadata query tool.

ec2metadata is a Python3 CLI from canonical/cloud-utils that queries and
displays AWS EC2 instance metadata (IMDSv1/IMDSv2). It is a pure script
tool (no compilation): the upstream Makefile only installs bin/ scripts
and man pages.

OHOS adaptation (patches/):
  0001  Makefile: install(1) --mode=0644 -> -m 0644 (HarmonyOS install
        does not support the long option)
  0002-0006  bin/*: hardcoded #!/bin/bash and #!/usr/bin/python3 shebangs
        -> #!/usr/bin/env bash / #!/usr/bin/env python3 (HarmonyOS has no
        /bin/bash or /usr/bin/python3)

Reference: cloud-utils 0.33 (same upstream) published as an application
package with no compiler requirements.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class CloudutilsEc2MetadataConan(ConanFile):
    name = "cloud-utils-ec2metadata"
    version = "0.34"
    description = "Query and display AWS EC2 metadata (from canonical/cloud-utils)"
    license = "GPL-3.0"
    homepage = "https://github.com/canonical/cloud-utils"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        pkg = self.package_folder
        self.run(
            f"make -C {self.source_folder} install"
            f" BINDIR={pkg}/bin"
            f" MANDIR={pkg}/share/man/man1"
            f" DOCDIR={pkg}/share/doc/cloud-utils"
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["share"]
        # 将包内 bin/ 注入消费者运行环境 PATH（conanrun），确保 test_package
        # 及下游可直接经 PATH 解析 ec2metadata/write-mime-multipart 等命令
        # （CI #42673 教训：仅 cpp_info.bindirs 不注入 conanrun PATH，
        #  test_package 按裸命令名解析时报 [Errno 2] No such file）
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin"))
