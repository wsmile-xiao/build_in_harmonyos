#!/usr/bin/env python3
"""test_package for PLINK 1.07 — real functional tests of the shipped binary.

The binary under test is an OHOS aarch64 (musl) ELF. On the CI worker it runs
natively; on a non-aarch64 host it is executed through qemu-aarch64. The
artefacts are all static, so no target sysroot is required for emulation.

Every assertion below inspects real output produced by a real PLINK run: no
echo/print placeholders, no stub assertions (R34). Columns are resolved by
header name rather than by fixed index so a formatting change surfaces as a
readable failure instead of silently comparing the wrong field.
"""
import os
import platform
import re
import shutil
import struct
import subprocess
import sys
import tempfile

PKG = sys.argv[1]
BIN = os.path.join(PKG, "bin", "plink")
DATA = os.path.join(PKG, "share", "plink")

RESULTS = []


def check(ok, label):
    RESULTS.append((bool(ok), label))
    print("  [%s] %s" % ("PASS" if ok else "FAIL", label))
    return bool(ok)


def runner():
    """Build an argv prefix that can execute the aarch64/musl binary on this host."""
    if platform.machine() in ("aarch64", "arm64"):
        return [BIN]
    qemu = shutil.which("qemu-aarch64") or shutil.which("qemu-aarch64-static")
    if not qemu:
        raise SystemExit(
            "cannot execute the aarch64 binary: host is %s and no qemu-aarch64 on PATH"
            % platform.machine()
        )
    return [qemu, BIN]


def plink(workdir, *args):
    proc = subprocess.run(
        runner() + ["--noweb"] + list(args), cwd=workdir, capture_output=True, text=True
    )
    return proc


def read_table(path):
    """Return (column_index_by_name, rows_as_dicts) for a whitespace PLINK table."""
    with open(path) as fh:
        lines = [ln for ln in fh.read().splitlines() if ln.strip()]
    header = lines[0].split()
    index = {name: i for i, name in enumerate(header)}
    return index, [dict(zip(header, ln.split())) for ln in lines[1:]]


# ---------------------------------------------------------------- T1
# HarmonyOS-specific: the artefact really is an aarch64 ELF, and it really
# executes on this platform (native on the OHOS worker, emulated elsewhere).
print("T1 aarch64 ELF identity and executability")
with open(BIN, "rb") as fh:
    ident = fh.read(20)
    fh.seek(18)
    e_machine = struct.unpack("<H", fh.read(2))[0]
check(ident[:4] == b"\x7fELF", "T1.1 ELF magic present")
check(ident[4] == 2, "T1.2 ELF64 (EI_CLASS=2)")
check(e_machine == 183, "T1.3 e_machine=EM_AARCH64 (183), got %d" % e_machine)

work = tempfile.mkdtemp(prefix="plink-test-")
shutil.copy(os.path.join(DATA, "test.ped"), work)
shutil.copy(os.path.join(DATA, "test.map"), work)

# --help is the invocation that exits 0; --version prints the banner but then
# falls through to the argument parser and exits 1 upstream (PLINK 1.07 quirk).
proc = plink(work, "--help")
check(proc.returncode == 0, "T1.4 binary executes on this platform (--help rc=0)")

proc = plink(work, "--version")
check("PLINK!" in proc.stdout, "T1.5 banner printed")
check("v1.07" in proc.stdout, "T1.6 reports version v1.07")

# ---------------------------------------------------------------- T2
print("T2 --freq allele frequency computation")
proc = plink(work, "--file", "test", "--freq")
check(proc.returncode == 0, "T2.1 rc=0")
check("Writing allele frequencies" in proc.stdout, "T2.2 reports writing frequencies")
idx, rows = read_table(os.path.join(work, "plink.frq"))
check(idx == {"CHR": 0, "SNP": 1, "A1": 2, "A2": 3, "MAF": 4, "NCHROBS": 5},
      "T2.3 .frq header schema")
check(len(rows) == 2, "T2.4 exactly 2 SNP rows, got %d" % len(rows))
check(rows[0]["SNP"] == "snp1" and rows[0]["MAF"] == "0.3333", "T2.5 snp1 MAF=0.3333")
check(rows[0]["NCHROBS"] == "12", "T2.6 snp1 NCHROBS=12 (6 samples x 2 haplotypes)")
check(rows[1]["SNP"] == "snp2" and rows[1]["MAF"] == "0.4167", "T2.7 snp2 MAF=0.4167")
check(rows[1]["NCHROBS"] == "12", "T2.8 snp2 NCHROBS=12")

# ---------------------------------------------------------------- T3
print("T3 --assoc case-control association statistics")
proc = plink(work, "--file", "test", "--assoc")
check(proc.returncode == 0, "T3.1 rc=0")
check("Writing main association results" in proc.stdout, "T3.2 reports writing results")
idx, rows = read_table(os.path.join(work, "plink.assoc"))
check(idx == {"CHR": 0, "SNP": 1, "BP": 2, "A1": 3, "F_A": 4, "F_U": 5,
              "A2": 6, "CHISQ": 7, "P": 8, "OR": 9}, "T3.3 .assoc header schema")
check(len(rows) == 2, "T3.4 exactly 2 association rows, got %d" % len(rows))
check(rows[0]["SNP"] == "snp1" and rows[0]["CHISQ"] == "1.5", "T3.5 snp1 CHISQ=1.5")
check(rows[0]["P"] == "0.2207", "T3.6 snp1 P=0.2207")
check(rows[1]["SNP"] == "snp2" and rows[1]["CHISQ"] == "3.086", "T3.7 snp2 CHISQ=3.086")
check(rows[1]["P"] == "0.07898", "T3.8 snp2 P=0.07898")

# ---------------------------------------------------------------- T4
print("T4 --make-bed binary format conversion")
proc = plink(work, "--file", "test", "--make-bed")
check(proc.returncode == 0, "T4.1 rc=0")
bed = os.path.join(work, "plink.bed")
check(os.path.isfile(bed), "T4.2 plink.bed written")
if os.path.isfile(bed):
    with open(bed, "rb") as fh:
        check(fh.read(3) == b"\x6c\x1b\x01", "T4.3 .bed magic 0x6c 0x1b 0x01 (SNP-major mode)")
bim_lines = [ln.split() for ln in open(os.path.join(work, "plink.bim")).read().splitlines() if ln.strip()]
check(bim_lines == [["1", "snp1", "0", "1", "A", "C"], ["1", "snp2", "0", "2", "G", "T"]],
      "T4.4 .bim rows match the source .map")
fam_lines = [ln for ln in open(os.path.join(work, "plink.fam")).read().splitlines() if ln.strip()]
check(len(fam_lines) == 6, "T4.5 .fam holds 6 samples")

# ---------------------------------------------------------------- T5
print("T5 round-trip: re-read the generated binary genotypes")
proc = plink(work, "--bfile", "plink", "--freq")
check(proc.returncode == 0, "T5.1 rc=0")
idx_bed, rows_bed = read_table(os.path.join(work, "plink.frq"))
check(len(rows_bed) == 2, "T5.2 2 SNP rows read back from .bed")
check([r["MAF"] for r in rows_bed] == ["0.3333", "0.4167"],
      "T5.3 BED-derived MAFs equal the PED-derived MAFs")

# ---------------------------------------------------------------- T6
print("T6 error handling for bad input")
proc = plink(work, "--summarize")
check(proc.returncode != 0, "T6.1 unsupported option exits non-zero (rc=%d)" % proc.returncode)
check("ERROR: Problem parsing the command line arguments." in proc.stderr,
      "T6.2 reports a command-line parse error on stderr")
proc = plink(work, "--file", "nosuch")
check(proc.returncode != 0, "T6.3 missing dataset exits non-zero (rc=%d)" % proc.returncode)
check("No file [ nosuch.ped ] exists." in proc.stderr, "T6.4 names the missing file")

# ---------------------------------------------------------------- T7
# The declared zlib dependency must really be linked into the artefact:
# zlib stamps its version into the inflate/deflate banner strings.
print("T7 declared zlib dependency is genuinely linked")
with open(BIN, "rb") as fh:
    blob = fh.read()
m_inf = re.search(rb"inflate (\d+\.\d+\.\d+) Copyright", blob)
m_def = re.search(rb"deflate (\d+\.\d+\.\d+) Copyright", blob)
check(m_inf is not None, "T7.1 zlib inflate banner present in the binary")
check(m_def is not None, "T7.2 zlib deflate banner present in the binary")
if m_inf and m_def:
    check(m_inf.group(1) == m_def.group(1),
          "T7.3 inflate/deflate versions agree (%s / %s)"
          % (m_inf.group(1).decode(), m_def.group(1).decode()))

shutil.rmtree(work, ignore_errors=True)

# ---------------------------------------------------------------- summary
total = len(RESULTS)
failed = [label for ok, label in RESULTS if not ok]
print("")
print("assertions: %d, passed: %d, failed: %d" % (total, total - len(failed), len(failed)))
for label in failed:
    print("  FAILED: %s" % label)
sys.exit(1 if failed else 0)
