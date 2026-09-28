"""Conan recipe for libconvolve 0.0.8 (static library)."""

import os
import shlex

from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class LibconvolveConan(ConanFile):
    name = "libconvolve"
    version = "0.0.8"
    description = "Partitioned convolution library for audio applications"
    homepage = "https://sourceforge.net/projects/heaven/files/Audio%20Applications/Jack%20Related/jack_convolve/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    # Conservative package-level declaration: the bundled LICENSE is GPL-2.0.
    # Individual source headers instead say LGPL-2.1-or-later; see notes.md.
    license = "GPL-2.0-only"
    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        # convolve.h includes fftw3.h, so its headers must reach consumers.
        self.requires("fftw3f/3.3.10", transitive_headers=True, transitive_libs=True)
        self.requires("libsndfile/1.2.2", transitive_libs=True)
        self.requires("libsamplerate/0.2.2", transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler(self):
        executables = self.conf.get("tools.build:compiler_executables", default={})
        return executables.get("c", "cc")

    def build(self):
        includes = []
        for dependency in self.dependencies.values():
            for directory in dependency.cpp_info.includedirs:
                includes.append("-I" + shlex.quote(directory))

        # libDSP is optional upstream. C_CMUL selects its portable C fallback.
        # GNU89 inline semantics emit complex_mul from the legacy source; C99
        # semantics leave an unresolved reference in the static archive.
        flags = " ".join(
            [
                "-O2",
                "-fPIC",
                "-DC_CMUL",
                "-D_POSIX_C_SOURCE=200112L",
                "-fgnu89-inline",
                "-include stdlib.h",
                "-include fftw3.h",
                "-include complex_mul.h",
            ]
            + includes
        )
        compiler = shlex.quote(self._compiler())
        source = shlex.quote(self.source_folder)
        self.run(
            "make -B -j1 -C {} libconvolve.a CC={} COMPILE_FLAGS={}".format(
                source, compiler, shlex.quote(flags)
            )
        )

        # The sole upstream test is not a default Make target, and its Makefile
        # rule names a nonexistent convolve.c. Compile the original test source
        # unchanged with its missing header injected at compile time.
        test_exe = shlex.quote(os.path.join(self.build_folder, "ringbuffer_test"))
        self.run(
            "{} -O2 -include ringbuffer.h {} ringbuffer_test.c ringbuffer.c -o {}".format(
                compiler, " ".join(includes), test_exe
            ),
            cwd=self.source_folder,
        )
        self.run("{} > upstream-ringbuffer-test.log".format(test_exe), cwd=self.build_folder)
        self.output.info("Upstream ringbuffer_test: 1/1 exited successfully")

    def package(self):
        copy(self, "convolve.h", self.source_folder, os.path.join(self.package_folder, "include"))
        copy(self, "libconvolve.a", self.source_folder, os.path.join(self.package_folder, "lib"))
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["convolve"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("cmake_file_name", "libconvolve")
        self.cpp_info.set_property("cmake_target_name", "libconvolve::libconvolve")
