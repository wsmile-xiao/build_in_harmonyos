#!/usr/bin/env python3
"""Conan recipe — RSEM 1.3.3 (RNA-Seq by Expectation-Maximization).

Makefile-based C++ tool suite. Upstream bundles samtools-1.3 (with
htslib-1.3) and a trimmed header-only boost 1.55, so the only external
dependency is zlib.

Build strategy (validated on aarch64-linux-ohos):
  1. samtools-1.3 ships its own ./configure, but its config.status awk
     step fails on HarmonyOS (HMDFS permission) and the `install` helper
     is absent. We therefore write config.mk/config.h directly and run
     `make samtools` with compiler vars from Conan (R33: never ${CC}).
  2. The rsem Makefile is driven with CXX/CXXFLAGS overrides; gnu++98 is
     required because rsem source relies on C++98 implicit istream->
     bool conversion (compiling as C++11 breaks SingleHit.h etc.).
  3. make install is skipped (no `install` helper on OHOS); package()
     copies the artifacts explicitly.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.layout import basic_layout


class RsemConan(ConanFile):
    name = "rsem"
    version = "1.3.3"
    description = "RSEM: accurate transcript quantification from RNA-Seq data"
    license = "GPL-3.0-only"
    homepage = "https://github.com/deweylab/RSEM"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _zlib(self):
        return self.dependencies["zlib"]

    def build(self):
        apply_conandata_patches(self)

        exe = self.conf.get("tools.build:compiler_executables", {}) or {}
        cc = exe.get("c", "clang")
        cxx = exe.get("cpp", "clang++")
        ar = exe.get("ar", "llvm-ar")
        ranlib = exe.get("ranlib", "llvm-ranlib")

        zinfo = self._zlib().cpp_info
        z_inc = zinfo.includedirs[0]
        z_lib = zinfo.libdirs[0]

        src = self.source_folder
        samtools_dir = os.path.join(src, "samtools-1.3")
        htslib_inc = os.path.join("samtools-1.3", "htslib-1.3")

        # --- 1. Write samtools config.mk / config.h (bypasses configure;
        #        its config.status awk step fails on OHOS filesystems).
        #        Base config.mk is regenerated from config.mk.in via the
        #        Makefile's own sed rule, then augmented.
        self.run(f"make -C {samtools_dir} config.mk")
        with open(os.path.join(samtools_dir, "config.mk"), "a") as f:
            f.write(
                "\n# Conan/OHOS overrides (config.status is not usable here)\n"
                f"CC = {cc}\n"
                "CFLAGS = -O2 -Wall\n"
                "CURSES_LIB =\n"
                "LIBS = -lz -lpthread\n"
            )
        self._write_samtools_config_h(samtools_dir)

        # --- 2. Build bundled samtools + htslib (static libhts.a).
        self.run(
            f"make -C {samtools_dir} -f Makefile samtools -j1 "
            f"CC={cc} AR={ar} RANLIB={ranlib} "
            f"CPPFLAGS=-I{z_inc} LDFLAGS=-L{z_lib}"
        )

        # --- 3. Build rsem programs (gnu++98 is required: the source
        #        relies on C++98 implicit istream->bool conversion).
        cxxflags = (
            "-std=gnu++98 -Wall -O2 "
            f"-I. -I{htslib_inc} -I{z_inc}"
        )
        self.run(
            f"make -C {src} -j1 CXX={cxx} "
            f'CXXFLAGS="{cxxflags}" '
            f"LDFLAGS=-L{z_lib} "
        )

    @staticmethod
    def _write_samtools_config_h(samtools_dir):
        """Generate samtools config.h from its config.h.in template.

        All probes default to off; zlib is on (bundled htslib requires it
        and the link probe in the base config.mk guarantees -lz).
        """
        tmpl = os.path.join(samtools_dir, "config.h.in")
        out = os.path.join(samtools_dir, "config.h")
        with open(tmpl) as f:
            body = f.read()
        # Neutralize every #undef probe, then enable what we know is true.
        lines = []
        for line in body.splitlines():
            s = line.strip()
            if s.startswith("#undef "):
                lines.append(f"/* {s} */")
            else:
                lines.append(line)
        lines += [
            "#define HAVE_LIBZ 1",
            '#define PACKAGE_VERSION "1.3"',
        ]
        with open(out, "w") as f:
            f.write("\n".join(lines) + "\n")

    def package(self):
        src = self.source_folder
        bindir = os.path.join(self.package_folder, "bin")

        progs = [
            # PROGS1
            "rsem-extract-reference-transcripts", "rsem-synthesis-reference-transcripts",
            "rsem-preref", "rsem-build-read-index", "rsem-simulate-reads",
            # PROGS2
            "rsem-parse-alignments", "rsem-run-em", "rsem-tbam2gbam", "rsem-bam2wig",
            "rsem-bam2readdepth", "rsem-get-unique", "rsem-sam-validator",
            "rsem-scan-for-paired-end-reads",
            # PROGS3
            "rsem-run-gibbs", "rsem-calculate-credibility-intervals",
            # bundled samtools (installed under the rsem- prefix to avoid
            # clashing with a system samtools, mirroring the make install rule)
            ("samtools-1.3/samtools", "rsem-samtools"),
        ]
        for item in progs:
            if isinstance(item, tuple):
                s, d = item
            else:
                s = d = item
            copy(self, s, src, bindir, keep_path=False)
            copied = os.path.join(bindir, os.path.basename(s))
            if os.path.basename(s) != d:
                shutil.move(copied, os.path.join(bindir, d))

        scripts = [
            "rsem-prepare-reference", "rsem-calculate-expression",
            "rsem-refseq-extract-primary-assembly", "rsem-gff3-to-gtf",
            "rsem-plot-model", "rsem-plot-transcript-wiggles",
            "rsem-gen-transcript-plots", "rsem-generate-data-matrix",
            "rsem-run-ebseq", "rsem-control-fdr", "rsem-generate-ngvector",
            "rsem-run-prsem-testing-procedure",
            "extract-transcript-to-gene-map-from-trinity",
            "convert-sam-for-rsem", "rsem_perl_utils.pm",
        ]
        for s in scripts:
            p = os.path.join(src, s)
            if os.path.isfile(p):
                copy(self, s, src, bindir, keep_path=False)

        for f in os.listdir(bindir):
            os.chmod(os.path.join(bindir, f), 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
