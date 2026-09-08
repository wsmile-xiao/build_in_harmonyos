from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
import os


class PxrVtConan(ConanFile):
    name = "pxr-vt"
    version = "26.08"
    description = "Value Types library from Pixar OpenUSD (Universal Scene Description)"
    license = "Modified Apache 2.0 License"
    homepage = "https://openusd.org"
    url = "https://github.com/PixarAnimationStudios/OpenUSD"
    topics = ("openusd", "pixar", "vt", "value-types", "pxr", "3d", "scene-description")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"

    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("tbb/2023.0.0")

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm("fPIC")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _get_cc(self):
        """Get C compiler path from Conan conf (R33)."""
        comp_execs = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return comp_execs.get("c") or "clang"

    def _sdk_llvm_libdir(self):
        """LLVM lib dir of the compiler toolchain (contains libxml2.so.16).

        The OHOS clang driver spawns lld for linking, and lld's RUNPATH
        ($ORIGIN/../lib) points into the SDK llvm/lib. On CI workers the
        ambient LD_LIBRARY_PATH may not include this path, causing lld to
        fail with "Error loading shared library libxml2.so.16" during
        CMake try-compile tests (E132). Prepend the SDK llvm/lib so the
        correct libxml2 is found first.
        """
        cc = self._get_cc()
        cc_real = os.path.realpath(cc)
        llvm_lib = os.path.join(os.path.dirname(os.path.dirname(cc_real)), "lib")
        return llvm_lib if os.path.isdir(llvm_lib) else ""

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["PXR_BUILD_IMAGING"] = False
        tc.variables["PXR_BUILD_USD_IMAGING"] = False
        tc.variables["PXR_BUILD_USDVIEW"] = False
        tc.variables["PXR_BUILD_TESTS"] = False
        tc.variables["PXR_BUILD_EXAMPLES"] = False
        tc.variables["PXR_BUILD_TUTORIALS"] = False
        tc.variables["PXR_BUILD_USD_TOOLS"] = False
        tc.variables["PXR_ENABLE_PYTHON_SUPPORT"] = False
        tc.variables["PXR_BUILD_EXEC"] = False
        tc.variables["PXR_BUILD_USD_VALIDATION"] = False
        tc.variables["PXR_BUILD_USD"] = False
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_Python"] = True
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_Python3"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # Fix E132: OHOS SDK lld linker depends on libxml2.so.16
        # which is in the SDK's llvm/lib directory. On CI workers the
        # ambient LD_LIBRARY_PATH may not include this path, causing
        # CMake try-compile tests to fail with "Toolchain is unable to
        # link executables". Prepend SDK llvm/lib so lld finds the
        # correct libxml2.so.16 (same pattern as abr2gbr/1.0.2).
        sdk_llvm_lib = self._sdk_llvm_libdir()
        if sdk_llvm_lib:
            existing = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = (
                sdk_llvm_lib + (os.pathsep + existing if existing else "")
            )

        cmake = CMake(self)
        cmake.configure()
        cmake.build(target="vt")

    def package(self):
        # USD libraries are named libusd_<name>.a and located in
        # build/pxr/base/<name>/ subdirectories
        for libname in ["vt", "arch", "tf", "gf", "trace"]:
            lib_subdir = os.path.join(self.build_folder, "pxr", "base", libname)
            copy(self, f"libusd_{libname}*", src=lib_subdir,
                 dst=os.path.join(self.package_folder, "lib"))
        # 'work' is a header-only library, no .a file to copy
        # Copy source headers
        include_base = os.path.join(self.source_folder, "pxr", "base")
        for libname in ["vt", "arch", "tf", "gf", "trace", "work"]:
            src_include = os.path.join(include_base, libname)
            if os.path.isdir(src_include):
                copy(self, "*.h", src=src_include,
                     dst=os.path.join(self.package_folder, "include", "pxr", "base", libname))
        # Copy generated headers (api.h, buildMode.h, etc.)
        gen_include = os.path.join(self.build_folder, "include")
        if os.path.isdir(gen_include):
            copy(self, "*.h", src=gen_include,
                 dst=os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["usd_vt", "usd_arch", "usd_tf", "usd_gf", "usd_trace"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.requires = ["tbb::tbb"]
