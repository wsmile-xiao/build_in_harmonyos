from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout
import os


class MultiGitStatusConan(ConanFile):
    name = "multi-git-status"
    version = "2.3"
    description = "Show status for multiple Git repositories"
    license = "MIT"
    homepage = "https://packages.debian.org/trixie/mgitstatus"
    url = "https://github.com/fboender/multi-git-status"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def package_id(self):
        self.info.clear()

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        src = self.source_folder
        copy(self, "mgitstatus", src=src, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "mgitstatus.1.md", src=src,
             dst=os.path.join(self.package_folder, "res", "man", "man1"))
        copy(self, "LICENSE.txt", src=src, dst=os.path.join(self.package_folder, "licenses"))
        os.chmod(os.path.join(self.package_folder, "bin", "mgitstatus"), 0o755)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
