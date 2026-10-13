#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Conan recipe: Lazarus 4.8 (lazbuild + LCL) for HarmonyOS PC (aarch64).

Scope
-----
Lazarus ships two layers: the LCL component library and the RAD IDE.  This
recipe delivers the command-line build tool ``lazbuild`` together with the
``nogui`` LCL widgetset and the component units (the ``make lazbuild``
target).  The GTK/Qt RAD IDE is not delivered:

* HarmonyOS PC has no X server, so no widgetset can open a display (the same
  conclusion recorded for bluefish/2.2.16);
* FPC's packaged GTK2 bindings request glibc-era sonames (``-lglib-2.0.0``,
  ``-lgdk-x11-2.0``, ``-lgdkglext-x11-1.0``, ...) that the OHOS GTK2 stack
  does not provide, and the gtk2/2.24.33 dependency closure is not fully
  published in the artifact repository;
* ``LCL_PLATFORM=nogui`` is not supported by the IDE component packages.

``lazbuild`` itself has no GUI dependency (upstream builds it with
``LCL_PLATFORM=nogui``) and runs natively on OHOS aarch64.

FPC target / OHOS specifics
---------------------------
FPC 3.2.2 has no ``ohos`` target, so ``fpc/3.2.2`` drives ``aarch64-linux``.
Its RTL is statically linked but the LCL uses ``dlopen``, which links the
OHOS musl ``libc.so`` and makes the lazarus binaries dynamically linked.
Three fixes are needed:

1. unit search order.  The FPC launcher passes every packaged package unit
   dir with ``-Fu`` before the caller's own; FPC takes the first match, so
   FPC's ``fv`` package shadows the LCL's ``menus``/``dialogs`` units.  The
   generated wrapper appends the FPC dirs after the caller's ``-Fu`` (and
   drops ``fv``), reproducing a system FPC install where those dirs come
   from ``fpc.cfg``.
2. OHOS sysroot.  ``-ldl``/``-lc`` come from FPC's Linux RTL; on OHOS
   ``libdl.a``/``libpthread.a`` are empty placeholders and the symbols live
   in musl ``libc.so``.  The wrapper adds the SDK sysroot lib dir and
   ``GCCLIBDIR=`` stops lazarus from injecting the host gcc directory.
3. glibc startup shim.  FPC's ``cprt0.o`` references the glibc-only
   ``__libc_csu_init``/``__libc_csu_fini``; an empty aarch64 stub object is
   linked in, and the ELF interpreter is retargeted from
   ``/lib/ld-linux-aarch64.so.1`` to ``/lib/ld-musl-aarch64.so.1``.
"""
import os
import shlex
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (apply_conandata_patches, copy,
                              export_conandata_patches, get)
from conan.tools.layout import basic_layout


_SHIM_ASM = """/* OHOS shim: glibc-only startup helpers used by FPC cprt0.o. */
        .text
        .globl __libc_csu_init
        .type  __libc_csu_init, %function
__libc_csu_init:
        ret
        .globl __libc_csu_fini
        .type  __libc_csu_fini, %function
__libc_csu_fini:
        ret
"""

_FPC_WRAPPER = """#!/bin/sh
# Generated wrapper around the packaged Free Pascal compiler.
FPC_ROOT=@FPC_ROOT@
SYSROOT=@SYSROOT@
SHIM=@SHIM@
UNITS=$FPC_ROOT/lib/fpc/3.2.2/units/aarch64-linux
PATH="$FPC_ROOT/bin:$PATH"; export PATH
for d in "$UNITS"/*; do
  case "$d" in "$UNITS/fv"|"$UNITS/jni") continue;; esac
  set -- "$@" -Fu"$d"
done
exec "$FPC_ROOT/lib/fpc/3.2.2/ppca64" \
  -FD"$FPC_ROOT/libexec/fpc-toolchain" -Fl"$SYSROOT" -k"$SHIM" \
  -Fu"$UNITS" -Fu"$UNITS/rtl" "$@"
"""

_LAUNCHER = """#!/bin/sh
# Relocatable launcher for @NAME@ inside the lazarus package.
self="$0"
case "$self" in
  */*) ;;
  *) self="$(command -v -- "$self" 2>/dev/null || printf '%s' "$self")" ;;
esac
while [ -h "$self" ]; do
  dir=$(cd -P "$(dirname "$self")" && pwd)
  link=$(readlink "$self")
  case "$link" in
    /*) self="$link" ;;
    *)  self="$dir/$link" ;;
  esac
done
root=$(cd -P "$(dirname "$self")/.." && pwd)
exec "$root/share/lazarus/@TARGET@" --lazarusdir="$root/share/lazarus" "$@"
"""


class LazarusConan(ConanFile):
    name = "lazarus"
    version = "4.8"
    package_type = "application"
    license = "GPL-2.0-or-later AND LGPL-2.1-or-later (with static-linking exception)"
    homepage = "https://www.lazarus-ide.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    description = ("Lazarus 4.8 command-line build tool (lazbuild) and LCL for "
                   "Free Pascal on HarmonyOS PC / aarch64")

    settings = "os", "compiler", "build_type", "arch"

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        self.tool_requires("fpc/3.2.2")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("lazarus/4.8 supports Linux/OHOS only")
        if str(self.settings.arch) not in ("armv8", "aarch64"):
            raise ConanInvalidConfiguration("lazarus/4.8 ships the aarch64 build only")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ------------------------------------------------------------------ utils
    def _toolchain_clang(self):
        try:
            execs = self.conf.get("tools.build:compiler_executables")
            if isinstance(execs, str):
                import json
                execs = json.loads(execs)
            if isinstance(execs, dict):
                return execs.get("c") or execs.get("cpp") or ""
        except Exception:
            pass
        return ""

    def _sysroot_libdir(self, clang):
        candidates = []
        if clang and os.path.isfile(clang):
            try:
                out = subprocess.run([clang, "-print-search-dirs"],
                                     capture_output=True, text=True,
                                     timeout=60).stdout
                for line in out.splitlines():
                    if not line.startswith("libraries:"):
                        continue
                    for entry in line.split("=", 1)[1].split(":"):
                        entry = os.path.normpath(entry.strip())
                        if entry.endswith("sysroot/usr/lib/aarch64-linux-ohos"):
                            candidates.append(entry)
            except Exception:
                pass
            native = os.path.normpath(os.path.join(os.path.dirname(clang), "..", ".."))
            candidates.append(os.path.join(native, "sysroot", "usr", "lib",
                                           "aarch64-linux-ohos"))
        # Fallbacks for workers whose compiler is a thin wrapper (no
        # -print-search-dirs sysroot entry) and for the local DevEco CLT.
        import glob
        for pattern in (
                "/data/service/hnp/ohos-sdk.org/*/ohos/native/sysroot/usr/lib/aarch64-linux-ohos",
                os.path.expanduser("~/command-line-tools/sdk/*/openharmony/native/sysroot/usr/lib/aarch64-linux-ohos"),
                os.path.expanduser("~/command-line-tools/sdk/default/openharmony/native/sysroot/usr/lib/aarch64-linux-ohos")):
            candidates.extend(sorted(glob.glob(pattern)))
        for entry in candidates:
            if os.path.isfile(os.path.join(entry, "libc.so")):
                return entry
        raise ConanException("OHOS aarch64 sysroot (libc.so) not found; checked: %s"
                             % candidates)

    def _make_shim(self, clang):
        src = os.path.join(self.build_folder, "ohos-glibc-shim.s")
        obj = os.path.join(self.build_folder, "ohos-glibc-shim.o")
        with open(src, "w", encoding="utf-8") as handle:
            handle.write(_SHIM_ASM)
        clang = clang or "aarch64-unknown-linux-ohos-clang"
        self.run('"%s" -c "%s" -o "%s"' % (clang, src, obj))
        return obj

    def _make_wrapper(self, fpc_root, sysroot, shim):
        wrapper = os.path.join(self.build_folder, "ohos-fpc")
        body = (_FPC_WRAPPER.replace("@FPC_ROOT@", fpc_root)
                .replace("@SYSROOT@", sysroot).replace("@SHIM@", shim))
        with open(wrapper, "w", encoding="utf-8") as handle:
            handle.write(body)
        os.chmod(wrapper, 0o755)
        return wrapper

    def _env(self, fpc_root):
        env = Environment()
        env.define_path("FPCDIR", os.path.join(fpc_root, "share", "fpc-3.2.2-src"))
        env.prepend_path("PATH", os.path.join(fpc_root, "bin"))
        return env

    def build(self):
        apply_conandata_patches(self)
        fpc_root = self.dependencies.build["fpc"].package_folder
        clang = self._toolchain_clang()
        sysroot = self._sysroot_libdir(clang)
        shim = self._make_shim(clang)
        wrapper = self._make_wrapper(fpc_root, sysroot, shim)
        self._fpc_root, self._wrapper = fpc_root, wrapper
        make = "make -j1 GCCLIBDIR= FPC=" + shlex.quote(wrapper)
        with self._env(fpc_root).vars(self).apply():
            self.run(make + " lazbuild", cwd=self.source_folder)

    def package(self):
        share = os.path.join(self.package_folder, "share", "lazarus")
        copy(self, "*", src=self.source_folder, dst=share,
             excludes=["build-release/*", "conaninfo.txt", "conanmanifest.txt",
                       "conanbuild.sh", "conanrun.sh", "conanbuild.bat",
                       "conanrun.bat", "ohos-fpc", "ohos-glibc-shim.*"])
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        for name, target in (("lazbuild", "lazbuild"),
                             ("lazres", "tools/lazres"),
                             ("lrstolfm", "tools/lrstolfm"),
                             ("updatepofiles", "tools/updatepofiles")):
            body = (_LAUNCHER.replace("@NAME@", name).replace("@TARGET@", target))
            path = os.path.join(bindir, name)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(body)
            os.chmod(path, 0o755)
        self._fix_interpreters()
        self._sign_elf()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))

    # ------------------------------------------------------------- post-build
    def _delivered_executables(self):
        """Exactly the ELF executables this package exposes (units/.o excluded)."""
        shipped = ("share/lazarus/lazbuild",
                   "share/lazarus/tools/lazres",
                   "share/lazarus/tools/lrstolfm",
                   "share/lazarus/tools/updatepofiles")
        executables = []
        for relative in shipped:
            path = os.path.join(self.package_folder, *relative.split("/"))
            if not os.path.isfile(path):
                continue
            try:
                with open(path, "rb") as handle:
                    if handle.read(4) == b"\x7fELF":
                        executables.append(path)
            except OSError:
                continue
        return executables

    def _fix_interpreters(self):
        old = b"/lib/ld-linux-aarch64.so.1\x00"
        new = b"/lib/ld-musl-aarch64.so.1\x00"
        for path in self._delivered_executables():
            with open(path, "rb") as handle:
                data = bytearray(handle.read())
            index = data.find(old)
            if index < 0:
                continue
            data[index:index + len(new)] = new
            data[index + len(new):index + len(old)] = b"\x00" * (len(old) - len(new))
            with open(path, "wb") as handle:
                handle.write(data)

    def _sign_elf(self):
        hnp = "/data/service/hnp/bin"
        signer = os.path.join(hnp, "binary-sign-tool")
        objcopy = os.path.join(hnp, "llvm-objcopy")
        if not os.path.isfile(signer) or not os.path.isfile(objcopy):
            self.output.warning("OHOS signing tools unavailable; skipping ELF re-sign")
            return
        for path in self._delivered_executables():
            self.run('"%s" --remove-section .codesign "%s" 2>/dev/null || true'
                     % (objcopy, path))
            self.run('"%s" sign -inFile "%s" -outFile "%s.signed" -selfSign 1'
                     % (signer, path, path))
            if os.path.isfile(path + ".signed"):
                os.replace(path + ".signed", path)
                os.chmod(path, 0o755)
