#!/usr/bin/env python3
"""HarmonyOS-specific artifact check for the kauth 6.26.0 Conan package (rule12).

This is the artifact-level half of kauth's HarmonyOS-specific test. It takes
the FINAL conan package folder (as installed in the conan cache) and verifies
properties that only hold for the OHOS/aarch64 adaptation of kauth:

  1. The packaged library libKF6AuthCore.a exists and is non-empty.
  2. It is a real `ar` archive (magic "!<arch>\\n").
  3. The archive has at least one member.
  4. At least one extracted member is an ELF relocatable object with the
     OHOS target shape: ELF64, little-endian, e_machine == EM_AARCH64 (183),
     e_type == ET_REL (1).
  5. The package ships no backend/helper plugins under lib/plugins/kf6/kauth,
     which is the precondition for BackendsManager::init() to fall back to
     FakeBackend (the OHOS adaptation). This is the artifact-level counterpart
     of the runtime assertions in test_kauth_ohos.cpp.

Everything is parsed with the standard library only (no readelf/llvm-ar
dependency), and every assertion fails closed: the process exits non-zero on
the first failure.

Usage: python3 ohos_artifact_check.py <kauth package_folder>
"""

import os
import struct
import sys

# ar global header magic.
AR_MAGIC = b"!<arch>\n"
AR_FILE_HEADER_LEN = 60

EM_AARCH64 = 183
ET_REL = 1

LIB_RELATIVE_PATH = os.path.join("lib", "libKF6AuthCore.a")

# Where the kauth backend/helper plugins would be installed if the recipe
# shipped any. On OHOS the recipe does not build them (Polkit/D-Bus are
# unavailable), so this directory must be absent - that is what makes
# BackendsManager::init() fall back to FakeBackend.
PLUGIN_DIR_RELATIVE_PATH = os.path.join("lib", "plugins", "kf6", "kauth")

_failures = []


def check(condition, message):
    if condition:
        print("[ohos-artifact] OK: {}".format(message))
    else:
        print("[ohos-artifact] FAIL: {}".format(message))
        _failures.append(message)
    return condition


def parse_ar_members(data):
    """Return a list of (name, payload) for a GNU/BSD ar archive."""
    if not data.startswith(AR_MAGIC):
        return []
    members = []
    offset = len(AR_MAGIC)
    total = len(data)
    long_names = b""
    while offset + AR_FILE_HEADER_LEN <= total:
        header = data[offset : offset + AR_FILE_HEADER_LEN]
        offset += AR_FILE_HEADER_LEN
        if len(header) < AR_FILE_HEADER_LEN:
            break
        # Header layout: name[16] mtime[12] uid[6] gid[6] mode[8] size[10] fmag[2]
        name = header[0:16].decode("ascii", "replace").rstrip()
        try:
            size = int(header[48:58].decode("ascii").strip() or "0")
        except ValueError:
            break
        payload = data[offset : offset + size]
        offset += size + (size % 2)  # members are 2-byte aligned
        if name.startswith("//"):
            long_names = payload
            continue
        if name.startswith("/") and name[1:].isdigit() and long_names:
            start = int(name[1:])
            end = long_names.find(b"/\n", start)
            if end == -1:
                end = long_names.find(b"\n", start)
            name = long_names[start:end].decode("ascii", "replace")
        else:
            name = name.rstrip("/")
        members.append((name, payload))
    return members


def elf_header_shape(payload):
    """Return (elf_class, endian, e_type, e_machine) or None if not ELF."""
    if len(payload) < 20 or payload[0:4] != b"\x7fELF":
        return None
    ei_class = payload[4]  # 1 = 32-bit, 2 = 64-bit
    ei_data = payload[5]  # 1 = little-endian, 2 = big-endian
    endian = "<" if ei_data == 1 else ">"
    e_type, e_machine = struct.unpack_from(endian + "HH", payload, 16)
    return ei_class, ei_data, e_type, e_machine


def main():
    if len(sys.argv) != 2:
        print("usage: ohos_artifact_check.py <kauth package_folder>")
        return 2

    package_folder = sys.argv[1]
    lib_path = os.path.join(package_folder, LIB_RELATIVE_PATH)
    print("[ohos-artifact] package_folder={}".format(package_folder))
    print("[ohos-artifact] checking {}".format(lib_path))

    # 1) The packaged static library exists and is non-empty.
    if not check(os.path.isfile(lib_path), "{} exists".format(LIB_RELATIVE_PATH)):
        return 1
    size = os.path.getsize(lib_path)
    if not check(size > 0, "{} is non-empty ({} bytes)".format(LIB_RELATIVE_PATH, size)):
        return 1

    with open(lib_path, "rb") as handle:
        data = handle.read()

    # 2) It is a real ar archive.
    if not check(data.startswith(AR_MAGIC), "archive magic is '!<arch>' (ar format)"):
        return 1

    # 3) The archive has at least one member.
    members = parse_ar_members(data)
    if not check(len(members) > 0, "archive has >= 1 member (got {})".format(len(members))):
        return 1
    print("[ohos-artifact] members={}".format(", ".join(name for name, _ in members[:6])))

    # 4) At least one member is an OHOS-shaped ELF relocatable object.
    ohos_objects = []
    for name, payload in members:
        shape = elf_header_shape(payload)
        if shape is None:
            continue
        ei_class, ei_data, e_type, e_machine = shape
        if ei_class == 2 and ei_data == 1 and e_type == ET_REL and e_machine == EM_AARCH64:
            ohos_objects.append(name)
    check(
        len(ohos_objects) > 0,
        "archive contains >= 1 ELF64/aarch64 relocatable object "
        "(got {}: {})".format(len(ohos_objects), ", ".join(ohos_objects[:4])),
    )

    # 5) No backend/helper plugins shipped: the precondition for the
    #    FakeBackend fallback that the runtime test relies on.
    plugin_dir = os.path.join(package_folder, PLUGIN_DIR_RELATIVE_PATH)
    if os.path.isdir(plugin_dir):
        entries = os.listdir(plugin_dir)
    else:
        entries = []
    # Report the compile-time plugin search path baked into BackendsManager so
    # the fallback chain is auditable (informational, not an assertion).
    for marker in (b"lib/plugins/kf6/kauth/backend", b"lib/plugins/kf6/kauth/helper"):
        index = data.find(marker)
        if index != -1:
            start = data.rfind(b"/", 0, index)
            print(
                "[ohos-artifact] info: BackendsManager plugin search path baked "
                "at build time: {}".format(
                    data[start:index + len(marker)].decode("ascii", "replace")
                )
            )
    check(
        len(entries) == 0,
        "no backend/helper plugins under {} (so BackendsManager falls back to "
        "FakeBackend)".format(PLUGIN_DIR_RELATIVE_PATH),
    )

    if _failures:
        print("[ohos-artifact] RESULT: FAIL ({} check(s) failed)".format(len(_failures)))
        return 1
    print("[ohos-artifact] RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
