#!/usr/bin/env python3
"""Conan recipe — libomptarget-rtl 18.1.8 (CMake, HarmonyOS PC aarch64)

LLVM OpenMP offloading RTL plugin library (openmp/libomptarget plugins-nextgen,
the libomptarget.rtl.aarch64.so generic-ELF64 offloading plugin). Packaging
target is the RTL plugin, mirroring the Alpine libomptarget-rtl package.

Built standalone from the official openmp-18.1.8.src.tar.xz with
OPENMP_STANDALONE_BUILD=ON + OPENMP_ENABLE_LIBOMPTARGET=ON, consuming the
already-published llvm/20.1.0 package (LLVMConfig.cmake + libLLVM) as the
required LLVM dependency (the RTL plugin links libLLVM.so.20.1; the
libomptarget 18.1.8 sources compile against LLVM 20.1.0 headers/libs).

Key adaptations for HarmonyOS PC (aarch64):
- Platform/HarmonyOS.cmake (include Platform/Linux) injected into the
  generators dir so CMake recognises the "HarmonyOS" system and sets
  CMAKE_SHARED_LIBRARY_SONAME_*_FLAG (without it SONAME is missing and
  DT_NEEDED entries end up build-tree relative).
- CMAKE_SYSTEM_NAME=HarmonyOS + CMAKE_SYSTEM_PROCESSOR=aarch64 so the
  aarch64 generic-ELF64 offloading plugin is built.
- CMAKE_DISABLE_FIND_PACKAGE_FFI=TRUE: force the self-contained
  "dlopened libffi" plugin mode (no system libffi dependency; a system
  libffi on the build host would otherwise switch the plugin to
  link-against-libffi mode and fail on ffi.h include path).
- patches/: kmp.h pthread_cancel capability guard (E081); libomp
  SOVERSION; aarch64 plugin HarmonyOS platform gate; JIT.cpp LLVM20 API
  fix (LLVMTargetMachine removed).
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, save, rm
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LibomptargetRtlConan(ConanFile):
    name = "libomptarget-rtl"
    version = "18.1.8"
    description = "LLVM OpenMP offloading RTL plugin library (libomptarget.rtl.*.so)"
    license = "Apache-2.0 WITH LLVM-exception"
    homepage = "https://openmp.llvm.org"
    url = "https://github.com/llvm/llvm-project"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # The RTL plugin links libLLVM.so.20.1 (NEEDED). llvm/18.1.8 is not
        # published in the ohpcd repository; llvm/20.1.0 is published and the
        # libomptarget 18.1.8 sources compile+link against it (verified).
        self.requires("llvm/20.1.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # The official openmp-18.1.8.src.tar.xz contains only the openmp/
        # tree; the LLVM root cmake modules referenced by
        # LLVM_COMMON_CMAKE_UTILS (../cmake) are not present. Provide the two
        # modules actually included by the openmp build here (same approach as
        # the libomp/15.0.4 and libomptarget/18.1.8 recipes).
        extend_path_cmake = (
            '# Extend the path in `base_path` with the path in `current_segment`, returning\n'
            '# the result in `joined_path`. If `current_segment` is an absolute path then\n'
            '# just return it, in effect overriding `base_path`, and issue a warning.\n'
            '#\n'
            '# Note that the code returns a relative path (avoiding introducing leading\n'
            '# slashes) if `base_path` is empty.\n'
            'function(extend_path joined_path base_path current_segment)\n'
            '  if("${current_segment}" STREQUAL "")\n'
            '    set(temp_path "${base_path}")\n'
            '  elseif("${base_path}" STREQUAL "")\n'
            '    set(temp_path "${current_segment}")\n'
            '  elseif(IS_ABSOLUTE "${current_segment}")\n'
            '    message(WARNING "Since \\"${current_segment}\\" is absolute, it overrides base path: \\"${base_path}\\".")\n'
            '    set(temp_path "${current_segment}")\n'
            '  else()\n'
            '    set(temp_path "${base_path}/${current_segment}")\n'
            '  endif()\n'
            '  set(${joined_path} "${temp_path}" PARENT_SCOPE)\n'
            'endfunction()\n'
        )
        save(self, "cmake/Modules/ExtendPath.cmake", extend_path_cmake)

        llvm_check_compiler_linker_flag = (
            'include(CMakePushCheckState)\n'
            '\n'
            'include(CheckCompilerFlag OPTIONAL)\n'
            '\n'
            'if(NOT COMMAND check_compiler_flag)\n'
            '  include(CheckCCompilerFlag)\n'
            '  include(CheckCXXCompilerFlag)\n'
            'endif()\n'
            '\n'
            'function(llvm_check_compiler_linker_flag lang flag out_var)\n'
            '  cmake_push_check_state()\n'
            '  set(CMAKE_REQUIRED_FLAGS "${CMAKE_REQUIRED_FLAGS} ${flag}")\n'
            '  if(COMMAND check_compiler_flag)\n'
            '    check_compiler_flag("${lang}" "" ${out_var})\n'
            '  else()\n'
            '    if("${lang}" STREQUAL "C")\n'
            '      check_c_compiler_flag("" ${out_var})\n'
            '    elseif("${lang}" STREQUAL "CXX")\n'
            '      check_cxx_compiler_flag("" ${out_var})\n'
            '    else()\n'
            '      message(FATAL_ERROR "\\"${lang}\\" is not C or CXX")\n'
            '    endif()\n'
            '  endif()\n'
            '  cmake_pop_check_state()\n'
            'endfunction()\n'
        )
        save(self, "cmake/Modules/LLVMCheckCompilerLinkerFlag.cmake",
             llvm_check_compiler_linker_flag)

    def generate(self):
        tc = CMakeToolchain(self)
        # Platform/HarmonyOS.cmake: CMake has no built-in Platform/HarmonyOS
        # module (it only ships OHOS.cmake), so the system is reported as
        # "unknown" and CMAKE_SHARED_LIBRARY_SONAME_*_FLAG is never set.
        # Inject Platform/Linux via the generators dir (conan_toolchain.cmake
        # already PREPENDs it to CMAKE_MODULE_PATH) so shared library SONAMEs
        # are emitted WITHOUT clobbering CMAKE_MODULE_PATH (the openmp
        # CMakeLists.txt list(INSERT)s its own cmake/ dir; an absolute
        # CMAKE_MODULE_PATH cache set here would shadow those includes).
        pm = os.path.join(self.generators_folder, "Platform")
        os.makedirs(pm, exist_ok=True)
        with open(os.path.join(pm, "HarmonyOS.cmake"), "w",
                  encoding="utf-8") as _f:
            _f.write("include(Platform/Linux)\n")
        tc.variables["CMAKE_SYSTEM_NAME"] = "HarmonyOS"
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.variables["OPENMP_STANDALONE_BUILD"] = "ON"
        tc.variables["OPENMP_ENABLE_LIBOMPTARGET"] = "ON"
        # DeviceRTL builds GPU bitcode via clang -fopenmp-targets; not usable
        # on this host-only platform, disable it.
        tc.variables["LIBOMPTARGET_BUILD_DEVICERTL_BCLIB"] = "FALSE"
        # The LLVM version-script (exports) adds VERS1.0 symbol versioning,
        # which the HarmonyOS dynamic loader cannot resolve at runtime
        # ("Error relocating ... symbol not found"). Disable it so the
        # shared library exports plain (non-versioned) symbols.
        tc.variables["LIBOMP_HAVE_VERSION_SCRIPT_FLAG"] = "FALSE"
        # The libomptarget CMakeLists sets LIBOMPTARGET_USE_LTO=TRUE (default)
        # and appends -flto AFTER CMAKE_CXX_FLAGS, re-enabling LTO even with
        # -fno-lto. LTO-built shared libraries are rejected by the HarmonyOS
        # musl loader (dlopen EACCES at ELF load); kill LTO at the source and
        # keep -fno-lto as a belt-and-braces guard.
        tc.variables["LIBOMPTARGET_USE_LTO"] = "FALSE"
        tc.variables["CMAKE_INTERPROCEDURAL_OPTIMIZATION"] = "FALSE"
        tc.variables["CMAKE_CXX_FLAGS"] = "-fno-lto"
        tc.variables["CMAKE_C_FLAGS"] = "-fno-lto"
        # Force the self-contained "dlopened libffi" generic-ELF64 plugin mode
        # (no system libffi dependency at build or runtime).
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_FFI"] = "TRUE"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # Packaging target is the RTL plugin libraries (Alpine libomptarget-rtl
        # parity): keep only libomptarget.rtl.*.so* under lib/. The
        # libomptarget main runtime (libomptarget.so), the host OpenMP runtime
        # (libomp.so) and tools (libarcher) belong to their own packages, as
        # do the OpenMP API headers (libomp/libomptarget dev packages).
        libdir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(libdir):
            for f in os.listdir(libdir):
                if f.startswith("libomptarget.rtl."):
                    continue
                p = os.path.join(libdir, f)
                if os.path.islink(p) or os.path.isfile(p):
                    os.remove(p)
            cmake_dir = os.path.join(libdir, "cmake")
            if os.path.isdir(cmake_dir):
                import shutil
                shutil.rmtree(cmake_dir)
        incdir = os.path.join(self.package_folder, "include")
        if os.path.isdir(incdir):
            import shutil
            shutil.rmtree(incdir)

    def package_info(self):
        # The RTL plugin is dlopened by libomptarget at runtime; expose it as
        # a linkable library for consumers/tests.
        self.cpp_info.libs = ["omptarget.rtl.aarch64"]
        self.cpp_info.includedirs = []  # headers belong to libomp/libomptarget dev packages
        self.cpp_info.set_property("cmake_file_name", "libomptarget-rtl")
        self.cpp_info.set_property("cmake_target_name",
                                   "libomptarget-rtl::omptarget.rtl.aarch64")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["dl"]
