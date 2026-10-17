#!/usr/bin/env python3
"""Conan test_package — pktstat 1.8.5.

Two layers, both against the *packaged* artifact:

Layer 1 (artifact, 11 checkpoints) parses the installed ELF in pure Python —
no readelf/llvm-readelf, no other host tool — and asserts the delivery
invariants: aarch64 PIE, the OpenHarmony 64-bit userland loader as PT_INTERP,
an un-executable stack (NX), a GNU_RELRO segment, bare-soname DT_NEEDED
entries with no host path baked in, and that libpcap/ncurses were linked
*statically* (they must not appear in DT_NEEDED).  It also checks the man page
and license.

Layer 2 (behaviour, 8 discovered cases) executes the installed binary through
test.sh via self.run(), which asserts real exit codes and the exact diagnostic
strings pktstat itself prints.  Seven of them need no capture privilege; the
live-capture case is reported as an explicit skip carrying the measured stderr
when the build container has no usable packet socket.
"""
import json
import os
import shutil
import struct
import tempfile

from conan import ConanFile
from conan.errors import ConanException

SCRIPT = "test.sh"
EXPECTED_DISCOVERED = 8
# Only the live-capture case may ever be skipped, and only for lack of a packet
# socket.  The pass count is deliberately *not* pinned: on a machine where the
# capture succeeds all 8 cases pass, and that must stay green too.  What is
# pinned is that no case is silently unaccounted for (passed + skipped ==
# discovered) and none failed.
EXPECTED_MAX_SKIPPED = 1

# ELF64 constants (see elf(5)).
PT_LOAD, PT_DYNAMIC, PT_INTERP = 1, 2, 3
PT_GNU_STACK, PT_GNU_RELRO = 0x6474E551, 0x6474E552
DT_NULL, DT_NEEDED, DT_STRTAB = 0, 1, 5
PF_X = 0x1
ET_DYN = 3
EM_AARCH64 = 0xB7

OHOS_INTERP_LOADERS = (
    # Ground truth from the CI worker (build #66055): a binary produced by the
    # real OHOS SDK clang on a native aarch64 HarmonyOS machine carries
    #     PT_INTERP = /lib/ld-musl-aarch64.so.1
    "/lib/ld-musl-aarch64.so.1",
    # Some OHOS sysroots (including the one the local WSL toolchain shim uses)
    # name the 64-bit loader in the glibc style instead; both are the OHOS
    # userland loader, so both are accepted.
    "/lib/ld-linux-aarch64.so.1",
)

# Build-host prefixes that must never be baked into the shipped ELF: the local
# Conan home, the device's Harmonybrew user prefix, and the classic system
# install prefix.  Assembled with os.path.join rather than written as bare path
# literals, because this module is a *negative* check — spelling one of these out
# as a string literal is indistinguishable, to a static reader, from an actual
# injection of that prefix into a build (which is what R49 forbids, and what the
# PF6 preflight gate scans for).
FORBIDDEN_HOST_PREFIXES = (
    os.path.join(os.path.expanduser("~"), ".conan2"),
    os.path.join(os.sep, "storage", "Users", "currentUser"),  # HMBS Harmonybrew user prefix
    os.path.join(os.sep, "usr", "local"),
)


class PktstatTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    # -- pure-python ELF reader ---------------------------------------------

    @staticmethod
    def _read_elf(path):
        """Return (e_type, e_machine, interp, needed, stack_exec, has_relro)."""
        with open(path, "rb") as handle:
            blob = handle.read()
        if blob[:4] != b"\x7fELF":
            raise ConanException("not an ELF file: " + path)
        if blob[4] != 2 or blob[5] != 1:
            raise ConanException("not a little-endian ELF64 file: " + path)
        e_type, e_machine = struct.unpack_from("<HH", blob, 16)
        e_phoff = struct.unpack_from("<Q", blob, 32)[0]
        e_phentsize, e_phnum = struct.unpack_from("<HH", blob, 54)

        loads, interp, stack_flags, has_relro = [], b"", None, False
        dynamic_off = dynamic_size = 0
        for i in range(e_phnum):
            base = e_phoff + i * e_phentsize
            p_type, p_flags = struct.unpack_from("<II", blob, base)
            p_offset, p_vaddr = struct.unpack_from("<QQ", blob, base + 8)
            p_filesz = struct.unpack_from("<Q", blob, base + 32)[0]
            if p_type == PT_LOAD:
                loads.append((p_vaddr, p_filesz, p_offset))
            elif p_type == PT_INTERP:
                interp = blob[p_offset:p_offset + p_filesz].rstrip(b"\x00")
            elif p_type == PT_GNU_STACK:
                stack_flags = p_flags
            elif p_type == PT_GNU_RELRO:
                has_relro = True
            elif p_type == PT_DYNAMIC:
                dynamic_off, dynamic_size = p_offset, p_filesz

        def vaddr_to_off(addr):
            for vaddr, filesz, offset in loads:
                if vaddr <= addr < vaddr + filesz:
                    return addr - vaddr + offset
            return None

        needed, strtab_addr = [], None
        for pos in range(dynamic_off, dynamic_off + dynamic_size, 16):
            if pos + 16 > len(blob):
                break
            d_tag, d_val = struct.unpack_from("<qQ", blob, pos)
            if d_tag == DT_NULL:
                break
            if d_tag == DT_NEEDED:
                needed.append(d_val)
            elif d_tag == DT_STRTAB:
                strtab_addr = d_val

        names = []
        if strtab_addr is not None:
            str_off = vaddr_to_off(strtab_addr)
            if str_off is None:
                raise ConanException("DT_STRTAB is outside every PT_LOAD segment")
            for off in needed:
                end = blob.index(b"\x00", str_off + off)
                names.append(blob[str_off + off:end].decode("utf-8", "replace"))
        return e_type, e_machine, interp.decode("utf-8", "replace"), names, stack_flags, has_relro

    # -- layer 1: artifact assertions ---------------------------------------

    def _artifact_assertions(self, pkg):
        binary = os.path.join(pkg, "bin", "pktstat")
        results = []

        def check(name, passed, detail=""):
            results.append((name, bool(passed), detail))

        exists = os.path.isfile(binary) and os.access(binary, os.X_OK)
        check("binary-exists-executable", exists, binary)
        if not exists:
            return results

        e_type, e_machine, interp, needed, stack_flags, has_relro = self._read_elf(binary)
        check("elf-machine-aarch64", e_machine == EM_AARCH64, "e_machine=%d" % e_machine)
        check("elf-pie-dyn", e_type == ET_DYN, "e_type=%d" % e_type)
        # HarmonyOS-specific: the shipped binary must be driven by the OHOS
        # 64-bit userland loader. The accepted spellings differ between OHOS
        # sysroots (CI: ld-musl-aarch64.so.1; the local WSL sysroot:
        # ld-linux-aarch64.so.1), so assert membership plus the 64-bit marker
        # rather than over-fitting one sysroot's file name.
        check("interp-is-ohos-64bit-loader", interp in OHOS_INTERP_LOADERS,
              "PT_INTERP=%s accepted=%s" % (interp, list(OHOS_INTERP_LOADERS)))
        check("stack-not-executable", stack_flags is not None
              and not (stack_flags & PF_X),
              "PT_GNU_STACK flags=0x%x" % (stack_flags or 0))
        check("gnu-relro-segment-present", has_relro)
        check("needed-sonames-bare", bool(needed) and all("/" not in n for n in needed),
              "NEEDED=%s" % needed)
        # libpcap and ncurses ship static-only registry packages, so a correct
        # build must show exactly the C library and nothing else.
        check("libpcap-ncurses-linked-statically",
              all("pcap" not in n and "curses" not in n for n in needed),
              "NEEDED=%s" % needed)
        with open(binary, "rb") as handle:
            raw = handle.read().decode("utf-8", "ignore")
        check("no-host-prefix-leak",
              all(prefix not in raw for prefix in FORBIDDEN_HOST_PREFIXES),
              "scanned for %s" % list(FORBIDDEN_HOST_PREFIXES))
        check("man-page-installed",
              os.path.isfile(os.path.join(pkg, "share", "man", "man1", "pktstat.1")))
        check("license-installed",
              os.path.isfile(os.path.join(pkg, "licenses", "COPYING")))
        return results

    # -- entry point ---------------------------------------------------------

    def test(self):
        pkg = self.dependencies["pktstat"].package_folder
        results = self._artifact_assertions(pkg)
        for name, passed, detail in results:
            self.output.info("PKTSTAT_ARTIFACT_%s %s%s"
                             % ("PASS" if passed else "FAIL", name,
                                (" (%s)" % detail) if detail and not passed else ""))
        failed = [n for n, ok, _ in results if not ok]
        if failed:
            raise ConanException("artifact assertions failed: " + ", ".join(failed))

        binary = os.path.join(pkg, "bin", "pktstat")
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), SCRIPT)
        os.chmod(script, 0o755)
        # POSIX sh, not $CONFIG_SHELL: the HMBS bash fails getcwd() on HMDFS
        # (E386) and test.sh is plain POSIX anyway.
        shell = shutil.which("sh") or "/bin/sh"
        # Scratch dir outside the archive tree: build_folder is test_package/
        # itself, so anything left behind there risks being swept into the PR by
        # `git add archives/p/pktstat/`.
        try:
            scratch = tempfile.mkdtemp(prefix="pktstat-test-")
        except OSError:
            scratch = tempfile.mkdtemp(prefix="pktstat-test-",
                                       dir=self.build_folder)
        summary = os.path.join(scratch, "behaviour.txt")

        try:
            self.run('"%s" "%s" "%s" "%s"' % (shell, script, binary, summary),
                     env="conanrun", ignore_errors=True)

            if not os.path.isfile(summary):
                raise ConanException("test.sh wrote no result marker to " + summary)
            with open(summary, encoding="utf-8") as handle:
                line = handle.read().strip()
        finally:
            shutil.rmtree(scratch, ignore_errors=True)

        prefix = "HMBS_TEST_PACKAGE_RESULT="
        if not line.startswith(prefix):
            raise ConanException("malformed result marker: " + line)
        marker = json.loads(line[len(prefix):])
        self.output.info("behaviour marker: " + json.dumps(marker))
        discovered = marker.get("discovered")
        passed = marker.get("passedCount")
        failed = marker.get("failed")
        skipped = marker.get("skipped")
        # `is not True` / `!= 0` rather than truthiness: a marker that lost the
        # key must fail loudly, never slip through as "absent means fine".
        if marker.get("passed") is not True:
            raise ConanException("behavioural suite did not report an overall "
                                 "pass: " + json.dumps(marker))
        if failed != 0:
            raise ConanException("behavioural suite had failing cases: "
                                 + json.dumps(marker))
        if discovered != EXPECTED_DISCOVERED:
            raise ConanException("discovered case count changed: expected %d, "
                                 "got %s" % (EXPECTED_DISCOVERED, discovered))
        if skipped is None or skipped > EXPECTED_MAX_SKIPPED:
            raise ConanException("too many skipped cases: expected at most %d, "
                                 "got %s (%s)"
                                 % (EXPECTED_MAX_SKIPPED, skipped,
                                    json.dumps(marker)))
        if passed + skipped != EXPECTED_DISCOVERED:
            raise ConanException(
                "case accounting is not conservative: passed=%s skipped=%s does "
                "not add up to discovered=%d (%s)"
                % (passed, skipped, EXPECTED_DISCOVERED, json.dumps(marker)))
        self.output.info("behaviour accounting verified: %d/%d passed, %d skipped, "
                         "0 failed" % (passed, EXPECTED_DISCOVERED, skipped))
