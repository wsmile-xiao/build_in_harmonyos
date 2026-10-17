#!/usr/bin/env python3
"""Conan recipe for czmq 4.2.0 on HarmonyOS PC (aarch64).

czmq is the high-level C binding for ZeroMQ (libzmq). This recipe builds the
library with the upstream CMake build system, linking against the published
``libzmq/4.3.5`` package, and runs the upstream ctest suite during the build
phase.

Adaptation notes (details in notes.md):

* Two portability patches are applied: the CMake 4.x minimum-version fix and
  a ``TMPDIR`` fix for ``zfile_tmp()`` (OHOS mounts ``/tmp`` read-only).
* libzmq discovery: ``find_package(libzmq REQUIRED)`` resolves czmq's own
  bundled ``Findlibzmq.cmake``, which asks pkg-config for ``libzmq``. The
  ``libzmq/4.3.5`` package exports ``pkg_config_name = libzmq``, so
  ``PkgConfigDeps`` is generated alongside ``CMakeDeps``.
* Draft classes are disabled (upstream recommends distributions do NOT build
  them); this reduces the registered ctest suite from 40 to 30 classes.
* The published libzmq is built with CURVE disabled (no libsodium), so czmq's
  certificate/auth helpers degrade gracefully through ``zsys_has_curve()``.
  ``zmakecert`` is therefore not shipped: it only generates CURVE keys.
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rmdir,
)
from conan.tools.gnu import PkgConfigDeps


class CzmqConan(ConanFile):
    name = "czmq"
    version = "4.2.0"
    description = "High-level C binding for ZeroMQ (CZMQ)"
    license = "MPL-2.0"
    homepage = "https://czmq.zeromq.org"
    url = "https://github.com/zeromq/czmq"
    topics = ("zmq", "zeromq", "messaging", "binding")

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"czmq 4.2.0 recipe supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def _resolve_compiler(self, key, fallback):
        """Resolve a compiler that exists on this host (R33).

        Returns the profile-configured executable when the file is really
        there, otherwise the same tool as found on PATH.
        """
        comp_execs = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        candidate = comp_execs.get(key)
        if candidate:
            if os.path.isabs(candidate):
                if os.path.exists(candidate):
                    return candidate
            elif shutil.which(candidate):
                return candidate
        return shutil.which(fallback) or fallback

    def requirements(self):
        # Official package name of the ZeroMQ core library. czmq's CMake
        # probes pkg-config for `libzmq`, which is exactly the pkg_config_name
        # this package exports.
        #
        # transitive_headers/transitive_libs must be True: czmq's public
        # headers (czmq.h -> czmq_prelude.h) do `#include <zmq.h>`, and the
        # linker needs -lzmq, so consumers of czmq need libzmq's includedirs
        # and libs propagated through this package. Without the traits
        # CMakeDeps generates empty include/lib metadata for the transitive
        # dependency and consumers fail with "'zmq.h' file not found"
        # (the merged zmqpp recipe declares its zeromq requirement the same
        # way).
        self.requires("libzmq/4.3.5", transitive_headers=True, transitive_libs=True)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # R33: compiler comes from the Conan conf, never from bare shell vars.
        # The OHOS profile pins tools.build:compiler_executables to the device
        # SDK path (/data/service/hnp/bin/clang). That path is absent on some
        # workers/preflight hosts, and CMake then aborts in project() with
        # "is not a full path to an existing compiler tool", so fall back to
        # the same binary resolved from PATH.
        self.conf.update(
            "tools.build:compiler_executables",
            {
                "c": self._resolve_compiler("c", "clang"),
                "cpp": self._resolve_compiler("cpp", "clang++"),
            },
        )

        # CMakeDeps: czmq's own find_package(libzmq) uses the bundled
        # Findlibzmq.cmake (module mode), so the config files are not what
        # resolves libzmq here; they are kept for completeness.
        CMakeDeps(self).generate()
        # PkgConfigDeps: provides libzmq.pc, which Findlibzmq.cmake consumes
        # via pkg_check_modules() to locate zmq.h / libzmq.so.
        PkgConfigDeps(self).generate()

        tc = CMakeToolchain(self)
        tc.variables["CZMQ_BUILD_SHARED"] = "ON" if self.options.shared else "OFF"
        tc.variables["CZMQ_BUILD_STATIC"] = "OFF" if self.options.shared else "ON"
        # Upstream: "Distributions are recommended NOT to build with them".
        # Draft classes also pull optional libcurl/microhttpd features.
        tc.variables["ENABLE_DRAFTS"] = "OFF"
        # Keep the package hermetic. czmq's zproject CMake probes a set of
        # optional system libraries (uuid/systemd/lz4/libcurl/libmicrohttpd)
        # and links whatever it happens to find on the build host into
        # libczmq -- the first local run picked up a stray libcurl.so.4 from
        # ~/usr/local, which would have made the package depend on the host.
        # CMAKE_DISABLE_FIND_PACKAGE_<name> is CMake's official way to force
        # those probes to fail, so the package depends on libzmq only.
        for optional_dep in ("uuid", "systemd", "lz4", "libcurl", "libmicrohttpd"):
            tc.variables["CMAKE_DISABLE_FIND_PACKAGE_%s" % optional_dep] = "ON"
        # CMake has no Platform/HarmonyOS module, so it does not know the
        # soname flag for this system and would produce libczmq.so without a
        # DT_SONAME (CI L5a gate, and downstream linkers cannot address it by
        # soname). Provide the Linux flag explicitly; czmq's own
        # VERSION/SOVERSION then produce libczmq.so.4.2.0 + soname
        # libczmq.so.4.
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_C_FLAG"] = "-Wl,-soname,"
        tc.variables["CMAKE_SHARED_LIBRARY_SONAME_CXX_FLAG"] = "-Wl,-soname,"
        tc.variables["CLASSTEST_TIMEOUT"] = "120"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

        if cross_building(self):
            self.output.info(
                "cross-building: skip upstream ctest suite because target binaries "
                "are not runnable on the build host"
            )
            return

        self.output.info("Running czmq upstream ctest suite")
        # The freshly built libczmq.so lives in the build folder and upstream's
        # CMake does not record a build-tree RPATH for it, so the musl loader
        # needs the build folder on LD_LIBRARY_PATH for every selftest binary.
        # libzmq is linked by soname (patch 0005), so its lib folder is needed
        # at run time as well.
        env = Environment()
        env.prepend_path("LD_LIBRARY_PATH", self.build_folder)
        libzmq = self.dependencies["libzmq"]
        for libdir in libzmq.cpp_info.libdirs:
            env.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(libzmq.package_folder, libdir)
            )
        with env.vars(self).apply():
            self.run(
                'ctest --output-on-failure -E "%s"' % self._ohos_excluded_tests(),
                cwd=self.build_folder,
                env="conanbuild",
            )

    @staticmethod
    def _ohos_excluded_tests():
        """OHOS-platform exclusions, item by item (all environment limits).

        Empty by default; each entry added here must come with a concrete,
        reproducible technical reason in notes.md / the PR body.
        """
        return ""

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        # The only installed helper binary is zmakecert, an interactive CURVE
        # certificate generator. libzmq/4.3.5 is published with CURVE disabled,
        # so the tool cannot produce usable certificates; the package stays a
        # pure library (and needs no commands.json, R38).
        rmdir(self, os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "czmq")
        self.cpp_info.set_property("cmake_target_name", "czmq::czmq")
        self.cpp_info.set_property("pkg_config_name", "libczmq")
        self.cpp_info.libs = ["czmq"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
