import os

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class MicrouiConan(ConanFile):
    name = "microui"
    version = "2.02"
    description = "Tiny, portable immediate-mode UI library written in ANSI C"
    license = "MIT"
    homepage = "https://github.com/rxi/microui"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c") or "clang"
        ar = compilers.get("ar") or "llvm-ar"
        cflags = "-fPIC -O2"
        self.run(
            f"{cc} {cflags} -I src -c src/microui.c -o microui.o",
            cwd=self.source_folder,
        )
        if self.options.shared:
            self.run(f"{cc} -shared microui.o -o libmicroui.so", cwd=self.source_folder)
        else:
            self.run(f"{ar} rcs libmicroui.a microui.o", cwd=self.source_folder)

    def package(self):
        copy(
            self,
            "microui.h",
            src=os.path.join(self.source_folder, "src"),
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "libmicroui.a",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "lib"),
        )
        copy(
            self,
            "libmicroui.so",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "lib"),
        )

    def package_info(self):
        self.cpp_info.libs = ["microui"]
