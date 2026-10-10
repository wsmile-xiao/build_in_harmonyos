#!/usr/bin/env python3
"""Conan recipe for yaku-ns 0.2 — tiny DNS server, HarmonyOS PC (aarch64-linux-ohos).

Upstream is Salvatore Sanfilippo's yaku-ns, last released as 0.2 in 2010 and
packaged by Debian ever since.  The release tarball builds with a
hand-written Makefile and no configure script; it installs two programs:

  yaku-ns        authoritative/forwarding DNS server (UDP + AXFR over TCP)
  yaku-getzone   AXFR client that prints a zone as a yaku-ns config file

There are no third-party dependencies at all: the whole server is plain C over
POSIX sockets, so `requirements()` is empty and the L0i registry gate has
nothing to resolve.

Source of record
----------------
The 0.2 release is not tagged in antirez/yaku-ns (that repository still has
ENS_VERSION 0.1.6, no release tag and no release tarball).  The tag `0.2` lives
in the Debian maintainer's mirror, and Debian's own `yaku-ns_0.2.orig.tar.gz`
is byte-for-byte identical to it (sha256 verified on both, see notes.md).
Debian's pool is used as the download URL because it is the authoritative,
immutable distribution channel for this release.

Patches
-------
0001-nameser-portability.patch
    nameser.h is a verbatim 1993 BSD <arpa/nameser.h> that uses
    __BEGIN_DECLS/__END_DECLS/__P() and the u_char/u_int16_t typedefs without
    including the header that defines them.  glibc reaches <sys/cdefs.h> through
    <features.h>; musl (the OHOS libc) does not, so every translation unit fails.
    The header is made self-contained.  No logic changes.

0002-cli-long-options.patch
    Neither binary answers --version (plain getopt() over a short-only option
    string, and -h exits 1).  getopt_long() is used with --version/--help added;
    all existing short options keep their behaviour.  The reported version is the
    release number injected by this recipe, because upstream never bumped
    ENS_VERSION for 0.2.

Runtime notes
-------------
* yaku-ns calls chdir("/") before reading its config file and only drops
  privileges when it is started as root, so the packaged daemon needs an absolute
  -c path and a resolvable -u user.  test_package handles both.
* FD_SET() expands to a call to __fd_chk() in the OHOS <sys/select.h>.  That
  symbol is exported by the real OHOS libc; the WSL guest musl used for local
  builds predates it, so local *execution* of the daemon needs an LD_PRELOAD
  shim.  That is a property of the local guest libc, not of this package - see
  notes.md, and the shim is never referenced from this recipe.
"""

import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import build_jobs
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import GnuToolchain
from conan.tools.layout import basic_layout


class YakunsConan(ConanFile):
    name = "yaku-ns"
    version = "0.2"
    description = ("Tiny DNS server (authoritative + forwarding, AXFR over TCP) "
                   "with the yaku-getzone AXFR client")
    license = "GPL-2.0-only"
    homepage = "https://github.com/antirez/yaku-ns"
    url = ""

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    _programs = ("yaku-ns", "yaku-getzone")

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: OHOS must be listed next to Linux, never compared with ==.
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"yaku-ns is a POSIX DNS server and supports Linux/OHOS only, "
                f"not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # GnuToolchain gives the build scope a CC that matches the profile's
        # compiler_executables; build() still reads the path from conf directly
        # so that nothing depends on the environment being pre-populated (R33).
        GnuToolchain(self).generate()

    def _compiler(self, language="c"):
        compilers = self.conf.get("tools.build:compiler_executables", default={},
                                  check_type=dict) or {}
        return compilers.get(language) or shutil.which("clang") or "clang"

    def _cflags(self):
        """Optimisation flags for the requested build type, plus the include path.

        Upstream's Makefile assigns CFLAGS itself, so the value has to be
        overridden on the command line.  -Wall replaces upstream's obsolete bare
        -W; debug info is only emitted for Debug builds so the shipped binaries
        do not carry it.
        """
        if str(self.settings.build_type) == "Debug":
            opt = ["-O0", "-g"]
        else:
            opt = ["-O2"]
        opt += ["-Wall"]
        # The generated version header lives in the build folder and is reached
        # through this include path (see build()).
        opt += ["-I" + self.build_folder]
        return " ".join(opt)

    def build(self):
        apply_conandata_patches(self)

        # Upstream's ENS_VERSION still reads 0.1.6 in the 0.2 release, so the
        # --version output has to come from the recipe.  The header is generated
        # here (not committed) and reached through the include path that the
        # patch adds; a build outside Conan keeps using ENS_VERSION.
        with open(os.path.join(self.build_folder, "yaku-version.h"), "w",
                  encoding="utf-8") as fh:
            fh.write(f'#define YAKUNS_PKG_VERSION "{self.version}"\n')

        cc = self._compiler("c")
        self.run(
            f'make CC={shlex.quote(cc)} '
            f'CFLAGS={shlex.quote(self._cflags())} '
            f'-j{build_jobs(self)}',
            cwd=self.source_folder,
            env="conanbuild",
        )

        for program in self._programs:
            path = os.path.join(self.source_folder, program)
            if not os.path.isfile(path) or os.path.getsize(path) == 0:
                raise ConanException(f"expected build output missing: {path}")

    def _sign_ohos(self, path):
        """Sign one packaged ELF for OHOS, if the signing tools are reachable.

        OHOS refuses to execute unsigned ELFs, so a signed package is the only
        form that actually runs on the target.  When the toolchain is absent
        (for example a plain Linux build host) this is a no-op with a warning
        rather than an error, matching how other application recipes in this
        repository behave.
        """
        if str(self.settings.os) != "OHOS":
            return

        signer = self.conf.get("user.ohos:sign_tool", default="", check_type=str)
        signer = (signer or os.environ.get("OHOS_SIGN_TOOL", "")
                  or shutil.which("binary-sign-tool")
                  or "/data/service/hnp/bin/binary-sign-tool")
        if not os.path.isfile(signer):
            self.output.warning(
                "binary-sign-tool unavailable; leaving yaku-ns binaries unsigned"
            )
            return

        objcopy = self.conf.get("user.ohos:objcopy", default="", check_type=str)
        objcopy = (objcopy or os.environ.get("OHOS_OBJCOPY", "")
                   or shutil.which("llvm-objcopy")
                   or "/data/service/hnp/bin/llvm-objcopy")
        if os.path.isfile(objcopy):
            self.run(f'"{objcopy}" --remove-section .codesign "{path}"',
                     ignore_errors=True)

        signed = f"{path}.signed"
        self.run(f'"{signer}" sign -inFile "{path}" -outFile "{signed}" '
                 f'-selfSign 1')
        if not os.path.isfile(signed):
            raise ConanException(f"binary-sign-tool produced no output for {path}")
        os.replace(signed, path)
        # HMDFS may drop the executable bit on the signed file (knowledge base
        # E046 / knowledge entry on HMDFS install EPERM); restore it so the
        # packaged command is runnable.
        os.chmod(path, 0o755)

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        for program in self._programs:
            # copy() (not a plain file move) plus chmod: on HMDFS the executable
            # bit of an installed artifact is not reliably preserved.
            copy(self, program, src=self.source_folder, dst=bindir,
                 keep_path=False)
            packaged = os.path.join(bindir, program)
            os.chmod(packaged, 0o755)
            self._sign_ohos(packaged)

        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        # The example configuration is the documented starting point for a
        # deployment (README: "See how to create a configuration file using the
        # self-commented config file").
        copy(self, "yaku-ns.conf.example",
             src=os.path.join(self.source_folder, "Documentation"),
             dst=os.path.join(self.package_folder, "etc"),
             keep_path=False)

    def package_info(self):
        # Pure executables: no library, no public headers.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["etc"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))