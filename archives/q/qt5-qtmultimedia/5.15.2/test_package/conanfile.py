import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Qt5QtmultimediaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # qt5-qtbase 必须作为 test_package 的直接依赖声明：
        # 与 qt5-qtcharts/qt5-qtdeclarative test_package 相同的处理，CMakeDeps
        # 才生成完整的 per-component Qt5Core/Qt5Gui/Qt5Widgets 配置。
        self.requires("qt5-qtbase/5.15.2.2")

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
        # Run test binary directly with LD_LIBRARY_PATH set to the package
        # lib dirs (OHOS conanrun env doesn't set them)
        multimedia = self.dependencies["qt5-qtmultimedia"]
        qtbase = self.dependencies["qt5-qtbase"]
        libdir = os.path.join(multimedia.package_folder, multimedia.cpp_info.libdirs[0])
        qtbase_libdir = os.path.join(qtbase.package_folder, "lib")
        test_bin = os.path.join(
            self.cpp.build.bindirs[0] if self.cpp.build.bindirs else ".",
            "test_qt5_qtmultimedia",
        )
        library_paths = [
            libdir, qtbase_libdir, os.environ.get("LD_LIBRARY_PATH"),
        ]
        os.environ["LD_LIBRARY_PATH"] = ":".join(
            path for path in library_paths if path
        )
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        self.run(test_bin, ignore_errors=False)
