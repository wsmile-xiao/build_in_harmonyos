import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Qt5QtgamepadTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # qt5-qtbase 必须作为 test_package 的直接依赖声明：与
        # qt5-qtwebsockets/qt5-qtmultimedia/qt5-qtcharts 相同，CMakeDeps
        # 才会生成完整的 per-component Qt5Core/Qt5Gui 配置（聚合
        # Qt5Config 中 Qt5::Core 为空壳的问题）。
        self.requires("qt5-qtbase/5.15.2.2")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # OHOS conan 生成的工具链把 CMAKE_SYSTEM_NAME 映射为 HarmonyOS，
        # 而 qmake install 阶段生成的 Qt5GamepadConfig.cmake 按普通 Linux
        # Qt5 包布局编写（find_package(Qt5) 平台检查走 Linux 分支）。
        # 双覆盖：CMAKE_SYSTEM_NAME=Linux + CMAKE_SYSTEM_PROCESSOR=arch，
        # 与 qtwebsockets/adamstark-audiofile/adios2 等 OHOS 先例一致。
        if str(self.settings.os) in ("Linux", "OHOS", "HarmonyOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            processor = str(self.settings.arch)
            if processor == "armv8":
                processor = "aarch64"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = processor
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
        # Run the test binary directly with LD_LIBRARY_PATH set to the
        # package lib dirs (OHOS conanrun env doesn't set them).
        gamepad = self.dependencies["qt5-qtgamepad"]
        qtbase = self.dependencies["qt5-qtbase"]
        libdir = os.path.join(
            gamepad.package_folder, gamepad.cpp_info.libdirs[0]
        )
        qtbase_libdir = os.path.join(qtbase.package_folder, "lib")
        plugin_path = os.path.join(
            gamepad.package_folder, "plugins", "gamepads", "libevdevgamepad.so"
        )
        test_bin = os.path.join(
            self.cpp.build.bindirs[0] if self.cpp.build.bindirs else ".",
            "test_qt5_qtgamepad",
        )
        library_paths = [
            libdir, qtbase_libdir, os.environ.get("LD_LIBRARY_PATH"),
        ]
        os.environ["LD_LIBRARY_PATH"] = ":".join(
            path for path in library_paths if path
        )
        # 消费者侧 evdev 后端插件（打包产物）绝对路径传给测试进程，
        # QPluginLoader 按路径 dlopen 并校验 IID/Keys 元数据。
        os.environ["QTGAMEPAD_PLUGIN_PATH"] = plugin_path
        self.run(test_bin, ignore_errors=False)
