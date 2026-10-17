import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class ReopConan(ConanFile):
    name = "reop"
    version = "2.1.1"
    description = "Simple file encryption and signing tool"
    license = "ISC"
    homepage = "https://github.com/tedu/reop"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires("libsodium/1.0.22")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        sodium = self.dependencies["libsodium"].package_folder
        include = os.path.join(sodium, "include")
        lib = os.path.join(sodium, "lib")
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        self.run(
            f'make -f GNUmakefile -j1 CC="{cc}" '
            f'CPPFLAGS="-Iother -I{include}" '
            f'LDFLAGS="-L{lib} -lsodium"',
            cwd=self.source_folder,
        )
        if not cross_building(self):
            self.run("sh test.sh", cwd=os.path.join(self.source_folder, "tests"))

    def package(self):
        copy(self, "reop", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "reop.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"),
             keep_path=False)
        # The tarball has no LICENSE file; each C source begins with its ISC notice.
        license_dir = os.path.join(self.package_folder, "licenses")
        os.makedirs(license_dir, exist_ok=True)
        with open(os.path.join(self.source_folder, "reop.c"), encoding="utf-8") as source:
            notice = source.read().split("*/", 1)[0] + "*/\n"
        with open(os.path.join(license_dir, "LICENSE"), "w", encoding="utf-8") as license_file:
            license_file.write(notice)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
