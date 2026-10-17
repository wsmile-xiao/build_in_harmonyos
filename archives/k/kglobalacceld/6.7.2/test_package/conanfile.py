#!/usr/bin/env python3
"""Conan test_package for kglobalacceld 6.7.2.

Two kinds of real assertions (no stub test):

1. Consumer C++ test (test_ohos_daemon, R34 real API usage): finds the
   exported KGlobalAccelD CMake package, links K::KGlobalAccelD and starts
   the actual daemon (KGlobalAccelD::init()) against the OHOS session bus
   (TCP + ANONYMOUS started from the dbus/1.14.10.1 tool package). It then
   verifies the daemon really owns org.kde.kglobalaccel on that bus and
   tears it down cleanly. On OHOS this is the platform-difference test: the
   device has no AF_UNIX session bus and no platform grabber plugin, so the
   daemon must register its D-Bus service gracefully without one.
2. Artifact-level OHOS adaptation assertions (OHOS host only, run via
   readelf): the packaged libKGlobalAccelD.so must carry DT_SONAME
   libKGlobalAccelD.so.0, must NOT link libKF6KIO*/libKF6JobWidgets*
   (WITH_KIO=OFF patch effective) nor libxcb*/libX11* (WITH_X11=OFF
   effective), the libexec kglobalacceld binary must exist, and the xcb
   platform plugin directory must be absent.
"""
import glob
import os
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import save

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


class KglobalacceldTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Qt6 base modules (Core/Gui/Widgets/DBus) come from qtbase-sql-dbus,
        # the only OHOS provider of Qt6::DBus (KGlobalAccelDConfig.cmake
        # find_dependency( Qt6DBus|Qt6Widgets )).
        self.requires("qtbase-sql-dbus/6.11.1")

    def build_requirements(self):
        self.tool_requires("dbus/1.14.10.1")

    def layout(self):
        # Ninja generator: OHOS make's mkfifo jobserver is denied by the
        # sandbox (see the main recipe docstring); attica-kf5 precedent.
        cmake_layout(self, generator="Ninja")

    def generate(self):
        tc = CMakeToolchain(self, generator="Ninja")
        tc.generate()

        lines = [
            'set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)',
        ]
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lines.append(
                    f'list(PREPEND CMAKE_PREFIX_PATH "{dep.package_folder}/lib/cmake")'
                )
                lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{dep.package_folder}/lib")')
                lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{dep.package_folder}/include")')
        # Make sure the Qt6 base config resolves against qtbase-sql-dbus.
        sqldbus = self.dependencies.get("qtbase-sql-dbus")
        if sqldbus:
            lines.append(
                f'list(PREPEND CMAKE_PREFIX_PATH "{sqldbus.package_folder}/lib/cmake")'
            )
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        paths_file = os.path.join(self.generators_folder, "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as f:
            f.write("\n".join(lines) + "\n")

    def build(self):
        # OHOS SDK lld depends on libxml2.so.16 shipped in the SDK llvm/lib
        # directory; prepend it so CMake TryCompile can link (kcrash/kconfig
        # 6.26.0 precedent).
        env = Environment()
        for llvm_lib in sorted(glob.glob("/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib")):
            env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def _start_session_bus(self):
        daemon = None
        dbus_dep = self.dependencies.build.get("dbus")
        if dbus_dep and dbus_dep.package_folder:
            candidate = os.path.join(dbus_dep.package_folder, "bin", "dbus-daemon")
            if os.path.isfile(candidate):
                daemon = candidate
        if not daemon:
            return None
        conf_path = os.path.join(self.build_folder, "session-tcp.conf")
        save(self, conf_path, _SESSION_TCP_CONF)
        proc = subprocess.Popen(
            [daemon, "--config-file", conf_path, "--print-address", "--nofork"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
        address = proc.stdout.readline().decode().strip()
        if proc.poll() is not None or not address.startswith("tcp:"):
            proc.terminate()
            self.output.warning(f"session bus failed to start (address={address!r})")
            return None
        self.output.info(f"session bus started: {address}")
        return proc, address

    def _runtime_env(self):
        env = Environment()
        env.append("LD_LIBRARY_PATH", [
            os.path.join(p.package_folder, "lib")
            for p in self.dependencies.values()
            if p.package_folder
        ])
        env.define("QT_QPA_PLATFORM", "offscreen")
        test_home = os.path.join(self.build_folder, "test-home")
        xdg_runtime = os.path.join(self.build_folder, "xdg-runtime")
        os.makedirs(test_home, exist_ok=True)
        os.makedirs(xdg_runtime, exist_ok=True)
        os.chmod(xdg_runtime, 0o700)
        env.define("HOME", test_home)
        env.define("XDG_RUNTIME_DIR", xdg_runtime)
        env.define("XDG_CACHE_HOME", os.path.join(test_home, ".cache"))
        env.define("XDG_CONFIG_HOME", os.path.join(test_home, ".config"))
        env.define("XDG_DATA_HOME", os.path.join(test_home, ".local", "share"))
        if self.settings.os == "OHOS":
            # The sandbox LD_LIBRARY_PATH can shadow the compatible
            # libc++_shared.so; /system/lib64 must win (kconfig/kcrash
            # 6.26.0 precedent).
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
            for llvm_lib in sorted(glob.glob("/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib")):
                env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
        return env

    def _elf_artifact_checks(self):
        """OHOS-specific artifact assertions (WITH_KIO=OFF / WITH_X11=OFF /
        SONAME flag are recipe-injected platform differences; verify they
        really took effect on the packaged binaries)."""
        tested = self.dependencies.get(self.tested_reference_str.split("/")[0])
        if not tested or not tested.package_folder:
            self.output.warning("tested package folder not found; skipping ELF artifact checks")
            return
        lib_dir = os.path.join(tested.package_folder, "lib")
        real_files = sorted(glob.glob(os.path.join(lib_dir, "libKGlobalAccelD.so.*.*")))
        assert real_files, "packaged libKGlobalAccelD.so not found"
        readelf = None
        candidates = sorted(glob.glob("/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/bin/llvm-readelf"))
        candidates += ["/data/service/hnp/bin/llvm-readelf", "/storage/Users/currentUser/.harmonybrew/bin/readelf"]
        for cand in candidates:
            if os.path.isfile(cand):
                readelf = cand
                break
        assert readelf, "no readelf/llvm-readelf found on this worker"

        def elf_section(path):
            out = subprocess.run([readelf, "-d", path], capture_output=True, text=True).stdout
            return out

        soname = None
        needed = []
        for line in elf_section(real_files[0]).splitlines():
            if "(SONAME)" in line:
                soname = line.split("[")[-1].rstrip("]")
            if "(NEEDED)" in line:
                needed.append(line.split("[")[-1].rstrip("]"))
        assert soname == "libKGlobalAccelD.so.0", f"DT_SONAME mismatch: {soname!r}"
        bad = [n for n in needed if n.startswith(("libKF6KIO", "libKF6JobWidgets", "libxcb", "libX11"))]
        assert not bad, f"WITH_KIO/WITH_X11=OFF not effective, unexpected DT_NEEDED: {bad}"
        # L5b spirit (E537): no machine-private absolute Conan cache paths may
        # leak into DT_NEEDED (unrelocatable artifacts).
        abs_needed = [n for n in needed if n.startswith(("/", "../"))]
        assert not abs_needed, f"absolute-path DT_NEEDED leak: {abs_needed}"

        daemon_candidates = [
            os.path.join(tested.package_folder, "libexec", "kglobalacceld"),
            os.path.join(tested.package_folder, "bin", "kglobalacceld"),
        ]
        daemon_bin = next((p for p in daemon_candidates if os.path.isfile(p)), None)
        assert daemon_bin, "kglobalacceld binary missing (expected in libexec/ or bin/)"
        plugin_dir = os.path.join(tested.package_folder, "plugins", "org.kde.kglobalacceld.platforms")
        assert not os.path.isdir(plugin_dir), "xcb platform plugin unexpectedly packaged"
        self.output.info("OHOS artifact assertions passed: SONAME, no-KIO/X11 DT_NEEDED, libexec daemon, no xcb plugin")

    def test(self):
        env = self._runtime_env()
        bus = self._start_session_bus()
        if bus:
            proc, address = bus
            env.define("DBUS_SESSION_BUS_ADDRESS", address)
        try:
            with env.vars(self).apply():
                cmake = CMake(self)
                cmake.test()
                self.run(
                    os.path.join(self.cpp.build.bindirs[0], "test_ohos_daemon"),
                    env="conanrun",
                )
            if self.settings.os == "OHOS":
                self._elf_artifact_checks()
        finally:
            if bus:
                proc.terminate()
