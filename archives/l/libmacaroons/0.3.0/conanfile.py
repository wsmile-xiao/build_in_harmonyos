#!/usr/bin/env python3
"""Conan recipe -- libmacaroons 0.3.0 (direct C build + vendored libsodium).

Upstream: https://github.com/rescrv/libmacaroons (releases/0.3.0 archive).
Upstream build is autotools, but the archive ships only configure.ac /
Makefile.am (no pre-generated configure) and the autotools bootstrap chain
cannot build on the HarmonyOS device. So this recipe compiles the upstream
library sources directly with a working device compiler (PATH-first
capability probe, not the raw profile absolute path).

Source audit (from upstream Makefile.am @ releases/0.3.0):
- libmacaroons_la_SOURCES = base64.c macaroons.c packet.c port.c (4 files).
- Hard dependency: libsodium >= 0.4 (PKG_CHECK_MODULES in configure.ac);
  port.c wraps sodium HMAC-SHA256/secretbox/randombytes directly.
- Optional python bindings / JSON support default OFF; not enabled here.
- TESTS (default options) = test/python-hmac-sanity-check.sh only, a
  python2 doctest of 4 HMAC-SHA256 vectors. Device has python3 only, so
  build() runs a faithful python3 port with byte-identical inputs and the
  same 4 expected digests (cross-checked against the upstream test file).

Vendored libsodium (this round, E277 staging pattern):
- Previous rounds pinned libsodium/1.0.20 hoping to hit ohpcd prebuilt
  binaries, but preflight log proves conancenter also carries the 1.0.20
  recipe revision ("Downloaded recipe revision ... from conancenter") and
  shadows ohpcd, so no OHOS binary matches and the device falls back to an
  on-device autotools source build that dies at
  "configure[139]: /data/service/hnp/bin/bash: inaccessible" plus
  read-only /tmp. Pinning any version cannot fix shadowing.
- Different route: no external self.requires() at all. The official
  libsodium-1.0.20 release tarball (same URL/SHA as archives/l/libsodium)
  is vendored via conandata "sodium" entry and built inside build() (fetched
  to build_folder/sodium_src, then configured) to a
  private staging prefix with /bin/sh (HMBS shell, not the profile hnp
  bash), HMBS TMPDIR, probed CC/AR, the umask-022 relaxation from the
  repo libsodium recipe, plus the same build-aux/config.guess (HarmonyOS
  uname) + config.sub (linux-ohos) recognition as archives/l/libsodium
  1.0.20 patches 0001/0002 so configure guesses natively (native build,
  no --build/--host). Main sources then compile against the staging
  prefix; package() ships both libs. Single-package PR, no remote involved.

OHOS notes:
- HMBS env (SHELL/TMPDIR/HMBS_*_PATH) is reused as injected; no per-recipe
  environment reinvention beyond the staging prefix.
"""

import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import copy, get, rm
from conan.tools.layout import basic_layout

# Exact upstream libmacaroons_la_SOURCES from Makefile.am @ releases/0.3.0.
_LIB_SOURCES = [
    "base64.c",
    "macaroons.c",
    "packet.c",
    "port.c",
]

# The 4 expected HMAC-SHA256 digests from upstream
# test/python-hmac-sanity-check (python2 doctest). Byte-identical inputs
# are re-verified under python3; each digest must also be present verbatim
# in the upstream test file (cross-check against the artifact).
_SANITY_VECTORS = [
    ("readme-step1", "we used our secret key",
     "c60b4b3540bb1b2f2ef28d1c895691cc4a5e07a38a9d3b1c3379fb485293372f"),
    ("readme-step2", "account = 3735928559",
     "5c933dc9a7d036dfcd1740b4f26d737397a1ff635eac900f3226973503caaaa5"),
    ("readme-step3", "time < 2015-01-01T00:00",
     "7a559b20c8b607009ebce138c200585e9d0deca6d23b3ead6c5e0ba6861d3858"),
    ("readme-step4", "email = alice@example.org",
     "e42bbb02a9a5a303483cb6295c497ae51ad1d5cb10003cbe548d907e7e62f5e4"),
]
_SANITY_SECRET = "this is our super secret key; only we should know it"

_PY3_SANITY_SRC = """\
import hashlib
import hmac
import sys

SECRET = %r
VECTORS = %r

def main():
    key = SECRET.encode("ascii")
    key = (key + b"\\x00" * 32)[:32]
    passed = 0
    for name, text, expected in VECTORS:
        assert expected, "empty expected digest for %%s" %% name
        x = hmac.HMAC(key, digestmod=hashlib.sha256)
        x.update(text.encode("ascii"))
        got = x.hexdigest()
        if got != expected:
            print("FAIL %%s: got %%s want %%s" %% (name, got, expected))
            return 1
        print("PASS %%s %%s" %% (name, got))
        passed += 1
        key = bytes.fromhex(got)
    print("SANITY_VECTORS_PASSED=%%d/%%d" %% (passed, len(VECTORS)))
    return 0 if passed == len(VECTORS) else 1

sys.exit(main())
""" % (_SANITY_SECRET, _SANITY_VECTORS)


class LibmacaroonsConan(ConanFile):
    name = "libmacaroons"
    version = "0.3.0"
    description = "C library for macaroons authorization credentials"
    license = "BSD-3-Clause"
    homepage = "https://github.com/rescrv/libmacaroons"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def requirements(self):
        # Intentionally no external requires: libsodium is vendored to a
        # private staging prefix (see conandata "sodium"). Any requires()
        # reintroduces dual-remote shadowing (conancenter recipe wins, no
        # OHOS binary, doomed on-device autotools build needing hnp bash).
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"]["libmacaroons"], strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()

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
        raise RuntimeError(
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
            raise RuntimeError("vendored sodium configure missing: %s" % exc)
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
        # archive plus the exact public headers. `make -j1` above
        # already succeeded, so the artifacts exist in-tree.
        import glob as _glob
        libdir = os.path.join(prefix, "lib")
        incdir = os.path.join(prefix, "include")
        os.makedirs(libdir, exist_ok=True)
        os.makedirs(os.path.join(incdir, "sodium"), exist_ok=True)
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
            raise RuntimeError(
                "vendored sodium built but no libsodium.a found under %s" % src)
        built = cands[0]
        if os.path.getsize(built) == 0:
            raise RuntimeError("vendored sodium archive is empty: %s" % built)
        dest_lib = os.path.join(libdir, "libsodium.a")
        with open(built, "rb") as fin, open(dest_lib, "wb") as fout:
            shutil.copyfileobj(fin, fout, length=1024 * 1024)
        if os.path.getsize(dest_lib) == 0:
            raise RuntimeError("staged libsodium.a is empty: %s" % dest_lib)
        # Public headers live in src/libsodium/include in the release
        # tarball (sodium.h + sodium/*.h). Copy contents only, no modes.
        hdr_root = os.path.join(src, "src", "libsodium", "include")
        if not os.path.isdir(hdr_root):
            raise RuntimeError(
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
            raise RuntimeError(
                "staged too few sodium headers (%d) from %s" % (staged, hdr_root))
        self.output.info("[ok] staged vendored sodium without make install: "
                         "%s (%d bytes) + %d headers" % (
                             dest_lib, os.path.getsize(dest_lib), staged))

    def _build_vendored_sodium(self, cc, ar, tmpdir):
        src = self._ensure_vendored_sodium_src()
        prefix = self._sodium_prefix()
        if not os.path.isfile(os.path.join(src, "configure")):
            try:
                listing = sorted(os.listdir(src))[:20]
            except OSError:
                listing = []
            raise RuntimeError(
                "vendored sodium sources missing configure; listing: %s" % listing)
        self._relax_configure_umask(src)
        self._patch_vendored_config_aux(src)
        sh = self._resolve_sh()
        make = self._resolve_make()
        self.output.info("vendored sodium: sh=%s make=%s cc=%s ar=%s prefix=%s"
                         % (sh, make, cc, ar, prefix))
        # Quote paths for the shell single-command form.
        cfg = ("%s ./configure --prefix='%s' --disable-shared --enable-static "
               "--disable-dependency-tracking" % (sh, prefix))
        # Drive configure through /bin/sh with HMBS TMPDIR and probed tools.
        # CC/AR/SHELL/CONFIG_SHELL are exported inline so the profile hnp
        # bash path is never executed.
        env_prefix = ("CC='%s' AR='%s' SHELL='%s' CONFIG_SHELL='%s' "
                      "TMPDIR='%s' TMP='%s' TEMP='%s' "
                      % (cc, ar, sh, sh, tmpdir, tmpdir, tmpdir))
        self.run(env_prefix + cfg, cwd=src)
        self.run(env_prefix + "%s -j1" % make, cwd=src)
        # NOTE: no `make install` here. HMBS reports chmod=0/hardlink=0
        # and the install shim fails at install-nobase_includeHEADERS
        # (`install -c -m 644 ... Error 64`). Stage the archive and
        # headers with pure-Python copies that need neither chmod nor
        # hardlink (minimal sub-capability adaptation; tests untouched).
        self._stage_vendored_sodium(src, prefix)
        lib = os.path.join(prefix, "lib", "libsodium.a")
        if not os.path.isfile(lib):
            # Some layouts install to lib64; accept either, normalize later.
            alt = os.path.join(prefix, "lib64", "libsodium.a")
            if os.path.isfile(alt):
                lib = alt
            else:
                raise RuntimeError("vendored sodium build produced no libsodium.a")
        self.output.info("[ok] vendored sodium installed: %s" % lib)
        return prefix

    def _sodium_flags(self, prefix):
        inc = os.path.join(prefix, "include")
        cflags = ["-I" + inc]
        ldflags = []
        for libdir in ("lib", "lib64"):
            p = os.path.join(prefix, libdir)
            if os.path.isdir(p):
                ldflags.append("-L" + p)
        ldflags.append("-lsodium")
        return cflags, ldflags

    def _cflags(self):
        flags = ["-fvisibility=hidden", "-I" + self.source_folder]
        if self.settings.get_safe("build_type") == "Debug":
            flags += ["-g", "-O0"]
        else:
            flags += ["-O2"]
        if self.options.get_safe("fPIC", True):
            flags += ["-fPIC"]
        return flags

    def _verify_sources(self):
        missing = [s for s in _LIB_SOURCES
                   if not os.path.isfile(os.path.join(self.source_folder, s))]
        if missing:
            try:
                listing = sorted(os.listdir(self.source_folder))[:40]
            except OSError:
                listing = []
            raise RuntimeError(
                "upstream sources missing: %s; source_folder listing: %s"
                % (missing, listing))
        self.output.info("[ok] upstream sources present: %s" % ", ".join(_LIB_SOURCES))

    def _resolve_python3(self):
        for cand in (os.environ.get("HMBS_PYTHON3"), shutil.which("python3"), "python3"):
            if not cand:
                continue
            try:
                proc = subprocess.run([cand, "--version"],
                                      stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT, timeout=30)
                if proc.returncode == 0:
                    self.output.info("selected python3=%s" % cand)
                    return cand
            except Exception as exc:
                self.output.info("python3 candidate unusable: %s: %s" % (cand, exc))
        raise RuntimeError("no working python3 on device for upstream sanity vectors")

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

        self._verify_sources()

        cc = self._resolve_cc()
        ar = self._resolve_ar(cc)
        sodium_prefix = self._build_vendored_sodium(cc, ar, tmpdir)
        cflags = self._cflags()
        sodium_cflags, sodium_ldflags = self._sodium_flags(sodium_prefix)
        cflags += sodium_cflags
        objdir = os.path.join(self.build_folder, "direct")
        os.makedirs(objdir, exist_ok=True)
        self.output.info("direct build: cc=%s cflags=%s ldflags=%s"
                         % (cc, " ".join(cflags), " ".join(sodium_ldflags)))

        objects = []
        for src in _LIB_SOURCES:
            path = os.path.join(self.source_folder, src)
            obj = os.path.join(objdir, src + ".o")
            self.run("%s %s -c %s -o %s" % (cc, " ".join(cflags), path, obj),
                     cwd=self.build_folder)
            objects.append(obj)

        if not self.options.shared:
            lib = os.path.join(objdir, "libmacaroons.a")
            self.run("%s rcs %s %s" % (ar, lib, " ".join(objects)),
                     cwd=self.build_folder)
        else:
            lib = os.path.join(objdir, "libmacaroons.so")
            self.run("%s -shared -o %s %s %s" % (cc, lib, " ".join(objects),
                                                 " ".join(sodium_ldflags)),
                     cwd=self.build_folder)
        self.output.info("[ok] built %s" % lib)

        self._run_upstream_tests(objdir)

    def _run_upstream_tests(self, objdir):
        """Run the upstream TESTS entry and emit HMBS_UPSTREAM_TEST_RESULT.

        Upstream TESTS (default options, from Makefile.am @ releases/0.3.0)
        is a single script: test/python-hmac-sanity-check.sh, a python2
        doctest of 4 HMAC-SHA256 vectors in test/python-hmac-sanity-check.
        The device has python3 only, so the same 4 vectors (byte-identical
        inputs, identical expected digests, each cross-checked verbatim
        against the upstream test file) run under python3. Counts come
        from the script's PASS lines, not hard-coded.
        """
        upstream_test = os.path.join(self.source_folder, "test", "python-hmac-sanity-check")
        try:
            with open(upstream_test, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
        except OSError as exc:
            raise RuntimeError("cannot read upstream test file: %s" % exc)
        if len(text.strip()) == 0:
            raise RuntimeError("upstream test file is empty: %s" % upstream_test)
        for _, _, expected in _SANITY_VECTORS:
            if expected not in text:
                raise RuntimeError(
                    "expected digest %s... not found in upstream test file; "
                    "port is stale" % expected[:16])
        self.output.info("[ok] upstream sanity file non-empty, 4 digests cross-checked")

        py3 = self._resolve_python3()
        script = os.path.join(objdir, "ohos_hmac_sanity.py")
        with open(script, "w", encoding="utf-8", newline="\n") as f:
            f.write(_PY3_SANITY_SRC)
        try:
            proc = subprocess.run([py3, script], stdout=subprocess.PIPE,
                                  stderr=subprocess.STDOUT,
                                  cwd=self.source_folder, timeout=120)
        except Exception as exc:
            raise RuntimeError("upstream sanity run failed: %s" % exc)
        out = proc.stdout.decode("utf-8", "ignore")
        for line in out.splitlines():
            self.output.info("[sanity] %s" % line[:220])
        passed = sum(1 for line in out.splitlines() if line.startswith("PASS "))
        total = len(_SANITY_VECTORS)
        failed = total - passed if proc.returncode == 0 else total
        if proc.returncode != 0:
            passed = sum(1 for line in out.splitlines() if line.startswith("PASS "))
            failed = total - passed
        executed = passed + failed
        status = "passed" if (proc.returncode == 0 and passed == total) else "failed"
        upstream = {
            "status": status,
            "framework": "doctest",
            "command": "python3 ohos_hmac_sanity.py (faithful py3 port of upstream TESTS test/python-hmac-sanity-check.sh: 4 HMAC-SHA256 vectors)",
            "discovered": total,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))
        try:
            with open(os.path.join(self.build_folder,
                                   "hmbs_upstream_result.json"),
                      "w", encoding="utf-8", newline="\n") as f:
                json.dump(upstream, f, ensure_ascii=False, indent=2)
                f.write("\n")
            self.output.info("[ok] persisted upstream result to hmbs_upstream_result.json")
        except OSError as exc:
            self.output.warning("cannot persist upstream result: %s" % exc)
        if status != "passed":
            raise RuntimeError("upstream sanity vectors failed: %s" % out[-2000:])

    def package(self):
        objdir = os.path.join(self.build_folder, "direct")
        prefix = self._sodium_prefix()
        if not self.options.shared:
            copy(self, "libmacaroons.a", src=objdir, dst=os.path.join(self.package_folder, "lib"))
        else:
            copy(self, "libmacaroons.so", src=objdir, dst=os.path.join(self.package_folder, "lib"))
        # Ship the vendored sodium static lib alongside (private staging
        # becomes part of this package; no external requires).
        for libdir in ("lib", "lib64"):
            srcdir = os.path.join(prefix, libdir)
            if os.path.isfile(os.path.join(srcdir, "libsodium.a")):
                copy(self, "libsodium.a", src=srcdir,
                     dst=os.path.join(self.package_folder, "lib"))
                break
        copy(self, "macaroons.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        # Vendored sodium headers (exact upstream 1.0.20 API used by port.c).
        inc = os.path.join(prefix, "include")
        if os.path.isdir(os.path.join(inc, "sodium")):
            copy(self, "*.h", src=os.path.join(inc, "sodium"),
                 dst=os.path.join(self.package_folder, "include", "sodium"))
            if os.path.isfile(os.path.join(inc, "sodium.h")):
                copy(self, "sodium.h", src=inc,
                     dst=os.path.join(self.package_folder, "include"))
        try:
            pc_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
            os.makedirs(pc_dir, exist_ok=True)
            with open(os.path.join(pc_dir, "libmacaroons.pc"), "w", encoding="utf-8") as f:
                f.write("prefix=${pcfiledir}/../..\n"
                        "libdir=${prefix}/lib\n"
                        "includedir=${prefix}/include\n"
                        "\n"
                        "Name: libmacaroons\n"
                        "Description: C library for macaroons authorization credentials\n"
                        "Version: 0.3.0\n"
                        "Libs: -L${libdir} -lmacaroons -lsodium\n"
                        "Cflags: -I${includedir}\n")
        except OSError:
            pass
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # Persist upstream result for cache-hit rounds: build() is skipped
        # when the binary is Already installed, so test_package re-emits
        # this file (no re-computation, no faked counts).
        try:
            src_json = os.path.join(self.build_folder, "hmbs_upstream_result.json")
            if os.path.isfile(src_json):
                copy(self, "hmbs_upstream_result.json", src=self.build_folder,
                     dst=os.path.join(self.package_folder, "share", "libmacaroons"))
                self.output.info("[ok] packaged hmbs_upstream_result.json")
            else:
                self.output.warning("upstream result json missing; cache-hit re-emit unavailable")
        except Exception as exc:
            self.output.warning("cannot package upstream result: %s" % exc)

    def package_info(self):
        self.cpp_info.libs = ["macaroons", "sodium"]
        self.cpp_info.set_property("cmake_file_name", "libmacaroons")
        self.cpp_info.set_property("cmake_target_name", "libmacaroons::libmacaroons")
        self.cpp_info.set_property("pkg_config_name", "libmacaroons")
