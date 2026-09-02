import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Qt5QtchartsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # qt5-qtbase 与 qt5-qtdeclarative 必须作为 test_package 的直接依赖声明：
        # 在传递依赖场景（qt5-qtcharts 为 shared-library 且仅通过 cpp_info.requires
        # 引用 qt5-qtbase::Qt5* 组件）下，CMakeDeps 生成的聚合 Qt5 数据会丢失组件
        # include dirs 与 libs（Qt5Config.cmake 中 Qt5::Core/Qt5::Widgets 为空壳），
        # 且不生成 per-component 的 Qt5CoreConfig.cmake。
        # 与已验证的 qt5-qtdeclarative/5.15.2 test_package 相同，将依赖声明为直接
        # 依赖后 CMakeDeps 会生成完整的 per-component 配置，Qt5::Core/Qt5::Widgets
        # 携带正确的 include dirs 与库，test 方能编译/链接/运行。
        self.requires("qt5-qtbase/5.15.2.2")
        self.requires("qt5-qtdeclarative/5.15.2")

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
        charts = self.dependencies["qt5-qtcharts"]
        qtbase = self.dependencies["qt5-qtbase"]
        qtdeclarative = self.dependencies["qt5-qtdeclarative"]
        libdir = os.path.join(charts.package_folder, charts.cpp_info.libdirs[0])
        qtbase_libdir = os.path.join(qtbase.package_folder, "lib")
        qtd_libdir = os.path.join(qtdeclarative.package_folder, "lib")
        test_bin = os.path.join(
            self.cpp.build.bindirs[0] if self.cpp.build.bindirs else ".",
            "test_qt5_qtcharts",
        )
        library_paths = [
            libdir, qtbase_libdir, qtd_libdir, os.environ.get("LD_LIBRARY_PATH"),
        ]
        os.environ["LD_LIBRARY_PATH"] = ":".join(
            path for path in library_paths if path
        )
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = os.path.join(
            qtbase.package_folder, "plugins", "platforms"
        )
        os.environ["QML2_IMPORT_PATH"] = os.path.join(
            charts.package_folder, "qml"
        )
        self.run(test_bin, ignore_errors=False)
