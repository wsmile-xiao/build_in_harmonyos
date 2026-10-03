#!/usr/bin/env python3
"""Conan recipe for kunifiedpush 26.04.0 on HarmonyOS PC.

kunifiedpush is the KDE UnifiedPush integration framework (KDE Gear). The
upstream build has four deliverables on a full Linux desktop:

  - libKUnifiedPush.so          client library
  - libKUnifiedPushDistributor.so  distributor library
  - libKUnifiedPushNotifier.so  ntfy notifier library
  - kcm_kunifiedpush.so + kunifiedpush-management tool (KCM module)

OHOS-specific adaptations:

  - KUNIFIEDPUSH_CLIENT_ONLY=ON builds only the application client library
    (libKUnifiedPush.so). The distributor/notifier/KCM deliverables need
    Qt6::WebSockets plus the KF6 stack (I18n, Solid, Service, KCMUtils,
    Crash); the ohpcd registry currently lacks solid and qtwebsockets for
    this dependency set, so the client library is the deliverable shipped
    (the same upstream-supported scope as the Android build, which also
    builds client-only via its own connector implementation).
  - Qt6::DBus and the generated DBus adaptor/interface sources are used by
    the client library; the qtbase-sql-dbus/6.11.1 variant provides
    Qt6::DBus together with the qdbusxml2cpp host tool and the Qt6DBusMacros
    module (akonadi 25.12.3 / alligator 26.04.0 precedent).
  - KF_IGNORE_PLATFORM_CHECK=TRUE bypasses the ECM/KDE platform allowlist
    (OHOS is not in the KDE platform list; kcrash 6.26.0 precedent).
  - BUILD_TESTING=ON and ctest execution run the upstream autotests that are
    available in the client-only feature set: connectorutilstest and
    contentencryptiontest (the connectortest/serversenteventsstreamtest/
    contentencryptortest/vapidtest autotests plus the tests/ demo binaries
    need the distributor/notifier libraries and stay out of scope).
  - ECM_MODULE_PATH set manually because the CMakeDeps-generated
    ECMConfig.cmake does not propagate the variable the project relies on
    (kcrash 6.26.0 precedent).
  - conan_cmakedeps_paths.cmake created manually because qtbase-sql-dbus
    uses cmake_find_mode=none, which prevents CMakeDeps from adding its
    lib/cmake builddir to CMAKE_PREFIX_PATH (kcrash 6.26.0 precedent).
  - OpenSSL::Crypto links against openssl/3.5.6.1 for the RFC 8291 push
    content encryption (akonadi 25.12.3 pinning precedent).
  - The sandbox LD_LIBRARY_PATH contains an incompatible libc++_shared.so
    which shadows the compatible one; /system/lib64 is prepended during
    configure and ctest (kconfig 6.26.0 / bluez-qt 6.28.0 / kcrash 6.26.0
    precedent).
"""
import glob
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import get


class KUnifiedPushConan(ConanFile):
    name = "kunifiedpush"
    version = "26.04.0"
    description = "KDE UnifiedPush integration (client connector library)"
    license = ("BSD-2-Clause", "LGPL-2.0-or-later")
    homepage = "https://invent.kde.org/libraries/kunifiedpush"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def requirements(self):
        self.requires("qtbase-sql-dbus/6.11.1")
        self.requires("openssl/3.5.6.1")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        # Client library only: skips the distributor/notifier/KCM deliverables
        # and their Qt6::WebSockets + KF6 (Solid/Service/KCMUtils/Crash)
        # requirements, none of which are available in the ohpcd registry for
        # this dependency set (W0 dependency verification, task #12932).
        tc.variables["KUNIFIEDPUSH_CLIENT_ONLY"] = "ON"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"

        # The CMakeDeps-generated ECMConfig.cmake does not set ECM_MODULE_PATH;
        # point the project at the installed ECM modules explicitly.
        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        # qtbase-sql-dbus uses cmake_find_mode=none -> CMakeDeps does not
        # generate conan_cmakedeps_paths.cmake entries for it. Create the
        # file manually so the toolchain adds every dependency's cmake dirs
        # to CMAKE_PREFIX_PATH/CMAKE_MODULE_PATH.
        lines = []
        for dep in list(self.dependencies.values()) + list(self.dependencies.build.values()):
            if dep and dep.package_folder:
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH '
                    f'"{dep.package_folder}/lib/cmake")'
                )
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH "{dep.package_folder}")'
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
                    f'list(PREPEND CMAKE_MODULE_PATH '
                    f'"{dep.package_folder}/lib/cmake")'
                )
        if ecm:
            ecm_cmake = os.path.join(ecm.package_folder, "share", "ECM", "cmake")
            lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
        lines.append(
            f'list(PREPEND CMAKE_MODULE_PATH "${{CMAKE_CURRENT_LIST_DIR}}")'
        )
        lines.append(
            f'list(PREPEND CMAKE_PREFIX_PATH "${{CMAKE_CURRENT_LIST_DIR}}")'
        )
        lines.append('set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)')
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

        tc.generate()

    def build(self):
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
            cmake.build()
        self._run_upstream_tests()

    def _cmake_build_env(self):
        build_env = self._library_runtime_env()
        if self.settings.os == "OHOS":
            for llvm_lib in sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            ):
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            # The sandbox LD_LIBRARY_PATH contains an incompatible
            # libc++_shared.so which shadows the compatible one; prepend
            # /system/lib64 so qtpaths/moc-style Qt host tools and the
            # linking steps resolve the compatible libc++ first (kcrash
            # 6.26.0 precedent).
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
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "bin")
                )
                runtime_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
        for rel in ("bin", "lib"):
            runtime_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, rel)
            )
        return runtime_env

    def _run_upstream_tests(self):
        test_env = self._library_runtime_env()
        if self.settings.os == "OHOS":
            test_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
            for llvm_lib in sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            ):
                test_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        # Deterministic writable XDG locations for the QSettings state file
        # read by ConnectorPrivate::loadState (connectorutilstest instantiates
        # a real Connector over the session bus).
        test_home = os.path.join(self.build_folder, "test-home")
        xdg_runtime = os.path.join(self.build_folder, "xdg-runtime")
        os.makedirs(test_home, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        test_env.define("HOME", test_home)
        test_env.define("XDG_RUNTIME_DIR", xdg_runtime)
        test_env.define("XDG_CACHE_HOME", os.path.join(test_home, ".cache"))
        test_env.define("XDG_CONFIG_HOME", os.path.join(test_home, ".config"))
        test_env.define("XDG_DATA_HOME", os.path.join(test_home, ".local", "share"))
        with test_env.vars(self).apply():
            self.run(
                'ctest --test-dir "{}" --output-on-failure --no-tests=error'.format(
                    self.build_folder
                )
            )

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # The project installs its own KUnifiedPushConfig.cmake with proper
        # dependency tracking (find_dependency on Qt6Core). Use
        # cmake_find_mode=none so CMakeDeps doesn't shadow it.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KUnifiedPush"]
