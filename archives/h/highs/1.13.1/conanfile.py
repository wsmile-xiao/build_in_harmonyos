from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import apply_conandata_patches, copy, get
import os

class HiGHSConan(ConanFile):
    name = "highs"
    version = "1.13.1"
    package_type = "library"
    license = "MIT"
    author = "ERGO-Code"
    url = "https://github.com/ERGO-Code/HiGHS"
    description = "Linear optimization library"
    topics = ("optimization", "solver", "linear-programming")
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    generators = "CMakeDeps"
    exports_sources = "patches/*"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # HiGHS 的 CMake install 会把头文件装到 include/highs/ 子目录下，
        # 但 cmake config 把 include path 设为 include/。
        # 从 src/ 按 keep_path=True 复制确保头文件结构与内部 #include 匹配。
        copy(self, "*.h", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include"), keep_path=True)
        copy(self, "*.hpp", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include"), keep_path=True)
        copy(self, "*.hh", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include"), keep_path=True)

    def package_info(self):
        self.cpp_info.libs = ["highs"]
        self.cpp_info.includedirs = ["include/highs", "include"]