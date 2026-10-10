#!/usr/bin/env python3
"""Conan recipe for kwayland 6.7.2 on HarmonyOS PC.

kwayland is the KDE Plasma Wayland client library (KWaylandClient) plus
the kwaylandScanner protocol-code generator tool. Note: since Plasma 6
the server-side classes moved out of kwayland (into kwin), so this
package is client-only.

Upstream hard requirements: Qt6 >= 6.10.0 (Gui + Private, Concurrent,
WaylandClient + Private), ECM >= 6.26.0, Wayland 1.24 (Client),
WaylandProtocols 1.15, PlasmaWaylandProtocols 1.21.0, EGL, WaylandScanner.

OHOS-specific adaptations (mirroring libkscreen 6.7.2 / layer-shell-qt
6.7.2, the merged Plasma 6.7.2 precedents):
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection.
  - patches/0001 lowers the Wayland minimum from 1.24 to 1.22: qtbase/
    6.11.1.2 and qtwayland/6.11.1 pin wayland/1.22.0 and mixing 1.24.0
    is a graph conflict; kwayland only uses the stable Wayland client
    API that 1.22 already provides (libkscreen precedent).
  - patches/0002 compiles out the wl_fixes support: wl_fixes is a
    Wayland >= 1.24 interface that src/client/registry.cpp uses
    unconditionally, and the QtWaylandClient private header included by
    src/client/surface_p.cpp refers to struct ::wl_fixes unguarded.
    registry.cpp guards every use with the WL_FIXES_INTERFACE macro
    that the generated wayland-client-protocol.h defines from 1.24 on
    (the 1.22 headers do not define it, so the code compiles out; a
    1.22 compositor cannot announce wl_fixes anyway), and surface_p.cpp
    forward-declares the incomplete type before including the Qt header
    (only a pointer type is needed and kwayland never calls into the
    interface). Both adaptations are no-ops with Wayland >= 1.24.
  - patches/0003 builds a single unversioned shared object. The
    HarmonyOS cmake toolchain has no platform module, so with a soname
    flag defined CMake generates the versioned chain
    libKWaylandClient.so -> .so.6 -> .so.6.7.2 and calls
    cmake_symlink_library to create it; symlink creation is not
    permitted in the OHOS build environment and the build dies with
    "Permission denied" (round 6). VERSION/SOVERSION are dropped from
    the target, matching every published OHOS ecosystem library, which
    is a single unversioned file (libKF6Screen.so, libKScreenLocker.so,
    libkdecorations3private.so; kdecoration/kscreenlocker precedents).
    DT_SONAME is unaffected: the soname flags below still make the
    linker record libKWaylandClient.so as the soname (device-probe
    verified on the unversioned library), so consumers keep a bare,
    relocatable DT_NEEDED entry.
  - wayland-protocols/1.36.1 and plasma-wayland-protocols/1.21.0 are
    tool_requires (build-context): they are pure XML data consumed at
    build time only, and keeping them out of the host graph avoids the
    version conflict with qtbase's host requires wayland-protocols/1.36
    (qtwayland uses the same tool_requires pattern for
    wayland-protocols). 1.36.1 is deliberately the SAME ref qtwayland
    6.11.1 already tool_requires, so the build context keeps exactly one
    wayland-protocols node. That node pins wayland/1.22.0, matching
    plasma-wayland-protocols/1.21.0 and the host graph; the kwin-chain
    wayland-protocols/1.48 pins wayland/1.24.0 (its bundled static
    scanner is built from wayland 1.24 sources), and two
    wayland-protocols versions in one build context is an unsolvable
    wayland version conflict — conan's override API cannot cross the
    build/non-build requirement boundary (Requirement.__hash__ is
    (ref.name, build), so a tool_requires override can never match a
    build-context node's plain requires). Upstream only asks for
    WaylandProtocols 1.15; 1.36.1 ships every XML kwayland consumes
    (stable/xdg-shell, unstable/xdg-shell-unstable-v6, relative-pointer,
    pointer-gestures, pointer-constraints, xdg-foreign, idle-inhibit,
    xdg-output, xdg-decoration).
  - WaylandScanner_EXECUTABLE pinned from the qtbase libexec dir with
    the wayland package bin dir as fallback (libkscreen precedent;
    khronos wayland-scanner is not shipped on OHOS as a standalone tool).
  - WaylandProtocols: the installed wayland-protocols.pc hardcodes a
    stale cache path; regenerate it with the real package prefix and
    put it first on PKG_CONFIG_PATH, plus set WaylandProtocols_DATADIR
    (layer-shell-qt precedent).
  - PlasmaWaylandProtocols: consumed via the upstream
    PlasmaWaylandProtocolsConfig.cmake (cmake_find_mode=none package);
    its share/cmake dir is added to CMAKE_PREFIX_PATH and
    PLASMA_WAYLAND_PROTOCOLS_DIR is set explicitly (belt and suspenders).
  - find_package(EGL) is satisfied from the OHOS SDK sysroot
    (sysroot/usr/include/EGL/egl.h + sysroot/usr/lib/aarch64-linux-ohos/
    libEGL.so) via EGL_INCLUDE_DIR/EGL_LIBRARY cache variables.
    Upstream only probes EGL (nothing in the tree links EGL_LIBRARIES or
    EGL::EGL) but ecm_feature_summary(FATAL_ON_MISSING_REQUIRED_PACKAGES)
    makes the probe fatal; at runtime EGL resolves from the OHOS system
    (/system/lib64/libEGL.so). No mesa dependency: mesa/24.3.4.1.1 pins
    expat/2.8.2.1.1, which is a graph version conflict with
    qtbase->dbus/wayland's expat/2.8.2.
  - ECM_MODULE_PATH set manually because the CMakeDeps-generated
    ECMConfig.cmake does not propagate the variable.
  - conan_cmakedeps_paths.cmake created manually because qtbase uses
    cmake_find_mode=none, which prevents CMakeDeps from adding its
    lib/cmake builddir to CMAKE_PREFIX_PATH.
  - CMAKE_SHARED_LIBRARY_SONAME flags set manually: OHOS has no
    Platform/HarmonyOS cmake module, so the generic rules leave the
    flag undefined and shared libraries would be built without a
    DT_SONAME entry, which makes the linker record a path-relative
    DT_NEEDED in consumers that the musl loader cannot resolve after
    installation (kdecoration precedent; layer-shell-qt uses the same
    flag). 0003 keeps the KWaylandClient target unversioned, so the
    flag yields SONAME libKWaylandClient.so without any versioned
    symlink chain.
  - BUILD_TESTING=ON builds the 12 upstream test executables
    (11 client tests + kwaylandScanner). Upstream kwayland 6.7.2 does
    NOT register ctest tests (tests/CMakeLists.txt only builds the
    client binaries; the org-kde-kf5-kwayland-testserver they run
    against moved out of this repo with the KF6 server-side split), so
    no ctest run; runtime verification is carried by the test_package
    E2E roundtrip (mini compositor + KWaylandClient over a socketpair).
"""
import glob
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class KwaylandConan(ConanFile):
    name = "kwayland"
    version = "6.7.2"
    description = "KDE Plasma Wayland client library (KWaylandClient)"
    license = "LGPL-2.1-or-later"
    homepage = "https://invent.kde.org/plasma/kwayland"
    url = "https://invent.kde.org/plasma/kwayland"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt6Gui(+Private)/Concurrent/Widgets 来自 qtbase 6.11.1.2
        # (libkscreen/layer-shell-qt 同款钉版)
        self.requires("qtbase/6.11.1.2")
        # Qt6WaylandClient(+Private) 来自 qtwayland 6.11.1
        self.requires("qtwayland/6.11.1")
        # Wayland::Client(1.22.0 钉版,0001 patch 把上游 min 1.24 降到 1.22)
        self.requires("wayland/1.22.0")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")
        # 纯构建期 XML 数据包,放 build context 避免与 qtbase 的 host
        # wayland-protocols/1.36 钉版冲突(qtwayland tool_requires 同款先例)。
        # 版本刻意取 1.36.1 = qtwayland 6.11.1 在 build context 里已带的
        # 同一个 ref:同 ref 去重后 build context 只剩一个 wayland-protocols
        # 节点,其 wayland 钉版 1.22.0 与 pwp/1.21.0、host 侧完全一致。
        # (kwin 链上的 wayland-protocols/1.48 自钉 wayland/1.24.0,一旦与
        # 1.36.1 同居一个 build context 即 wayland 版本冲突;该冲突无法用
        # override 化解——Requirement.__hash__=(ref.name, build),
        # tool_requires 声明的 override 永远匹配不上 build context 节点的
        # 普通 requires。上游只要 WaylandProtocols 1.15,1.36.1 的 XML 全集
        # 覆盖 kwayland 消费的全部协议。)
        self.tool_requires("wayland-protocols/1.36.1")
        self.tool_requires("plasma-wayland-protocols/1.21.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_QCH"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["CMAKE_CXX_STANDARD"] = "20"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        # OHOS 无 Platform/HarmonyOS cmake 模块 -> 共享库没有 DT_SONAME
        # (kdecoration/layer-shell-qt 先例)。0003 去掉目标的 VERSION/SOVERSION
        # 之后,这两个标志就是"无版本实体文件 + SONAME=libKWaylandClient.so"
        # 的组合:真机探针实测 19:40 产物 readelf 有 SONAME,且零符号链接。
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"

        # ECM_MODULE_PATH (libkscreen precedent)
        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        # WaylandScanner_EXECUTABLE: prefer qtbase libexec, fallback to the
        # wayland package bin dir (libkscreen precedent). The scanner runs
        # during build (ecm_add_wayland_client_protocol), qtbase's copy is
        # the one verified to execute on OHOS.
        qtbase = self.dependencies.get("qtbase")
        wayland = self.dependencies.get("wayland")
        scanner_candidates = []
        if qtbase and qtbase.package_folder:
            scanner_candidates.append(
                os.path.join(qtbase.package_folder, "libexec", "wayland-scanner"))
        if wayland and wayland.package_folder:
            scanner_candidates.append(
                os.path.join(wayland.package_folder, "bin", "wayland-scanner"))
        for cand in scanner_candidates:
            if os.path.isfile(cand):
                tc.variables["WaylandScanner_EXECUTABLE"] = cand
                break

        # find_package(EGL): 上游只 find 不链接(全树无 EGL_LIBRARIES/EGL::
        # 引用),但 ecm_feature_summary(FATAL_ON_MISSING_REQUIRED_PACKAGES)
        # 让 find 失败即 configure 失败。EGL 属 OHOS 系统图形栈:头/桩库取
        # SDK sysroot,运行期按 /system/lib64/libEGL.so 解析。不引制品仓
        # mesa——mesa/24.3.4.1.1 钉 expat/2.8.2.1.1,与
        # qtbase->dbus/wayland 的 expat/2.8.2 图版本冲突。
        for sdk_sysroot in sorted(glob.glob(
                "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/sysroot")):
            egl_inc = os.path.join(sdk_sysroot, "usr", "include")
            egl_lib = os.path.join(sdk_sysroot, "usr", "lib",
                                   "aarch64-linux-ohos", "libEGL.so")
            if (os.path.isfile(os.path.join(egl_inc, "EGL", "egl.h"))
                    and os.path.isfile(egl_lib)):
                tc.cache_variables["EGL_INCLUDE_DIR"] = egl_inc
                tc.cache_variables["EGL_LIBRARY"] = egl_lib
                break

        # WaylandProtocols (tool_require -> 无 CMakeDeps config,ECM
        # FindWaylandProtocols 走 pkg-config): 重生成 .pc 指向真实包前缀,
        # 置顶 PKG_CONFIG_PATH,并显式给 WaylandProtocols_DATADIR
        # (layer-shell-qt 先例;src/client/CMakeLists.txt 用
        # ${WaylandProtocols_DATADIR} 引用 xdg-shell 等协议 XML)
        wp = self.dependencies.build.get("wayland-protocols")
        if wp and wp.package_folder:
            wp_pkgconf = os.path.join(self.build_folder, "pkgconfig-fixed")
            os.makedirs(wp_pkgconf, exist_ok=True)
            wp_pc = os.path.join(wp_pkgconf, "wayland-protocols.pc")
            if not os.path.exists(wp_pc):
                with open(wp_pc, "w") as fh:
                    fh.write(
                        f"prefix={wp.package_folder}\n"
                        "datarootdir=${prefix}/share\n"
                        "pkgdatadir=${datarootdir}/wayland-protocols\n"
                        "\n"
                        "Name: Wayland Protocols\n"
                        "Description: Wayland protocol files\n"
                        f"Version: {wp.ref.version}\n"
                    )
            wp_env = Environment()
            wp_env.prepend_path("PKG_CONFIG_PATH", wp_pkgconf)
            wp_env.vars(self, scope="build").save_script(
                "conanbuild_wp_pkgconfig"
            )
            tc.cache_variables["WaylandProtocols_DATADIR"] = os.path.join(
                wp.package_folder, "share", "wayland-protocols"
            )

        # PlasmaWaylandProtocols (tool_require -> 上游 Config 包手工消费)
        pwp = self.dependencies.build.get("plasma-wayland-protocols")
        if pwp and pwp.package_folder:
            tc.cache_variables["PLASMA_WAYLAND_PROTOCOLS_DIR"] = os.path.join(
                pwp.package_folder, "share", "plasma-wayland-protocols"
            )

        # 注:kwayland 全树无 ki18n/po/,find_package 只取 Gui/Concurrent/
        # WaylandClient(±Private),不需要 Qt6LinguistTools(libkscreen/
        # kscreenlocker 需要它是为了 ECMPoQmTools 的 po->qm 步骤)。
        # self.dependencies.get() 对缺失依赖是抛 KeyError 的硬查找,故这里
        # 直接不查。

        # conan_cmakedeps_paths.cmake (libkscreen 全套先例)
        lines = []
        if qtbase and qtbase.package_folder:
            qt_pkg = qtbase.package_folder
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
        if ecm:
            ecm_pkg = ecm.package_folder
            ecm_cmake = os.path.join(ecm_pkg, "share", "ECM", "cmake")
            lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                continue
            try:
                dep_ref = str(dep.ref)
            except Exception:
                dep_ref = ""
            # 旧 qtbase/6.11.1 不带 Qt6GuiPrivate/Qt6WaylandClientPrivate,
            # 绝不能赢得 Qt6_DIR 查找(libkscreen 先例)
            if dep_ref == "qtbase/6.11.1":
                continue
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"{dep.package_folder}/lib/cmake")'
            )
            lines.append(
                f'list(PREPEND CMAKE_LIBRARY_PATH '
                f'"{dep.package_folder}/lib")'
            )
            lines.append(
                f'list(PREPEND CMAKE_INCLUDE_PATH '
                f'"{dep.package_folder}/include")'
            )
        # tool_requires 不在 self.dependencies(host)里,单独补路径:
        # pwp 的 Config 包目录
        if pwp and pwp.package_folder:
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH '
                f'"{pwp.package_folder}/share/cmake/PlasmaWaylandProtocols")'
            )
        lines.append(
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        lines.append(
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")'
        )
        lines.append('set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)')
        if qtbase:
            lines.append(f'set(CONAN_RUNTIME_LIB_DIRS "{qt_pkg}/lib")')
        if qtbase:
            # Re-assert qtbase LAST so it wins the Qt6_DIR lookup
            # (list(PREPEND) 最后一条在最前)
            lines.append(f'set(Qt6_DIR "{qt_pkg}/lib/cmake/Qt6")')
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")'
            )
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

        tc.generate()

    def build(self):
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # 上游安装自己的 KWaylandConfig.cmake(find_dependency Qt6Gui)。
        # cmake_find_mode=none 让 CMakeDeps 不遮蔽它
        # (kdecoration/libkscreen 先例)。
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KWaylandClient"]
