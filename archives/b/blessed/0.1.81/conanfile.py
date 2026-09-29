from conan import ConanFile
from conan.tools.files import get, copy
import os


class BlessedConan(ConanFile):
    name = "blessed"
    version = "0.1.81"
    description = "A high-level terminal interface library for node.js"
    homepage = "https://github.com/chjj/blessed"
    license = "MIT"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def package(self):
        copy(self, "*",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib", "node_modules", "blessed"),
             excludes=["conandata.yml", "conanfile.py", "*.pyc", "__pycache__"])
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        node_modules = os.path.join(self.package_folder, "lib", "node_modules")
        self.buildenv_info.prepend_path("NODE_PATH", node_modules)
        self.runenv_info.prepend_path("NODE_PATH", node_modules)
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
