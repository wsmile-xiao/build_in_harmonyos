#!/usr/bin/env python3
"""Conan recipe for liboglappth 1.0.0 — OpenGL utility class library.

liboglappth (part of the ghemical project) provides C++ classes for building
OpenGL scenes: cameras, lights, transformable objects and small vec/matrix
templates. It is a plain static/shared library with NO test suite upstream
(only a `tests/` directory with a manual demo program, no `make check`).

OHOS adaptation notes
=====================
* GL discovery: the configure script only checks that <GL/gl.h> and
  <GL/glu.h> compile (the link check is commented out upstream). gl4es/1.1.6
  provides both headers (and libGL.so with the 25 fixed-pipeline GL symbols
  liboglappth leaves undefined), so no precious-variable overrides are needed
  — AutotoolsDeps puts the gl4es include/lib dirs on the command line.
* GLU implementations: gl4es only *declares* gluLookAt/gluPerspective/
  gluPickMatrix in <GL/glu.h>; it ships no libGLU. liboglappth's Makefile.am
  has LIBADD commented out, so all GL/GLU symbols are intentionally left
  undefined in the produced library — but the undefined glu* symbols would
  break every static-linked consumer at link time. glu_shim.cpp (exported
  from the recipe) implements the three functions on top of plain GL calls
  and is compiled into the library.
* patches/0001-config.sub.patch teaches the vendored 2011 config.sub about
  aarch64 and -linux-ohos; the dual triplet is passed explicitly to pin
  autoconf into cross mode (conftest binaries cannot run in the sandbox).
* Upstream ships no test suite at all (see test_package/MANIFEST.yml); the
  consumer tests in test_package/ exercise the real public API instead.
"""
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
    rmdir,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class LibOglappthConan(ConanFile):
    name = "liboglappth"
    version = "1.0.0"
    description = (
        "OpenGL utility class library from the ghemical project: cameras, "
        "lights, transformable scene objects and vector templates"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://www.bioinformatics.org/ghemical/liboglappth/"
    topics = ("opengl", "camera", "scene-graph", "ghemical", "ohos")

    exports = "glu_shim.cpp"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "glu_shim.cpp", src=self.recipe_folder, dst=self.export_sources_folder)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # gl4es translates desktop GL 1.5 calls to GLES3; provides <GL/gl.h>,
        # <GL/glu.h> declarations and libGL.so (fixed-pipeline symbols).
        self.requires("gl4es/1.1.6")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            [
                "--enable-shared" if self.options.shared else "--disable-shared",
                "--disable-static" if self.options.shared else "--enable-static",
            ]
        )
        if self.settings.os == "OHOS":
            # The vendored 2011 config.guess cannot identify the build host and
            # freshly linked conftest binaries cannot run in the sandbox: pin
            # both triplets to force autoconf cross-compiling mode.
            tc.configure_args.extend(
                [
                    "--build=x86_64-unknown-linux-gnu",
                    "--host=aarch64-unknown-linux-ohos",
                ]
            )
        tc.generate()
        AutotoolsDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        # Compile the GLU shim into the build tree; it is picked up by
        # `make` through an amended liboglappth_la_SOURCES below.
        shim = os.path.join(self.export_sources_folder, "glu_shim.cpp")
        copy(self, "glu_shim.cpp", src=self.export_sources_folder,
             dst=os.path.join(self.source_folder, "src"))
        autotools = Autotools(self)
        autotools.configure()
        # Amend the Makefile so the shim object lands inside the library
        # (LIBADD is commented out upstream and regenerating autotools files
        # is not worth it — a single substitution achieves the same result).
        makefile_in = os.path.join(self.source_folder, "src", "Makefile.in")
        with open(makefile_in) as f:
            content = f.read()
        content = content.replace(
            "liboglappth_la_SOURCES = \\",
            "liboglappth_la_SOURCES = \\\n\tglu_shim.cpp \\",
        )
        content = content.replace(
            "am_liboglappth_la_OBJECTS = base_app.lo base_wnd.lo base_wcl.lo \\",
            "am_liboglappth_la_OBJECTS = glu_shim.lo base_app.lo base_wnd.lo base_wcl.lo \\",
        )
        with open(makefile_in, "w") as f:
            f.write(content)
        autotools.make()

    def package(self):
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        Autotools(self).install()
        # libtool archives hold absolute build paths and must not leak out
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.libs = ["oglappth"]
        self.cpp_info.set_property("cmake_file_name", "liboglappth")
        self.cpp_info.set_property("cmake_target_name", "liboglappth::liboglappth")
        self.cpp_info.set_property("pkg_config_name", "liboglappth")
        # Headers are included by consumers as <oglv3d.h> etc. (the upstream
        # .pc uses -I{includedir}/oglappth); gl4es provides <GL/gl.h>+<GL/glu.h>.
        self.cpp_info.includedirs = ["include", os.path.join("include", "oglappth")]
