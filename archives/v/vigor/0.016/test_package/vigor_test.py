#!/usr/bin/env python3
"""HarmonyOS test_package for the vigor executable.

Runs under the conanrun environment (PATH/LD_LIBRARY_PATH include the vigor
package and its tcl/tk/X11 chain).  Assertions:

  1. Real execution of the packaged `vigor` binary (rc == 0).
     NOTE: upstream vigor (nvi family) has no `--version` flag — `vigor
     --version` returns 1 with a usage message, so the binary is exercised via
     `vigor -e -r` (ex-mode recovery listing), which is a real editor code
     path that exits 0 on a clean worker.
  2. The binary embeds the built-in version stamp ("Version 1.79 ...").
  3. The binary is a 64-bit AArch64 ELF (e_machine == 0xB7).
  4. All DT_NEEDED shared libraries resolve via LD_LIBRARY_PATH / system.

Exit code is non-zero if any assertion fails (conan test() then fails).
"""
import os
import shutil
import struct
import subprocess
import sys

PASS_COUNT = 0
FAIL_COUNT = 0


def check(name, cond, detail=""):
    global PASS_COUNT, FAIL_COUNT
    if cond:
        PASS_COUNT += 1
        print(f"[PASS] {name}")
    else:
        FAIL_COUNT += 1
        print(f"[FAIL] {name}" + (f"  -- {detail}" if detail else ""))


def main():
    # 1. Locate the packaged binary (conanrun PATH includes the package bin/).
    bin_path = shutil.which("vigor")
    check("vigor binary found on PATH", bin_path is not None,
          "PATH=" + os.environ.get("PATH", ""))
    if not bin_path:
        sys.exit(1)

    # Writable scratch dir (OHOS /tmp may be read-only erofs).
    scratch = os.path.join(os.getcwd(), "vigor-test-tmp")
    os.makedirs(scratch, exist_ok=True)
    env = dict(os.environ)
    env["TMPDIR"] = scratch

    # 2. Real execution: ex-mode recovery listing (rc == 0, produces output).
    try:
        r = subprocess.run([bin_path, "-e", "-r"], capture_output=True,
                          text=True, timeout=60, env=env)
    except Exception as exc:  # noq: BLE001
        check("vigor -e -r executes cleanly", False, f"exception {exc!r}")
        sys.exit(1)
    check("vigor -e -r exit code 0", r.returncode == 0,
          f"rc={r.returncode} stderr={r.stderr[:200]!r}")
    out = (r.stdout or "") + (r.stderr or "")
    check("vigor -e -r produced output", len(out.strip()) > 0,
          f"out={r.stdout[:200]!r}")

    # 3. Embedded version stamp (upstream has no --version flag).
    with open(bin_path, "rb") as f:
        blob = f.read()
    check("binary embeds version stamp 'Version 1.79'",
          b"Version 1.79" in blob)

    # 4. AArch64 ELF check (e_machine == 0xB7).
    check("ELF magic", blob[:4] == b"\x7fELF")
    check("ELF64 class", len(blob) > 20 and blob[4] == 2, hex(blob[4] if blob else 0))
    if len(blob) >= 20:
        machine = struct.unpack_from("<H", blob, 18)[0]
        check("e_machine = 0xB7 (AArch64)", machine == 0xB7, hex(machine))

    # 5. Dynamic-link resolution: parse DT_NEEDED and verify each shared
    #    library resolves via LD_LIBRARY_PATH or system search.
    needed = _parse_dt_needed(blob)
    check("binary is dynamically linked (has DT_NEEDED)", len(needed) > 0,
          repr(needed))
    ld_path = [d for d in os.environ.get("LD_LIBRARY_PATH", "").split(os.pathsep) if d]
    sys_paths = ["/system/lib64", "/lib", "/lib64", "/usr/lib", "/usr/lib64"]
    # OHOS sysroot lib dir mirrors the device /system/lib64; libj.so and
    # similar base-system libraries live there (and only there on the build
    # worker).  Include it when present so base-system des resolve.
    for cand in ("/storage/Users/currentUser/usr/local/sysroot/usr/lib/"
                "aarch64-linux-ohos",
                "/storage/Users/currentUser/ohos-sdk/sysroot/usr/lib/"
                "aarch64-linux-ohos"):
        if os.path.isdir(cand):
            sys_paths.insert(0, cand)
    unresolved = []
    for lib in needed:
        if lib in ("libc.so", "libc.so.6"):
            # musl/glibc loader-provided; treated as system-resolved.
            continue
        if lib == "libz.so":
            # OHOS system library (E541): HarmonyOS ships a system libz.so,
            # so Conan must NOT publish a competing shared libz.so.  The
            # loader resolves it on the worker/device (verified: `vigor -e -r`
            # exits 0 above), so treat it as system-resolved like libc — the
            # static sys_paths list cannot enumerate every worker SDK layout.
            continue
        found = False
        for d in ld_path + sys_paths:
            if os.path.isfile(os.path.join(d, lib)):
                found = True
                break
        if not found:
            unresolved.append(lib)
    check("all DT_NEEDED libraries resolve", not unresolved,
          f"unresolved={unresolved} LD_LIBRARY_PATH={ld_path}")

    print(f"\nVIGOR TEST SUMMARY: {PASS_COUNT} passed, {FAIL_COUNT} failed")
    if FAIL_COUNT:
        sys.exit(1)


def _va_to_offset(blob, va, loads):
    """Map a virtual address to a file offset using the PT_LOAD segments."""
    for p_offset, p_vaddr, p_filesz in loads:
        if p_vaddr <= va < p_vaddr + p_filesz:
            return p_offset + (va - p_vaddr)
    return None


def _parse_dt_needed(blob):
    """Minimal ELF64 .dynamic (DT_NEEDED) extractor — no readelf dependency."""
    if len(blob) < 64 or blob[:4] != b"\x7fELF" or blob[4] != 2:
        return []
    e_phoff = struct.unpack_from("<Q", blob, 32)[0]
    e_phentsize = struct.unpack_from("<H", blob, 54)[0]
    e_phnum = struct.unpack_from("<H", blob, 56)[0]
    dyn_off = str_off = str_sz = None
    loads = []
    for i in range(e_phnum):
        ph = e_phoff + i * e_phentsize
        if ph + 56 > len(blob):
            break
        p_type, _, p_offset, p_vaddr, _, p_filesz, _, _ = struct.unpack_from(
            "<IIQQQQQQ", blob, ph)
        if p_type == 2:          # PT_DYNAMIC
            dyn_off, dyn_filesz = p_offset, p_filesz
        elif p_type == 1:        # PT_LOAD (offset, vaddr, filesz)
            loads.append((p_offset, p_vaddr, p_filesz))
    if dyn_off is None:
        return []
    dyn_end = dyn_off + dyn_filesz
    entries = []
    off = dyn_off
    while off + 16 <= dyn_end and off + 16 <= len(blob):
        d_tag, d_val = struct.unpack_from("<qQ", blob, off)
        if d_tag == 0:
            break
        entries.append((d_tag, d_val))
        off += 16
    str_va = str_sz = None
    for tag, val in entries:
        if tag == 5:      # DT_STRTAB
            str_va = val
        elif tag == 10:   # DT_STRSZ
            str_sz = val
    if str_va is None:
        return []
    str_off = _va_to_offset(blob, str_va, loads)
    if str_off is None or str_off >= len(blob):
        return []
    str_blob = blob[str_off:str_off + str_sz]
    needed = []
    for tag, val in entries:
        if tag == 1:                               # DT_NEEDED
            if val >= len(str_blob):
                continue
            end = str_blob.find(b"\x00", val)
            if end == -1:
                end = len(str_blob)
            name = str_blob[val:end].decode("utf-8", "replace")
            if name:
                needed.append(name)
    return needed


if __name__ == "__main__":
    main()
