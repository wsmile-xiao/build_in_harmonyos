#!/usr/bin/env python3
"""Conan recipe — kcolorpicker 0.3.1 (ksnip kColorPicker, Qt color picker widget).

kColorPicker 提供 Qt Widgets 取色按钮/弹出取色板控件，是 kImageAnnotator
0.7.x 的直接依赖（下游契约：find_package(kColorPicker-Qt6 0.3.1 REQUIRED)
+ kColorPicker::kColorPicker）。
构建系统：CMake >= 3.5，C++17，AUTOMOC/AUTORCC
产物：libkColorPicker.so（VERSION 0.3.1 / SOVERSION 0）
平台：OHOS aarch64；唯一外部依赖 qtbase/6.11.1（Qt6 Widgets 组件）。
"""

import os
import shutil
import stat
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import get


class KColorPickerConan(ConanFile):
    name = "kcolorpicker"
    version = "0.3.1"
    description = "kcolorpicker — ksnip Qt color picker widget library (Qt6)"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/ksnip/kColorPicker"
    url = "https://github.com/ksnip/kColorPicker"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def requirements(self):
        self.requires("qtbase/6.11.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # qtbase cmake_find_mode=none（自带 relocatable Qt6Config.cmake），
        # 显式把 Qt6 顶层与组件 DIR 指向 qtbase 包内 config 目录
        # （karchive/6.19.0 与 qtsvg/6.11.1 消费先例）
        qtbase_cmake = os.path.join(
            self.dependencies["qtbase"].package_folder, "lib", "cmake")
        tc.cache_variables["Qt6_DIR"] = os.path.join(qtbase_cmake, "Qt6")
        tc.cache_variables["Qt6Widgets_DIR"] = os.path.join(qtbase_cmake, "Qt6Widgets")
        # BUILD_TESTS=ON 时上游会 find_package(Qt6 COMPONENTS Test)
        tc.cache_variables["Qt6Test_DIR"] = os.path.join(qtbase_cmake, "Qt6Test")
        # SONAME 修复（知识命中 DRAFT-expat-cmake-soname-1912 / expat #1912）：
        # CMake 4.1 无 HarmonyOS 平台模块（configure 时报 "System is unknown
        # to cmake"），不定义 CMAKE_SHARED_LIBRARY_SONAME_*_FLAG —— 产物缺
        # DT_SONAME，导出 target 带 IMPORTED_NO_SONAME，下游链接器把包缓存
        # 绝对路径写进 DT_NEEDED，不可重定位。显式保留 SONAME flag，同时设
        # CMAKE_PLATFORM_NO_VERSIONED_SONAME=ON 跳过版本化软链（HMDFS 路径
        # 上 symlink 创建受限）：产物为带 SONAME 的非版本化 libkColorPicker.so
        tc.cache_variables["CMAKE_PLATFORM_NO_VERSIONED_SONAME"] = "ON"
        tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.variables["BUILD_WITH_QT6"] = "ON"
        # 上游默认 ON，避免多余 example 可执行与签名负担
        tc.variables["BUILD_EXAMPLE"] = "OFF"
        tc.variables["BUILD_TESTS"] = "ON"
        # 输出真实编译/链接行到构建日志，作为链接闭包显式化证据
        # （implement-policy 第 5 条：禁止依赖 lld 隐式 DT_NEEDED 闭包）
        tc.variables["CMAKE_VERBOSE_MAKEFILE"] = "ON"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        # -j1：OHOS 沙箱不支持 mkfifo（jobserver），并行编译失败（opensp 先例）
        cmake.build(build_tool_args=["-j1"])
        # 上游测试：tests/buttons/ColorButtonTest.cpp（QTest，QSignalSpy 验证
        # colorSelected 信号）。上游 CI 用 xvfb-run，设备无显示服务器 →
        # offscreen QPA（qtbase/6.11.1 同机 7 项 Qt Test 全过先例）。
        # 新链接的测试可执行保留链接期有效代码签名；安装后对 ELF 的改动
        # 才会使签名失效需重签（见 _sign_installed_elfs，qtbase 先例）。
        if can_run(self):
            # 链接闭包显式化（implement-policy 第 5 条 / E135 / 知识 E285/E312
            # 运行期先例）：CMake 4.1 无 HarmonyOS 平台模块（Platform/HarmonyOS
            # .cmake 缺失），链接行不产生 -rpath/-rpath-link，且设备默认加载
            # 路径无任何 Qt 库——构建树测试可执行必须经显式 LD_LIBRARY_PATH
            # 解析 libQt6*.so.6（qtbase 包 lib）与构建树 libkColorPicker.so。
            # conanbuild 环境无任何依赖定义 LD_LIBRARY_PATH（已核验 qtbase
            # recipe 无 buildenv_info），apply() 注入不会被 conanbuild.sh 覆盖。
            test_env = Environment()
            test_env.define("QT_QPA_PLATFORM", "offscreen")
            test_env.define("QT_LOGGING_RULES", "qt.qpa.*=false")
            test_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, "lib"))
            test_env.prepend_path(
                "LD_LIBRARY_PATH",
                os.path.join(self.dependencies["qtbase"].package_folder, "lib"))
            with test_env.vars(self).apply():
                self.run("ctest --output-on-failure -j1", cwd=self.build_folder)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        if str(self.settings.os) == "OHOS":
            self._sign_installed_elfs()

    def _sign_installed_elfs(self):
        """Re-sign installed OHOS ELF files (E077 four-step flow).

        CMake install strips the build-tree RPATH, which rewrites the ELF and
        invalidates the link-time .codesign section; altered/unsigned ELF files
        fail to load with "operation not permitted" (E077/E135). Flow:
        remove old signature -> (re)sign -> restore permissions.
        """
        binaries = []
        for root, _, filenames in os.walk(self.package_folder):
            for filename in filenames:
                candidate = os.path.join(root, filename)
                if os.path.islink(candidate):
                    continue
                if self._elf_type(candidate) in (2, 3):  # ET_EXEC, ET_DYN
                    binaries.append(candidate)
        if not binaries:
            return
        objcopy = self._resolve_tool("OBJCOPY", "llvm-objcopy")
        objdump = self._resolve_tool("OBJDUMP", "llvm-objdump")
        signer = self._resolve_tool("BINARY_SIGN_TOOL", "binary-sign-tool")
        for binary in sorted(binaries):
            original_mode = stat.S_IMODE(os.stat(binary).st_mode)
            with tempfile.TemporaryDirectory(
                    prefix=".conan-sign-", dir=os.path.dirname(binary)) as temp_dir:
                unsigned = os.path.join(temp_dir, "unsigned")
                signed = os.path.join(temp_dir, "signed")
                shutil.copy2(binary, unsigned)
                if self._has_codesign_section(objdump, unsigned):
                    self._run_tool(
                        [objcopy, "--remove-section", ".codesign", unsigned],
                        f"remove the old code signature from {binary}")
                self._run_tool(
                    [signer, "sign", "-inFile", unsigned, "-outFile", signed,
                     "-selfSign", "1"],
                    f"sign {binary}")
                if not os.path.isfile(signed) or self._elf_type(signed) not in (2, 3):
                    raise ConanInvalidConfiguration(
                        f"Signing did not produce a runnable ELF file for {binary}")
                if not self._has_codesign_section(objdump, signed):
                    raise ConanInvalidConfiguration(
                        f"Signing did not add a .codesign section to {binary}")
                os.replace(signed, binary)
                os.chmod(binary, original_mode)

    def _has_codesign_section(self, objdump, path):
        section_table = self._run_tool(
            [objdump, "-h", path], f"inspect ELF sections in {path}")
        return any(
            ".codesign" in line.split()
            for line in section_table.splitlines()
        )

    @staticmethod
    def _run_tool(command, action):
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=60,
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise ConanInvalidConfiguration(f"Unable to {action}: {error}") from error
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            raise ConanInvalidConfiguration(
                f"Unable to {action}: {detail or 'tool exited unsuccessfully'}"
            )
        return result.stdout

    @staticmethod
    def _resolve_tool(environment_variable, executable):
        configured = os.environ.get(environment_variable)
        candidate = configured or executable
        resolved = shutil.which(candidate)
        if (
            not resolved
            and os.path.isfile(candidate)
            and os.access(candidate, os.X_OK)
        ):
            resolved = os.path.abspath(candidate)
        if (
            not resolved
            or not os.path.isfile(resolved)
            or not os.access(resolved, os.X_OK)
        ):
            raise ConanInvalidConfiguration(
                f"Required tool {executable} was not found; set "
                f"{environment_variable} or add it to PATH"
            )
        return os.path.abspath(resolved)

    @staticmethod
    def _elf_type(path):
        """Return the ELF e_type value, or None for a non-ELF file."""
        try:
            with open(path, "rb") as binary:
                header = binary.read(18)
        except OSError as error:
            raise ConanInvalidConfiguration(
                f"Unable to inspect installed file {path}: {error}"
            ) from error
        if len(header) < 18 or header[:4] != b"\x7fELF":
            return None
        byte_order = {1: "little", 2: "big"}.get(header[5])
        if byte_order is None:
            raise ConanInvalidConfiguration(
                f"Unsupported ELF byte order in installed file {path}"
            )
        return int.from_bytes(header[16:18], byte_order)

    def package_info(self):
        # 头文件安装在 include/kColorPicker-Qt6/kColorPicker/（上游安装布局），
        # 公共头内部 #include "kColorPicker/KColorPickerExport.h"，
        # 因此 includedirs 指向 include/kColorPicker-Qt6
        self.cpp_info.includedirs = [os.path.join("include", "kColorPicker-Qt6")]
        self.cpp_info.libs = ["kColorPicker"]
        # 下游契约（kImageAnnotator 0.7.2 逐行核验）：
        #   find_package(kColorPicker-Qt6 0.3.1 REQUIRED)
        #   target_link_libraries(... PRIVATE kColorPicker::kColorPicker)
        self.cpp_info.set_property("cmake_file_name", "kColorPicker-Qt6")
        self.cpp_info.set_property("cmake_target_name", "kColorPicker::kColorPicker")
