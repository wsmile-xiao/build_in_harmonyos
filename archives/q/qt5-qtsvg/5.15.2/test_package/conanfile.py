import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Qt5QtSvgTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qt5-qtbase/5.15.2")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        variables = {}
        if str(self.settings.os) == "OHOS":
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
            compiler = compilers.get("cpp") or compilers.get("cxx")
            if compiler:
                compiler_dir = os.path.dirname(os.path.realpath(compiler))
                variables["OHOS_CXX_RUNTIME_DIR"] = os.path.join(
                    compiler_dir, "..", "lib", "aarch64-linux-ohos"
                )
        cmake.configure(variables=variables)
        cmake.build()

    def test(self):
        dep = self.dependencies["qt5-qtsvg"]
        qtbase = self.dependencies["qt5-qtbase"]
        libdir = os.path.join(dep.package_folder, dep.cpp_info.libdirs[0])
        qtbase_libdir = os.path.join(qtbase.package_folder, "lib")
        test_bin = os.path.join(self.cpp.build.bindirs[0] if self.cpp.build.bindirs else ".", "test_qt5_qtsvg")
        # Set runtime environment for the test binary
        library_paths = [libdir, qtbase_libdir]
        existing_ld = os.environ.get("LD_LIBRARY_PATH")
        if existing_ld:
            library_paths.append(existing_ld)
        ld_path = ":".join(library_paths)
        plugin_path = os.path.join(qtbase.package_folder, "plugins", "platforms")
        self.run(
            f'QT_QPA_PLATFORM=offscreen '
            f'QT_QPA_PLATFORM_PLUGIN_PATH="{plugin_path}" '
            f'LD_LIBRARY_PATH="{ld_path}" '
            f'"{test_bin}"',
            ignore_errors=False
        )
