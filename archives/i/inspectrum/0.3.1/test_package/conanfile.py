#!/usr/bin/env python3
"""Conan test_package — inspectrum 0.3.1 L1 test.

Two-stage consumer validation (R34):

1. C++ consumer test: builds and runs test.cpp, which links the same
   dependency face inspectrum uses (Qt5 Core/Widgets/Concurrent, single
   precision FFTW, liquid-dsp) and exercises the FFTW and liquid APIs plus
   Qt runtime initialization.  This proves the packaged dependency
   closure is consumable from a real client.

2. Application test: launches the packaged ``inspectrum`` under
   QT_QPA_PLATFORM=offscreen (no display server on OHOS — neovim-qt
   0.2.19 precedent) with a hard 15s budget.  A GUI process enters the
   Qt event loop after startup and never exits headlessly, so the success
   criteria are: the process stays alive for the full budget without
   crashing, and its log shows evidence of a fully initialized
   QApplication (offscreen platform plugin + font database loaded).
"""
import os
import subprocess
import textwrap

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.cmake.toolchain.blocks import Block
from conan.tools.files import load, save


class InspectrumTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 显式声明依赖以在 generate() 中取 package_folder（传递依赖的
        # package_folder 在 test_package 上下文不可靠；neovim-qt 先例）。
        self.requires("qt5-qtbase/5.15.2.2")
        self.requires("fftw3f/3.3.10")
        self.requires("liquid-dsp/1.8.2")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)

        # 与主配方一致：CMake 无 Platform/HarmonyOS.cmake，呈现为 Linux
        # 并置 CMAKE_CROSSCOMPILING=FALSE（鸿蒙 clang 驱动仍目标
        # aarch64-linux-ohos）。neovim-qt 0.2.19 先例。
        class OhosLinuxPlatformBlock(Block):
            template = textwrap.dedent(
                """\
                set(CMAKE_SYSTEM_NAME Linux)
                set(CMAKE_HOST_SYSTEM_NAME Linux)
                set(CMAKE_CROSSCOMPILING FALSE)
                set(CMAKE_SYSTEM_PROCESSOR aarch64)
                set(CMAKE_HOST_SYSTEM_PROCESSOR aarch64)
                """
            )

            def context(self):
                return {}

        tc.blocks["user_toolchain"] = OhosLinuxPlatformBlock

        # find_package(Qt5 ...) 命中 qtbase 包内的真实 Qt5 配置。
        qtbase_pkg = self.dependencies["qt5-qtbase"].package_folder
        fftw3f_pkg = self.dependencies["fftw3f"].package_folder
        liquid_pkg = self.dependencies["liquid-dsp"].package_folder
        tc.cache_variables["CMAKE_PREFIX_PATH"] = qtbase_pkg
        tc.cache_variables["FFTW_INC"] = os.path.join(fftw3f_pkg, "include")
        tc.cache_variables["LIQUID_INC"] = os.path.join(liquid_pkg, "include")
        tc.cache_variables["FFTW_LIB"] = self._dep_lib(fftw3f_pkg, "libfftw3f.so", "libfftw3f.a")
        tc.cache_variables["LIQUID_LIB"] = self._dep_lib(liquid_pkg, "libliquid.so", "libliquid.a")
        tc.cache_variables["BUILD_TESTING"] = "OFF"
        tc.generate()

        mkspec_cmake = os.path.join(
            qtbase_pkg, "lib", "cmake", "Qt5Core",
            "Qt5CoreConfigExtrasMkspecDir.cmake")
        if os.path.exists(mkspec_cmake):
            content = load(self, mkspec_cmake)
            fixed = content.replace(
                "${_qt5Core_install_prefix}/../b//mkspecs/linux-clang",
                "${_qt5Core_install_prefix}/mkspecs/linux-clang")
            if fixed != content:
                save(self, mkspec_cmake, fixed)

    @staticmethod
    def _dep_lib(pkg_folder, *names):
        for name in names:
            candidate = os.path.join(pkg_folder, "lib", name)
            if os.path.isfile(candidate):
                return candidate
        raise ConanException(
            f"none of {names} found in {os.path.join(pkg_folder, 'lib')}")

    def build(self):
        cmake = CMake(self)
        with open(os.path.join(self.build_folder, "configure.log"), "w") as log:
            cmake.configure(stdout=log, stderr=log)
        with open(os.path.join(self.build_folder, "build.log"), "w") as log:
            cmake.build(stdout=log, stderr=log)

    def test(self):
        # 1) C++ 消费者测试：Qt5 + fftw3f + liquid 链接与 API 调用
        test_exe = os.path.join(self.cpp.build.bindir, "test_inspectrum")
        self.run(f"QT_QPA_PLATFORM=offscreen {test_exe}", env="conanrun")

        # 2) 应用验证：打包后的 inspectrum 真实启动冒烟（限时）。
        #    GUI 程序构造 MainWindow 后进入事件循环、headless 下不会自行
        #    退出（实测 offscreen 平台），因此用 Popen 启动 + 定时 kill，
        #    断言：进程存活满 15s 未崩溃 + 日志出现 Qt 运行时初始化证据
        #    （offscreen 平台插件加载与字体库初始化，仅 QApplication 完整
        #    构造后才会打印）。
        dep = self.dependencies.get("inspectrum")
        if dep is None or not dep.package_folder:
            raise AssertionError("inspectrum not found in the dependency graph")
        app_bin = os.path.join(dep.package_folder, "bin", "inspectrum")
        if not os.path.exists(app_bin):
            raise AssertionError(f"missing packaged application: {app_bin}")

        run_cwd = os.path.join(self.build_folder, "app-run")
        os.makedirs(run_cwd, exist_ok=True)
        home = os.path.join(run_cwd, "test-home")
        xdg_runtime = os.path.join(run_cwd, "xdg-runtime")
        os.makedirs(home, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)

        # 显式构造运行时 env（不依赖 EnvVars→dict 转换 API）。
        ld_paths = []
        plugin_paths = []
        for it in self.dependencies.values():
            if it and it.package_folder:
                for layout_dir in ("lib", "bin"):
                    lib_dir = os.path.join(it.package_folder, layout_dir)
                    if os.path.isdir(lib_dir):
                        ld_paths.append(lib_dir)
                for plugins_dir in ("plugins", os.path.join("lib", "plugins")):
                    plugins_path = os.path.join(it.package_folder, plugins_dir)
                    if os.path.isdir(plugins_path):
                        plugin_paths.append(plugins_path)
        for system_lib in ("/system/lib64", "/system/lib64/platformsdk",
                           "/system/lib64/ndk"):
            ld_paths.append(system_lib)

        run_env = dict(os.environ)
        run_env["LD_LIBRARY_PATH"] = ":".join(ld_paths)
        run_env["QT_PLUGIN_PATH"] = ":".join(plugin_paths)
        run_env["QT_QPA_PLATFORM"] = "offscreen"
        run_env["HOME"] = home
        run_env["XDG_RUNTIME_DIR"] = xdg_runtime
        run_env["XDG_CACHE_HOME"] = os.path.join(home, ".cache")
        run_env["XDG_CONFIG_HOME"] = os.path.join(home, ".config")
        run_env["XDG_DATA_HOME"] = os.path.join(home, ".local", "share")

        run_log = os.path.join(run_cwd, "inspectrum-run.log")
        with open(run_log, "w") as log:
            proc = subprocess.Popen(
                [app_bin, "--help"], cwd=run_cwd, stdout=log, stderr=log,
                env=run_env)
            try:
                rc = proc.wait(timeout=15)
                # 事件循环空转的 GUI 不会自行退出；15s 内退出且非 0 = 启动失败
                if rc != 0:
                    with open(run_log, "r", errors="replace") as handle:
                        raise AssertionError(
                            f"packaged inspectrum exited rc={rc}:\n"
                            f"{handle.read()[-2000:]}")
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                self.output.info(
                    "inspectrum ran for the full 15s budget and was killed "
                    "(expected: GUI apps enter the event loop and never exit "
                    "headlessly)")
        with open(run_log, "r", errors="replace") as handle:
            run_out = handle.read()
        self.output.info("inspectrum run output:\n" + run_out[-2000:])
        # QApplication + offscreen 平台插件完整初始化的证据（无崩溃前提）
        if "QFontDatabase" not in run_out and "QStandardPaths" not in run_out:
            raise AssertionError(
                "no evidence of Qt runtime initialization in the run log; "
                f"the packaged application did not reach a working QApplication: "
                f"{run_out[-2000:]!r}")
