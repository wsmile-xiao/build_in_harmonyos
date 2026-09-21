#!/usr/bin/env python3
"""Conan recipe - perceptualdiff 2.1 (CMake).

perceptualdiff compares two images using a perceptually based image metric
(Yee et al.). The upstream project builds a small C++ library (``pdiff``) plus
the ``perceptualdiff`` command line tool and ships a shell based regression
suite (``test/run_tests.bash``: 7 image pair expectations + 19 CLI behaviour
assertions) which is executed inside ``build()``.

Image IO is provided by FreeImage, which is published on the OHOS registry as
``freeimage/3.18.0`` (all codecs bundled in-tree), so no IO backend rewrite was
needed.

Upstream sources are used unmodified except for a single CMake portability
patch (modern CMake compatibility, Conan ``freeimage::freeimage`` imported
target, library/header install rules).
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, get


class PerceptualdiffConan(ConanFile):
    name = "perceptualdiff"
    version = "2.1"
    description = (
        "Image comparison utility based on a perceptually based image metric "
        "(Yee et al.); provides the pdiff library and the perceptualdiff CLI"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/myint/perceptualdiff"
    url = "https://github.com/myint/perceptualdiff"
    topics = ("image", "comparison", "perceptual-diff", "testing", "quality-assurance")
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        # The pdiff library is delivered as a static archive (Conan default).
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # Image loading/saving (PNG, TIFF, ...) goes through FreeImage.
        self.requires("freeimage/3.18.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()
        # Runtime environment (LD_LIBRARY_PATH for libfreeimage.so) is needed to
        # execute the upstream regression suite from build().
        VirtualRunEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        # test/run_tests.bash searches for the freshly built binary in
        # ../build, .. and ../obj* relative to the test directory, so stage the
        # binary in <source>/build before running the suite. Any failing
        # expectation makes the script exit non-zero (bash -e), which aborts
        # conan create.
        helper = os.path.join(self.source_folder, "build")
        os.makedirs(helper, exist_ok=True)
        copy(self, "perceptualdiff", src=self.build_folder, dst=helper, keep_path=False)
        staged = os.path.join(helper, "perceptualdiff")
        if not os.path.isfile(staged):
            raise ConanException("built binary not found at {}".format(staged))
        self.run("bash test/run_tests.bash", cwd=self.source_folder, env="conanrun")

    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["pdiff"]
        # The package also ships the upstream CLI, so declare the binary
        # directory explicitly (mirrors what is actually packaged).
        self.cpp_info.bindirs = ["bin"]
        # pdiff objects are compiled with OpenMP (-fopenmp=libomp, provided by
        # the OHOS toolchain), so consumers linking the static library must link
        # the OpenMP runtime as well.
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.exelinkflags = ["-fopenmp=libomp"]
            self.cpp_info.sharedlinkflags = ["-fopenmp=libomp"]
        self.cpp_info.set_property("cmake_file_name", "perceptualdiff")
        self.cpp_info.set_property("cmake_target_name", "perceptualdiff::perceptualdiff")
