#!/usr/bin/env python3
"""Conan recipe — faiss 1.15.0 (CMake)"""
import os
import shutil
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, copy


class FaissConan(ConanFile):
    name = "faiss"
    version = "1.15.0"
    description = "A library for efficient similarity search and clustering of dense vectors"
    license = "MIT"
    homepage = "https://github.com/facebookresearch/faiss"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)
        # Also export the BLAS stub source (not a patch; bundled alongside)
        copy(self, "blas_stub.c", src=os.path.join(self.recipe_folder, "patches"),
             dst=self.export_sources_folder)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # faiss 1.15.0 build options — CPU-only OHOS arm64 build
        tc.variables["FAISS_ENABLE_GPU"] = False
        tc.variables["FAISS_ENABLE_MKL"] = False
        tc.variables["FAISS_ENABLE_SVS"] = False
        tc.variables["FAISS_ENABLE_PYTHON"] = False
        tc.variables["FAISS_ENABLE_METAL"] = False
        tc.variables["FAISS_ENABLE_C_API"] = False
        tc.variables["FAISS_ENABLE_EXTRAS"] = False
        tc.variables["FAISS_USE_LTO"] = False
        tc.variables["FAISS_OPT_LEVEL"] = "generic"
        tc.variables["BUILD_TESTING"] = False
        tc.variables["CMAKE_LINK_WHAT_YOU_USE"] = False
        # R26/R40: CMakeToolchain maps OHOS→CMAKE_SYSTEM_NAME=HarmonyOS, but CMake
        # has no Platform/HarmonyOS module so project() sets CMAKE_SYSTEM_PROCESSOR
        # to "unknown". faiss SIMD selection regex-matches CMAKE_SYSTEM_PROCESSOR
        # against (aarch64|arm64|ARM64); without the fix 10 ARM NEON TU are missing
        # from libfaiss.a. The tc.variables CACHE set below is overwritten by
        # project(); the fix-neon-simd-on-ohos.patch (applied in build()) forces
        # CMAKE_SYSTEM_PROCESSOR=aarch64 immediately after project() returns.
        # The CACHE value is kept as a belt-and-suspenders hint for non-project
        # consumers (e.g. CMakePackageCheckHelpers).
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # Point BLAS/LAPACK to the static stub (OpenBLAS not available on OHOS).
        # faiss 1.15.0 honors user-provided BLAS_LIBRARIES/LAPACK_LIBRARIES.
        stub_lib = os.path.join(self.build_folder, "libblas_stub.a")
        tc.variables["BLAS_LIBRARIES"] = stub_lib
        tc.variables["LAPACK_LIBRARIES"] = stub_lib
        tc.generate()

    def _get_toolchain_tools(self):
        """R33: Get compiler/archiver from Conan conf, not hardcoded paths or
        shell env vars. Falls back to plain 'clang'/'llvm-ar' so the recipe is
        self-contained on the OHOS toolchain."""
        comp_execs = self.conf.get("tools.build:compiler_executables",
                                   default={}, check_type=dict) or {}
        cc = comp_execs.get("c", "clang")
        ar = comp_execs.get("ar")
        if not ar:
            cc_dir = os.path.dirname(cc)
            if cc_dir:
                ar_cand = os.path.join(cc_dir, "llvm-ar")
                if os.path.isfile(ar_cand):
                    ar = ar_cand
        if not ar:
            ar = "llvm-ar"
        return cc, ar

    def build(self):
        # Apply any conandata patches (none currently, but required by G1).
        apply_conandata_patches(self)

        # Build BLAS stub (OpenBLAS not available on OHOS). The stub provides
        # functional sgemm_/dgemm_/sgemv_ plus link-only LAPACK stubs.
        # export_sources() copies blas_stub.c to export_sources_folder; after
        # source() extracts the upstream tarball, the stub lives next to the
        # extracted sources (Conan copies export_sources into source_folder).
        stub_src = os.path.join(self.source_folder, "blas_stub.c")
        if not os.path.exists(stub_src):
            # Fallback: recipe_folder/patches (local dev / non-export context)
            stub_src = os.path.join(self.recipe_folder, "patches", "blas_stub.c")
        cc, ar = self._get_toolchain_tools()
        self.run(f'"{cc}" -c -O2 "{stub_src}" -o "{self.build_folder}/blas_stub.o"')
        self.run(f'"{ar}" rcs "{self.build_folder}/libblas_stub.a" "{self.build_folder}/blas_stub.o"')

        cmake = CMake(self)
        cmake.configure()
        cmake.build(target="faiss")

        # Merge BLAS stub into libfaiss.a so all symbols are in one library.
        libfaiss = os.path.join(self.build_folder, "faiss", "libfaiss.a")
        if os.path.exists(libfaiss):
            self.run(f'"{ar}" rs "{libfaiss}" "{self.build_folder}/blas_stub.o"')

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Remove FAISS-installed CMake config to avoid conflict with Conan CMakeDeps
        for d in ["lib/cmake/faiss", "share"]:
            full = os.path.join(self.package_folder, d)
            if os.path.isdir(full):
                shutil.rmtree(full)

    def package_info(self):
        self.cpp_info.libs = ["faiss"]
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["omp", "pthread"]
        self.cpp_info.set_property("cmake_file_name", "faiss")
        self.cpp_info.set_property("cmake_target_name", "faiss::faiss")
        # OpenMP runtime: derive libomp.so path from Conan conf compiler path
        comp_execs = self.conf.get("tools.build:compiler_executables",
                                   default={}, check_type=dict) or {}
        cc = comp_execs.get("c", "")
        if cc:
            cc_bindir = os.path.dirname(os.path.realpath(cc))
            omp_dir = os.path.normpath(
                os.path.join(cc_bindir, "..", "lib", "aarch64-linux-ohos"))
            if os.path.isdir(omp_dir):
                self.runenv_info.append_path("LD_LIBRARY_PATH", omp_dir)
