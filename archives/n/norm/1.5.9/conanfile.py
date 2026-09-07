#!/usr/bin/env python3
"""Conan recipe for norm 1.5.9 — NRL NACK-Oriented Reliable Multicast library.

norm is a C/C++ protocol library built with its bundled `waf` build tool
(BUILD.TXT / wscript).  Artifacts from the default `waf build`:
  * libnorm.so.1.5.9 (+ libnorm.so / libnorm.so.1 symlinks)
  * libnorm.a             (self-contained static archive, protokit merged)
  * libprotokit.so/.a     (bundled protolib — not part of the norm package)
  * include/normApi.h     (single public NORM API header)
  * lib/pkgconfig/norm.pc

HarmonyOS notes:
  * platform.system() returns 'harmonyos' on OHOS; both wscripts map it to
    'linux' (patch 0001/0002) so the unix/linux source set and defines are
    selected exactly like a native Linux build.
  * OHOS sysroot's linux/socket.h and musl sys/socket.h both define
    sockaddr_storage (E091) — resolved with -D__MUSL__ (the musl sys/socket.h
    wraps its definition in #ifndef __MUSL__, bird2/alfred precedent).
  * The official GitHub release asset `src-norm-1.5.9.tgz` is in fact a plain
    tar (no gzip); conan's unzip auto-detects (r:*) and extracts fine.
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, rm, rmdir
from conan.tools.layout import basic_layout


class NormConan(ConanFile):
    name = "norm"
    version = "1.5.9"
    description = "NRL NORM (NACK-Oriented Reliable Multicast) reliable multicast transport library"
    license = "BSD-2-Clause"  # NRL permissive notice in README/LICENSE (custom NRL text)
    homepage = "https://www.nrl.navy.mil/our-research/areas-of-expertise/information-innovation/"
    url = "https://github.com/USNavalResearchLaboratory/norm"
    topics = ("norm", "multicast", "reliable", "protocol", "rfc5740", "rfc3940")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"norm/1.5.9 supports Linux/OHOS only, got {self.settings.os}")
        if not self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def source(self):
        # Official NRL release asset.  Filename ends .tgz but content is a
        # plain tar; conan get() auto-detects (r:*) and extracts correctly.
        get(self, **self.conan_data["sources"])

    def generate(self):
        # Profile [buildenv] PATH (compiler toolchain dir etc.)
        VirtualBuildEnv(self).generate()

    def _build_env(self):
        """Expose the profile toolchain (CC/CXX/AR/RANLIB + OHOS defines)
        to the waf build scripts."""
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        cc = compilers.get("c") or "clang"
        cxx = compilers.get("cpp") or "clang++"
        env = Environment()
        env.define("CC", cc)
        env.define("CXX", cxx)

        bindir = os.path.dirname(cc) if os.path.sep in cc else ""
        ar = compilers.get("ar") or (os.path.join(bindir, "llvm-ar") if bindir else "llvm-ar")
        ranlib = compilers.get("ranlib") or (os.path.join(bindir, "llvm-ranlib") if bindir else "llvm-ranlib")
        env.define("AR", ar)
        env.define("RANLIB", ranlib)

        if self.settings.os == "OHOS":
            # E091: OHOS linux/socket.h vs sys/socket.h sockaddr_storage
            # redefinition — musl sys/socket.h gates it behind __MUSL__.
            env.append("CFLAGS", "-D__MUSL__")
            env.append("CXXFLAGS", "-D__MUSL__")
        return env

    def _waf(self, command, *args):
        joined = " ".join(args)
        # Use the interpreter running this recipe (avoids PATH assumptions).
        self.run(f'"{sys.executable}" waf {command} {joined}'.strip(),
                 cwd=self.source_folder, env=["conanbuild"])

    def build(self):
        apply_conandata_patches(self)
        with self._build_env().vars(self).apply():
            self._waf("configure", "--prefix=/", "--libdir=/lib")
            self._waf("build")
            # Upstream functional self-test: FEC (RS16) encode/decode round trip.
            # norm ships no `make check`; fecTest is the bundled offline test.
            self._waf("build", "--targets=fecTest")
            import os as _os
            fec = _os.path.join(self.source_folder, "build", "fecTest")
            self.run(f'"{fec}"', env=["conanbuild"])

    def package(self):
        with self._build_env().vars(self).apply():
            self._waf("install", f"--destdir={self.package_folder}")
        # norm's own libs embed the bundled protokit objects; drop the
        # separate libprotokit artifacts (upstream "protolib" is a distinct
        # library released on its own).
        for pattern in ("libprotokit*",):
            rm(self, pattern, os.path.join(self.package_folder, "lib"),
               recursive=False)
        if not self.options.shared:
            # static-only build: drop shared objects/symlinks
            for f in os.listdir(os.path.join(self.package_folder, "lib")):
                if f.startswith("libnorm.so"):
                    try:
                        os.unlink(os.path.join(self.package_folder, "lib", f))
                    except OSError:
                        pass
        else:
            rm(self, "libnorm.a", os.path.join(self.package_folder, "lib"),
               recursive=False)
        rmdir(self, os.path.join(self.package_folder, "share"))

    def package_info(self):
        self.cpp_info.libs = ["norm"]
        self.cpp_info.set_property("cmake_file_name", "norm")
        self.cpp_info.set_property("cmake_target_name", "norm::norm")
        self.cpp_info.set_property("pkg_config_name", "norm")
        if not self.options.shared:
            # static libnorm.a pulls in protokit (merged) + pthread etc.
            self.cpp_info.system_libs = ["pthread"]
            if self.settings.os == "OHOS":
                self.cpp_info.system_libs.append("m")
            else:
                self.cpp_info.system_libs.extend(["dl", "rt", "m"])
        else:
            # Shared lib is self-contained; runtime needs libc++ (system).
            pass
