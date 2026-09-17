#!/usr/bin/env python3
"""Test package — cvsgraph 1.7.0.

Two-level consumer verification:
1. `cvsgraph -V` — binary runs and prints its version.
2. Full pipeline render: feed a minimal 2-revision RCS file through the
   real code path (RCS lexer/parser → branch layout → libgd drawing →
   PNG encoder) and assert the output is a well-formed PNG. The test
   config disables TrueType fonts (use_ttf = false) so no font files are
   needed on the target; text falls back to gd's built-in bitmap fonts.
"""
import os

from conan import ConanFile


class CvsgraphTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # gd/2.3.3 is static; the only runtime .so in the closure is
    # libpng16.so.16 (DT_NEEDED: libc only) — VirtualRunEnv provides the
    # LD_LIBRARY_PATH that makes it resolvable at run time.
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # The tested package's own bin/ is NOT on conanrun's PATH on this
        # Conan build (only dependencies' bindirs are), and cpp.build.bindirs
        # is empty because this test_package builds nothing of its own —
        # resolve the binary from the tested package folder directly.
        pkg = self.dependencies[self.tested_reference_str]
        exe = os.path.join(pkg.package_folder, "bin", "cvsgraph")

        # 1. Version smoke test
        self.run(f'"{exe}" -V', env="conanrun")

        # 2. RCS → PNG render through the gd pipeline
        here = os.path.dirname(os.path.abspath(__file__))
        conf = os.path.join(here, "cvsgraph.conf")
        rcs = os.path.join(here, "test.txt,v")
        out = os.path.join(self.build_folder, "test-out.png")

        # -c: explicit config (upstream defaults, use_ttf=false);
        # -o: output image; -r "": clear the config's cvsroot=/var/cvs so
        # the absolute RCS path is used verbatim (get_rcsfile builds
        # cvsroot+module+file).
        self.run(f'"{exe}" -c "{conf}" -o "{out}" -r "" "{rcs}"',
                 env="conanrun")

        # 3. Consumer demo: downstream workflow — render a branching RCS
        # tree to PNG and to an HTML imagemap, asserting the side branch
        # (1.2.2.1) and trunk head (1.3) appear. `sh` resolves to
        # /system/bin/sh on OHOS (PATH) and to POSIX sh elsewhere.
        demo = os.path.join(here, "consumer_demo.sh")
        outbase = os.path.join(self.build_folder, "consumer-out")
        self.run(f'CVSGRAPH="{exe}" sh "{demo}" "{outbase}"', env="conanrun")

        with open(out, "rb") as f:
            magic = f.read(8)
        assert magic == b"\x89PNG\r\n\x1a\n", f"output is not a PNG: {magic!r}"
        size = os.path.getsize(out)
        assert size > 100, f"suspiciously small PNG: {size} bytes"
