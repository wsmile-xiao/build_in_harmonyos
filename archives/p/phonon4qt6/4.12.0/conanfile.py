#!/usr/bin/env python3
"""Conan recipe for phonon4qt6 4.12.0 on HarmonyOS PC.

phonon4qt6 is KDE Multimedia's Qt6 media framework library (libphonon4qt6.so).

OHOS-specific adaptations:
  - OpenGLWidgets ALIAS patch: Qt6::OpenGLWidgets target does not exist in
    the qtbase OHOS build (OpenGL disabled). The upstream CMakeLists.txt
    unconditionally creates an ALIAS to this target, which fails. Patch
    wraps the ALIAS creation in a TARGET existence check.
  - PHONON_BUILD_QT5=OFF: only build Qt6 variant.
  - PHONON_BUILD_DESIGNER_PLUGIN=OFF: Qt6Designer cmake module not exported
    by qttools OHOS package.
  - PHONON_BUILD_SETTINGS=OFF: avoids building phononsettings executable;
    product is pure library (libphonon4qt6.so).
  - PHONON_BUILD_EXPERIMENTAL=OFF: disable experimental sub-library.
  - QT_ADDITIONAL_PACKAGES_PREFIX_PATH set to qttools path so Qt6 component
    lookup finds LinguistTools (needed by ECMPoQmTools for translation).

L5 SONAME gate fixes (主审 R52):
  - CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG="-Wl,-soname," injected because
    OHOS 适配版 conan maps os=OHOS → CMAKE_SYSTEM_NAME=HarmonyOS, and
    CMake 4.1 lacks Platform/HarmonyOS.cmake so Linux platform module
    (which defines the SONAME flag) is never loaded (E092 根因).
  - qt5compat's libQt6Core5Compat.so has no DT_SONAME (same root cause);
    E537 link-time-SONAME-basename fix: cmake_language(DEFER) re-sets
    IMPORTED_SONAME="libQt6Core5Compat.so" and clears IMPORTED_NO_SONAME
    on Qt6::Core5Compat so ld records SONAME basename not absolute path.
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Phonon4Qt6Conan(ConanFile):
    name = "phonon4qt6"
    version = "4.12.0"
    description = "KDE Multimedia Qt6 media framework library (libphonon4qt6.so)"
    license = "LGPL-2.1-or-later"
    homepage = "https://invent.kde.org/phonon/phonon"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        self.requires("qt5compat/6.11.1")
        self.requires("qttools/6.11.1")

    def build_requirements(self):
        self.tool_requires("ecm/6.20.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["PHONON_BUILD_QT5"] = "OFF"
        tc.variables["PHONON_BUILD_QT6"] = "ON"
        tc.variables["PHONON_BUILD_DESIGNER_PLUGIN"] = "OFF"
        tc.variables["PHONON_BUILD_DEMOS"] = "OFF"
        tc.variables["PHONON_BUILD_DOC"] = "OFF"
        tc.variables["PHONON_BUILD_SETTINGS"] = "OFF"
        tc.variables["PHONON_BUILD_EXPERIMENTAL"] = "OFF"

        # ── L5 SONAME 修复 ──────────────────────────────────────────────
        # 根因：OHOS 适配版 conan 将 settings.os=OHOS 映射为
        # CMAKE_SYSTEM_NAME=HarmonyOS，而 CMake 4.1 只有 Platform/OHOS.cmake
        # （无 Platform/HarmonyOS.cmake），Linux 平台模块未加载 →
        # CMAKE_SHARED_LIBRARY_SONAME_<LANG>_FLAG 未定义 → 链接时无
        # -Wl,-soname → libphonon4qt6.so 无 DT_SONAME（L5a/L5c 失败）。
        # 修复：显式注入 SONAME flag，等价于 Platform/Linux.cmake 的定义。
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_PLATFORM_USES_PATH_WHEN_NO_SONAME"] = "1"
        # phonon 的 CMakeLists 用 ecm_setup_version 设置 SOVERSION 4，链接器
        # 将生成 libphonon4qt6.so.4 → soname 为相对路径 libphonon4qt6.so.4。

        # ── E537 修复：qt5compat 无 DT_SONAME → 绝对路径 DT_NEEDED ─────
        # qt5compat 的 libQt6Core5Compat.so 无 SONAME，CMake 链接时记录
        # IMPORTED_LOCATION 绝对路径（conan 缓存路径），发布后消费方机器
        # 无该路径导致不可用。按 E537 方案在注入文件中为 Qt6::Core5Compat
        # target 设置 IMPORTED_SONAME 并清除 IMPORTED_NO_SONAME，
        # 使链接器按 -l:libQt6Core5Compat.so（SONAME basename）记录。

        # ECM module paths — CMakeDeps-generated ECMConfig.cmake does not
        # propagate ECM_MODULE_PATH needed by KDE cmake modules.
        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        # qtbase uses cmake_find_mode=none → CMakeDeps does not generate
        # conan_cmakedeps_paths.cmake. Create it manually so the toolchain
        # adds qtbase's cmake dirs to CMAKE_PREFIX_PATH/CMAKE_MODULE_PATH.
        # qttools and qt5compat also use cmake_find_mode=none or need paths.
        qtbase = self.dependencies.get("qtbase")
        if qtbase:
            qt_pkg = qtbase.package_folder
        else:
            qt_pkg = None

        qttools = self.dependencies.get("qttools")
        if qttools:
            qttools_pkg = qttools.package_folder
        else:
            qttools_pkg = None

        qt5compat = self.dependencies.get("qt5compat")
        if qt5compat:
            qt5compat_pkg = qt5compat.package_folder
        else:
            qt5compat_pkg = None

        lines = []
        if qt_pkg:
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
        if qttools_pkg:
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qttools_pkg}/lib/cmake")')
            # QT_ADDITIONAL_PACKAGES_PREFIX_PATH: Qt6Config component
            # lookup only searches _qt_cmake_dir (qtbase), so extra Qt modules
            # must be listed here for find_package(Qt6 COMPONENTS LinguistTools).
            lines.append(
                f'set(QT_ADDITIONAL_PACKAGES_PREFIX_PATH '
                f'"{qttools_pkg}/lib/cmake")'
            )
        if qt5compat_pkg:
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt5compat_pkg}/lib/cmake")')
        if ecm:
            ecm_pkg = ecm.package_folder
            ecm_cmake = os.path.join(ecm_pkg, "share", "ECM", "cmake")
            lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')

        lines.append(
            f'list(PREPEND CMAKE_MODULE_PATH '
            f'"${{CMAKE_CURRENT_LIST_DIR}}")'
        )
        lines.append(
            f'list(PREPEND CMAKE_PREFIX_PATH '
            f'"${{CMAKE_CURRENT_LIST_DIR}}")'
        )
        lines.append('set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)')
        if qt_pkg:
            lines.append(f'set(CONAN_RUNTIME_LIB_DIRS "{qt_pkg}/lib")')

        # ── E537: 给无 SONAME 的依赖 target 注入 IMPORTED_SONAME ────────
        # qt5compat 的 libQt6Core5Compat.so 无 DT_SONAME（平台级问题），
        # CMakeDeps/官方 config 生成的 Qt6::Core5Compat imported target 带
        # IMPORTED_LOCATION（conan 缓存绝对路径）且 IMPORTED_NO_SONAME=TRUE。
        # 若直接链接，DT_NEEDED 会记录绝对路径，发布后消费方不可用。
        # 修复：cmake_language(DEFER) 在 find_package 完成后重设
        # IMPORTED_SONAME=basename、清 IMPORTED_NO_SONAME，链接器将按
        # -l:libQt6Core5Compat.so 记录 DT_NEEDED（可重定位）。
        if qt5compat_pkg:
            lines.append(
                "function(_phonon_fix_qt5compat_soname_impl)"
            )
            lines.append("    if(TARGET Qt6::Core5Compat)")
            lines.append("        get_target_property(_imp_loc Qt6::Core5Compat IMPORTED_LOCATION)")
            lines.append("        if(_imp_loc)")
            lines.append(
                '            set_target_properties(Qt6::Core5Compat PROPERTIES'
            )
            lines.append(
                '                IMPORTED_SONAME "libQt6Core5Compat.so"'
            )
            lines.append("                IMPORTED_NO_SONAME FALSE")
            lines.append("            )")
            lines.append("        endif()")
            lines.append("    endif()")
            lines.append("endfunction()")
            lines.append(
                "cmake_language(DEFER CALL _phonon_fix_qt5compat_soname_impl)"
            )

        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

        tc.generate()

    def build(self):
        # Apply OHOS-specific patches (OpenGLWidgets ALIAS guard, etc.)
        apply_conandata_patches(self)
        # Host tools (lconvert from qttools, qtpaths from qtbase) run during
        # build and must resolve Qt6 shared libs at runtime. Inject every
        # dependency's lib dir into LD_LIBRARY_PATH (karchive precedent).
        runtime_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                runtime_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
        if str(self.settings.os) == "OHOS":
            # The sandbox LD_LIBRARY_PATH may contain an incompatible
            # libc++_shared.so; prepend /system/lib64 so host tools resolve
            # the compatible one first (karchive 6.26.0 precedent).
            runtime_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        cmake = CMake(self)
        with runtime_env.vars(self).apply():
            cmake.configure()
            cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # Phonon installs its own Phonon4Qt6Config.cmake with proper
        # dependency tracking (find_dependency on Qt6Core, Qt6Widgets).
        # Use cmake_find_mode=none so CMakeDeps doesn't shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["phonon4qt6"]
