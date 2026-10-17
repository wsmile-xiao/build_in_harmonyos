#!/usr/bin/env python3
"""Conan L1 test_package — libkysdk-applications 3.0.1.2.1 (Qt6 build).

Real consumer test (R34).  It builds ``probe.cpp`` against the *installed*
package, using the flags ``pkg-config`` emits for the ``kysdk-applications``
module, runs it, and re-runs it in ``test()``.

The probe (see probe.cpp) does not merely print a string:
  * dlopen(RTLD_NOW) on all four shipped shared objects (proves every DT_NEEDED
    of the artifacts resolves), and
  * constructs and uses kdk::KSwitchButton, KBorderlessButton, KTabBar,
    KPasswordEdit, KDialog and KWidget, and
  * includes the headers through both upstream spellings
    (``<kwidget.h>`` / ``<kpasswordedit.h>`` and
    ``<kysdk/applications/kdialog.h>``), which is exactly what the downstream
    Qt6 applet kylin-nm-plugin/4.0.0.1 needs.

The include/library flags of the package under test come from the *installed*
``kysdk-applications.pc`` (``pkg-config --cflags/--libs``), so a broken install
layout (missing nested include dir, renamed library) fails the test.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.layout import basic_layout

# directory name -> Qt module library name, for the Qt 6 modules the kdk
# widget set is built against (all shipped by qtbase-sql-dbus).
QT6_MODULES = [
    ("QtCore", "Qt6Core"),
    ("QtGui", "Qt6Gui"),
    ("QtWidgets", "Qt6Widgets"),
    ("QtDBus", "Qt6DBus"),
    ("QtNetwork", "Qt6Network"),
]


class LibkysdkApplicationsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("qtbase-sql-dbus/6.11.1")
        # the shipped libkysdk-qtwidgets links Qt6Svg and gsettings-qt; the probe
        # dlopen()s it with RTLD_NOW, so those prefixes must be on the search path.
        self.requires("qtsvg/6.11.1")
        self.requires("gsettings-qt/1.1.1")

    def layout(self):
        # out-of-source: the compiled probe must NOT land next to the recipe
        # (it is an ELF binary and would be picked up as junk by CI).
        basic_layout(self)

    # ── helpers ─────────────────────────────────────────────────────────────
    def _package(self):
        return self.dependencies["libkysdk-applications"]

    def _qtbase(self):
        return self.dependencies["qtbase-sql-dbus"]

    def _ld_paths(self):
        paths = []
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            libdir = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(libdir) and libdir not in paths:
                paths.append(libdir)
        return paths

    def _cxx(self):
        # R33: never rely on an ambient shell variable ($CXX) or a hardcoded
        # toolchain path.  The compiler is taken from the Conan profile
        # (`tools.build:compiler_executables`, already set by
        # ci/conan/profiles/ohos-aarch64) and we fail closed if it is absent.
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cxx = compilers.get("cpp")
        if not cxx:
            raise ConanInvalidConfiguration(
                "tools.build:compiler_executables['cpp'] is not set in the Conan "
                "profile; the L1 probe needs the profile's OHOS clang++ "
                "(ci/conan/profiles/ohos-aarch64)")
        if not os.path.isfile(cxx):
            raise ConanInvalidConfiguration(
                f"the cpp compiler from the profile does not exist: {cxx}")
        return cxx

    def _env(self):
        env = Environment()
        env.prepend_path("PKG_CONFIG_PATH",
                         os.path.join(self._package().package_folder, "lib", "pkgconfig"))
        for path in reversed(self._ld_paths()):
            env.prepend_path("LD_LIBRARY_PATH", path)
        env.define("QT_QPA_PLATFORM", "offscreen")
        qtbase = self._qtbase().package_folder
        env.define("QT_PLUGIN_PATH", os.path.join(qtbase, "plugins"))
        env.define("QT_QPA_PLATFORM_PLUGIN_PATH",
                   os.path.join(qtbase, "plugins", "platforms"))
        return env

    @staticmethod
    def _pkg_config(args):
        """Run pkg-config and return (rc, stdout+stderr)."""
        pkg_config = shutil.which("pkg-config") or "pkg-config"
        proc = subprocess.run([pkg_config] + args, capture_output=True, text=True)
        return proc.returncode, (proc.stdout + proc.stderr).strip()

    def _qt_flags(self):
        qtbase = self._qtbase().package_folder
        inc = os.path.join(qtbase, "include")
        lib = os.path.join(qtbase, "lib")
        cflags = [f"-I{inc}"]
        for directory, _ in QT6_MODULES:
            cflags.append(f"-I{inc}/{directory}")
        cflags.append(f"-I{os.path.join(qtbase, 'mkspecs', 'harmonyos-clang')}")
        libs = [f"-L{lib}"] + [f"-l{name}" for _, name in QT6_MODULES]
        return cflags, libs

    # ── build ───────────────────────────────────────────────────────────────
    def build(self):
        if not can_run(self):
            self.output.warning("cross-build: cannot run, skipping the probe")
            return

        pkg = self._package()
        libdir = os.path.join(pkg.package_folder, "lib")
        probe_src = os.path.join(self.source_folder, "probe.cpp")
        probe_bin = os.path.join(self.build_folder, "probe")

        with self._env().vars(self).apply():
            # 1) the pkg-config module must exist and emit the contract flags
            rc, cflags = self._pkg_config(["--cflags", "kysdk-applications"])
            if rc != 0:
                raise ConanInvalidConfiguration(
                    "pkg-config cannot find the kysdk-applications module: " + cflags)
            rc, libs = self._pkg_config(["--libs", "kysdk-applications"])
            if rc != 0:
                raise ConanInvalidConfiguration(
                    "pkg-config --libs kysdk-applications failed: " + libs)
            self.output.info(f"kysdk-applications Cflags: {cflags}")
            self.output.info(f"kysdk-applications Libs:   {libs}")
            # the .pc is relocatable (${pcfiledir}), so the emitted -I paths are
            # only equal to the package paths after normalisation
            emitted_includes = [os.path.normpath(tok[2:])
                                for tok in cflags.split() if tok.startswith("-I")]
            for wanted in (os.path.join(pkg.package_folder, "include"),
                           os.path.join(pkg.package_folder, "include",
                                        "kysdk", "applications")):
                if os.path.normpath(wanted) not in emitted_includes:
                    raise ConanInvalidConfiguration(
                        f"pkg-config Cflags is missing -I{wanted}: {cflags}")

            # 2) build the consumer program against the installed package
            qt_cflags, qt_libs = self._qt_flags()
            command = (f'"{self._cxx()}" -std=c++17 -fPIC "{probe_src}" '
                       f'-o "{probe_bin}" {cflags} {libs} '
                       f'{" ".join(qt_cflags)} {" ".join(qt_libs)}')
            # NB: no -ldl — dlopen lives in libc on OHOS/musl.
            self.run(command)

            # 3) run it: dlopen all four .so + instantiate the kdk widgets
            self.run(f'"{probe_bin}" "{libdir}"')

    def test(self):
        if not can_run(self):
            self.output.warning("cross-build: cannot run, skipping")
            return

        pkg = self._package()
        probe_bin = os.path.join(self.build_folder, "probe")
        if not os.path.isfile(probe_bin):
            raise ConanInvalidConfiguration(
                "probe binary was not produced by build(); L1 runtime test cannot run")

        # 1) real run of the real consumer program against the real artifacts
        with self._env().vars(self).apply():
            self.run(f'"{probe_bin}" "{os.path.join(pkg.package_folder, "lib")}"')

        # 2) artifact presence + install-layout sanity
        for name in ("kysdk-qtwidgets", "kysdk-alm", "kysdk-ukenv", "kysdk-widgetutils"):
            lib = os.path.join(pkg.package_folder, "lib", f"lib{name}.so")
            if not os.path.isfile(lib):
                raise ConanInvalidConfiguration(f"missing shipped library: {lib}")
        for header in ("kwidget.h", "kpasswordedit.h", "kswitchbutton.h",
                       "kborderlessbutton.h", "ktabbar.h", "kdialog.h"):
            path = os.path.join(pkg.package_folder, "include", "kysdk",
                                "applications", header)
            if not os.path.isfile(path):
                raise ConanInvalidConfiguration(f"missing public header: {path}")
        pc = os.path.join(pkg.package_folder, "lib", "pkgconfig", "kysdk-applications.pc")
        with open(pc, encoding="utf-8") as handle:
            content = handle.read()
        for needle in ("-lkysdk-qtwidgets", "-I${includedir}/kysdk/applications",
                       "-I${includedir}"):
            if needle not in content:
                raise ConanInvalidConfiguration(
                    f"kysdk-applications.pc lacks {needle!r}")

        # 3) the restored Qt6 capabilities' runtime deps must be reachable
        #    (libkysdk-qtwidgets is linked against Qt6Svg + gsettings-qt).
        wanted_libs = {"libQt6Svg.so": False, "libgsettings-qt6.so": False}
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            libdir = os.path.join(dep.package_folder, "lib")
            if not os.path.isdir(libdir):
                continue
            for entry in os.listdir(libdir):
                for name in list(wanted_libs):
                    if entry == name or entry.startswith(name + "."):
                        wanted_libs[name] = True
        for name, found in wanted_libs.items():
            if not found:
                raise ConanInvalidConfiguration(
                    f"restored dependency library {name} not found in any "
                    "dependency libdir (Qt6Svg/gsettings-qt wiring is broken)")
        self.output.info(
            "PASS: pkg-config module, libraries, public headers and the "
            "restored Qt6Svg/gsettings-qt runtime deps verified")
