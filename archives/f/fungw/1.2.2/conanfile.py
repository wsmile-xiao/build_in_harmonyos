#!/usr/bin/env python3
"""Conan recipe for fungw 1.2.2 — language-agnostic function gateway (C89).

fungw is a tiny portable C89 library that manages dynamic function calls across
different programming languages. Upstream builds with **scconfig**
(./configure regenerates the Makefiles from *.in templates, then make / make install).

OHOS (aarch64) adaptation notes:
  * scconfig bootstraps its own configure generator with the default ``cc``;
    the OHOS SDK ships clang only, so CC is injected from
    ``tools.build:compiler_executables`` (R33: never from a bare shell env var).
  * ``--disable-perl``: scconfig auto-detects scripting languages and would link
    the perl binding against a libperl that does not exist on OHOS. The bundled
    bindings (c / fawk / cli) stay enabled — they need no external library.
  * scconfig's ``install_link_`` step builds the SONAME aliases
    (libfungw.so -> .so.1 -> .so.1.2.2) with **hard links** (``sccbox ln -f``).
    Neither hard links nor symlinks are supported on the HMDFS build volume
    (``ln`` -> EACCES, os.link -> EPERM), so package() materialises the aliases
    as plain copies.
  * ``libfungw/fungw.h`` includes <genht/htsp.h> but upstream never installs the
    bundled genht headers; they are shipped into include/genht so consumers can
    actually compile against the installed headers.
"""
import glob
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
)
from conan.tools.layout import basic_layout


class FungwConan(ConanFile):
    name = "fungw"
    version = "1.2.2"
    description = "Language-agnostic function gateway (C89) for cross-language dynamic function calls"
    license = "LGPL-2.1-or-later"
    homepage = "http://www.repo.hu/projects/fungw/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("fungw", "scripting", "binding", "gateway", "c89")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.get_safe("os") == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: the compiler comes from the Conan conf, never from a bare ${CC}.
        # scconfig bootstraps itself with the default `cc`, which does not exist
        # on OHOS, so a missing conf entry must fail loudly instead of silently
        # falling back to whatever `clang` happens to be on PATH.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c")
        if not cc:
            raise ConanInvalidConfiguration(
                "fungw needs tools.build:compiler_executables={'c': ...}: scconfig "
                "bootstraps its configure generator with $(CC) (default `cc`), which "
                "the OHOS SDK does not provide")
        cc_prefix = f'CC="{cc}"'

        # scconfig: --prefix is the only argument needed; --disable-perl drops
        # the perl binding (there is no libperl on OHOS)
        # `configure` is a /bin/sh wrapper (cd scconfig && make && ./configure "$@");
        # conan's source copy drops the exec bit on the HMDFS volume, so run it
        # through `sh` instead of relying on the +x mode
        self.run(f'{cc_prefix} sh ./configure --prefix="{self.package_folder}" --disable-perl',
                 cwd=self.source_folder)

        # src_3rd/genht builds its "genht_std.a" compatibility alias with `ln -s`.
        # Neither symlinks nor hard links work on the HMDFS build volume
        # (EACCES/EPERM), and the regression tests link against that alias, so
        # materialise it as a plain copy before the top-level make.
        genht_dir = os.path.join(self.source_folder, "src_3rd", "genht")
        self.run(f"{cc_prefix} make libgenht.a", cwd=genht_dir)
        libgenht = os.path.join(genht_dir, "libgenht.a")
        genht_std = os.path.join(genht_dir, "genht_std.a")
        if os.path.isfile(libgenht) and not os.path.exists(genht_std):
            shutil.copy2(libgenht, genht_std)

        # genht (src_3rd) is a separate static archive upstream: the regression
        # tests link ../src_3rd/genht/genht_std.a explicitly, but the shared
        # libfungw*.so link rules never mention it, so the .so files keep
        # undefined symbols (strhash/htsp_init/...) and any consumer link dies
        # with ld.lld "--no-allow-shlib-undefined". Link the genht objects into
        # the shared libs so the packaged .so files are self-contained.
        genht_objs = " ".join(f'"{o}"' for o in sorted(glob.glob(os.path.join(genht_dir, "*.o"))))
        shared_ldflags = f"-rdynamic -fPIC {genht_objs}"
        self.run(f'{cc_prefix} make -C libfungw LDFLAGS=\'{shared_ldflags}\'',
                 cwd=self.source_folder)
        self.run(f'{cc_prefix} make -C libfungwbind LDFLAGS=\'{shared_ldflags}\'',
                 cwd=self.source_folder)

        self.run(f"{cc_prefix} make -j1", cwd=self.source_folder)

        # R51: run the upstream regression suite (5 executables) right here
        regression = os.path.join(self.source_folder, "regression")
        for exe in ("test", "test_c", "test_custom"):
            # these read a command line per line from stdin; /dev/null = EOF
            self.run(f"./{exe} < /dev/null", cwd=regression)
        # multicall has a golden reference file upstream
        self.run("./multicall | diff -u multicall.ref -", cwd=regression)
        # test_script drives the bundled fawk engine through a real script
        self.run("SCRIPT=../doc/example/00_hello/hello.fawk ./test_script",
                 cwd=regression)

        # PREFIX already points at package_folder, so no DESTDIR staging here
        self.run(f"{cc_prefix} make -C libfungw install", cwd=self.source_folder)
        self.run(f"{cc_prefix} make -C libfungwbind install", cwd=self.source_folder)

    def package(self):
        libdir = os.path.join(self.package_folder, "lib")
        incdir = os.path.join(self.package_folder, "include")

        if self.options.shared:
            rm(self, "*.a", libdir)
            self._materialise_soname_aliases(libdir)
        else:
            rm(self, "*.so*", libdir)
            # upstream installs static libs only for the bindings
            copy(self, "libfungw.a",
                 os.path.join(self.source_folder, "libfungw"), libdir)
            copy(self, "libgenht.a",
                 os.path.join(self.source_folder, "src_3rd", "genht"), libdir)

        # fungw.h includes <genht/htsp.h>: ship the bundled genht headers
        copy(self, "*.h",
             os.path.join(self.source_folder, "src_3rd", "genht"),
             os.path.join(incdir, "genht"))

        # LGPL-2.1-or-later: ship the upstream license text
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "fungw")
        self.cpp_info.set_property("cmake_target_name", "fungw::fungw")
        # static builds need the bundled genht archive (libfungw.a references it)
        self.cpp_info.libs = ["fungw", "fungw_c", "fungw_fawk", "fungw_cli"]
        if not self.options.shared:
            self.cpp_info.libs.append("genht")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        # puplug plugin dir (compiled in as <prefix>/lib/puplug) ships the
        # engine descriptors fungw scans at runtime — only the shared build
        # produces loadable plugins, so do not advertise it for static builds
        if self.options.shared and os.path.isdir(os.path.join(self.package_folder, "lib", "puplug")):
            self.cpp_info.resdirs = ["lib/puplug"]

    # ── helpers ──────────────────────────────────────────────────────────
    @staticmethod
    def _materialise_soname_aliases(libdir):
        """libfoo.so.X.Y.Z -> libfoo.so.X.Y / libfoo.so.X / libfoo.so

        scconfig's install_link_ does this with hard links (sccbox ln -f);
        HMDFS supports neither hard links nor symlinks, so copy instead. The
        puplug plugin alias lib/puplug/<name>.so is materialised the same way,
        but only for libs that actually ship a puplug descriptor (<name>.pup) —
        the core libfungw is not a plugin.
        """
        if not os.path.isdir(libdir):
            return
        puplug = os.path.join(libdir, "puplug")
        for name in sorted(os.listdir(libdir)):
            m = re.match(r"^(lib.+)\.so\.(\d+)\.(\d+)\.(\d+)$", name)
            if not m:
                continue
            base, major, minor, _patch = m.groups()
            src = os.path.join(libdir, name)
            for alias in (f"{base}.so.{major}.{minor}",
                          f"{base}.so.{major}",
                          f"{base}.so"):
                dst = os.path.join(libdir, alias)
                if not os.path.exists(dst):
                    shutil.copy2(src, dst)
            plugin = base[3:]  # strip the leading "lib"
            if os.path.isfile(os.path.join(puplug, f"{plugin}.pup")):
                dst = os.path.join(puplug, f"{plugin}.so")
                if not os.path.exists(dst):
                    shutil.copy2(src, dst)
