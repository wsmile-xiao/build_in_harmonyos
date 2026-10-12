#!/usr/bin/env python3
"""Deterministic integrity validator for the agnostic-lizard source package.

agnostic-lizard is a source-only Common Lisp library: there is no compiled
artifact, so -- exactly like the merged data-package exemption of
pari-seadata-big -- the build()/test() smoke check is replaced by full
byte-level verification.  Every file of the upstream tree
(0~git20201010.1.fe3a737 as shipped by Debian) is checked against the
pinned SHA256 table below; the file inventory must match exactly, with no
missing and no extra entries.

Usage:
    verify_agnostic_lizard.py --source-root <unpacked upstream tree>
    verify_agnostic_lizard.py --package-root <installed package folder>
"""

import argparse
import hashlib
import os
import sys


# path (posix, relative to the tree root) -> (size, sha256)
PINNED_FILES = {
    "AUTHORS": (15, "7da611135ab24b52d58483c004809a220a8f1d7ce30c81ddb2994993cb6993f3"),
    "COPYING": (370, "eed8f471e4933ec0cf4c3d77e7426e732dbe6fdebcc695db3fe7bfee15ed99f4"),
    "README": (715, "923a2f78ebc32660f910210bf9e256afc75246d98614746e70e9fb6fbbf5fb2b"),
    "README.debugger": (34, "b15a5a6cf30e0780471e6e0d0c555f4b82804ad277fc0a1382fe930526e46985"),
    "agnostic-lizard-debugger-prototype.asd": (652, "8b5dc993aa8a96f6856ace930ab33a06fc837831b07278fbcc2007810b41616a"),
    "agnostic-lizard.asd": (1528, "6a240905adf403f0bd5999d0fe329d61a79ba4b6a57bc185516eef203de83e6d"),
    "debugger-hooks.lisp": (14191, "315cdb278921c6f532f0fcc228d3c157485e77aa97df6a8e4bd2b52bce900ccc"),
    "debugger-prototype.lisp": (8738, "8881ba96222f269f1d70e91108fd2a9ab47ce02895d88c075f51c7f96818cd90"),
    "doc/special-and-hardwired.txt": (1326, "2740776e5eb4138ec9c29a19d696aefe81e7017e30a6520ade41e247ee0b5045"),
    "env-wrappers.lisp": (3943, "f8fc8dee7237e8007809a1f8127aef112a0798755973443d443a59de803b6932"),
    "examples.lisp": (10890, "7619919bf947069b301d04218df38299171b69f6b4a33dc36c2946d6123bbc21"),
    "generic-walking.lisp": (3421, "be446f933b5e46b4ff39a8bfa0df5c89c5dce1d6022a12a6bca149eba817e3cc"),
    "gpl-3.0.txt": (35147, "8ceb4b9ee5adedde47b31e975c1d90c73ad27b6b165a1dcd80c7c545eb65b903"),
    "lexenv.lisp": (1394, "1bbdcf48299595b50519b7d5cd28d4deb1c0174295a540bc110ddaa43de20eb8"),
    "local-variables.lisp": (3004, "3e96cf2f801abe727fa80523fc779da82ee588e1ee5781cd4c40be05520a81ca"),
    "macro-based-walking.lisp": (3077, "6495c75aae6e81d0c88d5f831748ec192248cef094952ad2a114eb60278ca788"),
    "metaenv.lisp": (10295, "ba4c3ed918272f1a77f8d5ced3c1e56208281b5d89f6a08427b7dd5656a50bea"),
    "nix-load-lisp.sh": (830, "c311ff7b520bc683f60de4ff65787176978b2c89d6208af847613ec13830786c"),
    "package.lisp": (1097, "7c00f0314fbda59c5bb1cf4a34a176be841263d27c2458cf4c8826df3ed47d61"),
    "pure-expansion.lisp": (6324, "88237d95ac4d375d9b706d412852837aa582297dc3dbbec8dfcf78d405c86282"),
    "special-form-handlers.lisp": (17714, "3eaf180b19268b1d786df2f31252bb8b5d73aea6a665c6f700ae7ae3942a8adb"),
    "test-iterate.lisp": (128, "e9986815c88db9ccf57ba4022c712c43dad8444fae2a470f822381e56df9a1a8"),
    "test-macroexpand-dammit.lisp": (271, "1ae203ac3db4d5d983431f1b4f4331a8f2ffc6c0f245514e2da5f410740c1beb"),
    "use-iterate-test.lisp": (1066, "cc806cb8dfddb77d5079a77556a8541b992ae7e3602be1fb91890a7936bbe24c"),
    "utils.lisp": (3458, "147875d4346023605ea6f45cc6ae9b8232d20f8974bcdddcd7c5cf571d7205a9"),
    "walking-examples.lisp": (677, "241cbf425128f86f2d8c1950c8997e2eabc2e200b88886271650c6dd8238a402"),
    "wrapping-reader.lisp": (1508, "7b81013d1e17189c3a75e53dde866a358aa0888800055f87da0f9c6ea783be84"),
}

# The upstream tree unpacks with one top-level directory; consumers may pass
# either that directory itself or its parent.
TOP_LEVEL_HINT = "agnostic-lizard-0~git20201010.1.fe3a737"


def locate_root(argument_value):
    root = os.path.abspath(argument_value)
    # 候选含安装布局 share/common-lisp/source/agnostic-lizard
    # (CI 66005 实测包根下两者皆无致 test() 挂;as 判据用 isfile)
    candidates = [
        os.path.join(root, TOP_LEVEL_HINT),
        root,
        os.path.join(root, "share", "common-lisp", "source", "agnostic-lizard"),
    ]
    for cand in candidates:
        if os.path.isfile(os.path.join(cand, "agnostic-lizard.asd")):
            return cand
    raise SystemExit(
        f"agnostic-lizard tree not found under {root!r} (looked for {TOP_LEVEL_HINT!r} and for agnostic-lizard.asd)"
    )


def verify(root):
    failures = []
    present = set()
    for rel, (size, digest) in PINNED_FILES.items():
        path = os.path.join(root, *rel.split("/"))
        if not os.path.isfile(path):
            failures.append(f"MISSING  {rel}")
            continue
        present.add(rel)
        data = open(path, "rb").read()
        if len(data) != size:
            failures.append(
                f"SIZE     {rel}: got {len(data)}, pinned {size}")
            continue
        actual = hashlib.sha256(data).hexdigest()
        if actual != digest:
            failures.append(
                f"SHA256   {rel}: got {actual}, pinned {digest}")
    extras = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root).replace(os.sep, "/")
            if rel not in PINNED_FILES:
                extras.append(rel)
    if extras:
        for rel in sorted(extras):
            failures.append(f"EXTRA    {rel}")
    return failures


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--source-root")
    group.add_argument("--package-root")
    args = parser.parse_args()
    root = locate_root(args.source_root or args.package_root)
    failures = verify(root)
    checked = len(PINNED_FILES)
    if failures:
        for line in failures:
            print(f"FAIL {line}", file=sys.stderr)
        raise SystemExit(
            f"agnostic-lizard integrity check failed: {len(failures)} problem(s) out of {checked} pinned files")
    print(
        f"agnostic-lizard integrity OK: {checked}/{checked} pinned files byte-identical ({root})")


if __name__ == "__main__":
    main()
