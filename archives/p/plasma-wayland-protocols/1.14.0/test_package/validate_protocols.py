#!/usr/bin/env python3
"""Consumer-side validation of an installed plasma-wayland-protocols tree.

The directory is the one advertised by the native
PlasmaWaylandProtocolsConfig.cmake as PLASMA_WAYLAND_PROTOCOLS_DIR.

For every protocol that kwayland5/5.116.0 consumes it asserts:
  * the file exists and is non-empty
  * it is well-formed XML
  * the root element is <protocol name="...">
  * the two backward-compatibility renames resolve to the expected protocol name
  * it declares at least one <interface name="..." version="...">

When a package folder is passed as the second argument it additionally asserts
that the directory advertised by the installed config lies inside that package,
which is the core contract of this data package: a config that leaked a
build-time path would otherwise still pass every per-file check whenever that
path happens to exist.

Prints `assertions=N failures=M` and exits non-zero when M > 0.
"""
import os
import sys
import xml.etree.ElementTree as ET

# The 22 protocol XML files that kwayland5/5.116.0 requires.
PROTOCOLS = [
    "appmenu", "blur", "contrast", "dpms", "fake-input", "fullscreen-shell",
    "idle", "keystate", "output-management", "outputdevice", "plasma-shell",
    "plasma-virtual-desktop", "plasma-window-management", "remote-access",
    "server-decoration-palette", "server-decoration", "shadow", "slide",
    "surface-extension", "text-input", "text-input-unstable-v2",
    "wayland-eglstream-controller",
]

# Backward-compatibility renames: installed file name -> expected <protocol name>.
RENAMES = {
    "plasma-virtual-desktop": "org_kde_plasma_virtual_desktop",
    "screencast": "zkde_screencast_unstable_v1",
}


def report(assertions, failures, notes):
    for line in notes:
        print(line)
    print(f"assertions={assertions} failures={len(failures)}")
    for failure in failures:
        print(f"FAIL: {failure}")
    return 1 if failures else 0


def check_protocol_xml(pwp_dir, name, expected_protocol_name, check, notes):
    """Validate one installed protocol XML.

    ``expected_protocol_name`` is the <protocol name="..."> the file must carry
    (used for the renamed copies); pass None to only require a non-empty name.
    """
    path = os.path.join(pwp_dir, name + ".xml")
    check(os.path.isfile(path), f"missing protocol XML: {name}.xml")
    if not os.path.isfile(path):
        return
    check(os.path.getsize(path) > 0, f"empty protocol XML: {name}.xml")
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        check(False, f"malformed XML {name}.xml: {exc}")
        return
    check(root.tag == "protocol",
          f"{name}.xml root tag is <{root.tag}>, expected <protocol>")
    check(bool(root.get("name")),
          f"{name}.xml <protocol> has no name attribute")
    if expected_protocol_name is not None:
        check(root.get("name") == expected_protocol_name,
              f"{name}.xml protocol name is {root.get('name')!r}, "
              f"expected {expected_protocol_name!r}")
    interfaces = root.findall("interface")
    check(len(interfaces) > 0, f"{name}.xml declares no <interface>")
    check(all(i.get("name") and i.get("version") for i in interfaces),
          f"{name}.xml has an <interface> without name/version")
    notes.append(f"  - {name}.xml -> protocol name={root.get('name')} "
                 f"interfaces={len(interfaces)}")


def main(argv):
    if len(argv) not in (2, 3):
        print("usage: validate_protocols.py <PLASMA_WAYLAND_PROTOCOLS_DIR> "
              "[<package_folder>]")
        return 2
    pwp_dir = argv[1]
    package_folder = argv[2] if len(argv) == 3 else None
    assertions = 0
    failures = []
    notes = []

    def check(condition, message):
        nonlocal assertions
        assertions += 1
        if not condition:
            failures.append(message)

    check(os.path.isdir(pwp_dir), f"PLASMA_WAYLAND_PROTOCOLS_DIR missing: {pwp_dir}")
    if not os.path.isdir(pwp_dir):
        return report(assertions, failures, notes)

    # Core contract of this data package: the directory published by the
    # installed config must be the one inside the package.  Without this the
    # per-file checks below can all pass against a config that still points at a
    # build-time path (e.g. an unpacked source tree), which is exactly the
    # failure mode this package exists to avoid for kwayland5.
    if package_folder is not None:
        pkg_real = os.path.realpath(package_folder)
        dir_real = os.path.realpath(pwp_dir)
        check(dir_real == pkg_real or dir_real.startswith(pkg_real + os.sep),
              f"PLASMA_WAYLAND_PROTOCOLS_DIR is outside the package: "
              f"{pwp_dir} (package: {package_folder})")
        check(os.path.basename(dir_real) == "plasma-wayland-protocols",
              f"PLASMA_WAYLAND_PROTOCOLS_DIR has unexpected basename: "
              f"{os.path.basename(dir_real)}")
        notes.append(f"  - PLASMA_WAYLAND_PROTOCOLS_DIR inside package: {dir_real}")
    else:
        notes.append("  ! package folder not supplied; containment not asserted")

    for name in PROTOCOLS:
        check_protocol_xml(pwp_dir, name, RENAMES.get(name), check, notes)

    # The two backward-compatibility renames are validated in a pass of their own.
    # Neither source name is part of PROTOCOLS (kwayland5 only consumes the
    # renamed files), so deriving the expectation from a loop over PROTOCOLS
    # alone would leave the rename assertions unreachable -- a tree that ships
    # the wrong file under a renamed name would then still report failures=0.
    # Names already covered above are skipped so nothing is counted twice.
    for name in sorted(RENAMES):
        if name in PROTOCOLS:
            continue
        check_protocol_xml(pwp_dir, name, RENAMES[name], check, notes)

    return report(assertions, failures, notes)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
