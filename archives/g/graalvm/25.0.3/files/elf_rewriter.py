#!/usr/bin/env python3
"""Rewrite the fixed glibc loader dependencies in GraalVM aarch64 ELFs."""

import argparse
import json
import struct
from collections import Counter
from pathlib import Path


PT_LOAD = 1
PT_DYNAMIC = 2
PT_INTERP = 3
DT_NULL = 0
DT_NEEDED = 1
DT_STRTAB = 5
DT_STRSZ = 10
DT_VERNEED = 0x6FFFFFFE
DT_VERNEEDNUM = 0x6FFFFFFF

OLD_INTERP = "/lib/ld-linux-aarch64.so.1"
NEW_INTERP = "/lib/ld-musl-aarch64.so.1"
NAME_REWRITES = {
    "ld-linux-aarch64.so.1": "libg.so",
    "libc.so.6": "libg.so",
    "libdl.so.2": "libg.so",
    "libm.so.6": "libg.so",
    "libpthread.so.0": "libg.so",
    "librt.so.1": "libg.so",
    "libz.so.1": "libjz.so",
    "libfreetype.so.6": "libfreetype.so",
}


class ElfFormatError(ValueError):
    pass


def is_elf(path):
    try:
        with open(path, "rb") as stream:
            return stream.read(4) == b"\x7fELF"
    except OSError:
        return False


def _bounded_cstring(data, offset, limit):
    if offset < 0 or offset >= limit or limit > len(data):
        raise ElfFormatError("string offset is outside the ELF")
    end = data.find(b"\0", offset, limit)
    if end < 0:
        raise ElfFormatError("unterminated ELF string")
    try:
        return data[offset:end].decode("ascii")
    except UnicodeDecodeError as exc:
        raise ElfFormatError("non-ASCII ELF loader string") from exc


def _program_headers(data):
    if len(data) < 64 or data[:4] != b"\x7fELF":
        raise ElfFormatError("not an ELF file")
    if data[4] != 2 or data[5] != 1:
        raise ElfFormatError("only little-endian ELF64 is supported")

    header = struct.unpack_from("<HHIQQQIHHHHHH", data, 16)
    machine = header[1]
    phoff = header[4]
    phentsize = header[8]
    phnum = header[9]
    if machine != 183:
        raise ElfFormatError(f"expected AArch64 ELF, found e_machine={machine}")
    if phentsize < 56 or phoff + phentsize * phnum > len(data):
        raise ElfFormatError("invalid program-header table")

    headers = []
    for index in range(phnum):
        offset = phoff + index * phentsize
        values = struct.unpack_from("<IIQQQQQQ", data, offset)
        headers.append(
            {
                "type": values[0],
                "offset": values[2],
                "vaddr": values[3],
                "filesz": values[5],
                "memsz": values[6],
            }
        )
    return headers


def _vaddr_to_offset(headers, address, size, data_size):
    for header in headers:
        if header["type"] != PT_LOAD:
            continue
        start = header["vaddr"]
        end = start + header["filesz"]
        if start <= address and address + size <= end:
            offset = header["offset"] + address - start
            if offset + size <= data_size:
                return offset
    raise ElfFormatError(f"virtual address 0x{address:x} is not file-backed")


def _metadata(data):
    headers = _program_headers(data)
    interpreter = None
    interpreter_offset = None
    interpreter_size = None
    dynamic = None

    for header in headers:
        if header["offset"] + header["filesz"] > len(data):
            raise ElfFormatError("program segment extends past EOF")
        if header["type"] == PT_INTERP:
            if interpreter is not None:
                raise ElfFormatError("multiple PT_INTERP segments")
            interpreter_offset = header["offset"]
            interpreter_size = header["filesz"]
            interpreter = _bounded_cstring(
                data, interpreter_offset, interpreter_offset + interpreter_size
            )
        elif header["type"] == PT_DYNAMIC:
            if dynamic is not None:
                raise ElfFormatError("multiple PT_DYNAMIC segments")
            dynamic = header

    references = []
    if dynamic is None:
        return {
            "interpreter": interpreter,
            "interpreter_offset": interpreter_offset,
            "interpreter_size": interpreter_size,
            "references": references,
        }

    tags = []
    dynamic_end = dynamic["offset"] + dynamic["filesz"]
    for offset in range(dynamic["offset"], dynamic_end, 16):
        if offset + 16 > len(data):
            raise ElfFormatError("truncated dynamic table")
        tag, value = struct.unpack_from("<QQ", data, offset)
        if tag == DT_NULL:
            break
        tags.append((tag, value))

    def one(tag, default=None):
        values = [value for current, value in tags if current == tag]
        if not values:
            return default
        if len(values) != 1:
            raise ElfFormatError(f"dynamic tag {tag:#x} appears more than once")
        return values[0]

    strtab_address = one(DT_STRTAB)
    strtab_size = one(DT_STRSZ)
    if strtab_address is None or strtab_size is None:
        raise ElfFormatError("dynamic string table is missing")
    strtab_offset = _vaddr_to_offset(
        headers, strtab_address, strtab_size, len(data)
    )
    strtab_end = strtab_offset + strtab_size

    for tag, value in tags:
        if tag != DT_NEEDED:
            continue
        references.append(
            {
                "kind": "needed",
                "offset": strtab_offset + value,
                "name": _bounded_cstring(data, strtab_offset + value, strtab_end),
            }
        )

    verneed_address = one(DT_VERNEED)
    verneed_count = one(DT_VERNEEDNUM, 0)
    if bool(verneed_address) != bool(verneed_count):
        raise ElfFormatError("incomplete GNU version-requirement metadata")
    if verneed_address:
        current = _vaddr_to_offset(headers, verneed_address, 16, len(data))
        for index in range(verneed_count):
            if current + 16 > len(data):
                raise ElfFormatError("truncated GNU version-requirement record")
            _version, _aux_count, file_index, _aux, next_offset = struct.unpack_from(
                "<HHIII", data, current
            )
            references.append(
                {
                    "kind": "version_file",
                    "offset": strtab_offset + file_index,
                    "name": _bounded_cstring(
                        data, strtab_offset + file_index, strtab_end
                    ),
                }
            )
            if index + 1 < verneed_count:
                if next_offset == 0:
                    raise ElfFormatError("short GNU version-requirement chain")
                current += next_offset

    return {
        "interpreter": interpreter,
        "interpreter_offset": interpreter_offset,
        "interpreter_size": interpreter_size,
        "references": references,
    }


def inspect_elf(path):
    data = Path(path).read_bytes()
    metadata = _metadata(data)
    return {
        "interpreter": metadata["interpreter"],
        "needed": sorted(
            reference["name"]
            for reference in metadata["references"]
            if reference["kind"] == "needed"
        ),
        "version_files": sorted(
            reference["name"]
            for reference in metadata["references"]
            if reference["kind"] == "version_file"
        ),
    }


def _replace_cstring(data, offset, old, new):
    old_bytes = old.encode("ascii")
    new_bytes = new.encode("ascii")
    if len(new_bytes) > len(old_bytes):
        raise ElfFormatError(f"replacement {new!r} is longer than {old!r}")
    if data[offset : offset + len(old_bytes) + 1] != old_bytes + b"\0":
        raise ElfFormatError(f"ELF string changed before rewrite: {old!r}")
    data[offset : offset + len(old_bytes) + 1] = (
        new_bytes + b"\0" * (len(old_bytes) + 1 - len(new_bytes))
    )


def rewrite_elf(path):
    path = Path(path)
    data = bytearray(path.read_bytes())
    before = _metadata(data)
    rewrites = Counter()

    if before["interpreter"] == OLD_INTERP:
        _replace_cstring(
            data, before["interpreter_offset"], OLD_INTERP, NEW_INTERP
        )
        rewrites["PT_INTERP"] += 1
    elif before["interpreter"] not in (None, NEW_INTERP):
        raise ElfFormatError(
            f"unexpected interpreter {before['interpreter']!r} in {path}"
        )

    pending = {}
    for reference in before["references"]:
        old = reference["name"]
        new = NAME_REWRITES.get(old)
        if new is None:
            continue
        previous = pending.setdefault(reference["offset"], (old, new))
        if previous != (old, new):
            raise ElfFormatError("conflicting dynamic-string rewrites")
        rewrites[f"{reference['kind']}:{old}->{new}"] += 1
    for offset, (old, new) in pending.items():
        _replace_cstring(data, offset, old, new)

    after = _metadata(data)
    stale = [
        reference["name"]
        for reference in after["references"]
        if reference["name"] in NAME_REWRITES
    ]
    if after["interpreter"] == OLD_INTERP or stale:
        raise ElfFormatError(f"stale glibc loader references remain: {stale}")
    path.write_bytes(data)
    return dict(sorted(rewrites.items()))


def scan_tree(root, rewrite=False):
    root = Path(root)
    records = []
    totals = Counter()
    for path in sorted(root.rglob("*")):
        if not path.is_file() or not is_elf(path):
            continue
        changes = rewrite_elf(path) if rewrite else {}
        info = inspect_elf(path)
        totals.update(changes)
        records.append(
            {
                "path": path.relative_to(root).as_posix(),
                "interpreter": info["interpreter"],
                "needed": info["needed"],
                "version_files": info["version_files"],
                "changes": changes,
            }
        )
    return {
        "elf_count": len(records),
        "interp_count": sum(record["interpreter"] is not None for record in records),
        "rewrite_totals": dict(sorted(totals.items())),
        "needed": sorted({item for record in records for item in record["needed"]}),
        "files": records,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("audit-tree", "rewrite-tree"))
    parser.add_argument("root")
    parser.add_argument("--expect-elf-count", type=int)
    parser.add_argument("--expect-interp-count", type=int)
    parser.add_argument("--report")
    args = parser.parse_args()

    report = scan_tree(args.root, rewrite=args.mode == "rewrite-tree")
    if (
        args.expect_elf_count is not None
        and report["elf_count"] != args.expect_elf_count
    ):
        raise SystemExit(
            f"expected {args.expect_elf_count} ELF files, found {report['elf_count']}"
        )
    if (
        args.expect_interp_count is not None
        and report["interp_count"] != args.expect_interp_count
    ):
        raise SystemExit(
            f"expected {args.expect_interp_count} interpreters, "
            f"found {report['interp_count']}"
        )

    output = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.report:
        Path(args.report).write_text(output, encoding="utf-8")
    print(output, end="")


if __name__ == "__main__":
    main()
