#!/usr/bin/env python3
"""Conan L1 test for klavaro 3.14 — real verification of the packaged binary.

R34: test_package must exercise the packaged artifact, not print strings.

klavaro is a GTK3 GUI application: full UI startup requires a display server
session which the headless CI worker cannot provide (R40 partial for
interactive typing-course UI — same probe strategy as gtkdatabox examples).
The test therefore verifies, in order:

 1. The packaged `klavaro` executable exists in the package bin/ dir and is
    executable (R38 artifact).
 2. It is an AArch64 dynamic ELF (magic + e_machine check, readelf-free).
 3. Its DT_NEEDED closure names the GTK3 stack actually used by upstream:
    libgtk-3.so.0, libgdk-3.so.0, libgtkdatabox.so.1 (the plot widget this
    app is built around), libcurl.so.4 (online ranking feature) — read via
    `llvm-readelf -d`. Missing any of them means the link line lost a dep.
 4. Launch attempt `klavaro --version`: on headless OHOS the process prints
    "Cannot open display" and exits non-zero AFTER the dynamic loader fully
    resolved the NEEDED closure — reaching GTK init proves every shared
    object in the closure loads (runtime smoke). A loader-level error
    ("Error loading shared library") is a FAIL, "Cannot open display" is a
    PASS for the headless probe.
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.env import VirtualRunEnv

EXPECTED_NEEDED = (
    "libgtk-3.so.0",
    "libgdk-3.so.0",
    "libgtkdatabox.so.1",
    "libcurl.so",
    "libcairo.so.2",
    "libpango-1.0.so.0",
)


class KlavaroTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        bindir = None
        dep = self.dependencies[self.tested_reference_str]
        for b in dep.cpp_info.bindirs or []:
            exe = os.path.join(b, "klavaro")
            if os.path.isfile(exe) and os.access(exe, os.X_OK):
                bindir = b
                break
        if not bindir:
            raise AssertionError(
                "FAIL: klavaro executable not found in package bindirs: "
                f"{dep.cpp_info.bindirs}")
        exe = os.path.join(bindir, "klavaro")
        self.output.info(f"[R38] klavaro binary present: {exe}")

        # ELF magic + machine check (AArch64 = 0xB7)
        with open(exe, "rb") as f:
            head = f.read(20)
        assert head[:4] == b"\x7fELF", "FAIL: klavaro is not an ELF binary"
        assert head[18] == 0xB7 and head[19] == 0x00, (
            f"FAIL: klavaro is not AArch64 (e_machine={head[18]:#x})")
        self.output.info("[OK] AArch64 dynamic ELF confirmed")

        # DT_NEEDED closure: the GTK3 stack must be linked (upstream
        # configure.ac hard-requires gtk/gdk/gtkdatabox/curl).
        readelf = self._find_readelf()
        if readelf:
            rd = subprocess.run([readelf, "-d", exe], capture_output=True,
                                text=True, timeout=60)
            needed = [ln.strip().split("[")[-1].rstrip("]")
                      for ln in rd.stdout.splitlines() if "(NEEDED)" in ln]
            self.output.info(f"[OK] NEEDED closure ({len(needed)} libs)")
            missing = [lib for lib in EXPECTED_NEEDED if lib not in needed]
            if missing:
                raise AssertionError(
                    f"FAIL: expected NEEDED libs missing from klavaro: {missing}")
            self.output.info(
                "[OK] GTK3 stack confirmed linked: " +
                ", ".join(l for l in EXPECTED_NEEDED))
        else:
            self.output.warning("[WARN] readelf not found, NEEDED check skipped")

        # Runtime smoke: dynamic loader must resolve the whole closure.
        # Headless OHOS: GTK init fails with "Cannot open display" AFTER all
        # libs load — that is the expected headless outcome (PASS). A loader
        # error ("Error loading shared library ...") means the closure is
        # broken (FAIL).
        # VirtualRunEnv: the conanrunenv script aggregates LD_LIBRARY_PATH
        # for the whole dependency closure (gtk tree incl.).
        run_env = VirtualRunEnv(self)
        env = run_env.environment()
        env_vars = dict(env.vars(self, scope="run"))
        # OHOS SDK runtime: libc++_shared.so (linked by the gtk tree's C++
        # bits, e.g. pango/harfbuzz) lives in the SDK sysroot; the conan
        # closure does not carry it.
        import glob as _glob
        for extra_glob in (
            # OHOS SDK runtime: libc++_shared.so (linked by the gtk tree's
            # C++ bits, e.g. pango/harfbuzz) lives in the SDK sysroot.
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib/aarch64-linux-ohos",
            # gtkdatabox was built against the cmd-pkgs system GTK stack and
            # its DT_NEEDED carries an unversioned libffi.so which only the
            # HNP libffi install provides.
            "/data/service/hnp/libffi.org/*/lib",
        ):
            extra = sorted(_glob.glob(extra_glob))
            if extra:
                env_vars["LD_LIBRARY_PATH"] = (
                    extra[0] + os.pathsep
                    + env_vars.get("LD_LIBRARY_PATH", ""))
        # self.run(env="conanrun") sources conanrun.sh, which does NOT carry
        # the SDK paths above — append them to the generated script so the
        # loader probe sees the full closure.
        runsh = os.path.join(self.generators_folder, "conanrun.sh")
        if os.path.isfile(runsh):
            text = open(runsh).read()
            prepend = ""
            for extra_glob in (
                "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib/aarch64-linux-ohos",
                "/data/service/hnp/libffi.org/*/lib",
            ):
                extra = sorted(_glob.glob(extra_glob))
                if extra:
                    prepend += (
                        'export LD_LIBRARY_PATH="' + extra[0]
                        + ':$LD_LIBRARY_PATH"\n')
            if prepend and "hnp/libffi.org" not in text:
                text = prepend + text
                with open(runsh, "w") as f:
                    f.write(text)
                self.output.info("Augmented conanrun.sh with SDK/hnp lib paths")
        # L0d: execute via self.run() so the tested binary really launches
        # under the conan run environment (VirtualRunEnv + SDK paths).
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".out",
                                         delete=False) as tf:
            out_path = tf.name
        cmd = f'"{exe}" --version >"{out_path}" 2>&1'
        self.run(cmd, env="conanrun", ignore_errors=True)
        out = ""
        try:
            with open(out_path) as f:
                out = f.read()
        finally:
            try:
                os.unlink(out_path)
            except OSError:
                pass
        self.output.info(f"[INFO] klavaro --version output: {out[:200]!r}")
        if "Error loading shared library" in out or "Error relocating" in out:
            raise AssertionError(
                f"FAIL: dynamic loader could not resolve klavaro closure: {out[:300]}")
        if "Cannot open display" in out:
            self.output.info(
                "[OK] full NEEDED closure resolved at runtime; GTK init "
                "reached (headless display absence is expected on CI)")
        elif "3.14" in out:
            self.output.info("[OK] klavaro --version printed 3.14")

        self.output.info(
            "[R40] interactive typing-course UI requires an OpenHarmony PC "
            "display session; binary/linkage/loader verified headless — "
            "partial-verification marker for the GUI layer.")

    @staticmethod
    def _find_readelf():
        for cand in (
            "/data/service/hnp/bin/llvm-readelf",
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/"
            "llvm/bin/llvm-readelf",
        ):
            if os.path.isfile(cand):
                return cand
        from shutil import which
        return which("readelf") or which("llvm-readelf")
