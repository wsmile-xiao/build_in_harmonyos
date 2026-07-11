#!/usr/bin/env python3
"""Conan recipe — bitwise 0.50 (terminal bit-field calculator).

Autotools project (configure + make + make install).
System prebuilt ncurses/readline via DEFAULT_PREFIX env var.
Bundled ncurses/readline headers and .a libraries as fallback
for CI workers that lack both.
"""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.env import Environment
from conan.tools.layout import basic_layout


class BitwiseConan(ConanFile):
    name = "bitwise"
    version = "0.50"
    description = "Terminal bit-field calculator with interactive mode"
    license = "MIT"
    package_type = "application"
    homepage = "https://github.com/mellowcandle/bitwise"
    url = "https://github.com/mellowcandle/bitwise"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        # Export bundled ncurses/readline headers + .a libs for CI workers
        res_src = os.path.join(self.recipe_folder, "res")
        if os.path.isdir(res_src):
            res_dst = os.path.join(self.export_folder, "res")
            if os.path.exists(res_dst):
                shutil.rmtree(res_dst)
            shutil.copytree(res_src, res_dst)

    # R26/R27: System prebuilt ncurses/readline are NOT in requires().
    # They are available via DEFAULT_PREFIX env var (CFLAGS/LDFLAGS).
    # CI workers may lack both headers and .a libraries; bundled in res/.

    def validate(self):
        # R32: Use `in ("Linux", "OHOS")` for settings.os check
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"bitwise supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Fix CRLF line endings in config.h.in (replaces 0004 patch)
        config_h = os.path.join(self.source_folder, "inc", "config.h.in")
        if os.path.exists(config_h):
            with open(config_h, "rb") as f:
                content = f.read()
            with open(config_h, "wb") as f:
                f.write(content.replace(b"\r\n", b"\n"))
        # Copy bundled headers from export folder to source folder
        # so they're available when sources are copied to build folder.
        # Conan only auto-copies conandata patches, not custom export_sources.
        export_dir = os.path.join(os.path.dirname(self.source_folder), "e")
        res_src = os.path.join(export_dir, "res")
        if os.path.isdir(res_src):
            res_dst = os.path.join(self.source_folder, "res")
            if os.path.exists(res_dst):
                shutil.rmtree(res_dst)
            shutil.copytree(res_src, res_dst)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # DEFAULT_PREFIX is set by build context; fallback to ~/usr/local
        sysroot = os.environ.get("DEFAULT_PREFIX", os.path.expanduser("~/usr/local"))
        sys_inc = os.path.join(sysroot, "include")

        # Check if system ncurses headers are available
        if os.path.exists(os.path.join(sys_inc, "form.h")):
            tc.extra_cflags.append(f"-I{sys_inc}")
        else:
            # CI worker has ncurses .a but no headers; use bundled
            bundled_inc = os.path.join(self.source_folder, "res", "headers")
            if os.path.isdir(bundled_inc):
                tc.extra_cflags.append(f"-I{bundled_inc}")
                # Force readline detection: configure's AC_CHECK_LIB fails
                # because static libreadline.a has unresolved ncurses symbols
                # when tested alone. Without these defines, bitwise.h skips
                # #include <readline/readline.h>, leaving rl_* undeclared.
                tc.extra_cflags.append("-DHAVE_LIBREADLINE")
                tc.extra_cflags.append("-DHAVE_READLINE_READLINE_H")
                tc.extra_cflags.append("-DHAVE_READLINE_HISTORY")
                tc.extra_cflags.append("-DHAVE_READLINE_HISTORY_H")
            # Point to bundled .a libraries (readline, form, ncurses)
            bundled_libs = os.path.join(self.source_folder, "res", "libs")
            if os.path.isdir(bundled_libs):
                tc.extra_ldflags.append(f"-L{bundled_libs}")

        tc.extra_cflags.append("-DNCURSES_WIDECHAR")
        # Fix: basic_layout creates build-release/ subdir, breaking -I./inc
        tc.extra_cflags.append(f"-I{self.source_folder}/inc")
        # Point to system prebuilt ncurses/readline libraries
        tc.extra_ldflags.append(f"-L{sysroot}/lib")
        # R26: Terminal tools must be statically linked
        tc.extra_ldflags.append("-static")
        # FIX: AutotoolsToolchain defaults to --prefix=package_folder,
        # and autotools.install() sets DESTDIR=package_folder.
        # This causes double-nesting: DESTDIR/prefix/bin/bitwise.
        # Setting --prefix=/ makes install path: DESTDIR/bin/bitwise
        tc.configure_args.append("--prefix=/")
        tc.generate()

        # Set TMPDIR for config.status mktemp (OHOS /tmp is read-only)
        env = Environment()
        tmpdir = os.path.expanduser("~/tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env.define("TMPDIR", tmpdir)
        env.vars(self).save_script("env_tmpdir")

    def build(self):
        # R33: build() does not depend on undefined shell environment variables.
        # All paths are set via AutotoolsToolchain in generate().
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        # When using bundled headers (CI worker), configure can't detect
        # readline/ncurses/form libraries (static lib dependency chain breaks
        # AC_CHECK_LIB). Patch Makefile to set LIBS directly — passing LIBS
        # on the make command line causes space-splitting (make treats
        # -lform -lncurses as -l options, not as part of LIBS value).
        # Order matters for static linking: readline → form → ncurses.
        sys_inc = os.path.join(
            os.environ.get("DEFAULT_PREFIX", os.path.expanduser("~/usr/local")),
            "include",
        )
        if not os.path.exists(os.path.join(sys_inc, "form.h")):
            makefile = os.path.join(self.build_folder, "Makefile")
            if os.path.exists(makefile):
                with open(makefile, "r") as f:
                    content = f.read()
                content = re.sub(
                    r"^LIBS\s*=.*$",
                    "LIBS = -lreadline -lform -lncurses",
                    content,
                    flags=re.MULTILINE,
                )
                with open(makefile, "w") as f:
                    f.write(content)
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
