import os
from pathlib import Path
from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.env import Environment, VirtualRunEnv


class ChromaprintConan(ConanFile):
    name = "chromaprint"
    version = "1.6.1"
    package_type = "library"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/acoustid/chromaprint"
    description = "Audio fingerprint calculation with the FFTW single-precision backend"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "ohos-elf.cmake"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("fftw3f/3.3.10")

    def layout(self):
        cmake_layout(self)

    def source(self):
        source = dict(self.conan_data["sources"][self.version])
        local = os.environ.get("CHROMAPRINT_SOURCE_ARCHIVE")
        if local:
            source["url"] = Path(local).resolve(strict=True).as_uri()
        get(self, **source, strip_root=True)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["BUILD_TESTS"] = True
        tc.variables["BUILD_TOOLS"] = False
        tc.variables["FFT_LIB"] = "fftw3f"
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_FFmpeg"] = True
        tc.variables["FFTW3_DIR"] = self.dependencies["fftw3f"].package_folder
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.10"
        if self.settings.os == "OHOS":
            tc.variables["CMAKE_PROJECT_INCLUDE"] = os.path.join(self.source_folder, "ohos-elf.cmake")
            # CMake install's RPATH rewrite changes an already signed ELF.
            # Conan supplies loader paths; keep signed bytes unchanged.
            tc.variables["CMAKE_SKIP_RPATH"] = True
        tc.generate()
        VirtualRunEnv(self).generate()

    def build(self):
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        local = Environment()
        local.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, "src"))
        # Bundled GoogleTest inherits BUILD_SHARED_LIBS and is loaded during
        # CMake's post-build discovery, before the first ctest invocation.
        local.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, "lib"))
        with VirtualRunEnv(self).vars().apply(), local.vars(self).apply():
            cmake.build()
            self.run("ctest --output-on-failure --parallel 2", cwd=self.build_folder, env="conanrun")

    def package(self):
        CMake(self).install()
        copy(self, "LICENSE*", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "COPYING*", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["chromaprint"]
        self.cpp_info.set_property("cmake_file_name", "Chromaprint")
        self.cpp_info.set_property("cmake_target_name", "Chromaprint::chromaprint")
        self.cpp_info.set_property("pkg_config_name", "libchromaprint")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
