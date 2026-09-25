#!/usr/bin/env python3
"""Conan recipe for libdsme 0.67.0.

libdsme is the DSME (Device State Management Entity) socket IPC library plus
the DSME / Thermal Manager D-Bus interface definition modules from the
Sailfish OS project.  The upstream tarball ships a hand-written Makefile (no
configure script) and produces three shared libraries:

  libdsme.so.0.3.0                    (SONAME libdsme.so.0)
  libdsme_dbus_if.so.0.3.0            (SONAME libdsme_dbus_if.so.0)
  libthermalmanager_dbus_if.so.0.3.0  (SONAME libthermalmanager_dbus_if.so.0)

OHOS adaptation notes:
  * The upstream Check based unit test suite (tests/ut_libdsme.c) is built by
    the Makefile but never executed by it; build() runs the built binary and
    validates the XML result (2/2 Check cases) for real.
  * Check 0.15.2 probes TEMP before TMPDIR/P_tmpdir and musl defines
    P_tmpdir as the read-only /tmp, so TEMP/TMP/TMPDIR are redirected to the
    Conan build folder before running the suite.
  * File system AF_UNIX sockets cannot be created on OHOS (HMDFS returns
    EPERM for bind() and /tmp is read-only); protocol.c therefore accepts
    abstract socket names with the '@' prefix and the upstream test daemon
    binds "@ut_libdsme".
  * The upstream install rules use GNU install(1), which does not exist on
    OHOS (toybox); package() lays out lib/include/pkgconfig explicitly.
"""

import os
import xml.etree.ElementTree as ElementTree

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


UPSTREAM_TESTS = 2
SHARED_LIBRARIES = (
    ("libdsme.so.0.3.0", "libdsme.so.0"),
    ("libdsme_dbus_if.so.0.3.0", "libdsme_dbus_if.so.0"),
    ("libthermalmanager_dbus_if.so.0.3.0", "libthermalmanager_dbus_if.so.0"),
)
PKG_CONFIG_FILES = ("dsme.pc", "dsme_dbus_if.pc", "thermalmanager_dbus_if.pc")


class LibdsmeConan(ConanFile):
    name = "libdsme"
    version = "0.67.0"
    description = (
        "DSME (Device State Management Entity) socket IPC libraries: the "
        "dsmesock client protocol plus the DSME and Thermal Manager D-Bus "
        "interface definition modules"
    )
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/sailfishos/libdsme"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "shared-library"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libdsme supports POSIX-like targets (Linux/OHOS), "
                f"not {self.settings.os}"
            )

    def requirements(self):
        # libdsme.so.0 keeps its client connections in a GLib GSList.
        self.requires("glib/2.84.0.1", transitive_libs=True)

    def build_requirements(self):
        # Only the upstream Check based unit test suite needs this package;
        # the installed libraries do not expose it.
        self.test_requires("check/0.15.2")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        VirtualBuildEnv(self).generate()

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _dependency(self, name):
        for dependencies in (
            self.dependencies.test,
            self.dependencies.host,
            self.dependencies.build,
        ):
            try:
                return dependencies[name]
            except KeyError:
                continue
        return None

    def _make_environment(self, for_tests=False):
        environment = Environment()
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        # R33: the Makefile drives the compiler through $(CC); define it from
        # the Conan profile instead of assuming a pre-populated shell.
        environment.define("CC", compilers.get("c", "clang"))
        # The Makefile calls pkg-config for glib-2.0 (and check); the Conan
        # generated metadata for those packages lives in the generators dir.
        environment.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        if str(self.settings.os) == "OHOS":
            # Check consults TEMP before P_tmpdir; musl defines P_tmpdir as
            # the read-only /tmp, so every spelling points at the build tree.
            temporary = os.path.join(self.build_folder, "tmp")
            os.makedirs(temporary, exist_ok=True)
            environment.define("TEMP", temporary)
            environment.define("TMP", temporary)
            environment.define("TMPDIR", temporary)
        if for_tests:
            environment.prepend_path("LD_LIBRARY_PATH", self.build_folder)
            for name in ("glib", "check"):
                dependency = self._dependency(name)
                if dependency is None:
                    continue
                for libdir in dependency.cpp_info.libdirs:
                    environment.prepend_path("LD_LIBRARY_PATH", libdir)
        return environment

    # ------------------------------------------------------------------
    # build lifecycle
    # ------------------------------------------------------------------

    def build(self):
        apply_conandata_patches(self)

        with VirtualBuildEnv(self).vars().apply(), \
                self._make_environment().vars(self).apply():
            self.run("make -j1", cwd=self.source_folder)

        # The Makefile only creates the versioned libraries; the SONAME
        # symlinks resolved by the dynamic loader are install rules upstream.
        for filename, soname in SHARED_LIBRARIES:
            link = os.path.join(self.build_folder, soname)
            if os.path.lexists(link):
                os.unlink(link)
            os.symlink(os.path.join(self.source_folder, filename), link)

        self._run_upstream_tests()

    def _run_upstream_tests(self):
        test_binary = os.path.join(self.source_folder, "tests", "ut_libdsme")
        result_xml = os.path.join(self.build_folder, "ut_libdsme.xml")
        with VirtualBuildEnv(self).vars().apply(), \
                self._make_environment(for_tests=True).vars(self).apply():
            self.run(f'"{test_binary}" -o "{result_xml}"', cwd=self.source_folder)

        if not os.path.isfile(result_xml):
            raise ConanException("upstream ut_libdsme produced no result file")
        root = ElementTree.parse(result_xml).getroot()
        # Check writes the result XML with a default namespace, so match on
        # the local tag name instead of the literal "test".
        outcomes = [
            element.get("result")
            for element in root.iter()
            if element.tag.rsplit("}", 1)[-1] == "test"
        ]
        if len(outcomes) != UPSTREAM_TESTS or any(o != "success" for o in outcomes):
            raise ConanException(
                f"upstream ut_libdsme: expected {UPSTREAM_TESTS} successful "
                f"checks, got {outcomes}"
            )
        self.output.info(
            f"upstream ut_libdsme: {len(outcomes)}/{UPSTREAM_TESTS} Check cases passed"
        )

    def package(self):
        # The upstream install rules depend on GNU install(1), which is not
        # available on OHOS (toybox); install the artifacts explicitly.
        libdir = os.path.join(self.package_folder, "lib")
        includedir = os.path.join(self.package_folder, "include", "dsme")
        pkgconfigdir = os.path.join(libdir, "pkgconfig")

        for filename, soname in SHARED_LIBRARIES:
            copy(self, filename, src=self.source_folder, dst=libdir)
            base = soname.rsplit(".so", 1)[0]
            os.symlink(filename, os.path.join(libdir, soname))
            os.symlink(soname, os.path.join(libdir, base + ".so"))

        copy(self, "*.h", src=os.path.join(self.source_folder, "include", "dsme"),
             dst=includedir)
        copy(self, "dsme_dbus_if.h", src=os.path.join(self.source_folder, "modules"),
             dst=includedir)
        copy(self, "thermalmanager_dbus_if.h",
             src=os.path.join(self.source_folder, "modules"), dst=includedir)

        # Copy the three upstream pkg-config files explicitly: with
        # basic_layout the Conan build tree lives inside the source folder,
        # so a "*.pc" glob would also match the generated dependency
        # metadata under the build directory.
        for pc_file in PKG_CONFIG_FILES:
            copy(self, pc_file, src=self.source_folder, dst=pkgconfigdir)
            # Make the shipped pkg-config metadata relocatable so it keeps
            # working from the Conan cache and from deployed prefixes.
            replace_in_file(
                self,
                os.path.join(pkgconfigdir, pc_file),
                "prefix=/usr",
                "prefix=${pcfiledir}/../..",
            )

        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libdsme")
        self.cpp_info.set_property("pkg_config_name", "libdsme")

        dsme = self.cpp_info.components["dsme"]
        dsme.libs = ["dsme"]
        dsme.requires = ["glib::glib-2.0"]
        dsme.set_property("cmake_target_name", "libdsme::dsme")
        dsme.set_property("pkg_config_name", "dsme")

        dbus_if = self.cpp_info.components["dsme_dbus_if"]
        dbus_if.libs = ["dsme_dbus_if"]
        dbus_if.set_property("cmake_target_name", "libdsme::dsme_dbus_if")
        dbus_if.set_property("pkg_config_name", "dsme_dbus_if")

        thermal = self.cpp_info.components["thermalmanager_dbus_if"]
        thermal.libs = ["thermalmanager_dbus_if"]
        thermal.set_property("cmake_target_name", "libdsme::thermalmanager_dbus_if")
        thermal.set_property("pkg_config_name", "thermalmanager_dbus_if")
