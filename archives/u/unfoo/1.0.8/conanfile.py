"""Package the upstream Bash archive extractor without pretending to compile it."""
import os
import stat

from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class UnfooConan(ConanFile):
    name = "unfoo"
    version = "1.0.8"
    description = "Bash wrapper for extracting archives of multiple formats"
    license = "BSD-3-Clause"
    homepage = "https://github.com/vitaminmoo/unfoo"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        # Script-only package: this hook applies declared patches, if any.
        apply_conandata_patches(self)

    def package(self):
        dest = os.path.join(self.package_folder, "bin")
        copy(self, "unfoo", src=self.source_folder, dst=dest, keep_path=False)
        program = os.path.join(dest, "unfoo")
        os.chmod(program, os.stat(program).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
