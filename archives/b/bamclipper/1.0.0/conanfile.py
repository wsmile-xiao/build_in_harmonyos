#!/usr/bin/env python3
"""Conan recipe for BAMClipper 1.0.0."""
import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class BamclipperConan(ConanFile):
    name = "bamclipper"
    version = "1.0.0"
    description = "Remove PCR primer sequences from SAM/BAM alignments by soft-clipping"
    license = "MIT"
    homepage = "https://github.com/tommyau/bamclipper"
    url = "https://github.com/tommyau/bamclipper"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("bash/5.3")
        self.requires("perl/5.42.2.1")
        self.requires("samtools/1.21")
        self.requires("parallel/20260522")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            strip_root=True,
        )
        apply_conandata_patches(self)

    def build(self):
        bash = os.path.join(self.dependencies["bash"].package_folder, "bin", "bash")
        perl = os.path.join(self.dependencies["perl"].package_folder, "bin", "perl")
        self.run(f'"{bash}" -n bamclipper.sh', cwd=self.source_folder)
        self.run(f'"{perl}" -c clipprimer.pl', cwd=self.source_folder)
        self.run(f'"{perl}" -c injectseparator.pl', cwd=self.source_folder)

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        for script in ("bamclipper.sh", "clipprimer.pl", "injectseparator.pl"):
            copy(self, script, src=self.source_folder, dst=bindir)
            os.chmod(os.path.join(bindir, script), 0o755)
        copy(self, "README.md", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "doc", "bamclipper"))
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        package_bin = os.path.join(self.package_folder, "bin")
        bash_bin = os.path.join(self.dependencies["bash"].package_folder, "bin")
        self.cpp_info.bindirs = ["bin"]
        self.buildenv_info.define_path("BAMCLIPPER_HOME", self.package_folder)
        self.buildenv_info.prepend_path("PATH", bash_bin)
        self.buildenv_info.prepend_path("PATH", package_bin)
        self.runenv_info.prepend_path("PATH", bash_bin)
        self.runenv_info.prepend_path("PATH", package_bin)
