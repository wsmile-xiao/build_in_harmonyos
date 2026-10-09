#!/usr/bin/env python3
"""Conan recipe for libubi 2.3.1-3 (upstream mtd-utils 2.3.1).

libubi is the UBI (Unsorted Block Images) development library shipped as
part of mtd-utils. The Debian/Ubuntu source package `mtd-utils 2.3.1-3`
produces the `libubi-dev` binary package, whose contents (libubi.a,
libmtd.a, the public + mtd/ kernel UAPI headers) are exactly what this
recipe packages.

Build route
-----------
autotools `./configure` is run **once, only to generate the autotools
`include/config.h`** (the lib/ sources carry `-include config.h`, and
`lib/execinfo.c` branches on `HAVE_EXECINFO_H`). The actual compilation
then uses the validated OHOS clang directly — no CMake, and no `make
install` (upstream marks these libs `noinst_LIBRARIES`, so `make install`
does not ship them). All optional mtd-utils features (zlib/lzo/zstd/
selinux/crypto/ubifs/jffs/lsmtd/ubihealthd/tests) are disabled, leaving
libubi with **zero external dependencies** (libc only). The six static
archives built by the top-level Makefile (libmtd/libmissing/libubi/
libubigen/libscan/libiniparser) are extracted and merged into a single
self-contained `libubi.a`, so a consumer links `-lubi` and pulls in the
whole UBI/MTD dev library in one go.

Why not a plain autotools build
-------------------------------
On OHOS the sandbox's `rm`/`sh` resolve to a broken safe-bin shim
(`#!/bin/bash` shebang, which does not exist on OHOS), so `./configure`
must be driven via `sh` with explicit `RM`/`SHELL`/`MKDIR_P` overrides and
a PATH that prefers /system/bin. Bypassing `make install` also avoids the
noinst_LIBRARIES gap (matched precedent: libogg/1.3.5.1 direct-cc route).
"""

import os
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (apply_conandata_patches, copy, get,
                                export_conandata_patches)
from conan.tools.layout import basic_layout


class LibubiConan(ConanFile):
    name = "libubi"
    version = "2.3.1-3"
    description = "UBI (Unsorted Block Images) development library from mtd-utils"
    license = "GPL-2.0-or-later"
    homepage = "https://www.linux-mtd.infradead.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def validate(self):
        # libubi (and the other mtd-utils dev libs) are declared
        # noinst_LIBRARIES upstream — no shared object is produced, so we
        # ship a static archive only (matches Debian libubi-dev and R4/R26).
        if self.options.shared:
            raise ConanException(
                "libubi is upstream noinst_LIBRARIES (static only); "
                "shared=True is not supported."
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def export_sources(self):
        export_conandata_patches(self)

    def test_requirements(self):
        # cmocka provides the unit-test harness for the upstream mtd-utils
        # unittests (tests/unittests/libubi_test.c, libmtd_test.c). A prebuilt
        # static OHOS aarch64 binary (cmocka/2.0.2) lives in the ohpcd remote,
        # so this does not add a build step.
        self.test_requires("cmocka/2.0.2")

    # ------------------------------------------------------------------
    # Toolchain helpers (validated clang + llvm-ar, matched libogg precedent)
    # ------------------------------------------------------------------
    def _validated_cc(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cand = (compilers.get("c") or "").strip()
        if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
        if cand:
            self.output.warning("conf c compiler '%s' not usable" % cand)
        for fallback in (shutil.which("clang"),
                         "/data/service/hnp/bin/clang",
                         shutil.which("cc"),
                         os.environ.get("CC")):
            if fallback and (os.path.isfile(fallback) or "/" not in fallback):
                self.output.info("Using C compiler: %s" % fallback)
                return fallback
        return "clang"

    def _validated_ar(self):
        for cand in (shutil.which("llvm-ar"),
                     "/data/service/hnp/bin/llvm-ar",
                     shutil.which("ar")):
            if cand and (os.path.isfile(cand) or "/" not in cand):
                return cand
        return "ar"

    def _writable_tmp(self):
        # autoconf's config.status hardcodes `mktemp -d "./confXXXXXX"` in its cwd
        # and IGNORES $TMPDIR. We patch config.status to honor $TMPDIR instead, so
        # $TMPDIR must point at a filesystem where SUBDIR creation actually works
        # (the CI build dir itself rejects subdir creation -> 'Permission denied').
        # Probe candidates and pick the first that allows a real subdir to be made.
        candidates = [
            "/data/storage/el2/base/cache",
            "/storage/Users/currentUser/.scratch",
            os.path.join(self.build_folder, "hmbs-tmp"),
        ]
        for base in candidates:
            if not base:
                continue
            try:
                os.makedirs(base, exist_ok=True)
                probe = tempfile.mkdtemp(prefix="ohpcd-", dir=base)
                os.rmdir(probe)
                cand = os.path.join(base, "libubi-conf")
                os.makedirs(cand, exist_ok=True)
                for key in ("TMPDIR", "TMP", "TEMP"):
                    os.environ[key] = cand
                self.output.info("using TMPDIR=%s" % cand)
                return cand
            except Exception as e:
                self.output.warning("candidate tmp %s unusable: %s" % (base, e))
                continue
        for key in ("TMPDIR", "TMP", "TEMP"):
            os.environ[key] = "/tmp"
        return "/tmp"

    def _patch_config_status(self, path, tmpdir):
        # autoconf 2.72 config.status creates a temp subdir with
        #   tmp=`(umask 077 && mktemp -d "./confXXXXXX") ...`
        # in its cwd and IGNORES $TMPDIR. On the CI worker the build dir rejects
        # subdir creation, so it dies with 'Permission denied'. Replace the
        # template with an EXPLICIT absolute path under tmpdir (a reliably
        # subdir-writable location) so mktemp places the temp dir there
        # regardless of whether the platform mktemp honors $TMPDIR.
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                data = f.read()
        except OSError:
            self.output.warning("config.status not found at %s; skipping mktemp patch" % path)
            return
        fixed = data.replace('mktemp -d "./confXXXXXX"',
                             'mktemp -d "%s/confXXXXXX"' % tmpdir)
        # harden the (rarely-taken) fallback branch too
        fixed = fixed.replace('tmp=./conf$$-$RANDOM',
                              'tmp=%s/conf$$-$RANDOM' % tmpdir)
        if fixed == data:
            self.output.warning("config.status mktemp pattern not found; leaving as-is")
            return
        with open(path, "w", encoding="utf-8") as f:
            f.write(fixed)
        self.output.info("patched config.status temp subdir -> %s" % tmpdir)

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------
    def _build_dir(self):
        # Out-of-tree (VPATH) build directory we create and own.
        # autoconf's config.status hardcodes a './confXXXXXX' temp subdir in its
        # cwd and IGNORES $TMPDIR; on the CI worker the Conan source tree rejects
        # subdir creation there, so we configure from a dir we control instead.
        bdir = os.path.join(self.build_folder, "ohos-build")
        os.makedirs(bdir, exist_ok=True)
        return bdir

    def build(self):
        tmpdir = self._writable_tmp()
        apply_conandata_patches(self)
        cc = self._validated_cc()
        ar = self._validated_ar()
        src = self.source_folder
        bdir = self._build_dir()

        # 1) Configure ONCE, out-of-tree (VPATH), to GENERATE config.status but
        #    NOT run it yet. autoconf's config.status hardcodes `mktemp -d
        #    "./confXXXXXX"` in its cwd and IGNORES $TMPDIR; on the CI worker the
        #    build dir rejects subdir creation, so we must patch config.status to
        #    use an explicit absolute temp dir (tmpdir) before it runs. OHOS
        #    safe-bin shim breaks bare `rm`/`sh`, so drive via `sh` with explicit
        #    RM/SHELL/MKDIR_P and a PATH that prefers /system/bin.
        configure_opts = [
            "sh %s/configure" % src,
            "--srcdir=%s" % src,
            "--no-create",
            "CC='%s'" % cc,
            "--prefix=/",
            "--without-zlib", "--with-lzo=no", "--with-zstd=no",
            "--with-selinux=no", "--without-crypto",
            "--without-ubifs", "--without-jffs", "--without-xattr",
            "--without-tests", "--disable-unit-tests",
            "--without-lsmtd", "--disable-ubihealthd",
            "RM=/system/bin/rm", "SHELL=/system/bin/sh",
            "MKDIR_P='/system/bin/mkdir -p'",
        ]
        self.run(
            "export PATH=/system/bin:$PATH; %s" % " ".join(configure_opts),
            cwd=bdir)

        # 1b) Patch config.status so its temp subdir lands in an explicit absolute
        #     tmpdir (a reliably subdir-writable location; the CI build dir itself
        #     is not), then run it ourselves to emit include/config.h + the
        #     Makefiles. Running it explicitly (via `sh`) also sidesteps the
        #     broken OHOS safe-bin shebang on the generated script.
        self._patch_config_status(os.path.join(bdir, "config.status"), tmpdir)
        self.run(
            "export PATH=/system/bin:$PATH; sh ./config.status",
            cwd=bdir)

        # 2) Build the six static lib archives (noinst_LIBRARIES) via VPATH make.
        self.run(
            "export PATH=/system/bin:$PATH; make libmtd.a libmissing.a libubi.a "
            "libubigen.a libscan.a libiniparser.a RM=/system/bin/rm "
            "SHELL=/system/bin/sh",
            cwd=bdir)

        # 3) Merge into a single self-contained libubi.a (staged in build_folder,
        #    not the source dir, so the extracted tarball stays pristine).
        objdir = os.path.join(self.build_folder, "objs")
        os.makedirs(objdir, exist_ok=True)
        libs = ["libmtd.a", "libmissing.a", "libubi.a",
                "libubigen.a", "libscan.a", "libiniparser.a"]
        for lib in libs:
            self.run("export PATH=/system/bin:$PATH; %s x '%s'"
                     % (ar, os.path.join(bdir, lib)), cwd=objdir)
        combined = os.path.join(self.build_folder, "libubi.a")
        self.run("export PATH=/system/bin:$PATH; %s rcs '%s' *.o"
                 % (ar, combined), cwd=objdir)

    # ------------------------------------------------------------------
    # Package
    # ------------------------------------------------------------------
    def package(self):
        # Public headers from the source tree (config.h.in is the template, skip it).
        copy(self, "*.h", os.path.join(self.source_folder, "include"),
             os.path.join(self.package_folder, "include"),
             keep_path=True, excludes=["config.h.in"])
        # config.h is generated by configure in the VPATH build dir.
        copy(self, "config.h", os.path.join(self._build_dir(), "include"),
             os.path.join(self.package_folder, "include"), keep_path=False)
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        copy(self, "libubi.a", self.build_folder,
             os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["ubi"]
        self.cpp_info.includedirs = ["include"]
