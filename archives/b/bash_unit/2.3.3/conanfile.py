#!/usr/bin/env python3
"""Conan recipe — bash_unit 2.3.3 (Bash script tool)."""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class BashUnitConan(ConanFile):
    name = "bash_unit"
    version = "2.3.3"
    description = "Bash unit testing framework"
    license = "MIT"
    homepage = "https://github.com/bash-unit/bash_unit"
    url = "https://github.com/bash-unit/bash_unit"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        test_tmp = os.path.join(self.build_folder, "upstream-test-tmp")
        os.makedirs(test_tmp, exist_ok=True)
        default_bash = (
            "/data/service/hnp/bin/bash"
            if str(self.settings.os) == "OHOS"
            else "bash"
        )
        bash = os.environ.get("CONFIG_SHELL", default_bash)
        self.run(
            f'TMPDIR="{test_tmp}" FORCE_COLOR=false '
            f'"{bash}" ./bash_unit tests/test*',
            cwd=self.source_folder,
        )

    def package(self):
        copy(self, "bash_unit", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "README.adoc", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc", "bash_unit"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
