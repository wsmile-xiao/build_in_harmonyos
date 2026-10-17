"""Conan recipe for oneTBB 2023.1.0."""

import glob
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class OnetbbConan(ConanFile):
    name = "onetbb"
    version = "2023.1.0"
    description = "oneAPI Threading Building Blocks parallel C++ library"
    license = "Apache-2.0"
    homepage = "https://uxlfoundation.github.io/oneTBB/"
    url = "https://github.com/uxlfoundation/oneTBB"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        # Keep the upstream CTest suite enabled so the build phase exercises
        # the real oneTBB tests instead of a smoke-only consumer check.
        tc.variables["TBB_TEST"] = True
        tc.variables["TBB_EXAMPLES"] = False
        tc.variables["TBB4PY_BUILD"] = False
        # The malloc proxy relies on glibc-style allocator interposition,
        # which is unavailable in the non-glibc OHOS runtime.
        tc.variables["TBBMALLOC_PROXY_BUILD"] = self.settings.os != "OHOS"
        tc.variables["TBB_ENABLE_IPO"] = False
        tc.variables["TBB_DISABLE_HWLOC_AUTOMATIC_SEARCH"] = True
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        if self.settings.os == "OHOS":
            # Conan's generic OHOS mapping uses HarmonyOS, while CMake ships
            # the platform module under OHOS.cmake.
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        cmake.test()

    def package(self):
        CMake(self).install()
        copy(self, "LICENSE.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        if self.settings.os == "OHOS" and self.options.shared:
            self._sign_shared_objects()

    def _sign_shared_objects(self):
        """Sign installed OHOS ELF libraries after the final package mutation."""
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for path in glob.glob(os.path.join(self.package_folder, "lib", "*.so*")):
            if os.path.islink(path) or not os.path.isfile(path):
                continue
            self.run('{0} --remove-section .codesign "{1}" 2>/dev/null || true'.format(objcopy, path))
            self.run('{0} sign -inFile "{1}" -outFile "{1}" -selfSign 1'.format(signer, path))

    def package_info(self):
        # oneTBB uses a platform-specific versioned output name.  Its Unix
        # install also provides the unversioned libtbb.so namelink, while
        # Windows and static builds use the tbb12 basename.
        if self.options.shared and self.settings.os != "Windows":
            self.cpp_info.libs = ["tbb"]
        else:
            self.cpp_info.libs = ["tbb12"]
        self.cpp_info.set_property("cmake_file_name", "TBB")
        self.cpp_info.set_property("cmake_target_name", "TBB::tbb")
        self.cpp_info.set_property("pkg_config_name", "tbb")
