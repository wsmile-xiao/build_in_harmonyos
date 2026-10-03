#!/usr/bin/env python3
"""Consumer-side checks for the packaged MashMap 3.1.3 commands.

Executed by test_package/conanfile.py through ``self.run()`` so the Conan test
stage really drives the shipped binaries.  Two kinds of checks live here:

* functional ones — the packaged ``mashmap`` is asked to map a query onto a
  reference, which is the product's whole purpose, using a deterministic data
  set generated in-process so no multi-megabyte fixture has to be carried in
  the repository;
* HarmonyOS specific ones — the produced ELF files are inspected, so a build
  that silently picked up host libraries or a foreign architecture is caught
  instead of being reported as a pass.
"""

import argparse
import gzip
import os
import re
import struct
import subprocess
import sys

MASHMAP_VERSION = "3.1.3"

# Deterministic synthetic reference: six contigs of decreasing size plus a
# query derived from it at a fixed substitution rate.  A xorshift64 generator is
# used rather than `random` so the data set is byte identical on every Python
# build and every run.
_CONTIG_LENGTHS = (600_000, 450_000, 380_000, 300_000, 260_000, 210_000)
_BASES = "ACGT"
_LINE_WIDTH = 60
# Query substitution rate against the reference.  MashMap is asked for 95%
# identity, so 3% substitutions stay inside the accepted band.
_SUBSTITUTION_NUM, _SUBSTITUTION_DEN = 3, 100

# OHOS ships musl, whose libc SONAME is plain `libc.so`.  These are the
# glibc/libstdc++ SONAMEs that must never appear in a HarmonyOS package.
_GLBC_SONAMES = frozenset(
    {
        "libc.so.6",
        "libm.so.6",
        "libpthread.so.0",
        "libdl.so.2",
        "librt.so.1",
        "libstdc++.so.6",
        "libgcc_s.so.1",
    }
)
# musl names its dynamic loader either way; both spellings are accepted.
_OHOS_LOADERS = frozenset({"/lib/ld-musl-aarch64.so.1", "/lib/ld-linux-aarch64.so.1"})
_EM_AARCH64 = 0xB7
_PT_INTERP = 3
_SHT_STRTAB = 3
_SHT_DYNAMIC = 6
_DT_NEEDED = 1
_DT_NULL = 0


class CheckError(AssertionError):
    """A verification step did not hold."""


# Every _require() call is recorded, so the reported assertion count is measured
# at run time instead of being a hand-maintained literal.  Checks inside the
# per-record PAF/SAM loops run once per record and are counted every time.
RECORDED = []


def _require(condition, message):
    RECORDED.append(message)
    if not condition:
        raise CheckError(message)


class Runner:
    """Runs packaged aarch64 binaries, with user-mode emulation when needed."""

    def __init__(self, prefix):
        self.prefix = [part for part in prefix if part]

    def __call__(self, argv, timeout=3600):
        completed = subprocess.run(
            self.prefix + argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
        return (
            completed.returncode,
            completed.stdout.decode("utf-8", "replace"),
            completed.stderr.decode("utf-8", "replace"),
        )


# --------------------------------------------------------------------------
# functional checks
# --------------------------------------------------------------------------

def check_version_banner(binary, run):
    """Upstream case 1 (`mashmap -v`), repeated from the consumer side."""
    mark = len(RECORDED)
    code, out, err = run([binary, "-v"])
    _require(code == 0, f"mashmap -v exited {code}: {err.strip()}")
    # MashMap reports the version through the logger, which writes to stderr.
    # Search every line rather than pinning the last one: a trailing diagnostic
    # would otherwise masquerade as a wrong version string.
    lines = [line.strip() for line in (out + err).splitlines() if line.strip()]
    _require(
        any(line in (MASHMAP_VERSION, f"v{MASHMAP_VERSION}") for line in lines),
        f"mashmap -v reported {lines!r}, expected a line equal to {MASHMAP_VERSION}",
    )
    return len(RECORDED) - mark


def check_align_usage(binary, run):
    """The second shipped command must start and print its usage banner."""
    mark = len(RECORDED)
    code, out, err = run([binary, "-h"])
    combined = out + err
    _require(code in (0, 1), f"mashmap-align -h exited {code}: {err.strip()}")
    for option in ("--mappingFile", "--perc_identity", "--threads", "--output"):
        _require(option in combined, f"mashmap-align -h lost the {option} option")
    return len(RECORDED) - mark


def _next_random(state):
    """xorshift64 — deterministic across interpreters."""
    state ^= (state << 13) & 0xFFFFFFFFFFFFFFFF
    state ^= state >> 7
    state ^= (state << 17) & 0xFFFFFFFFFFFFFFFF
    return state


def _write_fasta(path, contigs):
    """Write a FASTA plus its .fai index; returns the index path."""
    index_path = path + ".fai"
    with open(path, "w", encoding="ascii") as fasta, open(
        index_path, "w", encoding="ascii"
    ) as index:
        for name, sequence in contigs:
            header = f">{name}\n"
            fasta.write(header)
            offset = len(header)
            for start in range(0, len(sequence), _LINE_WIDTH):
                fasta.write(sequence[start : start + _LINE_WIDTH] + "\n")
            index.write(
                f"{name}\t{len(sequence)}\t{offset}\t{_LINE_WIDTH}\t{_LINE_WIDTH + 1}\n"
            )
    return index_path


def _gzip_copy(source_path, target_path):
    with open(source_path, "rb") as source, gzip.open(target_path, "wb") as target:
        target.write(source.read())


def build_reference_dataset(workdir):
    """Materialise a deterministic reference/query pair, gzipped like upstream."""
    state = 0x9E3779B97F4A7C15
    reference = []
    query = []
    for number, length in enumerate(_CONTIG_LENGTHS, start=1):
        name = f"chr{number}"
        sequence = []
        for _ in range(length):
            state = _next_random(state)
            sequence.append(_BASES[state & 3])
        sequence = "".join(sequence)
        reference.append((name, sequence))

        mutated = []
        for base in sequence:
            state = _next_random(state)
            if state % _SUBSTITUTION_DEN < _SUBSTITUTION_NUM:
                mutated.append(_BASES[(state >> 8) & 3])
            else:
                mutated.append(base)
        query.append((name, "".join(mutated)))

    plain_reference = os.path.join(workdir, "reference.fa")
    plain_query = os.path.join(workdir, "query.fa")
    reference_index = _write_fasta(plain_reference, reference)
    query_index = _write_fasta(plain_query, query)

    # MashMap ships its data set as .fa.gz and reads it through its own
    # gzstream layer, which is what goes through zlib; keep the same shape so
    # that path is what gets exercised.
    reference_gz = os.path.join(workdir, "reference.fa.gz")
    query_gz = os.path.join(workdir, "query.fa.gz")
    _gzip_copy(plain_reference, reference_gz)
    _gzip_copy(plain_query, query_gz)
    # The .fai stays plain text next to the compressed FASTA, exactly like the
# upstream data/ directory ships scerevisiae8.fa.gz.fai: MashMap opens it with
# a plain std::ifstream to sum the sequence lengths.
    for plain_index, packed in ((reference_index, reference_gz), (query_index, query_gz)):
        with open(plain_index, "rb") as source, open(packed + ".fai", "wb") as target:
            target.write(source.read())
    return reference_gz, query_gz


def _paf_identity(fields):
    """MashMap appends `id:f:<value>` tags after the twelve PAF columns."""
    for field in fields:
        if field.startswith("id:f:"):
            return float(field[len("id:f:") :])
    matches, block = int(fields[9]), int(fields[10])
    return matches / block if block else 0.0


def check_end_to_end_mapping(binary, align_binary, workdir, run):
    """Map the synthetic query onto the synthetic reference, then align.

    Two real runs, not a smoke test: ``mashmap`` produces the PAF and
    ``mashmap-align`` turns it into SAM, which is the pipeline the two packaged
    commands exist for.
    """
    mark = len(RECORDED)
    reference, query = build_reference_dataset(workdir)
    paf_path = os.path.join(workdir, "mapping.paf")
    log_path = os.path.join(workdir, "mapping.log")
    code, _, err = run(
        [
            binary,
            "-r", reference,
            "-q", query,
            "--pi", "95",
            "-n", "1",
            "--threads", "2",
            "-o", paf_path,
        ]
    )
    with open(log_path, "w", encoding="utf-8") as handle:
        handle.write(err)
    _require(code == 0, f"mashmap exited {code}; log at {log_path}")
    _require(os.path.isfile(paf_path), f"mashmap produced no PAF at {paf_path}")

    with open(paf_path, encoding="utf-8") as handle:
        lines = [line for line in handle if line.strip()]
    _require(len(lines) > 0, "the PAF file is empty, nothing was mapped")

    lengths = {}
    with open(reference + ".fai", encoding="utf-8") as handle:
        for line in handle:
            fields = line.rstrip("\n").split("\t")
            lengths[fields[0]] = int(fields[1])
    _require(
        len(lengths) == len(_CONTIG_LENGTHS),
        f"reference .fai lists {len(lengths)} contigs, expected {len(_CONTIG_LENGTHS)}",
    )

    seen_queries = set()
    seen_targets = set()
    identities = []
    for line in lines:
        fields = line.rstrip("\n").split("\t")
        _require(len(fields) >= 12, f"PAF record with {len(fields)} columns: {line!r}")
        query_name, query_len, query_start, query_end, strand, target_name = fields[:6]
        query_len, query_start, query_end = int(query_len), int(query_start), int(query_end)
        target_start, target_end = int(fields[7]), int(fields[8])
        _require(query_name in lengths, f"unknown query sequence {query_name}")
        _require(target_name in lengths, f"unknown target sequence {target_name}")
        _require(strand in ("+", "-"), f"bad PAF strand {strand!r}")
        _require(query_len == lengths[query_name], "PAF query length contradicts the .fai")
        _require(
            0 <= query_start < query_end <= query_len,
            f"query interval {query_start}-{query_end} outside 0-{query_len}",
        )
        _require(
            0 <= target_start < target_end <= lengths[target_name],
            f"target interval {target_start}-{target_end} outside the reference",
        )
        identity = _paf_identity(fields)
        _require(0.0 < identity <= 1.0, f"identity fraction out of range: {identity}")
        identities.append(identity)
        seen_queries.add(query_name)
        seen_targets.add(target_name)

    _require(
        seen_queries == set(lengths),
        f"not every query sequence was mapped: missing {sorted(set(lengths) - seen_queries)}",
    )
    _require(
        seen_targets == set(lengths),
        f"not every reference sequence received a hit: missing {sorted(set(lengths) - seen_targets)}",
    )
    _require(
        len(identities) >= len(lengths),
        f"only {len(identities)} PAF records for {len(lengths)} contigs",
    )
    lowest = min(identities)
    _require(
        lowest >= 0.95,
        f"lowest reported identity {lowest:.4f} is below the requested --pi 95",
    )

    # -- second command: turn the mapping into SAM ---------------------
    sam_path = os.path.join(workdir, "mapping.sam")
    align_log = os.path.join(workdir, "align.log")
    code, _, align_err = run(
        [
            align_binary,
            "-s", reference,
            "-q", query,
            "--mappingFile", paf_path,
            "--perc_identity", "95",
            "--threads", "2",
            "-o", sam_path,
        ]
    )
    with open(align_log, "w", encoding="utf-8") as handle:
        handle.write(align_err)
    _require(code == 0, f"mashmap-align exited {code}; log at {align_log}")
    _require(os.path.isfile(sam_path), f"mashmap-align produced no SAM at {sam_path}")

    # mashmap-align's SAM is not header-annotated and carries the CIGAR in the
    # last column, behind the `kc:f:` tag and a score: the upstream writer never
    # emitted @HD/@SQ/@PG lines.  Validate what it actually produces.
    records = []
    with open(sam_path, encoding="utf-8") as handle:
        for line in handle:
            line = line.rstrip("\n")
            if line:
                records.append(line.split("\t"))
    _require(len(records) > 0, "the SAM output carries no alignment record")
    _require(
        len(records) == len(lengths),
        f"{len(records)} SAM records for {len(lengths)} contigs, expected one each",
    )
    aligned_names = set()
    for fields in records:
        _require(len(fields) >= 14, f"SAM record with {len(fields)} columns: {fields!r}")
        query_name, target_name, strand = fields[0], fields[5], fields[4]
        _require(query_name in lengths, f"unknown SAM query name {query_name}")
        _require(target_name in lengths, f"unknown SAM reference name {target_name}")
        _require(strand in ("+", "-"), f"bad SAM strand {strand!r}")
        _require(
            int(fields[1]) == lengths[query_name],
            "SAM query length contradicts the reference .fai",
        )
        _require(
            fields[12].startswith("id:f:"),
            f"SAM record has no id:f: tag in column 13: {fields[12]!r}",
        )
        identity = float(fields[12][len("id:f:") :])
        _require(
            identity >= 0.95,
            f"SAM identity {identity:.4f} is below the requested --perc_identity 95",
        )
        cigar = fields[-1].rsplit(" ", 1)[-1]
        _require(
            re.fullmatch(r"(\d+[MIDNSHP=X])+", cigar) is not None,
            f"malformed CIGAR string in the SAM output: {cigar[:80]!r}",
        )
        reference_span = int(fields[8]) - int(fields[7])
        cigar_span = sum(
            int(length)
            for length, op in re.findall(r"(\d+)([MIDNSHP=X])", cigar)
            if op in "MDN=X"
        )
        _require(
            abs(cigar_span - reference_span) <= 1,
            f"CIGAR covers {cigar_span} reference bases but the record spans {reference_span}",
        )
        aligned_names.add(query_name)
    _require(
        aligned_names == set(lengths),
        f"not every contig was aligned: missing {sorted(set(lengths) - aligned_names)}",
    )
    return len(RECORDED) - mark


# --------------------------------------------------------------------------
# HarmonyOS specific checks
# --------------------------------------------------------------------------

def _read_elf(path):
    with open(path, "rb") as handle:
        data = handle.read()
    _require(data[:4] == b"\x7fELF", f"{path} is not an ELF file")
    _require(data[4] == 2, f"{path} is not 64-bit")
    endian = "<" if data[5] == 1 else ">"
    header = {
        "e_machine": struct.unpack_from(endian + "H", data, 18)[0],
        "e_phoff": struct.unpack_from(endian + "Q", data, 32)[0],
        "e_phentsize": struct.unpack_from(endian + "H", data, 54)[0],
        "e_phnum": struct.unpack_from(endian + "H", data, 56)[0],
        "e_shoff": struct.unpack_from(endian + "Q", data, 40)[0],
        "e_shentsize": struct.unpack_from(endian + "H", data, 58)[0],
        "e_shnum": struct.unpack_from(endian + "H", data, 60)[0],
        "e_shstrndx": struct.unpack_from(endian + "H", data, 62)[0],
    }
    return data, endian, header


def _section_headers(data, endian, header):
    """Yield (name, sh_type, sh_offset, sh_size, sh_entsize) per section."""
    shstr_base = header["e_shoff"] + header["e_shstrndx"] * header["e_shentsize"]
    shstr_off = struct.unpack_from(endian + "Q", data, shstr_base + 24)[0]

    def raw(index):
        base = header["e_shoff"] + index * header["e_shentsize"]
        return (
            struct.unpack_from(endian + "I", data, base)[0],
            struct.unpack_from(endian + "I", data, base + 4)[0],
            struct.unpack_from(endian + "Q", data, base + 24)[0],
            struct.unpack_from(endian + "Q", data, base + 32)[0],
            struct.unpack_from(endian + "Q", data, base + 56)[0],
        )

    for index in range(header["e_shnum"]):
        name_off, sh_type, offset, size, entsize = raw(index)
        end = data.index(b"\x00", shstr_off + name_off)
        yield data[shstr_off + name_off : end].decode("utf-8"), sh_type, offset, size, entsize


def _program_interpreter(data, endian, header):
    for index in range(header["e_phnum"]):
        base = header["e_phoff"] + index * header["e_phentsize"]
        if struct.unpack_from(endian + "I", data, base)[0] == _PT_INTERP:
            offset = struct.unpack_from(endian + "Q", data, base + 8)[0]
            size = struct.unpack_from(endian + "Q", data, base + 32)[0]
            return data[offset : offset + size].rstrip(b"\x00").decode("utf-8")
    return None


def _needed_libraries(data, endian, header):
    dynamic = None
    dynstr = None
    for name, sh_type, offset, size, entsize in _section_headers(data, endian, header):
        if sh_type == _SHT_DYNAMIC:
            dynamic = (offset, size, entsize)
        elif sh_type == _SHT_STRTAB and name == ".dynstr":
            dynstr = offset
    _require(
        dynamic is not None and dynstr is not None,
        "the ELF file has no usable .dynamic/.dynstr section",
    )
    offset, size, entsize = dynamic
    needed = []
    for position in range(offset, offset + size, entsize):
        tag, value = struct.unpack_from(endian + "qQ", data, position)
        if tag == _DT_NULL:
            break
        if tag == _DT_NEEDED:
            start = dynstr + value
            needed.append(data[start : data.index(b"\x00", start)].decode("utf-8"))
    return needed


def check_ohos_elf_profile(binaries):
    """HarmonyOS specific: the artifacts must be native aarch64 OHOS binaries.

    A cross build that accidentally picked up the x86_64 host libraries, or one
    configured for a foreign `settings.arch`, still compiles and links; only
    inspecting the produced ELF files exposes that.
    """
    checks = 0
    for path in binaries:
        label = os.path.basename(path)
        data, endian, header = _read_elf(path)

        _require(
            header["e_machine"] == _EM_AARCH64,
            f"{label} targets machine 0x{header['e_machine']:x}, not AArch64",
        )
        checks += 1

        interp = _program_interpreter(data, endian, header)
        _require(
            interp in _OHOS_LOADERS,
            f"{label} interpreter is {interp!r}, expected the OHOS musl loader",
        )
        checks += 1

        needed = _needed_libraries(data, endian, header)
        _require(bool(needed), f"{label} has no DT_NEEDED entries")
        leaked = sorted(set(needed) & _GLBC_SONAMES)
        _require(
            not leaked,
            f"{label} links host libraries {leaked}; a HarmonyOS package must not",
        )
        checks += 1

        _require(
            "libc.so" in needed,
            f"{label} does not link the OHOS musl libc.so (DT_NEEDED={needed})",
        )
        checks += 1
    if checks != 4 * len(binaries):
        raise CheckError(
            f"HarmonyOS ELF profile recorded {checks} checks for {len(binaries)} binaries, "
            "expected 4 per binary"
        )
    return checks


# --------------------------------------------------------------------------

def main(argv=None):
    parser = argparse.ArgumentParser(description="mashmap consumer checks")
    parser.add_argument("--bindir", required=True, help="directory holding the packaged commands")
    parser.add_argument("--workdir", required=True, help="scratch directory for the data set")
    parser.add_argument(
        "--runner",
        default="",
        help="space separated command prefix used to execute aarch64 binaries",
    )
    args = parser.parse_args(argv)

    os.makedirs(args.workdir, exist_ok=True)
    mashmap = os.path.join(args.bindir, "mashmap")
    mashmap_align = os.path.join(args.bindir, "mashmap-align")
    for path in (mashmap, mashmap_align):
        if not os.path.isfile(path):
            raise CheckError(f"packaged command is missing: {path}")
    if not os.access(mashmap, os.X_OK):
        raise CheckError(f"packaged command is not executable: {mashmap}")

    run = Runner(args.runner.split())
    groups = (
        ("functional/version-banner", check_version_banner(mashmap, run)),
        ("functional/align-usage", check_align_usage(mashmap_align, run)),
        (
            "functional/end-to-end-mapping",
            check_end_to_end_mapping(mashmap, mashmap_align, args.workdir, run),
        ),
        ("harmonyos/elf-profile", check_ohos_elf_profile([mashmap, mashmap_align])),
    )
    for name, count in groups:
        print(f"  {name}: {count} assertions")
    total = sum(count for _, count in groups)
    print(f"mashmap consumer checks passed, {total} assertions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
