import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Qt5QtwebsocketsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # qt5-qtbase 必须作为 test_package 的直接依赖声明：与
        # qt5-qtmultimedia/qt5-qtcharts 相同，CMakeDeps 才会生成完整的
        # per-component Qt5Core/Qt5Network 配置（聚合 Qt5Config 中
        # Qt5::Core 为空壳的问题）。
        self.requires("qt5-qtbase/5.15.2.2")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # OHOS conan 生成的工具链把 CMAKE_SYSTEM_NAME 映射为 HarmonyOS，
        # 而 qmake install 阶段生成的 Qt5WebSocketsConfig.cmake 按普通
        # Linux Qt5 包布局编写（find_package(Qt5) 平台检查走 Linux 分支）。
        # 双覆盖：CMAKE_SYSTEM_NAME=Linux + CMAKE_SYSTEM_PROCESSOR=arch，
        # 与 adamstark-audiofile/adios2 等 OHOS 先例一致。
        if self.settings.os in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = str(self.settings.arch)
        tc.generate()

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
        websockets = self.dependencies["qt5-qtwebsockets"]
        qtbase = self.dependencies["qt5-qtbase"]
        libdir = os.path.join(
            websockets.package_folder, websockets.cpp_info.libdirs[0]
        )
        qtbase_libdir = os.path.join(qtbase.package_folder, "lib")
        test_bin = os.path.join(
            self.cpp.build.bindirs[0] if self.cpp.build.bindirs else ".",
            "test_qt5_qtwebsockets",
        )
        library_paths = [
            libdir, qtbase_libdir, os.environ.get("LD_LIBRARY_PATH"),
        ]
        os.environ["LD_LIBRARY_PATH"] = ":".join(
            path for path in library_paths if path
        )
        self.run(test_bin, ignore_errors=False)
