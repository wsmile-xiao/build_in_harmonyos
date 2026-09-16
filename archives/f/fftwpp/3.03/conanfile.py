#!/usr/bin/env python3
"""Conan recipe — fftwpp 3.03 (header-only C++ wrapper for FFTW3).

FFTW++ (http://fftwpp.sourceforge.net) is a header/MPI transpose for
FFTW3. The 3.03 distribution ships:
  * public headers: fftw++.h, parallel.h, align.h, seconds.h,
    statistics.h, utils.h, Complex.h, Array.h, convolve.h, cmult-sse2.h
  * companion translation units that consumers must compile and link:
    fftw++.cc, parallel.cc (Array.cc / Complex.cc are optional helpers)

The upstream CMakeLists only drives tests/examples compilation (no
install rules), so this recipe packages headers + the two required
.cc sources directly, letting consumers either include headers only
or build the .cc files with `self.cpp_info.resdirs`-style access.

Multithreading is intentionally disabled (FFTWPP_SINGLE_THREAD):
  * fftw/3.3.10 on OHOS ships a serial libfftw3 (no fftw_init_threads)
  * OHOS SDK libomp.so only lives inside the SDK tree and gets baked
    into RUNPATH (see archives/f/fftw/3.3.10.2 notes)
The upstream README documents -DFFTWPP_SINGLE_THREAD as the official
single-thread switch; parallel.h then guards all omp.h usage.
"""
from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout
import os

required_conan_version = ">=2.0"


class FftwppConan(ConanFile):
    name = "fftwpp"
    version = "3.03"
    package_type = "header-library"

    description = (
        "FFTW++: header-only C++ wrapper for FFTW3 (1D/2D/3D FFTs, "
        "implicit dealiasing and convolutions, optional MPI transposes)"
    )
    homepage = "https://github.com/dealias/fftwpp"
    license = "GPL-3.0-or-later", "LGPL-3.0-or-later"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        # fftw/3.3.10 on OHOS: serial libfftw3.so with full symbol
        # coverage for every fftw* API fftwpp uses (verified by nm).
        self.requires("fftw/3.3.10")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        # No toolchain needed: nothing is compiled in this package.
        pass

    def build(self):
        pass

    def package(self):
        headers = [
            "fftw++.h", "parallel.h", "align.h", "seconds.h",
            "statistics.h", "utils.h", "Complex.h", "Array.h",
            "convolve.h", "cmult-sse2.h",
        ]
        for h in headers:
            copy(self, h, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "include", "fftwpp"))
        # Companion translation units: consumers compile these together
        # with their own sources (upstream examples do exactly that:
        # `g++ example0.cc ../fftw++.cc -lfftw3`).
        for cc in ["fftw++.cc", "parallel.cc", "Array.cc", "Complex.cc"]:
            copy(self, cc, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "src", "fftwpp"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "LICENSE.LESSER", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "fftwpp")
        self.cpp_info.set_property("cmake_target_name", "fftwpp::fftwpp")
        self.cpp_info.includedirs = ["include"]
        # headers live in include/fftwpp/, so consumers do
        # #include <fftwpp/fftw++.h>; srcdirs carries the .cc companions
        # (upstream usage: g++ app.cc <pkg>/src/fftwpp/fftw++.cc -lfftw3).
        self.cpp_info.srcdirs = ["src"]
        # Single-thread mode: documented upstream switch; matches the
        # serial libfftw3 in fftw/3.3.10 and avoids OHOS OpenMP RUNPATH
        # issues (libomp.so only exists inside the OHOS SDK tree).
        self.cpp_info.defines = ["FFTWPP_SINGLE_THREAD"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
