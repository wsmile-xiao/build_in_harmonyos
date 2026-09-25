#!/usr/bin/env python3
"""Conan recipe for bsc 2026.01 — Bluespec Compiler (BSV/BH -> Verilog/Bluesim).

bsc compiles Bluespec SystemVerilog (BSV) and Bluespec Haskell (BH) hardware
descriptions into synthesizable Verilog and Bluesim C++ simulators.  The
compiler core is written in Haskell (~500k lines) and needs GHC 7.10.3-9.12
plus the Hackage packages regex-compat, syb, old-time, split and
strict-concurrency plus libgmp (upstream INSTALL.md).

Toolchain bootstrap on OHOS (pure musl)
---------------------------------------
* The only runnable official GHC aarch64 bindist is aarch64-alpine3_18
  (musl); glibc variants cannot execute (E105/E172), and bsc publishes no
  linux-arm64 binary.  downloads.haskell.org throttles single connections
  (~20-60KB/s) and is not covered by the CI mirror fallback, so the 574MB
  bindist is fetched by a chunked-parallel downloader (HTTP Range requests
  scale linearly; verified 24x on a real OHOS device).
* Foreign ELFs must be self-signed for execution (llvm-objcopy strips the
  .codesign section, binary-sign-tool signs it back — pandoc recipe
  precedent).  Everything the bindist ships gets signed after extraction.
* hmdfs quirk: real `mktemp` chmods fresh dirs to 0700, which the uid-mapped
  filesystem then denies to the session, and same-session chmod is a silent
  no-op — a shim implements mktemp -d with umask 0.
* The SDK clang is a $0-relative wrapper that appends -Wl,--code-sign
  unconditionally (which breaks GHC's C-preprocessor phase under -Werror),
  so gcc/g++/cc shims call clang-15 directly with mode-appropriate flags:
  compile phases get --sysroot only; link phases additionally append
  libclang_rt.builtins, musl stubs (dlinfo, posix_spawn chdir_np) and
  --defsym aliases for the GCC-13-era __aarch64_*_sync atomics that
  clang-15's builtins predate.  GHC 9.12 passes phases via quoted
  @response-files, which the shims expand.
* runghc/GHCi cannot load objects on OHOS (libffi closures need executable
  anonymous memory, which the platform denies — ffi_closure_alloc fails),
  so Cabal Setup scripts are compiled (ghc --make) instead of interpreted.

Standard library composition
----------------------------
Compiling bsc's own src/Libraries with the bootstrapped toolchain hits a
systematic type-proviso failure (FixedPoint.bsv "too general", reproduced
identically under GHC 9.12.1 and 9.12.2).  The .bo/.v/tcllib artifacts are
architecture-independent, so they are taken from the same-version official
release; SAT solver stubs (STP_STUB/YICES_STUB) and the Bluesim primitive
libraries are built from source.

Upstream: https://github.com/B-Lang-org/bsc
License:  BSD-3-Clause (main body; see COPYING and LICENSES/ in source)
"""

import glob
import hashlib
import os
import re
import shutil
from concurrent.futures import ThreadPoolExecutor

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (apply_conandata_patches, chdir, copy,
                               download, export_conandata_patches, get,
                               unzip)
from conan.tools.layout import basic_layout

DL_CHUNKS = 24

# Provenance/build-contract files exported alongside the tools.
CONTRACT_FILES = [
    "COPYING",
    "LICENSE.txt",
    "LICENSES/*",
    "INSTALL.md",
    "README.md",
    "GNUmakefile",
    "platform.mk",
    "platform.sh",
    "src/Makefile",
    "release/ReleaseNotes.adoc",
]

# AArch64 out-of-line atomics: GCC-13-era *_sync helpers referenced by the
# GHC bindist; clang-15's compiler-rt only ships relax/acq/rel/acq_rel.
DEFYSMS = " ".join(
    f"-Wl,--defsym,__aarch64_{fam}{n}_sync=__aarch64_{fam}{n}_acq_rel"
    for fam in ("cas", "ldadd", "ldclr", "ldeor", "ldset", "swp")
    for n in (1, 2, 4, 8)
) + " -Wl,--defsym,__aarch64_cas16_sync=__aarch64_cas16_acq_rel"

GCC_SHIM = r"""#!/bin/sh
# gcc/g++/cc shim (OHOS): expands GHC's quoted @response-files, passes
# query/compile modes straight to clang-15, and appends runtime libs +
# atomics defsyms only on links.  Archive inputs are passed via -Wl, so
# `-x c` link invocations never mistake them for sources.
LOG="__SHIMDIR__/calls.log"
TC="__TC__"
SYSROOT="__SYSROOT__"
RT="__BUILTINS__"
SB="__SHIMDIR__/misc_stubs.o"
RL="__RUNTIME_LIBS__"
DY="__DEFYSMS__"
CXX=
[ "$(basename "$0")" = g++ ] && CXX="--driver-mode=g++"
EXP=""
for a in "$@"; do
  case "$a" in
    @*) rf=${a#@}
        [ -f "$rf" ] && rsp=$(cat "$rf" 2>/dev/null | tr "\n" " " | sed "s/\"//g") || rsp="$a"
        EXP="$EXP $rsp" ;;
    *)   EXP="$EXP $a" ;;
  esac
done
set -- $EXP
for a in "$@"; do
  case "$a" in
    -dumpversion|-dumpmachine|--version|-print*|-showMe*|-v)
      exec "$TC/clang-15" "$@" ;;
    -c|-S|-E)
      exec "$TC/clang-15" $CXX "--sysroot=$SYSROOT" -D__MUSL__ "$@" -Wno-unused-command-line-argument ;;
  esac
done
printf "[LINK] %s\n" "$*" >> "$LOG" 2>/dev/null
exec "$TC/clang-15" $CXX "--sysroot=$SYSROOT" -D__MUSL__ -fuse-ld=lld -Wl,--code-sign "-L$RL" "$@" -Wl,"$RT" -Wl,"$SB" $DY -Wno-unused-command-line-argument
"""

MKTEMP_SHIM = r"""#!/bin/sh
# hmdfs quirk: real mktemp chmods fresh dirs to 0700 which the uid-mapped
# filesystem denies to the session (and same-session chmod is a no-op).
real="__TC__/mktemp"
isd=0
tmpl=
for a in "$@"; do
    case "$a" in
        -d) isd=1 ;;
        -*) ;;
        *)  [ -z "$tmpl" ] && tmpl=$a ;;
    esac
done
[ "$isd" = 1 ] || exec "$real" "$@"
[ -z "$tmpl" ] && tmpl=./tmp.XXXXXXXXXX
prefix=$(printf "%s" "$tmpl" | sed "s/X\{1,\}$//")
i=0
while :; do
    i=$((i + 1))
    out="$prefix$$-$RANDOM$RANDOM-$i"
    if ( umask 0 && mkdir "$out" ) 2>/dev/null; then
        printf "%s\n" "$out"
        exit 0
    fi
    [ $i -gt 50 ] && exit 1
done
"""

TIME_SHIM = r"""#!/bin/sh
# OHOS toybox `time` lacks -a/-o/-f; the bsc test harness wraps commands
# GNU-time style.  Strip only time's own leading options, then pass the
# command through untouched.
while [ $# -gt 0 ]; do
    case "$1" in
        -a|-p|--append|--portability) shift ;;
        -o|-f) shift 2 ;;
        --output=*|--format=*) shift ;;
        -*) shift ;;
        *) break ;;
    esac
done
exec "$@"
"""

MISC_STUBS_C = r"""void dlinfo(void) {}
int posix_spawn_file_actions_addchdir_np(void *a, const char *p) {
    (void)a; (void)p; return 0;
}
"""

DEFAULT_SETUP_HS = "import Distribution.Simple\nmain = defaultMain\n"


class BscConan(ConanFile):
    name = "bsc"
    version = "2026.01"
    description = (
        "Bluespec Compiler: compiles BSV/BH hardware descriptions to "
        "synthesizable Verilog and Bluesim C++ simulators. Bootstraps the "
        "GHC (aarch64 alpine-musl) toolchain, installs the pinned Hackage "
        "closure, builds from source and composes the same-version official "
        "standard library artifacts."
    )
    license = "BSD-3-Clause"
    homepage = "https://github.com/B-Lang-org/bsc"
    url = ""  # CI fills this

    package_type = "application"

    # L0p: OHOS profile 需要全部四项 settings
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        # R32: settings.os 必须按 ("Linux", "OHOS") 判断
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")
        # The GHC alpine bindist (and thus this bootstrap) is aarch64-only.
        if str(self.settings.arch) not in ("armv8", "aarch64", "arm64"):
            raise ConanInvalidConfiguration(
                "bsc bootstraps an aarch64 musl GHC; unsupported arch: "
                f"{self.settings.arch}"
            )

    def export_sources(self):
        # Conan 2 only exports conanfile.py + conandata.yml by default;
        # patches/ must be exported explicitly (export_sources_folder is
        # only valid in this hook) or apply_conandata_patches fails at
        # source() time with FileNotFoundError.
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)
        # yices2 sources (empty submodule in the tag tarball; the stub build
        # still needs its headers).  Paths are bsc-root-relative.
        get(self, **self.conan_data["yices_src"])

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _toolchain_dir(self):
        """Directory holding clang-15/llvm-objcopy/binary-sign-tool."""
        cands = []
        cc = (self.conf.get("tools.build:compiler_executables",
                            check_type=dict) or {}).get("c")
        if cc:
            cands.append(os.path.dirname(os.path.realpath(cc)))
        path = os.environ.get("PATH", "")
        for d in path.split(os.pathsep):
            if d and os.path.exists(os.path.join(d, "clang")):
                cands.append(os.path.dirname(os.path.realpath(
                    os.path.join(d, "clang"))))
                break
        def complete(d):
            return (os.path.exists(os.path.join(d, "clang-15"))
                    and os.path.exists(os.path.join(d, "binary-sign-tool"))
                    and os.path.exists(os.path.join(d, "llvm-objcopy")))
        # Prefer a directory with the FULL toolset (clang-15 + signing
        # tools): SDK dirs exposed via profile paths often lack the
        # signing utilities.
        for c in ("/storage/Users/currentUser/usr/local/bin",
                  "/data/service/hnp/bin") + tuple(cands):
            if complete(c):
                return c
        for c in cands:
            if os.path.exists(os.path.join(c, "clang-15")):
                return c
        for c in ("/storage/Users/currentUser/usr/local/bin",
                  "/data/service/hnp/bin"):
            if os.path.exists(os.path.join(c, "clang-15")):
                return c
        raise ConanInvalidConfiguration("clang-15 toolchain not found")

    def _resolve_sysroot(self, tc):
        """Locate the musl sysroot carrying usr/include/inttypes.h.

        The wrapper clang scripts pass their own --sysroot; when we call
        clang-15 directly we must supply it ourselves.  Layouts differ
        (usr-local style: <tc>/../sysroot; SDK style: <tc>/../../sysroot),
        so probe candidates for the file clang's inttypes.h include_next
        needs.
        """
        cands = [
            os.path.join(tc, "..", "sysroot"),
            os.path.join(tc, "..", "..", "sysroot"),
            "/storage/Users/currentUser/usr/local/sysroot",
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/"
            "native/sysroot",
        ]
        for c in cands:
            if os.path.isfile(os.path.join(c, "usr", "include",
                                           "inttypes.h")):
                return os.path.normpath(c)
        raise ConanInvalidConfiguration(
            "musl sysroot (usr/include/inttypes.h) not found for " + tc)

    def _sign_elf(self, path):
        """Self-sign a foreign ELF for OHOS execution (pandoc precedent)."""
        import subprocess
        tc = self._tc
        try:
            with open(path, "rb") as f:
                if f.read(4) != b"\x7fELF":
                    return
        except OSError:
            return
        def resolve(name):
            cand = os.path.join(tc, name)
            if os.path.exists(cand):
                return cand
            found = shutil.which(name)
            if found:
                return found
            for d in ("/storage/Users/currentUser/usr/local/bin",
                      "/data/service/hnp/bin",
                      "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/"
                      "ohos/native/llvm/bin"):
                cand = os.path.join(d, name)
                if os.path.exists(cand):
                    return cand
            raise ConanException(f"signing tool not found: {name}")
        objcopy = resolve("llvm-objcopy")
        sign = resolve("binary-sign-tool")
        tmp = path + ".signed"
        subprocess.run([objcopy, "--remove-section", ".codesign", path],
                       capture_output=True, timeout=30)
        r = subprocess.run([sign, "sign", "-inFile", path,
                            "-outFile", tmp, "-selfSign", "1"],
                           capture_output=True, timeout=120)
        if r.returncode != 0 or not os.path.exists(tmp) or \
                os.path.getsize(tmp) == 0:
            raise ConanException(f"ELF signing failed: {path}: "
                                 f"{r.stderr[:200]!r}")
        shutil.copyfile(tmp, path)
        os.remove(tmp)
        os.chmod(path, 0o755)

    def _sign_tree(self, root):
        for d in ("bin", "libexec"):
            for f in glob.glob(os.path.join(root, d, "*")):
                if os.path.isfile(f):
                    self._sign_elf(f)
        for f in glob.glob(os.path.join(root, "lib", "**", "*.so"),
                           recursive=True):
            self._sign_elf(f)
        for b in glob.glob(os.path.join(root, "lib", "*", "bin", "*")):
            if os.path.isfile(b):
                self._sign_elf(b)

    def _parallel_fetch(self, url, dest, size, sha256):
        """Chunked-parallel download with per-chunk verification.

        The server throttles single connections (~20-60KB/s), so the bindist
        is fetched as HTTP Range chunks.  Some CI-farm proxies mangle ranged
        requests (answering 200 with full/cached content), so every chunk is
        verified for exact length, retried, and any range-ignoring response
        (status 200 delivering the whole file) is kept as the full download.
        """
        import time
        import urllib.request
        chunk = (size + DL_CHUNKS - 1) // DL_CHUNKS
        diagnostics = []

        def fetch(i):
            start_off = i * chunk
            end_off = min(start_off + chunk, size) - 1
            want = end_off - start_off + 1
            part = f"{dest}.part{i:03d}"
            for attempt in range(6):
                if os.path.exists(dest):
                    # A sibling chunk already captured a full-file response.
                    return "FULL"
                try:
                    req = urllib.request.Request(
                        url, headers={"Range": f"bytes={start_off}-{end_off}"})
                    with urllib.request.urlopen(req, timeout=600) as r,                             open(part, "wb") as f:
                        status = getattr(r, "status", None) or r.getcode()
                        got = 0
                        while True:
                            block = r.read(1 << 20)
                            if not block:
                                break
                            f.write(block)
                            got += len(block)
                    if status == 200 and got == size:
                        # Peer ignored Range and sent the whole file.
                        os.replace(part, dest)
                        return "FULL"
                    if got == want:
                        return "OK"
                    diagnostics.append(
                        f"chunk{i}: status={status} got={got} want={want} "
                        f"(attempt {attempt + 1})")
                except Exception as exc:
                    diagnostics.append(f"chunk{i}: {exc!r} "
                                       f"(attempt {attempt + 1})")
                time.sleep(2 * (attempt + 1))
            raise ConanException(
                "ghc bindist chunk fetch failed: " + "; ".join(diagnostics[-6:]))

        with ThreadPoolExecutor(max_workers=DL_CHUNKS) as pool:
            pool.map(fetch, range(DL_CHUNKS))

        if not os.path.exists(dest):
            with open(dest, "wb") as out:
                for i in range(DL_CHUNKS):
                    part = f"{dest}.part{i:03d}"
                    with open(part, "rb") as p:
                        shutil.copyfileobj(p, out, 1 << 20)
        for i in range(DL_CHUNKS):
            part = f"{dest}.part{i:03d}"
            if os.path.exists(part):
                os.remove(part)

        if os.path.getsize(dest) != size:
            raise ConanException(
                f"ghc bindist size mismatch: {os.path.getsize(dest)} != "
                f"{size}; diagnostics: {diagnostics[-6:]}")
        digest = hashlib.sha256()
        with open(dest, "rb") as f:
            while True:
                block = f.read(1 << 20)
                if not block:
                    break
                digest.update(block)
        if digest.hexdigest() != sha256:
            raise ConanException(
                f"ghc bindist sha256 mismatch: {digest.hexdigest()} != "
                f"{sha256}; diagnostics: {diagnostics[-6:]}")

    def _write_file(self, path, content):
        with open(path, "w", newline="\n") as f:
            f.write(content)
        os.chmod(path, 0o755)

    # ------------------------------------------------------------------
    # Toolchain bootstrap
    # ------------------------------------------------------------------

    def _bootstrap(self):
        """GHC + runtime libs + tcl + shims.  Returns env for builds."""
        b = self.build_folder
        tc = self._tc = self._toolchain_dir()
        sysroot = self._sysroot = self._resolve_sysroot(tc)

        # --- GHC bindist ---
        gb = self.conan_data["ghc_bootstrap"]
        tarball = os.path.join(b, os.path.basename(gb["url"]))
        ghc_dir = os.path.join(b, gb["topdir"])
        if not os.path.exists(os.path.join(ghc_dir, "bin", "ghc")):
            self.output.info("Fetching GHC alpine-musl bindist "
                             f"({gb['size']} bytes, {DL_CHUNKS} chunks)")
            self._parallel_fetch(gb["url"], tarball, gb["size"], gb["sha256"])
            unzip(self, tarball, b)
        hl = glob.glob(os.path.join(ghc_dir, "lib", "aarch64-linux-ghc-*"))
        if not hl:
            raise ConanException("GHC lib dir (aarch64-linux-ghc-*) not found")
        hl = hl[0]

        # --- runtime libs + tcl from alpine APKs ---
        rl = os.path.join(b, "runtime-libs")
        os.makedirs(rl, exist_ok=True)
        tcl_dir = None
        for apk in self.conan_data["ghc_runtime_libs"]:
            pkg = os.path.join(b, "apk-" + os.path.basename(apk["url"]))
            if not os.path.isdir(pkg):
                # APKs are gzip'd tarballs with an unknown-to-conan
                # extension: get() auto-extracts and dies with BadZipFile,
                # so download (checksum-verified) + tarfile here.
                apk_name = os.path.basename(apk["url"])
                apk_path = os.path.join(b, apk_name)
                if not os.path.exists(apk_path):
                    download(self, apk["url"], apk_path,
                             sha256=apk["sha256"])
                import tarfile
                with tarfile.open(apk_path) as tf:
                    tf.extractall(pkg, filter="data")
            for so in glob.glob(os.path.join(pkg, "usr", "lib", "*.so*")):
                if os.path.isfile(so):
                    shutil.copy2(so, rl)
                    self._sign_elf(os.path.join(rl, os.path.basename(so)))
            if "/tcl-" in apk["url"] and "-dev" not in apk["url"]:
                tcl_dir = pkg
        # linker names for -lgmp / -lffi (searched via the shim's -L)
        for soname, link in (("libgmp.so.10", "libgmp.so"),
                             ("libffi.so.8", "libffi.so")):
            target = os.path.join(rl, soname)
            link_path = os.path.join(rl, link)
            if os.path.exists(target) and not os.path.lexists(link_path):
                os.symlink(soname, link_path)
        # also drop them next to the RTS (GHC's own -L set)
        for rts in glob.glob(os.path.join(hl, "rts-*")):
            for soname, link in (("libgmp.so.10", "libgmp.so"),
                                 ("libffi.so.8", "libffi.so")):
                link_path = os.path.join(rts, link)
                if not os.path.lexists(link_path):
                    os.symlink(os.path.join(rl, soname), link_path)

        # tclsh (for htcl) must run: sign its ELF + library
        if tcl_dir is None:
            raise ConanException("tcl apk not processed")
        for f in glob.glob(os.path.join(tcl_dir, "usr", "bin", "tclsh*")):
            if os.path.isfile(f) and not os.path.islink(f):
                self._sign_elf(f)
        tcllib = os.path.join(tcl_dir, "usr", "lib")
        for so in glob.glob(os.path.join(tcllib, "*.so*")):
            if os.path.isfile(so):
                self._sign_elf(so)
        tclinc_pkg = os.path.join(b, "apk-tcl-dev-8.6.13-r1.apk")
        tclinc = os.path.join(tclinc_pkg, "usr", "include")

        self._sign_tree(ghc_dir)

        # --- shims ---
        shims = os.path.join(b, "shims")
        os.makedirs(shims, exist_ok=True)
        builtins = None
        for pat in (os.path.join(tc, "..", "lib", "clang", "15.0.4", "lib",
                                 "aarch64-linux-ohos",
                                 "libclang_rt.builtins.a"),
                    os.path.join(tc, "..", "lib", "clang", "15.0.4", "lib",
                                 "aarch64-unknown-linux-ohos",
                                 "libclang_rt.builtins.a")):
            import glob as _g
            hits = _g.glob(pat)
            if hits:
                builtins = hits[0]
                break
        if builtins is None:
            raise ConanInvalidConfiguration(
                "libclang_rt.builtins.a not found near " + tc)
        gcc = (GCC_SHIM.replace("__SHIMDIR__", shims)
               .replace("__TC__", tc)
               .replace("__SYSROOT__", sysroot)
               .replace("__BUILTINS__", builtins)
               .replace("__RUNTIME_LIBS__", rl)
               .replace("__DEFYSMS__", DEFYSMS))
        for name in ("gcc", "g++", "cc"):
            self._write_file(os.path.join(shims, name), gcc)
        mktemp = MKTEMP_SHIM.replace("__TC__", tc)
        self._write_file(os.path.join(shims, "mktemp"), mktemp)
        self._write_file(os.path.join(shims, "time"), TIME_SHIM)
        stubs_c = os.path.join(shims, "misc_stubs.c")
        with open(stubs_c, "w", newline="\n") as f:
            f.write(MISC_STUBS_C)
        import subprocess
        subprocess.run([os.path.join(tc, "clang-15"),
                        f"--sysroot={sysroot}",
                        "-D__MUSL__", "-c", stubs_c,
                        "-o", os.path.join(shims, "misc_stubs.o")],
                       check=True, capture_output=True, timeout=60)
        # htcl's platform.sh does `PKG_CONFIG=$(which pkg-config)` — it
        # ignores a PKG_CONFIG env var, and CI workers ship a real
        # pkg-config that knows nothing of our extracted tcl.  Provide a
        # proper tcl .pc via PKG_CONFIG_PATH (honored by any pkg-config),
        # plus a same-behavior shim for workers without one.
        pcdir = os.path.join(b, "pkgconfig")
        os.makedirs(pcdir, exist_ok=True)
        pc = ("Name: Tcl\n"
              "Description: Tcl 8.6 (alpine apk)\n"
              "Version: 8.6.13\n"
              f"Cflags: -I{tclinc}\n"
              f"Libs: -L{tcllib} -ltcl8.6\n")
        for pcname in ("tcl.pc", "tcl8.6.pc", "tcl86.pc"):
            with open(os.path.join(pcdir, pcname), "w", newline="\n") as f:
                f.write(pc)
        self._write_file(os.path.join(shims, "pkg-config"),
                         "#!/bin/sh\n"
                         "case \" $* \" in\n"
                         "  *tcl*) case \" $* \" in\n"
                         f"    *--cflags-only-I*) echo \"-I{tclinc}\" ;;\n"
                         f"    *--libs*) echo \"-L{tcllib} -ltcl8.6\" ;;\n"
                         "    *) exit 0 ;; esac ;;\n"
                         "  *) exit 1 ;;\n"
                         "esac\n")

        tmpdir = os.path.join(b, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env = Environment()
        env.prepend_path("PATH", os.path.join(ghc_dir, "bin"))
        env.prepend_path("PATH", os.path.join(tcl_dir, "usr", "bin"))
        env.prepend_path("PATH", shims)
        env.prepend_path("LD_LIBRARY_PATH", tcllib)
        env.prepend_path("LD_LIBRARY_PATH", hl)
        env.prepend_path("LD_LIBRARY_PATH", rl)
        env.define("TMPDIR", tmpdir)
        env.define("LANG", "C.UTF-8")
        env.define("OSTYPE", "linux")
        env.define("NO_DEPS_CHECKS", "1")
        env.define("STP_STUB", "1")
        env.define("YICES_STUB", "1")
        env.define("PKG_CONFIG", os.path.join(shims, "pkg-config"))
        env.define("PKG_CONFIG_PATH", pcdir)
        return ghc_dir, rl, hl, env

    def _install_hackage(self, ghc_dir, env):
        b = self.build_folder
        hdir = os.path.join(b, "hackage")
        os.makedirs(hdir, exist_ok=True)
        for pkg in self.conan_data["hackage"]:
            name, ver = pkg["name"], pkg["version"]
            pv = f"{name}-{ver}"
            self.output.info(f"Installing Hackage package {pv}")
            tarball = os.path.join(hdir, f"{pv}.tar.gz")
            if not os.path.exists(tarball):
                download(self,
                         f"https://hackage.haskell.org/package/{pv}/{pv}.tar.gz",
                         tarball, sha256=pkg["sha256"])
            pkg_dir = os.path.join(hdir, pv)
            if not os.path.isdir(pkg_dir):
                unzip(self, tarball, hdir)
            with chdir(self, pkg_dir):
                # Some Hackage packages ship Setup.lhs (literate) or no
                # Setup at all; pick what exists, inject a default only
                # when neither does.
                setup_hs = ("Setup.hs" if os.path.exists("Setup.hs")
                            else "Setup.lhs" if os.path.exists("Setup.lhs")
                            else None)
                if setup_hs is None:
                    with open("Setup.hs", "w", newline="\n") as f:
                        f.write(DEFAULT_SETUP_HS)
                    setup_hs = "Setup.hs"
                # GHC 9.12 ships base-4.21 / deepseq-1.5; old Hackage
                # packages carry stale upper bounds against both.
                # Relax every ">= X && < Y" upper bound (device-proven:
                # the full-relaxation sed is what made the real-machine
                # run pass; library builds never hit test-suite bounds).
                for cab in glob.glob("*.cabal"):
                    with open(cab, encoding="utf-8", errors="replace") as f:
                        s = f.read()
                    s2 = re.sub(r"(>=\s*[0-9.]+)\s*&&\s*<\s*[0-9.]+",
                                r"\1", s)
                    if s2 != s:
                        with open(cab, "w", newline="\n") as f:
                            f.write(s2)
                # ConanFile.run(env=...) takes env NAMES, not Environment
                # objects; apply the composed Environment via vars().apply().
                with env.vars(self, scope="build").apply():
                    for step in (
                        ["ghc", "--make", setup_hs, "-o", "setup.bin"],
                        ["./setup.bin", "configure", "--global",
                         f"--prefix={ghc_dir}"],
                        ["./setup.bin", "build"],
                        ["./setup.bin", "install"],
                    ):
                        self.run(" ".join(
                            f'"{a}"' if (" " in a or '"' in a) else a
                            for a in step))

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(self):
        ghc_dir, rl, hl, env = self._bootstrap()
        self._install_hackage(ghc_dir, env)
        src = self.source_folder
        inst = os.path.join(src, "inst")

        with env.vars(self, scope="build").apply(), chdir(self, src):
            for d in ("src/vendor/stp", "src/vendor/yices",
                      "src/vendor/htcl"):
                self.run(f'make -C {d} PREFIX="{inst}" install')
            # the Haskell core (bsc) + utility tools.  Upstream forces
            # -j1 here ("we need to build targets from here sequentially"):
            # bsc and bluetcl share build/comp artifacts and must not race.
            self.run(f'make -C src/comp -j1 PREFIX="{inst}" install')
            self.run(f'make -C src/comp PREFIX="{inst}" install-extra')
            # Bluesim primitive libraries (aarch64; official release
            # ships x86_64 archives)
            self.run(f'make -C src/bluesim PREFIX="{inst}" install')
            for d in ("src/exec", "src/VPI", "src/Verilog.Quartus",
                      "src/Verilog.Vivado", "src/Verilator"):
                self.run(f'make -C {d} PREFIX="{inst}" install')

        # --- official same-version standard library (arch-independent) ---
        b = self.build_folder
        off = self.conan_data["official_stdlib"]
        offpkg = os.path.join(b, "official")
        if not os.path.isdir(offpkg):
            # The CI mirror-fallback rewrites conandata URLs into lists of
            # [mirror, official]; handle both shapes and try each in turn.
            urls = off["url"] if isinstance(off["url"], list) else [off["url"]]
            off_tgz = os.path.join(b, os.path.basename(urls[0]))
            if not os.path.exists(off_tgz):
                last = None
                for u in urls:
                    try:
                        download(self, u, off_tgz, sha256=off["sha256"])
                        last = None
                        break
                    except Exception as exc:
                        last = exc
                if last is not None:
                    raise ConanException(
                        f"official stdlib download failed: {last}")
            # conan's unzip mangles the release tarball's lib/ layout
            # (Libraries ends up a non-directory); tarfile handles it.
            import tarfile
            with tarfile.open(off_tgz) as tf:
                tf.extractall(b, filter="data")
            # glob also matches the .tar.gz itself and its order is
            # filesystem-dependent; pick the extracted DIRECTORY only.
            cand = [d for d in glob.glob(
                os.path.join(b, "bsc-2026.01-debian-*"))
                if os.path.isdir(d)]
            if not cand:
                raise ConanException("official stdlib extraction failed")
            os.rename(cand[0], offpkg)
        for sub in ("Libraries", "Verilog", "Verilog.Quartus",
                    "Verilog.Vivado", "tcllib"):
            dst = os.path.join(inst, "lib", sub)
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(os.path.join(offpkg, "lib", sub), dst)

        # --- SAT stub fixups (upstream stub sonames) ---
        sat = os.path.join(inst, "lib", "SAT")
        stub = os.path.join(src, "src", "vendor", "stp", "lib",
                            "libstp_stub.so")
        if os.path.exists(stub):
            shutil.copy2(stub, os.path.join(sat, "libstp_stub.so"))
            self._sign_elf(os.path.join(sat, "libstp_stub.so"))
        for soname, links in (("libyices.so.2.6",
                               ("libyices.so.2", "libyices.so")),
                              ("libstp.so.1", ("libstp.so",))):
            target = os.path.join(sat, soname)
            for link in links:
                lp = os.path.join(sat, link)
                if os.path.exists(target) and not os.path.lexists(lp):
                    os.symlink(soname, lp)

        # --- compiler-level verification (no Verilog simulator needed) ---
        env.prepend_path("PATH", os.path.join(inst, "bin"))
        with env.vars(self, scope="build").apply(), chdir(self, b):
            # bsc writes generated Verilog next to the input file unless
            # told otherwise; assert there (and copy into the build root
            # for a stable record).
            src_v = os.path.join(src, "examples", "smoke_test",
                                 "mkFibOne.v")
            vfile = os.path.join(b, "mkFibOne.v")
            for f in (src_v, vfile):
                if os.path.exists(f):
                    os.remove(f)
            self.run(
                'bsc -no-show-timestamps -no-show-version -verilog '
                f'-g mkFibOne "{src}/examples/smoke_test/FibOne.bsv"')
            if not os.path.exists(src_v):
                raise ConanException("bsc did not produce mkFibOne.v")
            shutil.copy2(src_v, vfile)
            self._fibone_v = vfile

    # ------------------------------------------------------------------
    # Package
    # ------------------------------------------------------------------

    def package(self):
        src = self.source_folder
        b = self.build_folder
        copy(self, "*", os.path.join(src, "inst", "bin"),
             os.path.join(self.package_folder, "bin"))
        copy(self, "*", os.path.join(src, "inst", "lib"),
             os.path.join(self.package_folder, "lib"))
        # musl runtime deps for the shipped binaries (VirtualRunEnv adds
        # lib/ to LD_LIBRARY_PATH)
        copy(self, "*.so*", os.path.join(b, "runtime-libs"),
             os.path.join(self.package_folder, "lib"))
        # Provenance/build-contract files (kept for auditability).
        for pattern in CONTRACT_FILES:
            copy(self, pattern, src=src, dst=self.package_folder)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib"]
