import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class E2FsimageConan(ConanFile):
    name = "e2fsimage"
    version = "0.2.3"
    description = "Tool to create and populate an ext2 filesystem image from a directory"
    license = "GPL-2.0"
    homepage = "https://github.com/Ledest/e2fsimage"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("e2fsprogs/1.47.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Get e2fsprogs paths from dependency
        e2fsprogs = self.dependencies["e2fsprogs"]
        e2fsprogs_include = os.path.join(e2fsprogs.package_folder, "include")
        e2fsprogs_lib = os.path.join(e2fsprogs.package_folder, "lib")
        # Overwrite Local.mak with correct Conan paths
        local_mak = os.path.join(self.source_folder, "Local.mak")
        with open(local_mak, "w") as f:
            f.write(f"""CPPFLAGS= -I{e2fsprogs_include}
CFLAGS=-fPIC -O2

LDFLAGS= -L{e2fsprogs_lib}
LIBS= -lext2fs -lcom_err

CC ?= clang
LD ?= ld.lld
STRIP ?= llvm-strip

prefix=/
basedir=
mandir=man
VERSION=0.2.3
""")
        # Build e2fsimage (R9: use -j1)
        self.run(f"make -C {self.source_folder} -j1")

    def package(self):
        # Copy e2fsimage binary to bin/
        copy(self, "e2fsimage", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "bin"))
        # Copy man pages if they exist
        copy(self, "*.8", src=os.path.join(self.source_folder, "man"),
             dst=os.path.join(self.package_folder, "share", "man", "man8"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
