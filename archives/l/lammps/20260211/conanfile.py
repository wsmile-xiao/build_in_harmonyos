#!/usr/bin/env python3
"""Conan recipe - lammps 20260211 (CMake, build tree lives in cmake/)."""

import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (apply_conandata_patches, chmod, export_conandata_patches,
                               get, save)


class LammpsConan(ConanFile):
    name = "lammps"
    version = "20260211"
    package_type = "application"
    license = "GPL-2.0-only"
    homepage = "https://www.lammps.org"
    url = "https://github.com/lammps/lammps"
    description = ("Large-scale Atomic/Molecular Massively Parallel Simulator "
                   "(molecular dynamics code)")
    topics = ("molecular-dynamics", "simulation", "physics", "cli")
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*", "conandata.yml"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        data = self.conan_data["sources"][self.version]
        # `filename` is mandatory for the extension-less codeload URL: without it
        # conan mis-detects the payload as a zip and strip_root fails.
        keys = tuple(k for k in ("url", "sha256", "filename") if k in data)
        get(self, **{k: data[k] for k in keys}, strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            # CMake ships no HarmonyOS platform module and OHOS clang is
            # Linux-compatible, so drive it in Linux mode (same solution that
            # afmize/2.0.2 uses; no platform macro is injected -> PF5 clean).
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # The CMake project root of this release is cmake/, not the source
        # root; keep every generated file out of the source tree.
        tc.cache_variables["CMAKE_EXPORT_COMPILE_COMMANDS"] = "OFF"
        # Stock package set: a plain CMake configure enables no PKG_* at all.
        # Anything that would pull an external library or a download is closed
        # explicitly so the build is hermetic (path A, no Conan dependencies).
        tc.cache_variables["BUILD_MPI"] = "OFF"
        tc.cache_variables["BUILD_OMP"] = "OFF"
        tc.cache_variables["BUILD_SHARED_LIBS"] = "OFF"
        tc.cache_variables["BUILD_TOOLS"] = "OFF"
        tc.cache_variables["BUILD_LAMMPS_GUI"] = "OFF"
        tc.cache_variables["WITH_SWIG"] = "OFF"
        tc.cache_variables["LAMMPS_INSTALL_RPATH"] = "OFF"
        tc.cache_variables["DOWNLOAD_POTENTIALS"] = "OFF"
        tc.cache_variables["USE_INTERNAL_LINALG"] = "ON"
        # Every name below is cross-checked against upstream's own
        # STANDARD_PACKAGES/SUFFIX_PACKAGES pools (cmake/CMakeLists.txt builds
        # `option(PKG_${PKG} ...)` dynamically, so grepping for PKG_<NAME> would
        # over-rate coverage). 30 names were listed before; `USER-INTEL` was
        # dropped because this release defines no such package (the real one is
        # plain `INTEL`, already in the list).
        for pkg in ("GPU", "KOKKOS", "OPENMP", "INTEL",
                    "MOLFILE", "NETCDF", "VTK", "H5MD", "ADIOS", "KIM",
                    "COMPRESS", "GRAPHICS", "PYTHON", "MDI", "PLUMED",
                    "QMMM", "SCAFACOS", "MACHDYN", "MBX", "COLVARS",
                    "LEPTON", "ML-IAP", "ML-HDNNP", "ML-PACE", "ML-QUIP",
                    "VORONOI", "KSPACE", "EXTRA-COMMAND", "DPD-SMOOTH"):
            tc.cache_variables["PKG_" + pkg] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        # cmake/CMakeLists.txt is the project root of this tag.
        cmake.configure(build_script_folder="cmake")
        cmake.build(cli_args=["--parallel", "1"], build_tool_args=["-j1"])

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # K0 (2026-09-25): the package name differs from the upstream main
        # command name (lammps vs lmp) and upstream only implements the
        # single-dash -h (src/lammps.cpp:490 rejects --help/--version, rc=1).
        # Ship a package-named entry point that answers --help/--version with
        # rc=0 without touching upstream argument parsing or the lmp binary.
        wrapper = "\n".join([
            "#!/bin/sh",
            "# Package-named entry point for lammps (K0 directive, 2026-09-25).",
            "# Upstream lmp only accepts single-dash -h; --help delegates to it,",
            "# --version reports the adapted version, everything else passes through.",
            'case "${1-}" in',
            "  --help)",
            '    exec "$(dirname "$0")/lmp" -h ;;',
            "  --version)",
            '    echo "lammps 20260211 (patch_11Feb2026)"',
            "    exit 0 ;;",
            "  *)",
            '    exec "$(dirname "$0")/lmp" "$@" ;;',
            "esac",
            "",
        ])
        wrap_path = os.path.join(self.package_folder, "bin", "lammps")
        save(self, wrap_path, wrapper)
        chmod(self, wrap_path, execute=True)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", self.package_folder + "/bin")
