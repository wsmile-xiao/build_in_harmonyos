#!/usr/bin/env python3
"""Conan recipe for plasma-wayland-protocols 1.21.0 — CMake (KDE).

plasma-wayland-protocols (pwp) ships the KDE Plasma Wayland protocol XMLs
plus the PlasmaWaylandProtocols CMake package (find_package consumers read
PLASMA_WAYLAND_PROTOCOLS_DIR). Pure data package — no compiled libraries.

Version note (R37): 1.21.0 is the minimum release satisfying kwin 6.7.2 /
kwayland 6.7.2 (`find_package(PlasmaWaylandProtocols 1.21)`). The ohpcd
registry has no plasma-wayland-protocols package; libkscreen 6.7.2 worked
around that by carrying the 1.21 tarball as a second source — this recipe
makes pwp a first-class package so the kwin dependency chain
(wayland-protocols 1.48 -> pwp 1.21.0 -> kwayland 6.7.2 -> kwin 6.7.2)
can consume it from the registry.

Upstream requirements: CMake >= 3.16, ECM >= 5.69 (NO_MODULE). With
BUILD_TESTING: WaylandScanner + Wayland COMPONENTS Client.

OHOS-specific adaptations:
  - KF_IGNORE_PLATFORM_CHECK=TRUE: OHOS is not in the KDE platform list
    (libkscreen/kdecoration precedent).
  - ECM_MODULE_PATH set manually: the CMakeDeps-generated ECMConfig.cmake
    does not propagate ECM_MODULE_PATH (libkscreen precedent).
  - wayland/1.22.0 instead of a newer wayland: qtbase/6.11.1.x and
    qtwayland/6.11.1 pin wayland/1.22.0 and mixing versions is a graph
    conflict (libkscreen precedent). pwp's find_package(Wayland
    COMPONENTS Client) has no version minimum, 1.22.0 satisfies it.
  - Static wayland-scanner: HMDFS forbids loading shared libraries from
    the Conan cache, so the `wayland` package's scanner (linked against
    libexpat.so/libxml2.so) cannot execute here. The recipe compiles a
    -static scanner (libc-only) from the wayland 1.24.0 source and pins
    WaylandScanner_EXECUTABLE to it (wayland-protocols 1.47/1.48
    precedent), so BUILD_TESTING=ON's autotests run on device.
  - BUILD_TESTING=ON + ctest inside build() (kdecoration 6.7.2
    precedent): the upstream autotests (30 protocols x 4 = 120 tests)
    execute during conan create.
  - conan_cmakedeps_paths.cmake written manually so wayland's cmake dirs
    are on CMAKE_PREFIX_PATH and find_package(Wayland COMPONENTS Client)
    resolves via the CMakeDeps config instead of pkg-config
    (layer-shell-qt precedent, CMAKE_FIND_PACKAGE_PREFER_CONFIG ON).
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)

# wayland 源码版本,用于编译静态 wayland-scanner(wayland-protocols 1.48 同款)
SCANNER_WAYLAND_VERSION = "1.24.0"


class PlasmaWaylandProtocolsConan(ConanFile):
    name = "plasma-wayland-protocols"
    version = "1.21.0"
    description = "KDE Plasma Wayland protocol XML definitions"
    license = "BSD-3-Clause"
    homepage = "https://invent.kde.org/plasma/plasma-wayland-protocols"
    url = "https://invent.kde.org/plasma/plasma-wayland-protocols"

    # 纯 XML 数据包,无编译产物,用 "unknown" 免 shared 选项校验
    # (wayland-protocols 1.48 同款先例)
    package_type = "unknown"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # find_package(Wayland COMPONENTS Client) + autotests 的
        # Wayland_INCLUDE_DIRS。钉 1.22.0 与 qtbase/qtwayland 一致
        # (libkscreen 先例:混用 1.24.0 会图冲突)。
        self.requires("wayland/1.22.0")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # wayland 源码,仅用于编译静态 wayland-scanner
        get(self, **self.conan_data["scanner_sources"],
            strip_root=True, destination="wayland-scanner-src")
        # 零补丁包也保留标准补丁链调用(统一配方口径,G1 检查项;
        # conandata patches: {} 时为空操作)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # BUILD_TESTING=ON -> autotests/CMakeLists.txt 注册
        # 30 协议 x 4 = 120 项测试(build() 里 ctest 直跑)
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"

        # ECM's own installed ECMConfig.cmake sets ECM_MODULE_PATH, but the
        # CMakeDeps-generated ECMConfig.cmake does not. Set it manually so
        # KDEInstallDirs / KDECMakeSettings / ECMSetupVersion are found
        # (libkscreen precedent).
        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        # WaylandScanner_EXECUTABLE: 静态 scanner(仅依赖 libc,HPMS 平台可
        # 执行),build() 里先编译再 configure,configure 时文件已存在。
        # ECM FindWaylandScanner 走 pkg-config 找不到 wayland-scanner.pc,
        # 钉住可执行文件后 Wayland::Scanner 目标成立(libkscreen 先例)。
        tc.variables["WaylandScanner_EXECUTABLE"] = os.path.join(
            self.generators_folder, "wayland-scanner")

        # conan_cmakedeps_paths.cmake: CMakeDeps 不生成(无 qtbase 先例
        # 需要),手工写一份把 wayland 的 cmake 目录加进 CMAKE_PREFIX_PATH,
        # 并让 find_package(Wayland COMPONENTS Client) 走 CMakeDeps config
        # (提供 Wayland_INCLUDE_DIRS 变量供 autotests 使用)。
        lines = ['set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)']
        wayland = self.dependencies.get("wayland")
        if wayland and wayland.package_folder:
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH "{wayland.package_folder}")'
            )
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"{wayland.package_folder}/lib/cmake")'
            )
        if ecm:
            ecm_cmake = os.path.join(
                ecm.package_folder, "share", "ECM", "cmake")
            lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
        lines.append(
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        lines.append(
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

        tc.generate()

    # --- 静态 wayland-scanner(wayland-protocols 1.47/1.48 同款机制) ---

    def _find_expat_static(self):
        """Locate a static libexpat.a for the fully static scanner link.

        The scanner is linked with `-static` so it depends only on libc (HMDFS
        cannot dlopen cache libraries). A static libexpat is therefore
        required. Preference order: the SDK-bundled copy used by the
        wayland-protocols recipes, then any static libexpat shipped by
        dependencies (wayland/1.22.0 requires expat transitively).
        """
        candidates = [
            "/data/service/hnp/expat.org/expat_2.7.3/lib/libexpat.a",
        ]
        for dep in self.dependencies.values():
            if dep.ref.name == "expat":
                candidates.append(os.path.join(dep.package_folder,
                                               "lib", "libexpat.a"))
        for c in candidates:
            if os.path.isfile(c):
                self.output.info(f"plasma-wayland-protocols: static expat -> {c}")
                return c
        raise ConanException(
            "no static libexpat.a found for the static wayland-scanner link; "
            f"tried: {candidates}")

    def _find_expat_include(self):
        candidates = [
            "/data/service/hnp/expat.org/expat_2.7.3/include",
        ]
        for dep in self.dependencies.values():
            if dep.ref.name == "expat":
                candidates.append(os.path.join(dep.package_folder, "include"))
        for c in candidates:
            if os.path.isdir(c):
                return c
        return None

    def _build_static_scanner(self):
        """Build a statically-linked wayland-scanner from wayland source.

        pwp 的 autotests 只跑 scanner + C 编译,不需要
        libwayland-protocol.a(wayland-protocols 配方的那部分省略)。
        """
        scanner_src = os.path.join(self.source_folder, "wayland-scanner-src")

        # Generate config.h
        config_h = os.path.join(scanner_src, "config.h")
        with open(config_h, "w", encoding="utf-8") as f:
            f.write(f'#define HAVE_EXPAT 1\n'
                    f'#define PACKAGE "wayland"\n'
                    f'#define VERSION "{SCANNER_WAYLAND_VERSION}"\n')

        # Generate wayland-version.h from template
        version_in = os.path.join(scanner_src, "src", "wayland-version.h.in")
        version_h = os.path.join(scanner_src, "src", "wayland-version.h")
        major, minor, micro = (SCANNER_WAYLAND_VERSION.split(".") + ["0"])[:3]
        with open(version_in, "r", encoding="utf-8") as f:
            content = f.read()
        for key, val in [("@WAYLAND_VERSION@", SCANNER_WAYLAND_VERSION),
                         ("@WAYLAND_VERSION_MAJOR@", major),
                         ("@WAYLAND_VERSION_MINOR@", minor),
                         ("@WAYLAND_VERSION_MICRO@", micro)]:
            content = content.replace(key, val)
        with open(version_h, "w", encoding="utf-8") as f:
            f.write(content)

        # Generate wayland.dtd.h using embed.py
        dtd_h = os.path.join(scanner_src, "src", "wayland.dtd.h")
        self.run(
            f'python3 {scanner_src}/src/embed.py '
            f'{scanner_src}/protocol/wayland.dtd wayland_dtd > {dtd_h}',
            env="conanbuild",
        )

        # Compile static scanner (only depends on libc.so)
        scanner_bin = os.path.join(self.generators_folder, "wayland-scanner")
        cc = shutil.which("clang") or "/data/service/hnp/bin/clang"
        expat_inc = self._find_expat_include()
        expat_lib = self._find_expat_static()
        inc_flag = f"-I{expat_inc} " if expat_inc else ""
        self.run(
            f'{cc} -o {scanner_bin} '
            f'-include {config_h} '
            f'-I{scanner_src} -I{scanner_src}/src -I{scanner_src}/protocol '
            f'{scanner_src}/src/scanner.c {scanner_src}/src/wayland-util.c '
            f'{inc_flag}{expat_lib} '
            f'-lm -lpthread -static',
            env="conanbuild",
        )
        self.output.info("plasma-wayland-protocols: built static wayland-scanner")

    def build(self):
        # 静态 scanner 必须在 cmake configure 之前构建:
        # configure 阶段 FindWaylandScanner 校验 WaylandScanner_EXECUTABLE。
        self._build_static_scanner()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        # autotests: 30 协议 x (3 scan + 1 build-C) = 120 项。
        # scan 测试跑静态 scanner(--strict,任何输出即 FAIL,
        # plasma-window-management 豁免=上游已知既有问题);
        # build 测试用 ${CMAKE_C_COMPILER} 编译 build-<proto>.c + 生成的
        # protocol.c(-Wl,--unresolved-symbols=ignore-all)。
        test_env = Environment()
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure '
                '--no-tests=error --timeout 90'.format(self.build_folder)
            )

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # 上游安装自己的 PlasmaWaylandProtocolsConfig.cmake(仅定义
        # PLASMA_WAYLAND_PROTOCOLS_DIR 变量,无 find_dependency)。
        # cmake_find_mode=none 让 CMakeDeps 不遮蔽它
        # (kdecoration/libkscreen 先例);消费者把
        # share/cmake/PlasmaWaylandProtocols 加进 CMAKE_PREFIX_PATH 即可。
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [
            os.path.join("share", "cmake", "PlasmaWaylandProtocols")]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
