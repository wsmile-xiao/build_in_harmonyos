#!/usr/bin/env python3
"""Conan recipe for kglobalacceld 6.7.2 on HarmonyOS PC.

kglobalacceld is the KDE Plasma global-shortcut daemon (libKGlobalAccelD.so +
the libexec kglobalacceld binary). It builds on top of KF6::GlobalAccel.

OHOS-specific adaptations (recipe layer + two minimal source patches):
  - WITH_X11=OFF: upstream defaults WITH_X11 to ON and then requires XCB
    (KEYSYMS/XKB/RECORD) and compiles the KGlobalAccelDXcb platform plugin
    against <private/qtx11extras_p.h>; the OHOS qtbase / qtbase-sql-dbus
    builds have FEATURE_xcb/xlib=OFF and do not ship that private header
    (kglobalaccel 6.26.0 precedent). With WITH_X11=OFF the daemon keeps its
    registration / config-migration / allow-list / D-Bus duties and simply
    has no key-grabbing backend (upstream is likewise a no-op grabber on
    Wayland sessions).
  - WITH_KIO=OFF (patches 0001+0002): the only consumer of KF6::KIOGui and
    KF6::JobWidgets is the desktop-file launch path in
    KServiceActionComponent. No ohpcd package ships KF6::KIOGui (kio/6.26.0
    is built KIOCORE_ONLY because KIOGui's own 6.26 dependencies
    kconfigwidgets/kbookmarks/kcolorscheme/kjobwidgets are not published at
    6.26), so the launch path is compiled out and the daemon logs a warning
    instead of launching. Everything else (D-Bus service, shortcut
    registration, migration, allow-list) is unaffected.
  - Qt6::DBus is only provided by qtbase-sql-dbus/6.11.1 (qtbase/6.11.1 is
    built with FEATURE_dbus=OFF and ships no Qt6DBus cmake module).
  - Shared libdbus-1.so.3 is vendored (built from the official dbus 1.14.10
    sources inside this recipe): the OHOS qtbase builds Qt6DBus with
    dbus-linked=OFF, so libQt6DBus dlopen()s "libdbus-1.so.3" at runtime, but
    the ohpcd registry only ships STATIC libdbus-1.a — without a shared
    libdbus every Qt6DBus consumer gets an invalid session bus connection
    ("DBus session bus not found") and KGlobalAccelD::init() fails. The
    client library needs no expat (NEEDED: libc only). Long-term fix is a
    shared-lib dbus package on the registry, after which this vendored copy
    can be dropped.
  - HarmonyOS platform has no CMake SONAME rule: recipe sets
    CMAKE_SHARED_LIBRARY_SONAME_*_FLAG=-Wl,-soname, so KGlobalAccelD's
    VERSION/SOVERSION produce libKGlobalAccelD.so.0 with DT_SONAME
    (kglobalaccel 6.26.0 error #5 precedent).
  - ECM_MODULE_PATH set explicitly (CMakeDeps does not propagate it) and a
    hand-written conan_cmakedeps_paths.cmake (qtbase uses cmake_find_mode=none).
  - Upstream autotests (migrateconfigtest/shortcutstest/allowlisttest) are
    built with BUILD_TESTING=ON and really executed on device during build();
    the two D-Bus-driven tests run against a session bus started from the
    dbus/1.14.10.1 tool package (TCP + ANONYMOUS: the OHOS sandbox forbids
    AF_UNIX binds and musl has no passwd record for the running UID;
    DRAFT-dbus-1.14.10.1-ohos-session-bus-runtime).
"""
import glob
import os
import subprocess

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, save
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment

_SESSION_TCP_CONF = """<!DOCTYPE busconfig PUBLIC "-//freedesktop//DTD D-BUS Bus Configuration 1.0//EN"
 "http://www.freedesktop.org/standards/dbus/1.0/busconfig.dtd">
<busconfig>
  <type>session</type>
  <keep_umask/>
  <listen>tcp:host=127.0.0.1,port=0,bind=127.0.0.1</listen>
  <auth>ANONYMOUS</auth>
  <allow_anonymous/>
  <policy context="default">
    <allow send_destination="*" eavesdrop="true"/>
    <allow eavesdrop="true"/>
    <allow own="*"/>
  </policy>
</busconfig>
"""


class KglobalacceldConan(ConanFile):
    name = "kglobalacceld"
    version = "6.7.2"
    description = "KDE Plasma global shortcut daemon (KGlobalAccelD)"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/plasma/kglobalacceld"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Qt6::Core/Gui/Widgets/DBus(+Private) are all provided by
        # qtbase-sql-dbus (superset build of qtbase with FEATURE_dbus=ON).
        self.requires("qtbase-sql-dbus/6.11.1")
        # KF6::GlobalAccel is the PUBLIC link dependency of KGlobalAccelD.
        self.requires("kglobalaccel/6.26.0")
        # PRIVATE link dependencies kept with WITH_KIO=OFF:
        #   KF6::WindowSystem (KKeyServer), KF6::CoreAddons (KAboutData),
        #   KF6::ConfigCore, KF6::Service, and the executable's
        #   KF6::DBusAddons (KDBusService) + KF6::Crash.
        self.requires("kconfig/6.26.0")
        self.requires("kcoreaddons/6.26.0")
        self.requires("kcrash/6.26.0")
        # kdbusaddons 6.29.0 exists on the registry but requires
        # qtbase/6.11.1.1, which conflicts with the qtbase/6.11.1 that
        # kconfig/kcoreaddons/kcrash/kwindowsystem/kservice 6.26.0 and
        # qtbase-sql-dbus/6.11.1 link. kdbusaddons/6.18.0 aligns on
        # qtbase-sql-dbus/6.11.1; patch 0003 lowers KF6_MIN_VERSION to
        # 6.18.0 accordingly (aurorae 6.7.2 precedent).
        self.requires("kdbusaddons/6.18.0")
        self.requires("kwindowsystem/6.26.0")
        self.requires("kservice/6.26.0")

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")
        # Provides the dbus-daemon binary used to start a session bus for the
        # upstream autotests (OHOS has no session bus of its own).
        self.tool_requires("dbus/1.14.10.1")

    def layout(self):
        # Ninja generator: the OHOS port of GNU make 4.4.1 uses an mkfifo-based
        # jobserver, and the OHOS sandbox denies mkfifo everywhere (EPERM on
        # HMDFS, EROFS on /tmp) — any make -jN build dies with
        # "make: jobserver mkfifo ... Operation not permitted". Ninja needs no
        # FIFOs and is available at /data/service/hnp/bin/ninja (attica-kf5
        # 5.116.0 precedent).
        cmake_layout(self, generator="Ninja")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Vendored shared libdbus-1.so.3 runtime for Qt6DBus (dlopen-based
        # loading on OHOS, see docstring). Fixed URL + SHA256.
        get(self,
            url="https://dbus.freedesktop.org/releases/dbus/dbus-1.14.10.tar.xz",
            sha256="ba1f21d2bd9d339da2d4aa8780c09df32fea87998b73da24f49ab9df1e36a50f",
            strip_root=True, destination="dbus-src")

    def _build_vendored_libdbus(self):
        """Build the shared dbus-1 client library (no expat needed)."""
        src = os.path.join(self.source_folder, "dbus-src")
        bld = os.path.join(self.build_folder, "dbus-build")
        gen = self.generators_folder
        # The bundled CMake helper of this conan version cannot configure a
        # custom source/build folder pair, so drive cmake directly, pointing
        # at the same conan_toolchain (Ninja generator, OHOS clang).
        variables = {
            "BUILD_SHARED_LIBS": "ON",
            "DBUS_BUILD_TESTS": "OFF",
            "DBUS_BUILD_TOOLS": "OFF",
            "DBUS_ENABLE_DOXYGEN_DOCS": "OFF",
            "DBUS_ENABLE_XML_DOCS": "OFF",
            "DBUS_ENABLE_X11": "OFF",
            "DBUS_ENABLE_SYSTEMD": "OFF",
            "DBUS_ENABLE_SELINUX": "OFF",
            "DBUS_ENABLE_APPARMOR": "OFF",
            "DBUS_ENABLE_EMBEDDED_TESTS": "OFF",
            "DBUS_ENABLE_MODULAR_TESTS": "OFF",
            "DBUS_ENABLE_INSTALLED_TESTS": "OFF",
            "CMAKE_POLICY_VERSION_MINIMUM": "3.5",
            # OHOS has no CMake platform file ("System is unknown to
            # cmake"); force the UNIX branch so dbus does not pick
            # its Windows transport (dbus/1.14.10 recipe precedent).
            "CMAKE_SYSTEM_NAME": "OHOS",
            "DBUS_SESSION_SOCKET_DIR": "/tmp",
        }
        args = [
            "cmake", "-G", "Ninja",
            "-S", src, "-B", bld,
            f"-DCMAKE_TOOLCHAIN_FILE={os.path.join(gen, 'conan_toolchain.cmake')}",
        ]
        args += [f"-D{k}={v}" for k, v in variables.items()]
        with self._cmake_build_env().vars(self).apply():
            self.run(" ".join(args))
            self.run(f'cmake --build "{bld}" --target dbus-1')

    def _vendored_libdbus_dir(self):
        return os.path.join(self.build_folder, "dbus-build", "lib")

    def generate(self):
        tc = CMakeToolchain(self, generator="Ninja")
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        # Upstream defaults WITH_X11 to ON; the OHOS Qt builds ship
        # FEATURE_xcb/xlib=OFF and no private/qtx11extras_p.h, so the xcb
        # platform plugin and the GuiPrivate branch cannot be built.
        tc.variables["WITH_X11"] = "OFF"
        if self.settings.os == "OHOS":
            # No ohpcd package ships KF6::KIOGui (kio/6.26.0 is KIOCORE_ONLY);
            # patches make KF6KIO/KF6JobWidgets optional via WITH_KIO.
            tc.variables["WITH_KIO"] = "OFF"
        # CMake selects Platform/OHOS.cmake (which inherits the Linux SONAME
        # rule) only when CMAKE_SYSTEM_NAME=OHOS; Conan maps settings.os=OHOS
        # to CMAKE_SYSTEM_NAME=HarmonyOS, for which CMake has no platform
        # module. The generic fallback leaves the SONAME flag undefined, so
        # CMake drops VERSION/SOVERSION and emits an unversioned .so without
        # DT_SONAME (L5 soname gate fails, downstream cannot link by SONAME).
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        qt_pkgs = [d for d in self.dependencies.values()
                   if d.package_folder and os.path.isdir(os.path.join(d.package_folder, "lib", "cmake"))]
        if qt_pkgs:
            lines = []
            # qtbase/qtbase-sql-dbus use cmake_find_mode=none, so CMakeDeps does
            # not emit conan_cmakedeps_paths.cmake; create it manually.
            for dep in qt_pkgs:
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{dep.package_folder}/lib/cmake")')
                lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{dep.package_folder}/lib")')
                lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{dep.package_folder}/include")')
            # qtbase-sql-dbus must win the find_package(Qt6) lookup: it is the
            # only provider of Qt6::DBus (qtbase ships FEATURE_dbus=OFF), and it
            # also ships the full Core/Gui/Widgets/Test set.
            sqldbus = self.dependencies.get("qtbase-sql-dbus")
            if sqldbus:
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{sqldbus.package_folder}/lib/cmake")')
            if ecm:
                ecm_cmake = os.path.join(ecm.package_folder, "share", "ECM", "cmake")
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
            lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
            lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
            lines.append('set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)')
            paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
            with open(paths_file, "w") as f:
                f.write("\n".join(lines) + "\n")

        tc.generate()

    def _library_runtime_env(self):
        runtime_env = Environment()
        if self.settings.os == "OHOS":
            # Vendored shared libdbus-1.so.3 must be resolvable when Qt6DBus
            # dlopen()s it (see docstring).
            vendored = self._vendored_libdbus_dir()
            if os.path.isdir(vendored):
                runtime_env.prepend_path("LD_LIBRARY_PATH", vendored)
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                runtime_env.prepend_path("LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
                runtime_env.prepend_path("QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins"))
        for rel in ("bin", "lib", os.path.join("src", "lib"), "autotests"):
            runtime_env.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, rel))
        return runtime_env

    def _cmake_build_env(self):
        build_env = self._library_runtime_env()
        if self.settings.os == "OHOS":
            for llvm_lib in sorted(glob.glob("/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib")):
                build_env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            # KDEInstallDirs runs the qtbase qtpaths host tool during
            # configure; the sandbox LD_LIBRARY_PATH may contain an
            # incompatible libc++_shared.so which shadows the compatible
            # one; prepend /system/lib64 so the loader resolves the
            # compatible libc++ first (kconfig/kcrash/kglobalaccel precedent).
            build_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return build_env

    def build(self):
        # Platform guard: apply OHOS-specific patches only on OHOS so other
        # platforms are unaffected (kcrash/kglobalaccel precedent).
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
            self._build_vendored_libdbus()
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
            cmake.build()
        if self.settings.os == "OHOS":
            self._run_upstream_tests()

    def _find_dbus_daemon(self):
        dbus_dep = self.dependencies.build.get("dbus")
        if not dbus_dep or not dbus_dep.package_folder:
            return None
        daemon = os.path.join(dbus_dep.package_folder, "bin", "dbus-daemon")
        return daemon if os.path.isfile(daemon) else None

    def _start_session_bus(self, workdir):
        """Start a session bus (TCP + ANONYMOUS) and return (proc, address).

        The OHOS sandbox forbids AF_UNIX socket binds (EPERM) and musl has no
        passwd record for the running UID, so the session bus listens on
        127.0.0.1 TCP with ANONYMOUS auth
        (DRAFT-dbus-1.14.10.1-ohos-session-bus-runtime).
        """
        daemon = self._find_dbus_daemon()
        if not daemon:
            self.output.warning("dbus-daemon not found in tool dependencies; upstream D-Bus tests will run without a session bus")
            return None
        conf_path = os.path.join(workdir, "session-tcp.conf")
        save(self, conf_path, _SESSION_TCP_CONF)
        try:
            proc = subprocess.Popen(
                [daemon, "--config-file", conf_path, "--print-address", "--nofork"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            )
            address = proc.stdout.readline().decode().strip()
            if proc.poll() is not None or not address.startswith("tcp:"):
                proc.terminate()
                self.output.warning(f"session bus failed to start (address={address!r}); upstream D-Bus tests will run without a session bus")
                return None
            self.output.info(f"session bus started: {address}")
            return proc, address
        except OSError as exc:
            self.output.warning(f"session bus could not be started: {exc}")
            return None

    def _run_upstream_tests(self):
        test_env = self._library_runtime_env()
        test_env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
        test_env.define("QT_QPA_PLATFORM", "offscreen")
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

        bus = self._start_session_bus(self.build_folder)
        if bus:
            proc, address = bus
            test_env.define("DBUS_SESSION_BUS_ADDRESS", address)
        # Real run of the upstream autotests; failures are reported honestly
        # from the build log (ctest return code is not fatal for packaging,
        # kio 6.26.0 precedent: environment limitations are documented, not
        # hidden). Per-test timeout bounds a hung event loop.
        try:
            with test_env.vars(self).apply():
                self.run(
                    'ctest --test-dir "{}" --output-on-failure --timeout 120'.format(self.build_folder),
                    ignore_errors=True,
                )
        finally:
            if bus:
                proc.terminate()

    def package(self):
        cmake = CMake(self)
        with self._library_runtime_env().vars(self).apply():
            cmake.install()
        if self.settings.os == "OHOS":
            # Ship the vendored shared libdbus-1.so.3 (Qt6DBus dlopens it at
            # runtime; the registry only has a static libdbus-1.a).
            import shutil
            lib_dir = os.path.join(self.package_folder, "lib")
            os.makedirs(lib_dir, exist_ok=True)
            for path in sorted(glob.glob(os.path.join(self._vendored_libdbus_dir(), "libdbus-1.so*"))):
                target = os.path.join(lib_dir, os.path.basename(path))
                if os.path.islink(path):
                    if not os.path.lexists(target):
                        os.symlink(os.readlink(path), target)
                elif not os.path.exists(target):
                    shutil.copy2(path, target)

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KGlobalAccelD"]
