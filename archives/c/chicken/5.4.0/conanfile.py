#!/usr/bin/env python3
"""Conan recipe for chicken 5.4.0 — custom Makefile build system (HarmonyOS PC).

CHICKEN is a Scheme-to-C compiler. Build products:
  - 9 binaries: chicken, csi, csc, chicken-install, chicken-uninstall,
    chicken-status, chicken-profile, chicken-do, feathers
  - libchicken.so.11 / libchicken.a
  - 43 import modules (chicken.*.import.so)

Build: make PLATFORM=linux PREFIX=... C_COMPILER=... (NO configure script)
Notes:
  - HarmonyOS toybox lacks `install` command (E098/E174):
    an install wrapper (cp+chmod) is injected via INSTALL_PROGRAM.
  - Parallel make (-j) is NOT supported by CHICKEN (E074-related, R9: -j1).
  - make check: posix file-permissions fails on OHOS (E046, SELinux chmod);
    recorded in reports/, non-blocking.
  - R33: compiler path is taken from Conan conf (tools.build:compiler_executables:c),
    never from bare shell ${CC} which is empty on CI workers.
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout

# install wrapper (E098/E174): toybox on HarmonyOS lacks the `install` command.
# This wrapper emulates the subset of `install` used by CHICKEN's Makefile:
#   install -d -m MODE DIR...        (create dirs)
#   install -m MODE SRC... DEST      (copy file(s) + chmod)
_INSTALL_WRAPPER = r"""#!/bin/sh
# install-wrapper — toybox `install` replacement for HarmonyOS (E098/E174)
set -e
mkdir_only=0
mode=""
while [ $# -gt 0 ]; do
  case "$1" in
    -d) mkdir_only=1; shift ;;
    -m) mode="$2"; shift 2 ;;
    -g|-o|-t) shift 2 ;;
    -*) shift ;;
    *) break ;;
  esac
done
if [ "$mkdir_only" = "1" ]; then
  for d in "$@"; do
    mkdir -p "$d"
    if [ -n "$mode" ]; then chmod "$mode" "$d" 2>/dev/null || true; fi
  done
  exit 0
fi
n=$#
if [ "$n" -eq 0 ]; then echo "install-wrapper: missing operand" >&2; exit 1; fi
eval "dest=\"\${$n}\""
i=1
while [ "$i" -lt "$n" ]; do
  eval "s=\"\${$i}\""
  if [ -d "$dest" ]; then
    if ! cp -f "$s" "$dest/" 2>/dev/null && ! cp "$s" "$dest/"; then
      echo "install-wrapper: failed to copy $s -> $dest/" >&2
      exit 1
    fi
    if [ -n "$mode" ]; then
      b=$(basename "$s")
      chmod "$mode" "$dest/$b" 2>/dev/null || true
    fi
  else
    if ! cp -f "$s" "$dest" 2>/dev/null && ! cp "$s" "$dest"; then
      echo "install-wrapper: failed to copy $s -> $dest" >&2
      exit 1
    fi
    if [ -n "$mode" ]; then
      chmod "$mode" "$dest" 2>/dev/null || true
    fi
  fi
  i=$((i+1))
done
"""


class ChickenConan(ConanFile):
    name = "chicken"
    version = "5.4.0"
    description = ("CHICKEN Scheme-to-C compiler with csi REPL, csc driver, "
                   "egg manager tools and feathers debugger frontend")
    license = "BSD-3-Clause"
    homepage = "https://code.call-cc.org/"
    url = "https://code.call-cc.org/releases/5.4.0/chicken-5.4.0.tar.gz"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)
        # CHICKEN builds in-source via a custom Makefile (no configure script)
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _write_install_wrapper(self):
        wrapper = os.path.join(self.build_folder, "install-wrapper.sh")
        with open(wrapper, "w") as f:
            f.write(_INSTALL_WRAPPER)
        os.chmod(wrapper, 0o755)
        return wrapper

    def build(self):
        apply_conandata_patches(self)
        # R33: compiler from Conan conf (dict), never from bare shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        wrapper = self._write_install_wrapper()
        # Also export so the recursive sub-make inside `make install`
        # (NEEDS_RELINKING=yes) inherits the same settings.
        os.environ["C_COMPILER"] = cc
        os.environ["INSTALL_PROGRAM"] = wrapper
        # R9: CHICKEN does not support parallel make -> -j1
        self.run(
            f"make PLATFORM=linux PREFIX={self.package_folder} "
            f"C_COMPILER={cc} INSTALL_PROGRAM={wrapper} -j1",
            cwd=self.source_folder)

    def package(self):
        wrapper = os.path.join(self.build_folder, "install-wrapper.sh")
        # R33: 显式获取编译器，不依赖 build() 的 os.environ 隐式传递（跨方法自包含）
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        os.environ["C_COMPILER"] = cc
        self.run(
            f"make install PLATFORM=linux PREFIX={self.package_folder} "
            f"C_COMPILER={cc} INSTALL_PROGRAM={wrapper} -j1",
            cwd=self.source_folder)

    def package_info(self):
        self.cpp_info.libs = ["chicken"]
        self.cpp_info.bindirs = ["bin"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "dl"]
