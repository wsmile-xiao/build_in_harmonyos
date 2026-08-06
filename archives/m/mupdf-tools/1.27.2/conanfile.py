#!/usr/bin/env python3
"""Conan recipe for mupdf-tools 1.27.2 — command-line PDF tools.

MuPDF uses a custom Makefile build system (no configure step).
All thirdparty libraries are bundled (freetype, harfbuzz, libjpeg, etc.).
Build produces: mutool, muraster executables + libmupdf.a static library.

The GitHub archive doesn't include thirdparty submodules. The source() method
downloads each submodule at the exact commit referenced by the mupdf 1.27.2 tag.

Build options (no trimming):
  HAVE_X11=no     — disable X11 GUI viewer (not part of mupdf-tools)
  HAVE_GLUT=no    — disable GLUT GUI viewer (not part of mupdf-tools)
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


SUBMODULES = {
    "jbig2dec": ("jbig2dec", "d915733ec69260c1fd2c458b06835cb57bb85ac7"),
    "mujs": ("mujs", "33c83d8553048fd7710a518821cdefa5818e1559"),
    "freetype": ("thirdparty-freetype2", "42608f77f20749dd6ddc9e0536788eaad70ea4b5"),
    "gumbo-parser": ("thirdparty-gumbo-parser", "61bd4e736c3b342e592f65be0d65ec6a0acd8dcb"),
    "harfbuzz": ("thirdparty-harfbuzz", "ff8031d14b30d7c1b10fa3466d5f7c458837647b"),
    "libjpeg": ("thirdparty-libjpeg", "7fe42a89507fac623fadf0c68fd1b10ebef66a23"),
    "lcms2": ("thirdparty-lcms2", "f75fad71d53efd58d7312bea21c2bedca0b9e6da"),
    "openjpeg": ("thirdparty-openjpeg", "5781f7478694c78e7a245dc21fe7fa6f65bf3b96"),
    "zlib": ("thirdparty-zlib", "51b7f2abdade71cd9bb0e7a373ef2610ec6f9daf"),
    "curl": ("thirdparty-curl", "f43c6fbb2dbdf68dfdd0f0c3399e3711a621614a"),
    "freeglut": ("thirdparty-freeglut", "d5e2256d571b3ef66fb60716c99e35e9d3e570a2"),
    "extract": ("extract", "8750ac39c30a0d65119b426b5a491c5b8e8bf674"),
    "brotli": ("thirdparty-brotli", "6e092ab79683949f432d1c0cab88effa683c90d7"),
    "zxing-cpp": ("thirdparty-zxing-cpp", "742aef959e12a41eda494df78fd567c2e715ff57"),
    "zint": ("thirdparty-zint", "7a9fdd6cd00cd5bfd0082705d934c13ef84f25e1"),
    "tesseract": ("thirdparty-tesseract", "4a25c1f7280654545557d077b96dc14026c45c1f"),
    "leptonica": ("thirdparty-leptonica", "0dc051249fa596016310e6d1509518fd34be4f63"),
}


class MupdfToolsConan(ConanFile):
    name = "mupdf-tools"
    version = "1.27.2"
    description = "MuPDF command-line tools: mutool (PDF/XPS/EPUB tool) and muraster (rasterizer)"
    license = "AGPL-3.0"
    homepage = "https://mupdf.com/"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        for dir_name, (repo, commit) in SUBMODULES.items():
            url = f"https://codeload.github.com/ArtifexSoftware/{repo}/tar.gz/{commit}"
            dest = os.path.join(self.source_folder, "thirdparty", dir_name)
            shutil.rmtree(dest, ignore_errors=True)
            os.makedirs(dest, exist_ok=True)
            tmpfile = os.path.join(self.source_folder, f".{dir_name}.tar.gz")
            self.run(f'curl -L -o "{tmpfile}" "{url}" --connect-timeout 30 --max-time 90 -k -s')
            self.run(f'tar xzf "{tmpfile}" -C "{dest}" --strip-components=1')
            os.remove(tmpfile)

    def build(self):
        apply_conandata_patches(self)
        cc = "clang"
        cxx = "clang++"
        ar = "llvm-ar"
        ranlib = "llvm-ranlib"
        # Ensure bash and python3 are in PATH for font generation rules
        env_path = os.environ.get("PATH", "")
        if "/data/service/hnp/bin" not in env_path:
            env_path = f"/data/service/hnp/bin:{env_path}"
        env = dict(os.environ, PATH=env_path)
        make_cmd = (
            f"make CC={cc} CXX={cxx} AR={ar} RANLIB={ranlib} "
            f"HAVE_X11=no HAVE_GLUT=no shared=no build=release "
            f"HAVE_OBJCOPY=no -j1"
        )
        self.run(make_cmd, cwd=self.source_folder, env=env)
        make_extra = (
            f"make CC={cc} CXX={cxx} AR={ar} RANLIB={ranlib} "
            f"HAVE_X11=no HAVE_GLUT=no shared=no build=release "
            f"HAVE_OBJCOPY=no extra-apps -j1"
        )
        self.run(make_extra, cwd=self.source_folder, env=env)

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
        self.cpp_info.libs = ["mupdf", "mupdf-third"]
        self.cpp_info.includedirs = ["include"]
