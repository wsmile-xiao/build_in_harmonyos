#!/usr/bin/env python3
"""Conan recipe for sbc 2.1 — the Bluetooth low-complexity codec library.

libsbc is a self-contained C99 codec (subband codec used by A2DP): the
library plus three command-line tools (sbcenc / sbcdec / sbcinfo).
Autotools with a pre-generated configure and **no external dependencies**
— everything is in-tree.

Platform notes carried over from this archive's proven autotools pattern
(libcdaudio/ncpth lineage): explicit --build/--host triplets (the shipped
config.sub predates aarch64/musl), bash as SHELL/CONFIG_SHELL (toybox sh
lacks IFS word splitting), umask 077→022 rewrite in every configure
(hmdfs does not preserve permission bits), stdin from /dev/null (autoconf
exec-fd tricks fail on closed fd0), CC exported from the profile, and an
explicitly empty LD_LIBRARY_PATH (some CI workers carry an ambient LD
whose incompatible libxml2.so.16 breaks the SDK's lld on every link —
CI-021 build #48068, mechanism in libodfgen/libabw).
"""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout

OHOS_SHELL_CANDIDATES = ("/data/service/hnp/bin/bash", "/usr/bin/zsh", "bash")


class SbcConan(ConanFile):
    name = "sbc"
    version = "2.1"
    description = ("sbc - Bluetooth low-complexity, subband codec (SBC) "
                   "library: encoder, decoder and analysis tools")
    license = ("GPL-2.0-or-later", "LGPL-2.1-or-later")
    homepage = "https://www.kernel.org/pub/linux/bluetooth/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"sbc is adapted for Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        # url may arrive as a candidate list (the CI pre-download step
        # rewrites conandata's url into [mirror, official]) — conan's
        # get() handles both shapes natively.
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        import subprocess

        shell = self._resolve_shell()
        build = self.build_folder
        self._copy_tree(self.source_folder, build)
        self._relax_umask_in_configures()

        env = dict(os.environ)
        # Explicitly neutralize LD_LIBRARY_PATH (lld/libxml2 protection —
        # see class docstring and libodfgen/libabw for the mechanism).
        env["LD_LIBRARY_PATH"] = ""
        env["CC"] = self._cc()
        env["SHELL"] = shell
        env["CONFIG_SHELL"] = shell
        configure = os.path.join(build, "configure")
        if not os.path.isfile(configure):
            raise ConanException(f"configure script is missing: {configure}")
        cmd = (f"{shlex.quote(shell)} ./configure "
               "--build=aarch64-unknown-linux-musl "
               "--host=aarch64-unknown-linux-gnu --prefix=/ "
               # sbctester is an upstream self-test tool that hard-requires
               # libsndfile (absent on this platform); upstream ships the
               # --disable-tester switch, which skips both the tool and its
               # fatal sndfile pkg-config check.  The library and the
               # sbcenc/sbcdec/sbcinfo tools are unaffected.
               "--disable-tester "
               # Static-only delivery: OHOS ships its own system libsbc.so
               # (Bluetooth stack), so a shared libsbc would collide with
               # the system copy at runtime (loader picks the system one,
               # whose ABI lacks what consumers need).  LT_INIT disables
               # static by default but --enable-static overrides it.
               "--enable-static --disable-shared < /dev/null")
        completed = subprocess.run(cmd, shell=True, cwd=build, env=env)
        if completed.returncode != 0:
            self._dump_failure_diagnostics(build, env)
            raise ConanException(f"configure failed (rc={completed.returncode})")
        make_cmd = "make -j1 < /dev/null"
        completed = subprocess.run(make_cmd, shell=True, cwd=build, env=env)
        if completed.returncode != 0:
            self._dump_failure_diagnostics(build, env)
            raise ConanException("make failed")

    def package(self):
        # Stage with upstream's own `make install DESTDIR` — it knows the
        # real layout (include/sbc/sbc.h, lib/libsbc.a, bin/tools) — then
        # assemble the package from the staging tree.  Static-only
        # delivery (repo precedent): skip the .so so consumers link
        # statically.
        build = self.build_folder
        inst = os.path.join(build, "inst")
        shell = self._resolve_shell()
        env = dict(os.environ)
        env["LD_LIBRARY_PATH"] = ""  # lld/libxml2 shield (see build())
        env["CC"] = self._cc()
        env["SHELL"] = shell
        env["CONFIG_SHELL"] = shell
        import subprocess
        cmd = (f"make -j1 install "
               f"DESTDIR={shlex.quote(inst + os.sep)} < /dev/null")
        completed = subprocess.run(cmd, shell=True, cwd=build, env=env)
        if completed.returncode != 0:
            raise ConanException(f"make install failed (rc={completed.returncode})")
        copy(self, "*.h", src=os.path.join(inst, "include"),
             dst=os.path.join(self.package_folder, "include"),
             keep_path=True)
        # prefix=/ → automake stages under inst/lib and inst/bin
        copy(self, "*.a", src=os.path.join(inst, "lib"),
             dst=os.path.join(self.package_folder, "lib"),
             keep_path=False)
        copy(self, "sbcenc sbcdec sbcinfo",
             src=os.path.join(inst, "bin"),
             dst=os.path.join(self.package_folder, "bin"),
             keep_path=False)
        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        copy(self, "COPYING.LIB", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "SBC")
        self.cpp_info.set_property("cmake_target_name", "SBC::SBC")
        self.cpp_info.set_property("pkg_config_name", "sbc")
        self.cpp_info.libs = ["sbc"]

    # ── helpers ─────────────────────────────────────────────────────────

    def _cc(self):
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default=None)
        if compilers:
            if isinstance(compilers, str):
                import json
                try:
                    compilers = json.loads(compilers)
                except ValueError:
                    compilers = {}
            if compilers.get("c"):
                return compilers["c"]
        return "clang"

    def _resolve_shell(self):
        for candidate in OHOS_SHELL_CANDIDATES:
            if os.path.isfile(candidate):
                return candidate
        return "/bin/sh"

    def _copy_tree(self, src, dst):
        import shutil
        shutil.copytree(src, dst, dirs_exist_ok=True, symlinks=True)

    def _relax_umask_in_configures(self):
        for root, _, files in os.walk(self.build_folder):
            for name in files:
                if name != "configure":
                    continue
                path = os.path.join(root, name)
                with open(path, encoding="utf-8", errors="replace") as handle:
                    content = handle.read()
                if "umask 077" in content:
                    with open(path, "w", encoding="utf-8",
                              newline="\n") as handle:
                        handle.write(content.replace("umask 077", "umask 022"))

    def _dump_failure_diagnostics(self, directory, environment):
        self.output.info("---- ohos diagnostics: environment ----")
        for name in ("CC", "CXX", "CFLAGS", "CPPFLAGS", "LDFLAGS", "LIBS",
                     "TMPDIR", "LD_LIBRARY_PATH", "PATH", "SHELL"):
            if name in environment:
                self.output.info(f"{name}={environment[name]}")
        config_log = os.path.join(directory, "config.log")
        if os.path.isfile(config_log):
            with open(config_log, errors="replace") as handle:
                lines = handle.readlines()
            for line in lines[-25:]:
                self.output.info(line.rstrip())
