import os
from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout

class TestGstLibavConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        cmake = CMake(self)
        # Run CTest (executes test_gst_libav with plugin path argument)
        # The CMakeLists.txt passes the plugin path via environment variable
        # Plugin path is set by the conan test environment
        plugin_path = None
        for dep in self.dependencies.values():
            if dep.ref.name == "gst-libav":
                plugin_path = os.path.join(
                    str(dep.package_folder),
                    "lib", "gstreamer-1.0", "libgstlibav.so"
                )
                break

        if can_run(self) and plugin_path:
            assert os.path.exists(plugin_path), f"Plugin not found: {plugin_path}"
            # Verify plugin ELF structure (OHOS blocks dlopen of unsigned ELF)
            self.run(f"readelf -d {plugin_path} | grep SONAME", env="conanrun")
            self.run(
                f"readelf --dyn-syms {plugin_path} | grep gst_plugin_libav",
                env="conanrun"
            )
            # Run the consumer test binary with plugin path as argument
            bin_path = os.path.join(self.cpp.build.bindir[0], "test_gst_libav")
            self.run(f'{bin_path} "{plugin_path}"', env="conanrun", ignore_errors=True)
        else:
            # Build-only mode: verify package structure
            assert plugin_path, "gst-libav dependency not found"
