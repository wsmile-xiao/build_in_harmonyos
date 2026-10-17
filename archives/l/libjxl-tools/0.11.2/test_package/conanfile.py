#!/usr/bin/env python3
"""test_package for libjxl-tools 0.11.2 — real JPEG XL encode/decode roundtrip.

Consumer verification: execute the installed `cjxl`/`djxl`/`jxlinfo` binaries
the way a real user would — run --version, then encode a tiny PPM image to
JXL, decode it back, and inspect the container with jxlinfo.  This exercises
the actual compression pipeline (brotli + libjxl + skcms), not just a banner.
"""
import os
import tempfile

from conan import ConanFile


class LibjxlToolsTestConan(ConanFile):
    """test_package — runs installed cjxl/djxl/jxlinfo on a real image."""
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # 1) Real consumer roundtrip, driven by the shell test source
        #    (test_package/test_tools.sh): cjxl/djxl banner checks, a real
        #    PPM -> cjxl -> .jxl -> djxl -> PPM roundtrip, and jxlinfo
        #    container inspection.  Runs with the conanrun env (RPATH resolves
        #    against the package lib/ directory).
        self.run("sh test_tools.sh", env="conanrun")

        # 2) Self-containment: run the tools with a COMPLETELY EMPTY environment
        #    (no LD_LIBRARY_PATH at all) so the $ORIGIN/../lib RPATH is the only
        #    thing that can resolve the shared runtime deps.  This is the check
        #    that catches a package whose libpng16.so.16 / libz.so only resolve
        #    because the host's LD_LIBRARY_PATH leaked in (the original defect,
        #    which silently passed under `env="conanrun"`).
        tmp = tempfile.mkdtemp(prefix="libjxl-tools-test-")
        self._assert_clean_env_roundtrip(tmp)

        self.output.info("libjxl-tools 0.11.2 roundtrip: cjxl encode, djxl decode, jxlinfo inspect — OK")

    def _assert_clean_env_roundtrip(self, tmp):
        """Run cjxl/djxl/jxlinfo with env={} and assert they still work."""
        import subprocess

        pkg = self.dependencies[self.tested_reference_str].package_folder
        bindir = os.path.join(pkg, "bin")

        def run_clean(exe, *args):
            path = os.path.join(bindir, exe)
            r = subprocess.run([path, *args], capture_output=True, text=True, env={})
            if r.returncode != 0:
                raise RuntimeError(
                    f"clean-env `{exe} {' '.join(args)}` failed (rc={r.returncode}): "
                    f"{(r.stderr or r.stdout).strip()[:500]}"
                )
            return (r.stdout or "") + (r.stderr or "")

        for exe in ("cjxl", "djxl"):
            out = run_clean(exe, "--version")
            if "v0.11.2" not in out:
                raise RuntimeError(f"clean-env `{exe} --version` unexpected output: {out!r}")
        run_clean("jxlinfo", "--help")  # jxlinfo has no --version

        ppm_in = os.path.join(tmp, "clean-in.ppm")
        jxl = os.path.join(tmp, "clean.jxl")
        ppm_out = os.path.join(tmp, "clean-out.ppm")
        with open(ppm_in, "wb") as f:
            f.write(b"P6\n4 4\n255\n")
            f.write(bytes(range(48)))
        run_clean("cjxl", ppm_in, jxl)
        if not os.path.isfile(jxl) or os.path.getsize(jxl) == 0:
            raise RuntimeError("clean-env cjxl produced no .jxl output")
        run_clean("djxl", jxl, ppm_out)
        if not os.path.isfile(ppm_out) or os.path.getsize(ppm_out) == 0:
            raise RuntimeError("clean-env djxl produced no output image")
        run_clean("jxlinfo", jxl)
        self.output.info("clean-env (env={}) roundtrip OK — package is self-contained")
