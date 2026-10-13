import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Qt5QtscxmlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # qt5-qtbase 必须作为 test_package 的直接依赖声明：
        # 与 qt5-qtmultimedia/qt5-qtdeclarative test_package 相同的处理，
        # CMakeDeps 才生成完整的 per-component Qt5Core 配置。
        self.requires("qt5-qtbase/5.15.2.2")
        # libQt5Scxml 链接 Qt5Qml（ECMAScript datamodel），运行时需要
        # qtdeclarative 的 lib 与 qml 导入路径。
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
        scxml = self.dependencies["qt5-qtscxml"]
        qtbase = self.dependencies["qt5-qtbase"]
        qtdecl = self.dependencies["qt5-qtdeclarative"]
        scxml_libdir = os.path.join(scxml.package_folder, scxml.cpp_info.libdirs[0])
        qtbase_libdir = os.path.join(qtbase.package_folder, "lib")
        qtdecl_libdir = os.path.join(qtdecl.package_folder, "lib")
        # Deterministic loader paths: the test binary needs libQt5Scxml and
        # its Qt5Qml/Qt5Core dependencies.  The inherited LD_LIBRARY_PATH is
        # NOT propagated: build hosts may carry incompatible libc++ copies
        # in unrelated prefix dirs that shadow the system one (probe-verified
        # failure mode); the system default paths serve everything else.
        os.environ["LD_LIBRARY_PATH"] = ":".join(
            [scxml_libdir, qtbase_libdir, qtdecl_libdir]
        )
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        qml_dir = os.path.join(qtdecl.package_folder, "qml")
        if os.path.isdir(qml_dir):
            os.environ["QML_IMPORT_PATH"] = qml_dir
            os.environ["QML2_IMPORT_PATH"] = qml_dir
        test_bin = os.path.join(
            self.cpp.build.bindirs[0] if self.cpp.build.bindirs else ".",
            "test_qt5_qtscxml",
        )
        self.run(test_bin, ignore_errors=False)
