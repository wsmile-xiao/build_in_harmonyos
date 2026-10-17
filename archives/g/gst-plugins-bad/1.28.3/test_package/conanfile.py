#!/usr/bin/env python3
"""Conan test_package -- gst-plugins-bad 1.28.3 consumer test.

Builds a consumer binary against the packaged libraries (validates
headers, pkg-config style metadata and linking), then verifies at
runtime that the libraries load on OHOS (ELF signature check by the
loader) and export their public API (dlopen/dlsym), plus readelf-based
structural checks on the packaged libraries and plugins.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class GstPluginsBadTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # gst/gst.h and glib headers come from the transitive deps; declare
        # them explicitly (same pattern as the gstreamer test_package)
        self.requires("gstreamer/1.28.3")
        self.requires("glib2/2.88.0")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _package_dir(self):
        for dep in self.dependencies.values():
            if dep.ref.name == "gst-plugins-bad":
                return str(dep.package_folder)
        return None

    def test(self):
        pkg = self._package_dir()
        assert pkg, "gst-plugins-bad dependency not found"

        lib_dir = os.path.join(pkg, "lib")
        plugin_dir = os.path.join(lib_dir, "gstreamer-1.0")

        # Structural checks: the packaged libraries exist and carry the
        # right SONAMEs (E274/E316 class of issues would break consumers).
        for lib in ("libgstinsertbin-1.0.so.0", "libgstcodecparsers-1.0.so.0",
                    "libgstwebrtc-1.0.so.0", "libgstvideo-1.0.so.0"):
            path = os.path.join(lib_dir, lib)
            assert os.path.exists(path), f"missing library: {path}"
            self.run(f'readelf -d "{path}" | grep "Library soname: \\[{lib}\\]"',
                     env="conanrun")

        # The bad plugins must be present and export their plugin symbols.
        plugins = [f for f in os.listdir(plugin_dir) if f.endswith(".so")]
        assert len(plugins) > 10, f"too few plugins packaged: {len(plugins)}"
        self.run(f'readelf --dyn-syms "{os.path.join(plugin_dir, "libgstaccurip.so")}"'
                 f' | grep gst_plugin_acc', env="conanrun")

        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindirs[0],
                                    "test_gst_plugins_bad")
            self.run(bin_path, env="conanrun")
