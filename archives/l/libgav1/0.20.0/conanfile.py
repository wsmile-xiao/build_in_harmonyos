from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, get


class Libgav1Conan(ConanFile):
    name = "libgav1"
    version = "0.20.0"
    description = "AV1 decoder library"
    license = "BSD-3-Clause"
    homepage = "https://chromium.googlesource.com/codecs/libgav1/"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        sources = self.conan_data["sources"]
        try:
            get(self, url=sources["url"], sha256=sources.get("sha256"), strip_root=True)
            return
        except Exception as error:
            mirror_urls = sources.get("mirror_urls") or []
            mirror_sha256 = sources.get("mirror_sha256")
            if not mirror_urls or not mirror_sha256:
                raise
            self.output.warning(f"Primary source failed ({error}); trying verified mirrors")
        for mirror_url in mirror_urls:
            try:
                get(self, url=mirror_url, sha256=mirror_sha256, strip_root=True)
                return
            except Exception as error:
                self.output.warning(f"Mirror source failed ({error}): {mirror_url}")
        raise ConanException(
            "libgav1/0.20.0: no pinned source archive could be downloaded and "
            "sha256-verified; see the mirror_urls in conandata.yml"
        )

    def layout(self):
        cmake_layout(self, src_folder=".")

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            # On HarmonyOS CMake resolves both the host and the target CPU to the
            # literal string "unknown", so upstream's optimization detection in
            # cmake/libgav1_cpu_detection.cmake (it matches CMAKE_SYSTEM_PROCESSOR
            # against "^arm|^aarch64") never enables NEON: the library was built
            # with LIBGAV1_ENABLE_NEON=0 and the tests/libgav1_tests.cmake target
            # common_neon_test was not even registered. Declaring the target system
            # and processor restores the ARM NEON DSP path. Same workaround as
            # libmatio/libaec/libnghttp2 in this repository; the os guard is needed
            # so that Linux profiles keep CMake's own platform detection.
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["LIBGAV1_ENABLE_TESTS"] = False
        tc.variables["LIBGAV1_ENABLE_EXAMPLES"] = False
        tc.variables["LIBGAV1_THREADPOOL_USE_STD_MUTEX"] = 1
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["gav1"]
        self.cpp_info.set_property("cmake_file_name", "libgav1")
        self.cpp_info.set_property("cmake_target_name", "gav1::gav1")
