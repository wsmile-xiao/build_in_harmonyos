#!/usr/bin/env python3
"""Conan recipe for ksystemstats 6.7.2 on HarmonyOS PC.

KSystemStats is the KDE Plasma system statistics daemon:

  - ``bin/ksystemstats`` — the ``org.kde.ksystemstats`` D-Bus service built on
    the KSysGuard::SystemStats sensor framework.
  - ``lib/plugins/ksystemstats/*.so`` — the sensor plugins (cpu, disk, gpu,
    memory, network, osinfo, power, pressure), dlopen'ed by the daemon through
    KPluginMetaData. The lmsensors plugin is only built when sensors support is
    enabled; see the lm-sensors entry below for why it is not on this platform.
  - ``bin/kstatsviewer`` — the sensor inspection CLI.
  - ``bin/ksystemstats_intel_helper`` — the Intel GPU perf helper
    (KDE_INSTALL_LIBEXECDIR maps to bin/ here).

OHOS-specific adaptations (recipe layer):

  - Platform family: the OHOS clang target (``aarch64-linux-ohos``) defines
    both ``__OHOS__`` and ``__linux__``, so Qt's ``qsystemdetection.h``
    reports ``Q_OS_LINUX`` and every ``#ifdef Q_OS_LINUX`` branch in the
    sources is taken. Conan, however, maps ``settings.os=OHOS`` to
    ``CMAKE_SYSTEM_NAME=HarmonyOS``, for which the upstream
    ``CMAKE_SYSTEM_NAME STREQUAL "Linux"`` gates are all false. That mismatch
    selects unbuildable code paths (``LinuxCpuPluginPrivate``,
    ``RtNetlinkBackend``, ``<sensors/sensors.h>``) while excluding the sources
    that provide them. Patch 0001 introduces a single
    ``KSYSTEMSTATS_LINUX_PLATFORM`` variable (Linux or HarmonyOS) that the
    remaining patches use, so the CMake gates and the preprocessor branches
    agree again and the real Linux backends are enabled instead of falling
    back to no-op stubs (R40).
  - KF6 floor: upstream requires KF6 >= 6.26.0. The published ohpcd KF6 matrix
    pinned by libksysguard/6.7.2 (the KSysGuard provider) is the 6.18 series
    (kcoreaddons/kconfig/ki18n/kservice 6.18.0), so patch 0001 lowers
    KF6_MIN_VERSION to 6.18.0 (libksysguard 6.7.2 0001 precedent).
  - KIO: the disks plugin is the only KIO consumer
    (``KIO::fileSystemFreeSpace`` for one statfs call). No published kio in the
    KF6 6.18 line exists: kio/6.26.0 hard-requires kcoreaddons/6.26.0 and
    forcing that (overrides) conflicts with kpackage/6.18.0.1 ->
    karchive/6.18.0 and would drop the prebuilt libksysguard/6.7.2 binary in
    favour of a from-source rebuild. Patches 0005/0006 make the KIO link
    selectable (``KSYSTEMSTATS_USE_KIO``, default ON) and add a dependency-free
    QStorageInfo fallback, which is what the recipe selects
    (kglobalacceld 6.7.2 WITH_KIO=OFF precedent).
  - lm-sensors: upstream marks it REQUIRED on Linux and uses
    ``KSysGuard::makeSensorsFeatureSensor`` in four places (daemon sensors init,
    cpu temperature, AMD GPU temperature, the lmsensors plugin). The published
    libksysguard/6.7.2 does not export that symbol for providers built without
    lm-sensors, so the sensors API is first made selectable — patches 0003/0008/
    0011/0017 wire ``SENSORS_LIBRARIES``/``SENSORS_INCLUDE_DIR`` into every
    target that uses it and gate the call sites on ``HAVE_SENSORS`` — and this
    recipe then sets ``KSYSTEMSTATS_WITH_LM_SENSORS=OFF``. The README/notes
    documents the resulting feature gap and the recovery path.
  - Qt6: ``qtbase/6.11.1.1`` with ``override=True``. Qt6::DBus is REQUIRED by
    the daemon and ``qtbase/6.11.1.1`` is the published release built with
    FEATURE_dbus=ON; the override unifies the transitive ``qtbase/6.11.1``
    references onto it and every dependency binary stays a registry hit
    (libksysguard/6.7.2 precedent).
  - Session bus: ``ksystemstatstest`` drives the daemon through
    ``QDBusConnection::sessionBus()`` and OHOS ships no session bus. The
    ``dbus/1.14.10.1`` tool package provides ``dbus-daemon``, which is started
    for the test run with the TCP + ANONYMOUS configuration the sandbox
    requires (AF_UNIX binds are denied; kglobalacceld/6.7.2 precedent).
  - Vendored shared libdbus-1: libQt6DBus loads its dbus client at runtime with
    ``QLibrary("libdbus-1")`` — it records neither a ``dbus_*`` import nor a
    ``libdbus-1.so`` NEEDED entry, so the library is invisible to readelf — and
    the registry only publishes a STATIC ``libdbus-1.a``. Without a shared
    library the load fails silently, ``QDBusConnection::sessionBus()`` returns
    an unconnected connection (``isConnected()==false``, empty baseService) and
    QtDBus crashes with SIGSEGV once a DBusInterface call is issued. ``source()``
    therefore extracts the official dbus 1.14.10 tarball, ``build()`` compiles a
    shared ``dbus-1`` target, ``_library_runtime_env()`` puts it on
    ``LD_LIBRARY_PATH`` and ``package()`` ships ``libdbus-1.so*`` under ``lib/``
    (kglobalacceld 6.7.2 precedent).
  - Ninja: the OHOS port of GNU make 4.4.1 creates an mkfifo-based jobserver
    that the sandbox denies (EPERM), which breaks any parallel make build, so
    the layout pins the Ninja generator (kglobalacceld/6.7.2 precedent).
"""
import glob
import os
import shutil
import subprocess
import xml.etree.ElementTree as ET

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    save,
)

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


class KsystemstatsConan(ConanFile):
    name = "ksystemstats"
    version = "6.7.2"
    description = "KDE Plasma system statistics daemon (KSystemStats)"
    license = "GPL-2.0-only OR GPL-3.0-only"
    homepage = "https://invent.kde.org/plasma/ksystemstats"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # qtbase/6.11.1.1 is the published Qt6 release built with
        # FEATURE_dbus=ON (Qt6::DBus is REQUIRED by the daemon and its D-Bus
        # adaptor). The override unifies the transitive qtbase/6.11.1
        # references onto it; all dependency binaries remain registry hits.
        self.requires("qtbase/6.11.1.1", override=True)
        # KF6 6.18 series — the matrix libksysguard/6.7.2 is built against.
        self.requires("kcoreaddons/6.18.0")
        self.requires("kcrash/6.18.0")
        self.requires("solid/6.26.0")
        # KSysGuard::SystemStats / Formatter / ProcessCore (the sensor
        # framework the daemon and the plugins are built on).
        self.requires("libksysguard/6.7.2")
        # The KSysGuard exported targets link Qt6::Qml/Qt6::Quick and
        # KF6::Service, and their link interfaces are resolved at
        # find_package(KSysGuard) time, so the providing packages are direct
        # requirements here (qtdeclarative/kservice are already in the
        # libksysguard graph at these exact versions).
        self.requires("qtdeclarative/6.11.1")
        self.requires("kservice/6.18.0")
        # Linux-like platform facilities, located by the top-level
        # find_package(NL)/find_package(UDev):
        self.requires("libnl/3.11.0")       # NL (REQUIRED): rtnetlink + sock_diag
        self.requires("eudev/3.2.14")       # UDev (RECOMMENDED): gpu device scan
        self.requires("libdrm/2.4.133")     # libdrm/i915_drm.h for the Intel helper
        # lm-sensors is deliberately NOT required: the lm-sensors based
        # temperature sensors also need KSysGuard::makeSensorsFeatureSensor,
        # which the published libksysguard/6.7.2 does not export (its
        # systemstats/CMakeLists.txt only compiles SensorsFeatureSensor.cpp
        # when it was itself configured with lm-sensors). See
        # KSYSTEMSTATS_WITH_LM_SENSORS below and notes.md.

    def build_requirements(self):
        self.tool_requires("ecm/6.26.0")
        # Provides dbus-daemon, used to start the session bus the upstream
        # ksystemstatstest needs (OHOS ships none).
        self.tool_requires("dbus/1.14.10.1")

    def layout(self):
        # Ninja avoids the mkfifo-based make jobserver the OHOS sandbox denies.
        cmake_layout(self, generator="Ninja")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Vendored shared libdbus-1.so.3 runtime: libQt6DBus loads the client
        # library at runtime with QLibrary("libdbus-1") and the registry only
        # publishes a STATIC libdbus-1.a, so without a shared library every
        # session bus connection is invalid (kglobalacceld 6.7.2 precedent,
        # DRAFT-dbus-1.14.10.1-ohos-session-bus-runtime).
        get(
            self,
            url="https://dbus.freedesktop.org/releases/dbus/dbus-1.14.10.tar.xz",
            sha256="ba1f21d2bd9d339da2d4aa8780c09df32fea87998b73da24f49ab9df1e36a50f",
            strip_root=True,
            destination="dbus-src",
        )

    def _vendored_libdbus_dir(self):
        return os.path.join(self.build_folder, "dbus-build", "lib")

    def _build_vendored_libdbus(self):
        """Build the shared dbus-1 client library (no expat needed)."""
        src = os.path.join(self.source_folder, "dbus-src")
        build = os.path.join(self.build_folder, "dbus-build")
        # The bundled CMake helper cannot configure a custom source/build
        # folder pair, so drive cmake directly against the same
        # conan_toolchain (Ninja generator, OHOS clang).
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
            # CMake has no platform module for this system; force the UNIX
            # branch so dbus does not pick its Windows transport.
            "CMAKE_SYSTEM_NAME": "OHOS",
            "DBUS_SESSION_SOCKET_DIR": "/tmp",
        }
        args = [
            "cmake",
            "-G",
            "Ninja",
            "-S",
            src,
            "-B",
            build,
            "-DCMAKE_TOOLCHAIN_FILE={}".format(
                os.path.join(self.generators_folder, "conan_toolchain.cmake")
            ),
        ]
        args += ["-D{}={}".format(key, value) for key, value in variables.items()]
        with self._cmake_build_env().vars(self).apply():
            self.run(" ".join(args))
            self.run('cmake --build "{}" --target dbus-1'.format(build))
        self.output.info(
            "vendored shared libdbus built in %s" % self._vendored_libdbus_dir()
        )

    def generate(self):
        tc = CMakeToolchain(self, generator="Ninja")
        tc.variables["BUILD_SHARED_LIBS"] = "ON"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_BUILD_PARALLEL_LEVEL"] = "1"
        # No published kio in the KF6 6.18 line (kio/6.26.0 requires
        # kcoreaddons/6.26.0, which conflicts with the libksysguard 6.7.2
        # dependency set); the disks plugin uses its QStorageInfo path.
        tc.variables["KSYSTEMSTATS_USE_KIO"] = "OFF"
        # The published libksysguard/6.7.2 was built without lm-sensors, so it
        # does not export KSysGuard::makeSensorsFeatureSensor and any consumer
        # of the lm-sensors temperature sensors fails to link. Build the
        # sensors-free paths instead (CPU/memory/disk/network/pressure plugins
        # and their upstream tests are unaffected).
        tc.variables["KSYSTEMSTATS_WITH_LM_SENSORS"] = "OFF"

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join(
                [
                    os.path.join(ecm_share, "modules"),
                    os.path.join(ecm_share, "find-modules"),
                    os.path.join(ecm_share, "kde-modules"),
                ]
            )

        self._write_cmake_paths()
        tc.variables["CMAKE_PROJECT_TOP_LEVEL_INCLUDES"] = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        tc.generate()

    def _write_cmake_paths(self):
        """CMake path layer.

        qtbase and the KF6 packages are published with cmake_find_mode=none,
        so CMakeDeps emits no conan_cmakedeps_paths.cmake for them. Build the
        prefix/library/include/module path lists from the declared
        dependencies so that both the config-mode lookups (Qt6, KSysGuard,
        UDev) and the module-mode lookups (FindSensors, FindNL) resolve.
        """
        prefixes = []
        libraries = []
        includes = []
        modules = []

        def add_unique(collection, value):
            normalized = value.replace("\\", "/")
            if normalized not in collection:
                collection.append(normalized)

        for dep in list(self.dependencies.values()) + list(
            self.dependencies.build.values()
        ):
            if dep and dep.package_folder:
                add_unique(prefixes, os.path.join(dep.package_folder, "lib", "cmake"))
                add_unique(prefixes, dep.package_folder)
                add_unique(libraries, os.path.join(dep.package_folder, "lib"))
                add_unique(includes, os.path.join(dep.package_folder, "include"))
                add_unique(modules, os.path.join(dep.package_folder, "lib", "cmake"))

        ecm = self.dependencies.build.get("ecm")
        if ecm and ecm.package_folder:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            add_unique(prefixes, os.path.join(ecm_share, "cmake"))
            for rel in ("modules", "find-modules", "kde-modules"):
                add_unique(modules, os.path.join(ecm_share, rel))

        lines = [
            "set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)",
            'set(CMAKE_PREFIX_PATH "{};${{CMAKE_PREFIX_PATH}}")'.format(
                ";".join(prefixes)
            ),
            'set(CMAKE_LIBRARY_PATH "{};${{CMAKE_LIBRARY_PATH}}")'.format(
                ";".join(libraries)
            ),
            'set(CMAKE_INCLUDE_PATH "{};${{CMAKE_INCLUDE_PATH}}")'.format(
                ";".join(includes)
            ),
            'set(CMAKE_MODULE_PATH "{};${{CMAKE_MODULE_PATH}}")'.format(
                ";".join(modules)
            ),
            'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")',
            'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")',
        ]
        paths_file = os.path.join(
            self.generators_folder, "conan_cmakedeps_paths.cmake"
        )
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def _system_lib_env(self, env):
        """Prepend the system library dirs so the compatible libc++_shared.so
        wins over the sandbox bundle copy (the ECM qtpaths host tool needs it
        during configure; kconfig/kdeclarative 6.26.0 precedent)."""
        if self.settings.os == "OHOS":
            for llvm_lib in sorted(
                glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"
                )
            ):
                env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")

    def _library_runtime_env(self, include_build=False):
        runtime_env = Environment()
        if self.settings.os == "OHOS":
            # The vendored shared libdbus-1.so.3 must be resolvable when
            # Qt6DBus loads it (see source()).
            vendored = self._vendored_libdbus_dir()
            if os.path.isdir(vendored):
                runtime_env.prepend_path("LD_LIBRARY_PATH", vendored)
        deps = list(self.dependencies.values())
        if include_build:
            deps += list(self.dependencies.build.values())
        for dep in deps:
            if dep and dep.package_folder:
                runtime_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                runtime_env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "bin")
                )
                runtime_env.prepend_path(
                    "PATH", os.path.join(dep.package_folder, "bin")
                )
                runtime_env.prepend_path(
                    "PKG_CONFIG_PATH",
                    os.path.join(dep.package_folder, "lib", "pkgconfig"),
                )
                runtime_env.prepend_path(
                    "QT_PLUGIN_PATH", os.path.join(dep.package_folder, "plugins")
                )
        for rel in ("bin", "lib"):
            runtime_env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.build_folder, rel)
            )
        return runtime_env

    def _cmake_build_env(self):
        build_env = self._library_runtime_env(include_build=True)
        self._system_lib_env(build_env)
        return build_env

    def build(self):
        apply_conandata_patches(self)
        if self.settings.os == "OHOS":
            self._build_vendored_libdbus()
        cmake = CMake(self)
        with self._cmake_build_env().vars(self).apply():
            cmake.configure()
            cmake.build()
        self._run_upstream_tests()

    # ── Upstream autotests (R51: census -> run -> report) ────────────────
    #
    # Upstream registers exactly THREE CTest executables (ecm_add_test):
    #
    #   1. ksystemstatstest  (autotests/,        always registered)
    #         QTest functions: initTestCase, findById, update, subscription,
    #         changes, dbusApi   -> 5 test functions (+ initTestCase)
    #   2. TestLinuxCpu      (plugins/cpu/autotests/, registered when the
    #         Linux platform is selected -> enabled by patch 0004)
    #         QTest functions: testParseCpuinfo (+ _data) -> 1 test function
    #   3. nvidiatest        (plugins/gpu/autotests/, registered together with
    #         the gpu plugin, which needs UDev -> present via eudev)
    #         QTest functions: testDmonParsing (+ _data) -> 1 test function
    #
    # ksystemstatstest drives the real Daemon over D-Bus, so it needs a session
    # bus; the OHOS sandbox denies AF_UNIX binds, hence the TCP + ANON bus.
    _UPSTREAM_TESTS = ("ksystemstatstest", "TestLinuxCpu", "nvidiatest")

    def _find_dbus_daemon(self):
        dbus_dep = self.dependencies.build.get("dbus")
        if not dbus_dep or not dbus_dep.package_folder:
            return None
        daemon = os.path.join(dbus_dep.package_folder, "bin", "dbus-daemon")
        return daemon if os.path.isfile(daemon) else None

    def _start_session_bus(self, workdir, env_vars):
        """Start a session bus (TCP + ANONYMOUS) and return (proc, address).

        The sandbox forbids AF_UNIX socket binds (EPERM) and the runtime has
        no passwd record for the running UID, so the bus listens on
        127.0.0.1 TCP with ANONYMOUS auth (kglobalacceld/6.7.2 precedent).
        """
        daemon = self._find_dbus_daemon()
        if not daemon:
            self.output.warning(
                "dbus-daemon not found in tool dependencies; the upstream "
                "D-Bus test will run without a session bus"
            )
            return None

        conf_path = os.path.join(workdir, "session-tcp.conf")
        save(self, conf_path, _SESSION_TCP_CONF)
        try:
            proc = subprocess.Popen(
                [daemon, "--config-file", conf_path, "--print-address", "--nofork"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                env=env_vars,
            )
            address = proc.stdout.readline().decode().strip()
            if proc.poll() is not None or not address.startswith("tcp:"):
                proc.terminate()
                self.output.warning(
                    "session bus failed to start (address=%r); the upstream "
                    "D-Bus test will run without a session bus" % address
                )
                return None
            self.output.info("session bus started: %s" % address)
            return proc, address
        except OSError as exc:
            self.output.warning("session bus could not be started: %s" % exc)
            return None

    # ── Legacy DT_NEEDED bridging (E537) ─────────────────────────────────
    #
    # Two dependency-side packaging quirks make the published
    # libksysguard/6.7.2 unloadable as-is, and both are bridged with
    # compatibility links before ctest runs (akonadi/baloo precedent):
    #
    #  1. libKSysGuardFormatter.so records its KF6 dependencies as absolute
    #     paths under the Conan cache layout of the machine it was built on
    #     (<home>/.cache/conan2/...). Loaders resolve DT_NEEDED entries that
    #     contain a "/" verbatim and never fall back to LD_LIBRARY_PATH, so the
    #     stale prefix is bridged to the live cache with one directory symlink.
    #  2. libKSysGuardSystemStats.so records libKSysGuardFormatter.so as the
    #     relative path "../bin/libKSysGuardFormatter.so", which the loader
    #     resolves against the process CWD. The library is materialized next to
    #     every directory the tests run from.
    _STALE_CACHE_MARKER = "/.cache/conan2/"

    def _find_readelf(self):
        for pattern in (
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/bin/llvm-readelf",
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/bin/readelf",
        ):
            for candidate in sorted(glob.glob(pattern)):
                if os.path.isfile(candidate):
                    return candidate
        return shutil.which("llvm-readelf") or shutil.which("readelf")

    def _runtime_elf_paths(self):
        roots = [os.path.join(self.build_folder, rel) for rel in ("bin", "lib")]
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                roots.append(os.path.join(dep.package_folder, "lib"))
        paths = []
        for root in roots:
            if not os.path.isdir(root):
                continue
            for entry in sorted(os.listdir(root)):
                full = os.path.join(root, entry)
                if ".so" in entry and os.path.isfile(full):
                    paths.append(full)
        return paths

    def _needed_entries(self, readelf, elf_path):
        try:
            completed = subprocess.run(
                [readelf, "-d", elf_path],
                capture_output=True,
                text=True,
                timeout=60,
            )
        except (OSError, subprocess.SubprocessError):
            return []
        entries = []
        for line in completed.stdout.splitlines():
            if "(NEEDED)" not in line:
                continue
            start, end = line.find("["), line.rfind("]")
            if start != -1 and end > start:
                entries.append(line[start + 1:end])
        return entries

    def _live_library_map(self):
        libraries = {}
        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                continue
            libdir = os.path.join(dep.package_folder, "lib")
            if not os.path.isdir(libdir):
                continue
            for entry in sorted(os.listdir(libdir)):
                if ".so" in entry and entry not in libraries:
                    full = os.path.join(libdir, entry)
                    if os.path.isfile(full):
                        libraries[entry] = full
        return libraries

    def _link_if_missing(self, source, target):
        if os.path.lexists(target):
            return False
        os.makedirs(os.path.dirname(target), exist_ok=True)
        try:
            os.symlink(source, target)
        except OSError:
            shutil.copy2(source, target)
        return True

    def _test_working_dirs(self):
        """Every directory ctest runs a test from (plus the build root)."""
        dirs = {os.path.abspath(self.build_folder)}
        for root, subdirs, files in os.walk(self.build_folder):
            subdirs[:] = [name for name in subdirs if name != "CMakeFiles"]
            if "CTestTestfile.cmake" in files:
                dirs.add(os.path.abspath(root))
        return sorted(dirs)

    def _bridge_legacy_needed_paths(self):
        """Bridge the published libksysguard/6.7.2 DT_NEEDED quirks (E537)."""
        if str(self.settings.os) != "OHOS":
            return
        readelf = self._find_readelf()
        if not readelf:
            self.output.warning(
                "readelf not found; skipping legacy DT_NEEDED bridging"
            )
            return

        libraries = self._live_library_map()
        working_dirs = self._test_working_dirs()
        stale_needed = set()
        relative_links = 0
        unstale_prefixes = set()

        for elf_path in self._runtime_elf_paths():
            for needed in self._needed_entries(readelf, elf_path):
                normalized = needed.replace("\\", "/")
                if os.path.isabs(needed):
                    if self._STALE_CACHE_MARKER in normalized:
                        stale_needed.add(normalized)
                    continue
                if "/" not in normalized:
                    continue
                source = libraries.get(os.path.basename(normalized))
                if not source:
                    continue
                for workdir in working_dirs:
                    target = os.path.normpath(os.path.join(workdir, normalized))
                    if self._link_if_missing(source, target):
                        relative_links += 1

        for needed in sorted(stale_needed):
            head, _, _tail = needed.partition(self._STALE_CACHE_MARKER)
            stale_root = head + "/.cache/conan2"
            live_root = head + "/.conan2"
            if os.path.exists(stale_root) or not os.path.isdir(live_root):
                continue
            try:
                os.symlink(live_root, stale_root)
            except OSError as exc:
                self.output.warning(
                    "could not bridge %s -> %s: %s" % (stale_root, live_root, exc)
                )
                continue
            unstale_prefixes.add(stale_root)
            self.output.info(
                "bridged stale Conan cache prefix %s -> %s" % (stale_root, live_root)
            )

        if relative_links:
            self.output.info(
                "materialized %d relative DT_NEEDED link(s) for ctest working "
                "directories" % relative_links
            )

    def _run_upstream_tests(self):
        test_env = self._library_runtime_env(include_build=False)
        self._system_lib_env(test_env)
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        test_env.define("CTEST_PARALLEL_LEVEL", "1")
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

        # The session bus runs outside conan's own environment, so it is
        # started while the runtime environment (notably expat/2.8.2's lib
        # directory, which dbus-daemon needs) is applied.
        self._bridge_legacy_needed_paths()
        bus = None
        with test_env.vars(self).apply():
            bus = self._start_session_bus(self.build_folder, dict(os.environ))
        if bus:
            test_env.define("DBUS_SESSION_BUS_ADDRESS", bus[1])
            self.output.info("test session bus: %s" % bus[1])
        try:
            with test_env.vars(self).apply():
                if bus:
                    # Belt and braces: make sure the address reaches the test
                    # processes even if a generator rewrites the environment.
                    os.environ["DBUS_SESSION_BUS_ADDRESS"] = bus[1]
                result = self.run(
                    'ctest --test-dir "{}" --output-on-failure '
                    '--no-tests=error --timeout 120 --output-junit "{}"'.format(
                        self.build_folder,
                        os.path.join(self.build_folder, "junit.xml"),
                    ),
                    ignore_errors=True,
                )
        finally:
            if bus:
                bus[0].terminate()
        self.output.info("ctest exit code: %s" % result)
        self._evaluate_ctest_results(
            os.path.join(self.build_folder, "junit.xml")
        )

    # Tests that are expected to fail on this platform, each with the concrete
    # technical reason recorded in notes.md and test_package/MANIFEST.yml.
    # Empty means "every registered upstream test must pass" (R51 / path A).
    _UPSTREAM_TEST_ALLOWANCES = {}

    def _evaluate_ctest_results(self, junit_path):
        """R51 step 3: assert the census, report the real numbers.

        Every test in the upstream census must be registered and must pass
        unless it carries a documented platform allowance.
        """
        if not os.path.isfile(junit_path):
            raise ConanException(
                "upstream ctest produced no junit report at %s" % junit_path
            )
        results = {}
        for case in ET.parse(junit_path).iter("testcase"):
            name = case.get("name", "")
            for token in self._UPSTREAM_TESTS:
                if token in name:
                    status = "passed"
                    if case.find("failure") is not None:
                        status = "failed"
                    elif case.find("skipped") is not None:
                        status = "skipped"
                    results[token] = status
                    break

        missing = sorted(set(self._UPSTREAM_TESTS) - set(results))
        if missing:
            raise ConanException(
                "upstream ctest did not report: %s" % ", ".join(missing)
            )

        summary = ", ".join("%s=%s" % (t, results[t]) for t in self._UPSTREAM_TESTS)
        self.output.info("upstream ctest results: %s" % summary)

        unallowed = [
            (t, results[t])
            for t in self._UPSTREAM_TESTS
            if results[t] != "passed" and t not in self._UPSTREAM_TEST_ALLOWANCES
        ]
        if unallowed:
            raise ConanException(
                "upstream tests did not pass (no documented allowance): %s"
                % ", ".join("%s=%s" % item for item in unallowed)
            )
        for token in self._UPSTREAM_TESTS:
            if token in self._UPSTREAM_TEST_ALLOWANCES and results[token] != "passed":
                self.output.info(
                    "upstream test %s result=%s, allowance: %s"
                    % (
                        token,
                        results[token],
                        self._UPSTREAM_TEST_ALLOWANCES[token],
                    )
                )

    def package(self):
        cmake = CMake(self)
        with self._library_runtime_env(include_build=True).vars(self).apply():
            cmake.install()
        if self.settings.os == "OHOS":
            # Ship the vendored shared libdbus-1.so.3: the packaged daemon
            # needs it at runtime for the same reason the tests do.
            lib_dir = os.path.join(self.package_folder, "lib")
            os.makedirs(lib_dir, exist_ok=True)
            vendored = self._vendored_libdbus_dir()
            for path in sorted(glob.glob(os.path.join(vendored, "libdbus-1.so*"))):
                target = os.path.join(lib_dir, os.path.basename(path))
                if os.path.islink(path):
                    if not os.path.lexists(target):
                        os.symlink(os.readlink(path), target)
                elif not os.path.exists(target):
                    shutil.copy2(path, target)

    def package_info(self):
        # Application package: no linkable libraries ship here. The sensor
        # plugins are dlopen'ed from <prefix>/lib/plugins/ksystemstats by the
        # daemon, and the CLI tools are declared in the software-level
        # commands.json (R38).
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        # The daemon locates its sensor plugins through
        # QCoreApplication::libraryPaths()/ksystemstats; KDEInstallDirs
        # installs them under lib/plugins/ksystemstats here, so consumers (and
        # the test_package) need that directory on QT_PLUGIN_PATH.
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
        self.runenv_info.prepend_path(
            "QT_PLUGIN_PATH", os.path.join(self.package_folder, "lib", "plugins")
        )
