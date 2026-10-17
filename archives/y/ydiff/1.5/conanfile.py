import os
import stat

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class YdiffConan(ConanFile):
    name = "ydiff"
    version = "1.5"
    description = "View colored incremental diffs in a terminal"
    license = "BSD-3-Clause"
    homepage = "https://github.com/ymattw/ydiff"
    url = "https://github.com/ymattw/ydiff"
    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        source = self.conan_data["sources"][0]
        get(
            self,
            url=source["url"],
            sha256=source["sha256"],
            strip_root=True,
        )

    def build(self):
        apply_conandata_patches(self)
        script = os.path.join(self.source_folder, "ydiff.py")
        self.run(f'python3 -m py_compile "{script}"')
        self.run(f'python3 "{script}" --version')

    def package(self):
        copy(
            self,
            "ydiff.py",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )
        installed = os.path.join(self.package_folder, "bin", "ydiff.py")
        target = os.path.join(self.package_folder, "bin", "ydiff")
        os.rename(installed, target)
        os.chmod(
            target,
            os.stat(target).st_mode
            | stat.S_IXUSR
            | stat.S_IXGRP
            | stat.S_IXOTH,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
