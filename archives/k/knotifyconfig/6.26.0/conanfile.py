#!/usr/bin/env python3
"""Conan recipe for knotifyconfig 6.26.0 on HarmonyOS PC.

knotifyconfig is a KDE Frameworks 6 library providing the notification
configuration widget: ``libKF6NotifyConfig.so.6`` exporting
``KNotifyConfigWidget`` (plus the private element/event-list helpers).

OHOS-specific adaptations (KF6 6.26 chain baseline, knotifications 6.26.0
precedent):
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS is
    not in KDE's platform allowlist)
  - BUILD_TESTING=OFF: upstream tests/ needs KF6ConfigWidgets, KF6WidgetsAddons
    and KF6XmlGui at 6.26; only 6.14.0/6.18.0 of those are published to ohpcd.
    Upstream N=1 (the single ``knotifytest`` executable registered through
    ``ecm_mark_as_test``) is declared but not executed; the real verification
    lives in test_package.
  - USE_DBUS=OFF: Qt6DBus is not published to ohpcd; the HAVE_DBUS block only
    guards the post-save "reload your config" broadcast
  - patch 0001: ``ki18n_install(po)`` skipped on OHOS (Qt6LinguistTools /
    gettext are not published to ohpcd); runtime i18n still resolves through
    KF6::I18n
  - patches 0002-0004: the sound field used ``KUrlRequester``, which lives in
    ``KF6::KIOWidgets``. ohpcd builds kio in KIOCORE_ONLY mode (solid /
    kbookmarks / kjobwidgets / kiconthemes 6.26 are unpublished), so the
    target links ``KF6::KIOCore`` and the widget becomes a plain ``QLineEdit``
  - patch 0005: link ``KF6::ConfigCore`` explicitly. ``<KConfig>`` /
    ``<KConfigGroup>`` are forwarding headers installed under
    ``include/KF6/KConfigCore``, and only ``KF6::ConfigCore`` puts that
    directory on the include path. Upstream inherits the usage requirement
    transitively through ``KF6::KIOWidgets``, which ohpcd does not re-export
    (kio is KIOCORE_ONLY), so the patch-0002 swap dropped the include dir
    along with the missing target and the build died on
    ``fatal error: 'KConfig' file not found``
  - ECM_MODULE_PATH set manually because the CMakeDeps-generated
    ECMConfig.cmake does not propagate the variable the project's
    CMakeLists.txt relies on
  - conan_cmakedeps_paths.cmake created manually because qtbase uses
    cmake_find_mode=none, which prevents CMakeDeps from adding its lib/cmake
    builddir to CMAKE_PREFIX_PATH
  - /system/lib64 prepended to LD_LIBRARY_PATH for the build (sandbox
    libc++_shared.so shadowing, kconfig 6.26.0 / bluez-qt 6.28.0 precedent)
  - the installed ELF files are re-signed: CMake rewrites the RUNPATH of an
    installed shared library, which invalidates the OHOS build-time
    .codesign section, and the OHOS loader then refuses to load it
    ("Permission denied"). kiconthemes 6.26.0 precedent.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class KnotifyconfigConan(ConanFile):
    name = "knotifyconfig"
    version = "6.26.0"
    description = "KDE Frameworks 6 - notification configuration widget library"
    license = "LGPL-2.0-only"
    homepage = "https://invent.kde.org/frameworks/knotifyconfig"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1")
        # The top-level CMakeLists.txt asks for Canberra first and falls back
        # to Qt6Multimedia ("Needed to preview notification sounds when
        # Canberra isn't available"). Canberra is not published to ohpcd, so
        # the Qt6Multimedia branch is the one that has to resolve.
        self.requires("qtmultimedia/6.11.1")
        self.requires("kcompletion/6.26.0")
        self.requires("kconfig/6.26.0")
        self.requires("ki18n/6.26.0")
        # KF6::KIOCore replaces the upstream KF6::KIOWidgets link (see patches).
        self.requires("kio/6.26.0")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # Qt6DBus is not published to ohpcd.
        tc.variables["USE_DBUS"] = "OFF"
        # tests/ needs KF6ConfigWidgets / KF6WidgetsAddons / KF6XmlGui 6.26,
        # none of which are published to ohpcd; see the module docstring.
        tc.variables["BUILD_TESTING"] = "OFF"

        # Native builds on the HarmonyOS device leave CMake in the Generic
        # platform module (no CMAKE_SYSTEM_NAME set because os_build ==
        # os_host == OHOS), which has no shared-library SONAME rule. Without
        # this flag CMake drops -Wl,-soname and the resulting
        # libKF6NotifyConfig.so.6 has no DT_SONAME (CI L5a gate) and the
        # exported CMake targets get IMPORTED_NO_SONAME TRUE (L5c).
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
            tc.cache_variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"

        # ECM's own installed ECMConfig.cmake sets ECM_MODULE_PATH, but the
        # CMakeDeps-generated one does not. Set it manually so the KDE cmake
        # modules (KDEInstallDirs, KDECMakeSettings, ...) are found.
        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        qtbase = self.dependencies.get("qtbase")
        if qtbase:
            qt_pkg = qtbase.package_folder
            # qtbase uses cmake_find_mode=none -> CMakeDeps does not generate
            # conan_cmakedeps_paths.cmake. Create it manually so the toolchain
            # adds qtbase's cmake dirs to CMAKE_PREFIX_PATH/CMAKE_MODULE_PATH.
            lines = [
                'set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)',
                f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")',
                f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")',
                f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")',
            ]
            if ecm:
                ecm_cmake = os.path.join(ecm.package_folder, "share", "ECM", "cmake")
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
            # Add every dependency's lib/cmake dir so find_package(KF6Config)
            # and the transitive find_dependency() chains all resolve
            # (KF6KIOConfig.cmake pulls in KF6CoreAddons and Qt6Network).
            for dep in self.dependencies.values():
                if dep and dep.package_folder:
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
            lines.append(
                'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")'
            )
            lines.append(
                'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")'
            )
            lines.append(f'set(CONAN_RUNTIME_LIB_DIRS "{qt_pkg}/lib")')
            paths_file = os.path.join(
                self.generators_folder, "conan_cmakedeps_paths.cmake"
            )
            with open(paths_file, "w") as handle:
                handle.write("\n".join(lines) + "\n")

        tc.generate()

    def build(self):
        # The OHOS-specific patches are applied only on OHOS so that other
        # platforms keep the unmodified upstream sources.
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        cmake = CMake(self)
        with self._build_env().vars(self).apply():
            cmake.configure()
            cmake.build()

    def _build_env(self):
        build_env = self._library_runtime_env()
        if self.settings.os == "OHOS":
            for llvm_lib in sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            ):
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            # ECM 6.26 KDEInstallDirs6 runs the qtbase qtpaths host tool during
            # configure (ecm_query_qt -> QT_INSTALL_PREFIX). The sandbox
            # LD_LIBRARY_PATH contains an incompatible libc++_shared.so under
            # /data/storage/el1/bundle/libs/arm64 which shadows the compatible
            # one; prepend /system/lib64 so the compatible libc++ is found
            # first (kconfig 6.26.0 / bluez-qt 6.28.0 precedent).
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return build_env

    def _library_runtime_env(self):
        runtime_env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                runtime_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                runtime_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
        for rel in ("bin", "lib", os.path.join("src", "lib")):
            runtime_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, rel)
            )
        return runtime_env

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _find_ohos_tool(self, name):
        candidates = []
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        for compiler in (compilers.get("c"), compilers.get("cpp")):
            if compiler:
                candidates.append(os.path.join(os.path.dirname(compiler), name))
        found = shutil.which(name)
        if found:
            candidates.append(found)
        candidates.append(os.path.join("/data/service/hnp/bin", name))
        return next((path for path in candidates if path and os.path.isfile(path)), "")

    @staticmethod
    def _quote(value):
        return '"' + str(value).replace('"', '\\"') + '"'

    def _sign_ohos_elf_tree(self, root_folder):
        if str(self.settings.os) not in ("OHOS", "HarmonyOS") or not os.path.isdir(root_folder):
            return
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanException("Cannot locate OHOS ELF signing tools")
        signed = 0
        for root, _, files in os.walk(root_folder):
            for name in files:
                path = os.path.join(root, name)
                if os.path.islink(path) or not self._is_elf(path):
                    continue
                self.run(
                    f"{self._quote(objcopy)} --remove-section .codesign {self._quote(path)}",
                    ignore_errors=True,
                )
                self.run(
                    f"{self._quote(signer)} sign -inFile {self._quote(path)} "
                    f"-outFile {self._quote(path)} -selfSign 1"
                )
                signed += 1
        self.output.info(f"Signed {signed} OHOS package ELF file(s)")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        self._sign_ohos_elf_tree(self.package_folder)

    def package_info(self):
        # The project installs its own KF6NotifyConfigConfig.cmake with proper
        # dependency tracking (find_dependency(Qt6Widgets)). Use
        # cmake_find_mode=none so CMakeDeps does not shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6NotifyConfig"]
