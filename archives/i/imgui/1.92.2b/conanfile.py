import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import check_sha256, copy, get, save, unzip


class ImguiConan(ConanFile):
    name = "imgui"
    version = "1.92.2b"
    description = "Bloat-free immediate-mode graphical user interface library"
    license = "MIT"
    homepage = "https://github.com/ocornut/imgui"
    url = "https://github.com/ocornut/imgui"

    package_type = "library"
    exports_sources = "sources/*"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        source = self.conan_data["sources"]
        cache_root = os.getenv(
            "OHPCD_SOURCE_CACHE", os.path.expanduser("~/Download")
        )
        staged = os.path.join(cache_root, "imgui-1.92.2b.tar.gz")
        if os.path.isfile(staged):
            check_sha256(self, staged, source["sha256"])
            unzip(self, staged, strip_root=True)
        else:
            get(self, **source, strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        toolchain.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(
            self.options.get_safe("fPIC", True)
        )
        toolchain.generate()

    def build(self):
        copy(
            self,
            "imgui_impl_ohos.*",
            src=os.path.join(self.source_folder, "sources"),
            dst=os.path.join(self.source_folder, "backends"),
            keep_path=False,
        )
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
            "LICENSE.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["imgui"]
        if str(self.settings.os) == "OHOS":
            self.cpp_info.system_libs = [
                "ace_ndk.z",
                "EGL",
                "GLESv3",
            ]
        self.cpp_info.set_property("cmake_file_name", "imgui")
        self.cpp_info.set_property("cmake_target_name", "imgui::imgui")

    @staticmethod
    def _cmake_lists():
        return """\
cmake_minimum_required(VERSION 3.15)
project(imgui LANGUAGES CXX)

add_library(imgui
    imgui.cpp
    imgui_demo.cpp
    imgui_draw.cpp
    imgui_tables.cpp
    imgui_widgets.cpp
)
if(CMAKE_SYSTEM_NAME MATCHES "OHOS|HarmonyOS")
    target_sources(imgui PRIVATE
        backends/imgui_impl_ohos.cpp
        backends/imgui_impl_opengl3.cpp
    )
    target_compile_definitions(imgui PRIVATE IMGUI_IMPL_OPENGL_ES3)
    target_link_libraries(imgui PUBLIC ace_ndk.z EGL GLESv3)
endif()
target_include_directories(imgui PUBLIC
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}>
    $<BUILD_INTERFACE:${CMAKE_CURRENT_SOURCE_DIR}/backends>
    $<INSTALL_INTERFACE:include>
)
target_compile_features(imgui PUBLIC cxx_std_11)

install(TARGETS imgui
    ARCHIVE DESTINATION lib
    LIBRARY DESTINATION lib
    RUNTIME DESTINATION bin
)
install(FILES
    imconfig.h
    imgui.h
    imgui_internal.h
    imstb_rectpack.h
    imstb_textedit.h
    imstb_truetype.h
    DESTINATION include
)
if(CMAKE_SYSTEM_NAME MATCHES "OHOS|HarmonyOS")
    install(FILES
        backends/imgui_impl_ohos.h
        backends/imgui_impl_opengl3.h
        backends/imgui_impl_opengl3_loader.h
        DESTINATION include
    )
endif()
"""
