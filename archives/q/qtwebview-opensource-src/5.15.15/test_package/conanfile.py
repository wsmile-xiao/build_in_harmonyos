import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class QtWebViewTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)
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
        webview_dep = self.dependencies["qtwebview-opensource-src"]
        qtbase = self.dependencies["qt5-qtbase"]
        qtdecl = self.dependencies["qt5-qtdeclarative"]

        # Set up LD_LIBRARY_PATH for Qt5 shared libraries
        webview_libdir = os.path.join(webview_dep.package_folder, "lib")
        qtbase_libdir = os.path.join(qtbase.package_folder, "lib")
        qtdecl_libdir = os.path.join(qtdecl.package_folder, "lib")
        library_paths = [webview_libdir, qtdecl_libdir, qtbase_libdir,
                         os.environ.get("LD_LIBRARY_PATH")]
        ld_path = ":".join(path for path in library_paths if path)

        test_bin = os.path.join(
            self.cpp.build.bindirs[0] if self.cpp.build.bindirs else ".",
            "test_qtwebview_opensource_src",
        )
        self.run(
            f'LD_LIBRARY_PATH="{ld_path}" '
            f'"{test_bin}"',
            ignore_errors=False
        )
