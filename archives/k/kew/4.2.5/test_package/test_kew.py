#!/usr/bin/env python3
"""Consumer test for kew/4.2.5 on HarmonyOS PC.

kew is a terminal music player: the packaged artifact is one executable plus
its data tree.  Upstream ships no test suite (see MANIFEST.yml), so the
assertion set below is the counted test scope.  Every assertion is a real
check against the packaged binary -- nothing is skipped, nothing tolerated.
"""

import os
import struct
import subprocess
import sys

DT_NEEDED = 1
DT_STRTAB = 5
DT_STRSZ = 10
PT_LOAD = 1
PT_DYNAMIC = 2
PT_GNU_RELRO = 0x6474E552
PT_GNU_STACK = 0x6474E551
PF_X = 0x1


def read_elf(path):
    """Return (ei_class, e_machine, e_type, program_headers, needed_libs)."""
    with open(path, "rb") as handle:
        blob = handle.read()
    if blob[:4] != b"\x7fELF":
        raise ValueError("not an ELF file")
    ei_class = blob[4]
    if ei_class != 2:
        return ei_class, None, None, [], []

    e_machine = struct.unpack_from("<H", blob, 18)[0]
    e_type = struct.unpack_from("<H", blob, 16)[0]
    e_phoff = struct.unpack_from("<Q", blob, 32)[0]
    e_phentsize = struct.unpack_from("<H", blob, 54)[0]
    e_phnum = struct.unpack_from("<H", blob, 56)[0]

    segments = []
    dynamic = None
    for index in range(e_phnum):
        off = e_phoff + index * e_phentsize
        p_type, p_flags, p_offset, p_vaddr, _p_paddr, p_filesz, p_memsz, _align = \
            struct.unpack_from("<IIQQQQQQ", blob, off)
        segments.append((p_type, p_flags, p_offset, p_vaddr, p_filesz, p_memsz))
        if p_type == PT_DYNAMIC:
            dynamic = (p_offset, p_filesz)

    def vaddr_to_offset(vaddr):
        for p_type, _flags, p_offset, p_vaddr, p_filesz, _memsz in segments:
            if p_type == PT_LOAD and p_vaddr <= vaddr < p_vaddr + p_filesz:
                return p_offset + (vaddr - p_vaddr)
        return None

    needed = []
    if dynamic:
        dyn_off, dyn_size = dynamic
        entries = []
        pos = dyn_off
        while pos + 16 <= dyn_off + dyn_size:
            d_tag, d_val = struct.unpack_from("<qQ", blob, pos)
            entries.append((d_tag, d_val))
            pos += 16
            if d_tag == 0:
                break
        strtab_off = None
        strtab_size = 0
        for d_tag, d_val in entries:
            if d_tag == DT_STRTAB:
                strtab_off = vaddr_to_offset(d_val)
            elif d_tag == DT_STRSZ:
                strtab_size = d_val
        if strtab_off is not None:
            strtab = blob[strtab_off:strtab_off + strtab_size]
            for d_tag, d_val in entries:
                if d_tag != DT_NEEDED or d_val >= len(strtab):
                    continue
                end = strtab.find(b"\x00", d_val)
                if end < 0:
                    end = len(strtab)
                needed.append(strtab[d_val:end].decode("ascii", "replace"))
    return ei_class, e_machine, e_type, segments, needed


def read_bytes(path):
    with open(path, "rb") as handle:
        return handle.read()


class Recorder(object):
    def __init__(self):
        self.total = 0
        self.passed = 0
        self.failed = []

    def check(self, name, condition, detail=""):
        self.total += 1
        if condition:
            self.passed += 1
            print("PASS {}".format(name))
        else:
            self.failed.append(name)
            print("FAIL {} :: {}".format(name, detail))


def count_files(package_folder, directory, suffix):
    root = os.path.join(package_folder, directory)
    if not os.path.isdir(root):
        return 0, root
    return len([n for n in os.listdir(root) if n.endswith(suffix)]), root


def main():
    executable = sys.argv[1]
    package_folder = sys.argv[2] if len(sys.argv) > 2 else \
        os.path.dirname(os.path.dirname(executable))
    # LD_LIBRARY_PATH collected from the Conan run environment by the caller.
    # It is applied only to the child processes started here, never to this
    # interpreter (see test_package/conanfile.py for why).
    run_env = dict(os.environ)
    if len(sys.argv) > 3 and sys.argv[3]:
        run_env["LD_LIBRARY_PATH"] = sys.argv[3]
    rec = Recorder()

    rec.check("bin/kew exists", os.path.isfile(executable), executable)
    rec.check("bin/kew has the executable bit", os.access(executable, os.X_OK), executable)

    elf_class = e_machine = e_type = None
    segments = []
    needed = []
    try:
        elf_class, e_machine, e_type, segments, needed = read_elf(executable)
        rec.check("ELF magic \\x7fELF", True, "")
    except Exception as exc:  # noqa: BLE001 - a broken binary is a failed assertion
        rec.check("ELF magic \\x7fELF", False, repr(exc))

    rec.check("ELF class is ELF64", elf_class == 2, "ei_class={}".format(elf_class))
    rec.check("ELF machine is AArch64 (0xb7)", e_machine == 0xB7, "e_machine={}".format(e_machine))
    rec.check("ELF type is ET_DYN (PIE)", e_type == 3, "e_type={}".format(e_type))
    rec.check("PT_GNU_RELRO program header present",
              any(seg[0] == PT_GNU_RELRO for seg in segments),
              "segments={}".format([hex(seg[0]) for seg in segments]))
    stack = [seg for seg in segments if seg[0] == PT_GNU_STACK]
    rec.check("PT_GNU_STACK is non-executable (NX)",
              bool(stack) and (stack[0][1] & PF_X) == 0,
              "stack={}".format(stack))

    # Shared objects the resolved dependency graph ships: the executable has to
    # name each of them in DT_NEEDED.
    for prefix in ("libglib-2.0", "libgio-2.0", "libgobject-2.0", "libgmodule-2.0",
                   "libchafa", "libfftw3f", "libopus", "libopusfile",
                   "libvorbis", "libvorbisfile", "libogg", "libintl", "libc++"):
        rec.check("DT_NEEDED references {}".format(prefix),
                  any(item.startswith(prefix) for item in needed),
                  "needed={}".format(needed))
    rec.check("DT_NEEDED references the musl libc",
              any(item.startswith("libc.so") for item in needed),
              "needed={}".format(needed))

    # TagLib ships as a static archive (its pkg-config file defines
    # TAGLIB_STATIC), so it must not show up as a dynamic dependency; what proves
    # the metadata code really was absorbed is its mangled symbol names living
    # inside the ELF image.  zlib is consumed the same way.
    rec.check("taglib is not a dangling dynamic dependency",
              not any(item.startswith("libtag") for item in needed),
              "needed={}".format(needed))
    rec.check("zlib is not a dangling dynamic dependency",
              not any(item.startswith("libz.so") for item in needed),
              "needed={}".format(needed))
    blob = read_bytes(executable)
    rec.check("TagLib symbols live inside the binary",
              b"_ZN6TagLib" in blob, "size={}".format(len(blob)))

    # Every non-system DT_NEEDED entry must be a real file inside the Conan run
    # environment handed over by the caller.
    ld_dirs = [d for d in (run_env.get("LD_LIBRARY_PATH") or "").split(":") if d]
    system_prefixes = ("libc.so", "ld-musl", "libm.so", "libpthread.so",
                       "libdl.so", "librt.so", "libc++_shared.so")
    unresolved = [
        soname for soname in needed
        if not soname.startswith(system_prefixes)
        and not any(os.path.isfile(os.path.join(d, soname)) for d in ld_dirs)
    ]
    rec.check("every DT_NEEDED soname resolves in the Conan run env",
              bool(ld_dirs) and not unresolved,
              "unresolved={} ld_dirs={}".format(unresolved, len(ld_dirs)))

    themes, themes_root = count_files(package_folder, "share/kew/themes", ".theme")
    rec.check("share/kew/themes holds at least one .theme", themes >= 1, themes_root)
    layouts, layouts_root = count_files(package_folder, "share/kew/layouts", ".layout")
    rec.check("share/kew/layouts holds at least one .layout", layouts >= 1, layouts_root)
    rec.check("zh_CN catalogue installed",
              os.path.isfile(os.path.join(package_folder, "share/locale/zh_CN/LC_MESSAGES/kew.mo")),
              "share/locale/zh_CN/LC_MESSAGES/kew.mo")
    rec.check("ja catalogue installed",
              os.path.isfile(os.path.join(package_folder, "share/locale/ja/LC_MESSAGES/kew.mo")),
              "share/locale/ja/LC_MESSAGES/kew.mo")
    rec.check("man page installed",
              os.path.isfile(os.path.join(package_folder, "share/man/man1/kew.1")),
              "share/man/man1/kew.1")
    rec.check("desktop entry installed",
              os.path.isfile(os.path.join(package_folder, "share/applications/kew.desktop")),
              "share/applications/kew.desktop")

    version = subprocess.run([executable, "--version"], capture_output=True,
                             text=True, timeout=30, check=False, env=run_env)
    version_out = (version.stdout or "") + (version.stderr or "")
    rec.check("kew --version exits 0", version.returncode == 0,
              "rc={} out={!r}".format(version.returncode, version_out[:200]))
    rec.check("kew --version reports 4.2.5", "4.2.5" in version_out,
              "out={!r}".format(version_out[:200]))

    help_run = subprocess.run([executable, "--help"], capture_output=True,
                              text=True, timeout=30, check=False, env=run_env)
    help_out = (help_run.stdout or "") + (help_run.stderr or "")
    # Verbatim runtime evidence for notes.md / the W3 log.
    print("EVIDENCE kew --version output: " + repr(version_out))
    print("EVIDENCE kew --help output: " + repr(help_out))
    rec.check("kew --help exits 0", help_run.returncode == 0,
              "rc={} out={!r}".format(help_run.returncode, help_out[:200]))
    rec.check("kew --help prints usage", "kew" in help_out.lower(),
              "out={!r}".format(help_out[:200]))

    print("SUMMARY kew consumer: total={} passed={} failed={}".format(
        rec.total, rec.passed, len(rec.failed)))
    if rec.failed:
        print("FAILED_ASSERTIONS: {}".format(", ".join(rec.failed)))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
