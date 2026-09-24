#!/usr/bin/env python3
"""Conan recipe — libguytools2 2.1.0.

libguytools2 is the shared support library of the Guymager forensic imager.
It provides logging (t_Log), an error registry (ToolError), a configuration
file/command-line parser (ToolCfg), a signal-guarding thread (ToolSignal) and
system information helpers (ToolSysInfo).

Upstream: https://sourceforge.net/projects/libguytools/
Tarball:  libguytools/LatestSource/tools-2.1.0.tar.gz
Build:    qmake (Qt5 .pro project) — NOTE: upstream ships no configure/CMake
          and no install rules; this recipe generates the missing version
          include and drives qmake/make directly (see patches/).

Status: built (local W3 verification passed)
"""

import os
import re

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout
from conan.tools.scm import Version


class Libguytools2Conan(ConanFile):
    name = "libguytools2"
    version = "2.1.0"
    description = (
        "libguytools2 — support library of the Guymager forensic imager: "
        "logging, error registry, configuration parsing, signal guarding, "
        "system information"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/libguytools/"
    url = "https://sourceforge.net/projects/libguytools/"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # The library only uses QMutex (toollog.cpp) and QString (toolsysinfo.h
        # public API) — both live in QtCore, so a plain qt5-qtbase suffices.
        # transitive_headers/transitive_libs: tooltypes.h and toolsysinfo.h
        # expose QString in the public API, so consumers need Qt5 headers.
        self.requires("qt5-qtbase/5.15.2", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: settings.os checks must accept both Linux and OHOS.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} only supports Linux and OHOS, got {self.settings.os}"
            )
        if self.settings.compiler == "clang" and Version(self.settings.compiler.version) < "15":
            raise ConanInvalidConfiguration(
                f"{self.name} requires clang >= 15, got {self.settings.compiler.version}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _qtbase(self):
        return self.dependencies["qt5-qtbase"]

    def _qmake_path(self):
        qtbase = self._qtbase()
        if qtbase.package_folder is None:
            raise ConanInvalidConfiguration("qt5-qtbase has no package folder")
        qmake = os.path.join(qtbase.package_folder, "bin", "qmake")
        if not os.path.exists(qmake):
            raise ConanInvalidConfiguration(f"qmake not found in qt5-qtbase: {qmake}")
        return qmake

    def generate(self):
        VirtualBuildEnv(self).generate()

    def _setup_qmake_modules(self, build_env):
        """Expose qt5-qtbase's Qt module .pri files to qmake.

        The .pri files shipped inside qt5-qtbase/mkspecs/modules record the
        *build-time* absolute paths (e.g. .../.conan2/p/b/qt5-qXXXX/b), which no
        longer exist once the recipe has been packaged. Because the paths are
        also inconsistent (a stale package hash, not the one in this graph),
        qmake reports "Unknown module(s) in QT: core".

        Copy the module .pri files into this recipe's build folder, rewrite the
        dangling build paths to the Qt5 package folder, and expose the copy via
        QMAKEMODULES (same approach as the baka 2.0.4 recipe).
        """
        qtbase = self._qtbase()
        if qtbase.package_folder is None:
            return
        pkg_root = qtbase.package_folder

        modules_root = os.path.join(self.build_folder, "qmake-modules")
        modules_dir = os.path.join(modules_root, "modules")
        # The copied .pri files include files from <pkg>/mkspecs/modules-inst,
        # so rewrite those include paths to point at the package folder too.
        os.makedirs(modules_dir, exist_ok=True)

        src_modules = os.path.join(pkg_root, "mkspecs", "modules")
        if not os.path.isdir(src_modules):
            return

        for name in os.listdir(src_modules):
            if not name.endswith(".pri"):
                continue
            src = os.path.join(src_modules, name)
            dst = os.path.join(modules_dir, name)
            with open(src, "r", encoding="utf-8") as handle:
                content = handle.read()
            # .../.conan2/p/b/<stale-pkg>/b  ->  <pkg_root>
            content = re.sub(r"/[^\s)]*?conan2/p/b/[^/\s)]+/b", pkg_root, content)
            with open(dst, "w", encoding="utf-8") as handle:
                handle.write(content)

        build_env.define("QMAKEMODULES", modules_dir)

    def build(self):
        apply_conandata_patches(self)
        qmake = self._qmake_path()
        src = self.source_folder

        build_env = Environment()
        qtbase = self._qtbase()
        if qtbase.package_folder:
            # qmake needs the Qt5 libraries on its own RUNPATH while it runs the
            # moc/uic helper binaries shipped inside the qt5-qtbase package.
            build_env.append("LD_LIBRARY_PATH", os.path.join(qtbase.package_folder, "lib"))
        self._setup_qmake_modules(build_env)

        with build_env.vars(self).apply():
            # Upstream ships no libguytools_version.pro.inc; tools.pro includes
            # it unconditionally. create_version_file.sh derives it, but relies
            # on a Debian-specific `debian/changelog` path, so generate the file
            # in a portable way.
            version_file = os.path.join(src, "libguytools_version.pro.inc")
            with open(version_file, "w", encoding="utf-8") as handle:
                handle.write(f"VERSION = {self.version}\n")

            # qmake defaults to the linux-g++ mkspec; force the clang one to
            # match the conan clang toolchain, and disable strip (the OHOS
            # loader rejects stripped ELF binaries).
            self.run(
                f'cd "{src}" && "{qmake}" trunk.pro -spec linux-clang',
                env="conanbuild",
            )
            self.run(
                f'cd "{src}" && make -j1 QMAKE_STRIP=""',
                env="conanbuild",
            )

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

        lib_dir = os.path.join(self.source_folder, "lib")
        # Keep the versioned SONAME layout produced by qmake:
        # libguytools.so -> libguytools.so.2 -> libguytools.so.2.1.0
        copy(self, "libguytools.so*", src=lib_dir,
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)

        copy(self, "*.h", src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include", "libguytools"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["guytools"]
        self.cpp_info.includedirs = ["include", os.path.join("include", "libguytools")]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
