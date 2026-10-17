#!/usr/bin/env python3
"""Conan recipe for mtbl 1.7.1 — Farsight Security immutable sorted key-value
store (SSTable library and CLI tools).

Build system: Autotools.
Upstream test suite: `make check` runs 15 tests natively on the OHOS/aarch64
host (this machine), exercised during build().
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class MtblConan(ConanFile):
    name = "mtbl"
    version = "1.7.1"
    description = "Immutable sorted key-value store (SSTable) library and tools"
    license = "Apache-2.0"
    homepage = "https://github.com/farsightsec/mtbl"
    url = "https://github.com/farsightsec/mtbl"
    topics = ("key-value", "sst", "sorted-table", "database", "immutable")
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("mtbl is supported only on Linux/OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def requirements(self):
        # mtbl uses a mandatory compression framework: LZ4, SNAPPY, ZSTD and
        # zlib are all hard requirements of libmtbl (see configure.ac).
        self.requires("lz4/1.10.0")
        self.requires("snappy/1.2.2")
        self.requires("zstd/1.5.7.1")
        self.requires("zlib/1.3.2")
        # pkg-config comes from the system (repo convention: no pkgconf tool_requires)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = PkgConfigDeps(self)
        deps.generate()

        # mtbl's configure looks up `liblz4` via PKG_CHECK_MODULES, but the
        # Conan lz4 package generates `lz4.pc` (Name: lz4). Write a thin
        # alias .pc that Requires: lz4 so the upstream check resolves
        # without patching configure.ac.
        alias_pc = os.path.join(self.generators_folder, "liblz4.pc")
        if not os.path.isfile(alias_pc):
            with open(alias_pc, "w", encoding="utf-8") as f:
                f.write(
                    "Name: liblz4\n"
                    "Description: alias to the Conan lz4 package\n"
                    "Version: 1.10.0\n"
                    "Requires: lz4\n"
                )

        tc = AutotoolsToolchain(self)
        # Library package: publish static only (repo convention: static+fPIC).
        tc.configure_args.append("--disable-shared")
        # snappy 1.2.2 static lib is C++ code; the pure-C link checks in
        # mtbl's configure (AC_CHECK_LIB snappy) need the C++ runtime linked.
        tc.extra_ldflags.append("-lc++")
        # mtbl's configure finds snappy/zlib via plain AC_CHECK_HEADER /
        # AC_CHECK_LIB (not pkg-config), so their include and lib dirs must
        # be on the compiler search path explicitly.
        for dep_name in ("snappy", "zlib", "lz4", "zstd"):
            dep = self.dependencies[dep_name]
            cppinfo = dep.cpp_info.aggregated_components()
            for inc in cppinfo.includedirs:
                tc.extra_cflags.append(f"-I{inc}")
            for libd in cppinfo.libdirs:
                tc.extra_ldflags.append(f"-L{libd}")
        tc.generate()

        # make check: test programs link the shared zstd/zlib Conan packages;
        # they must find those libs at runtime when executed in place.
        # A recipe's own buildenv_info is NOT collected into conanbuildenv-*.sh,
        # so build() passes the library path explicitly to the check run.
        lib_dirs = []
        for dep in self.dependencies.host.values():
            cppinfo = dep.cpp_info.aggregated_components()
            lib_dirs.extend(cppinfo.libdirs)
        # dedupe, keep order
        seen = set()
        self._check_lib_path = ":".join(
            d for d in lib_dirs if not (d in seen or seen.add(d))
        )

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # L1c: run the upstream test suite (15 tests) natively on OHOS/aarch64.
        # The test programs link shared zstd/zlib from Conan, so the check run
        # needs LD_LIBRARY_PATH pointing at the dependency lib dirs (the
        # recipe's own build env would not carry it).
        if can_run(self):
            from conan.tools.env import Environment
            env = Environment()
            env.prepend_path("LD_LIBRARY_PATH", self._check_lib_path)
            with env.vars(self).apply():
                autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # libtool *.la files are not meaningful for Conan consumers
        for la in _glob_la(self.package_folder):
            os.remove(la)

    def package_info(self):
        self.cpp_info.libs = ["mtbl"]
        # mtbl installs a single flat header: include/mtbl.h — consumers use
        # `#include <mtbl.h>` with include/ on the path.
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.system_libs = ["m", "pthread"]
        # mtbl ships 4 CLI tools (mtbl_dump/info/verify/merge) in bin/, but the
        # library is the primary artifact: package_type is "library" and no
        # bindirs are declared (repo policy: library packages carry no
        # commands.json).
        self.cpp_info.set_property("pkg_config_name", "mtbl")


def _glob_la(package_folder):
    import glob
    return glob.glob(os.path.join(package_folder, "lib", "*.la"))
