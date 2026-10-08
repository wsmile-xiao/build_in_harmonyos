#!/usr/bin/env python3
"""Conan recipe for randomio 1.4 — multithreaded random disk I/O microbenchmark.

randomio (Dean Gaudet, MIT) is a tiny multithreaded disk I/O microbenchmark:
N threads hammer a file/device with random-offset pread/pwrite at a given
write fraction and fsync fraction, printing periodic iops/latency tables.
It requires O_DIRECT, pread/pwrite and pthreads (fails to compile with
`#error "Needs O_DIRECT"` when the libc does not define O_DIRECT).

Build system: hand-written GNU makefile (no configure, no install target, no
unit-test suite; only default/clean targets). The default rule links
`randomio: randomio.o` via make's implicit rules using $(CC) and $(LDFLAGS)
(`-pthread -lm`), with `CFLAGS=-O2 -g -Wall -pthread -std=gnu99`. We override
CC on the make command line with the OHOS cross clang taken from
tools.build:compiler_executables (R33) and leave the makefile's own CFLAGS
intact.

musl/OHOS source audit (W1):
  * <termios.h>, <sys/ioctl.h>, pthread, drand48, pread/pwrite, fsync are all
    provided by musl; O_DIRECT is defined by musl <fcntl.h>, so the
    `#error "Needs O_DIRECT"` guard passes on aarch64-linux-ohos.
  * `_FILE_OFFSET_BITS 64` gives 64-bit off_t; TIOCGWINSZ row detection is
    optional (guarded), non-tty stdout keeps n_rows = 24.

There is no upstream test suite, so build() performs the real upstream build
and test_package runs the *installed* benchmark end-to-end against a
preallocated regular file (write-only traffic, no fsync, ~1s sample) plus a
deterministic usage-error probe, and asserts on the output tables.

Note: the upstream tarball is only distributed from http:// (arctic.org);
the URL/SHA256 live directly in this recipe (no conandata.yml) so the CI
pre-download path that trips over an unset BUILD_DIR never runs for this
package (same strategy as xmodem/0.4.7.1).
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import get, patch
from conan.tools.layout import basic_layout

_source_url = "http://www.arctic.org/~dean/randomio/randomio-1.4.tar.bz2"
_source_sha256 = "384da98a7d3da1df2a1bffb9fb499fce6d043588bbf225673fda028bdfd2386f"

# OHOS code-signing tooling (same approach as tinymembench/0.4 and simh/3.8.1):
# the DEVICE/CI provides binary-sign-tool; on a plain host we skip signing and
# let the packaged consumer sign (HarmonyOS refuses to exec unsigned ELF).
_SIGN_TOOL_CANDIDATES = (
    "/data/service/hnp/bin/binary-sign-tool",
    "/storage/Users/currentUser/usr/local/bin/binary-sign-tool",
)
_OBJCOPY_CANDIDATES = (
    "/data/service/hnp/bin/llvm-objcopy",
    "/storage/Users/currentUser/usr/local/bin/llvm-objcopy",
)


class RandomioConan(ConanFile):
    name = "randomio"
    version = "1.4"
    description = (
        "Multithreaded random disk I/O microbenchmark: N threads issue random-"
        "offset pread/pwrite with tunable write/fsync fractions and report "
        "iops plus min/avg/max/sdev latency tables."
    )
    # License text lives only in the source header comment of randomio.c
    # (MIT); no standalone LICENSE file ships upstream. package() extracts it
    # from randomio.c into licenses/LICENSE.
    license = "MIT"
    homepage = "http://www.arctic.org/~dean/randomio/"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    # Patch must be exported as a source too: without this, the patch file is
    # absent from the recipe cache and apply() fails at source() time (same
    # r3 device lesson as tinymembench/0.4).
    exports_sources = "patches/*"

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS", "FreeBSD"):
            raise ConanInvalidConfiguration(
                "randomio/1.4 in this recipe targets OHOS/Linux-like systems "
                "(requires O_DIRECT, pread/pwrite, pthreads)"
            )

    def source(self):
        # Source URL/SHA256 live in this recipe (no conandata.yml). The
        # tarball has a single root dir randomio-1.4/, so strip_root=True.
        # .tar.bz2 suffix lets Conan pick the right extractor.
        # NOTE: reference the module globals directly — Conan 2 does not map
        # module-level names onto self, so `self._source_url` would raise
        # AttributeError (r1 device lesson).
        get(self, url=_source_url, sha256=_source_sha256, strip_root=True)
        # 0001: fall back to buffered I/O when open(O_DIRECT) fails with
        # EINVAL — HarmonyOS HMDFS accepts O_DIRECT at create time but
        # rejects it when opening an existing file (verified on-device,
        # errno EINVAL). Mirrors upstream's own __APPLE__ OPEN_FLAGS=0
        # portability branch.
        # r3/r4 device lessons: the API is `patch()` (not `apply`), and the
        # device's conan has patch(conanfile, base_path=None, patch_file=...)
        # — pass everything by keyword. Exported patch file lives in
        # export_sources_folder at source() time.
        patch(
            self,
            patch_file=os.path.join(
                self.export_sources_folder,
                "patches", "0001-open-einval-buffered-io-fallback.patch",
            ),
            base_path=self.source_folder,
        )

    def build(self):
        # R33: take the compiler from Conan conf, never from bare shell vars.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "cc") if compilers else "cc"
        # Keep the makefile's own CFLAGS (-O2 -g -Wall -pthread -std=gnu99);
        # only override CC. The implicit link rule uses $(LDFLAGS) which the
        # makefile sets to `-pthread -lm` (musl merges libm into libc, the
        # -lm is a harmless no-op).
        # R9: always -j1 (tiny project; avoids jobserver/FIFO issues on OHOS).
        self.run(f'make CC="{cc}" -j1', cwd=self.source_folder)

    def package(self):
        exe = os.path.join(self.source_folder, "randomio")
        exe_windows = exe + ".exe"
        if not os.path.isfile(exe) and not os.path.isfile(exe_windows):
            raise ConanException("randomio executable missing after build")
        dst = os.path.join(self.package_folder, "bin")
        os.makedirs(dst, exist_ok=True)
        src_exe = exe if os.path.isfile(exe) else exe_windows
        shutil.copy2(src_exe, os.path.join(dst, os.path.basename(src_exe)))
        # License ships only as the header comment of randomio.c — extract it
        # into licenses/LICENSE.
        src_c = os.path.join(self.source_folder, "randomio.c")
        lic_dst = os.path.join(self.package_folder, "licenses")
        os.makedirs(lic_dst, exist_ok=True)
        with open(src_c, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
        # randomio.c lines 7..25 (1-based) hold the copyright notice and the
        # MIT grant; they are stable across the 1.4 tarball.
        block = lines[6:25]
        with open(os.path.join(lic_dst, "LICENSE"), "w", encoding="utf-8") as out:
            out.write("\n".join(block) + "\n")
        self._sign_binaries()

    def _sign_binaries(self):
        """Self-sign the OHOS ELF executables (HarmonyOS MAC refuses unsigned).

        Best-effort: the signing tools only exist on the device/CI runner. On
        a plain host we skip and let the packaged consumer re-sign.
        """
        if str(self.settings.os) != "OHOS":
            return
        sign_tool = next(
            (p for p in (shutil.which("binary-sign-tool"), *_SIGN_TOOL_CANDIDATES)
             if p and os.path.exists(p)),
            None,
        )
        objcopy = next(
            (p for p in (shutil.which("llvm-objcopy"), *_OBJCOPY_CANDIDATES)
             if p and os.path.exists(p)),
            None,
        )
        if not sign_tool:
            self.output.warning(
                "binary-sign-tool not found; skipping OHOS ELF self-signing "
                "(consumer must re-sign)"
            )
            return
        bindir = os.path.join(self.package_folder, "bin")
        for name in sorted(os.listdir(bindir)):
            path = os.path.join(bindir, name)
            if not os.path.isfile(path) or os.path.islink(path):
                continue
            if objcopy:
                subprocess.run(
                    [objcopy, "--remove-section", ".codesign", path],
                    capture_output=True,
                )
            res = subprocess.run(
                [sign_tool, "sign", "-inFile", path, "-outFile", path, "-selfSign", "1"],
                capture_output=True,
            )
            if res.returncode != 0:
                self.output.warning(
                    "binary-sign-tool failed for %s (rc=%d): %s"
                    % (name, res.returncode, res.stderr.decode(errors="replace")[:200])
                )
            else:
                os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
