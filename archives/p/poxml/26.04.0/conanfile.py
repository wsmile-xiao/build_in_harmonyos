#!/usr/bin/env python3
"""Conan recipe for poxml 26.04.0 on HarmonyOS PC — KDE gettext/PO toolset.

poxml ships the DocBook <-> gettext PO converters used by KDE's
documentation workflow: split2po, xml2pot, po2xml and swappo.  It is a
plain CMake + ECM (extra-cmake-modules) project.

Dependencies (from upstream CMakeLists.txt):
  find_package(ECM)                        -> tool_requires ecm
  find_package(GettextPO REQUIRED)         -> gettext (gettext-po.h + libgettextpo)
  find_package(Gettext)                    -> gettext (msgfmt/msgmerge, tests)
  find_package(Qt6 Core Xml REQUIRED)      -> qtbase/6.11.1
  find_package(KF6 REQUIRED COMPONENTS DocTools)
                                           -> kdoctools/6.19.0 (kdoctools_install,
                                              kdoctools_create_manpage, checkXML6)

Notes specific to this adaptation:
* Upstream's own ``cmake/modules/FindGettextPO.cmake`` is a plain
  ``find_path``/``find_library`` probe (no config package), so the gettext
  package prefix must be on CMAKE_PREFIX_PATH — supplied by the generated
  ``conan_cmakedeps_paths.cmake`` (see ``_write_cmake_paths``).
* ``KF_SKIP_PO_PROCESSING=ON``: the translation catalogues are irrelevant
  to the tools themselves and would need a full gettext pipeline.
* ``KF_IGNORE_PLATFORM_CHECK=TRUE``: ECM's platform check does not know
  HarmonyOS.
* BUILD_TESTING=ON runs the upstream ctest targets (tests/CMakeLists.txt,
  two tests: ``lauri_de`` via checkXML6 and ``split2po``); they are gated by
  GETTEXT_FOUND upstream and cover the real converter pipeline.

R32/R38: application package shipping bin/ tools -> archives/p/poxml/commands.json.
R51: upstream ctest targets are really executed in build().
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)


class PoxmlConan(ConanFile):
    name = "poxml"
    version = "26.04.0"
    description = ("poxml — KDE tools to convert DocBook XML and gettext PO "
                   "files (split2po, xml2pot, po2xml, swappo)")
    license = "GPL-2.0-or-later"
    homepage = "https://invent.kde.org/sdk/poxml"
    url = "https://download.kde.org/stable/release-service/26.04.0/src/poxml-26.04.0.tar.xz"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("poxml is supported only on Linux/OHOS")

    def requirements(self):
        # Qt6 Core + Xml
        self.requires("qtbase/6.11.1")
        # GettextPO (gettext-po.h + libgettextpo) and the gettext CLI tools
        # used by the upstream tests (msgfmt/msgmerge).
        self.requires("gettext/0.22.5.1")
        # NOTE: kdoctools (KF6 DocTools) is deliberately NOT a dependency —
        # patch 0001 removes the DocBook man-page chain, which requires the
        # DocBook XML 4.5 DTD that this platform does not provide; the four
        # converter tools do not link it (kfourinline precedent).

    def build_requirements(self):
        self.tool_requires("ecm/6.20.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
        tc.variables["CMAKE_INSTALL_LIBDIR"] = "lib"
        # No Platform/HarmonyOS CMake module -> supply -Wl,-soname explicitly
        # (baloo/keditbookmarks 26.04.x precedent).
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])
        self._write_cmake_paths(ecm)
        tc.generate()

    def _write_cmake_paths(self, ecm):
        # qtbase / KF6 / gettext use cmake_find_mode=none, so the generated
        # conan_cmakedeps_paths.cmake lacks their lib/cmake dirs; recreate it
        # (baloo / keditbookmarks precedent) so both find_package() and
        # upstream's bare find_path()/find_library() probes resolve.
        lines = ["set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)"]
        for dep in (list(self.dependencies.values())
                    + list(self.dependencies.build.values())):
            if dep and dep.package_folder:
                lines.append('list(PREPEND CMAKE_PREFIX_PATH "%s/lib/cmake")'
                             % dep.package_folder)
                lines.append('list(PREPEND CMAKE_PREFIX_PATH "%s")'
                             % dep.package_folder)
                lines.append('list(PREPEND CMAKE_LIBRARY_PATH "%s/lib")'
                             % dep.package_folder)
                lines.append('list(PREPEND CMAKE_INCLUDE_PATH "%s/include")'
                             % dep.package_folder)
        if ecm and ecm.package_folder:
            ecm_cmake = os.path.join(ecm.package_folder, "share", "ECM", "cmake")
            lines.append('list(PREPEND CMAKE_PREFIX_PATH "%s")' % ecm_cmake)
            lines.append('list(PREPEND CMAKE_MODULE_PATH "%s")' % ecm_cmake)
        if self.settings.os == "OHOS":
            # OHOS sysroot usr/include for CMake find_path() probes.
            for sdk_inc in sorted(glob.glob(
                    "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/"
                    "sysroot/usr/include")):
                lines.append('list(PREPEND CMAKE_INCLUDE_PATH "%s")' % sdk_inc)
        lines.append('list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        lines.append('list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")')
        paths_file = os.path.join(self.generators_folder,
                                  "conan_cmakedeps_paths.cmake")
        with open(paths_file, "w") as fh:
            fh.write("\n".join(lines) + "\n")

    def _runtime_env(self):
        env = Environment()
        for dep in self.dependencies.values():
            if not dep or not dep.package_folder:
                continue
            env.prepend_path("LD_LIBRARY_PATH",
                             os.path.join(dep.package_folder, "lib"))
            for bindir in dep.cpp_info.bindirs:
                env.prepend_path("PATH", bindir)
        for rel in ("bin", "lib"):
            env.prepend_path("LD_LIBRARY_PATH",
                             os.path.join(self.build_folder, rel))
        return env

    def _build_env(self):
        # Host tools (moc, meinproc6, checkXML6) are plain executables with no
        # RPATH: they must see the conan Qt/KF libs, and /system/lib64 carries
        # the compatible libc++_shared.so (prepended LAST -> ends up FIRST),
        # because the SDK's aarch64-linux-ohos/libc++.so is a linker script
        # the runtime loader cannot use (keditbookmarks/kconfig precedent).
        env = self._runtime_env()
        env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        return env

    def build(self):
        cmake = CMake(self)
        with self._build_env().vars(self).apply():
            cmake.configure()
            cmake.build()
        if self.settings.os == "OHOS":
            self._run_upstream_tests()

    def _run_upstream_tests(self):
        # Upstream registers two ctest targets (tests/CMakeLists.txt): the
        # ``lauri_de`` XML validity check via checkXML6, and ``split2po``
        # round trip.  Both exercise the real converter pipeline.
        env = self._runtime_env()
        env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        env.define("CTEST_OUTPUT_ON_FAILURE", "1")
        tmp = os.path.join(self.build_folder, "test-tmp")
        os.makedirs(tmp, exist_ok=True)
        env.define("TMPDIR", tmp)
        with env.vars(self).apply():
            self.run('ctest --test-dir "%s" --output-on-failure'
                     % self.build_folder)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        # Runtime needs the Qt6/KF6/gettext shared libraries.
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                self.runenv_info.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
