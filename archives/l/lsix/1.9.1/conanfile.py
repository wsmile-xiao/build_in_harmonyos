import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    load,
    save,
)
from conan.tools.layout import basic_layout


class LsixConan(ConanFile):
    name = "lsix"
    version = "1.9.1"
    description = "Like ls, but for images: shows thumbnails directly in the terminal via SIXEL graphics"
    license = "GPL-3.0-or-later"
    url = "https://gitcode.com/atomgit-mirrors/lsix"
    homepage = "https://github.com/hackerb9/lsix"
    topics = ("sixel", "terminal-graphics", "image-viewer", "cli", "shell-script")
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    # lsix is a single bash script; run-time interpreters and tools come from
    # the "imagemagick-full" package (magick/montage) and "bash" (>= 4).
    def requirements(self):
        self.requires("imagemagick-full/7.1.2-23")
        self.requires("bash/5.3")

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        # Ship the stty-optional patch with the exported recipe, otherwise
        # apply_conandata_patches() cannot find it during create.
        export_conandata_patches(self)

    def source(self):
        # The codeload URL ends with the bare tag name ("…/refs/tags/1.9.1"),
        # which carries no extension, so get() has to be told the archive name
        # or it picks the wrong decompressor (same trap as archives/t/ttygif).
        get(
            self,
            **self.conan_data["sources"][self.version],
            strip_root=True,
            filename="lsix-1.9.1.tar.gz",
        )

    def build(self):
        # Nothing to compile: upstream lsix is a single interpreted bash
        # script. The conandata patches still have to be applied here —
        # Conan 2 does not apply them automatically.
        apply_conandata_patches(self)

    def package(self):
        save(
            self,
            os.path.join(self.package_folder, "res", "lsix"),
            load(self, os.path.join(self.source_folder, "lsix")),
        )
        # lsix has no native executable, so it needs no ELF signing.
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # The script lives in res/ (not a native executable), so only resdirs
        # and bindirs are declared; no libdirs, no CMake target.
        self.cpp_info.bindirs = ["res"]
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["res"]
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.set_property("pkg_config", "lsix")

    def package_id(self):
        self.info.clear()
