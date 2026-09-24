#!/usr/bin/env python3
"""Generate src/sigar_version.c from the upstream src/sigar_version.c.in template.

The 1.6.4 release tag ships the library with sigar_version.c.in but no build
scaffolding (the autotools/CMake files live only in the project's dev branch).
This script performs the same placeholder substitution the missing build would
have done, pinning the version to 1.6.4.

Any value token may optionally be overridden with --<name>=<value>.
"""
import os
import sys


# Values that are substituted *inside* a quoted string literal in the template
# must be bare (no quotes); numeric fields are bare integers.
DEFAULTS = {
    "BUILD_DATE": "2026-09-19",
    "SCM_REVISION": "sigar-1.6.4",
    "VERSION_STRING": "1.6.4",
    "ARCHNAME": "aarch64",
    "ARCHLIB": "libsigar.a",
    "BINNAME": "sigar",
    "VERSION_MAJOR": "1",
    "VERSION_MINOR": "6",
    "VERSION_MAINT": "4",
    "VERSION_BUILD": "0",
}


def main():
    vals = dict(DEFAULTS)
    for arg in sys.argv[1:]:
        if arg.startswith("--") and "=" in arg:
            key, value = arg[2:].split("=", 1)
            if key in vals:
                vals[key] = value
    srcdir = os.path.dirname(os.path.abspath(__file__))
    if os.path.basename(srcdir) == "src":
        srcdir = os.path.dirname(srcdir)
    template = os.path.join(srcdir, "src", "sigar_version.c.in")
    with open(template, encoding="utf-8") as handle:
        text = handle.read()
    for key, value in vals.items():
        text = text.replace("@@%s@@" % key, value)
    with open(os.path.join(srcdir, "src", "sigar_version.c"), "w", encoding="utf-8") as handle:
        handle.write(text)
    print("generated src/sigar_version.c (sigar %s)" % vals["VERSION_STRING"])


if __name__ == "__main__":
    main()
