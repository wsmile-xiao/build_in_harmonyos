from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
import os


class MinjaConan(ConanFile):
    name = "minja"
    version = "0-git20250922.021c2293c187"
    description = "Minimalistic C++ Jinja templating engine for LLM chat templates"
    license = "MIT"
    homepage = "https://github.com/google/minja"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("jinja", "template", "llm", "header-only")
    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def package_id(self):
        self.info.clear()

    def requirements(self):
        self.requires("nlohmann_json/3.12.0")
        self.test_requires("gtest/1.17.0")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, filename="minja-20250922.tar.gz", **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        tc.variables["MINJA_TEST_ENABLED"] = True
        tc.variables["MINJA_FUZZTEST_ENABLED"] = False
        tc.variables["MINJA_EXAMPLE_ENABLED"] = False
        tc.variables["MINJA_USE_VENV"] = False
        CMakeDeps(self).generate()
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self.run("ctest --output-on-failure -E ToolTest", cwd=self.build_folder)

    def package(self):
        copy(self, "*.hpp", src=os.path.join(self.source_folder, "include", "minja"),
             dst=os.path.join(self.package_folder, "include", "minja"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.requires = ["nlohmann_json::nlohmann_json"]
        self.cpp_info.set_property("cmake_file_name", "minja")
        self.cpp_info.set_property("cmake_target_name", "minja::minja")
