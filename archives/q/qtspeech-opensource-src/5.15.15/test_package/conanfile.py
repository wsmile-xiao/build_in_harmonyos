import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class QtSpeechTestConan(ConanFile):
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
        speech_dep = self.dependencies["qtspeech-opensource-src"]
        qtbase = self.dependencies["qt5-qtbase"]
        qtdecl = self.dependencies["qt5-qtdeclarative"]

        # Set up LD_LIBRARY_PATH for Qt5 shared libraries
        speech_libdir = os.path.join(speech_dep.package_folder, "lib")
        qtbase_libdir = os.path.join(qtbase.package_folder, "lib")
        qtdecl_libdir = os.path.join(qtdecl.package_folder, "lib")
        library_paths = [speech_libdir, qtdecl_libdir, qtbase_libdir,
                         os.environ.get("LD_LIBRARY_PATH")]
        ld_path = ":".join(path for path in library_paths if path)

        # Set up plugin path for TTS backends (mock backend)
        plugin_paths = []
        for dep in [speech_dep, qtbase, qtdecl]:
            p = os.path.join(dep.package_folder, "plugins")
            if os.path.isdir(p):
                plugin_paths.append(p)
        qt_plugin_path = ":".join(plugin_paths)

        test_bin = os.path.join(
            self.cpp.build.bindirs[0] if self.cpp.build.bindirs else ".",
            "test_qtspeech_opensource_src",
        )
        self.run(
            f'LD_LIBRARY_PATH="{ld_path}" '
            f'QT_PLUGIN_PATH="{qt_plugin_path}" '
            f'QT_QPA_PLATFORM=offscreen '
            f'"{test_bin}"',
            ignore_errors=False
        )
