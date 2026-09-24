import json
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class BoulderGameConan(ConanFile):
    name = "boulder-game"
    version = "1.02"
    package_type = "application"
    description = "Boulder puzzle game and original map editor with an OHOS ArkUI host"
    license = "Public Domain", "MIT", "Apache-2.0 WITH LLVM-exception"
    homepage = "https://github.com/rh-galaxy/boulder"
    settings = "os", "arch", "compiler", "build_type"
    default_options = {"sdl2/*:shared": False}

    def requirements(self):
        self.requires("sdl2/2.32.10")

    def validate(self):
        if str(self.settings.os) != "OHOS" or str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("The packaged ArkUI application targets OHOS armv8")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_TESTING"] = True
        tc.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Upstream has no automated suite. These added checks exercise its real
        # image/audio decoders and map serialization; GUI validation is separate.
        with VirtualRunEnv(self).vars().apply():
            cmake.test()

    def package(self):
        CMake(self).install()
        copy(self, "*", src=os.path.join(self.dependencies["sdl2"].package_folder, "licenses"),
             dst=os.path.join(self.package_folder, "licenses", "sdl2"))
        project = os.path.join(self.package_folder, "share", "boulder", "harmony-project")
        libs = os.path.join(project, "entry", "libs", "arm64-v8a")
        for name in ("libboulderhost.so", "libeditorhost.so"):
            copy(self, name, src=os.path.join(self.package_folder, "lib", "boulder"), dst=libs)
        resources = os.path.join(project, "entry", "src", "main", "resources", "rawfile")
        data = os.path.join(self.source_folder, "exe", "data")
        copy(self, "*", src=data, dst=os.path.join(resources, "boulder"))
        files = sorted(os.path.relpath(os.path.join(root, name), data).replace(os.sep, "/")
                       for root, _, names in os.walk(data) for name in names)
        with open(os.path.join(resources, "boulder-files.json"), "w", encoding="utf-8") as handle:
            json.dump(files, handle)

    def package_info(self):
        # These NAPI modules are private to the application, not linkable SDKs.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
