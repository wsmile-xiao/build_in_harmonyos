#!/usr/bin/env python3
"""Conan recipe for qtquickeffectmaker (QQEM) 6.11.1 on HarmonyOS PC (arm64).

qtquickeffectmaker（Qt Quick Effect Maker，QQEM）是 Qt 官方的 QML 着色器
特效编辑器。Qt 6.11.1 模块，CMake 构建（qt_build_repo），BSD-3-Clause。

OHOS 适配（参考 qtdeclarative 6.11.1 配方模式）:
- 依赖制品仓已发布包：qtbase/6.11.1（含 Qt6BuildInternals，提供
  qt_internal_* 构建宏）、qtdeclarative/6.11.1（Qt::Quick/Qml）、
  qtshadertools/6.11.1（Qt::ShaderTools）；qtquick3d 为上游可选依赖
  （Quick3DGlslParserPrivate 仅用于语法高亮，缺失不影响构建）;
- CMake 无 Platform/HarmonyOS.cmake：通过 toolchain block 把系统呈现为
  Linux 并设 CMAKE_CROSSCOMPILING=FALSE——上游 CMakeLists 在
  CMAKE_CROSSCOMPILING 时会跳过整个构建;
- CMAKE_PREFIX_PATH 指向 qtbase，QT_ADDITIONAL_PACKAGES_PREFIX_PATH 指向
  qtdeclarative/qtshadertools 包;
- 产物：libQt6QuickEffectMaker 库 + QtQuickEffectMaker QML 模块 +
  defaultnodes 节点资源（qt_copy_or_install 复制到 QML 安装目录）。
"""
import os
import shutil
import stat
import subprocess
import tempfile
import textwrap

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.cmake.toolchain.blocks import Block
from conan.tools.env import Environment
from conan.tools.files import get


class QtquickeffectmakerConan(ConanFile):
    name = "qtquickeffectmaker"
    version = "6.11.1"
    description = "Qt Quick Effect Maker (QQEM) for creating custom shader effects"
    license = "BSD-3-Clause"
    homepage = "https://code.qt.io/cgit/qt/qtquickeffectmaker.git"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("qtdeclarative/6.11.1")
        self.requires("qtshadertools/6.11.1")

    def validate(self):
        if self.settings.os != "OHOS":
            raise ConanInvalidConfiguration(
                "qtquickeffectmaker/6.11.1 in this recipe is a HarmonyOS PC adaptation"
            )

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)

        # 上游 CMakeLists 在 CMAKE_CROSSCOMPILING 时跳过整个构建；
        # CMake 无 Platform/HarmonyOS.cmake。把平台呈现为 Linux 并
        # 置 CMAKE_CROSSCOMPILING=FALSE（同 qtdeclarative 6.11.1 配方，
        # OHOS clang 驱动仍目标 aarch64-unknown-linux-ohos）。
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

        qtbase_pkg = self.dependencies["qtbase"].package_folder
        qml_pkg = self.dependencies["qtdeclarative"].package_folder
        shadertools_pkg = self.dependencies["qtshadertools"].package_folder
        tc.cache_variables.update(
            {
                "CMAKE_PREFIX_PATH": qtbase_pkg,
                "QT_ADDITIONAL_PACKAGES_PREFIX_PATH": f"{qml_pkg};{shadertools_pkg}",
                "BUILD_SHARED_LIBS": "ON" if self.options.shared else "OFF",
                "QT_BUILD_TESTS": "OFF",
                "QT_BUILD_EXAMPLES": "OFF",
                "QT_BUILD_EXAMPLES_BY_DEFAULT": "OFF",
            }
        )
        tc.generate()

        # qsb 等 Qt 构建期宿主工具需要 qtbase/qtshadertools 的 lib 在
        # LD_LIBRARY_PATH 上以解析 libQt6Core 等。
        env = Environment()
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(qtbase_pkg, "lib"))
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(shadertools_pkg, "lib"))
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(qml_pkg, "lib"))
        env.vars(self).save_script("conanbuild_qt_libs")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        if str(self.settings.os) == "OHOS":
            self._sign_installed_elfs()

    def _sign_installed_elfs(self):
        """Re-sign installed OHOS ELF executables and shared objects."""
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
                prefix=".conan-sign-", dir=os.path.dirname(binary)
            ) as temp_dir:
                unsigned = os.path.join(temp_dir, "unsigned")
                signed = os.path.join(temp_dir, "signed")
                shutil.copy2(binary, unsigned)
                if self._has_codesign_section(objdump, unsigned):
                    self._run_tool(
                        [objcopy, "--remove-section", ".codesign", unsigned],
                        f"remove the old code signature from {binary}",
                    )
                self._run_tool(
                    [
                        signer,
                        "sign",
                        "-inFile",
                        unsigned,
                        "-outFile",
                        signed,
                        "-selfSign",
                        "1",
                    ],
                    f"sign {binary}",
                )
                if not os.path.isfile(signed) or self._elf_type(signed) not in (2, 3):
                    raise ConanInvalidConfiguration(
                        f"Signing did not produce a runnable ELF file for {binary}"
                    )
                if not self._has_codesign_section(objdump, signed):
                    raise ConanInvalidConfiguration(
                        f"Signing did not add a .codesign section to {binary}"
                    )
                os.replace(signed, binary)
                os.chmod(binary, original_mode)

    def _has_codesign_section(self, objdump, path):
        section_table = self._run_tool(
            [objdump, "-h", path], f"inspect ELF sections in {path}"
        )
        return any(".codesign" in line.split() for line in section_table.splitlines())

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

    def package_info(self):
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
