#!/usr/bin/env python3
"""Conan recipe — liboprf 0.9.4 (raw makefile, OPRF library).

liboprf implements OPRF(ristretto255, SHA-512) per RFC 9497 plus threshold
OPRF variants on top of libsodium. Upstream builds with a handwritten
makefile in src/ (lowercase "makefile", no configure step) and a vendorized
noise_xk sub-make. The makefile hard-requires the pkgconf binary for its
libsodium version probe, provided via tool_requires("pkgconf/3.0.5").

Vendored libsodium (no external requires): preflight proves any
requires("libsodium/...") is shadowed — conancenter also carries the
1.0.20/1.0.22 recipe revisions ("Downloaded recipe revision ... from
conancenter"), so no OHOS binary matches and the device falls back to an
on-device autotools source build that dies at
"configure[139/142]: /data/service/hnp/bin/bash: inaccessible" (profile
CONFIG_SHELL=/data/service/hnp/bin/bash missing on the runner, exit 127)
plus read-only /tmp (libequihash 1.0.10 / libmacaroons 0.3.0 notes).
Pinning any version cannot fix shadowing. The official libsodium-1.0.20
release tarball (same URL/SHA as archives/l/libsodium 1.0.20) is therefore
vendored via conandata "sodium" entry and built inside build() to a
private staging prefix with /bin/sh (HMBS shell, never the profile hnp
bash), HMBS TMPDIR, probed CC/AR, the umask-022 relaxation, plus the same
build-aux/config.guess (HarmonyOS uname) + config.sub (linux-ohos)
recognition as archives/l/libsodium 1.0.20 patches 0001/0002 so configure
guesses natively (native build, no --build/--host). A staged
libsodium.pc satisfies the makefile's pkgconf probe. Main sources then
compile against the staging prefix with CPPFLAGS/LDFLAGS; package() ships
both libs. Single-package PR, no remote involved. 1.0.20 satisfies the
makefile's HAVE_SODIUM_HKDF gate (>= 1.0.19), so no aux_ fallback needed.

The upstream suite (src/tests, 11 binaries) runs at the end of build() and
emits HMBS_UPSTREAM_TEST_RESULT with output-derived numbers.
"""
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rm
from conan.tools.layout import basic_layout


class LiboprfConan(ConanFile):
    name = "liboprf"
    version = "0.9.4"
    description = "Oblivious Pseudorandom Function (OPRF) and threshold OPRF library based on libsodium"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/stef/liboprf"
    url = "https://github.com/stef/liboprf"
    topics = ("crypto", "oprf", "ristretto255", "threshold")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Intentionally no external requires: libsodium is vendored to a
        # private staging prefix (see conandata "sodium"). Any requires()
        # reintroduces dual-remote shadowing (conancenter recipe wins, no
        # OHOS binary, doomed on-device autotools build needing hnp bash).
        pass

    def build_requirements(self):
        self.tool_requires("pkgconf/3.0.5")

    def layout(self):
        basic_layout(self)

    def generate(self):
        VirtualBuildEnv(self).generate()

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def _candidate_compilers(self):
        # PATH-first ordering: hmbs puts its tool dirs at the front of
        # PATH, so `cc`/`clang` found via PATH reflect the device-side
        # reality. The profile absolute hnp path is kept as a fallback
        # but is only used after it proves executable (--version check).
        cands = []
        env_cc = os.environ.get("CC")
        if env_cc:
            cands.append(env_cc)
        for name in ("cc", "clang"):
            try:
                found = shutil.which(name)
            except Exception:
                found = None
            if found:
                cands.append(found)
        try:
            exes = self.conf.get("tools.build:compiler_executables")
            if isinstance(exes, dict):
                for key in ("c", "C"):
                    val = exes.get(key)
                    if val:
                        cands.append(val)
        except Exception:
            pass
        for fallback in ("/data/service/hnp/bin/clang", "cc", "clang"):
            cands.append(fallback)
        seen = []
        for cand in cands:
            if cand and cand not in seen:
                seen.append(cand)
        return seen

    def _compiler_works(self, cand):
        env = dict(os.environ)
        tmpdir = env.get("TMPDIR") or env.get("TMP") or env.get("TEMP")
        if tmpdir:
            env["TMPDIR"] = tmpdir
            env["TMP"] = tmpdir
            env["TEMP"] = tmpdir
        try:
            proc = subprocess.run([cand, "--version"],
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT,
                                  timeout=30, env=env)
            if proc.returncode == 0:
                return True, proc.stdout.decode("utf-8", "ignore")[:200]
            return False, "exit=%d %s" % (
                proc.returncode, proc.stdout.decode("utf-8", "ignore")[:200])
        except Exception as exc:
            return False, "%s: %s" % (type(exc).__name__, exc)

    def _resolve_cc(self):
        tried = []
        for cand in self._candidate_compilers():
            ok, detail = self._compiler_works(cand)
            tried.append("%s (%s)" % (cand, detail.replace("\n", " ")[:120]))
            if ok:
                self.output.info("selected working cc=%s" % cand)
                return cand
            self.output.info("cc candidate unusable: %s: %s" % (cand, detail[:200]))
        raise ConanException(
            "no working C compiler on device; tried: %s" % "; ".join(tried))

    def _resolve_ar(self, cc):
        cands = []
        if os.path.isabs(cc):
            bindir = os.path.dirname(cc)
            for name in ("llvm-ar", "ar"):
                cands.append(os.path.join(bindir, name))
        for name in ("llvm-ar", "ar"):
            try:
                found = shutil.which(name)
            except Exception:
                found = None
            if found:
                cands.append(found)
        cands.append("ar")
        seen = []
        for cand in cands:
            if cand and cand not in seen:
                seen.append(cand)
        for cand in seen:
            try:
                if os.path.isabs(cand):
                    if os.path.isfile(cand) and os.access(cand, os.X_OK):
                        self.output.info("selected ar=%s" % cand)
                        return cand
                    continue
                if shutil.which(cand):
                    self.output.info("selected ar=%s" % cand)
                    return cand
            except Exception:
                continue
        return "ar"

    def _resolve_sh(self):
        # HMBS shell is /bin/sh; never use the profile hnp bash here.
        for cand in (os.environ.get("HMBS_SHELL"), "/bin/sh", "sh"):
            if not cand:
                continue
            if os.path.isabs(cand):
                if os.path.isfile(cand):
                    return cand
                continue
            found = shutil.which(cand)
            if found:
                return found
        return "/bin/sh"

    def _resolve_make(self):
        for cand in (os.environ.get("HMBS_MAKE"), shutil.which("make"), "make"):
            if not cand:
                continue
            if os.path.isabs(cand):
                if os.path.isfile(cand):
                    self.output.info("selected make=%s" % cand)
                    return cand
                continue
            if shutil.which(cand):
                self.output.info("selected make=%s" % cand)
                return cand
        return "make"

    def _sodium_src(self):
        # NOTE: fetched in build() (not source()) on purpose: the device
        # Conan layout does not expose base_source_folder here, and keeping
        # the vendored tree under build_folder avoids any source_layout
        # attribute mismatch across Conan revisions.
        return os.path.join(self.build_folder, "sodium_src")

    def _ensure_vendored_sodium_src(self):
        src = self._sodium_src()
        if os.path.isfile(os.path.join(src, "configure")):
            return src
        os.makedirs(src, exist_ok=True)
        get(self, **self.conan_data["sources"]["sodium"],
            strip_root=True, destination=src)
        return src

    def _sodium_prefix(self):
        return os.path.join(self.build_folder, "sodium_prefix")

    def _relax_configure_umask(self, src):
        # Same HMDFS fix as archives/l/libsodium: configure's umask 077
        # temp dirs fail under UID mapping; 022 works. Only the temp-dir
        # root is changed, tests are untouched.
        path = os.path.join(src, "configure")
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except OSError as exc:
            raise ConanException("vendored sodium configure missing: %s" % exc)
        if "umask 077" in content:
            content = content.replace("umask 077", "umask 022")
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
            self.output.info("[ok] relaxed vendored configure umask 077 -> 022")
        else:
            self.output.info("[ok] vendored configure umask already relaxed/absent")

    def _patch_vendored_config_aux(self, src):
        # Native device build: teach vendored config.guess/sub to recognize
        # HarmonyOS so configure guesses natively. Same edits as
        # archives/l/libsodium/1.0.20 patches 0001/0002. No --build/--host
        # flags are passed (native build; forcing triplets would falsely
        # mark cross_compiling=yes and break AC_RUN_IFELSE per P-AUTOTOOLS-001).
        import glob as _glob
        guess_snippet = (
            "    *:HarmonyOS:*:*)\n"
            "\tcase \"$UNAME_MACHINE\" in\n"
            "\t    aarch64|arm64) machine=aarch64 ;;\n"
            "\t    armv7*|armv8*) machine=arm ;;\n"
            "\t    x86_64|amd64) machine=x86_64 ;;\n"
            "\t    i?86) machine=i686 ;;\n"
            "\t    *) machine=\"$UNAME_MACHINE\" ;;\n"
            "\tesac\n"
            "\tGUESS=${machine}-unknown-linux-ohos\n"
            "\t;;\n"
        )
        guess_targets = set(
            _glob.glob(os.path.join(src, "**", "config.guess"), recursive=True))
        for rel in ("build-aux/config.guess", "config.guess"):
            guess_targets.add(os.path.join(src, rel))
        for path in sorted(guess_targets):
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except OSError:
                continue
            if "HarmonyOS" in content:
                self.output.info("[ok] config.guess already knows HarmonyOS: %s" % path)
                continue
            marker = "    *:NetBSD:*:*)"
            if marker in content:
                content = content.replace(marker, guess_snippet + marker, 1)
                with open(path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(content)
                self.output.info("[ok] patched HarmonyOS into %s" % path)
            else:
                self.output.info("config.guess marker missing, skipped: %s" % path)
        sub_targets = set(
            _glob.glob(os.path.join(src, "**", "config.sub"), recursive=True))
        for rel in ("build-aux/config.sub", "config.sub"):
            sub_targets.add(os.path.join(src, rel))
        for path in sorted(sub_targets):
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except OSError:
                continue
            orig = content
            if "ohos*" not in content:
                content = content.replace(
                    "gnu* | android* | bsd*",
                    "gnu* | android* | ohos* | bsd*",
                    1,
                )
            if "linux-ohos*-" not in content:
                content = content.replace(
                    "linux-gnu*- | linux-android*- |",
                    "linux-gnu*- | linux-android*- | linux-ohos*- |",
                    1,
                )
            if content != orig:
                with open(path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(content)
                self.output.info("[ok] patched ohos triplet into %s" % path)
            else:
                self.output.info("[ok] config.sub already accepts ohos or pattern absent: %s" % path)

    def _stage_vendored_sodium(self, src, prefix):
        # HMBS platform caps on this device: chmod=0, hardlink=0
        # (HMBS_PLATFORM_CAPABILITIES in preflight). The vendored
        # `make install` dies at install-nobase_includeHEADERS with
        # `install -c -m 644 ... Error 64` because the install shim
        # cannot chmod on HMDFS. Stage by hand with pure-Python
        # copyfile (no chmod/hardlink/mode preservation): the static
        # archive plus the exact public headers, plus a libsodium.pc so
        # the liboprf makefile's `pkgconf --exists/--atleast-version`
        # probe passes. `make -j1` above already succeeded, so the
        # artifacts exist in-tree.
        import glob as _glob
        libdir = os.path.join(prefix, "lib")
        incdir = os.path.join(prefix, "include")
        pcdir = os.path.join(libdir, "pkgconfig")
        os.makedirs(libdir, exist_ok=True)
        os.makedirs(os.path.join(incdir, "sodium"), exist_ok=True)
        os.makedirs(pcdir, exist_ok=True)
        cands = []
        for pat in (os.path.join(src, "src", "libsodium", ".libs", "libsodium.a"),
                    os.path.join(src, "**", ".libs", "libsodium.a"),
                    os.path.join(src, "**", "libsodium.a")):
            for hit in _glob.glob(pat, recursive=True):
                if os.path.isfile(hit) and hit not in cands:
                    cands.append(hit)
        # Prefer the largest archive (real build output, not a stub).
        cands.sort(key=lambda p: os.path.getsize(p) if os.path.isfile(p) else 0,
                   reverse=True)
        if not cands:
            raise ConanException(
                "vendored sodium built but no libsodium.a found under %s" % src)
        built = cands[0]
        if os.path.getsize(built) == 0:
            raise ConanException("vendored sodium archive is empty: %s" % built)
        dest_lib = os.path.join(libdir, "libsodium.a")
        with open(built, "rb") as fin, open(dest_lib, "wb") as fout:
            shutil.copyfileobj(fin, fout, length=1024 * 1024)
        if os.path.getsize(dest_lib) == 0:
            raise ConanException("staged libsodium.a is empty: %s" % dest_lib)
        # Public headers live in src/libsodium/include in the release
        # tarball (sodium.h + sodium/*.h). Copy contents only, no modes.
        hdr_root = os.path.join(src, "src", "libsodium", "include")
        if not os.path.isdir(hdr_root):
            raise ConanException(
                "vendored sodium include root missing: %s" % hdr_root)
        staged = 0
        top_h = os.path.join(hdr_root, "sodium.h")
        if os.path.isfile(top_h):
            with open(top_h, "rb") as fin, \
                    open(os.path.join(incdir, "sodium.h"), "wb") as fout:
                shutil.copyfileobj(fin, fout, length=1024 * 1024)
            staged += 1
        sodium_dir = os.path.join(hdr_root, "sodium")
        for name in sorted(os.listdir(sodium_dir)):
            spath = os.path.join(sodium_dir, name)
            if not os.path.isfile(spath) or not name.endswith(".h"):
                continue
            with open(spath, "rb") as fin, \
                    open(os.path.join(incdir, "sodium", name), "wb") as fout:
                shutil.copyfileobj(fin, fout, length=1024 * 1024)
            staged += 1
        if staged < 5 or not os.path.isfile(os.path.join(incdir, "sodium.h")):
            raise ConanException(
                "staged too few sodium headers (%d) from %s" % (staged, hdr_root))
        # Minimal libsodium.pc for the liboprf makefile probe.
        with open(os.path.join(pcdir, "libsodium.pc"), "w", encoding="utf-8", newline="\n") as f:
            f.write("prefix=%s\n" % prefix)
            f.write("exec_prefix=${prefix}\n")
            f.write("libdir=${prefix}/lib\n")
            f.write("includedir=${prefix}/include\n")
            f.write("\n")
            f.write("Name: libsodium\n")
            f.write("Description: vendored libsodium for liboprf (no external requires)\n")
            f.write("Version: 1.0.20\n")
            f.write("Libs: -L${libdir} -lsodium\n")
            f.write("Cflags: -I${includedir}\n")
        self.output.info("[ok] staged vendored sodium without make install: "
                         "%s (%d bytes) + %d headers + libsodium.pc" % (
                             dest_lib, os.path.getsize(dest_lib), staged))

    def _build_vendored_sodium(self, cc, ar, tmpdir):
        src = self._ensure_vendored_sodium_src()
        prefix = self._sodium_prefix()
        if not os.path.isfile(os.path.join(src, "configure")):
            try:
                listing = sorted(os.listdir(src))[:20]
            except OSError:
                listing = []
            raise ConanException(
                "vendored sodium sources missing configure; listing: %s" % listing)
        self._relax_configure_umask(src)
        self._patch_vendored_config_aux(src)
        sh = self._resolve_sh()
        make = self._resolve_make()
        self.output.info("vendored sodium: sh=%s make=%s cc=%s ar=%s prefix=%s"
                         % (sh, make, cc, ar, prefix))
        cfg = ("%s ./configure --prefix='%s' --disable-shared --enable-static "
               "--disable-dependency-tracking" % (sh, prefix))
        # Drive configure through /bin/sh with HMBS TMPDIR and probed tools.
        # CC/AR/SHELL/CONFIG_SHELL are exported inline so the profile hnp
        # bash path is never executed.
        env_prefix = ("CC='%s' AR='%s' SHELL='%s' CONFIG_SHELL='%s' "
                      "TMPDIR='%s' TMP='%s' TEMP='%s' "
                      % (cc, ar, sh, sh, tmpdir, tmpdir, tmpdir))
        self.run(env_prefix + cfg, cwd=src, env="conanbuild")
        self.run(env_prefix + "%s -j1" % make, cwd=src, env="conanbuild")
        # NOTE: no `make install` here (chmod=0/hardlink=0 install-shim
        # failure); stage the archive and headers with pure-Python copies.
        self._stage_vendored_sodium(src, prefix)
        lib = os.path.join(prefix, "lib", "libsodium.a")
        if not os.path.isfile(lib):
            alt = os.path.join(prefix, "lib64", "libsodium.a")
            if os.path.isfile(alt):
                lib = alt
            else:
                raise ConanException("vendored sodium build produced no libsodium.a")
        self.output.info("[ok] vendored sodium installed: %s" % lib)
        return prefix

    def _make_flags(self, prefix, cc, ar):
        """Compiler and vendored-staging paths for the raw makefile.

        R33: compiler comes from probed working cc (PATH-first, profile
        absolute path only as verified fallback), never from shell env.
        CPPFLAGS and LDFLAGS are passed as make command-line variables; the
        upstream makefile only reads them (never assigns), so nothing is
        overridden. CFLAGS is otherwise left alone so the makefile's own
        hardening (-fstack-protector-strong, -D_FORTIFY_SOURCE=3,
        -Wl,-z,...) stays intact, except the GCC-only
        -fstack-clash-protection token stripped by _patch_stack_clash
        (OHOS clang-15 rejects it under the makefile's -Werror).
        """
        inc = os.path.join(prefix, "include")
        lib = os.path.join(prefix, "lib")
        return 'CC="%s" AR="%s" CPPFLAGS="-I%s" LDFLAGS="-L%s"' % (cc, ar, inc, lib)

    def _patch_stack_clash(self):
        # OHOS device compiler is clang-15, which rejects the GCC-only
        # -fstack-clash-protection flag; noise_xk/makefile builds with
        # global -Werror, so the "unused during compilation" warning
        # becomes a fatal error (preflight: makefile:85 Error 1).
        # Upstream appends the flag in src/makefile, src/noise_xk/makefile
        # and src/tests/makefile for every non-Darwin non-parisc arch, so
        # command-line ARCH/CFLAGS overrides cannot suppress it (the ?= base
        # would be lost while += still appends). Strip only the offending
        # token in-code (libmacaroons config.guess precedent, no patches/
        # dir); all other hardening flags stay intact. Idempotent.
        for rel in ("src/makefile", "src/noise_xk/makefile", "src/tests/makefile"):
            path = os.path.join(self.source_folder, rel)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except OSError:
                self.output.info("[ok] makefile absent, skipped: %s" % rel)
                continue
            if "fstack-clash-protection" not in content:
                self.output.info("[ok] no stack-clash flag in %s" % rel)
                continue
            stripped = content.replace("-fstack-clash-protection", "")
            if stripped != content:
                with open(path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(stripped)
                self.output.info("[ok] stripped -fstack-clash-protection from %s "
                                 "(OHOS clang-15 rejects it under -Werror)" % rel)

    def _patch_tests_ldflags(self):
        # src/tests/makefile ignores LDFLAGS on 7 link rules (tv1, tv2,
        # toprf, mpmult, toprf-update/-corrupt, update-poc/ft-mult): they
        # expand $(CC) $(CPPFLAGS) $(CFLAGS) ... -lsodium with no
        # $(LDFLAGS), so the vendored staging -L never reaches the linker
        # and tv1 dies first with `ld.lld: unable to find library
        # -lsodium` even though src/ links fine (it uses $(LDFLAGS)
        # $(LIBS)). dkg/tp-dkg/stp-dkg already reference $(LDFLAGS) and are
        # left unchanged by the dedupe step. In-code edit (same precedent
        # as _patch_stack_clash, no patches/ dir); test sources and the 11
        # run invocations are untouched. Idempotent.
        path = os.path.join(self.source_folder, "src", "tests", "makefile")
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except OSError:
            self.output.info("[ok] tests makefile absent, skipped LDFLAGS patch")
            return
        patched = content.replace(" -lsodium", " $(LDFLAGS) -lsodium")
        while "$(LDFLAGS) $(LDFLAGS)" in patched:
            patched = patched.replace("$(LDFLAGS) $(LDFLAGS)", "$(LDFLAGS)")
        if patched != content:
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(patched)
            self.output.info("[ok] patched $(LDFLAGS) into src/tests/makefile "
                             "link rules missing it (tv1/tv2/toprf/mpmult/update)")
        else:
            self.output.info("[ok] src/tests/makefile already carries $(LDFLAGS)")

    def _patch_tests_heap(self):
        # OHOS stack overflow: the 6 threshold tests (tp-dkg/stp-dkg/
        # toprf-update, each plain + corrupt) segfault with rc=-11
        # (SIGSEGV) on device while the 5 small tests pass. Root cause is
        # `uint8_t network_buf[n+1][NETWORK_BUF_SIZE]` (16MB per slot) on
        # main()'s stack: 4*16=64MB for tp-dkg 3 2, 10*16=160MB for
        # stp-dkg/toprf-update 9 4. Upstream relies on
        # `(ulimit -s 66000 / 1966000; ./...)` to raise RLIMIT_STACK, but
        # the device hard limit rejects ~1.9GB so the stack stays small
        # and the first touch of the buffer faults. Fix: allocate the
        # identical buffer on the heap (same size, same send/recv logic,
        # compatible with the `uint8_t [][NETWORK_BUF_SIZE]` fuzz_loop
        # parameters); protocol, assertions and the 11-run invocation
        # count are untouched. In-code edit, same precedent as
        # _patch_stack_clash, no patches/ dir. Idempotent.
        for rel in ("src/tests/tp-dkg.c", "src/tests/stp-dkg.c",
                    "src/tests/toprf-update.c"):
            path = os.path.join(self.source_folder, rel)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
            except OSError:
                self.output.info("[ok] test source absent, skipped heap patch: %s" % rel)
                continue
            orig = content
            if "#include <stdlib.h>" not in content:
                content = content.replace(
                    "#include <stdio.h>",
                    "#include <stdio.h>\n#include <stdlib.h>", 1)
            old_decl = "  uint8_t network_buf[n+1][NETWORK_BUF_SIZE];"
            if old_decl in content:
                new_decl = (
                    "  uint8_t (*network_buf)[NETWORK_BUF_SIZE] =\n"
                    "      malloc(((size_t) n + 1) * NETWORK_BUF_SIZE);\n"
                    "  if (!network_buf) {\n"
                    "    fprintf(stderr, \"network_buf malloc failed\\n\");\n"
                    "    return 1;\n"
                    "  }")
                content = content.replace(old_decl, new_decl, 1)
            if content != orig:
                with open(path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(content)
                self.output.info("[ok] moved network_buf to heap in %s "
                                 "(OHOS stack limit, same 16MB*(n+1) size)" % rel)
            else:
                self.output.info("[ok] network_buf already on heap or pattern absent: %s" % rel)

    def build(self):
        # HMBS-injected writable tmp (device /tmp is read-only erofs).
        tmpdir = os.environ.get("TMPDIR") or os.path.join(self.build_folder, ".tmp")
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir
        self._patch_stack_clash()
        self._patch_tests_ldflags()
        self._patch_tests_heap()
        cc = self._resolve_cc()
        ar = self._resolve_ar(cc)
        make = self._resolve_make()
        sodium_prefix = self._build_vendored_sodium(cc, ar, tmpdir)
        # Expose staged libsodium.pc to the makefile's pkgconf probe.
        pc_dir = os.path.join(sodium_prefix, "lib", "pkgconfig")
        prev_pc = os.environ.get("PKG_CONFIG_PATH", "")
        os.environ["PKG_CONFIG_PATH"] = pc_dir + (os.pathsep + prev_pc if prev_pc else "")
        os.environ["PKG_CONFIG_LIBDIR"] = pc_dir
        # Belt-and-braces: compiler library search path for any link rule
        # that still ignores $(LDFLAGS); harmless when LDFLAGS already works.
        try:
            _sodium_lib = os.path.join(sodium_prefix, "lib")
            _prev_lp = os.environ.get("LIBRARY_PATH", "")
            os.environ["LIBRARY_PATH"] = _sodium_lib + (os.pathsep + _prev_lp if _prev_lp else "")
        except Exception:
            pass
        flags = self._make_flags(sodium_prefix, cc, ar)
        src_dir = os.path.join(self.source_folder, "src")
        # -j1: OHOS sandbox has no mkfifo jobserver support (opensp precedent).
        self.run('%s -C "%s" %s all -j1' % (make, src_dir, flags), env="conanbuild")
        self._run_upstream_tests(flags, make)

    def _run_upstream_tests(self, flags, make="make"):
        """Build and run the upstream src/tests suite, emit the HMBS marker.

        Source audit (src/tests/makefile, tag v0.9.4): `all` builds 11 test
        binaries; the `tests` target runs exactly these 11 invocations.
        Per-case contracts (read from the makefile, not assumed):
        tp-dkg-corrupt and stp-dkg-corrupt are wrapped with `|| exit 0`
        (informational: either exit keeps `make tests` green; a nonzero
        exit means the injected corruption was detected, exit 1 via the
        cheater path); toprf-update-corrupt has NO `|| exit 0`, i.e.
        upstream requires exit 0 — confirmed by src/toprf-update.c, where
        the UNITTEST_CORRUPT helper states the corruption "does not
        influence the outcome of the protocol ... but the end result is
        correct!". Heavy threshold tests mirror upstream's `ulimit -s`
        wrapper. Numbers in the marker come from the real exits observed;
        crashes (signals/128+ exits) never count as "detected".
        """
        tests_dir = os.path.join(self.source_folder, "src", "tests")
        self.run('%s -C "%s" %s all -j1' % (make, tests_dir, flags), env="conanbuild")
        # (argv, shell prefix for stack size, expect exit 0?)
        cases = [
            (["./dkg"], None, True),
            (["./tv1"], None, True),
            (["./tv2"], None, True),
            (["./toprf"], None, True),
            (["./mpmult"], None, True),
            (["./tp-dkg", "3", "2"], "ulimit -s 66000; ", True),
            (["./tp-dkg-corrupt", "3", "2"], "ulimit -s 66000; ", False),
            (["./stp-dkg", "9", "4"], "ulimit -s 1966000; ", True),
            (["./stp-dkg-corrupt", "9", "4"], "ulimit -s 1966000; ", False),
            (["./toprf-update", "9", "4"], "ulimit -s 1966000; ", True),
            # Upstream `tests` target has no `|| exit 0` here: exit 0 required.
            (["./toprf-update-corrupt", "9", "4"], "ulimit -s 1966000; ", True),
        ]
        discovered = len(cases)
        executed = 0
        passed = 0
        failed = 0
        commands = []
        records = []
        for argv, prefix, expect_zero in cases:
            if prefix:
                cmd = ["sh", "-c", prefix + "exec " + subprocess.list2cmdline(argv)]
                shown = "(ulimit stack) " + " ".join(argv)
            else:
                cmd = argv
                shown = " ".join(argv)
            commands.append(shown)
            # Stream output line-by-line so the SSH/preflight session sees
            # continuous progress: the heavy threshold cases (stp-dkg 9 4,
            # toprf-update 9 4) run for many minutes with no shell output,
            # and the previous buffering subprocess.run() left the session
            # idle until each case finished (preflight died with
            # "Connection ... closed by remote host" right after the
            # src/tests link lines). Same pass/fail semantics, only the
            # transport changes; numbers still come from real exits.
            self.output.info("[upstream] start: %s (expect %s)" % (
                shown, "exit 0" if expect_zero else "nonzero exit"))
            import time as _time
            run_env = dict(os.environ)
            tmpd = run_env.get("TMPDIR") or run_env.get("TMP") or run_env.get("TEMP")
            if tmpd:
                run_env["TMPDIR"] = tmpd
                run_env["TMP"] = tmpd
                run_env["TEMP"] = tmpd
            try:
                proc = subprocess.Popen(
                    cmd, cwd=tests_dir, stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT, text=True, bufsize=1,
                    env=run_env)
            except Exception as exc:
                self.output.error("upstream test spawn failed: %s: %s" % (shown, exc))
                failed += 1
                continue
            lines = []
            last_beat = _time.monotonic()
            rc = None
            try:
                assert proc.stdout is not None
                for line in proc.stdout:
                    lines.append(line)
                    # Echo progress incrementally to keep preflight alive.
                    self.output.info("[upstream %s] %s" % (shown, line.rstrip()[-2000:]))
                    last_beat = _time.monotonic()
                try:
                    rc = proc.wait(timeout=1500)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    try:
                        proc.wait(timeout=30)
                    except Exception:
                        pass
                    rc = None
            except Exception as exc:
                try:
                    proc.kill()
                except Exception:
                    pass
                self.output.error("upstream test read failed: %s: %s" % (shown, exc))
                failed += 1
                continue
            if rc is None:
                self.output.error("upstream test timed out: %s" % shown)
                failed += 1
                continue
            executed += 1
            out = "".join(lines)
            tail = "\n".join(out.splitlines()[-8:])
            self.output.info("%s exit=%d\n%s" % (shown, rc, tail))
            if expect_zero:
                ok = (rc == 0)
            else:
                # Negative tests: cheater detection exits 1 via main's
                # `return 1` on cheater_len>0. A crash (negative returncode
                # from signals, or 128+ shell exits, e.g. stack overflow
                # from the 16MB x (n+1) network_buf VLA) must NOT count as
                # "corruption detected". Accept only ordinary error exits.
                ok = (rc is not None and 1 <= rc <= 125)
            records.append({"name": shown, "expect": "exit 0" if expect_zero else "nonzero exit",
                            "rc": rc, "ok": bool(ok)})
            if ok:
                passed += 1
            else:
                failed += 1
                self.output.warning(
                    "upstream test unexpected exit: %s rc=%d (expected %s)" % (
                        shown, rc,
                        "0" if expect_zero else "nonzero"))
        status = "passed" if (failed == 0 and discovered > 0 and executed == discovered) else "failed"
        marker = {
            "status": status,
            "framework": "custom",
            "command": "%s -C src/tests all && " % make + " && ".join(commands),
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
            "cases": records,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))
        try:
            with open(os.path.join(self.build_folder,
                                   "hmbs_upstream_result.json"),
                      "w", encoding="utf-8", newline="\n") as f:
                json.dump(marker, f, ensure_ascii=False, indent=2)
                f.write("\n")
        except OSError as exc:
            self.output.warning("cannot persist upstream result: %s" % exc)
        if status != "passed":
            raise ConanException(
                "upstream test suite failed: passed=%d/%d" % (passed, discovered))

    def package(self):
        make = self._resolve_make()
        src_dir = os.path.join(self.source_folder, "src")
        # PREFIX=/ + DESTDIR lays out <package>/lib, <package>/include/oprf,
        # <package>/lib/pkgconfig directly (both makefiles honor them).
        self.run(
            '%s -C "%s" install PREFIX=/ DESTDIR="%s" -j1' % (make, src_dir, self.package_folder),
            env="conanbuild")
        # Ship the vendored sodium static lib alongside (private staging
        # becomes part of this package; no external requires).
        prefix = self._sodium_prefix()
        for libdir in ("lib", "lib64"):
            srcdir = os.path.join(prefix, libdir)
            if os.path.isfile(os.path.join(srcdir, "libsodium.a")):
                copy(self, "libsodium.a", src=srcdir,
                     dst=os.path.join(self.package_folder, "lib"))
                break
        inc = os.path.join(prefix, "include")
        if os.path.isdir(os.path.join(inc, "sodium")):
            copy(self, "*.h", src=os.path.join(inc, "sodium"),
                 dst=os.path.join(self.package_folder, "include", "sodium"))
            if os.path.isfile(os.path.join(inc, "sodium.h")):
                copy(self, "sodium.h", src=inc,
                     dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        # Respect the shared option so consumers link the intended artifact.
        # Upstream `make install` ships both .a and .so(.0) unconditionally;
        # leaving the .so in a shared=False package makes `-loprf` prefer
        # the shared object, and the OHOS loader ignores LD_LIBRARY_PATH,
        # so test_package fell back to a stale system liboprf.so.0
        # (preflight: "Error loading shared library liboprf.so.0" +
        # "oprf_KeyGen: symbol not found", rc=127). Filter here; the
        # test_package additionally links static archives by absolute path.
        try:
            libdir = os.path.join(self.package_folder, "lib")
            if self.options.shared:
                rm(self, "*.a", libdir)
                self.output.info("[ok] shared=True: removed static archives")
            else:
                rm(self, "*.so*", libdir)
                self.output.info("[ok] shared=False: removed shared objects")
        except Exception as exc:
            self.output.warning("cannot filter lib artifacts: %s" % exc)
        try:
            src_json = os.path.join(self.build_folder, "hmbs_upstream_result.json")
            if os.path.isfile(src_json):
                copy(self, "hmbs_upstream_result.json", src=self.build_folder,
                     dst=os.path.join(self.package_folder, "share", "liboprf"))
                self.output.info("[ok] packaged hmbs_upstream_result.json")
        except Exception as exc:
            self.output.warning("cannot package upstream result: %s" % exc)

    def package_info(self):
        # liboprf.so/.a implement the OPRF API and link against the bundled
        # noise XK transport (liboprf-noiseXK.so/.a) plus the vendored
        # libsodium static archive shipped in the same package; keep link
        # order so consumers link -loprf -loprf-noiseXK -lsodium.
        self.cpp_info.libs = ["oprf", "oprf-noiseXK", "sodium"]
        self.cpp_info.set_property("pkg_config_name", "liboprf")
