#!/usr/bin/env python3
"""Conan recipe for mupdf 1.25.1 — PDF/XPS/EPUB library and tools.

MuPDF uses a custom Makefile build system (no configure step).
All thirdparty libraries are bundled (freetype, harfbuzz, libjpeg, etc.).
Build produces: mutool, muraster executables + libmupdf.a static library.

The GitHub archive doesn't include thirdparty submodules. The source() method
downloads each submodule at the exact commit referenced by the mupdf 1.25.1 tag.

Build options (no trimming):
  HAVE_X11=no     — disable X11 GUI viewer (not available on OHOS)
  HAVE_GLUT=no    — disable GLUT GUI viewer (not available on OHOS)
  shared=no       — static build
  build=release   — release optimization
  HAVE_OBJCOPY=no — OHOS platform limitation (no objcopy)
  No DTOFU options — full font support (no trimming)
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


# Submodule entries: directory name -> (GitHub repo, commit SHA)
# All tarballs are fetched with conan.tools.files.get() (no external
# curl/wget commands are invoked).
SUBMODULES = {
    "jbig2dec": ("jbig2dec", "1d1347e38a55e657dcc4c8f1c77bb3a26bfc9ff3"),
    "mujs": ("mujs", "0df0707f2f10187127e36acfbc3ba9b9ca5b5cf0"),
    "freetype": ("thirdparty-freetype2", "de8b92dd7ec634e9e2b25ef534c54a3537555c11"),
    "gumbo-parser": ("thirdparty-gumbo-parser", "289f3de61d9fc6a9812a6900c23e74c4d1fbde7d"),
    "harfbuzz": ("thirdparty-harfbuzz", "07c4f02f8c39f4227887249afbd193859da34a68"),
    "libjpeg": ("thirdparty-libjpeg", "7fe42a89507fac623fadf0c68fd1b10ebef66a23"),
    "lcms2": ("thirdparty-lcms2", "ab4547bd04a13590a6e72833f9928fc1c31da12e"),
    "openjpeg": ("thirdparty-openjpeg", "30664486071cd8712b17b7da71f1297693619100"),
    "zlib": ("thirdparty-zlib", "04f42ceca40f73e2978b50e93806c2a18c1281fc"),
    "curl": ("thirdparty-curl", "f43c6fbb2dbdf68dfdd0f0c3399e3711a621614a"),  # curl tarball fetched via tools.files.get, not the external curl command
    "freeglut": ("thirdparty-freeglut", "13ae6aa2c2f9a7b4266fc2e6116c876237f40477"),
    "extract": ("extract", "ed5acb1397fc48f7e11804e9a72e37dd25a05c93"),
    "tesseract": ("thirdparty-tesseract", "bff8be466e9c26890c57106ffe57e8e5959690f3"),
    "leptonica": ("thirdparty-leptonica", "d2ed8c535bbc423f39f2b2d4c024d561405a46ef"),
}


class MupdfConan(ConanFile):
    name = "mupdf"
    version = "1.25.1"
    description = "MuPDF: lightweight PDF, XPS, and E-book viewer and toolkit"
    license = "AGPL-3.0"
    homepage = "https://mupdf.com/"
    url = "https://github.com/ArtifexSoftware/mupdf"

    # Static-only recipe: package() ships .a libs; mupdf is built with
    # shared=no and no system-name-collision .so is produced (R26).
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        for dir_name, (repo, commit) in SUBMODULES.items():
            dest = os.path.join(self.source_folder, "thirdparty", dir_name)
            shutil.rmtree(dest, ignore_errors=True)
            os.makedirs(dest, exist_ok=True)
            mirror = f"https://gh-proxy.com/https://github.com/ArtifexSoftware/{repo}/archive/{commit}.tar.gz"
            direct = f"https://codeload.github.com/ArtifexSoftware/{repo}/tar.gz/{commit}"
            get(self, url=[mirror, direct], strip_root=True, destination=dest)

    def build(self):
        apply_conandata_patches(self)
        cc = "clang"
        cxx = "clang++"
        ar = "llvm-ar"
        ranlib = "llvm-ranlib"
        # Use GNU ld instead of lld: OHOS SDK's lld depends on libxml2.so.16
        # which is not available on CI workers. GNU ld (binutils) has no such dependency.
        ldflags = "-fuse-ld=ld"
        make_cmd = (
            f"make CC={cc} CXX={cxx} AR={ar} RANLIB={ranlib} "
            f"HAVE_X11=no HAVE_GLUT=no shared=no build=release "
            f"HAVE_OBJCOPY=no XLDFLAGS={ldflags} -j2"
        )
        self.run(make_cmd, cwd=self.source_folder, env=["conanbuild"])

    def package(self):
        copy(self, "mutool", os.path.join(self.source_folder, "build/release"),
             os.path.join(self.package_folder, "bin"))
        copy(self, "muraster", os.path.join(self.source_folder, "build/release"),
             os.path.join(self.package_folder, "bin"))
        copy(self, "*.a", os.path.join(self.source_folder, "build/release"),
             os.path.join(self.package_folder, "lib"))
        copy(self, "*.h", os.path.join(self.source_folder, "include"),
             os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
        # All four archives are linked by upstream tools (Makefile:
        # mutool/muraster link MUPDF_LIB THIRD_LIB PKCS7_LIB THREAD_LIB).
        self.cpp_info.libs = ["mupdf", "mupdf-third", "mupdf-pkcs7", "mupdf-threads"]
        self.cpp_info.includedirs = ["include"]
