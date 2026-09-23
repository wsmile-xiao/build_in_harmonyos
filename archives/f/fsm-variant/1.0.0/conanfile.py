from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, get
import os


class FsmVariantConan(ConanFile):
    name = "fsm-variant"
    version = "1.0.0"
    description = "Header-only finite state machine built with std::variant"
    license = "MIT"
    homepage = "https://github.com/mpusz/fsm-variant"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    exports_sources = "conandata.yml"

    def export_sources(self):
        copy(self, "conandata.yml", dst=".", src=self.recipe_folder)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # The v1.0.0 release omits cmake/common. Compile the two shipped
        # examples directly without fetching an unpinned SSH submodule.
        cxx = (self.conf.get("tools.build:compiler_executables",
                             default={}, check_type=dict) or {}).get("cpp", "c++")
        include_dir = os.path.join(self.source_folder, "src", "include")
        examples = [("connection_fsm", "connection_fsm"), ("tcp_fsm", "tcp_fsm")]
        for name, stem in examples:
            subdir = os.path.join(self.source_folder, "example", name)
            source = os.path.join(subdir, f"{stem}_tests.cpp")
            output = os.path.join(self.build_folder, name)
            self.run(f'"{cxx}" -std=c++17 -I"{include_dir}" -I"{subdir}" "{source}" -o "{output}"')
            self.run(f'"{output}"')

    def package(self):
        copy(self, "*.h", dst=os.path.join(self.package_folder, "include"),
             src=os.path.join(self.source_folder, "src", "include"))
        copy(self, "LICENSE.md", dst=os.path.join(self.package_folder, "licenses"),
             src=self.source_folder)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "fsm")
        self.cpp_info.set_property("cmake_target_name", "mp::fsm")
