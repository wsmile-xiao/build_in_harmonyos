import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Qt5QtspeechTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # qt5-qtbase 必须作为 test_package 的直接依赖声明：
        # 与 qt5-qtmultimedia/qt5-qtscxml test_package 相同的处理，
        # CMakeDeps 才生成完整的 per-component Qt5Core 配置。
        self.requires("qt5-qtbase/5.15.2.2")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # CMAKE_SYSTEM_NAME=Linux 强制覆盖（与主配方 build() 内的上游 cmake
        # 套件同款“双覆盖”）：OHOS 适配版 conan 的 CMakeToolchain 默认将
        # OHOS 映射为 CMAKE_SYSTEM_NAME=HarmonyOS，而 Qt5 的 config 文件
        # 与 mkspecs 探测按 Linux 平台路径解析——本地原型实测带 Linux 覆盖
        # 后上游 module_includes ctest 全绿（1/1 Passed）。
        # CMAKE_POLICY_VERSION_MINIMUM=3.5：CMake >= 4 移除了对上游模板
        # cmake_minimum_required(2.8) 的兼容。
        tc = CMakeToolchain(self)
        if str(self.settings.os) in ("Linux", "OHOS"):
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) in ("armv8", "armv8.3")
                else str(self.settings.arch)
            )
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        # Deterministic host-tool environment (same rationale as the
        # qt5-qtscxml recipe notes): the inherited LD_LIBRARY_PATH may
        # carry an incompatible libc++_shared.so copy that shadows the
        # system one needed by host tools (cmake) — probe-verified on the
        # OpenDesk build host ("Error relocating ... symbol not found",
        # rc=127 when /data/storage/el1/bundle/libs/arm64 precedes the
        # musl default search path).  The conanbuild env script expands
        # ${LD_LIBRARY_PATH} from this process, so resetting it here
        # yields a deterministic toolchain+system search path.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compilers.get("cpp") or compilers.get("cxx")
        clean_paths = []
        if compiler:
            toolchain_lib = os.path.normpath(os.path.join(
                os.path.dirname(os.path.realpath(compiler)), "..", "lib"
            ))
            if os.path.isdir(toolchain_lib):
                clean_paths.append(toolchain_lib)
        if os.path.isdir("/system/lib64"):
            clean_paths.append("/system/lib64")
        if clean_paths:
            os.environ["LD_LIBRARY_PATH"] = ":".join(clean_paths)

        cmake = CMake(self)
        variables = {}
        if str(self.settings.os) == "OHOS":
            if compiler:
                compiler_dir = os.path.dirname(os.path.realpath(compiler))
                variables["OHOS_CXX_RUNTIME_DIR"] = os.path.join(
                    compiler_dir, "..", "lib", "aarch64-linux-ohos"
                )
        cmake.configure(variables=variables)
        cmake.build()

    def test(self):
        speech = self.dependencies["qt5-qtspeech"]
        qtbase = self.dependencies["qt5-qtbase"]
        speech_libdir = os.path.join(speech.package_folder, speech.cpp_info.libdirs[0])
        qtbase_libdir = os.path.join(qtbase.package_folder, "lib")
        # Deterministic loader paths（不继承父级 LD_LIBRARY_PATH，防宿主
        # 不兼容 libc++ 副本遮蔽系统真 so——同 qtscxml 先例）
        library_paths = [speech_libdir, qtbase_libdir]
        ld_path = ":".join(library_paths)
        test_bin = os.path.join(
            self.cpp.build.bindirs[0] if self.cpp.build.bindirs else ".",
            "test_qt5_qtspeech",
        )
        self.run(
            f'QT_QPA_PLATFORM=offscreen '
            f'LD_LIBRARY_PATH="{ld_path}" '
            f'"{test_bin}"',
            ignore_errors=False,
        )
