"""Prepare native DejaGNU test programs for HarmonyOS execution.

Only a program being executed below the current suite's tmpdir and its local
DT_NEEDED dependencies are signed. Link/objcopy inspection fixtures remain
unchanged until the test asks to execute them. Signing never changes verdicts.
"""

import hashlib
import json
import os
import struct
import subprocess
import sys
from pathlib import Path


def native_elf_info(data):
    """Return local dependencies and signature state for an AArch64 ELF."""
    if len(data) < 64 or data[:6] != b"\x7fELF\x02\x01":
        return None
    elf_type, machine = struct.unpack_from("<HH", data, 16)
    if elf_type not in (2, 3) or machine != 183:
        return None
    offset = struct.unpack_from("<Q", data, 40)[0]
    entry_size, count, names_index = struct.unpack_from("<HHH", data, 58)
    if entry_size != 64 or not count or names_index >= count or offset + count * entry_size > len(data):
        raise ValueError("invalid ELF section table")
    sections = [struct.unpack_from("<IIQQQQIIQQ", data, offset + index * entry_size)
                for index in range(count)]

    def section_bytes(section):
        start, size = section[4:6]
        if start + size > len(data):
            raise ValueError("ELF section exceeds the file")
        return data[start:start + size]

    def string_at(table, index):
        if index >= len(table) or b"\0" not in table[index:]:
            raise ValueError("invalid ELF string table offset")
        return table[index:].split(b"\0", 1)[0].decode("utf-8")

    names = section_bytes(sections[names_index])
    signed = any(string_at(names, section[0]) == ".codesign" for section in sections)
    needed = []
    for section in sections:
        if section[1] != 6:
            continue
        if section[6] >= count:
            raise ValueError("invalid dynamic string table index")
        strings = section_bytes(sections[section[6]])
        dynamic = section_bytes(section)
        if len(dynamic) % 16:
            raise ValueError("invalid ELF dynamic table size")
        for tag, value in struct.iter_unpack("<qQ", dynamic):
            if tag == 0:
                break
            if tag == 1:
                needed.append(string_at(strings, value))
    return needed, signed


def prepare(program, suite):
    suite = Path(suite).resolve()
    temporary = suite / "tmpdir"
    # Do not follow a test-created tmpdir symlink out of this suite.
    if temporary.is_symlink():
        raise ValueError("test tmpdir must be a directory inside the current suite")
    program = Path(program).resolve()
    if not program.is_relative_to(temporary) or not program.is_file():
        return []
    if native_elf_info(program.read_bytes()) is None:
        return []
    cache_file = suite / ".ohos-signed-tests.json"
    cache = json.loads(cache_file.read_text()) if cache_file.exists() else {}
    pending, seen, records = [program], set(), []
    # shared.exp loads these libraries by literal dlopen paths rather than
    # DT_NEEDED. They are declared deployment inputs of that upstream fixture.
    dlopen_fixtures = {
        "dl1a": "libdl1.so",
        "dl1b": "libdl1.so",
        "pr21964-2": "pr21964-2b.so",
    }
    dlopen_fixtures.update({f"dl6a{index}": "libdl6a.so" for index in range(1, 8)})
    dlopen_fixtures.update({"dl6b1": "libdl6b.so", "dl6b2": "libdl6b.so",
                            "dl6c1": "libdl6c.so", "dl6d1": "libdl6d.so"})
    for name in ([dlopen_fixtures[program.name]] if program.name in dlopen_fixtures else []):
        candidate = (temporary / name).resolve()
        if candidate.is_relative_to(temporary) and candidate.is_file():
            pending.append(candidate)
    while pending:
        path = pending.pop()
        if path in seen:
            continue
        seen.add(path)
        data = path.read_bytes()
        info = native_elf_info(data)
        if info is None:
            continue
        needed, signed = info
        for library in needed:
            for directory in (suite, path.parent, temporary):
                candidate = (directory / library).resolve()
                if candidate.is_relative_to(temporary) and candidate.is_file():
                    pending.append(candidate)
                    break
        before = hashlib.sha256(data).hexdigest()
        key = str(path)
        if cache.get(key) == before:
            continue
        mode = path.stat().st_mode & 0o777
        if signed:
            subprocess.run(["/data/service/hnp/bin/llvm-objcopy", "--remove-section=.codesign", str(path)],
                           check=True, capture_output=True)
        result = subprocess.run(
            ["/data/service/hnp/bin/binary-sign-tool", "sign", "-inFile", str(path),
             "-outFile", str(path), "-selfSign", "1"], capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(f"signing {path} failed: {result.stdout}{result.stderr}")
        path.chmod(mode | 0o100)
        after = hashlib.sha256(path.read_bytes()).hexdigest()
        cache[key] = after
        records.append({"file": key, "before": before, "after": after})
    cache_file.write_text(json.dumps(cache), encoding="utf-8")
    with (suite / "ohos-test-signing.jsonl").open("a", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record) + "\n")
    return records


if __name__ == "__main__":
    prepare(sys.argv[1], os.getcwd())
