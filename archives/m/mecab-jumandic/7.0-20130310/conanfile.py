#!/usr/bin/env python3
"""Conan recipe for mecab-jumandic 7.0-20130310 — Japanese JumanDic dictionary for MeCab.

NLP dictionary data package. Source data (16 CSV + 9 DEF + dicrc, UTF-8 encoded
with 4 files containing upstream-inherited truncated-UTF-8 line endings that
mecab-dict-index tolerates, as does the unpatched Debian package) is downloaded
from the Debian official mirror of the upstream release tarball via conandata.yml
(SHA256 verified).

Binary indices (char.bin, matrix.bin, sys.dic, unk.dic) are generated
deterministically in build() by mecab-dict-index from tool_requires("mecab/0.996")
— the OHOS binary of mecab-dict-index runs natively on the OHOS aarch64 build
host and produces target-compatible dictionary binaries (verified: sys.dic from
this exact recipe stack was consumed by libmecab on OHOS with correct Japanese
morphological analysis output).

OHOS-specific runtime note (E-usable): mecab's default rcfile is the build-time
hardcoded MECAB_DEFAULT_RC "//etc/mecabrc", which does not exist on OHOS's
read-only rootfs. Consumers MUST pass "--rcfile <dicdir>/dicrc" (the dicrc
shipped in this package's dic/ dir) when creating the tagger, e.g.
  mecab_new2("-d <dicdir> --rcfile <dicdir>/dicrc").
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout


class MecabJumandicConan(ConanFile):
    name = "mecab-jumandic"
    version = "7.0-20130310"
    description = "mecab-jumandic — Japanese JumanDic dictionary data for MeCab (morphological analysis)"
    license = "BSD-3-Clause"
    homepage = "https://taku910.github.io/mecab/"
    url = "https://taku910.github.io/mecab/"

    # Data/dictionary package — no C/C++ compilation of this package's own code.
    # settings 保留四项以满足 CI L0p 门禁（数据包构建无编译，实际不依赖编译器）。
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        # Exports recipe-adjacent data per repo convention (conandata-driven;
        # no patches for this version — see conandata.yml patches: []).
        from conan.tools.files import export_conandata_patches
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def build_requirements(self):
        # Deterministic binary index generation: mecab-dict-index from the
        # archived mecab/0.996 (OHOS aarch64 native binary) compiles the CSV
        # dictionary into char.bin/matrix.bin/model.bin/sys.dic/unk.dic.
        self.tool_requires("mecab/0.996")

    def source(self):
        # Strict source integrity: download the upstream release tarball
        # (Debian official mirror; upstream canonical hosting is the Google
        # Drive link on taku910.github.io — unstable for automated builds)
        # with SHA256 verification. Pre-populated data is NOT accepted.
        src_data = self.conan_data["sources"]
        import socket
        socket.setdefaulttimeout(30)
        get(self, **src_data, strip_root=True)
        self.output.info("Source downloaded and SHA256 verified from Debian mirror")

    def build(self):
        # No patches for this version (patches: [] in conandata.yml) — the
        # apply_conandata_patches call is kept per repo convention so a future
        # patch entry in conandata.yml is picked up automatically.
        from conan.tools.files import apply_conandata_patches
        apply_conandata_patches(self)

        srcdir = self.source_folder
        csv_files = sorted([f for f in os.listdir(srcdir) if f.endswith('.csv')])
        def_files = sorted([f for f in os.listdir(srcdir) if f.endswith('.def')])
        has_dicrc = os.path.isfile(os.path.join(srcdir, 'dicrc'))

        self.output.info("=== mecab-jumandic source data integrity check ===")
        self.output.info(f"  CSV files: {len(csv_files)}")
        self.output.info(f"  DEF files: {len(def_files)}")
        self.output.info(f"  dicrc: {'YES' if has_dicrc else 'MISSING!'}")

        # Official release: 16 CSV + 9 DEF + dicrc
        assert len(csv_files) == 16, f"Expected 16 CSV, got {len(csv_files)}"
        assert len(def_files) == 9, f"Expected 9 DEF, got {len(def_files)}"
        assert has_dicrc, "dicrc is missing"

        # Core CSV files exist and have entries
        core_csv = ['ContentW.csv', 'Wikipedia.csv', 'Auto.csv', 'Noun.koyuu.csv', 'Suffix.csv']
        for fname in core_csv:
            fpath = os.path.join(srcdir, fname)
            assert os.path.isfile(fpath), f"Missing: {fname}"
            with open(fpath, encoding='utf-8', errors='replace') as f:
                lines = sum(1 for _ in f)
            self.output.info(f"    {fname}: {lines} entries")
            assert lines > 0, f"{fname} is empty"

        # Official release DEF files
        core_def = ['char.def', 'feature.def', 'left-id.def', 'matrix.def',
                    'model.def', 'pos-id.def', 'rewrite.def', 'right-id.def', 'unk.def']
        for fname in core_def:
            assert os.path.isfile(os.path.join(srcdir, fname)), f"Missing: {fname}"

        # Total CSV line count (official release: 751,185)
        total_lines = 0
        for fname in csv_files:
            fpath = os.path.join(srcdir, fname)
            with open(fpath, encoding='utf-8', errors='replace') as f:
                total_lines += sum(1 for _ in f)
        self.output.info(f"  Total CSV lines: {total_lines}")
        assert total_lines == 751185, f"Expected 751185 total lines, got {total_lines}"

        # UTF-8 encoding validation. NOTE: the upstream release tarball ships 4
        # files (AuxV.csv, left-id.def, right-id.def, model.def) whose final
        # field of ~2937 lines ends with a truncated 2-byte UTF-8 sequence
        # (\xe3\x81 without the 3rd byte). This is upstream-inherited data:
        # Debian's unpatched package ships it as-is and mecab-dict-index
        # tolerates it (compiles successfully, output verified). We therefore
        # validate that the remaining 21 files are strictly UTF-8 clean and
        # that the 4 known-quirky files stay within the expected bad-line
        # budget — deviation from upstream byte-content is NOT patched, to
        # keep the data identical to the official release.
        expected_bad = {'AuxV.csv': 6, 'left-id.def': 6, 'right-id.def': 6, 'model.def': 2919}
        bad_ok = 0
        bad_fail = 0
        for fname in csv_files + def_files + ['dicrc']:
            fpath = os.path.join(srcdir, fname)
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    f.read()
            except UnicodeDecodeError:
                # count invalid lines
                bad_lines = 0
                with open(fpath, 'rb') as f:
                    for raw in f:
                        try:
                            raw.decode('utf-8')
                        except UnicodeDecodeError:
                            bad_lines += 1
                if fname in expected_bad and bad_lines == expected_bad[fname]:
                    self.output.info(f"  UTF-8 quirk (upstream-inherited): {fname} — {bad_lines} truncated-sequence lines, as in official release")
                    bad_ok += 1
                else:
                    self.output.warning(f"UTF-8 UNEXPECTED: {fname} — {bad_lines} bad lines (expected {expected_bad.get(fname, 0)})")
                    bad_fail += 1
        self.output.info(f"  UTF-8 validation: {bad_fail} unexpected failures")
        assert bad_fail == 0, f"{bad_fail} files have unexpected UTF-8 deviations"

        # Deterministic binary index generation via tool_requires mecab/0.996
        self._build_indices(srcdir)

        self.output.info("=== mecab-jumandic integrity check PASSED ===")

    def _build_indices(self, srcdir):
        """Generate binary indices with mecab-dict-index from the mecab/0.996
        tool dependency (OHOS aarch64 native binary)."""
        import subprocess
        dep = self.dependencies.build["mecab"]
        dict_index = os.path.join(dep.package_folder, "libexec", "mecab", "mecab-dict-index")
        assert os.path.isfile(dict_index) and os.access(dict_index, os.X_OK), \
            f"mecab-dict-index not found in mecab/0.996 package: {dict_index}"

        # JumanDic is UTF-8 (dicrc uses no explicit config-charset; upstream
        # Makefile.am compiles with -f utf-8 -t @CHARSET@ where CHARSET=utf-8)
        outdir = os.path.join(self.build_folder, "dic")
        os.makedirs(outdir, exist_ok=True)
        result = subprocess.run(
            [dict_index, '-d', srcdir, '-o', outdir, '-f', 'utf-8', '-t', 'utf-8'],
            capture_output=True, text=True, timeout=1800
        )
        if result.returncode != 0:
            self.output.error(f"mecab-dict-index failed (RC={result.returncode}): {result.stderr[-500:]}")
            raise Exception("mecab-dict-index binary index generation failed")

        binary_files = ['char.bin', 'matrix.bin', 'model.bin', 'sys.dic', 'unk.dic']
        for fname in binary_files:
            fpath = os.path.join(outdir, fname)
            assert os.path.isfile(fpath) and os.path.getsize(fpath) > 0, \
                f"Binary index not generated: {fname}"
            self.output.info(f"  Generated: {fname} ({os.path.getsize(fpath)} bytes)")

        # dicrc must be installed alongside the binary indices: mecab's
        # load_dictionary_resource() (utils.cpp:384-388) loads <dicdir>/dicrc
        # and fails without it. Copy it next to the .bin files.
        copy(self, "dicrc", src=srcdir, dst=outdir)

    def package(self):
        # Copy source data files (CSV, DEF, dicrc)
        copy(self, "*.csv", src=self.source_folder, dst=os.path.join(self.package_folder, "dic"))
        copy(self, "*.def", src=self.source_folder, dst=os.path.join(self.package_folder, "dic"))
        copy(self, "dicrc", src=self.source_folder, dst=os.path.join(self.package_folder, "dic"))

        # Copy generated binary indices (deterministic, from build/dic/)
        bdir = os.path.join(self.build_folder, "dic")
        for fname in ['char.bin', 'matrix.bin', 'model.bin', 'sys.dic', 'unk.dic']:
            fpath = os.path.join(bdir, fname)
            if os.path.isfile(fpath):
                copy(self, fname, src=bdir, dst=os.path.join(self.package_folder, "dic"))

        # Copy license
        for lic in ['COPYING', 'LICENSE', 'LICENSE.txt']:
            fpath = os.path.join(self.source_folder, lic)
            if os.path.isfile(fpath):
                copy(self, lic, src=self.source_folder, dst=os.path.join(self.package_folder, "lic"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        dic_dir = os.path.join(self.package_folder, "dic")
        self.output.info(f"Dictionary installed to: {dic_dir}")
        self.output.info(f"  Use: mecab -d {dic_dir} --rcfile {dic_dir}/dicrc")
        self.output.info("  (OHOS: --rcfile is REQUIRED — default //etc/mecabrc does not exist on read-only rootfs)")
