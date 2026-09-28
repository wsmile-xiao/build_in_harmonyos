#!/usr/bin/env python3
"""Conan recipe for xcmsdb 1.0.7 (X.org application).

xcmsdb loads, queries, lists and removes the ICC colour database of an X
server through the Xcms API of libX11.  The upstream build system is GNU
autotools and the sources are two C files (xcmsdb.c, loadData.c) plus one
generated man page.

Declared patches, applied for real in build():
  0001 configure HMDFS pwd fallback plus config.status umask relaxation
  0002 config.guess HarmonyOS host detection
  0003 config.sub   acceptance of the ohos OS token
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (apply_conandata_patches, export_conandata_patches,
                               get, rm)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout

# E182/E188: the install(1) shim on HMFS fails as soon as it receives a -c
# option, which is exactly what automake emits for install-man (exit 64).
# automake only needs copy, mkdir and an optional mode here, so Makefile
# INSTALL is redirected to this cp/mkdir shim.  chmod stays best effort
# because HMFS has no chmod capability (E046/E087).
_INSTALL_SHIM = """#!/bin/sh
set -eu
mode=
while [ $# -gt 0 ]; do
  case "$1" in
    -p|-c) shift ;;
    -m) [ $# -ge 2 ] || exit 2; mode=$2; shift 2 ;;
    -d) shift; [ $# -gt 0 ] || exit 2; mkdir -p "$@"; exit 0 ;;
    --) shift; break ;;
    -*) shift ;;
    *) break ;;
  esac
done
[ $# -ge 2 ] || exit 2
dest=
for arg in "$@"; do dest=$arg; done
count=$(($# - 1))
mkdir -p "$(dirname "$dest")"
i=1
for src in "$@"; do
  [ $i -gt $count ] && break
  cp -f "$src" "$dest"
  if [ -n "$mode" ]; then
    if [ -d "$dest" ]; then
      chmod "$mode" "$dest/${src##*/}" 2>/dev/null || true
    else
      chmod "$mode" "$dest" 2>/dev/null || true
    fi
  fi
  i=$((i + 1))
done
"""


class XcmsdbConan(ConanFile):
    name = "xcmsdb"
    version = "1.0.7"
    description = ("xcmsdb loads, queries, lists and removes ICC colour "
                   "database entries of an X server through the Xcms API")
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/app/xcmsdb"
    url = ""

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "xcmsdb is an X11 client, supported on Linux and OHOS only"
            )

    def requirements(self):
        self.requires("libx11/1.8.13")
        self.requires("xorgproto/2025.1")

    def build_requirements(self):
        # configure probes xorg-macros through pkg-config (XORG_DEFAULT_OPTIONS
        # / XORG_MANPAGE_SECTIONS), so util-macros has to be reachable in the
        # build context.
        self.tool_requires("util-macros/1.20.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            env = tc.environment()
            shell = "/data/service/hnp/bin/bash"
            env.define_path("SHELL", shell)
            env.define_path("CONFIG_SHELL", shell)
            env.define_path("CC", "/data/service/hnp/bin/clang")
            env.define_path("CXX", "/data/service/hnp/bin/clang++")
            env.define_path("LD", "/data/service/hnp/bin/ld.lld")
            env.define_path("AR", "/data/service/hnp/bin/llvm-ar")
            env.define_path("RANLIB", "/data/service/hnp/bin/llvm-ranlib")
            env.define_path("STRIP", "/data/service/hnp/bin/llvm-strip")
            env.define_path("NM", "/data/service/hnp/bin/llvm-nm")
        tc.generate()
        # PKG_CHECK_MODULES(XCMSDB, x11) needs x11.pc at configure time.  The
        # libX11 package publishes pkg_config_name=x11, so PkgConfigDeps writes
        # a usable x11.pc into the generators folder, and VirtualBuildEnv
        # exports PKG_CONFIG_PATH (plus the util-macros .pc dir) for configure.
        PkgConfigDeps(self).generate()
        VirtualBuildEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        # HMDFS: after conan has created the build tree the parent directory is
        # unreachable for getcwd(), so the pwd substitution inside configure
        # aborts with "working directory cannot be determined".  Exporting PWD
        # lets the shell builtin report the logical path (as in the adms and
        # analog recipes) and patch 0001 falls back to it.
        os.environ["PWD"] = self.build_folder
        autotools = Autotools(self)
        autotools.configure()
        if str(self.settings.os) == "OHOS":
            shim = self._write_install_shim()
            self._redirect_install_to_shim(shim)
        autotools.make(args=["-j1"])

    def _write_install_shim(self):
        shim_dir = os.path.join(self.build_folder, "_ohos_install_shim")
        os.makedirs(shim_dir, exist_ok=True)
        install = os.path.join(shim_dir, "install")
        # HMFS takes the mode from the open call, so the shim is created
        # executable instead of relying on a later chmod.
        fd = os.open(install, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(_INSTALL_SHIM)
        except Exception:
            os.close(fd)
            raise
        return install.replace("\\", "/")

    def _redirect_install_to_shim(self, shim_install):
        # configure has already baked the probed install program into every
        # generated Makefile.  Only the INSTALL assignment is rewritten;
        # INSTALL_DATA and INSTALL_PROGRAM reference ${INSTALL} so they follow.
        for root, _, files in os.walk(self.build_folder):
            for name in files:
                if name != "Makefile":
                    continue
                path = os.path.join(root, name)
                with open(path, "r", encoding="utf-8", errors="ignore") as handle:
                    content = handle.read()
                if "INSTALL =" not in content:
                    continue
                lines = []
                changed = False
                for line in content.splitlines(True):
                    stripped = line.lstrip()
                    if stripped.startswith("INSTALL = ") and "/install" in stripped:
                        indent = line[:len(line) - len(stripped)]
                        lines.append(indent + "INSTALL = " + shim_install + "\n")
                        changed = True
                    else:
                        lines.append(line)
                if changed:
                    with open(path, "w", encoding="utf-8", newline="\n") as handle:
                        handle.write("".join(lines))

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        rm(self, "*.la", self.package_folder, recursive=True)
        rm(self, "*.o", self.package_folder, recursive=True)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
