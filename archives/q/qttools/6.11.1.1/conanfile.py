#!/usr/bin/env python3
"""Conan recipe for Qt Tools (linguist/designer/qdbus/help) 6.11.1 on HarmonyOS PC (arm64)."""

import os
import shlex
import shutil
import stat
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class QttoolsConan(ConanFile):
    name = "qttools"
    version = "6.11.1.1"
    description = "Qt Tools (Linguist, Designer, qdbus, qtpaths, help) for HarmonyOS PC"
    license = "BSD-3-Clause AND LGPL-3.0-only AND GPL-3.0-only"
    homepage = "https://doc.qt.io/qt-6/qttools-index.html"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires(
            "qtbase/6.11.1",
            transitive_headers=True,
            transitive_libs=True,
        )
        # qttools 顶层 find_package(Qt6 OPTIONAL_COMPONENTS Qml Quick Widgets ...)，
        # Linguist/Designer 依赖 qtbase（Gui/Widgets），Qml 工具依赖 qtdeclarative。
        self.requires(
            "qtdeclarative/6.11.1",
            transitive_headers=True,
            transitive_libs=True,
        )

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "qttools/6.11.1 in this recipe is a HarmonyOS PC adaptation"
            )

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        qtbase = self.dependencies["qtbase"].package_folder
        qtdeclarative = self.dependencies["qtdeclarative"].package_folder
        tc.variables["Qt6_DIR"] = os.path.join(qtbase, "lib", "cmake", "Qt6")
        tc.variables["Qt6Declarative_DIR"] = os.path.join(
            qtdeclarative, "lib", "cmake", "Qt6Declarative"
        )
        # ltext2id/trparser 的 QML/JS 转换依赖 Qt::QmlPrivate target；
        # 不显式指定 Qt6Qml_DIR 会得到 NOTFOUND，构建时定义 QT_NO_QML，
        # 导致 ltext2id 忽略 .js/.qml 文件（上游 tst_ltext2id 失败）。
        tc.variables["Qt6Qml_DIR"] = os.path.join(
            qtdeclarative, "lib", "cmake", "Qt6Qml"
        )
        tc.variables["CMAKE_FIND_ROOT_PATH_MODE_PACKAGE"] = "BOTH"
        if self.settings.os == "OHOS":
            tc.variables["QT_QMAKE_TARGET_MKSPEC"] = "harmonyos-clang"
        tc.variables["QT_BUILD_TESTS"] = False
        tc.variables["QT_BUILD_TESTS_BY_DEFAULT"] = False
        tc.variables["QT_BUILD_EXAMPLES"] = False
        tc.variables["QT_BUILD_EXAMPLES_BY_DEFAULT"] = False
        tc.variables["QT_BUILD_BENCHMARKS"] = False
        tc.variables["QT_BUILD_MANUAL_TESTS"] = False
        # qttools 引用 qtdeclarative 的 SBOM 外部文档（spdx）在 install 阶段找不到，
        # 禁用 SBOM 生成（E324 先例）。
        tc.variables["QT_GENERATE_SBOM"] = False
        tc.generate()
        VirtualRunEnv(self).generate()

    def _ctest_executable(self):
        for candidate in (
            shutil.which("ctest"),
            "/data/service/hnp/bin/ctest",
            "/data/service/hnp/cmake.org/cmake_4.1.2/bin/ctest",
        ):
            if (
                candidate
                and os.path.isfile(candidate)
                and os.access(candidate, os.X_OK)
            ):
                return candidate
        raise ConanInvalidConfiguration("ctest executable was not found")

    def _locate_build_dir(self, rel_path):
        """Locate a directory inside the CMake build tree regardless of generator layout."""
        candidates = [
            os.path.join(self.build_folder, rel_path),
            os.path.join(self.build_folder, "Release", rel_path),
            os.path.join(self.build_folder, "Debug", rel_path),
        ]
        for candidate in candidates:
            if os.path.isdir(candidate):
                return candidate
        return candidates[0]

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        self._ensure_soname_symlinks()
        if str(self.settings.os) == "OHOS":
            self._sign_installed_elfs()

    def _ensure_soname_symlinks(self):
        """Ensure libQt6Help.so / .so.6 links exist (E215: HMDFS breaks
        relative symlinks during install)."""
        libdir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(libdir):
            return
        for root, _, filenames in os.walk(libdir):
            for filename in filenames:
                if not filename.startswith("libQt6Help.so.6.11.1"):
                    continue
                real = os.path.join(root, filename)
                for link_name in ("libQt6Help.so.6", "libQt6Help.so"):
                    link = os.path.join(root, link_name)
                    if not os.path.lexists(link):
                        os.symlink(filename, link)

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
                timeout=120,
            )
        except subprocess.TimeoutExpired:
            raise ConanInvalidConfiguration(f"Timed out while trying to {action}")
        if result.returncode != 0:
            raise ConanInvalidConfiguration(
                f"Failed to {action}: {result.stderr.strip()}"
            )
        return result.stdout

    @staticmethod
    def _elf_type(path):
        try:
            with open(path, "rb") as f:
                ident = f.read(16)
            if len(ident) < 16 or ident[:4] != b"\x7fELF":
                return 0
            e_type = int.from_bytes(ident[16:18], "little")
            return e_type
        except (OSError, IndexError):
            return 0

    def _resolve_tool(self, env_name, default):
        tool = os.environ.get(env_name, "") or default
        resolved = shutil.which(tool)
        if resolved:
            return resolved
        for candidate in (f"/data/service/hnp/bin/{tool}", f"/data/service/hnp/{tool}"):
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        raise ConanInvalidConfiguration(
            f"Required tool '{tool}' ({env_name}) was not found"
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        help_cmake = self.cpp_info.components["help"]
        help_cmake.set_property("cmake_target_name", "Qt6::Help")
        help_cmake.libs = ["Qt6Help"]
        help_cmake.builddirs = [os.path.join("lib", "cmake")]
        linguisttools = self.cpp_info.components["linguisttools"]
        linguisttools.set_property("cmake_target_name", "Qt6::LinguistTools")
        linguisttools.builddirs = [os.path.join("lib", "cmake")]
        # bin/ 工具（lrelease/lupdate/qtpaths/qdbus 等）由下游通过
        # find_package(Qt6 COMPONENTS LinguistTools) 或直接 PATH 使用。
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
