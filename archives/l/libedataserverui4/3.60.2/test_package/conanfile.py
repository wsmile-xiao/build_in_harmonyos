#!/usr/bin/env python3
"""Test package for libedataserverui4 3.60.2.

Builds a small C program against the *public* libedataserverui4 API and runs
it on the target (HarmonyOS PC aarch64), so the test really exercises the
shared library: type registration of ECredentialsPrompter and instantiation
of the ECellRendererColor GObject.

The dependency metadata fixes of ../conanfile.py are repeated here on the
consumer side, because PkgConfigDeps runs for the test package as well and
the very same upstream/dependency quirks apply.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.gnu import PkgConfigDeps


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        self._fix_dependency_metadata()
        PkgConfigDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        executable = os.path.join(self.cpp.build.bindirs[0],
                                  "test_libedataserverui4")
        with self._run_environment().vars(self).apply():
            self.run(executable)

    def _run_environment(self):
        """LD_LIBRARY_PATH with every (transitive) dependency libdir.

        The test links libedataserverui4-1.0.so and, through the `Requires:`
        entries of its .pc file, also the shared libraries of the EDS
        dependency graph (nss, nspr, gtk4, glib, ...).  All of them live in
        their conan package folders, so the loader needs an explicit search
        path.
        """
        environment = Environment()
        added = set()
        for dependency in self.dependencies.host.values():
            if not dependency.package_folder:
                continue
            for libdir in dependency.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dependency.package_folder, libdir)
                if libdir in added or not os.path.isdir(libdir):
                    continue
                added.add(libdir)
                environment.prepend_path("LD_LIBRARY_PATH", libdir)
        # The tested package comes first: it bundles the SONAME-fixed libical
        # objects that libecal-2.0.so needs at run time.
        for dependency in self.dependencies.host.values():
            if dependency.ref.name != "libedataserverui4":
                continue
            for libdir in reversed(list(dependency.cpp_info.libdirs)):
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dependency.package_folder, libdir)
                if os.path.isdir(libdir):
                    environment.prepend_path("LD_LIBRARY_PATH", libdir)
        return environment

    def _fix_dependency_metadata(self):
        # 1) libical3 is built with ICAL_GLIB=ON but exports its pkg-config
        #    module as "libical3"; upstream CMake probes "libical-glib" and
        #    its `cpp_info.requires` names glib components that do not exist
        #    in the ohpc glib recipe (PkgConfigDeps would abort).  Its shared
        #    objects carry the relative SONAME "./libical-glib.so", which the
        #    OHOS loader resolves against the working directory, so they can
        #    never be linked or loaded by a consumer (see below).
        libical3 = self.dependencies["libical3"]
        libical3.cpp_info.set_property("pkg_config_name", "libical-glib")
        libical3.cpp_info.requires = [
            "glib::glib-2.0",
            "glib::gobject-2.0",
            "libxml2::libxml2",
        ]
        #    The SONAME-fixed libical objects live in the *tested package's*
        #    own lib/ directory and libecal-2.0.so already carries the libical
        #    glue, so the dependency itself must be neither linked nor loaded.
        #    (Linking its static archives would register the libical GObject
        #    types a second time: "cannot register existing type 'ICalValue'".)
        libical3.cpp_info.libs = []
        libical3.cpp_info.sharedlinkflags = []
        libical3.cpp_info.libdirs = []
        # 2) icu only exports "icu.pc" (upstream probes icu-i18n/icu-uc) and it
        #    is a static C++ build, so the C++ runtime has to be linked.
        icu = self.dependencies["icu"]
        icu.cpp_info.set_property("pkg_config_aliases", ["icu-i18n", "icu-uc"])
        if "c++" not in icu.cpp_info.libs:
            icu.cpp_info.libs.append("c++")
        # 3) glib2 is a static GLib build whose pkg_config_name collides with
        #    the shared glib's glib-2.0.pc; the static archives must not leak
        #    into the link (two GObject copies abort the process).
        glib2 = self.dependencies["glib2"]
        glib2.cpp_info.set_property("pkg_config_name", "glib2-static")
        glib2.cpp_info.libs = []
        glib2.cpp_info.libdirs = []
        glib2.cpp_info.includedirs = []
        # 4) nss ships both static coreconf archives and the shared
        #    libnss3.so/...; only the shared names export the NSS API.
        nss = self.dependencies["nss"]
        nss.cpp_info.libs = ["nss3", "ssl3", "smime3", "nssutil3", "softokn3",
                             "freebl3", "nssckbi", "nssdbm3", "sqlite3"]
        # 5) glib's proxy-libintl provides the g_libintl_* gettext wrappers.
        glib = self.dependencies["glib"]
        for component in glib.cpp_info.components.values():
            if "intl" not in component.libs:
                component.libs.append("intl")
