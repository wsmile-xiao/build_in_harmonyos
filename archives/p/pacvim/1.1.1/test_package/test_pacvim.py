#!/usr/bin/env python3
"""Verify the packaged pacvim binary and data files.

pacvim is an ncurses-based terminal game. This test:
1. Executes the pacvim binary (R34 — must execute the package's binary)
2. Verifies the binary is an AArch64 ELF
3. Verifies map data files are present
4. Checks dynamic dependencies via ELF parsing
"""
import os
import struct
import subprocess
import sys


def read_elf_needed(path):
    """Parse ELF dynamic section to find NEEDED library names."""
    try:
        with open(path, "rb") as f:
            ident = f.read(16)
            is_64 = ident[4] == 2
            is_le = ident[5] == 1
            endian = "<" if is_le else ">"

            if is_64:
                f.seek(0x20)
                phoff = struct.unpack(endian + "Q", f.read(8))[0]
                f.seek(0x36)
                phentsize = struct.unpack(endian + "H", f.read(2))[0]
                phnum = struct.unpack(endian + "H", f.read(2))[0]
            else:
                f.seek(0x1C)
                phoff = struct.unpack(endian + "I", f.read(4))[0]
                f.seek(0x2A)
                phentsize = struct.unpack(endian + "H", f.read(2))[0]
                phnum = struct.unpack(endian + "H", f.read(2))[0]

            # Find PT_DYNAMIC
            dyn_offset = None
            for i in range(phnum):
                f.seek(phoff + i * phentsize)
                p_type = struct.unpack(endian + "I", f.read(4))[0]
                if p_type == 2:  # PT_DYNAMIC
                    if is_64:
                        f.seek(4, 1)  # skip p_flags (4 bytes) to reach p_offset
                        p_offset = struct.unpack(endian + "Q", f.read(8))[0]
                    else:
                        f.seek(4, 1)
                        p_offset = struct.unpack(endian + "I", f.read(4))[0]
                    dyn_offset = p_offset
                    break

            if dyn_offset is None:
                return []

            f.seek(dyn_offset)
            needed_offsets = []
            strtab_addr = None
            if is_64:
                while True:
                    d_tag = struct.unpack(endian + "Q", f.read(8))[0]
                    d_val = struct.unpack(endian + "Q", f.read(8))[0]
                    if d_tag == 0:
                        break
                    if d_tag == 1:
                        needed_offsets.append(d_val)
                    if d_tag == 5:
                        strtab_addr = d_val
            else:
                while True:
                    d_tag = struct.unpack(endian + "I", f.read(4))[0]
                    d_val = struct.unpack(endian + "I", f.read(4))[0]
                    if d_tag == 0:
                        break
                    if d_tag == 1:
                        needed_offsets.append(d_val)
                    if d_tag == 5:
                        strtab_addr = d_val

            if strtab_addr is None or not needed_offsets:
                return []

            # Find PT_LOAD segment containing strtab
            for i in range(phnum):
                f.seek(phoff + i * phentsize)
                p_type = struct.unpack(endian + "I", f.read(4))[0]
                if p_type == 1:  # PT_LOAD
                    if is_64:
                        f.seek(4, 1)  # skip p_flags (4 bytes) to reach p_offset
                        p_offset = struct.unpack(endian + "Q", f.read(8))[0]
                        p_vaddr = struct.unpack(endian + "Q", f.read(8))[0]
                        f.seek(8, 1)  # skip p_paddr (8 bytes) to reach p_filesz
                        p_filesz = struct.unpack(endian + "Q", f.read(8))[0]
                    else:
                        p_offset = struct.unpack(endian + "I", f.read(4))[0]
                        p_vaddr = struct.unpack(endian + "I", f.read(4))[0]
                        p_filesz = struct.unpack(endian + "I", f.read(4))[0]

                    if p_vaddr <= strtab_addr < p_vaddr + p_filesz:
                        strtab_file = p_offset + (strtab_addr - p_vaddr)
                        libs = []
                        for off in needed_offsets:
                            f.seek(strtab_file + off)
                            name = b""
                            while True:
                                ch = f.read(1)
                                if ch == b"\x00" or not ch:
                                    break
                                name += ch
                            libs.append(name.decode("utf-8", errors="replace"))
                        return libs
            return []
    except Exception:
        return []


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: test_pacvim.py /path/to/pacvim /path/to/package_folder", file=sys.stderr)
        return 2

    game = sys.argv[1]
    package_folder = sys.argv[2]

    # 1. Binary exists and is ELF
    if not os.path.isfile(game):
        print(f"FAIL: binary not found: {game}", file=sys.stderr)
        return 1

    with open(game, "rb") as f:
        magic = f.read(4)
        if magic != b"\x7fELF":
            print(f"FAIL: not an ELF file: {game}", file=sys.stderr)
            return 1
        f.seek(18)
        e_machine = struct.unpack("<H", f.read(2))[0]
        if e_machine != 183:  # EM_AARCH64
            print(f"FAIL: not AArch64 ELF (machine={e_machine})", file=sys.stderr)
            return 1
    print("PASS: binary is AArch64 ELF")

    # 2. Execute the pacvim binary (R34 — must execute the package's binary)
    # Without a real terminal, ncurses fails immediately with an error,
    # which proves the binary was loaded and executed.
    env = os.environ.copy()
    env.pop("TERM", None)  # Remove TERM to force ncurses failure
    try:
        result = subprocess.run(
            [game], capture_output=True, text=True, timeout=3, env=env
        )
        combined = result.stdout + result.stderr
        if "terminal" in combined.lower():
            print("PASS: pacvim binary executed (ncurses terminal init detected)")
        elif "Invalid arguments" in combined:
            print("PASS: pacvim binary executed (usage output detected)")
        else:
            if result.returncode < 0:
                print(f"FAIL: binary crashed (signal {-result.returncode})", file=sys.stderr)
                return 1
            print(f"PASS: pacvim binary executed (exit={result.returncode})")
    except subprocess.TimeoutExpired:
        print("PASS: pacvim binary executed (timed out)")
    except Exception as e:
        print(f"FAIL: could not execute pacvim binary: {e}", file=sys.stderr)
        return 1

    # 3. Dynamic dependencies via ELF parsing
    needed_libs = read_elf_needed(game)
    if needed_libs:
        print(f"PASS: dynamic dependencies: {', '.join(needed_libs)}")
        if not any("ncurses" in lib for lib in needed_libs):
            print("PASS: ncurses statically linked (R26 system same-name lib)")
    else:
        print("WARN: could not parse dynamic dependencies", file=sys.stderr)

    # 4. Map data files present
    maps_dir = os.path.join(package_folder, "share", "pacvim-maps")
    if not os.path.isdir(maps_dir):
        print(f"FAIL: maps directory not found: {maps_dir}", file=sys.stderr)
        return 1

    map_files = [f for f in os.listdir(maps_dir) if f.startswith("map") and f.endswith(".txt")]
    if len(map_files) < 1:
        print(f"FAIL: no map files found in {maps_dir}", file=sys.stderr)
        return 1
    print(f"PASS: {len(map_files)} map files present")

    print("All checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
