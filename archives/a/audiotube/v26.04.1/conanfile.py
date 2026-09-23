#!/usr/bin/env python3
"""Conan recipe for audiotube v26.04.1 — KDE YouTube Music client (ytm library).

Build: CMake with OHOS_MINIMAL_BUILD=ON → libytm.a static library + ytmusic.h header
Deps:  ECM (Conan), pybind11 (pip, header-only)

The full audiotube GUI requires Qt6Qml/Quick/KF6Kirigami which are not available
on OHOS. The OHOS_MINIMAL_BUILD option builds only the ytm static library
(pybind11::embed wrapper for ytmusicapi).

pybind11 is installed via pip because it is not available as a Conan package
in the OHOS registry. It is header-only (with CMake config), so pip install
provides both the headers and the cmake configuration.

See: https://github.com/KDE/audiotube
"""
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class AudiotubeConan(ConanFile):
    name = "audiotube"
    version = "v26.04.1"
    description = "KDE YouTube Music client — ytm C++ static library (pybind11 wrapper for ytmusicapi)"
    license = "BSD-2-Clause"
    homepage = "https://github.com/KDE/audiotube"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("ecm/6.20.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ensure_pybind11(self):
        """Ensure pybind11 is installed via pip and return its CMake dir.

        Always uses sys.executable (the interpreter running conan) for BOTH
        the pip install and the import probe. Resolving `pip3` and `python3`
        separately from PATH can pick different interpreters on CI workers,
        which installs pybind11 into a site-packages directory that the
        probed interpreter never sees (observed in build #49384).
        """
        def _get_cmake_dir():
            try:
                result = subprocess.run(
                    [sys.executable, "-c", "import pybind11; print(pybind11.get_cmake_dir())"],
                    capture_output=True, text=True, timeout=30,
                )
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip()
            except Exception:
                pass
            return None

        cmake_dir = _get_cmake_dir()
        if not cmake_dir:
            self.run(f'"{sys.executable}" -m pip install pybind11==3.0.4')
            cmake_dir = _get_cmake_dir()
        return cmake_dir

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["OHOS_MINIMAL_BUILD"] = "ON"
        pybind11_dir = self._ensure_pybind11()
        if not pybind11_dir:
            raise ConanInvalidConfiguration(
                "pybind11 CMake config dir not found even after "
                '"pip install pybind11==3.0.4"; cannot point CMake at '
                "pybind11Config.cmake")
        tc.variables["pybind11_DIR"] = pybind11_dir
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build(target="ytm")

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["ytm"]
