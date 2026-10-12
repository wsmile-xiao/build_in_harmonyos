import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Qt5QtsensorsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # qt5-qtbase 必须作为 test_package 的直接依赖声明：
        # 与 qt5-qtmultimedia/qt5-qtdeclarative test_package 相同的处理，
        # CMakeDeps 才生成完整的 per-component Qt5Core/Qt5Gui 配置。
        self.requires("qt5-qtbase/5.15.2.2")
        # QML 消费者侧断言链接 Qt5Qml（QtSensors QML 模块依赖）
        self.requires("qt5-qtdeclarative/5.15.2")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # OHOS 工具链默认将 CMAKE_SYSTEM_NAME 映射为 HarmonyOS，
        # 强制回 Linux + aarch64 以复用 Linux 平台语义的 Qt5 config
        # 发现路径（adamstark-audiofile 先例模式）
        tc = CMakeToolchain(self)
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            if str(self.settings.arch) in ("armv8", "aarch64"):
                tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
            else:
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
        sensors = self.dependencies["qt5-qtsensors"]
        qtbase = self.dependencies["qt5-qtbase"]
        qtdecl = self.dependencies["qt5-qtdeclarative"]
        libdir = os.path.join(sensors.package_folder, sensors.cpp_info.libdirs[0])
        # 运行期库路径：本包 + qtbase + qtdeclarative（OHOS conanrun
        # 环境不自动设置，需显式拼接）
        library_paths = [
            libdir,
            os.path.join(qtbase.package_folder, "lib"),
            os.path.join(qtdecl.package_folder, "lib"),
            os.environ.get("LD_LIBRARY_PATH"),
        ]
        os.environ["LD_LIBRARY_PATH"] = ":".join(
            path for path in library_paths if path
        )
        # QML 导入路径：QtSensors 模块 + 其依赖的 QtQml/QtQuick 基础模块
        qml_paths = [
            os.path.join(sensors.package_folder, "qml"),
            os.path.join(qtdecl.package_folder, "qml"),
        ]
        os.environ["QML_IMPORT_PATH"] = ":".join(qml_paths)
        os.environ["QML2_IMPORT_PATH"] = ":".join(qml_paths)
        # 插件路径：软件手势识别插件 + generic 纯软件后端
        # （包内已通过 SENSORS_PLUGINS=generic 裁剪 iio-sensor-proxy
        #   硬件后端，避免无系统 D-Bus 环境下加载崩溃）
        os.environ["QT_PLUGIN_PATH"] = os.path.join(
            sensors.package_folder, "plugins"
        )
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        test_bin = os.path.join(
            self.cpp.build.bindirs[0] if self.cpp.build.bindirs else ".",
            "test_qt5_qtsensors",
        )
        self.run(test_bin, ignore_errors=False)
