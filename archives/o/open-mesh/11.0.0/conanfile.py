from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.files import get, copy
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
import os, tarfile, shutil, glob

class OpenMeshConan(ConanFile):
    name = "open-mesh"
    version = "11.0.0"
    description = "OpenMesh polygonal mesh data structure"
    license = "BSD-3-Clause"
    homepage = "https://www.graphics.rwth-aachen.de/software/openmesh/"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def layout(self):
        cmake_layout(self)

    def source(self):
        local = os.environ.get("OHC_TARBALL")
        if local and os.path.isfile(local):
            with tarfile.open(local, "r:gz") as tf:
                tf.extractall(self.source_folder)
            entries = [e for e in os.listdir(self.source_folder) if e not in (".", "..")]
            if len(entries) == 1 and os.path.isdir(os.path.join(self.source_folder, entries[0])):
                inner = os.path.join(self.source_folder, entries[0])
                for n in os.listdir(inner):
                    os.rename(os.path.join(inner, n), os.path.join(self.source_folder, n))
        else:
            get(self, **self.conan_data["sources"], strip_root=True)
        dest = os.path.join(self.source_folder, "cmake-library")
        if not os.path.isdir(dest):
            raise ConanException("cmake-library missing from OpenMesh tarball")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.variables["BUILD_APPS"] = False
        tc.variables["OPENMESH_BUILD_UNIT_TESTS"] = True
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j1"])
        if can_run(self):
            self.run("ctest --output-on-failure", cwd=self.build_folder, ignore_errors=True)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE*", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        libdir = os.path.join(self.package_folder, "lib")
        if not self.options.shared:
            for p in glob.glob(os.path.join(libdir, "*.so*")):
                os.remove(p)

    def package_info(self):
        self.cpp_info.libs = ["OpenMeshTools", "OpenMeshCore"]
        self.cpp_info.set_property("cmake_file_name", "open-mesh")
        self.cpp_info.set_property("cmake_target_name", "open-mesh::open-mesh")
