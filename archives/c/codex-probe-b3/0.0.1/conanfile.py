import os
from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches

class CodexProbeB3Conan(ConanFile):
    name = "codex-probe-b3"
    version = "0.0.1"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"
    package_type = "application"

    def source(self):
        get(self, **self.conan_data["sources"][0], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

    def package(self):
        copy(self, "provider_probe.py", src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "codex_probe.py", src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib"))
        copy(self, "*", src=os.path.join(self.source_folder, "codex_probe_data"),
             dst=os.path.join(self.package_folder, "lib", "codex_probe_data"))
        copy(self, "*.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "codex-probe"),
             keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "codex-probe"),
             keep_path=False)

    def package_info(self):
        lib_dir = os.path.join(self.package_folder, "lib")
        self.runenv_info.prepend_path("PYTHONPATH", lib_dir)
        self.buildenv_info.prepend_path("PYTHONPATH", lib_dir)
        self.cpp_info.bindirs = ["lib"]
