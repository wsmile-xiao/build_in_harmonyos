import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import check_sha256, copy, get, unzip


class OpenmeshConan(ConanFile):
    name = "openmesh"
    version = "11.0.0"
    description = "Polygon mesh data structure and processing library"
    license = "BSD-3-Clause"
    homepage = "https://www.graphics.rwth-aachen.de/software/openmesh/"
    url = ""

    package_type = "library"
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
        staged = os.path.join(cache_root, "OpenMesh-11.0.0.tar.gz")
        if os.path.isfile(staged):
            check_sha256(self, staged, source["sha256"])
            unzip(self, staged, strip_root=True)
        else:
            get(self, **source, strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.variables["BUILD_APPS"] = False
        toolchain.variables["OPENMESH_DOCS"] = False
        toolchain.variables["OPENMESH_BUILD_UNIT_TESTS"] = False
        toolchain.variables["OPENMESH_BUILD_SHARED"] = bool(self.options.shared)
        toolchain.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = bool(
            self.options.get_safe("fPIC", True)
        )
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        if self.settings.os != "Windows":
            target = (
                "OpenMeshTools"
                if self.options.shared
                else "OpenMeshToolsStatic"
            )
            cmake.build(target=target)
        else:
            cmake.build()

    def package(self):
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

        if self.settings.os != "Windows" and not self.options.shared:
            for component in ("Core", "Tools"):
                include_src = os.path.join(
                    self.source_folder, "src", "OpenMesh", component
                )
                include_dst = os.path.join(
                    self.package_folder,
                    "include",
                    "OpenMesh",
                    component,
                )
                for pattern in ("*.h", "*.hh", "*.inl"):
                    copy(
                        self,
                        pattern,
                        src=include_src,
                        dst=include_dst,
                        keep_path=True,
                    )
            libdir = os.path.join(self.package_folder, "lib")
            built_libdir = os.path.join(
                self.build_folder, "Build", "lib"
            )
            debug_postfix = (
                "d" if self.settings.build_type == "Debug" else ""
            )
            for component in ("Core", "Tools"):
                library = (
                    f"libOpenMesh{component}{debug_postfix}.a"
                )
                built_library = os.path.join(built_libdir, library)
                if not os.path.isfile(built_library):
                    raise ConanException(
                        f"Expected OpenMesh library was not built: "
                        f"{built_library}"
                    )
                copy(
                    self,
                    library,
                    src=built_libdir,
                    dst=libdir,
                    keep_path=False,
                )
        else:
            cmake = CMake(self)
            cmake.install()

    def package_info(self):
        debug_postfix = (
            "d" if self.settings.build_type == "Debug" else ""
        )
        self.cpp_info.libs = [
            f"OpenMeshTools{debug_postfix}",
            f"OpenMeshCore{debug_postfix}",
        ]
        if not self.options.shared:
            self.cpp_info.defines = ["OM_STATIC_BUILD"]
        self.cpp_info.set_property("cmake_file_name", "OpenMesh")
        self.cpp_info.set_property(
            "cmake_target_name", "OpenMesh::OpenMesh"
        )
