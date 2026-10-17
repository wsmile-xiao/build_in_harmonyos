#!/usr/bin/env python3
"""Conan recipe for yubico-c 2.15 (ykclient).

Yubico C client library (libykclient) for validating YubiKey OTPs against
the YubiCloud validation server.  Upstream repository:
  https://github.com/Yubico/yubico-c-client

Produces:
  - libykclient (static by default)
  - ykclient CLI tool

Dependencies:
  - libcurl/8.5.0 (HTTP transport, published on ohpcd)

OHOS adaptations (same family as libtatsu 1.0.5):
  - --build/--host=aarch64-unknown-linux-gnu: the bundled config.sub (2014)
    rejects the ohos vendor string ("Invalid configuration: machine
    'aarch64-unknown-linux' not recognized").  Use gnu which config.sub
    accepts; the actual compiler is OHOS clang via compiler_executables.
  - E114 umask fix: configure uses `umask 077 && mktemp -d` / `mkdir` which
    creates drwx--S--- dirs on HMDFS (setgid + MAC), causing config.status
    to fail.  Strip `umask 077 &&` from the generated configure in build().
  - mktemp wrapper: return failure to force the mkdir fallback.
  - AutotoolsDeps + PkgConfigDeps: feed -I/-L/-l and .pc files for libcurl.
  - LD_LIBRARY_PATH: OHOS loader has no default search path for conan-cached
    shared libs; configure conftest programs need it set.
  - make -j1: parallel make hits HMDFS jobserver fifo EPERM.
  - E289: help2man missing on OHOS; clear automake man lists
    (MANS=/man_MANS=/man1_MANS=/dist_man_MANS=) on make and make install;
    pass -j1 to install() to stop Conan auto-appending -j20 (R9).
"""
import os
import stat
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps, PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.env import Environment


def _drop_umask_077(conanfile, path):
    """E114: HMDFS forces setgid on directories; `umask 077 && mktemp -d`
    creates a drwx--S--- temp dir that is not writable even by its owner.
    Remove `umask 077 &&` so config.status can create its temp dir."""
    with open(path, "r", encoding="utf-8") as f:
        data = f.read()
    data = data.replace(
        'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null`',
        'tmp=`mktemp -d "./confXXXXXX" 2>/dev/null`')
    data = data.replace('(umask 077 && mkdir "$tmp")', 'mkdir "$tmp"')
    with open(path, "w", encoding="utf-8") as f:
        f.write(data)


class YubicoCConan(ConanFile):
    name = "yubico-c"
    version = "2.15"
    description = "Yubico C client library (libykclient) for YubiKey OTP validation"
    license = "BSD-2-Clause"
    homepage = "https://developers.yubico.com/yubico-c-client/"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"yubico-c is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def requirements(self):
        self.requires("libcurl/8.5.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # HarmonyOS: mktemp -d creates dirs with drwx--S--- (broken group perms),
        # causing config.status to fail.  Return failure to force mkdir fallback.
        wrapper_dir = Path(self.build_folder) / ".hmos_fix"
        wrapper_dir.mkdir(exist_ok=True)
        wrapper = wrapper_dir / "mktemp"
        wrapper.write_text(
            '#!/bin/sh\n'
            '# HarmonyOS: mktemp -d creates dirs with broken perms (hmmac MAC).\n'
            '# Return failure to force autoconf AS_TMPDIR to use mkdir fallback.\n'
            'exit 1\n'
        )
        wrapper.chmod(wrapper.stat().st_mode | stat.S_IEXEC)

        # AutotoolsDeps: feed -I/-L/-l from libcurl into configure/make
        deps = AutotoolsDeps(self)
        deps.generate()

        # PkgConfigDeps: generate libcurl.pc for pkg-config checks
        pkgconfig = PkgConfigDeps(self)
        pkgconfig.generate()

        tc = AutotoolsToolchain(self)
        # config.sub (2014) rejects the ohos vendor string
        # ("Invalid configuration: machine 'aarch64-unknown-linux' not
        # recognized").  Use gnu which config.sub accepts; the actual
        # compiler is OHOS clang from tools.build:compiler_executables.
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.configure_args.append("--host=aarch64-unknown-linux-gnu")
        # AutotoolsToolchain auto-adds --enable-static/--disable-shared
        # when shared=False; no need to duplicate.
        tc.generate()

        # Prepend wrapper to PATH
        env = Environment()
        env.prepend_path("PATH", str(wrapper_dir))
        # OHOS loader needs LD_LIBRARY_PATH for conftest programs.
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.vars(self, scope="build").save_script("hmos_env")

        # Override CONFIG_SHELL in the buildenv: the OHOS profile sets it to
        # /data/service/hnp/bin/bash which does not exist on the local macOS
        # build host.  "sh" resolves on both OHOS (PATH includes hnp/bin) and
        # macOS (/bin/sh).  configure re-execs itself via "$CONFIG_SHELL" "$0".
        self.buildenv.define("CONFIG_SHELL", "sh")
        self.buildenv.define("SHELL", "sh")

    def build(self):
        apply_conandata_patches(self)
        # E114: strip umask 077 from the generated configure (HMDFS)
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.exists(configure_path):
            _drop_umask_077(self, configure_path)
        autotools = Autotools(self)
        autotools.configure()
        # R9: single job — parallel make hits HMDFS jobserver fifo EPERM.
        # E289: help2man is not available in the OHOS build environment.
        # automake puts $(MANS) in the all-am dependencies, and the man rule
        # (ykclient.1: ykclient tool.c configure.ac) re-runs help2man because
        # the freshly built ykclient binary is newer than the shipped man
        # page.  Override MANS/man1_MANS on the command line to skip man page
        # generation (clear-automake-man-list).
        autotools.make(args=["-j1", "MANS=", "man1_MANS="])

    def package(self):
        autotools = Autotools(self)
        # E289: this automake template puts $(dist_man_MANS) directly in the
        # install-man1 prerequisites (install-man1: $(dist_man_MANS)), so
        # MANS=/man_MANS=/man1_MANS= alone are not enough — clear
        # dist_man_MANS= as well.  Conan's install() auto-appends -j<n> when
        # args carry no -j; pass -j1 explicitly (R9: HMDFS jobserver EPERM).
        autotools.install(args=["-j1", "MANS=", "man_MANS=", "man1_MANS=", "dist_man_MANS="])

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "yubico-c")
        self.cpp_info.set_property("pkg_config_name", "ykclient")
        self.cpp_info.libs = ["ykclient"]
        self.cpp_info.requires = ["libcurl::libcurl"]
