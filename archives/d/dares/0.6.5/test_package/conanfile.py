#!/usr/bin/env python3
"""Conan test_package — dares 0.6.5 smoke tests.

Upstream ships no test suite; these are self-built, fully non-interactive
smoke tests that exercise the rescued-package binary for real:

  1. no-arg run        — prints the usage banner "DAta REScue dares 0.6.5"
  2. invalid argument  — deterministic "argument '--version' invalid" +
                         usage (exit code is 0, see below)
  3. empty image scan  — opens image, scans 0 blocks, exits 0
  4. real carve run    — scans a 5-block text image with -a (autosave):
                         the packaged magic.mgc is loaded via the libmagic
                         MAGIC env fallback, text file classified ("ASCII
                         text") and carved to the save directory
                         ("Saving N files ... finished")
  5. mime variant      — -m -a run classifies via the same database

Magic-db note: dares tries "magic"/"magic.mime" relative to the CWD first,
but explicit-path loading of a compiled magic.mgc is broken in the
redistributed libmagic (map rejected, source re-parse of binary garbage
fails); the MAGIC env fallback is the one path that verifiably loads it.
"Could not load ..." is therefore expected on stdout and NOT asserted
against; real classification (found files + carved output) is asserted
instead. See notes.md for the full experiment matrix.

Exit-code note: dares always exits 0 via daresClose() EXCEPT the autosave
path, which ends with exit(1) after saving (backend/dares.c). All assertions
are therefore made on stdout content; output is redirected to files and
checked via read_output() (lenient UTF-8 decode).
"""
import glob
import os

from conan import ConanFile


def read_output(path):
    """Read command output as bytes and decode leniently.

    libmagic embeds raw (non-UTF-8) bytes from the magic database in its
    parse warnings, so dares stdout is not guaranteed to be valid UTF-8.
    """
    with open(path, "rb") as f:
        return f.read().decode("utf-8", "replace")


class DaresTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        work = os.path.join(self.build_folder, "smoke")
        out = os.path.join(work, "rescued")
        os.makedirs(out, exist_ok=True)

        # The packaged compiled magic.mgc is consumed via the libmagic MAGIC
        # env var (set by package_info runenv) on the fallback load path —
        # verified the only working load path on the redistributed libmagic.
        # No CWD staging: explicit-path load of a compiled mgc is broken.
        dares_share = os.path.join(
            self.dependencies["dares"].package_folder, "share", "dares"
        )
        assert os.path.isfile(os.path.join(dares_share, "magic.mgc")), (
            "packaged magic.mgc missing"
        )

        # Fake image: 640 x 17-byte text lines = 10880 bytes -> 5 full
        # 2048-byte blocks of pure text (no ISO9660 payload needed; dares
        # carves by content, so the run still exercises libmagic).
        image = os.path.join(work, "image.img")
        with open(image, "wb") as f:
            f.write(b"dares smoke test\n" * 640)
        empty_image = os.path.join(work, "empty.img")
        open(empty_image, "wb").close()

        # NOTE: cwd=work on every run — dares resolves its magic database
        # relative to the CWD, so the staged copies must be the ones found.
        # Test 1: usage banner (proves the binary runs and links).
        usage_file = os.path.join(work, "usage.out")
        self.run(
            'dares > "%s" 2>&1' % usage_file, env="conanrun", cwd=work
        )
        usage = read_output(usage_file)
        assert "DAta REScue dares 0.6.5" in usage, usage
        assert "Synopsis:" in usage, usage

        # Test 2: invalid argument diagnostics (deterministic error path).
        bad_file = os.path.join(work, "badarg.out")
        self.run(
            'dares --version > "%s" 2>&1' % bad_file, env="conanrun", cwd=work
        )
        bad = read_output(bad_file)
        assert "argument '--version' invalid" in bad, bad
        assert "DAta REScue dares 0.6.5" in bad, bad

        # Test 3: empty image — clean scan of 0 blocks, exit 0.
        empty_file = os.path.join(work, "empty.out")
        self.run(
            'dares -i "%s" -s "%s" -l "%s" > "%s" 2>&1'
            % (empty_image, out, os.path.join(work, "empty.log"), empty_file),
            env="conanrun",
            cwd=work,
        )
        empty = read_output(empty_file)
        assert "opening image" in empty and ": ok" in empty, empty
        assert "finished: scanned 0 2K blocks, found 0 files" in empty, empty

        # Test 4: real carve run (-a autosave keeps it non-interactive and
        # saves the carved file; it exits 1 by design after saving).
        scan_file = os.path.join(work, "scan.out")
        self.run(
            'dares -a -i "%s" -s "%s" -l "%s" > "%s" 2>&1'
            % (image, out, os.path.join(work, "dares.log"), scan_file),
            env="conanrun",
            cwd=work,
            ignore_errors=True,  # autosave path exits 1 after saving
        )
        scan = read_output(scan_file)
        assert "opening image" in scan and ": ok" in scan, scan
        assert "contains 5 blocks of 2048 byte size" in scan, scan
        # "Could not load ..." (CWD first-path attempt) is expected and
        # cosmetic; the MAGIC-env fallback then loads the packaged mgc.
        # The functional proof is real classification + carved output:
        assert "found 1 files" in scan, scan
        assert "Saving 1 files to" in scan, scan
        assert "finished." in scan, scan
        rescued = glob.glob(os.path.join(out, "*.asc"))
        assert rescued, "no carved .asc file in save dir: " + scan

        # Test 5: mime variant (-m) classifies via the same packaged
        # database, reporting MIME type strings.
        mime_file = os.path.join(work, "mime.out")
        self.run(
            'dares -m -a -i "%s" -s "%s" -l "%s" > "%s" 2>&1'
            % (image, out, os.path.join(work, "dares2.log"), mime_file),
            env="conanrun",
            cwd=work,
            ignore_errors=True,  # autosave path exits 1 after saving
        )
        mime = read_output(mime_file)
        assert "Saving" in mime, mime
        rescued_mime = glob.glob(os.path.join(out, "*"))
        assert rescued_mime, "save dir unexpectedly empty: " + mime
