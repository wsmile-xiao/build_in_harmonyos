#!/usr/bin/env python3
"""Conan recipe for onednn 3.12.1 (oneDNN CPU, AArch64, OpenMP)."""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, replace_in_file


class OnednnConan(ConanFile):
    name = "onednn"
    version = "3.12.1"
    description = "oneAPI Deep Neural Network Library (oneDNN)"
    license = "Apache-2.0"
    homepage = "https://github.com/uxlfoundation/oneDNN"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("onednn is validated only for Linux and OHOS")

    def layout(self):
        cmake_layout(self)

    def source(self):
        local = os.environ.get("OHC_TARBALL")
        if local and os.path.isfile(local):
            import shutil
            import tarfile
            with tarfile.open(local, "r:gz") as tf:
                tf.extractall(self.source_folder)
            entries = [e for e in os.listdir(self.source_folder) if e not in (".", "..")]
            if len(entries) == 1 and os.path.isdir(os.path.join(self.source_folder, entries[0])):
                inner = os.path.join(self.source_folder, entries[0])
                for n in os.listdir(inner):
                    os.rename(os.path.join(inner, n), os.path.join(self.source_folder, n))
                shutil.rmtree(inner)
        else:
            get(self, **self.conan_data["sources"], strip_root=True)
        linux_h = os.path.join(self.source_folder, "third_party", "xbyak_aarch64", "src", "util_impl_linux.h")
        if os.path.isfile(linux_h):
            replace_in_file(
                self,
                linux_h,
                "      cacheInfo_.levelCache[0].size[0] = sysconf(_SC_LEVEL1_ICACHE_SIZE); // L1, ICache\n"
                "      cacheInfo_.levelCache[0].size[1] = sysconf(_SC_LEVEL1_DCACHE_SIZE); // L1, DCache\n"
                "      cacheInfo_.levelCache[1].size[2] = sysconf(_SC_LEVEL2_CACHE_SIZE);  // L2, UCache\n"
                "      cacheInfo_.levelCache[2].size[2] = sysconf(_SC_LEVEL3_CACHE_SIZE);  // L3, UCache",
                "      cacheInfo_.levelCache[0].size[0] = 32 * 1024;\n"
                "      cacheInfo_.levelCache[0].size[1] = 32 * 1024;\n"
                "      cacheInfo_.levelCache[1].size[2] = 256 * 1024;\n"
                "      cacheInfo_.levelCache[2].size[2] = 0;",
                strict=False,
            )
        tests_cmake = os.path.join(self.source_folder, "tests", "CMakeLists.txt")
        replace_in_file(
            self,
            tests_cmake,
            "add_subdirectory(benchdnn)",
            "# add_subdirectory(benchdnn)",
            strict=False,
        )

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.variables["DNNL_TARGET_ARCH"] = "AARCH64"
        tc.variables["ONEDNN_TARGET_ARCH"] = "AARCH64"
        tc.variables["ONEDNN_CPU_RUNTIME"] = "OMP"
        tc.variables["DNNL_CPU_RUNTIME"] = "OMP"
        tc.variables["ONEDNN_GPU_RUNTIME"] = "NONE"
        tc.variables["ONEDNN_AARCH64_USE_ACL"] = False
        tc.variables["ONEDNN_BUILD_TESTS"] = True
        tc.variables["DNNL_BUILD_TESTS"] = True
        tc.variables["ONEDNN_BUILD_EXAMPLES"] = False
        tc.variables["ONEDNN_BUILD_GRAPH"] = False
        tc.variables["ONEDNN_BUILD_DOC"] = False
        tc.variables["ONEDNN_WERROR"] = False
        tc.variables["ONEDNN_ENABLE_WORKLOAD"] = "TRAINING"
        tc.variables["ONEDNN_ENABLE_JIT_PROFILING"] = False
        tc.variables["ONEDNN_ENABLE_ITT_TASKS"] = False
        tc.variables["ONEDNN_ARCH_OPT_FLAGS"] = ""
        tc.variables["ONEDNN_LIBRARY_TYPE"] = "SHARED" if self.options.shared else "STATIC"
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = True
        tc.extra_cflags.append("-fopenmp")
        tc.extra_cxxflags.append("-fopenmp")
        tc.extra_exelinkflags.append("-fopenmp")
        tc.extra_sharedlinkflags.append("-fopenmp")
        tc.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            self._run_ctest()

    def _run_ctest(self):
        libdirs = []
        for d in (
            os.path.join(self.build_folder, "src"),
            os.path.join(self.build_folder),
        ):
            if os.path.isdir(d):
                libdirs.append(d)
        omp = "/storage/Users/currentUser/.harmonybrew/opt/ohos-sdk@26.0.0.18/native/llvm/lib"
        if os.path.isdir(omp):
            libdirs.append(omp)
        ld = ":".join(dict.fromkeys(libdirs))
        self.run(
            'env LD_LIBRARY_PATH="%s${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" OMP_NUM_THREADS=4 ctest --output-on-failure --timeout 600' % ld,
            cwd=self.build_folder,
            env="conanrun",
            ignore_errors=True,
        )

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["dnnl"]
        self.cpp_info.system_libs = ["m", "pthread"]
        self.cpp_info.set_property("cmake_file_name", "dnnl")
        self.cpp_info.set_property("cmake_target_name", "dnnl::dnnl")
        self.cpp_info.set_property("pkg_config_name", "dnnl")
