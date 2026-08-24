import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class LastzConan(ConanFile):
    name = "lastz"
    version = "1.04.52"

    license = "MIT"
    homepage = "https://github.com/lastz/lastz"
    url = "https://github.com/lastz/lastz"
    description = "Pairwise DNA sequence alignment program"
    topics = ("bioinformatics", "alignment", "dna")

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self, src_folder="src")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(
            self,
            **self.conan_data["sources"][self.version],
            strip_root=True,
        )

    def build(self):
        apply_conandata_patches(self)

        copy(
            self,
            "*",
            src=self.source_folder,
            dst=self.build_folder,
        )

        compiler_executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
        )

        cc = compiler_executables.get("c", "cc")

        cc_command = "{} -Wno-unused-command-line-argument".format(cc)

        self.run(
            'make -C "{}" CC="{}"'.format(
                self.build_folder,
                cc_command,
            )
        )

        self.run(
            'make -C "{}" CC="{}" test'.format(
                self.build_folder,
                cc_command,
            )
        )

        self.run(
            'make -C "{}" CC="{}" base_tests'.format(
                self.build_folder,
                cc_command,
            )
        )

        self.run(
            'make -C "{}" CC="{}" base_test_nib1'.format(
                os.path.join(self.build_folder, "src"),
                cc_command,
            )
        )
    def package(self):
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

        copy(
            self,
            "lastz",
            src=os.path.join(self.build_folder, "src"),
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )

        copy(
            self,
            "lastz_D",
            src=os.path.join(self.build_folder, "src"),
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []

        self.buildenv_info.prepend_path(
            "PATH",
            os.path.join(self.package_folder, "bin"),
        )

        self.runenv_info.prepend_path(
            "PATH",
            os.path.join(self.package_folder, "bin"),
        )
