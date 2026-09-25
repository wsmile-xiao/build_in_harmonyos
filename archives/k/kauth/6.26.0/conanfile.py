#!/usr/bin/env python3
"""Conan recipe for kauth 6.26.0 on HarmonyOS PC."""
import os
import shutil
import subprocess
from contextlib import contextmanager

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, save


class KauthConan(ConanFile):
    name = "kauth"
    version = "6.26.0"
    description = "KDE Frameworks 6 - authorization library"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/kauth"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase-sql-dbus/6.11.1")
        self.requires("kcoreaddons/6.26.0")
        # dbus/1.14.10 (pulled in by qtbase-sql-dbus) declares expat/2.8.2, whose
        # upstream CCI recipe tool_requires("cmake/[>=3.17]") — the CCI cmake
        # recipe resolves binaries by OS key and has no OHOS entry, so the graph
        # fails with `KeyError: 'OHOS'` (and, with conancenter disabled, with
        # `cmake/[>=3.17] not resolved`). ohpcd publishes an OHOS-adapted
        # expat/2.8.2.1 with no conan-side cmake tool_require, so pin it here
        # (same approach as avahi-tools / avahi-compat-libdns_sd / awf-gtk).
        self.requires("expat/2.8.2.1", override=True)
        # kcoreaddons/6.26.0 references the plain qtbase/6.11.1, whose
        # qconfig.h sets QT_NO_DBUS (FEATURE_dbus=OFF). Mixing that QtCore with
        # the QtDBus headers from qtbase-sql-dbus defines QT_NO_DBUS while
        # qdbuserror.h's DBus branch is compiled, so Q_DBUS_EXPORT is never
        # defined and the autotests fail with
        #   "variable has incomplete type 'class Q_DBUS_EXPORT'".
        # qtbase/6.11.1.1 is the FEATURE_dbus=ON variant; override=True unifies
        # every transitive qtbase reference (same approach as baloo/6.28.0 and
        # statusnotifieritem/6.26.0; dependency binaries stay cache hits).
        self.requires("qtbase/6.11.1.1", override=True)

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        if str(self.settings.os) in ("OHOS", "HarmonyOS"):
            # Conan's HarmonyOS name has no complete CMake platform module. Use
            # CMake's OHOS platform rules so shared C++ targets receive SONAMEs.
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
            self._configure_ohos_shared_library_rules(tc)
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["BUILD_DESIGNERPLUGIN"] = "OFF"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["KAUTH_BACKEND_NAME"] = "FAKE"
        tc.variables["KAUTH_HELPER_BACKEND_NAME"] = "FAKE"
        self._define_ecm(tc)
        self._write_cmake_paths()
        tc.generate()

    def _configure_ohos_shared_library_rules(self, toolchain):
        rules = os.path.join(self.generators_folder, "ohos-shared-library-rules.cmake")
        save(
            self,
            rules,
            "\n".join(
                (
                    'set(CMAKE_SHARED_LIBRARY_SONAME_C_FLAG "-Wl,-soname,")',
                    'set(CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG "-Wl,-soname,")',
                    'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG "-Wl,-rpath,")',
                    'set(CMAKE_SHARED_LIBRARY_RUNTIME_CXX_FLAG "-Wl,-rpath,")',
                    'set(CMAKE_SHARED_LIBRARY_RUNTIME_C_FLAG_SEP ":")',
                    'set(CMAKE_SHARED_LIBRARY_RUNTIME_CXX_FLAG_SEP ":")',
                )
            )
            + "\n",
        )
        toolchain.cache_variables["CMAKE_USER_MAKE_RULES_OVERRIDE_C"] = rules
        toolchain.cache_variables["CMAKE_USER_MAKE_RULES_OVERRIDE_CXX"] = rules

    def _define_ecm(self, tc):
        ecm = self.dependencies.build.get("ecm")
        if not ecm:
            return
        ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
        tc.variables["ECM_MODULE_PATH"] = ";".join(
            os.path.join(ecm_share, rel)
            for rel in ("modules", "find-modules", "kde-modules")
        )

    def _write_cmake_paths(self):
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in list(self.dependencies.values()) + list(self.dependencies.build.values()):
            if dep and dep.package_folder:
                lines.extend(
                    [
                        f'list(PREPEND CMAKE_PREFIX_PATH "{dep.package_folder}/lib/cmake")',
                        f'list(PREPEND CMAKE_LIBRARY_PATH "{dep.package_folder}/lib")',
                        f'list(PREPEND CMAKE_INCLUDE_PATH "{dep.package_folder}/include")',
                    ]
                )
        ecm = self.dependencies.build.get("ecm")
        if ecm and ecm.package_folder:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            lines.extend(
                [
                    f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_share}/cmake")',
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_share}/modules")',
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_share}/find-modules")',
                    f'list(PREPEND CMAKE_MODULE_PATH "{ecm_share}/kde-modules")',
                ]
            )
        lines.extend(
            [
                'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
                'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            ]
        )
        with open(os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake"), "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    def _upstream_test_environment(self, session_bus_address=""):
        env = Environment()
        env.define("QT_QPA_PLATFORM", "offscreen")
        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                continue
            env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
            env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))
            env.prepend_path(
                "QT_QPA_PLATFORM_PLUGIN_PATH",
                os.path.join(dep.package_folder, "plugins", "platforms"),
            )
        if session_bus_address:
            env.define("DBUS_SESSION_BUS_ADDRESS", session_bus_address)
        return env

    @contextmanager
    def _optional_dbus_session(self):
        # dbus/1.14.10 on ohpcd packages the client library only (the daemon
        # does not link against expat in the OHOS cross build), so a session
        # bus is normally unavailable. Start a temporary one when a dbus-daemon
        # can be located; otherwise the caller excludes the session-bus tests.
        daemon = shutil.which("dbus-daemon")
        if not daemon:
            yield ""
            return
        runtime_dir = os.path.join(self.build_folder, "test-runtime")
        os.makedirs(runtime_dir, exist_ok=True)
        command = [
            daemon,
            "--session",
            "--fork",
            "--print-address=1",
            "--print-pid=1",
            f"--address=unix:path={os.path.join(runtime_dir, 'kauth-dbus-session')}",
        ]
        pid = None
        try:
            probe = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10,
                check=False,
            )
            lines = [line.strip() for line in probe.stdout.splitlines() if line.strip()]
            if probe.returncode != 0 or not lines:
                self.output.warning("dbus-daemon failed to start; excluding session-bus tests")
                yield ""
                return
            if len(lines) > 1:
                try:
                    pid = int(lines[1])
                except ValueError:
                    pid = None
            yield lines[0]
        except (OSError, subprocess.TimeoutExpired) as exc:
            self.output.warning(f"dbus-daemon failed to start: {exc}")
            yield ""
        finally:
            if pid:
                try:
                    os.kill(pid, 15)
                except OSError:
                    pass

    def _run_upstream_tests(self):
        # Upstream registers three ECM/CTest entries when Qt6::Test and
        # Qt6::DBus are present: KAuthSetupActionTest, KAuthHelperTest and
        # KAuthFdTest. KAuthPolicyGen{,TestCompare} stay unregistered because
        # the OHOS baseline uses KAUTH_BACKEND_NAME=FAKE.
        #
        # KAuthHelperTest drives DBusHelperProxy over the session bus and
        # KAuthFdTest waits for the helper service to register, so both need a
        # live D-Bus session bus. When none can be started they are excluded
        # and reported as excluded (never counted as passing), following the
        # akonadi/25.12.3 precedent for dbus/1.14.10 environments.
        session_bus_tests = ("KAuthHelperTest", "KAuthFdTest")
        with self._optional_dbus_session() as session_bus_address:
            exclude = ""
            if not session_bus_address:
                # The -E argument is a regex containing '|', so it must reach
                # ctest quoted (an unquoted '|' is a shell pipe).
                exclude = ' -E "{}"'.format("|".join(session_bus_tests))
                self.output.warning(
                    "dbus-daemon is unavailable; excluding session-bus dependent "
                    "upstream tests: " + ", ".join(session_bus_tests)
                )
            with self._upstream_test_environment(session_bus_address).vars(self).apply():
                self.run(
                    'ctest --test-dir "{}" --output-on-failure --no-tests=error -j1{}'.format(
                        self.build_folder, exclude
                    )
                )

    def package(self):
        CMake(self).install()

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF6AuthCore"]
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
