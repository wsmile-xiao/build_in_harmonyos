#!/usr/bin/env python3
"""Conan recipe — mffm-fftw 1.7 (raw Makefile C++ wrapper over FFTW3).

MFFM FFTw C++ wrapper (upstream SourceForge project mffmfftwrapper,
author Matt Flax) is a small C++ class library that wraps FFTW3:
  * libfft.so.1    — realFFT / realFFTData / complexFFT
  * lib2Dfft.so.1  — real2DFFT
Headers are consumed as <mffm/*.H> (upstream installs them into
include/mffm/, examples include <mffm/realFFT.H>).

The upstream build is a plain Makefile with no configure script. It
hard-codes CC=g++, so this recipe drives the compile directly with the
Conan toolchain compiler (R33: never shell ${CXX}). FFTW3 is the only
dependency and comes from the ohpcd artifact registry (fftw/3.3.11).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class MffmFftwConan(ConanFile):
    name = "mffm-fftw"
    version = "1.7"
    description = (
        "MFFM FFTw C++ wrapper — realFFT/complexFFT/real2DFFT class "
        "library over FFTW3"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/mffmfftwrapper/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("fftw/3.3.11")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # The upstream tarball nests the sources under
        # home/flatmax/personal/research.flatmax/fft/. strip_root removes
        # the first level only, so promote the fft/ content to the root.
        src = self.source_folder
        nested = os.path.join(
            src, "flatmax", "personal", "research.flatmax", "fft"
        )
        if os.path.isdir(nested):
            for item in os.listdir(nested):
                shutil.move(
                    os.path.join(nested, item), os.path.join(src, item)
                )
            shutil.rmtree(os.path.join(src, "flatmax"))

    def _get_cxx(self):
        comp = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return comp.get("cpp", "clang++") if comp else "clang++"

    def _fftw_flags(self):
        """Return (-I, -L, -l) flags for the fftw dependency."""
        dep = self.dependencies["fftw"]
        root = dep.package_folder
        inc = " ".join(
            f"-I{os.path.join(root, d)}" for d in dep.cpp_info.includedirs
        )
        lib = " ".join(
            f"-L{os.path.join(root, d)}" for d in dep.cpp_info.libdirs
        )
        libs = " ".join(f"-l{l}" for l in dep.cpp_info.libs)
        return inc, lib, libs

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        cxx = self._get_cxx()
        inc, lib, libs = self._fftw_flags()
        cflags = f"-O3 -fPIC {inc}"

        # Compile the four translation units.
        for cc in ("realFFT.cc", "realFFTData.cc", "complexFFT.cc",
                   "real2DFFT.cc"):
            self.run(
                f'"{cxx}" {cflags} -c "{os.path.join(src, cc)}" '
                f'-o "{os.path.join(src, cc[:-3] + ".o")}"',
                env="conanbuild",
            )
        # libfft.so.1: realFFT + realFFTData + complexFFT
        objs_fft = " ".join(
            f'"{os.path.join(src, o)}"'
            for o in ("realFFT.o", "realFFTData.o", "complexFFT.o")
        )
        self.run(
            f'"{cxx}" -shared -Wl,-soname,libfft.so.1 '
            f'-o "{os.path.join(src, "libfft.so.1")}" {objs_fft} '
            f"{lib} {libs}",
            env="conanbuild",
        )
        # lib2Dfft.so.1: real2DFFT
        obj_2d = f'"{os.path.join(src, "real2DFFT.o")}"'
        self.run(
            f'"{cxx}" -shared -Wl,-soname,lib2Dfft.so.1 '
            f'-o "{os.path.join(src, "lib2Dfft.so.1")}" {obj_2d} '
            f"{lib} {libs}",
            env="conanbuild",
        )

    def package(self):
        src = self.source_folder
        pkg = self.package_folder

        # Shared libraries + unversioned symlinks for -lfft / -l2Dfft.
        libdir = os.path.join(pkg, "lib")
        os.makedirs(libdir, exist_ok=True)
        for base in ("libfft.so.1", "lib2Dfft.so.1"):
            shutil.copy2(os.path.join(src, base), os.path.join(libdir, base))
            link = os.path.join(libdir, base[:-2])  # libfft.so / lib2Dfft.so
            if not os.path.lexists(link):
                os.symlink(base, link)

        # Headers land in include/mffm/ (upstream include convention).
        for h in ("realFFT.H", "realFFTData.H", "complexFFT.H",
                  "real2DFFT.H"):
            copy(self, h, src=src, dst=os.path.join(pkg, "include", "mffm"),
                 keep_path=False)
        copy(self, "License.txt.gpl", src=src,
             dst=os.path.join(pkg, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "mffm-fftw")
        self.cpp_info.set_property("cmake_target_name", "mffm-fftw::mffm-fftw")
        self.cpp_info.libs = ["fft", "2Dfft"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.requires = ["fftw::fftw"]
