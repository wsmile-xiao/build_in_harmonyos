#!/usr/bin/env python3
"""Conan recipe for qastools 1.4.0 — Qt6-based ALSA GUI tools for HarmonyOS PC.

qastools bundles three GUI applications (qasmixer / qashctl / qasconfig) built
with CMake >= 3.25 against Qt6 (Core/Gui/Widgets/Svg/Network/DBus/LinguistTools),
alsa-lib and libudev.

Key adaptations (see knowledge/qastools.md):
  - R36: qtbase must be a dbus variant (qtbase-sql-dbus/6.11.1); the plain
    qtbase/6.11.1 ships FEATURE_dbus=OFF and its Qt6Config.cmake rejects
    find_package(Qt6 COMPONENTS DBus).
  - R26-style: udev is satisfied by the static libudev-zero/1.0.4 drop-in
    (libudev.a + libudev.h), no systemd required.
  - E438: qtbase ships its own relocatable Qt6Config.cmake, so CMAKE_PREFIX_PATH
    must point at the qtbase package folder and CMAKE_MODULE_PATH at its
    lib/cmake/Qt6/platforms directory (Platform/HarmonyOS.cmake includes Linux).
  - E237: the udev sound-card hotplug monitor degrades gracefully at runtime
    when no udev daemon exists (source already handles a NULL monitor); noted
    in notes.md, no source patch needed.
  - FIND_PACKAGE(UnixCommands REQUIRED) resolves through the toolchain (gzip),
    so no CMAKE_DISABLE_FIND_PACKAGE_UnixCommands override is needed.
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class QasToolsConan(ConanFile):
    name = "qastools"
    version = "1.4.0"
    description = (
        "QasTools: Qt-based mixer and setup tools for the Linux sound system ALSA"
        " (QasMixer, QasHctl, QasConfig)"
    )
    license = "MIT"
    homepage = "https://gitlab.com/sebholt/qastools"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        # qastools only produces executables; the shared option exists for
        # CMake's BUILD_SHARED_LIBS plumbing only (there is no library target).
        if self.options.shared:
            self.options["qtbase-sql-dbus"].shared = True

    def layout(self):
        cmake_layout(self, src_folder=".")

    def requirements(self):
        # E323/E441: DBus component requires the qtbase dbus variant.
        self.requires("qtbase-sql-dbus/6.11.1")
        self.requires("qtsvg/6.11.1")
        self.requires("alsa-lib/1.2.16.1")
        # System-name library "udev" is served by the static drop-in.
        self.requires("libudev-zero/1.0.4")

    def validate(self):
        if self.settings.os != "OHOS":
            raise ConanInvalidConfiguration(
                "qastools/1.4.0 in this recipe is a HarmonyOS PC adaptation"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # qtbase ships its own relocatable Qt6Config.cmake (cmake_find_mode
        # "none"); expose its package dir to CMake directly.
        qtbase_prefix = self.dependencies["qtbase-sql-dbus"].package_folder
        qtsvg_prefix = self.dependencies["qtsvg"].package_folder
        tc.cache_variables["CMAKE_PREFIX_PATH"] = (
            qtbase_prefix + os.pathsep + qtsvg_prefix
        )
        # Set Qt6_DIR / Qt6Svg_DIR directly so all subdirectory CMakeLists.txt
        # can find Qt6Config.cmake / Qt6SvgConfig.cmake even when
        # CMAKE_PREFIX_PATH is not propagated to nested add_subdirectory.
        tc.cache_variables["Qt6_DIR"] = os.path.join(
            qtbase_prefix, "lib", "cmake", "Qt6"
        )
        tc.cache_variables["Qt6Svg_DIR"] = os.path.join(
            qtsvg_prefix, "lib", "cmake", "Qt6Svg"
        )
        # Platform/HarmonyOS.cmake (include Linux) lives under qtbase's cmake
        # dir; without it CMake treats HarmonyOS as an unknown platform.
        tc.cache_variables["CMAKE_MODULE_PATH"] = os.path.join(
            qtbase_prefix, "lib", "cmake", "Qt6", "platforms"
        )
        udev_prefix = self.dependencies["libudev-zero"].package_folder
        tc.cache_variables.update(
            {
                # udev is a static-only system-name library (libudev-zero);
                # expose the absolute path under _CACHE so the subdirectory
                # patches (0004/0005) can pick it up without the SET() in
                # qashctl/qasmixer CMakeLists.txt clobbering it.
                "UDEV_LIBRARIES_CACHE": os.path.join(udev_prefix, "lib", "libudev.a"),
                # Expose alsa-lib and libudev-zero include dirs so
                # #include <alsa/asoundlib.h> and #include <libudev.h>
                # resolve without pkg-config in subdirectory CMakeLists.
                "ALSA_INCLUDE_DIRS": os.path.join(
                    self.dependencies["alsa-lib"].package_folder, "include"
                ),
                "UDEV_INCLUDE_DIRS": os.path.join(
                    self.dependencies["libudev-zero"].package_folder, "include"
                ),
            }
        )
        tc.generate()
        # Generate CMakeDeps for alsa-lib and libudev-zero so that
        # target_link_libraries can use imported targets with include dirs.
        cd = CMakeDeps(self)
        cd.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # E077: OHOS 内核只允许加载带有效 .codesign 签名的 ELF；用户存储路径的
        # 未签名 ELF 在执行时被拒（execve EPERM，rc=126）。三个 GUI 二进制在打包
        # 期自签，使 test_package 的真实 exec 探针（TP-010..013）与后续真机/桌面
        # 安装运行均可用（cronutils/1.1 先例；签名输出会丢执行位，须恢复 0o755）。
        bin_dir = os.path.join(self.package_folder, "bin")
        for name in ("qasmixer", "qashctl", "qasconfig"):
            path = os.path.join(bin_dir, name)
            if os.path.isfile(path):
                os.chmod(path, 0o755)
                self._sign_ohos_binary(path)

    def _sign_ohos_binary(self, path):
        if str(self.settings.os) != "OHOS":
            return

        signer = self.conf.get(
            "user.ohos:sign_tool",
            default="",
            check_type=str,
        )
        signer = (
            signer
            or os.environ.get("OHOS_SIGN_TOOL", "")
            or shutil.which("binary-sign-tool")
            or "/data/service/hnp/bin/binary-sign-tool"
        )
        if not os.path.isfile(signer):
            self.output.warning(
                "binary-sign-tool is unavailable; skipping OHOS ELF signing"
            )
            return

        objcopy = self.conf.get(
            "user.ohos:objcopy",
            default="",
            check_type=str,
        )
        objcopy = (
            objcopy
            or os.environ.get("OHOS_OBJCOPY", "")
            or shutil.which("llvm-objcopy")
            or "/data/service/hnp/bin/llvm-objcopy"
        )
        if os.path.isfile(objcopy):
            self.run(
                f'"{objcopy}" --remove-section .codesign "{path}"',
                ignore_errors=True,
            )

        signed = f"{path}.signed"
        self.run(
            f'"{signer}" sign -inFile "{path}" '
            f'-outFile "{signed}" -selfSign 1'
        )
        if not os.path.isfile(signed):
            raise ConanException(f"binary-sign-tool produced no output for {path}")
        os.replace(signed, path)
        os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
