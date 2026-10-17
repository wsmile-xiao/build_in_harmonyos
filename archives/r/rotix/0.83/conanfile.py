#!/usr/bin/env python3
"""Conan recipe for rotix 0.83 — generate rotational (ROT-x, e.g. ROT13) obfuscations.

Upstream: https://github.com/shemminga/rotix (GPL-2.0-or-later)
Build system: hand-written POSIX shell ./configure + GNU Makefile (not autotools).

OHOS portability notes
----------------------
1. The hand-written configure probes only ``gcc``/``cc`` and always writes
   ``CC=gcc`` into Makefile.settings. The OHOS sysroot ships clang only, so
   build() exposes a ``gcc`` -> target clang shim on PATH for the probe and
   pins ``CC`` on the make command line. No upstream source is modified for this.
2. Upstream ``help.c`` includes ``<libintl.h>`` unconditionally, while ``rotix.c``
   guards the identical include with ``#ifdef I18N``. OHOS musl ships an
   empty-shell libintl.h (macros only, no ``gettext`` prototype), so the
   unguarded include turns ``gettext()`` into an implicit int and help.c fails
   with 14 ``-Wint-conversion`` errors. patches/0001 mirrors the rotix.c guard.
   The recipe builds with ``--i18n=0`` (no real libintl is available, NLS off).
3. Only the ``rotix`` make target is built; the default ``all`` target also
   builds ``po/NL.mo`` which requires ``msgfmt`` (gettext).
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class RotixConan(ConanFile):
    name = "rotix"
    version = "0.83"
    description = (
        "Generate rotational obfuscations (ROT-x, e.g. ROT13) from files, "
        "stdin or command-line text"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/shemminga/rotix"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # rotix depends only on the C library; no third-party dependencies.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: take the compiler from the Conan conf, never from bare shell vars.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"

        prefix = self.package_folder.replace("\\", "/")

        # OHOS has no usable /bin/sh for scripts (R5); run configure through bash.
        config_shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")

        # The hand-written configure only looks for `gcc` or `cc`; provide a
        # `gcc` shim pointing at the target compiler so detection succeeds and
        # configure does not abort with "Cannot find a C compiler". configure
        # only *tests for* the command (`type gcc`, no execution); make uses the
        # CC override below, so the shim is never run. Its shebang still points
        # at bash so it stays functional if it is ever executed on OHOS.
        shim_dir = os.path.join(self.build_folder, "build-bin")
        os.makedirs(shim_dir, exist_ok=True)
        shim = os.path.join(shim_dir, "gcc")
        with open(shim, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(f'#!{config_shell}\nexec "{cc}" "$@"\n')
        os.chmod(shim, 0o755)
        os.environ["PATH"] = shim_dir + os.pathsep + os.environ.get("PATH", "")

        # --i18n=0: NLS off (OHOS provides no gettext/libintl at runtime).
        # --strip=0: keep symbols; ELF stripping/signing is handled by CI.
        self.run(
            f'{config_shell} ./configure --prefix="{prefix}" --i18n=0 --strip=0',
            cwd=self.source_folder,
        )
        # STRIP=true neutralises the Makefile strip rule: upstream writes
        # `STRIP=0` when no strip utility is found, which the Makefile would then
        # try to execute as the command `0 rotix`.
        # Build only the `rotix` target so `po` (needs msgfmt) is not triggered.
        self.run(
            f'make CC="{cc}" STRIP=true -j1 rotix',
            cwd=self.source_folder,
        )

    def package(self):
        src = self.source_folder
        copy(self, "COPYING", src=src, dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "rotix", src=src, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "rotix.1", src=src, dst=os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "README", src=src, dst=os.path.join(self.package_folder, "share", "rotix", "doc"))
        # Upstream installs the binary with mode 0755; ensure the exec bit survives.
        os.chmod(os.path.join(self.package_folder, "bin", "rotix"), 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
