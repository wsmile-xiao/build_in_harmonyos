import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)


class ImplotConan(ConanFile):
    name = "implot"
    version = "0.8"
    description = "Immediate Mode Plotting library for Dear ImGui"
    license = "MIT"
    homepage = "https://github.com/epezent/implot"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/tree/main/archives/i/implot/0.8"
    topics = ("plotting", "imgui", "immediate-mode", "gui")
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires("imgui/1.92.2b")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS", "Windows", "Macos", "FreeBSD"):
            raise ConanInvalidConfiguration(
                f"{self.name} not validated for {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        toolchain.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(
            self.options.get_safe("fPIC", True)
        )
        toolchain.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        save(
            self,
            os.path.join(self.source_folder, "CMakeLists.txt"),
            self._cmake_lists(),
        )
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["implot"]
        self.cpp_info.requires = ["imgui::imgui"]
        # CMakeDeps on conan 2.29.1 serializes empty includedirs for
        # transitive dependencies, so propagate imgui headers explicitly.
        imgui_dep = self.dependencies["imgui"]
        self.cpp_info.includedirs.extend(imgui_dep.cpp_info.includedirs)
        self.cpp_info.set_property("cmake_file_name", "implot")
        self.cpp_info.set_property("cmake_target_name", "implot::implot")

    @staticmethod
    def _cmake_lists():
        return """\
cmake_minimum_required(VERSION 3.15)
project(implot LANGUAGES CXX)

find_package(imgui CONFIG REQUIRED)

add_library(implot implot.cpp implot_items.cpp)
target_link_libraries(implot PUBLIC imgui::imgui)
target_include_directories(implot PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
    $<INSTALL_INTERFACE:include>
)
target_compile_features(implot PUBLIC cxx_std_17)

install(TARGETS implot EXPORT implot-config
    ARCHIVE DESTINATION lib
    LIBRARY DESTINATION lib
)
install(FILES implot.h implot_internal.h DESTINATION include)
install(EXPORT implot-config
    FILE implot-config.cmake
    NAMESPACE implot::
    DESTINATION lib/cmake/implot
)
"""
