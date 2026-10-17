#!/usr/bin/env python3
"""Conan recipe for mupdf-gl 1.27.2 — MuPDF PDF viewer's GL rendering path.

This is a Path-B (knowledge-base extension) recipe. The package builds the
MuPDF core static libraries (libmupdf.a etc.) from the mupdf 1.27.2 source
(custom Makefile build, all thirdparty bundled), and carries the OHOS-specific
adaptation of the GL rendering path (platform/gl/gl-ui.c).

Key OHOS findings (see knowledge/drafts/DRAFT-mupdf-gl-1.27.2-immediate-mode-
unavailable-vao-rewrite.kv):

  * The OHOS GLES driver (Maleoon/FreeBox, EGL 1.4 vendor=OpenHarmony) does
    NOT expose the immediate-mode GL entry points:
        eglGetProcAddress("glBegin")  == NULL
        eglGetProcAddress("glEnd")    == NULL
        eglGetProcAddress("glVertex2f")   == NULL
        eglGetProcAddress("glTexCoord2f") == NULL
    Immediate mode is deprecated in ES 2.0 and removed in ES 3.0; the pure-ES
    OHOS driver has no fixed-function path. Modern VAO + shader pipeline
    (glGenVertexArrays / glVertexAttribPointer / glDrawArrays /
    glCreateShader) IS available via eglGetProcAddress.

  * mupdf-gl's platform/gl/gl-ui.c ui_draw_image() uses immediate mode
    (glBegin(GL_TRIANGLE_STRIP) / glVertex2f / glTexCoord2f / glEnd), so its
    GL rendering path is unavailable on OHOS. The patch carried here rewrites
    ui_draw_image() to the modern VAO + glDrawArrays pipeline.

Build notes:
  * HAVE_X11=no HAVE_GLUT=no — the GUI viewer executable is out of scope for
    this recipe. freeglut/3.6.0 (OHOS EGL-pbuffer adaptation) IS published to
    the registry, but the full viewer (platform/gl/*.c) still references
    fixed-function symbols that the OHOS GLES driver does not export at all
    (glNewList/glCallList display lists, glMatrixMode/glOrtho matrix stack,
    glyph/annotation immediate-mode drawing, ~13 undefined symbols total), so
    the viewer cannot link on OHOS until that fixed-function->GLES3 port is
    done (separate follow-up task; the symbol list is in the PR). This recipe
    ships the MuPDF core libs + the adapted GL rendering source (gl-ui.c +
    gl-app.h), and the test_package compiles the real patched gl-ui.c and
    drives ui_draw_image() end-to-end on a headless pbuffer ES 3.2 context.
  * shared=no — static build (R26).
  * `make libs` (not the default apps+libs) — builds only the static
    libraries, avoiding the mutool/muraster executable link that fails on
    OHOS because the bundled brotli .o files are not all archived into
    libmupdf-third.a by the stock Makefile. build() below repairs that by
    archiving the compiled brotli objects into libmupdf-third.a.
  * XLDFLAGS=-fuse-ld=ld — GNU ld (the OHOS SDK's lld depends on
    libxml2.so.16, unavailable on CI workers).
"""
import glob
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


# Submodule entries: directory name -> (GitHub repo, commit SHA or ref).
# The mupdf 1.27.2 GitHub archive does not include thirdparty submodules.
# The core thirdparty pins reuse the verified 1.25.1 set (compatible with
# 1.27.2, confirmed by a successful 1.27.2 build); brotli is new in 1.27.2
# (used for PDF stream decompression) and is taken from the Artifex fork.
SUBMODULES = {
    "jbig2dec":     ("jbig2dec",                 "1d1347e38a55e657dcc4c8f1c77bb3a26bfc9ff3"),
    "mujs":         ("mujs",                     "0df0707f2f10187127e36acfbc3ba9b9ca5b5cf0"),
    "freetype":     ("thirdparty-freetype2",     "de8b92dd7ec634e9e2b25ef534c54a3537555c11"),
    "gumbo-parser": ("thirdparty-gumbo-parser",  "289f3de61d9fc6a9812a6900c23e74c4d1fbde7d"),
    "harfbuzz":     ("thirdparty-harfbuzz",      "07c4f02f8c39f4227887249afbd193859da34a68"),
    "libjpeg":      ("thirdparty-libjpeg",       "7fe42a89507fac623fadf0c68fd1b10ebef66a23"),
    "lcms2":        ("thirdparty-lcms2",         "ab4547bd04a13590a6e72833f9928fc1c31da12e"),
    "openjpeg":     ("thirdparty-openjpeg",      "30664486071cd8712b17b7da71f1297693619100"),
    "zlib":         ("thirdparty-zlib",          "04f42ceca40f73e2978b50e93806c2a18c1281fc"),
    "curl":         ("thirdparty-curl",          "f43c6fbb2dbdf68dfdd0f0c3399e3711a621614a"),  # curl tarball fetched via tools.files.get, not the external curl command
    "freeglut":     ("thirdparty-freeglut",      "13ae6aa2c2f9a7b4266fc2e6116c876237f40477"),
    "extract":      ("extract",                  "ed5acb1397fc48f7e11804e9a72e37dd25a05c93"),
    "tesseract":    ("thirdparty-tesseract",     "bff8be466e9c26890c57106ffe57e8e5959690f3"),
    "leptonica":    ("thirdparty-leptonica",     "d2ed8c535bbc423f39f2b2d4c024d561405a46ef"),
    # New in mupdf 1.27.2 (PDF stream decompression). Pinned to the exact
    # gitlink commit of the mupdf 1.27.2 thirdparty/brotli submodule
    # (deterministic; resolves the former floating-master limitation).
    "brotli":       ("thirdparty-brotli",          "6e092ab79683949f432d1c0cab88effa683c90d7"),
}


class MupdfGlConan(ConanFile):
    name = "mupdf-gl"
    version = "1.27.2"
    description = ("MuPDF GL viewer rendering path: MuPDF core libs + OHOS "
                   "VAO-rewrite of platform/gl/gl-ui.c (immediate-mode GL is "
                   "unavailable on the OHOS GLES driver).")
    license = "AGPL-3.0"
    homepage = "https://mupdf.com/"
    url = "https://github.com/ArtifexSoftware/mupdf"

    # Static-only recipe: package() ships .a libs; mupdf is built with
    # shared=no so no system-name-collision .so is produced (R26).
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
        for dir_name, (repo, ref) in SUBMODULES.items():
            dest = os.path.join(self.source_folder, "thirdparty", dir_name)
            import shutil
            shutil.rmtree(dest, ignore_errors=True)
            os.makedirs(dest, exist_ok=True)
            # codeload.github.com is GitHub's official tarball endpoint (the
            # redirect target of github.com/<owner>/<repo>/archive/<ref>);
            # all refs are exact commits -> deterministic downloads.
            # filename= is required: conan get() picks the extraction format
            # from the filename suffix (codeload URL basenames are bare refs).
            get(self, url=f"https://codeload.github.com/ArtifexSoftware/{repo}/tar.gz/{ref}",
                filename=f"{dir_name}.tar.gz", strip_root=True, destination=dest)

    def build(self):
        apply_conandata_patches(self)
        cc = "clang"
        cxx = "clang++"
        ar = "llvm-ar"
        ranlib = "llvm-ranlib"
        # GNU ld instead of lld: the OHOS SDK's lld depends on libxml2.so.16,
        # unavailable on CI workers. GNU ld (binutils) has no such dependency.
        ldflags = "-fuse-ld=ld"
        # `libs` target: build only the static libraries (libmupdf.a,
        # libmupdf-third.a, libmupdf-pkcs7.a, libmupdf-threads.a). The default
        # target also builds the mutool/muraster executables, whose link fails
        # on OHOS because the stock Makefile does not archive all bundled
        # brotli .o files into libmupdf-third.a. We repair that below.
        make_cmd = (
            f"make libs CC={cc} CXX={cxx} AR={ar} RANLIB={ranlib} "
            f"HAVE_X11=no HAVE_GLUT=no shared=no build=release "
            f"HAVE_OBJCOPY=no XLDFLAGS={ldflags} -j2"
        )
        self.run(make_cmd, cwd=self.source_folder, env=["conanbuild"])

        # Repair: the stock mupdf Makefile compiles the bundled brotli
        # (thirdparty/brotli/c/{common,dec,enc}/*.c) into .o files but does not
        # archive all of them into libmupdf-third.a, leaving
        # BrotliDecoderEnsureStaticInit / kStaticDictionaryBuckets etc.
        # undefined for downstream executables that link libmupdf.a. Archive
        # the compiled brotli objects into libmupdf-third.a so the MuPDF core
        # links cleanly (the test_package links the core libs).
        third_lib = os.path.join(self.source_folder, "build", "release", "libmupdf-third.a")
        brotli_obj_dir = os.path.join(self.source_folder, "build", "release", "thirdparty", "brotli", "c")
        if os.path.isfile(third_lib) and os.path.isdir(brotli_obj_dir):
            brotli_objs = glob.glob(os.path.join(brotli_obj_dir, "**", "*.o"), recursive=True)
            if brotli_objs:
                self.run(f'"{ar}" q "{third_lib}" ' + " ".join(f'"{o}"' for o in brotli_objs),
                         env=["conanbuild"])
                self.run(f'"{ranlib}" "{third_lib}"', env=["conanbuild"])
                self.output.info(f"archived {len(brotli_objs)} brotli objects into libmupdf-third.a")

    def package(self):
        # Ship the MuPDF core static libraries + public headers.
        copy(self, "*.a", os.path.join(self.source_folder, "build", "release"),
             os.path.join(self.package_folder, "lib"))
        copy(self, "*.h", os.path.join(self.source_folder, "include"),
             os.path.join(self.package_folder, "include"))
        # Ship the adapted GL rendering source (the OHOS VAO rewrite of
        # platform/gl/gl-ui.c) so the knowledge is captured with the package.
        # gl-app.h is the companion header (struct texture + ui_* declarations)
        # needed to compile gl-ui.c standalone — the test_package does exactly
        # that (end-to-end verification of the patched ui_draw_image).
        copy(self, "gl-ui.c", os.path.join(self.source_folder, "platform", "gl"),
             os.path.join(self.package_folder, "include", "mupdf-gl-ohos"))
        copy(self, "gl-app.h", os.path.join(self.source_folder, "platform", "gl"),
             os.path.join(self.package_folder, "include", "mupdf-gl-ohos"))

    def package_info(self):
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include"]
        # `make libs` builds the core static libs (MUPDF_LIB + THIRD_LIB +
        # COMMERCIAL_LIBS). The threads/pkcs7 archives are separate Makefile
        # targets (not part of `libs`), so they are not shipped here; downstream
        # consumers of the full MuPDF toolchain use the complete mupdf package.
        self.cpp_info.libs = ["mupdf", "mupdf-third"]
