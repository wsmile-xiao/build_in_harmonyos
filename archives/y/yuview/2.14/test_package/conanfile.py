#!/usr/bin/env python3
"""Consumer test for the YUView package.

YUView upstream installs an application binary and builds a static library
(YUViewLib) rather than installing a library with public headers. The package
therefore ships both, and this test exercises both:

1. a real consumer program is compiled against the packaged YUViewLib headers
   and linked against the packaged YUViewLib archive, then executed;
2. the packaged YUView executable is queried through its command line.

Removing either artifact makes the test fail, so it cannot pass against an
empty or broken package.
"""

import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment


class YUViewTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # The consumer program compiles against the Qt headers and links the Qt
        # libraries, so Qt must be a direct requirement here as well.
        self.requires("qtbase/6.11.1.3")

    def layout(self):
        self.folders.source = "."
        self.folders.build = "build"

    def build(self):
        """Compile the consumer program against the packaged YUViewLib SDK."""
        for directory in (self._sdk_include_dir(), self._sdk_lib_dir()):
            if not os.path.isdir(directory):
                raise ConanInvalidConfiguration(
                    "The YUViewLib SDK is missing from the package: {}".format(directory)
                )
        qt_include = self._qt_include_dir()
        command = [
            self._compiler(),
            "-std=c++17",
            "-fPIC",
            "-I{}".format(self._sdk_include_dir()),
            # Qt modules keep their headers in per-module subdirectories that
            # have to be reached both through the top level include directory
            # and directly.
            "-I{}".format(qt_include),
            "-I{}".format(os.path.join(qt_include, "QtCore")),
            "-I{}".format(os.path.join(qt_include, "QtGui")),
            "-I{}".format(os.path.join(qt_include, "QtWidgets")),
            os.path.join(self.source_folder, "test_yuviewlib.cpp"),
            self._sdk_library(),
            "-L{}".format(self._qt_lib_dir()),
            "-lQt6Core", "-lQt6Gui", "-lQt6Widgets",
            "-o", os.path.join(self.build_folder, "test_yuviewlib"),
        ]
        # Linking the consumer needs the OHOS SDK linker libraries on the
        # loader path, exactly like the recipe's own build block (E120/E132).
        with self._link_environment().vars(self).apply():
            result = subprocess.run(command)
        if result.returncode != 0:
            raise ConanInvalidConfiguration(
                "Compiling the YUViewLib consumer failed with exit code {}".format(
                    result.returncode
                )
            )

    def test(self):
        if not can_run(self):
            return
        consumer = os.path.join(self.build_folder, "test_yuviewlib")
        if not os.path.isfile(consumer):
            raise ConanInvalidConfiguration(
                "The compiled YUViewLib consumer is missing: {}".format(consumer)
            )
        with self._environment().vars(self).apply():
            self.run(consumer, env="conanrun")
            self.run("{} --version".format(shlex.quote(self._binary())), env="conanrun")
            self.run("{} --help".format(shlex.quote(self._binary())), env="conanrun")

    # ── package layout ─────────────────────────────────────────────────────

    def _yuview_package_folder(self):
        return self.dependencies["yuview"].package_folder

    def _sdk_include_dir(self):
        return os.path.join(self._yuview_package_folder(), "sdk", "YUViewLib", "src")

    def _sdk_lib_dir(self):
        return os.path.join(self._yuview_package_folder(), "sdk", "YUViewLib")

    def _sdk_library(self):
        library = os.path.join(self._sdk_lib_dir(), "libYUViewLib.a")
        if not os.path.isfile(library):
            raise ConanInvalidConfiguration(
                "The packaged YUViewLib archive is missing: {}".format(library)
            )
        return library

    def _binary(self):
        return os.path.join(self._yuview_package_folder(), "bin", "YUView")

    # ── Qt helpers ─────────────────────────────────────────────────────────

    def _qt_package_folder(self):
        dependency = self.dependencies.direct_host.get("qtbase")
        if dependency is None or not dependency.package_folder:
            raise ConanInvalidConfiguration("qtbase is not an available dependency")
        return dependency.package_folder

    def _qt_include_dir(self):
        return os.path.join(self._qt_package_folder(), "include")

    def _qt_lib_dir(self):
        return os.path.join(self._qt_package_folder(), "lib")

    def _compiler(self):
        """Locate the C++ compiler the same way the recipe does (R33).

        The Conan configuration is the authoritative source; the PATH lookup is
        only a fallback for environments that do not set it.
        """
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        return compilers.get("cpp") or shutil.which("clang++") or "clang++"

    def _environment(self):
        env = Environment()
        qt = self._qt_package_folder()
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(qt, "lib"))
        env.prepend_path("QT_PLUGIN_PATH", os.path.join(qt, "plugins"))
        env.define("QT_QPA_PLATFORM", "offscreen")
        return env

    def _link_environment(self):
        """Environment for compiling/linking the consumer program.

        The OHOS SDK drives `llvm/bin/lld` in-process, and that linker is a
        dynamically linked host ELF needing `libxml2.so.16` from its sibling
        `llvm/lib` directory (E120/E132). CI workers do not expose that
        directory on the loader path, so linking fails with
        `Error loading shared library libxml2.so.16` even though the package
        itself was built successfully.

        Scoped to the compile/link invocation only: `test()` keeps using
        `_environment()`, so the SDK host libraries stay out of the target test
        processes (E341 forbid_2).
        """
        env = self._environment()
        libdir = self._ohos_sdk_llvm_libdir()
        if libdir:
            env.prepend_path("LD_LIBRARY_PATH", libdir)
        return env

    def _ohos_sdk_llvm_libdir(self):
        """Locate the OHOS SDK llvm/lib directory that ships libxml2.so.16."""
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        clang = compilers.get("c") or shutil.which("clang") or ""
        if clang:
            # <sdk>/native/llvm/bin/clang -> <sdk>/native/llvm/lib
            candidate = os.path.join(
                os.path.dirname(os.path.dirname(os.path.realpath(clang))), "lib"
            )
            if os.path.isfile(os.path.join(candidate, "libxml2.so.16")):
                return candidate
        return ""
