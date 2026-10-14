import os
from pathlib import Path
from conan import ConanFile
from conan.tools.files import get, copy, export_conandata_patches, apply_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.gnu import PkgConfigDeps
from conan.tools.env import Environment, VirtualRunEnv


class Lib2GeomConan(ConanFile):
    name = "lib2geom"
    version = "1.4.0"
    package_type = "library"
    license = "LGPL-2.1-or-later", "MPL-1.1"
    homepage = "https://gitlab.com/inkscape/lib2geom"
    description = "Computational geometry library for vector graphics"
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
        self.requires("boost/1.90.0.3", transitive_headers=True)
        self.requires("double-conversion/3.4.0")
        self.requires("glib/2.88.3.1", transitive_headers=True)
        self.requires("gsl/2.8", transitive_headers=True)

    def build_requirements(self):
        self.test_requires("gtest/1.17.0.2")

    def layout(self):
        cmake_layout(self)

    def source(self):
        source = dict(self.conan_data["sources"][self.version])
        local = os.environ.get("LIB2GEOM_SOURCE_ARCHIVE")
        if local:
            source["url"] = Path(local).resolve(strict=True).as_uri()
        get(self, **source, strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.set_property("boost", "cmake_file_name", "Boost")
        deps.generate()
        PkgConfigDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["2GEOM_BUILD_SHARED"] = bool(self.options.shared)
        tc.variables["2GEOM_TESTING"] = True
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_Cython"] = True
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.10"
        double = self.dependencies["double-conversion"]
        tc.variables["DoubleConversion_LIBRARYDIR"] = double.cpp_info.libdirs[0]
        tc.variables["DoubleConversion_INCLUDEDIR"] = double.cpp_info.includedirs[0]
        for include in self.dependencies["boost"].cpp_info.includedirs:
            tc.extra_cxxflags.append("-I" + include)
        # Upstream consumes pkg-config *_LIBRARIES (-lname), not its
        # *_LDFLAGS or imported targets. Preserve the graph's link directories
        # for both the shared library and all upstream executable tests.
        for dep in self.dependencies.host.values():
            for directory in dep.cpp_info.libdirs:
                if os.path.isdir(directory):
                    tc.extra_sharedlinkflags.append("-L" + directory)
                    tc.extra_exelinkflags.append("-L" + directory)
        if self.settings.os == "OHOS":
            # Preserve separately rounded multiply/add operations used by
            # the upstream geometric predicates on the ARM64 Clang target.
            # This flag does not change assertions. The separate OHOS circle
            # tolerance patch is disclosed in the manifest and test report.
            if str(self.settings.compiler) == "clang":
                tc.extra_cxxflags.append("-ffp-contract=off")
            tc.variables["CMAKE_PROJECT_INCLUDE"] = os.path.join(self.source_folder, "ohos-elf.cmake")
            tc.variables["CMAKE_SKIP_RPATH"] = True
        tc.generate()
        env = Environment()
        # Upstream's optional Cairo/GTK probes must not silently consume
        # untracked libraries installed on a developer device.
        env.define_path("PKG_CONFIG_LIBDIR", self.generators_folder)
        env.vars(self).save_script("conanbuildenv-pkgconfig")
        VirtualRunEnv(self).generate()

    def build(self):
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        local = Environment()
        local.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, "src", "2geom"))
        with VirtualRunEnv(self).vars().apply(), local.vars(self).apply():
            cmake.build()
            self.run("ctest --output-on-failure --verbose --parallel 2", cwd=self.build_folder, env="conanrun")

    def package(self):
        CMake(self).install()
        copy(self, "COPYING*", self.source_folder, os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["2geom"]
        self.cpp_info.includedirs = ["include/2geom-1.4.0"]
        self.cpp_info.set_property("cmake_file_name", "2Geom")
        self.cpp_info.set_property("cmake_target_name", "2Geom::2geom")
        self.cpp_info.set_property("pkg_config_name", "2geom")
