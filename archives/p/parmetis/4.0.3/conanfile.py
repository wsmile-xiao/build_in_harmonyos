#!/usr/bin/env python3
"""Conan recipe for ParMETIS 4.0.3 — parallel graph partitioning library.

ParMETIS is the parallel extension of METIS, requiring MPI for inter-process
communication. This recipe bundles METIS and GKlib from the upstream source
tree (no external METIS dependency).

R32: settings.os check uses `in ("Linux", "OHOS")`
R33: build() does not depend on undefined shell environment variables
"""
from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
import os


class ParmetisConan(ConanFile):
    name = "parmetis"
    version = "4.0.3"
    description = "ParMETIS - Parallel Graph Partitioning and Fill-reducing Matrix Ordering"
    license = "University of Minnesota (free for research/education)"
    homepage = "https://karypis.github.io/glaros/software/parmetis/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("open-mpi/5.0.10")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        openmpi = self.dependencies["open-mpi"]
        mpi_root = openmpi.package_folder
        mpi_include = os.path.join(mpi_root, "include")
        mpi_lib = os.path.join(mpi_root, "lib")
        tc.cache_variables["GKLIB_PATH"] = os.path.join(self.source_folder, "metis", "GKlib")
        tc.cache_variables["METIS_PATH"] = os.path.join(self.source_folder, "metis")
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.cache_variables["SHARED"] = self.options.shared
        # MPI: use default clang compiler + explicit MPI paths via cache
        # variables that the upstream CMakeLists.txt already respects.
        #   include_directories(${MPI_INCLUDE_PATH})  — root CMakeLists.txt
        #   target_link_libraries(... ${MPI_LIBRARIES})  — libparmetis
        #   set_target_properties(... LINK_FLAGS "${MPI_LINK_FLAGS}")
        # Additionally, CMAKE_EXE_LINKER_FLAGS ensures programs find -lmpi
        # (LINK_FLAGS on a static lib target does not propagate to exes).
        tc.cache_variables["MPI_INCLUDE_PATH"] = mpi_include
        tc.cache_variables["MPI_LIBRARIES"] = "mpi"
        tc.cache_variables["MPI_LINK_FLAGS"] = f"-L{mpi_lib}"
        tc.cache_variables["CMAKE_EXE_LINKER_FLAGS"] = f"-L{mpi_lib}"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # ParMETIS's CMake goes directly into metis/libmetis without going
        # through metis/CMakeLists.txt, so metis.h and libmetis.a are never
        # installed. Copy them manually from the build/source trees.
        copy(self, "metis.h",
             src=os.path.join(self.source_folder, "metis", "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "libmetis.a",
             src=os.path.join(self.build_folder, "libmetis"),
             dst=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["parmetis", "metis"]
        self.cpp_info.includedirs = ["include"]

