#!/usr/bin/env python3
"""Conan recipe — pd-lua 0.12.23 (make + Makefile.pdlibbuilder).

pd-lua is a Pure Data (Pd) external loader that lets you write Pd
externals in Lua. It builds `pdlua.pd_linux` (a shared object loaded by
Pd) using the bundled Makefile.pdlibbuilder, linking the static liblua
provided by the `lua` package and compiling against Pd's public headers
(m_pd.h / s_stuff.h) provided by the `puredata` package.

OHOS / HarmonyOS PC notes (see notes.md):
- The project is a plain Makefile build (no configure). The tarball has an
  empty `lua/` dir, so the Makefile's `pkg-config --cflags lua` branch
  would be used; instead we pass luaflags/lualibs explicitly on the make
  command line so no pkg-config .pc file is needed for lua.
- The `lua/5.4.8.1` package on ohpcd exposes a PIC static liblua.a (a
  stale non-PIC binary also exists on the remote for an older recipe
  revision — conan resolves the newest package revision, which is PIC;
  verify with a shared-link smoke test if link errors about
  R_AARCH64_ADR_PREL_PG_HI21 reappear).
- `make -j1` only: parallel jobserver mkfifo is denied on HMDFS
  ("make: jobserver mkfifo: ... Operation not permitted").
- No upstream `check` target exists; `make check` fails with
  "No rule to make target 'check'" (documented in test report / MANIFEST).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class PdluaConan(ConanFile):
    name = "pd-lua"
    version = "0.12.23"
    description = "Pd-Lua — write Pure Data externals in Lua"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/agraef/pd-lua"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    # Compatibility placeholder (conan-center recipe convention suggests
    # libraries expose a `shared` option). The Pd external is always built
    # as a shared object (pdlua.pd_linux) that Pd dlopen's, so the build
    # never branches on this option and the package content is identical
    # for either value.
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: OHOS platform check must accept both Linux and OHOS.
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"pd-lua supports Linux/OHOS only, got {self.settings.os}"
            )

    def requirements(self):
        self.requires("lua/5.4.8.1")
        self.requires("puredata/0.54.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _build_flags(self):
        # R33: compilers/flags come from Conan conf/deps, never bare ${CC}.
        tools = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = tools.get("c", "clang")
        lua = self.dependencies["lua"]
        pd = self.dependencies["puredata"]
        lua_inc = os.path.join(lua.package_folder, "include")
        lua_lib = os.path.join(lua.package_folder, "lib")
        # puredata package ships m_pd.h/s_stuff.h under include/pd (its
        # recipe exposes no cpp_info include dirs, so use package_folder).
        pd_inc = os.path.join(pd.package_folder, "include", "pd")
        return cc, pd_inc, lua_inc, lua_lib

    def _make_args(self):
        # Shared by build() and package(); keeps the two make invocations
        # consistent if flags ever change.
        cc, pd_inc, lua_inc, lua_lib = self._build_flags()
        return (
            f'CC="{cc}" '
            f'PDINCLUDEDIR="{pd_inc}" '
            f'luaflags="-I{lua_inc}" '
            f'lualibs="-L{lua_lib} -llua -ldl -lm"'
        )

    def build(self):
        apply_conandata_patches(self)
        # -j1: parallel jobserver mkfifo is denied on HMDFS.
        self.run(f"make -j1 {self._make_args()}", env="conanbuild", cwd=self.source_folder)

    def package(self):
        # PDLIBDIR=/lib/pd/extra matches the puredata package layout so a
        # `pd -lib pdlua` consumer finds the external at
        # <prefix>/lib/pd/extra/pdlua/.
        self.run(
            f"make install DESTDIR={self.package_folder} "
            f"PDLIBDIR=/lib/pd/extra {self._make_args()}",
            env="conanbuild",
            cwd=self.source_folder,
        )

    def package_info(self):
        # pdlua is a Pd external (a shared object dlopen'ed by Pd), not a
        # linkable library for other C/C++ consumers. Downstream programs
        # use it via `pd -lib pdlua`.
        self.cpp_info.bindirs = []
        self.cpp_info.libs = []
