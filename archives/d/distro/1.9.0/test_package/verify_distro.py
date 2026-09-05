#!/usr/bin/env python3
"""verify_distro.py — verify the distro module shipped by THIS package.

The host system may already provide a 'distro' module with the same version
(e.g. a global python3 install). To prove the test genuinely depends on the
package under test (R34 / CI L1e negative test), the site-packages directory
of the *installed Conan package* is inserted at the front of sys.path, and we
assert that distro.__file__ actually lives inside that directory.

Usage: python3 verify_distro.py <site-packages-of-package-under-test>
Exit 0 on success, non-zero on failure.
"""
import os
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print("[FAIL] usage: verify_distro.py <site-packages>", file=sys.stderr)
        return 1

    site = os.path.abspath(sys.argv[1])
    if not os.path.isdir(site):
        print(f"[FAIL] package site-packages not found: {site}", file=sys.stderr)
        return 1

    # Force the package-under-test to win over any system-wide distro.
    sys.path.insert(0, site)

    import distro  # noqa: E402

    mod_file = os.path.abspath(distro.__file__)
    if not mod_file.startswith(site + os.sep):
        print(
            f"[FAIL] distro loaded from OUTSIDE the package under test: {mod_file}",
            file=sys.stderr,
        )
        return 1

    expected = "1.9.0"
    actual = distro.__version__
    if actual != expected:
        print(
            f"[FAIL] unexpected distro version: got '{actual}' want '{expected}'",
            file=sys.stderr,
        )
        return 1

    # Real API call: query the running OS distribution. An empty result is
    # valid on OpenHarmony when the platform is not recognized.
    distro_id = distro.id()

    print(f"distro assertions: 2 passed (version={actual} id={distro_id} "
          f"file={mod_file})")
    return 0


if __name__ == "__main__":
    sys.exit(main())