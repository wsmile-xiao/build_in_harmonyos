from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.layout import basic_layout
import os


class BlockhashConan(ConanFile):
    name = "blockhash"
    version = "0.1"
    description = "Perceptual image hash calculation tool based on Block Mean Value algorithm"
    license = "MIT"
    homepage = "https://github.com/commonsmachinery/blockhash"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        if os.path.abspath(self.recipe_folder) != os.path.abspath(self.export_sources_folder):
            copy(self, "stb_image.h", src=self.recipe_folder, dst=self.export_sources_folder)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        if os.path.abspath(self.export_sources_folder) != os.path.abspath(self.source_folder):
            copy(self, "stb_image.h", src=self.export_sources_folder, dst=self.source_folder)
        # R33: Get compiler from Conan conf, not hardcoded
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        self.run(
            f"cd {self.source_folder} && {cc} -O3 -DVERSION='\"0.3.2-harmonyos\"' "
            f"-o blockhash blockhash.c -lm",
            env="conanbuild",
        )

    def package(self):
        copy(self, "blockhash", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
