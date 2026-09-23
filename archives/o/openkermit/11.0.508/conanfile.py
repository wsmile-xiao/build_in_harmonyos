#!/usr/bin/env python3
"""Conan recipe — openkermit 11.0.508 (hand-written makefile, musl static target pattern).

OpenKermit (C-Kermit 11) is the Kermit Project's portable network/serial
communication and file-transfer tool.  Upstream ships a single hand-written
`makefile` (no autoconf/CMake); for musl-based systems it provides the
official `linux+musl` target which calls `xermit` directly with explicit
CFLAGS (no host probing), exactly what a HarmonyOS cross build needs.

This recipe follows that official pattern:
  * make xermit CC=<cc> CC2=<cc> CFLAGS="<LINUXCFLAGS> + pty + no-curses"
  * `xermit` produces ./wermit (select()-based CONNECT module); no hardcoded
    gcc anywhere in that path (verified: no gcc shim needed, unlike 9.0.302).
  * -DNOCURSES / -DNOGETUSERSHELL / -DNOARROWKEYS keep the build free of
    ncurses and of musl-missing libc APIs (getusershell, opaque FILE).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class OpenKermitConan(ConanFile):
    name = "openkermit"
    version = "11.0.508"
    description = "Kermit file transfer, terminal connection and scripting tool"
    license = "BSD-3-Clause"
    homepage = "https://www.openkermit.org/"
    url = "https://github.com/OpenKermit/ckermit"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        # HMBS readonly-/tmp hardening: conan get() stages the archive via
        # tempfile (honors TMPDIR); pin it to the task-private dir so a
        # read-only /tmp cannot truncate the download and cause a spurious
        # sha256 mismatch here (cf. preflight.sh /tmp errors).
        tmpdir = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                  or os.environ.get("TEMP"))
        if tmpdir:
            os.makedirs(tmpdir, exist_ok=True)
            os.environ["TMPDIR"] = tmpdir
            os.environ["TMP"] = tmpdir
            os.environ["TEMP"] = tmpdir
        # codeload tag tarball unpacks to a single top dir ckermit-11.0.508/
        # (strip_root=True strips it, matching the layout c-kermit recipe
        # expects after its flat-package exception).
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # HMBS readonly-/tmp hardening: redirect tool temp files to the
        # task-private dir injected as TMPDIR/TMP/TEMP.
        tmpdir = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                  or os.environ.get("TEMP"))
        if tmpdir:
            os.makedirs(tmpdir, exist_ok=True)
            os.environ["TMPDIR"] = tmpdir
            os.environ["TMP"] = tmpdir
            os.environ["TEMP"] = tmpdir
        # R33: compiler from Conan conf, never ${CC} from shell env.
        # tools.build:compiler_executables is a dict conf ({"c": "clang"});
        # read the dict first (the ":c" sub-key form does not exist in
        # Conan 2.30's conf list and raises).
        try:
            compiler_exes = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict)
        except Exception:
            compiler_exes = {}
        if isinstance(compiler_exes, dict) and compiler_exes.get("c"):
            cc = compiler_exes["c"]
        else:
            cc = "clang"
        make = os.environ.get("HMBS_MAKE", "make")
        sh = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        # Official musl build pattern (makefile target `linux+musl`, minus
        # OpenSSL and ncurses which HarmonyOS PC does not need here):
        #   xermit is called directly with explicit CFLAGS so no host
        #   autodetection runs (the `linux` target probes /usr/include and
        #   `ld -l*`, meaningless for a cross toolchain).
        linflags = ("-O2 -DLINUX -pipe -funsigned-char -DFNFLOAT "
                    "-DCK_POSIX_SIG -DCK_NEWTERM -DTCPSOCKET -DLINUXFSSTND "
                    "-DNOCOTFMC -DPOSIX -DUSE_STRERROR")
        extra = ("-DHAVE_PTMX -DHAVE_OPENPTY -DNOCURSES "
                 "-DNOGETUSERSHELL -DNOARROWKEYS")
        cflags = f"{linflags} {extra}"
        # R9: -j1 (OHOS build constraint).  Build in source_folder (the
        # makefile lives there; basic_layout separates source/build dirs).
        self.run(f"{make} xermit CC={cc} CC2={cc} "
                 f"CFLAGS=\"{cflags}\" LIBS=-lm SHELL={sh} -j1",
                 cwd=self.source_folder)

    def package(self):
        # Upstream produces ./wermit; ship it as bin/kermit.
        src = os.path.join(self.source_folder, "wermit")
        dst_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(dst_dir, exist_ok=True)
        shutil.copy2(src, os.path.join(dst_dir, "kermit"))
        copy(self, "COPYING.TXT", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
