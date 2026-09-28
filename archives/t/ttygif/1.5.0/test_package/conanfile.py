#!/usr/bin/env python3
"""Conan test_package for ttygif 1.5.0 - HarmonyOS consumer test via test.sh.

Upstream ships no test suite at all (see MANIFEST.yml for the audit), so every
case below is a NEW consumer case that really executes the packaged binary.

This driver only does the parts that need Python:
  * resolve the packaged bindir by absolute path instead of trusting PATH
    (same rationale as alive/2.0.3 and vamps/0.99.2)
  * resolve ImageMagick's bin dir explicitly as well, so the D-group capability
    probe still has a handle on the dependency when PATH assembly differs
    (measured in this task: with `requires(..., run=True)` the packaged
    `convert` *is* reachable through the conanrun environment, whereas a plain
    `conan install --requires=imagemagick/7.1.2.29` -- which is not a run
    require -- produces a run environment without it)
  * build a well-formed 4-frame ttyrec fixture (struct.pack of 3 little-endian
    int32 per header + payload) whose inter-frame gaps exercise ttygif's delay
    arithmetic
  * seed a writable, per-process scratch TMPDIR for the test: HarmonyOS /tmp is
    a read-only mount and this device's ambient TMPDIR is the home directory,
    so both get rejected in favour of CI's injected temp dir, falling back to
    the test's own build folder (see _scratch_dir)
"""

import os
import struct

from conan import ConanFile
from conan.tools.build import can_run


class TtygifTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        # run=True: VirtualRunEnv only injects bin/ of run deps into PATH, and
        # ttygif is an application package whose CLI test.sh must execute
        # (without run=True the packaged binary is not even on PATH — see
        # tlsh/5.0.0, vamps/0.99.2, alive/2.0.3 for the same finding).
        self.requires(self.tested_reference_str, run=True)
        # ttygif exec's `convert` at run time; the test also drives ImageMagick
        # directly to measure what the packaged build can really decode/encode.
        # requires(..., run=True) is the only shape that reaches conanrun —
        # tool_requires / run=False do not (E365/E442, presage 三轮 CI 实证).
        self.requires("imagemagick/7.1.2.29",
                      headers=False, libs=False, run=True)

    @staticmethod
    def _bin_dir(dep):
        try:
            rel = dep.cpp_info.bindirs[0] if dep.cpp_info.bindirs else "bin"
        except Exception:
            rel = "bin"
        if not os.path.isabs(rel):
            rel = os.path.join(dep.package_folder, rel)
        return rel if os.path.isdir(rel) else os.path.join(dep.package_folder,
                                                           "bin")

    def _write_recording(self, path):
        """4-frame ttyrec fixture.

        ttyrec record = little-endian int32 tv_sec, tv_usec, len + payload.
        Timestamps 100.000 / 100.500 / 101.200 / 103.000 give inter-frame gaps
        of 500 / 700 / 1800 ms, i.e. ImageMagick delays 50.0 / 70.0 / 180.0
        (ttygif multiplies milliseconds by 0.1), plus the 100.0 tail frame.
        Halved by `-s 2.0` to 25.0 / 35.0 / 90.0 while the tail stays 100.0.
        """
        frames = [(100, 0, b"abcd"),
                  (100, 500000, b"efgh"),
                  (101, 200000, b"ijkl"),
                  (103, 0, b"mnop")]
        with open(path, "wb") as fh:
            for sec, usec, payload in frames:
                fh.write(struct.pack("<iii", sec, usec, len(payload)))
                fh.write(payload)
        return len(frames)

    def _scratch_dir(self):
        """A writable, per-process scratch dir owned by this test run.

        Order of preference, and why:
          1. an ambient TMPDIR/TMP/TEMP that exists, is writable and is *not*
             the home directory / the read-only /tmp -- this is what CI (HMBS)
             injects;
          2. a per-pid directory under this test's build folder.
        The home directory is deliberately rejected even though it is writable:
        on this device TMPDIR resolves to $HOME, and the fixture plus every
        test artifact would then be dropped as stray files in the home root.
        /tmp is rejected because HarmonyOS mounts it read-only (E002).
        """
        home = os.path.expanduser("~")
        rejected = (home, "/", "/tmp", "")
        for var in ("TMPDIR", "TMP", "TEMP"):
            cand = os.environ.get(var) or ""
            if cand in rejected or not os.path.isdir(cand):
                continue
            sub = os.path.join(cand, "ttygif-test-%d" % os.getpid())
            try:
                os.makedirs(sub, exist_ok=True)
                return sub
            except OSError:
                continue
        base = self.build_folder or os.getcwd()
        cand = os.path.join(base, "scratch-%d" % os.getpid())
        try:
            os.makedirs(cand, exist_ok=True)
            return cand
        except OSError:
            return base

    def test(self):
        if not can_run(self):
            self.output.warning(
                "ttygif test_package not executed: cannot run target binaries")
            return

        dep = self.dependencies.get("ttygif")
        bin_dir = self._bin_dir(dep) if dep is not None else ""
        if dep is not None:
            self.output.info("ttygif package_folder=%s bindir=%s" % (
                dep.package_folder, bin_dir))
            try:
                for fn in sorted(os.listdir(bin_dir)):
                    fp = os.path.join(bin_dir, fn)
                    self.output.info("ttygif bindir entry: %s link=%s exec=%s" % (
                        fn, os.path.islink(fp), os.access(fp, os.X_OK)))
            except OSError as e:
                self.output.warning("list ttygif bindir failed: %s" % e)

        im = self.dependencies.get("imagemagick")
        im_bin = self._bin_dir(im) if im is not None else ""
        self.output.info("imagemagick package_folder=%s bindir=%s" % (
            im.package_folder if im is not None else "<missing>", im_bin))

        # OHOS /tmp is read-only (erofs): seed a writable TMPDIR before exec so
        # ttygif's mkdtemp() and the shell's own scratch both land somewhere
        # writable (HMBS may also inject TMPDIR/TMP/TEMP; see _scratch_dir).
        tmpdir = self._scratch_dir()
        for var in ("TMPDIR", "TMP", "TEMP", "TEMPDIR"):
            os.environ[var] = tmpdir
        self.output.info("test TMPDIR=%s" % tmpdir)

        rec = os.path.join(tmpdir, "consumer-fixture.tty")
        nframes = self._write_recording(rec)
        self.output.info("ttyrec fixture: %s (%d frames, %d bytes)" % (
            rec, nframes, os.path.getsize(rec)))

        script = os.path.join(os.path.dirname(__file__), "test.sh")
        shell = os.environ.get("CONFIG_SHELL") or "/bin/sh"
        self.run('"%s" "%s" "%s" "%s" "%s"' % (shell, script, bin_dir, im_bin,
                                               rec), env="conanrun")
