#!/usr/bin/env python3
"""Conan recipe — npth 1.8.1 (Autotools)

npth 1.8.1 = upstream npth 1.8 + HarmonyOS PC adaptation fixes:
  - build-aux/config.guess and build-aux/config.sub: HarmonyOS /
    aarch64-linux-ohos detection
  - configure.ac: probe pthread_create instead of pthread_cancel on
    *-*-linux-ohos* (musl libc does not implement pthread_cancel);
    configure is regenerated with autoconf inside build() so the patch
    stays on the source file rather than on the generated script
  - build(): point the config.status temporary directory at device-local
    storage (E114), restore the Autotools helper execute bits (E490) and
    run the upstream `make check` suite (R51)
"""
import hashlib
import os
import shlex
import stat

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

# Device-local scratch space: the shared HMDFS volume turns directories
# created with `umask 077` into unwritable ones, so config.status cannot
# create ./confXXXXXX there (E114).
_DEVICE_TMP = "/data/storage/el2/base/temp"

# Known Autotools helper scripts that must keep their execute bits (E490).
_HELPER_SCRIPTS = {
    "configure",
    "config.guess",
    "config.sub",
    "install-sh",
    "missing",
    "compile",
    "depcomp",
    "ltmain.sh",
}


class NpthConan(ConanFile):
    name = "npth"
    version = "1.8.1"
    description = "GNU Portable Threads library — lightweight threading based on pthread"
    license = "LGPL-2.1-or-later"
    homepage = "https://gnupg.org/software/npth/"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # R26: system-name libraries are packaged statically by default
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self._restore_helper_modes()
        # Patch 0003 edits configure.ac, so configure has to be regenerated
        # for the patched pthread probe to take effect.
        self.run("autoconf -o configure configure.ac", cwd=self.source_folder)
        self._fix_config_status_tmp()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # R51: run the upstream test suite, not only the consumer test.
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        self._cleanup_config_status_tmp()

    def package_info(self):
        self.cpp_info.libs = ["npth"]

    def _config_status_tmp(self):
        digest = hashlib.sha256(self.build_folder.encode("utf-8")).hexdigest()[:16]
        return os.path.join(_DEVICE_TMP, "npth-" + digest)

    def _fix_config_status_tmp(self):
        """E114: config.status cannot create its temp dir on HMDFS."""
        tmp_dir = self._config_status_tmp()
        os.makedirs(tmp_dir, exist_ok=True)
        self.output.info("config.status temp dir: {}".format(tmp_dir))
        replace_in_file(
            self,
            os.path.join(self.source_folder, "configure"),
            "ac_tmp=$tmp",
            "ac_tmp={}".format(shlex.quote(tmp_dir)),
        )

    def _cleanup_config_status_tmp(self):
        tmp_dir = self._config_status_tmp()
        if os.path.isdir(tmp_dir):
            for name in os.listdir(tmp_dir):
                os.remove(os.path.join(tmp_dir, name))
            os.rmdir(tmp_dir)

    def _restore_helper_modes(self):
        """E490: HMDFS-style paths can drop the execute bit of the helpers."""
        exec_bits = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        for root, _dirs, files in os.walk(self.source_folder):
            for name in files:
                if name in _HELPER_SCRIPTS:
                    path = os.path.join(root, name)
                    os.chmod(path, os.stat(path).st_mode | exec_bits)
