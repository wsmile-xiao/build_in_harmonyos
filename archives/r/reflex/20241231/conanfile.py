#!/usr/bin/env python3
"""Conan recipe for reflex — Thomas Dickey's REFLEX lexical scanner generator.

REFLEX ("relocalizable fast lexical scanner") is the maintainer's fork of
flex 2.5.4.  Upstream installs the scanner generator under a configurable
name prefix (here ``reflex``), so the package ships:

  * ``bin/reflex``    — the scanner generator (drop-in flex)
  * ``bin/reflex++``  — the same generator in C++ mode (``reflex -+``)
  * ``lib/librefl.a`` — the scanner runtime library (``-lfl`` replacement,
                        provides ``main`` and ``yywrap``)
  * ``include/reFlexLexer.h`` — the C++ scanner class interface
  * ``share/man/man1/reflex.1`` — the manual page

HarmonyOS PC (aarch64) build notes
----------------------------------
* The vintage ``config.guess`` in the tarball cannot classify the HongMeng
  kernel ("cannot guess build type; you must specify one"), so configure is
  invoked with explicit ``--build=aarch64-linux-ohos`` /
  ``--host=aarch64-linux-ohos`` triplets.  Both canonicalise to the same
  value, so autoconf keeps ``cross_compiling=no`` and the
  ``@no_cross@``-guarded self-hosting rules (``scan.c`` regeneration, the
  ``check``/``bigcheck`` targets) stay enabled.
* The release ships no top-level ``parse.c``/``parse.h``/``scan.c`` (only the
  bootstrap ``initscan.c``), so a yacc implementation is a genuine build
  requirement: ``bison -y`` generates the option-parser tables.  byacc —
  Alpine's choice of yacc — is not available in the ohpcd registry.
* ``make check`` is the upstream self-hosting regression test: it runs the
  freshly built generator over its own ``scan.l`` and diffs the result
  against the release's pre-generated ``initscan.c``, i.e. it proves the
  generator reproduces the shipped scanner byte for byte.  OHOS refuses to
  execute an ELF without a ``.codesign`` section (E077), so the built binary
  is signed before the test runs and the installed binaries are signed again
  in ``package()``.
* Patch 0001 fixes an upstream skeleton defect that makes *every* generated
  C++ scanner uncompilable; see notes.md for the full evidence chain.
* Patch 0002 plus the ``_pin_tmpdir`` helper keep autoconf's scratch
  directory usable: on a CI worker whose TMPDIR resolves onto HMDFS,
  ``config.status`` cannot write into the directory it just created and the
  build dies with ".../subs.sed: Permission denied".
"""
import os
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ReflexConan(ConanFile):
    name = "reflex"
    version = "20241231"
    description = ("REFLEX - relocalizable fast lexical scanner: a maintained "
                   "flex 2.5.4 fork producing C and C++ scanners")
    license = "BSD-3-Clause-flex"
    homepage = "https://invisible-island.net/reflex/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("lexer", "scanner", "flex", "code-generator", "tokenizer")

    # Upstream builds only the static ``librefl.a`` (no libtool, no shared
    # option); the executable it also installs is declared through the
    # software-level commands.json (R38).  The static-library type satisfies
    # R26 (system-name libraries default to static).
    package_type = "static-library"

    settings = "os", "arch", "compiler", "build_type"

    # Upstream's own ``bigcheck`` target drives exactly these modes, but it
    # starts with a bare ``-C``, which this option parser rejects when the
    # next word is a separate argument (``./flex: unknown -C option '/'``),
    # so the sweep is driven explicitly here and bare ``-C`` is excluded.
    _test_compression_modes = ("-Ce", "-Cm", "-f", "-Cfea", "-CFer", "-l")

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # No generated parser in the tarball -> a yacc is required.
        self.tool_requires("bison/3.8.2")
        # ``make check`` regenerates the scanner and pipes it through diff.
        self.tool_requires("diffutils/3.12")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # -- helpers -------------------------------------------------------

    @staticmethod
    def _gnu_triplet(arch):
        machine = {
            "x86_64": "x86_64",
            "x86": "i686",
            "armv8": "aarch64",
            "armv8_3": "aarch64",
            "armv8_aes": "aarch64",
            "armv8_sha": "aarch64",
            "armv8_crypto": "aarch64",
            "armv9": "aarch64",
            "armv9_aes": "aarch64",
            "armv9_sha": "aarch64",
            "armv9_crypto": "aarch64",
            "riscv64": "riscv64",
            "s390x": "s390x",
            "ppc64le": "powerpc64le",
        }.get(str(arch), str(arch))
        return "{0}-linux-ohos".format(machine)

    @staticmethod
    def _has_ohos_signature(path):
        """True if the ELF already carries a .codesign/.note.ohos section."""
        try:
            with open(path, "rb") as binary:
                data = binary.read()
        except OSError:
            return False
        return b".codesign" in data or b".note.ohos" in data

    def _sign_elf_if_ohos(self, path):
        """OHOS post-install signing (E077); the order is not negotiable:

        copy to tmp -> llvm-objcopy --remove-section .codesign (best effort)
        -> binary-sign-tool sign -selfSign 1 -> move back -> chmod 755.
        """
        if not os.path.isfile(path):
            return
        if self._has_ohos_signature(path):
            os.chmod(path, 0o755)
            return

        signer = (shutil.which("binary-sign-tool")
                  or "/data/service/hnp/bin/binary-sign-tool")
        objcopy = (shutil.which("llvm-objcopy")
                   or "/data/service/hnp/bin/llvm-objcopy")
        if not os.path.isfile(signer) or not os.path.isfile(objcopy):
            raise ConanException(
                "OHOS packaging requires binary-sign-tool and llvm-objcopy")

        tmp_in = "{0}.unsigned".format(path)
        tmp_out = "{0}.signed".format(path)
        shutil.copy2(path, tmp_in)
        subprocess.run(
            [objcopy, "--remove-section", ".codesign", tmp_in],
            capture_output=True,
            timeout=30,
        )
        subprocess.check_call([
            signer, "sign", "-selfSign", "1",
            "-inFile", tmp_in, "-outFile", tmp_out,
            "-signAlg", "SHA256withECDSA",
        ])
        shutil.move(tmp_out, path)
        os.chmod(path, 0o755)
        if os.path.isfile(tmp_in):
            os.unlink(tmp_in)

    def _force_patched_skeleton(self):
        """Keep the patched skel.c in charge of the build.

        The release tarball ships ``skel.c`` and ``flex.skl`` with *identical*
        mtimes, and the two files disagree: ``flex.skl`` still emits
        ``NULL`` where the released ``skel.c`` (and the pre-generated
        ``initscan.c`` derived from it) emits ``(char *) 0``.  Because
        equal timestamps never trigger the ``skel.c: flex.skl`` rule, the
        shipped skel.c is the effective build input — which is exactly where
        patch 0001 lives.  Make that deterministic by forcing the patched
        skel.c strictly newer than flex.skl, in whichever folder the patch
        landed.
        """
        for folder in {self.source_folder, self.build_folder}:
            skel_c = os.path.join(folder, "skel.c")
            if os.path.isfile(skel_c):
                os.utime(skel_c, None)

    @staticmethod
    def _usable_tmpdir(candidate):
        """True if autoconf can really use *candidate* as its scratch root.

        Replays exactly what ``config.status`` does: create a fresh directory
        and immediately redirect into it.  On HMDFS (the /storage user volume
        on device and on CI workers) a just-created directory can come back
        without usable owner permissions, which is what turns every later
        ``> "$tmp"/<file>`` into "Permission denied".  A plain "is it
        writable?" check does not catch that, because the *parent* is fine —
        only a write into a directory we created a moment ago does.
        """
        try:
            os.makedirs(candidate, exist_ok=True)
            previous_umask = os.umask(0o077)
            try:
                probe_dir = tempfile.mkdtemp(dir=candidate)
            finally:
                os.umask(previous_umask)
        except OSError:
            return False
        try:
            probe_file = os.path.join(probe_dir, "probe")
            with open(probe_file, "w") as handle:
                handle.write("ok")
            os.chmod(probe_dir, 0o700)
            with open(probe_file) as handle:
                return handle.read() == "ok"
        except OSError:
            return False
        finally:
            shutil.rmtree(probe_dir, ignore_errors=True)

    def _pin_tmpdir(self):
        """Point TMPDIR at a scratch root that survives the HMDFS quirk.

        A CI worker may hand the build a TMPDIR under the HMDFS user volume
        (``$HOME/.cache/tmp`` was observed), even though the worker itself
        exports a /data path; conan does not set TMPDIR, so whatever the
        build inherits is what configure and config.status get.  Pin it here,
        preferring the /data (non-HMDFS) cache that the CI worker and this
        host both export, and fall back conservatively.
        """
        candidates = [
            os.environ.get("HMBS_TMPDIR"),
            "/data/storage/el2/base/cache",
            os.path.join(os.path.expanduser("~"), "tmp"),
            os.path.join(self.build_folder, "hmbs-tmp"),
            os.environ.get("TMPDIR"),
        ]
        for candidate in candidates:
            if candidate and os.path.isdir(candidate) \
                    and self._usable_tmpdir(candidate):
                for name in ("TMPDIR", "TMP", "TEMP"):
                    os.environ[name] = candidate
                self.output.info(
                    "Using usable TMPDIR={0}".format(candidate))
                return
        self.output.warning(
            "no candidate TMPDIR passed the write-into-fresh-dir probe; "
            "keeping the inherited TMPDIR={0}".format(
                os.environ.get("TMPDIR")))

    # -- build / package -----------------------------------------------

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        if self.settings.os == "OHOS":
            triplet = self._gnu_triplet(self.settings.arch)
            toolchain.configure_args.append("--build={0}".format(triplet))
            toolchain.configure_args.append("--host={0}".format(triplet))
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        self._force_patched_skeleton()

        if self.settings.os == "OHOS":
            # Autoconf's own scratch directory (see _pin_tmpdir) — must be
            # settled before configure runs, config.status inherits it.
            self._pin_tmpdir()

        autotools = Autotools(self)
        autotools.configure()
        autotools.make()

        if self.settings.os == "OHOS":
            # E077: the self-hosting test executes the freshly built generator.
            self._sign_elf_if_ohos(os.path.join(self.build_folder, "flex"))

        # Upstream self-hosting regression test: regenerate the scanner from
        # scan.l with the just-built generator and diff it against the
        # release's initscan.c (copied to scan.c by the .bootstrap rule).
        autotools.make(target="check")

        # Supplementary sweep across the generator's table-compression paths
        # (upstream ``bigcheck`` minus its broken bare ``-C`` first mode).
        # Each mode regenerates scan.c and must reproduce itself exactly.
        for mode in self._test_compression_modes:
            scan_c = os.path.join(self.build_folder, "scan.c")
            if os.path.exists(scan_c):
                os.unlink(scan_c)
            autotools.make(target="check", args=["COMPRESSION={0}".format(mode)])

    def package(self):
        autotools = Autotools(self)
        # Installs into DESTDIR=<package_folder> with the toolchain's default
        # --prefix=/, i.e. package_folder/{bin,lib,include,share/man}.
        autotools.install()

        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

        # E077: both entry points must carry a .codesign section to be
        # executable on the device.
        for executable in ("bin/reflex", "bin/reflex++"):
            self._sign_elf_if_ohos(os.path.join(self.package_folder, executable))

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        # librefl.a is the scanner runtime (the -lfl replacement: it also
        # supplies a default main() and yywrap()).
        self.cpp_info.libs = ["refl"]
        self.cpp_info.bindirs = ["bin"]
        self.buildenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin"))
