#!/usr/bin/env python3
"""OHOS-specific platform contract test for the packaged mtm (test_package).

Six assertions in one test case (o1-o6, counted as 1 OHOS-specific test):

  o1  packaged mtm is an AArch64 ELF (64-bit LSB, EM_AARCH64)
  o2  dynamic interpreter is /lib/ld-musl-aarch64.so.1 (OHOS musl loader)
  o3  OHOS .codesign section exists (binary-signing segment, not stripped)
  o4  DT_NEEDED contains no libutil (OHOS musl merged libutil into libc)
  o5  forkpty is resolved by OHOS libc: mtm references it as UND, its only
      NEEDED library is libc.so, and the runtime musl libc
      (/lib/ld-musl-aarch64.so.1, which IS libc on musl) exports forkpty
  o6  packaged mtm runs in a real PTY and exits cleanly (Ctrl-g w -> 0)

The ELF facts are parsed with pure Python struct (no readelf dependency),
so the test runs anywhere the conan test_package runs.

Return code: 0 = all six assertions passed, 1 = any failed.
"""
import errno
import os
import pty
import select
import signal
import struct
import sys
import time

OHOS_INTERP = "/lib/ld-musl-aarch64.so.1"
# On OHOS the musl dynamic loader is the libc itself (all-in-one).
OHOS_LIBC = "/lib/ld-musl-aarch64.so.1"

ELFCLASS64 = 2
ELFDATA2LSB = 1
EM_AARCH64 = 183
PT_INTERP = 3
PT_DYNAMIC = 2
DT_NULL = 0
DT_NEEDED = 1
SHT_DYNSYM = 11
SHN_UNDEF = 0

KEY_TIMEOUT = 12


class Elf:
    """Minimal 64-bit little-endian ELF reader (headers, sections, dynamic)."""

    def __init__(self, path: str):
        with open(path, "rb") as fh:
            self.data = fh.read()
        if self.data[:4] != b"\x7fELF":
            raise ValueError(f"{path}: not an ELF file")
        self.is_64 = self.data[4] == ELFCLASS64
        self.is_le = self.data[5] == ELFDATA2LSB
        if not (self.is_64 and self.is_le):
            raise ValueError(f"{path}: expected 64-bit little-endian ELF")
        (self.e_type, self.e_machine) = struct.unpack_from(
            "<HH", self.data, 16)
        (self.e_phoff,) = struct.unpack_from("<Q", self.data, 32)
        (self.e_shoff,) = struct.unpack_from("<Q", self.data, 40)
        (self.e_phentsize, self.e_phnum) = struct.unpack_from(
            "<HH", self.data, 54)
        (self.e_shentsize, self.e_shnum, self.e_shstrndx) = struct.unpack_from(
            "<HHH", self.data, 58)
        self._load_sections()

    def _load_sections(self):
        self.sections = []
        for i in range(self.e_shnum):
            off = self.e_shoff + i * self.e_shentsize
            (sh_name, sh_type, _sh_flags, _sh_addr, sh_offset, sh_size,
             sh_link, _sh_info, _sh_align, _sh_entsize) = struct.unpack_from(
                "<IIQQQQIIQQ", self.data, off)
            self.sections.append({
                "name_off": sh_name, "type": sh_type, "offset": sh_offset,
                "size": sh_size, "link": sh_link,
            })
        shstr = self.sections[self.e_shstrndx]
        table = self.data[shstr["offset"]:shstr["offset"] + shstr["size"]]
        for sec in self.sections:
            end = table.find(b"\x00", sec["name_off"])
            sec["name"] = table[sec["name_off"]:end].decode("ascii", "replace")

    def section(self, name):
        for sec in self.sections:
            if sec["name"] == name:
                return sec
        return None

    def interpreter(self):
        for i in range(self.e_phnum):
            off = self.e_phoff + i * self.e_phentsize
            (p_type, _p_flags, p_offset, _vaddr, _paddr, p_filesz,
             _p_memsz, _p_align) = struct.unpack_from("<IIQQQQQQ", self.data, off)
            if p_type == PT_INTERP:
                raw = self.data[p_offset:p_offset + p_filesz]
                return raw.split(b"\x00")[0].decode("ascii", "replace")
        return None

    def needed(self):
        """Library names from DT_NEEDED entries in PT_DYNAMIC."""
        dynstr = self.section(".dynstr")
        if dynstr is None:
            return []
        table = self.data[dynstr["offset"]:dynstr["offset"] + dynstr["size"]]
        names = []
        for i in range(self.e_phnum):
            off = self.e_phoff + i * self.e_phentsize
            (p_type, _p_flags, p_offset, _vaddr, _paddr, p_filesz,
             _p_memsz, _p_align) = struct.unpack_from("<IIQQQQQQ", self.data, off)
            if p_type != PT_DYNAMIC:
                continue
            for j in range(0, p_filesz, 16):
                (d_tag, d_val) = struct.unpack_from("<QQ", self.data,
                                                    p_offset + j)
                if d_tag == DT_NULL:
                    break
                if d_tag == DT_NEEDED:
                    end = table.find(b"\x00", d_val)
                    names.append(table[d_val:end].decode("ascii", "replace"))
        return names

    def dynsyms(self):
        """List of (name, shndx, value) from .dynsym."""
        dynsym = self.section(".dynsym")
        dynstr = self.section(".dynstr")
        if dynsym is None or dynstr is None:
            return []
        table = self.data[dynstr["offset"]:dynstr["offset"] + dynstr["size"]]
        syms = []
        for off in range(dynsym["offset"],
                         dynsym["offset"] + dynsym["size"], 24):
            (st_name, _st_info, _st_other, st_shndx, st_value,
             _st_size) = struct.unpack_from("<IBBHQQ", self.data, off)
            end = table.find(b"\x00", st_name)
            name = table[st_name:end].decode("ascii", "replace")
            syms.append((name, st_shndx, st_value))
        return syms


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: ohos_specific_test.py <mtm-path>")
        return 2
    mtm = sys.argv[1]
    if not os.path.exists(mtm):
        print(f"FAIL o1: binary not found: {mtm}")
        return 1

    failures = []

    elf = Elf(mtm)

    # o1: AArch64 ELF
    if elf.e_machine == EM_AARCH64:
        print(f"OK o1: {mtm} is an AArch64 (EM_AARCH64) 64-bit LSB ELF")
    else:
        failures.append(f"o1: e_machine={elf.e_machine} != EM_AARCH64")

    # o2: OHOS musl interpreter
    interp = elf.interpreter()
    if interp == OHOS_INTERP:
        print(f"OK o2: interpreter is {interp}")
    else:
        failures.append(f"o2: interpreter {interp!r} != {OHOS_INTERP!r}")

    # o3: .codesign section present (OHOS code signing segment)
    cs = elf.section(".codesign")
    if cs is not None and cs["size"] > 0:
        print(f"OK o3: .codesign section present (size={cs['size']})")
    else:
        failures.append("o3: no non-empty .codesign section (stripped or unsigned?)")

    # o4: no libutil in NEEDED
    needed = elf.needed()
    bad = [n for n in needed if "libutil" in n]
    if not bad:
        print(f"OK o4: NEEDED={needed} contains no libutil (merged into libc on OHOS musl)")
    else:
        failures.append(f"o4: NEEDED contains {bad}")

    # o5: forkpty resolved by OHOS libc
    syms = elf.dynsyms()
    forkpty_und = any(n == "forkpty" and shndx == SHN_UNDEF
                      for (n, shndx, _v) in syms)
    libc_in_needed = any(n.startswith("libc.so") for n in needed)
    if not (forkpty_und and libc_in_needed):
        failures.append(
            f"o5: forkpty UND={forkpty_und}, libc in NEEDED={libc_in_needed}")
    else:
        try:
            libc_elf = Elf(OHOS_LIBC)
        except (OSError, ValueError) as exc:
            failures.append(f"o5: cannot parse runtime libc {OHOS_LIBC}: {exc}")
        else:
            exported = any(n == "forkpty" and shndx != SHN_UNDEF and value != 0
                           for (n, shndx, value) in libc_elf.dynsyms())
            if exported:
                print(f"OK o5: forkpty is UND in mtm, libc in NEEDED, "
                      f"and exported (defined) by {OHOS_LIBC}")
            else:
                failures.append(f"o5: {OHOS_LIBC} does not export forkpty")

    # o6: real PTY run of the packaged binary
    os.environ["TERM"] = "screen"  # terminfo provided by ncurses runenv
    pid, fd = pty.fork()
    if pid == 0:
        os.environ["SHELL"] = "/bin/sh"
        os.execv(mtm, [mtm])
    exit_code = None
    output = b""
    try:
        try:
            import fcntl
            import termios
            fcntl.ioctl(fd, termios.TIOCSWINSZ,
                        struct.pack("HHHH", 24, 80, 0, 0))
        except OSError:
            pass
        saw_output = False
        deadline = time.time() + KEY_TIMEOUT
        while time.time() < deadline:
            wpid, _ = os.waitpid(pid, os.WNOHANG)
            if wpid == pid:
                break  # exited before producing output; fail below
            r, _, _ = select.select([fd], [], [], 0.5)
            if not r:
                continue
            try:
                chunk = os.read(fd, 4096)
            except OSError:
                break
            if not chunk:
                break
            output += chunk
            if len(output) >= 64 or b"\x1b[" in output:
                saw_output = True
                break
        if not saw_output:
            failures.append(f"o6: no multiplexed output within {KEY_TIMEOUT}s "
                            f"(bytes={len(output)})")
        else:
            try:
                os.write(fd, b"\x07w")  # Ctrl-g (command key) then w (delete node)
            except OSError as exc:
                # EIO/EBADF on the pty master usually just means the child
                # already exited and closed its side.  Fail closed: tolerate
                # it only after waitpid confirms the child is gone, and then
                # still assert on its real exit status below; any other
                # OSError - or a still-running child - is re-raised, never
                # silently swallowed.
                if exc.errno not in (errno.EIO, errno.EBADF):
                    raise
                wpid, status = os.waitpid(pid, os.WNOHANG)
                if wpid != pid:
                    raise
                exit_code = os.waitstatus_to_exitcode(status)
            wait_deadline = time.time() + 5
            while exit_code is None and time.time() < wait_deadline:
                wpid, status = os.waitpid(pid, os.WNOHANG)
                if wpid == pid:
                    exit_code = os.waitstatus_to_exitcode(status)
                    break
                time.sleep(0.2)
                try:
                    r, _, _ = select.select([fd], [], [], 0)
                    if r:
                        os.read(fd, 4096)
                except OSError:
                    pass
            if exit_code == 0:
                print(f"OK o6: packaged mtm ran in a real PTY and exited "
                      f"cleanly (rc=0, bytes={len(output)})")
            else:
                failures.append(f"o6: exit_code={exit_code} (expected 0)")
    finally:
        try:
            os.close(fd)
        except OSError:
            pass
        try:
            os.kill(pid, signal.SIGKILL)
            os.waitpid(pid, 0)
        except (ProcessLookupError, ChildProcessError, OSError):
            pass

    if failures:
        for f in failures:
            print(f"FAIL {f}")
        return 1
    print("OK: all 6 OHOS-specific assertions passed (o1-o6)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
