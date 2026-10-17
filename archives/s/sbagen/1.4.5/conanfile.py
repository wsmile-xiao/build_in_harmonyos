#!/usr/bin/env python3
"""Conan recipe — sbagen 1.4.5 (single-file C CLI; upstream ships `mk` scripts, no configure/Makefile).

SBaGen (Sequenced Binaural Beat Generator) by Jim Peters synthesises binaural
beats in real time from tone-specs, sequence files (*.sbg) or predefined
sequences, and can mix them with an existing audio file.  Output goes to the
OSS device (/dev/dsp) where available, otherwise to a raw/WAV file or pipe.

Upstream: https://uazu.net/sbagen/

Adaptation notes for HarmonyOS PC (aarch64) — full exploration log in notes.md:
  * Zero third-party dependencies: sbagen.c uses libc/libm only.  MP3/OGG mixing
    would need libmad + libvorbisidec (tremor); tremor is not published in the
    OHOS registry (R36), so the optional decoders stay disabled.  For such
    inputs the CLI reports "Ogg/MP3 support wasn't compiled into this
    executable"; the core feature set (sequence synthesis, raw/WAV output,
    wav/raw mixing) is fully functional.
  * HarmonyOS provides no OSS audio device (no /dev/dsp).  Upstream covers this
    case itself with the T_POSIX target (mk-nodevdsp: `cc -DT_POSIX ...`), which
    defines NO_AUDIO and routes output to file/pipe only; running without -o
    prints an explicit hint.  No source patch is needed for the adaptation.
  * Upstream has no configure/Makefile, only `mk`-family scripts whose shebang
    points at /bin/bash (absent on OHOS) and which default to -m32.  The recipe
    does not run them and invokes the compiler directly, following the
    mk-nodevdsp command line.
  * The tarball bundles a 32-bit x86 prebuilt `sbagen` binary plus libs/*.a
    (x86 and 32-bit ARM) — foreign architectures, never packaged; the recipe
    builds from sbagen.c into the build folder instead.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout

# Documentation shipped by the upstream tarball (SBAGEN.txt is the manual;
# mk-msvc.txt / readme-windows.txt are Windows build notes and are skipped).
DOCS = (
    "COPYING.txt",
    "README.txt",
    "ChangeLog.txt",
    "TODO.txt",
    "SBAGEN.txt",
    "focus.txt",
    "focus2.txt",
    "holosync.txt",
    "theory.txt",
    "theory2.txt",
    "wave.txt",
)


class SbagenConan(ConanFile):
    name = "sbagen"
    version = "1.4.5"
    description = (
        "Sequenced Binaural Beat Generator: synthesises binaural beats from "
        "tone-specs, sequence files or predefined sequences and writes raw/WAV "
        "audio to a file or pipe"
    )
    license = "GPL-2.0-only"  # per upstream source header ("GNU GPL v2")
    homepage = "https://uazu.net/sbagen/"
    url = ("https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/"
           "tree/main/archives/s/sbagen/1.4.5")

    package_type = "application"  # ships the sbagen CLI tool
    languages = "C"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        # 本配方无补丁（平台适配依赖上游内置的 T_POSIX 目标宏，见模块 docstring），
        # 保留导出钩子以维持与其他配方一致的配方结构。
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # 无补丁时为空操作；保留调用以维持配方结构（conandata.yml 的 patches 为空表）。
        apply_conandata_patches(self)

        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "sbagen is a POSIX CLI tool; the T_POSIX target covers Linux/OHOS"
            )

        # E002: the OHOS target machine has a read-only /tmp, so the compiler
        # needs an explicitly writable temporary directory.
        tmpdir = os.environ.get("TMPDIR")
        if not tmpdir or not os.path.isdir(tmpdir) or not os.access(tmpdir, os.W_OK):
            tmpdir = os.path.join(self.build_folder, "tmp")
            os.makedirs(tmpdir, exist_ok=True)
            os.environ["TMPDIR"] = tmpdir

        # R33: take the compiler from the Conan toolchain, never bare ${CC}.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c") or "clang"

        # Upstream mk-nodevdsp: `cc -DT_POSIX -Wall -O3 -s -lm sbagen.c -o sbagen`.
        # T_POSIX == NO_AUDIO + UNIX_TIME + UNIX_MISC, i.e. file/pipe output only.
        # R9: single translation unit, no parallel make to worry about.
        src = os.path.join(self.source_folder, "sbagen.c")
        cmd = ('{cc} -DT_POSIX -D_GNU_SOURCE -Wall -O2 "{src}" -o sbagen -lm -lpthread'
               .format(cc=cc, src=src))
        self.output.info("building: " + cmd)
        self.run(cmd)

    def package(self):
        # Only the binary we just built: the upstream tarball's prebuilt
        # `sbagen` (ELF 32-bit i386) and libs/*.a stay out of the package.
        copy(self, "sbagen", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"))
        doc_dir = os.path.join(self.package_folder, "share", "doc", "sbagen")
        for doc in DOCS:
            copy(self, doc, src=self.source_folder, dst=doc_dir)
        copy(self, "*.sbg", src=os.path.join(self.source_folder, "examples"),
             dst=os.path.join(self.package_folder, "share", "sbagen", "examples"))
        copy(self, "*", src=os.path.join(self.source_folder, "scripts"),
             dst=os.path.join(self.package_folder, "share", "sbagen", "scripts"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share/sbagen"]
