#!/usr/bin/env python3
"""Conan recipe -- libopaque 1.0.1 (direct C build + vendored liboprf/libsodium).

Upstream: https://github.com/stef/libopaque (tag v1.0.1).
libopaque implements the OPAQUE asymmetric password-authenticated
key-exchange (IRTF CFRG draft). It hard-depends on libsodium and on
liboprf (https://github.com/stef/liboprf).

Dependency strategy (single-package PR, no external requires):
- liboprf has no recipe in this repository and is not published to the
 制品仓, so it cannot be a requires() (R36/PF4). Its 0.9.4 release
  tarball (same API generation Debian pairs with libopaque 1.0.1:
  liboprf-dev >= 0.3.2, sid ships 0.9.4) is vendored via conandata and
  its three portable core sources (oprf.c, toprf.c, utils.c) are
  compiled directly. Files needing Zephyr/noise backends (dkg.c,
  tp-dkg.c, stp-dkg.c, mpmult.c, toprf-update.c, jni.c) are not part of
  the core OPAQUE protocol and are intentionally not built.
- libsodium/1.0.22 is not published to the ohpcd 制品仓 either, and a
  conan requires() would reintroduce the dual-remote shadowing that
  broke earlier sodium consumers (see archives/m/minisign/0.12). The
  official 1.0.22 release tarball (same URL/SHA as
  archives/l/libsodium/1.0.22) is therefore vendored and built to a
  private staging prefix, following the proven archives/l/libmacaroons
  0.3.0 pattern (private prefix, /bin/sh, HMBS TMPDIR, umask-022
  relaxation, config.guess/config.sub HarmonyOS recognition).

Upstream build system: a hand-written src/makefile using -march=native,
sanitizers and pkgconf probes, none of which is portable to the
HarmonyOS device. This recipe compiles the exact upstream source files
directly with a working device compiler instead, with minimal portable
flags (-O2 -fPIC -std=c99 -DHAVE_SODIUM_HKDF=1); no upstream source is
modified, so no patches/ directory is needed.

Upstream tests (run in build(), see _run_upstream_tests):
- src/tests/opaque-test.c: end-to-end 1-step + 4-step registration and
  full AKE with shared-secret comparison (1 program).
- src/tests/opaque-munit.c: munit parameter matrix 2 pwdU x 2 idU x 2
  idS x 4 registration types = 32 cases.
- src/tests/opaque-testvectors.c (CFRG vectors) is intentionally not
  run: upstream itself builds it only when OPRFHOME (a liboprf git
  checkout with generated test headers) exists, and its result is
  ignored (`|| true`). The vendored release tarball has no generated
  vector headers. See notes.md.

OHOS notes:
- HMBS env (SHELL/TMPDIR/HMBS_*_PATH) is reused as injected; no
  per-recipe environment reinvention beyond the private prefixes.
"""

import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import copy, export_conandata_patches, get, rm
from conan.tools.layout import basic_layout

# Exact core OPRF sources needed by opaque.c (see notes.md audit).
_OPRF_SOURCES = ["oprf.c", "toprf.c", "utils.c"]
_OPRF_HEADERS = ["oprf.h", "toprf.h"]

# Exact upstream libopaque library sources (src/makefile @ v1.0.1).
_OPAQUE_SOURCES = ["opaque.c", "common.c"]

# munit parameter matrix: 2 pwdU x 2 idU x 2 idS x 4 types (see
# src/tests/opaque-munit.c @ v1.0.1).
_MUNIT_CASES = 32


class LibopaqueConan(ConanFile):
    name = "libopaque"
    version = "1.0.1"
    description = "C implementation of the OPAQUE asymmetric password-authenticated key-exchange protocol"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/stef/libopaque"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libopaque is only supported on Linux/OHOS, got %s" % self.settings.os
            )

    def requirements(self):
        # Intentionally no external requires: liboprf is unpublished
        # (R36) and libsodium requires() is shadowed (minisign 0.12
        # precedent). Both are vendored to private prefixes instead.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"]["libopaque"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()

    # -- tool probing (PATH-first, HMBS capability aware) -----------------

    def _candidate_compilers(self):
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
        for key in ("c", "C"):
            try:
                exes = self.conf.get("tools.build:compiler_executables")
                if isinstance(exes, dict) and exes.get(key):
                    cands.append(exes[key])
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
            proc = subprocess.run(
                [cand, "--version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=30,
                env=env,
            )
            if proc.returncode == 0:
                return True, proc.stdout.decode("utf-8", "ignore")[:200]
            return False, "exit=%d %s" % (
                proc.returncode,
                proc.stdout.decode("utf-8", "ignore")[:200],
            )
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
        raise RuntimeError(
            "no working C compiler on device; tried: %s" % "; ".join(tried)
        )

    def _resolve_ar(self, cc):
        cands = []
        if os.path.isabs(cc):
            bindir = os.path.dirname(cc)
            for tool in ("llvm-ar", "ar"):
                cands.append(os.path.join(bindir, tool))
        for tool in ("llvm-ar", "ar"):
            try:
                found = shutil.which(tool)
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
        for cand in ("/bin/sh", "sh"):
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

    # -- vendored sources --------------------------------------------------

    def _vendored_dir(self, name):
        # NOTE: fetched in build() (not source()) on purpose, following
        # archives/l/libmacaroons 0.3.0: the device Conan layout does
        # not expose base_source_folder here, and keeping the vendored
        # trees under build_folder avoids source_layout mismatches.
        return os.path.join(self.build_folder, "vendor_%s" % name)

    def _ensure_vendored(self, name):
        dest = self._vendored_dir(name)
        if name == "liboprf":
            probe = os.path.join(dest, "src", "oprf.c")
        else:
            probe = os.path.join(dest, "configure")
        if os.path.isfile(probe):
            return dest
        os.makedirs(dest, exist_ok=True)
        get(self, **self.conan_data["sources"][name],
            strip_root=True, destination=dest)
        if not os.path.isfile(probe):
            try:
                listing = sorted(os.listdir(dest))[:20]
            except OSError:
                listing = []
            raise RuntimeError(
                "vendored %s incomplete, missing %s; listing: %s"
                % (name, probe, listing)
            )
        return dest

    def _relax_configure_umask(self, src):
        # Same HMDFS fix as archives/l/libsodium: configure's umask 077
        # temp dirs fail under UID mapping; 022 works (knowledge E114).
        path = os.path.join(src, "configure")
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
        except OSError as exc:
            raise RuntimeError("vendored sodium configure missing: %s" % exc)
        if "umask 077" in content:
            content = content.replace("umask 077", "umask 022")
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
            self.output.info("[ok] relaxed vendored configure umask 077 -> 022")
        else:
            self.output.info("[ok] vendored configure umask already relaxed/absent")

    def _patch_vendored_config_aux(self, src):
        # Native device build: teach vendored config.guess/sub to
        # recognize HarmonyOS so configure guesses natively (same edits
        # as archives/l/libsodium 1.0.20 patches 0001/0002). No
        # --build/--host flags are passed (native build).
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
            _glob.glob(os.path.join(src, "**", "config.guess"), recursive=True)
        )
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
            _glob.glob(os.path.join(src, "**", "config.sub"), recursive=True)
        )
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
                self.output.info(
                    "[ok] config.sub already accepts ohos or pattern absent: %s" % path
                )

    def _stage_vendored_sodium(self, src, prefix):
        # No `make install`: HMBS reports chmod=0/hardlink=0 and the
        # install shim fails on HMDFS. Stage by hand with pure-Python
        # copies (no chmod/hardlink/mode preservation), following
        # archives/l/libmacaroons 0.3.0.
        import glob as _glob
        libdir = os.path.join(prefix, "lib")
        incdir = os.path.join(prefix, "include")
        os.makedirs(libdir, exist_ok=True)
        os.makedirs(os.path.join(incdir, "sodium"), exist_ok=True)
        cands = []
        for pat in (
            os.path.join(src, "src", "libsodium", ".libs", "libsodium.a"),
            os.path.join(src, "**", ".libs", "libsodium.a"),
            os.path.join(src, "**", "libsodium.a"),
        ):
            for hit in _glob.glob(pat, recursive=True):
                if os.path.isfile(hit) and hit not in cands:
                    cands.append(hit)
        cands.sort(
            key=lambda p: os.path.getsize(p) if os.path.isfile(p) else 0,
            reverse=True,
        )
        if not cands:
            raise RuntimeError(
                "vendored sodium built but no libsodium.a found under %s" % src
            )
        built = cands[0]
        if os.path.getsize(built) == 0:
            raise RuntimeError("vendored sodium archive is empty: %s" % built)
        dest_lib = os.path.join(libdir, "libsodium.a")
        with open(built, "rb") as fin, open(dest_lib, "wb") as fout:
            shutil.copyfileobj(fin, fout, length=1024 * 1024)
        if os.path.getsize(dest_lib) == 0:
            raise RuntimeError("staged libsodium.a is empty: %s" % dest_lib)
        hdr_root = os.path.join(src, "src", "libsodium", "include")
        if not os.path.isdir(hdr_root):
            raise RuntimeError(
                "vendored sodium include root missing: %s" % hdr_root
            )
        staged = 0
        top_h = os.path.join(hdr_root, "sodium.h")
        if os.path.isfile(top_h):
            with open(top_h, "rb") as fin, open(
                os.path.join(incdir, "sodium.h"), "wb"
            ) as fout:
                shutil.copyfileobj(fin, fout, length=1024 * 1024)
            staged += 1
        sodium_dir = os.path.join(hdr_root, "sodium")
        for hdr in sorted(os.listdir(sodium_dir)):
            spath = os.path.join(sodium_dir, hdr)
            if not os.path.isfile(spath) or not hdr.endswith(".h"):
                continue
            with open(spath, "rb") as fin, open(
                os.path.join(incdir, "sodium", hdr), "wb"
            ) as fout:
                shutil.copyfileobj(fin, fout, length=1024 * 1024)
            staged += 1
        if staged < 5 or not os.path.isfile(os.path.join(incdir, "sodium.h")):
            raise RuntimeError(
                "staged too few sodium headers (%d) from %s" % (staged, hdr_root)
            )
        self.output.info(
            "[ok] staged vendored sodium without make install: %s (%d bytes) + %d headers"
            % (dest_lib, os.path.getsize(dest_lib), staged)
        )

    def _build_vendored_sodium(self, cc, ar, tmpdir):
        src = self._ensure_vendored("libsodium")
        prefix = os.path.join(self.build_folder, "sodium_prefix")
        self._relax_configure_umask(src)
        self._patch_vendored_config_aux(src)
        sh = self._resolve_sh()
        make = self._resolve_make()
        self.output.info(
            "vendored sodium: sh=%s make=%s cc=%s ar=%s prefix=%s"
            % (sh, make, cc, ar, prefix)
        )
        cfg = "%s ./configure --prefix='%s' --disable-shared --enable-static " \
            "--disable-dependency-tracking" % (sh, prefix)
        env_prefix = (
            "CC='%s' AR='%s' SHELL='%s' CONFIG_SHELL='%s' "
            "TMPDIR='%s' TMP='%s' TEMP='%s' "
            % (cc, ar, sh, sh, tmpdir, tmpdir, tmpdir)
        )
        self.run(env_prefix + cfg, cwd=src)
        self.run(env_prefix + "%s -j1" % make, cwd=src)
        self._stage_vendored_sodium(src, prefix)
        lib = os.path.join(prefix, "lib", "libsodium.a")
        if not os.path.isfile(lib):
            raise RuntimeError("vendored sodium build produced no libsodium.a")
        self.output.info("[ok] vendored sodium ready: %s" % lib)
        return prefix

    def _stage_oprf_headers(self, oprf_src):
        # opaque.c includes <oprf/oprf.h>: provide an include root with
        # an oprf/ subdir via plain copies (no symlinks, HMBS-safe).
        inc = os.path.join(self.build_folder, "oprf_inc", "oprf")
        os.makedirs(inc, exist_ok=True)
        for hdr in _OPRF_HEADERS:
            spath = os.path.join(oprf_src, "src", hdr)
            if not os.path.isfile(spath):
                raise RuntimeError("vendored liboprf header missing: %s" % spath)
            with open(spath, "rb") as fin, open(
                os.path.join(inc, hdr), "wb"
            ) as fout:
                shutil.copyfileobj(fin, fout, length=1024 * 1024)
        self.output.info("[ok] staged oprf headers: %s" % inc)
        return os.path.join(self.build_folder, "oprf_inc")

    # -- build -------------------------------------------------------------

    def _cflags(self, sodium_inc, oprf_inc, oprf_src):
        # libopaque 1.0.1 calls bare expand_message_xmd() while vendored
        # liboprf 0.9.4 renamed it to oprf_expand_message_xmd() with an
        # identical signature (see oprf.h @ 0.9.4 vs opaque.c @ 1.0.1);
        # alias it so the unmodified upstream sources link.
        flags = [
            "-O2",
            "-std=c99",
            "-DHAVE_SODIUM_HKDF=1",
            "-Dexpand_message_xmd=oprf_expand_message_xmd",
            "-I" + os.path.join(self.source_folder, "src"),
            "-I" + sodium_inc,
            "-I" + oprf_inc,
            "-I" + os.path.join(oprf_src, "src"),
        ]
        if self.settings.get_safe("build_type") == "Debug":
            flags.append("-g")
        if self.options.get_safe("fPIC", True):
            flags.append("-fPIC")
        return flags

    def _verify_upstream_sources(self, oprf_src):
        missing = []
        for name in _OPAQUE_SOURCES:
            if not os.path.isfile(os.path.join(self.source_folder, "src", name)):
                missing.append("libopaque/src/%s" % name)
        for name in _OPRF_SOURCES:
            if not os.path.isfile(os.path.join(oprf_src, "src", name)):
                missing.append("liboprf/src/%s" % name)
        if not os.path.isfile(os.path.join(self.source_folder, "src", "opaque.h")):
            missing.append("libopaque/src/opaque.h")
        if missing:
            raise RuntimeError("upstream sources missing: %s" % missing)
        self.output.info(
            "[ok] upstream sources present: %s + %s"
            % (", ".join(_OPAQUE_SOURCES), ", ".join(_OPRF_SOURCES))
        )

    def build(self):
        tmpdir = os.environ.get("TMPDIR") or os.path.join(self.build_folder, ".tmp")
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir

        cc = self._resolve_cc()
        ar = self._resolve_ar(cc)
        oprf_src = self._ensure_vendored("liboprf")
        self._verify_upstream_sources(oprf_src)
        sodium_prefix = self._build_vendored_sodium(cc, ar, tmpdir)
        sodium_inc = os.path.join(sodium_prefix, "include")
        sodium_lib = os.path.join(sodium_prefix, "lib", "libsodium.a")
        oprf_inc = self._stage_oprf_headers(oprf_src)

        cflags = self._cflags(sodium_inc, oprf_inc, oprf_src)
        objdir = os.path.join(self.build_folder, "obj")
        os.makedirs(objdir, exist_ok=True)
        self.output.info("direct build: cc=%s cflags=%s" % (cc, " ".join(cflags)))

        def _compile(src_path, obj_name):
            obj = os.path.join(objdir, obj_name)
            self.run(
                "%s %s -c '%s' -o '%s'" % (cc, " ".join(cflags), src_path, obj),
                cwd=self.build_folder,
            )
            if not os.path.isfile(obj) or os.path.getsize(obj) == 0:
                raise RuntimeError("compile produced no object: %s" % obj)
            return obj

        oprf_objs = [
            _compile(os.path.join(oprf_src, "src", name), "oprf_%s.o" % name)
            for name in _OPRF_SOURCES
        ]
        opaque_objs = [
            _compile(
                os.path.join(self.source_folder, "src", name),
                "opaque_%s.o" % name,
            )
            for name in _OPAQUE_SOURCES
        ]

        if self.options.shared:
            libopaque = os.path.join(objdir, "libopaque.so")
            self.run(
                "%s -shared -o '%s' %s '%s'" % (
                    cc,
                    libopaque,
                    " ".join("'%s'" % o for o in opaque_objs + oprf_objs),
                    sodium_lib,
                ),
                cwd=self.build_folder,
            )
        else:
            liboprf = os.path.join(objdir, "liboprf.a")
            self.run(
                "%s rcs '%s' %s" % (
                    ar, liboprf, " ".join("'%s'" % o for o in oprf_objs)
                ),
                cwd=self.build_folder,
            )
            libopaque = os.path.join(objdir, "libopaque.a")
            self.run(
                "%s rcs '%s' %s" % (
                    ar, libopaque, " ".join("'%s'" % o for o in opaque_objs)
                ),
                cwd=self.build_folder,
            )
        for lib in (libopaque,):
            if not os.path.isfile(lib) or os.path.getsize(lib) == 0:
                raise RuntimeError("library archive missing or empty: %s" % lib)
        self.output.info("[ok] built %s" % libopaque)

        self._run_upstream_tests(cc, cflags, objdir, sodium_lib)

    def _build_tmpfile_shim(self, cc, testdir):
        """Build a TMPDIR-aware tmpfile() shim object for munit only.

        OHOS libc tmpfile() hardcodes /tmp (musl src/stdio/tmpfile.c:
        ``char s[] = \"/tmp/tmpfile_XXXXXX\"``) and ignores TMPDIR, so on
        the HMBS device where /tmp is read-only it always fails with
        EACCES(13). munit calls tmpfile() once per case to buffer
        stderr, hence 32/32 ``unable to create buffer for stderr``.
        The shim implements ``hmbs_tmpfile()`` via mkstemp() in
        $TMPDIR/$TMP/$TEMP (all injected writable by HMBS) and munit is
        compiled with ``-Dtmpfile=hmbs_tmpfile`` so only the test
        harness is redirected; library code and the static archives are
        untouched and no LD_PRELOAD is needed (knowledge E272 same
        root cause, compile-time variant).
        """
        shim_src = os.path.join(testdir, "hmbs_tmpfile_shim.c")
        shim_obj = os.path.join(testdir, "hmbs_tmpfile_shim.o")
        if not os.path.isfile(shim_obj) or os.path.getsize(shim_obj) == 0:
            shim_code = (
                "#include <stdio.h>\n"
                "#include <stdlib.h>\n"
                "#include <string.h>\n"
                "#include <fcntl.h>\n"
                "#include <unistd.h>\n"
                "FILE *hmbs_tmpfile(void) {\n"
                "  const char *d = getenv(\"TMPDIR\");\n"
                "  if (!d || !*d) d = getenv(\"TMP\");\n"
                "  if (!d || !*d) d = getenv(\"TEMP\");\n"
                "  if (!d || !*d) d = \".\";\n"
                "  size_t n = strlen(d) + 32;\n"
                "  char *t = (char *) malloc(n);\n"
                "  if (!t) return NULL;\n"
                "  snprintf(t, n, \"%s/hmbs_tmpfile_XXXXXX\", d);\n"
                "  int fd = mkstemp(t);\n"
                "  if (fd < 0) { free(t); return NULL; }\n"
                "  unlink(t);\n"
                "  free(t);\n"
                "  int fl = fcntl(fd, F_GETFD);\n"
                "  if (fl != -1) fcntl(fd, F_SETFD, fl | FD_CLOEXEC);\n"
                "  FILE *f = fdopen(fd, \"w+\");\n"
                "  if (!f) close(fd);\n"
                "  return f;\n"
                "}\n"
            )
            with open(shim_src, "w", encoding="utf-8", newline="\n") as f:
                f.write(shim_code)
            self.run(
                "%s -O2 -std=c99 -D_POSIX_C_SOURCE=200809L -D_XOPEN_SOURCE=700 -c '%s' -o '%s'" % (cc, shim_src, shim_obj),
                cwd=self.build_folder,
            )
            if not os.path.isfile(shim_obj) or os.path.getsize(shim_obj) == 0:
                raise RuntimeError("tmpfile shim produced no object: %s" % shim_obj)
            self.output.info("[ok] built TMPDIR-aware tmpfile shim: %s" % shim_obj)
        return shim_obj

    def _link_test(self, cc, cflags, objdir, sodium_lib,
                   test_src, test_name, extra_srcs=()):
        # Static link order matters: consumer objects, libopaque objects,
        # liboprf objects, libsodium archive. Include flags come from
        # cflags (sodium/oprf/opaque include roots).
        testdir = os.path.join(self.build_folder, "upstream")
        os.makedirs(testdir, exist_ok=True)
        exe = os.path.join(testdir, test_name)
        objs = []
        # munit buffers each case's stderr via tmpfile(), which on OHOS
        # ignores TMPDIR and hardcodes read-only /tmp (EACCES 13). Build
        # the test harness with -Dtmpfile=hmbs_tmpfile so only munit's
        # tmpfile() calls are redirected to the HMBS-writable TMPDIR.
        use_shim = "munit" in test_name
        shim_obj = None
        if use_shim:
            shim_obj = self._build_tmpfile_shim(cc, testdir)
        for i, src in enumerate([test_src] + list(extra_srcs)):
            obj = os.path.join(testdir, "%s_%d.o" % (test_name, i))
            extra_defs = " -Dtmpfile=hmbs_tmpfile" if use_shim else ""
            self.run(
                "%s %s%s -c '%s' -o '%s'" % (cc, " ".join(cflags), extra_defs, src, obj),
                cwd=self.build_folder,
            )
            objs.append("'%s'" % obj)
        if shim_obj is not None:
            objs.append("'%s'" % shim_obj)
        lib_objs = []
        for name in _OPAQUE_SOURCES:
            lib_objs.append(
                "'%s'" % os.path.join(objdir, "opaque_%s.o" % name)
            )
        for name in _OPRF_SOURCES:
            lib_objs.append(
                "'%s'" % os.path.join(objdir, "oprf_%s.o" % name)
            )
        self.run(
            "%s %s %s '%s' -o '%s'" % (
                cc, " ".join(objs), " ".join(lib_objs), sodium_lib, exe
            ),
            cwd=self.build_folder,
        )
        if not os.path.isfile(exe) or os.path.getsize(exe) == 0:
            raise RuntimeError("upstream test binary missing: %s" % exe)
        return exe

    def _run_binary(self, exe, args=()):
        try:
            proc = subprocess.run(
                [exe] + list(args),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=self.build_folder,
                timeout=300,
            )
        except Exception as exc:
            raise RuntimeError("upstream test exec failed (%s): %s" % (exe, exc))
        out = proc.stdout.decode("utf-8", "ignore")
        for line in out.splitlines()[-25:]:
            self.output.info("[upstream] %s" % line[:220])
        return proc.returncode, out

    def _run_upstream_tests(self, cc, cflags, objdir, sodium_lib):
        """Build and run the upstream C test suite, emit the HMBS marker.

        Upstream `make test` runs opaque-tv1 (optional, ignored on
        failure), opaque-test and opaque-munit. tv1 is excluded here for
        the reason documented in notes.md, so the counted suite is
        1 (opaque-test) + 32 (munit matrix) = 33 cases.
        """
        tests_dir = os.path.join(self.source_folder, "src", "tests")
        munit_src = os.path.join(tests_dir, "munit", "munit.c")

        exe_test = self._link_test(
            cc, cflags, objdir, sodium_lib,
            os.path.join(tests_dir, "opaque-test.c"), "opaque-test",
        )
        rc_test, out_test = self._run_binary(exe_test)
        test_ok = (
            rc_test == 0
            and len(out_test.strip()) > 0
            and "all ok" in out_test
        )
        if not test_ok:
            self.output.warning(
                "opaque-test failed: rc=%d len=%d tail=%s"
                % (rc_test, len(out_test), out_test[-500:])
            )

        exe_munit = self._link_test(
            cc, cflags, objdir, sodium_lib,
            os.path.join(tests_dir, "opaque-munit.c"), "opaque-munit",
            extra_srcs=(munit_src,),
        )
        rc_munit, out_munit = self._run_binary(exe_munit, ("--fatal-failures",))
        munit_total, munit_passed = 0, 0
        munit_match = re.search(r"(\d+) of (\d+)[^\n]*tests successful", out_munit)
        if munit_match:
            munit_passed = int(munit_match.group(1))
            munit_total = int(munit_match.group(2))
        if munit_total != _MUNIT_CASES:
            self.output.warning(
                "munit case count %d != audited %d; full output tail: %s"
                % (munit_total, _MUNIT_CASES, out_munit[-500:])
            )
            munit_total = _MUNIT_CASES
        if rc_munit != 0:
            self.output.warning("opaque-munit rc=%d" % rc_munit)
            munit_passed = min(munit_passed, munit_total - 1) if munit_total else 0

        discovered = 1 + munit_total
        passed = (1 if test_ok else 0) + munit_passed
        failed = discovered - passed
        status = "passed" if failed == 0 else "failed"
        upstream = {
            "status": status,
            "framework": "munit+ctest",
            "command": "./opaque-test && ./opaque-munit --fatal-failures "
                       "(upstream src/tests/, 1 end-to-end program + "
                       "32 munit matrix cases)",
            "discovered": discovered,
            "executed": discovered,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
        }
        marker = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
        print(marker, flush=True)
        self.output.info(marker)
        try:
            with open(
                os.path.join(self.build_folder, "hmbs_upstream_result.json"),
                "w", encoding="utf-8", newline="\n",
            ) as f:
                json.dump(upstream, f, ensure_ascii=False, indent=2)
                f.write("\n")
        except OSError as exc:
            self.output.warning("cannot persist upstream result: %s" % exc)
        if status != "passed":
            raise RuntimeError(
                "upstream tests failed: %d/%d passed" % (passed, discovered)
            )
        self.output.info(
            "[ok] upstream tests passed: %d/%d" % (passed, discovered)
        )

    # -- package -----------------------------------------------------------

    def package(self):
        objdir = os.path.join(self.build_folder, "obj")
        if self.options.shared:
            copy(self, "libopaque.so", src=objdir,
                 dst=os.path.join(self.package_folder, "lib"))
        else:
            copy(self, "libopaque.a", src=objdir,
                 dst=os.path.join(self.package_folder, "lib"))
            copy(self, "liboprf.a", src=objdir,
                 dst=os.path.join(self.package_folder, "lib"))
            sodium_lib = os.path.join(
                self.build_folder, "sodium_prefix", "lib", "libsodium.a"
            )
            if os.path.isfile(sodium_lib):
                copy(self, "libsodium.a",
                     src=os.path.join(self.build_folder, "sodium_prefix", "lib"),
                     dst=os.path.join(self.package_folder, "lib"))
        copy(self, "opaque.h", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "include"))
        oprf_src = self._vendored_dir("liboprf")
        for hdr in _OPRF_HEADERS:
            copy(self, hdr, src=os.path.join(oprf_src, "src"),
                 dst=os.path.join(self.package_folder, "include", "oprf"))
        sodium_inc = os.path.join(self.build_folder, "sodium_prefix", "include")
        if os.path.isdir(os.path.join(sodium_inc, "sodium")):
            copy(self, "*.h", src=os.path.join(sodium_inc, "sodium"),
                 dst=os.path.join(self.package_folder, "include", "sodium"))
            if os.path.isfile(os.path.join(sodium_inc, "sodium.h")):
                copy(self, "sodium.h", src=sodium_inc,
                     dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        try:
            src_json = os.path.join(self.build_folder, "hmbs_upstream_result.json")
            if os.path.isfile(src_json):
                copy(self, "hmbs_upstream_result.json", src=self.build_folder,
                     dst=os.path.join(self.package_folder, "res"))
                self.output.info("[ok] packaged hmbs_upstream_result.json")
            else:
                self.output.warning(
                    "upstream result json missing; cache-hit re-emit unavailable"
                )
        except Exception as exc:
            self.output.warning("cannot package upstream result: %s" % exc)
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))

    def package_info(self):
        if self.options.shared:
            self.cpp_info.libs = ["opaque"]
        else:
            self.cpp_info.libs = ["opaque", "oprf", "sodium"]
        self.cpp_info.set_property("cmake_file_name", "libopaque")
        self.cpp_info.set_property("cmake_target_name", "libopaque::libopaque")
        self.cpp_info.set_property("pkg_config_name", "libopaque")
