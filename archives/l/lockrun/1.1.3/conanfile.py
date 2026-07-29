#!/usr/bin/env python3
"""Build lockrun 1.1.3 from its single C source file."""
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, download, export_conandata_patches
from conan.tools.layout import basic_layout


class LockrunConan(ConanFile):
    name = "lockrun"
    version = "1.1.3"
    description = "Run cron jobs with overrun protection"
    license = "LicenseRef-Public-Domain"
    homepage = "https://unixwiz.net/tools/lockrun.html"
    url = "https://unixwiz.net/tools/lockrun.html"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        download(
            self,
            url=self.conan_data["sources"]["url"],
            filename=os.path.join(self.source_folder, "lockrun.c"),
            sha256=self.conan_data["sources"]["sha256"],
        )

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        default_cc = {
            "gcc": "gcc",
            "clang": "clang",
        }.get(str(self.settings.compiler), "cc")
        cc = compilers.get("c", default_cc)
        build_type_flags = {
            "Debug": ["-O0", "-g"],
            "Release": ["-O2", "-DNDEBUG"],
            "RelWithDebInfo": ["-O2", "-g", "-DNDEBUG"],
            "MinSizeRel": ["-Os", "-DNDEBUG"],
        }
        optimization_flags = build_type_flags.get(
            str(self.settings.build_type),
            ["-O2", "-DNDEBUG"],
        )
        subprocess.run(
            [
                cc,
                "-fPIC",
                *optimization_flags,
                "-Wall",
                "-Wextra",
                "-Werror",
                "-o",
                "lockrun",
                "lockrun.c",
            ],
            cwd=self.source_folder,
            check=True,
        )

    def package(self):
        copy(self, "lockrun", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)

        bin_path = os.path.join(self.package_folder, "bin", "lockrun")
        if os.path.exists(bin_path):
            os.chmod(bin_path, 0o755)
        if os.path.exists(bin_path) and str(self.settings.os) == "OHOS":
            sign_tool = "/data/service/hnp/bin/binary-sign-tool"
            tmp_signed = bin_path + ".signed"
            subprocess.run(
                [sign_tool, "sign", "-inFile", bin_path, "-outFile", tmp_signed, "-selfSign", "1"],
                check=True,
            )
            os.replace(tmp_signed, bin_path)
            os.chmod(bin_path, 0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
