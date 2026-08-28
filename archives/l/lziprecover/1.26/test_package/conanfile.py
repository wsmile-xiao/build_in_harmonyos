#!/usr/bin/env python3
"""Test package for lziprecover 1.26.

Real file-level functional tests. The fixtures are committed as **text-only
Base64** (fixture.txt.lz.b64, damaged.lz.b64) plus the plaintext reference
(fixture.txt) so the PR .diff carries no binary data — safe for GitCode
checkout-pr / git apply.

At test time the .b64 fixtures are decoded to a fresh tempfile.mkdtemp()
directory using only the Python standard library (base64, tempfile, shutil,
pathlib). The source tree is never written to. The temp dir is removed in
a finally block.

This package also ships a real C test helper, test.c, which is compiled in
build() with the OHOS C compiler obtained from the Conan conf
`tools.build:compiler_executables` (never a bare shell variable, per R33).
The helper compares two files byte-for-byte (length + content) and is
invoked from test() to validate lziprecover's -cd and -B paths against
fixture.txt. The sha256 checks are kept as an extra belt-and-suspenders
assertion; the compiled helper is the primary content check.

Tests (semantics unchanged from the binary-fixture version, still 4):
  1. --version smoke check (sanity only)
  2. -t integrity check on a valid .lz fixture
  3. -cd decompress a valid .lz fixture and compare byte-for-byte
     (compiled test helper + sha256)
  4. -B byte-repair a damaged .lz fixture, then -cd decompress and compare
     (compiled test helper + sha256)
"""
import base64
import hashlib
import os
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import Environment


class LziprecoverTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    # ── Compiler + OHOS linker-runtime helpers ──────────────────────────

    def _get_cc(self):
        # R33: compiler comes from the Conan conf, never from bare shell
        # variables. The dict form is required for conan 2.29.1.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return compilers.get("c") or "clang"

    def _sdk_llvm_libdir(self):
        """LLVM lib dir of the active compiler (contains libxml2.so.16).

        Only relevant on OHOS: the OHOS clang driver spawns `lld` for
        linking, and lld's RUNPATH ($ORIGIN/../lib) points into the SDK
        llvm/lib. On CI workers the ambient LD_LIBRARY_PATH can shadow
        that dir with an incompatible libxml2.so.16, making lld fail with
        "Error loading shared library libxml2.so.16 ... symbol not found".
        Prepend the SDK llvm/lib so the correct libxml2 is found first.

        The path is derived dynamically from the compiler executable — no
        SDK version is hardcoded, and on non-OHOS hosts this returns "".
        """
        if str(self.settings.os) != "OHOS":
            return ""
        cc = self._get_cc()
        try:
            cc_real = os.path.realpath(cc)
        except OSError:
            return ""
        llvm_lib = os.path.join(os.path.dirname(os.path.dirname(cc_real)), "lib")
        return llvm_lib if os.path.isdir(llvm_lib) else ""

    def _usable_sdk_llvm_libdir(self):
        """Resolve and probe the SDK llvm/lib; raise if the linker is dead."""
        if str(self.settings.os) != "OHOS":
            return ""
        cached = getattr(self, "_checked_sdk_llvm_libdir", None)
        if cached is not None:
            return cached
        sdk_llvm_lib = self._sdk_llvm_libdir()
        if not sdk_llvm_lib:
            # No SDK lib dir discoverable — let the bare link proceed; if
            # lld fails, the build error will surface normally rather than
            # a confusing ConanException about a missing libxml2.so.16.
            self._checked_sdk_llvm_libdir = ""
            return ""
        lld = os.path.join(os.path.dirname(sdk_llvm_lib), "bin", "lld")
        probe_env = os.environ.copy()
        old_ld_path = probe_env.get("LD_LIBRARY_PATH", "")
        probe_env["LD_LIBRARY_PATH"] = os.pathsep.join(
            part for part in (sdk_llvm_lib, old_ld_path) if part
        )
        try:
            probe = subprocess.run(
                [lld, "-flavor", "gnu", "--version"],
                env=probe_env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise ConanException(
                f"Cannot execute the active OHOS SDK linker {lld}: {error}"
            ) from error
        if probe is not None and probe.returncode == 0:
            self._checked_sdk_llvm_libdir = sdk_llvm_lib
            return sdk_llvm_lib
        raise ConanException(
            f"The active OHOS SDK linker failed its GNU-flavor probe: {lld}; "
            f"stderr={probe.stderr.strip()!r}"
        )

    def _build_environment(self):
        env = Environment()
        sdk_llvm_lib = self._usable_sdk_llvm_libdir()
        if sdk_llvm_lib:
            self.output.info(
                f"Prepending OHOS SDK linker runtime path: {sdk_llvm_lib}"
            )
            env.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
        return env

    # ── build(): compile test.c into a real test helper ──────────────────

    def build(self):
        cc = self._get_cc()
        src = os.path.join(self.source_folder, "test.c")
        helper = os.path.join(self.build_folder, "cmp_files")
        opt = "-O2" if str(self.settings.build_type) == "Release" else "-g -O0"
        # Compile the byte-for-byte comparison helper with the real OHOS C
        # compiler. The _build_environment() injects the SDK llvm/lib on
        # OHOS only so lld finds the matching libxml2.so.16.
        with self._build_environment().vars(self).apply():
            self.run(
                f'"{cc}" {opt} -o "{helper}" "{src}"',
                env="conanbuild",
            )

    # ── test(): 4 functional tests ───────────────────────────────────────

    def test(self):
        if not can_run(self):
            return

        # VirtualRunEnv adds lziprecover's bin/ to PATH, so call it by name.
        src = self.source_folder
        helper = os.path.join(self.build_folder, "cmp_files")

        expected_txt_sha = "2bbb7ebbfaa1c819358dcf2c32d2366777bd327aee2705e33fed3731114c576d"
        expected_lz_sha = "dcff874ccb444a5a47d84e784fea7e29009cc4dee0fcdac6a218ebabc05cf9ec"
        expected_dmg_sha = "dd8bc1a2f50ccd98a74071d985f8a243fea3fedfee771849b44b169d1a8ada1d"

        def sha256(path):
            h = hashlib.sha256()
            with open(path, "rb") as f:
                h.update(f.read())
            return h.hexdigest()

        # Decode the .b64 fixtures to a fresh temp dir (never the source tree).
        # The .b64 files are text, PR-diff-friendly; the .lz binaries exist
        # only transiently in the temp dir and are cleaned up in finally.
        workdir = tempfile.mkdtemp(prefix="lziprecover_test_")
        try:
            fixture_txt = os.path.join(src, "fixture.txt")
            fixture_lz = os.path.join(workdir, "fixture.txt.lz")
            damaged_lz = os.path.join(workdir, "damaged.lz")

            for b64_name, out_path in (
                ("fixture.txt.lz.b64", fixture_lz),
                ("damaged.lz.b64", damaged_lz),
            ):
                with open(os.path.join(src, b64_name), "r") as f:
                    data = base64.b64decode(f.read())
                with open(out_path, "wb") as f:
                    f.write(data)

            # Verify the decoded fixtures match the committed sha256 before
            # using them — guards against a silently corrupted .b64.
            assert sha256(fixture_lz) == expected_lz_sha, (
                "decoded fixture.txt.lz sha256 mismatch"
            )
            assert sha256(damaged_lz) == expected_dmg_sha, (
                "decoded damaged.lz sha256 mismatch"
            )

            # ── Test 1: version smoke (sanity only) ──
            ver_out = os.path.join(workdir, "version.txt")
            self.run(f'lziprecover --version > "{ver_out}"', env="conanrun")
            with open(ver_out) as f:
                ver = f.read()
            assert "lziprecover 1.26" in ver, f"version mismatch: {ver}"

            # ── Test 2: integrity check on a valid .lz file ──
            self.run(f'lziprecover -t "{fixture_lz}"', env="conanrun")

            # ── Test 3: decompress and compare byte-for-byte ──
            # -c writes to stdout (keep input), so redirect to a file. (-o
            # would be ignored when -c/--stdout is set, per lziprecover
            # --help.) The compiled helper compares out.txt vs fixture.txt;
            # the sha256 is kept as an extra assertion.
            assert sha256(fixture_txt) == expected_txt_sha, (
                "fixture.txt corrupted"
            )
            out_txt = os.path.join(workdir, "out.txt")
            self.run(f'lziprecover -cd "{fixture_lz}" > "{out_txt}"', env="conanrun")
            assert os.path.exists(out_txt), "decompress produced no output"
            # Primary content check: real compiled byte-for-byte helper.
            self.run(
                f'"{helper}" "{fixture_txt}" "{out_txt}"', env="conanrun"
            )
            # Extra belt-and-suspenders assertion (retained).
            assert sha256(out_txt) == expected_txt_sha, (
                "decompressed content mismatch"
            )

            # ── Test 4: byte-repair recovery on a damaged .lz, then decompress
            repaired_lz = os.path.join(workdir, "repaired.lz")
            self.run(
                f'lziprecover -B -o "{repaired_lz}" "{damaged_lz}"',
                env="conanrun",
            )
            assert os.path.exists(repaired_lz), "byte-repair produced no output"
            repaired_txt = os.path.join(workdir, "repaired.txt")
            self.run(
                f'lziprecover -cd "{repaired_lz}" > "{repaired_txt}"',
                env="conanrun",
            )
            assert os.path.exists(repaired_txt), (
                "decompress of repaired produced no output"
            )
            # Primary content check: real compiled byte-for-byte helper.
            self.run(
                f'"{helper}" "{fixture_txt}" "{repaired_txt}"', env="conanrun"
            )
            # Extra belt-and-suspenders assertion (retained).
            assert sha256(repaired_txt) == expected_txt_sha, (
                "recovered content does not match original"
            )
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
