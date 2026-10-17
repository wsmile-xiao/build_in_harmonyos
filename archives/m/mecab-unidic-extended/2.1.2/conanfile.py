#!/usr/bin/env python3
"""Conan recipe for mecab-unidic-extended 2.1.2 — UniDic (kana-accent variant)
dictionary + prebuilt binary indices for MeCab.

Unlike mecab-ipadic / mecab-ko-dic (source-data-only packages), this package
REQUIRES mecab at build time: mecab-dict-index compiles the 756,463-entry
lex.csv + 5981x5981 matrix.def into MeCab's binary indices
(sys.dic ~188MB, matrix.bin ~72MB). The package ships both the compiled
indices (ready to load with `mecab -d <pkg>/res/unidic`) and the original
source data (lex.csv, matrix.def, *.def, dicrc) for reproducibility.

Package layout:
  res/unidic/      loadable dictionary (char.bin, matrix.bin, sys.dic,
                   unk.dic, dicrc) — use `mecab -d $UNIDIC_EXT_DICDIR`
  res/unidic-src/  original UTF-8 source data (lex.csv, matrix.def, *.def,
                   dicrc) for reproducibility / re-indexing
  licenses/        COPYING, GPL, LGPL, BSD, AUTHORS, ChangeLog

Build flow (host-side, no cross-compilation of native code):
  source()       download + SHA256 verify the upstream zip
  build()        validate source data (file inventory, 756,463 lex entries,
                 5981x5981 matrix, UTF-8 decode check), then run
                 mecab-dict-index (from the mecab/0.996 tool_require)
                 against the UTF-8 source data and sanity-check the
                 generated indices (existence + size floors).
  package()      copy compiled indices + dicrc + source data + licenses
  package_info() expose the dictionary directory to consumers via the
                 UNIDIC_EXT_DICDIR environment variable (conanrun env).

test_package/ contains a real C++ consumer that links libmecab, loads the
packaged indices via MeCab::create() and checks the tokenization of a
Japanese sentence against a golden output — the full consumer path a
HarmonyOS NLP application would exercise.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class MecabUnidicExtendedConan(ConanFile):
    name = "mecab-unidic-extended"
    version = "2.1.2"
    description = "UniDic 2.1.2 (kana-accent) dictionary + compiled MeCab indices"
    license = "GPL-2.0-or-later", "LGPL-2.1-or-later", "BSD-3-Clause"
    homepage = "https://clrd.ninjal.ac.jp/unidic/"
    url = "https://clrd.ninjal.ac.jp/unidic/"

    # Data + prebuilt-index package: indices are compiled by the mecab
    # tool_require; no C/C++ code is built from this recipe. Like the other
    # dictionary packages (mecab-ipadic, mecab-ko-dic) no package_type is
    # declared; the binary indices are architecture-dependent, so the four
    # settings below participate in the package id (also required by the
    # CI L0p gate).
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # mecab-dict-index (and the libmecab it links) come from the mecab
        # package, resolved against the build profile. On the HarmonyOS PC
        # the build runs on-device, so the OHOS mecab tool executes natively
        # and emits indices loadable by the OHOS libmecab (same endianness /
        # dictionary format).
        self.tool_requires("mecab/0.996")

    def layout(self):
        basic_layout(self)

    def source(self):
        # Strict source integrity: download the upstream NINJAL release zip
        # (dotsrc.org mirror first — the canonical clrd.ninjal.ac.jp host is
        # often unreachable) with SHA256 verification. Pre-populated data is
        # NOT accepted as a bypass.
        import socket
        socket.setdefaulttimeout(30)
        get(self, **self.conan_data["sources"], strip_root=True)
        self.output.info("Source downloaded and SHA256 verified from upstream mirror")

    def build(self):
        apply_conandata_patches(self)

        srcdir = self.source_folder
        self.output.info("=== mecab-unidic-extended source data integrity check ===")

        # Official unidic-mecab_kana-accent-2.1.2_src.zip data inventory.
        # NOTE: the upstream zip ships NO pos-id.def and NO model.def —
        # mecab-dict-index falls back to a minimal pos-id table (verified
        # on-device: "minimum setting is used" warning, exit code 0).
        required = ["lex.csv", "matrix.def", "char.def", "unk.def", "rewrite.def",
                    "feature.def", "left-id.def", "right-id.def", "dicrc"]
        for fname in required:
            fpath = os.path.join(srcdir, fname)
            assert os.path.isfile(fpath), f"Missing: {fname}"
            assert os.path.getsize(fpath) > 0, f"Empty: {fname}"
        self.output.info(f"  Required data files: {len(required)} present")

        # lex.csv: exactly 756,463 entries (official 2.1.2 release)
        with open(os.path.join(srcdir, "lex.csv"), encoding="utf-8") as f:
            lex_lines = sum(1 for _ in f)
        self.output.info(f"  lex.csv entries: {lex_lines}")
        assert lex_lines == 756463, f"lex.csv: {lex_lines} != 756463"

        # matrix.def: 5981x5981 connection cost matrix
        with open(os.path.join(srcdir, "matrix.def"), encoding="utf-8") as f:
            header = f.readline().strip()
        assert header == "5981 5981", f"matrix.def header: {header!r} != '5981 5981'"
        self.output.info("  matrix.def: 5981x5981")

        # UTF-8 encoding validation (UniDic 2.1.2 kana-accent is UTF-8)
        for fname in required:
            with open(os.path.join(srcdir, fname), encoding="utf-8") as f:
                f.read()
        self.output.info(f"  UTF-8 validation: {len(required)}/{len(required)} OK")

        # --- compile binary indices with mecab-dict-index (mecab tool_require) ---
        mecab = self.dependencies.build["mecab"]
        dict_index = os.path.join(mecab.package_folder, "libexec", "mecab", "mecab-dict-index")
        assert os.path.isfile(dict_index), f"mecab-dict-index not found: {dict_index}"

        dicdir = os.path.join(self.build_folder, "dic")
        os.makedirs(dicdir, exist_ok=True)
        self.output.info(f"Compiling UniDic indices with {dict_index}")
        self.run(f'"{dict_index}" -d "{srcdir}" -o "{dicdir}" -f utf8 -t utf8')

        # mecab-dict-index does not copy dicrc into the output directory, but
        # the runtime dictionary dir needs it (output format / cost config).
        copy(self, "dicrc", src=srcdir, dst=dicdir)

        # --- sanity-check the generated indices ---
        # Expected sizes from a verified on-device build:
        #   sys.dic ~188MB, matrix.bin ~72MB, char.bin ~256KB, unk.dic ~5KB
        min_sizes = {
            "sys.dic": 100 * 1024 * 1024,
            "matrix.bin": 30 * 1024 * 1024,
            "char.bin": 100000,
            "unk.dic": 4000,
        }
        for fname, minimum in min_sizes.items():
            fpath = os.path.join(dicdir, fname)
            assert os.path.isfile(fpath), f"Generated index missing: {fname}"
            size = os.path.getsize(fpath)
            self.output.info(f"  Generated: {fname} ({size:,} bytes)")
            assert size >= minimum, f"{fname}: {size} < {minimum}"
        assert os.path.isfile(os.path.join(dicdir, "dicrc")), "dicrc missing from dicdir"

        self.output.info("=== mecab-unidic-extended integrity check PASSED ===")

    def package(self):
        srcdir = self.source_folder
        dicdir = os.path.join(self.build_folder, "dic")

        # Loadable dictionary: binary indices + dicrc
        for fname in ("char.bin", "matrix.bin", "sys.dic", "unk.dic", "dicrc"):
            copy(self, fname, src=dicdir, dst=os.path.join(self.package_folder, "res", "unidic"))

        # Original source data for reproducibility / re-indexing
        for pattern in ("*.csv", "*.def", "dicrc"):
            copy(self, pattern, src=srcdir, dst=os.path.join(self.package_folder, "res", "unidic-src"))

        # Licenses
        for lic in ("COPYING", "GPL", "LGPL", "BSD", "AUTHORS", "ChangeLog"):
            copy(self, lic, src=srcdir, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        dicdir = os.path.join(self.package_folder, "res", "unidic")
        self.runenv_info.define("UNIDIC_EXT_DICDIR", dicdir)
        self.output.info(f"UniDic extended dictionary directory: {dicdir}")
        self.output.info("  Use: mecab -d $UNIDIC_EXT_DICDIR")
