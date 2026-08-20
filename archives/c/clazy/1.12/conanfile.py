from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
import os


class ClazyConan(ConanFile):
    name = "clazy"
    version = "1.12"
    description = "Qt-oriented static code analyzer based on the Clang framework"
    license = "LGPL-2.0-or-later"
    homepage = "https://github.com/KDE/clazy"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CLAZY_LINK_CLANG_DYLIB"] = "ON"
        tc.cache_variables["CLAZY_BUILD_CLANG_TIDY"] = "OFF"
        # OHOS SDK LLVM ships only monolithic libLLVM.so
        tc.cache_variables["CMAKE_EXE_LINKER_FLAGS"] = "-Wl,--unresolved-symbols=ignore-all -Wl,--allow-shlib-undefined"
        tc.cache_variables["CMAKE_SHARED_LINKER_FLAGS"] = "-Wl,--allow-shlib-undefined"
        # ABI namespace override: OHOS SDK LLVM uses __h, system libc++ uses __n1
        abi_override_dir = os.path.join(self.source_folder, "abi-override")
        os.makedirs(abi_override_dir, exist_ok=True)
        config_site = os.path.join(abi_override_dir, "__config_site")
        with open(config_site, "w") as f:
            f.write(
                "#ifndef _LIBCPP___CONFIG_SITE\n"
                "#define _LIBCPP___CONFIG_SITE\n"
                "#define _LIBCPP_ABI_VERSION 1\n"
                "#define _LIBCPP_ABI_NAMESPACE __h\n"
                "#define _LIBCPP_HAS_NO_VENDOR_AVAILABILITY_ANNOTATIONS\n"
                "#define _LIBCPP_ENABLE_ASSERTIONS_DEFAULT 0\n"
                "#endif // _LIBCPP___CONFIG_SITE\n"
            )
        tc.cache_variables["CMAKE_CXX_FLAGS"] = "-I" + abi_override_dir
        tc.generate()

    def build(self):
        # E132: OHOS SDK lld needs libxml2.so from SDK lib path
        llvm_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
        cur = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = f"{llvm_lib}:{cur}" if cur else llvm_lib
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["ClazyPlugin"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
