#!/usr/bin/env python3
"""Conan recipe for X.Org lndir 1.0.5."""

import os
import shlex
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    save,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LndirConan(ConanFile):
    name = "lndir"
    version = "1.0.5"
    description = "X.Org lndir: create a shadow directory of symbolic links to another directory tree"
    license = "MIT-open-group"
    homepage = "https://gitlab.freedesktop.org/xorg/util/lndir"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # xorgproto provides the `xproto` pkg-config module and the X11/Xos.h,
        # X11/Xfuncproto.h headers that lndir.c includes. XPROTO_LIBS is empty
        # (header-only); the dep is only for compile-time headers.
        self.requires("xorgproto/2025.1", transitive_headers=True)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"lndir supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        AutotoolsToolchain(self).generate()

    def build(self):
        apply_conandata_patches(self)
        environment = self._build_environment()
        with environment.vars(self).apply():
            if str(self.settings.os) == "OHOS":
                self._patch_config_sub()
                self._generate_ohos_configure()
                # Upstream ships a pre-generated configure; run the OHOS variant
                # (it calls our config.guess-compiler instead of the broken
                # upstream config.guess). make check is the automake no-op
                # (upstream declares no TESTS); run it for faithfulness.
                self._configure_ohos()
                self._run_ohos("make -j1")
                self._run_ohos("make -j1 check")
            else:
                autotools = Autotools(self)
                autotools.configure()
                autotools.make(args=["-j1"])
                autotools.make(target="check", args=["-j1"])

    def package(self):
        environment = self._build_environment()
        with environment.vars(self).apply():
            if str(self.settings.os) == "OHOS":
                destination = shlex.quote(self.package_folder)
                self._run_ohos(f"make -j1 install DESTDIR={destination}")
            else:
                Autotools(self).install(args=["-j1"])
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        # Application package: single `lndir` executable in bin/.
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "lndir")
        self.cpp_info.set_property("pkg_config_name", "lndir")

    # ── OHOS helpers ──────────────────────────────────────────────────
    # libXext 1.3.7 proved the working pattern for X.Org autotools on OHOS:
    # the published config.guess cannot recognize OHOS (uname looks like
    # Linux), so generate a config.guess that returns the compiler's own
    # -dumpmachine tuple (aarch64-unknown-linux-ohos), and a config.sub that
    # accepts the ohos OS. No worker tool paths are hardcoded: the compiler
    # and shell come from the Conan profile / PATH, not fixed /data paths.

    def _build_environment(self):
        temporary = Path(self.build_folder, ".tmp")
        temporary.mkdir(parents=True, exist_ok=True)
        environment = Environment()
        environment.define_path("TMPDIR", str(temporary))
        environment.define("TMPPREFIX", str(temporary / "zsh-tmp-"))
        # lndir needs no shared libs (single executable, XPROTO_LIBS empty),
        # but keep LD_LIBRARY_PATH for any future lib deps as a safety net.
        for dependency in self.dependencies.host.values():
            for libdir in dependency.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dependency.package_folder, libdir)
                if os.path.isdir(libdir):
                    environment.prepend_path("LD_LIBRARY_PATH", libdir)
        if str(self.settings.os) == "OHOS":
            environment.define("MKDIR_P", "mkdir -p")
        return environment

    def _patch_config_sub(self):
        """Patch upstream config.sub so the OHOS OS suffix is accepted.

        OHOS uses the linux kernel with a musl-based libc; uname looks like
        ``HarmonyOS`` to config.guess (which then fails to compile a probe).
        We bypass config.guess entirely (see ``_generate_ohos_configure``) by
        feeding configure the compiler's own ``-dumpmachine`` tuple
        (``aarch64-unknown-linux-ohos``). config.sub must then accept that
        tuple, which requires patching two of its case blocks:
          1. the master OS-acceptance list (``| fiwix* | mlibc* )``) — add ``ohos*``
          2. the kernel-OS combination list (``| linux-musl* ... )``) — add ``linux-ohos*``
        """
        config_sub = Path(self.source_folder, "config.sub")
        if not config_sub.is_file():
            raise ConanException(f"config.sub missing in source tree: {config_sub}")
        sub = config_sub.read_text(encoding="utf-8", errors="replace")
        if "ohos*" not in sub:
            needle_master = "| fiwix* | mlibc* )"
            repl_master = "| fiwix* | mlibc* | ohos* )"
            if needle_master not in sub:
                raise ConanException("config.sub master OS list not found")
            sub = sub.replace(needle_master, repl_master, 1)
        if "linux-ohos*" not in sub:
            needle_kernel = "| linux-musl* | linux-relibc* | linux-uclibc* | linux-mlibc* )"
            repl_kernel = "| linux-musl* | linux-relibc* | linux-uclibc* | linux-mlibc* | linux-ohos* )"
            if needle_kernel not in sub:
                raise ConanException("config.sub kernel-OS list not found")
            sub = sub.replace(needle_kernel, repl_kernel, 1)
        save(self, config_sub, sub)

    def _generate_ohos_configure(self):
        """Write a per-build configure variant that bypasses config.guess.

        The upstream config.guess cannot recognize OHOS (uname -s returns
        ``HarmonyOS``, and the generic probe cannot compile under OHOS perms).
        Mirror the libXext 1.3.7 pattern: generate a tiny ``config.guess-
        compiler`` script that prints ``${CC} -dumpmachine`` (which is
        ``aarch64-unknown-linux-ohos`` for the OHOS clang), then rewrite the
        upstream configure to call THAT instead of the bundled config.guess.
        Also relax the hardcoded ``umask 077`` (twice) to ``umask 022`` so the
        Conan package directory is writable as expected.
        """
        upstream = Path(self.source_folder, "configure")
        if not upstream.is_file():
            raise ConanException(f"configure missing in source tree: {upstream}")
        config_guess = self._generate_compiler_config_guess()
        if any(c.isspace() for c in str(config_guess)):
            raise ConanException("config.guess build path contains whitespace")
        content = upstream.read_text(encoding="utf-8", errors="replace")
        if content.count("umask 077") != 2:
            raise ConanException("configure umask contract changed")
        replacements = (
            (
                'ac_config_guess="$SHELL ${ac_aux_dir}config.guess"',
                f'ac_config_guess="$SHELL {config_guess}"',
            ),
            (
                'ac_build_alias=`$SHELL "${ac_aux_dir}config.guess"`',
                f'ac_build_alias=`$SHELL "{config_guess}"`',
            ),
        )
        for original, replacement in replacements:
            if content.count(original) != 1:
                raise ConanException("configure config.guess contract changed")
            content = content.replace(original, replacement)
        generated = Path(self.build_folder, "configure-ohos")
        generated.parent.mkdir(parents=True, exist_ok=True)
        generated.write_text(
            content.replace("umask 077", "umask 022"),
            encoding="utf-8",
            newline="\n",
        )

    def _generate_compiler_config_guess(self):
        """Write a config.guess that prints the compiler's -dumpmachine tuple.

        The OHOS clang target is ``aarch64-unknown-linux-ohos``; emitting it
        directly lets configure skip the broken uname-based probing.
        """
        generated = Path(self.build_folder, "config.guess-compiler")
        content = """#!/bin/sh
set -eu
compiler="${CC_FOR_BUILD:-${CC:-}}"
if [ -z "$compiler" ]; then
    echo "config.guess compiler is unavailable" >&2
    exit 1
fi
tuple="$("$compiler" -dumpmachine)"
case "$tuple" in
    ""|*[!A-Za-z0-9._+-]*)
        echo "config.guess compiler tuple is invalid" >&2
        exit 1
        ;;
esac
printf '%s\\n' "$tuple"
"""
        generated.parent.mkdir(parents=True, exist_ok=True)
        generated.write_text(content, encoding="utf-8", newline="\n")
        return generated

    def _configure_ohos(self):
        shell = self._ohos_shell_path()
        configure = Path(self.build_folder, "configure-ohos")
        configure_args = [
            f"--srcdir={self.source_folder}",
            "--prefix=",
        ]
        arguments = " ".join(shlex.quote(a) for a in configure_args)
        self._run_ohos(f'"{shell}" "{configure}" {arguments}')

    def _ohos_shell_path(self):
        # Prefer the profile/PATH bash; fall back to a fixed path only if the
        # environment actually provides it. Do NOT hardcode a worker path that
        # may not exist on every OHOS device.
        shell = os.environ.get("CONFIG_SHELL") or shutil.which("bash")
        if not shell or not os.path.isfile(shell):
            raise ConanInvalidConfiguration(
                "OHOS configure needs bash (set CONFIG_SHELL or put bash on PATH)"
            )
        return shell

    def _run_ohos(self, command):
        shell = self._ohos_shell_path()
        prefix = f"export SHELL={shlex.quote(shell)} CONFIG_SHELL={shlex.quote(shell)}; "
        self.run(prefix + command, cwd=self.build_folder, env="conanbuild")
