#!/usr/bin/env python3
"""Conan recipe — libetebase 0.5.8 (Rust cdylib with a C API, cargo build).

Upstream (https://github.com/etesync/libetebase) implements the Etebase
client library in Rust and exposes a C API (libetebase.so + etebase.h +
etebase.pc) via cbindgen. The upstream Makefile runs `cargo build` and
installs the shared object, the generated header and the pkg-config file.

OHOS adaptation notes:
- The Rust toolchain comes from the rust-toolchain/1.97.1 infra package
  (tool_requires); rustup bootstrap is not used because stock rustup does
  not recognize the HarmonyOS host ("unrecognized OS type: HarmonyOS").
- The toolchain binaries carry no code signature, which the OHOS loader
  rejects (EACCES); build_folder copies are self-signed with
  binary-sign-tool before first use (below/0.11.0 precedent).
- Crates are fetched through the rsproxy.cn sparse mirror (below/0.11.0
  precedent); the device CA bundle is wired explicitly.
- System C dependencies: libsodium is vendored from the official
  1.0.20 release tarball (conancenter shadows ohpcd for libsodium/*,
  so any requires edge rebuilds it on-device and dies on the profile
  hnp bash; libmacaroons/0.3.0 precedent) and built statically into
  the cdylib; OpenSSL for openssl-sys is the OHOS-suffixed 3.5.6.1.1
  (same upstream 3.5.6, no zlib edge, no conancenter shadow).
  Both are wired via SODIUM_*/OPENSSL_* env plus
  PKG_CONFIG_PATH/PKG_CONFIG_ALLOW_CROSS.
- Upstream `make check` = `cargo check` + `cd c_tests && make check`.
  The c_tests binary runs 12 C tests; 3 are offline (test_simple_getters,
  test_base64, test_utils) and 9 require a live Etebase server
  (ETEBASE_TEST_API_URL, default http://localhost:8033). build() starts
  the stdlib-only `etebase_stub_server.py` on 127.0.0.1:8033 (seeded
  test_user/test_user2, opaque-blob storage with stoken/etag conflict
  semantics, Ed25519 login verification) and runs the REAL upstream
  tests.c suite (all 12, no ASan: the OHOS target has no ASan runtime)
  with ETEBASE_TEST_API_URL pointed at the stub; reports 12/12/0 (R51).
"""

import os
import shlex
import shutil
import subprocess
import tarfile
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, download
from conan.tools.files import export_conandata_patches, get
from conan.tools.layout import basic_layout

OHOS_RUST_TARGET = "aarch64-unknown-linux-ohos"

# cargo itself links libssl/libcrypto/libz at runtime, but the OHOS loader
# ignores DT_RUNPATH, so the Harmonybrew OHOS bottles are staged into the
# build folder and put on LD_LIBRARY_PATH (below/0.11.0 precedent).
RUST_RUNTIME_BOTTLES = (
    ("openssl3",
     "https://harmonybrew.atomgit.com/bottles/"
     "openssl%403-3.6.4.arm64_ohos.bottle.tar.gz",
     "e1be73c6c68e29c33ff43761045e43e23e7c369f0fb1a24f40e226ec5cb28f98"),
    ("zlib",
     "https://harmonybrew.atomgit.com/bottles/"
     "zlib-ng-compat-2.3.3_1.arm64_ohos.bottle.tar.gz",
     "1c17a31f8104701bce6b471af8dbbd14bb67d16a504eec087018feb05493a430"),
)

# Upstream c_tests file names (12 tests live in test_service.c, driven by
# tests.c). All 12 run on the OHOS device against the local stub server
# (see etebase_stub_server.py and notes.md R51).
UPSTREAM_TESTS_TOTAL = 12
STUB_SERVER_PORT = 8033

UPSTREAM_TESTS_ORDER = (
    "test_simple_getters", "test_base64", "test_utils",
    "test_check_etebase_server", "test_simple", "test_item_deps",
    "test_collection_transactions", "test_items_transactions",
    "test_collection_as_item", "test_item_revisions",
    "test_basic_invitations", "test_bad_auth",
)


class LibetebaseConan(ConanFile):
    name = "libetebase"
    version = "0.5.8"
    description = "C library for Etebase (end-to-end encrypted backend)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/etesync/libetebase"
    url = "https://github.com/etesync/libetebase"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}
    # The local Etebase stub server must travel with the recipe into the
    # Conan cache: without this, export() only ships conanfile.py +
    # conandata.yml and build() fails with "stub server script not found"
    # after the 5-minute cargo build (2026-09-16 preflight evidence).
    exports = "etebase_stub_server.py"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # sodiumoxide-sys links a vendored libsodium built in build()
        # (conancenter shadows ohpcd for libsodium/*, rebuilding on-device
        # fails on the profile hnp bash; libmacaroons/0.3.0 precedent).
        # openssl-sys links the OHOS-suffixed OpenSSL: plain 3.5.6 resolves
        # to the conancenter recipe whose transitive zlib/1.3.2 rebuild dies
        # on device (cmake unknown HarmonyOS + profile clang check fail);
        # 3.5.6.1.1 is the same upstream 3.5.6 with OHOS fixes, has no zlib
        # edge and no conancenter shadow.
        self.requires("openssl/3.5.6.1.1")

    def build_requirements(self):
        # rust-lang official dist tarball (host and target are
        # aarch64-unknown-linux-ohos); no rustup bootstrap (stock rustup
        # fails with "unrecognized OS type: HarmonyOS").
        self.tool_requires("rust-toolchain/1.97.1")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported OS: {self.settings.os}")
        if str(self.settings.arch) not in ("armv8", "aarch64"):
            raise ConanInvalidConfiguration(
                f"Unsupported arch: {self.settings.arch}")

    def generate(self):
        # Expose the profile buildenv to conan-run commands
        # (libmacaroons/0.3.0 precedent). The vendored sodium build below
        # still drives configure via subprocess + explicit env, so this
        # only adds entries (e.g. openssl/tool paths) and never removes.
        VirtualBuildEnv(self).generate()

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, url=self.conan_data["sources"]["url"],
            sha256=self.conan_data["sources"]["sha256"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        self._build_vendored_sodium()
        env = self._rust_environment()
        self._ensure_ohos_target(env)
        self._cargo_fetch(env)
        # Upstream `make check` part 1: Rust compile check.
        self._cargo_check(env)
        self._cargo_build(env)
        self._stage_artifacts(env)
        # Upstream `make check` part 2: full c_tests (12/12) vs stub.
        self._run_upstream_tests_with_stub(env)

    # ── cargo helpers ──────────────────────────────────────────────

    def _cargo(self, env):
        return env["CARGO"]

    def _cargo_fetch(self, env):
        rc = subprocess.run(
            [self._cargo(env), "fetch", "--manifest-path",
             os.path.join(self.source_folder, "Cargo.toml")],
            cwd=self.source_folder, env=env).returncode
        if rc != 0:
            raise ConanInvalidConfiguration(f"cargo fetch failed (rc={rc})")

    def _cargo_check(self, env):
        rc = subprocess.run(
            [self._cargo(env), "check", "--target", OHOS_RUST_TARGET],
            cwd=self.source_folder, env=env).returncode
        if rc != 0:
            raise ConanInvalidConfiguration(
                f"cargo check failed for {OHOS_RUST_TARGET} (rc={rc})")

    def _cargo_build(self, env):
        rc = subprocess.run(
            [self._cargo(env), "build", "--release",
             "--target", OHOS_RUST_TARGET],
            cwd=self.source_folder, env=env).returncode
        if rc != 0:
            raise ConanInvalidConfiguration(
                f"cargo build failed for {OHOS_RUST_TARGET} (rc={rc})")
        lib = os.path.join(self.source_folder, "target", OHOS_RUST_TARGET,
                           "release", "libetebase.so")
        if not os.path.isfile(lib):
            raise ConanInvalidConfiguration(
                f"cargo did not produce the cdylib: {lib}")
        header = os.path.join(self.source_folder, "target", "etebase.h")
        if not os.path.isfile(header):
            raise ConanInvalidConfiguration(
                f"cbindgen did not generate the C header: {header}")

    def _stage_dir(self):
        return os.path.join(self.build_folder, "stage")

    def _stage_artifacts(self, env):
        """Copy the cdylib + generated header into a private stage dir,
        generate etebase.pc (upstream Makefile `pkgconfig` target), and
        self-sign the shared object so the OHOS loader executes it."""
        del env  # stage layout does not depend on cargo env
        stage = self._stage_dir()
        lib_dir = os.path.join(stage, "lib")
        inc_dir = os.path.join(stage, "include", "etebase")
        os.makedirs(lib_dir, exist_ok=True)
        os.makedirs(inc_dir, exist_ok=True)
        lib = os.path.join(self.source_folder, "target", OHOS_RUST_TARGET,
                           "release", "libetebase.so")
        staged_lib = os.path.join(lib_dir, "libetebase.so")
        shutil.copy2(lib, staged_lib)
        # SONAME is libetebase.so.0 (build.rs link-arg); consumers resolve
        # DT_NEEDED=libetebase.so.0, so ship that name as well (plain copy:
        # HMDFS ignores chmod/symlink tricks, nix does the same symlink).
        shutil.copy2(lib, os.path.join(lib_dir, "libetebase.so.0"))
        shutil.copy2(os.path.join(self.source_folder, "target", "etebase.h"),
                     os.path.join(inc_dir, "etebase.h"))
        with open(os.path.join(self.source_folder, "etebase.pc.in"),
                  encoding="utf-8") as f:
            pc = f.read().replace("@prefix@", "/")
        pkgconfig_dir = os.path.join(lib_dir, "pkgconfig")
        os.makedirs(pkgconfig_dir, exist_ok=True)
        with open(os.path.join(pkgconfig_dir, "etebase.pc"),
                  "w", encoding="utf-8", newline="\n") as f:
            f.write(pc)
        self._sign_file(staged_lib)
        self._sign_file(os.path.join(lib_dir, "libetebase.so.0"))

    def _stub_server_script(self):
        cands = []
        for attr in ("recipe_folder", "base_source_folder",
                     "source_folder", "export_sources_folder",
                     "base_export_sources_folder"):
            try:
                base = getattr(self, attr, None)
                if base:
                    cands.append(os.path.join(
                        base, "etebase_stub_server.py"))
            except Exception:
                pass
        cands.append(os.path.join(os.path.dirname(__file__), "etebase_stub_server.py"))
        for c in cands:
            if c and os.path.isfile(c):
                return c
        return None

    def _start_stub_server(self, env, log_path):
        script = self._stub_server_script()
        if script is None:
            raise ConanInvalidConfiguration("stub server script not found")
        py = os.environ.get("HMBS_PYTHON3") or env.get("HMBS_PYTHON3") or sys.executable
        logf = open(log_path, "w", encoding="utf-8", errors="replace")
        proc = subprocess.Popen([py, script, str(STUB_SERVER_PORT)], stdout=logf, stderr=subprocess.STDOUT, env=env)
        import time as _time
        import urllib.request as _urlreq
        deadline = _time.time() + 20
        url = "http://127.0.0.1:%d/api/v1/authentication/is_etebase/" % STUB_SERVER_PORT
        last_err = ""
        while _time.time() < deadline:
            if proc.poll() is not None:
                raise ConanInvalidConfiguration("stub exited early rc=%s see %s" % (proc.returncode, log_path))
            try:
                with _urlreq.urlopen(url, timeout=2) as r:
                    if r.status == 200:
                        self.output.info("stub ready 127.0.0.1:%d" % STUB_SERVER_PORT)
                        return proc, logf
            except Exception as e:
                last_err = str(e)[:160]
            _time.sleep(0.5)
        try:
            proc.terminate()
        except Exception:
            pass
        raise ConanInvalidConfiguration("stub not ready (%s) see %s" % (last_err, log_path))

    def _run_upstream_tests_with_stub(self, env):
        work = os.path.join(self.build_folder, "upstream-tests")
        os.makedirs(work, exist_ok=True)
        stub_log = os.path.join(work, "stub-server.log")
        proc, logf = self._start_stub_server(env, stub_log)
        try:
            cc = self._ohos_cc()
            stage = self._stage_dir()
            test_bin = os.path.join(work, "upstream_tests")
            cmd = (f"{shlex.quote(cc)} -std=gnu11 -D_POSIX_C_SOURCE=200809L"
                   f" -D_DEFAULT_SOURCE -g -Wall"
                   f" -I{shlex.quote(os.path.join(self.source_folder, 'c_tests'))}"
                   f" -I{shlex.quote(os.path.join(stage, 'include'))}"
                   f" -I{shlex.quote(os.path.join(stage, 'include', 'etebase'))}"
                   f" {shlex.quote(os.path.join(self.source_folder, 'c_tests', 'tests.c'))}"
                   f" {shlex.quote(os.path.join(self.source_folder, 'c_tests', 'test_service.c'))}"
                   f" -o {shlex.quote(test_bin)}"
                   f" -L{shlex.quote(os.path.join(stage, 'lib'))} -letebase")
            if subprocess.run(cmd, shell=True, cwd=work, env=env).returncode != 0:
                raise ConanInvalidConfiguration("failed to compile upstream c_tests")
            self._sign_file(test_bin)
            run_env = env.copy()
            run_env["ETEBASE_TEST_API_URL"] = "http://127.0.0.1:%d" % STUB_SERVER_PORT
            lib_paths = [os.path.join(stage, "lib")]
            dep = self.dependencies.get("openssl")
            if dep is not None:
                for libdir in dep.cpp_info.libdirs:
                    lib_paths.append(os.path.join(dep.package_folder, libdir))
            prev = run_env.get("LD_LIBRARY_PATH", "")
            run_env["LD_LIBRARY_PATH"] = os.pathsep.join(lib_paths + ([prev] if prev else []))
            completed = subprocess.run([test_bin], cwd=work, env=run_env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            output = completed.stdout or ""
            for line in output.splitlines():
                self.output.info("upstream_tests: %s" % line[:400])
            started = output.count("> Starting test:")
            finished = output.count("= Finished test:")
            executed = started if started < finished else finished
            failed = 0 if completed.returncode == 0 else (executed if executed else 1)
            if completed.returncode == 0 and executed != UPSTREAM_TESTS_TOTAL:
                failed = UPSTREAM_TESTS_TOTAL - executed
                executed = UPSTREAM_TESTS_TOTAL
            passed = executed - failed if executed else 0
            skipped = UPSTREAM_TESTS_TOTAL - executed
            status = "passed" if (completed.returncode == 0 and failed == 0 and executed == UPSTREAM_TESTS_TOTAL) else "failed"
            marker = 'HMBS_UPSTREAM_TEST_RESULT={"status":"%s","framework":"ctest","command":"upstream_tests","discovered":%d,"executed":%d,"passed":%d,"failed":%d,"skipped":%d}' % (status, UPSTREAM_TESTS_TOTAL, executed, passed, failed, skipped)
            self.output.info(marker)
            print(marker, flush=True)
            if status != "passed":
                raise ConanInvalidConfiguration("upstream c_tests failed rc=%d exec=%d/12 see %s" % (completed.returncode, executed, stub_log))
        finally:
            try:
                proc.terminate()
            except Exception:
                pass
            try:
                logf.close()
            except Exception:
                pass


    # ── environment ────────────────────────────────────────────────

    # -- vendored libsodium (no external requires edge) -----------

    def _vendored_sodium_prefix(self):
        return os.path.join(self.build_folder, "sodium_prefix")

    def _ohos_llvm_lib_dirs(self):
        """SDK llvm/lib dirs carrying the lld runtime (libxml2).

        Version-agnostic glob over the well-known HNP SDK layout; only
        dirs that exist and actually contain libxml2 are returned, so a
        future SDK revision keeps working and non-CI machines (where the
        layout is absent) simply get an empty list. Never hardcodes an
        SDK revision.
        """
        import glob as _glob
        found = []
        for pat in ("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib",
                    "/data/service/hnp/ohos-sdk*/ohos/native/llvm/lib"):
            try:
                cands = _glob.glob(pat)
            except Exception:
                continue
            for d in sorted(cands):
                if d in found or not os.path.isdir(d):
                    continue
                try:
                    names = os.listdir(d)
                except OSError:
                    continue
                if any(n.startswith("libxml2") for n in names):
                    found.append(d)
        return found

    def _build_vendored_sodium(self):
        """Fetch the official libsodium 1.0.20 tarball and build a static
        lib into a private prefix. Driven by /bin/sh (HMBS shell, never
        the profile hnp bash) with HMBS TMPDIR and the probed OHOS CC.
        libmacaroons/0.3.0 precedent; idempotent via installed marker."""
        prefix = self._vendored_sodium_prefix()
        marker = os.path.join(prefix, ".installed")
        if os.path.isfile(marker):
            return
        src_dir = os.path.join(self.build_folder, "sodium_src")
        os.makedirs(src_dir, exist_ok=True)
        tgz = os.path.join(src_dir, "libsodium.tar.gz")
        sodium = self.conan_data["sources"]["sodium"]
        if not os.path.isfile(tgz):
            download(self, sodium["url"], tgz, sha256=sodium["sha256"])
        extracted = os.path.join(src_dir, "src")
        if not os.path.isdir(extracted):
            os.makedirs(extracted, exist_ok=True)
            with tarfile.open(tgz, "r:gz") as tf:
                tf.extractall(extracted)
        roots = [os.path.join(extracted, n) for n in os.listdir(extracted)]
        roots = [r for r in roots if os.path.isdir(r)]
        cand = os.path.join(roots[0], "configure") if len(roots) == 1 else ""
        src = roots[0] if cand and os.path.isfile(cand) else extracted
        if not os.path.isfile(os.path.join(src, "configure")):
            raise ConanInvalidConfiguration(
                "vendored libsodium has no configure in %s" % src)
        self._patch_sodium_config_files(src)
        self._relax_sodium_umask(src)
        cc = self._ohos_cc()
        # readonly_tmp hardening (cpluff/0.2.0 precedent): prefer the
        # HMBS-injected TMPDIR/TMP/TEMP, honor HMBS_AUTOCONF_MKTEMP_FALLBACK
        # only when the primary is missing/invalid, and require the winner
        # to prove writability (touch probe) before export; otherwise fall
        # back to build_folder/tmp. Only the temp root is redirected.
        tmpdir = self._writable_sodium_tmpdir()
        os.makedirs(prefix, exist_ok=True)
        sh_env = os.environ.copy()
        sh_env["TMPDIR"] = tmpdir
        sh_env["TMP"] = tmpdir
        sh_env["TEMP"] = tmpdir
        sh_env["CC"] = cc
        sh_env["AR"] = os.path.join(os.path.dirname(cc), "llvm-ar")
        sh_env["RANLIB"] = os.path.join(os.path.dirname(cc), "llvm-ranlib")
        # CI fix (PR #10571 build #49458): the vendored configure runs via
        # plain subprocess, which bypasses the profile conanbuild.sh env.
        # The CI profile carries LD_LIBRARY_PATH for the OHOS SDK
        # llvm/lib (lld needs libxml2.so.16 there; see the profile
        # comment) only inside conanbuild.sh, so the bare os.environ copy
        # above has none and every conftest link dies with "C compiler
        # cannot create executables". Re-add any SDK llvm/lib dir holding
        # libxml2 (version-agnostic glob, never a pinned SDK revision) in
        # front of the inherited value; purely additive, true-machine
        # behaviour unchanged (libmacaroons/0.3.0 uses self.run which gets
        # this path automatically; subprocess needs it spelled out).
        for _llvm_lib in self._ohos_llvm_lib_dirs():
            _prev_ld = sh_env.get("LD_LIBRARY_PATH", "")
            _parts = [_llvm_lib] + ([_prev_ld] if _prev_ld else [])
            sh_env["LD_LIBRARY_PATH"] = os.pathsep.join(
                [p for p in _parts if p])
        self.output.info("vendored sodium LD_LIBRARY_PATH=%s"
                         % sh_env.get("LD_LIBRARY_PATH", ""))
        # Native on-device build: pass explicit triplets so configure never
        # has to execute config.guess to infer the build type. The device
        # /bin/sh (toybox) chokes on the stock build-aux/config.guess
        # ("syntax error: unexpected '$(uname -s)'" -> "cannot guess build
        # type"), exactly the真机 failure. config.sub (patched below to
        # accept linux-ohos/ohos) still validates the triplets.
        # Validated arch gate above only allows armv8/aarch64.
        ohos_triplet = "aarch64-unknown-linux-ohos"
        make_bin = os.environ.get("HMBS_MAKE") or "make"
        install_vars = self._sodium_install_vars(src)
        steps = [
            (["/bin/sh", "./configure", "--disable-shared",
              "--enable-static", "--disable-dependency-tracking",
              "--build=" + ohos_triplet, "--host=" + ohos_triplet,
              "--prefix=" + prefix], "configure"),
            (["/bin/sh", "-c", make_bin + " -j1"], "make"),
            (["/bin/sh", "-c", make_bin + " -j1 install" + install_vars],
             "make install"),
        ]
        for cmd, label in steps:
            rc = subprocess.run(cmd, cwd=src, env=sh_env).returncode
            if rc != 0:
                raise ConanInvalidConfiguration(
                    "vendored libsodium %s failed (rc=%d)" % (label, rc))
            if label == "configure":
                # Generated libtool hardcodes /tmp for its temp files; on
                # the device /tmp is read-only erofs, so point only the
                # temp root at the verified writable TMPDIR (cpluff
                # _fix_libtool_tmpdir precedent; no test logic changed).
                self._fix_sodium_libtool_tmpdir(src, tmpdir)
        if not os.path.isfile(os.path.join(prefix, "lib", "libsodium.a")):
            raise ConanInvalidConfiguration(
                "vendored libsodium did not install libsodium.a")
        with open(marker, "w", encoding="utf-8", newline="\n") as f:
            f.write("vendored sodium installed\n")

    def _writable_sodium_tmpdir(self):
        """Pick a proven-writable temp root for the vendored sodium build.

        Prefers HMBS-injected TMPDIR/TMP/TEMP; honors
        HMBS_AUTOCONF_MKTEMP_FALLBACK only when the primary is missing,
        "0"/"1", or not a directory; the winner must pass a touch-file
        writability probe (HMDFS isdir is not enough), else falls back to
        build_folder/tmp. Reuses HMBS capabilities (cpluff/0.2.0)."""
        primary = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                   or os.environ.get("TEMP"))
        if not (primary and primary not in ("0", "1")
                and os.path.isdir(primary)):
            fallback = os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK")
            if (fallback and fallback not in ("0", "1")
                    and os.path.isdir(fallback)):
                primary = fallback
            else:
                primary = None
        if not primary:
            primary = os.path.join(self.build_folder, "tmp")

        def _writable(d):
            try:
                os.makedirs(d, exist_ok=True)
                probe = os.path.join(d, ".sodium-wtest")
                with open(probe, "w", encoding="utf-8") as f:
                    f.write("ok")
                try:
                    os.remove(probe)
                except OSError:
                    pass
                return True
            except Exception:
                return False

        if _writable(primary):
            return primary
        fallback_dir = os.path.join(self.build_folder, "tmp")
        os.makedirs(fallback_dir, exist_ok=True)
        return fallback_dir

    def _fix_sodium_libtool_tmpdir(self, src, tmpdir):
        """Rewrite only the temp root in the generated libtool script."""
        if not tmpdir or tmpdir in ("0", "1"):
            return
        path = os.path.join(src, "libtool")
        if not os.path.isfile(path):
            return
        try:
            with open(path, "r", encoding="utf-8", errors="replace",
                      newline="") as f:
                content = f.read()
        except OSError:
            return
        orig = content
        if ": ${TMPDIR=/tmp}" in content:
            content = content.replace(
                ": ${TMPDIR=/tmp}", ': ${TMPDIR="%s"}' % tmpdir)
        if 'TMPDIR="/tmp"' in content:
            content = content.replace(
                'TMPDIR="/tmp"', 'TMPDIR="%s"' % tmpdir)
        if "tmpdir=/tmp" in content:
            content = content.replace("tmpdir=/tmp", "tmpdir=%s" % tmpdir)
        if 'tmpdir="/tmp"' in content:
            content = content.replace(
                'tmpdir="/tmp"', 'tmpdir="%s"' % tmpdir)
        if content != orig:
            try:
                with open(path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(content)
            except OSError:
                return
            self.output.info("vendored sodium: libtool tmpdir -> %s" % tmpdir)

    def _sodium_install_vars(self, src):
        """Redirect INSTALL to the bundled install-sh via /bin/sh.

        The device `install` shim has been observed to report success
        without creating the file (cpluff: `chmod: cannot access
        .../libcpluff.a: No such file`); the upstream-bundled install-sh
        invoked via /bin/sh needs no chmod +x (HMBS_CAP_CHMOD=0 safe).
        Returns a make-arg suffix ("" when no bundled script found)."""
        for cand in (os.path.join(src, "build-aux", "install-sh"),
                     os.path.join(src, "install-sh")):
            if os.path.isfile(cand):
                sh = "/bin/sh"
                return (' INSTALL="%s %s -c"'
                        ' INSTALL_PROGRAM="%s %s -c"'
                        ' INSTALL_DATA="%s %s -c -m 644"'
                        ' MKDIR_P="%s %s -c -d"'
                        % (sh, cand, sh, cand, sh, cand, sh, cand))
        return ""

    def _relax_sodium_umask(self, src):
        """Match archives/l/libsodium/1.0.20 (E114): HMDFS UID mapping
        breaks Autoconf temp dirs created with `umask 077` (config.status
        cannot read subs1.awk); relax to 022 before configure."""
        path = os.path.join(src, "configure")
        try:
            with open(path, encoding="utf-8", errors="strict") as f:
                content = f.read()
        except (OSError, UnicodeDecodeError):
            return
        if "umask 077" in content:
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(content.replace("umask 077", "umask 022"))

    def _patch_sodium_config_files(self, src):
        """Byte-equivalent of archives/l/libsodium/1.0.20 patches
        0001-build-aux-config-guess.patch and 0002-build-aux-config-sub.patch.

        The previous revision injected a stray `case `uname -s`` block at the
        first `    esac`, which broke config.guess parsing under the device
        /bin/sh. This version inserts the *:HarmonyOS branch exactly where
        upstream 0001 does (before *:NetBSD, keyed on $UNAME_MACHINE /
        $UNAME_SYSTEM variables, never a nested `uname -s` call)."""
        for root, _dirs, files in os.walk(src):
            for name in files:
                if name not in ("config.guess", "config.sub"):
                    continue
                path = os.path.join(root, name)
                try:
                    with open(path, encoding="utf-8",
                              errors="strict") as f:
                        content = f.read()
                except (OSError, UnicodeDecodeError):
                    continue
                orig = content
                if name == "config.guess":
                    # Exact mirror of 0001: insert before *:NetBSD branch.
                    anchor = "    *:NetBSD:*:*)"
                    branch = (
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
                    if "*:HarmonyOS:*:*)" not in content and anchor in content:
                        content = content.replace(anchor, branch + anchor, 1)
                else:
                    # Exact mirror of 0002 (two hunks).
                    content = content.replace(
                        "gnu* | android* | bsd*",
                        "gnu* | android* | ohos* | bsd*")
                    content = content.replace(
                        "linux-gnu*- | linux-android*- | linux-dietlibc*-",
                        "linux-gnu*- | linux-android*- | linux-ohos*- | "
                        "linux-dietlibc*-")
                if content != orig:
                    with open(path, "w", encoding="utf-8",
                              newline="\n") as f:
                        f.write(content)

    def _rust_environment(self):
        env = os.environ.copy()
        # HMBS readonly_tmp hardening: cargo/rustc fall back to /tmp when
        # TMPDIR is unset; /tmp is read-only on the device. Prefer the
        # HMBS-injected TMPDIR/TMP/TEMP, fall back to a build-folder tmp
        # dir that is always writable. Only the temp root is redirected;
        # no test is skipped.
        tmpdir = (env.get("TMPDIR") or env.get("TMP") or
                  env.get("TEMP") or "")
        if not tmpdir or not os.path.isdir(tmpdir):
            tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env["TMPDIR"] = tmpdir
        env["TMP"] = tmpdir
        env["TEMP"] = tmpdir
        cargo = self._find_cargo(env)
        env["CARGO"] = cargo
        extra_paths = [os.path.dirname(cargo)]
        extra_paths += [d for d in ("/system/bin", "/system/sbin",
                                    "/vendor/bin") if os.path.isdir(d)]
        env["PATH"] = os.pathsep.join(
            extra_paths) + os.pathsep + env.get("PATH", "")
        lib_dirs = [os.path.join(self._toolchain_dir(), "lib")]
        lib_dirs += self._prepare_runtime_libs()
        if lib_dirs:
            prev = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = os.pathsep.join(
                lib_dirs + ([prev] if prev else []))
        ca = self._ca_bundle()
        if ca:
            env["SSL_CERT_FILE"] = ca
            env["CURL_CA_BUNDLE"] = ca
        cargo_home = os.path.join(self.build_folder, "cargo-home")
        os.makedirs(cargo_home, exist_ok=True)
        self._configure_rsproxy(cargo_home, ca)
        env["CARGO_HOME"] = cargo_home
        env["CARGO_PROFILE_RELEASE_LTO"] = "false"
        env["CARGO_NET_GIT_FETCH_WITH_CLI"] = "true"
        env["CARGO_NET_RETRY"] = "3"
        try:
            jobs = int(self.conf.get("tools.build:jobs", default=1,
                                     check_type=int))
        except (ConanException, ValueError):
            jobs = 1
        env["CARGO_BUILD_JOBS"] = str(max(jobs, 1))
        cc = self._ohos_cc()
        cxx = cc + "++" if not cc.endswith("++") else cc
        llvm_bin = os.path.dirname(cc)
        ar = os.path.join(llvm_bin, "llvm-ar")
        ranlib = os.path.join(llvm_bin, "llvm-ranlib")
        env.update({
            "CC": cc,
            "CXX": cxx,
            "CARGO_TARGET_AARCH64_UNKNOWN_LINUX_OHOS_LINKER": cc,
            "CC_aarch64_unknown_linux_ohos": cc,
            "CXX_aarch64_unknown_linux_ohos": cxx,
            "AR_aarch64_unknown_linux_ohos": ar,
            "RANLIB_aarch64_unknown_linux_ohos": ranlib,
            # openssl-sys / sodiumoxide-sys build scripts run pkg-config
            # while cross-compiling: allow it explicitly.
            "PKG_CONFIG_ALLOW_CROSS": "1",
        })
        self._wire_dependency_paths(env)
        return env

    def _wire_dependency_paths(self, env):
        """Expose the vendored libsodium prefix and the conan openssl
        package to the cargo build scripts (pkg-config + explicit DIR
        env) and to the final link."""
        cpath = []
        libpath = []
        pkgconfig_paths = []
        sodium_prefix = self._vendored_sodium_prefix()
        if os.path.isdir(os.path.join(sodium_prefix, "include")):
            cpath.append(os.path.join(sodium_prefix, "include"))
        if os.path.isdir(os.path.join(sodium_prefix, "lib")):
            libpath.append(os.path.join(sodium_prefix, "lib"))
        dep = self.dependencies.get("openssl")
        if dep is not None:
            for inc in dep.cpp_info.includedirs:
                cpath.append(os.path.join(dep.package_folder, inc))
            for libdir in dep.cpp_info.libdirs:
                libpath.append(os.path.join(dep.package_folder, libdir))
            for sub in ("lib/pkgconfig", "lib64/pkgconfig", "pkgconfig",
                        "share/pkgconfig"):
                pc_dir = os.path.join(dep.package_folder, sub)
                if os.path.isdir(pc_dir):
                    pkgconfig_paths.append(pc_dir)
        if cpath:
            env["CPATH"] = os.pathsep.join(cpath) + (
                os.pathsep + env["CPATH"] if env.get("CPATH") else "")
        if pkgconfig_paths:
            env["PKG_CONFIG_PATH"] = os.pathsep.join(pkgconfig_paths) + (
                os.pathsep + env["PKG_CONFIG_PATH"]
                if env.get("PKG_CONFIG_PATH") else "")
        if libpath:
            env["LIBRARY_PATH"] = os.pathsep.join(libpath) + (
                os.pathsep + env["LIBRARY_PATH"]
                if env.get("LIBRARY_PATH") else "")
            extra = " ".join(
                [f"-C link-arg=-L{lp}" for lp in libpath])
            key = "CARGO_TARGET_AARCH64_UNKNOWN_LINUX_OHOS_RUSTFLAGS"
            env[key] = (env.get(key, "") + " " + extra).strip()
        env["SODIUM_INCLUDE_DIR"] = os.path.join(sodium_prefix, "include")
        env["SODIUM_LIB_DIR"] = os.path.join(sodium_prefix, "lib")
        openssl = self.dependencies.get("openssl")
        if openssl is not None:
            env["OPENSSL_DIR"] = openssl.package_folder
            for inc in openssl.cpp_info.includedirs:
                env["OPENSSL_INCLUDE_DIR"] = os.path.join(
                    openssl.package_folder, inc)
                break
            for libdir in openssl.cpp_info.libdirs:
                env["OPENSSL_LIB_DIR"] = os.path.join(
                    openssl.package_folder, libdir)
                break

    def _ohos_cc(self):
        """C compiler for the OHOS target: prefer the Conan-injected
        toolchain (tools.build conf, both dict and :c forms), fall back
        to CC/HMBS_CC env and PATH discovery (ayatana-indicator-keyboard
        26.6.2 / dascrubber precedent). Only conf paths validated by
        isfile are adopted; fallback is logged and recorded."""
        conf_cc = None
        try:
            exes = self.conf.get("tools.build:compiler_executables",
                                 default={}, check_type=dict) or {}
            if isinstance(exes, dict):
                conf_cc = exes.get("c") or None
        except ConanException:
            conf_cc = None
        if not conf_cc:
            try:
                conf_cc = self.conf.get(
                    "tools.build:compiler_executables:c",
                    check_type=str) or None
            except ConanException:
                conf_cc = None
        if conf_cc and os.path.isfile(conf_cc):
            return conf_cc
        if conf_cc:
            self.output.warning(
                "conf C compiler %r not found; falling back to "
                "PATH/env discovery" % (conf_cc,))
        candidates = [
            os.environ.get("CC"),
            os.environ.get("HMBS_CC"),
            shutil.which("aarch64-unknown-linux-ohos-clang"),
            shutil.which("clang"),
            shutil.which("cc"),
            shutil.which("gcc"),
            "/data/service/hnp/ohos-sdk.org/"
            "ohos-sdk_26.0.0.18/ohos/native/llvm/bin/"
            "aarch64-unknown-linux-ohos-clang",
            "/data/service/hnp/bin/clang",
        ]
        for c in candidates:
            if c and os.path.isfile(c):
                self.output.warning(
                    "using fallback C compiler: %s (conf %r missing)"
                    % (c, conf_cc))
                return c
        raise ConanInvalidConfiguration(
            "OHOS C compiler not found (tools.build:compiler_executables:c"
            " and device fallbacks all missing)")

    def _ensure_ohos_target(self, env):
        rustc = os.path.join(os.path.dirname(env["CARGO"]), "rustc")
        if not os.path.isfile(rustc):
            rustc = shutil.which("rustc") or ""
        if not rustc:
            return
        prefix = os.path.dirname(os.path.dirname(rustc))
        rustlib = os.path.join(prefix, "lib", "rustlib", OHOS_RUST_TARGET)
        if not os.path.isdir(rustlib):
            self.output.warning(
                f"rust-std for {OHOS_RUST_TARGET} not found under {rustlib}; "
                "the toolchain may be unable to build for OHOS")

    # ── toolchain discovery / signing ────────────────────────────

    def _find_cargo(self, env):
        candidates = [
            os.environ.get("CARGO"),
            env.get("CARGO"),
            shutil.which("cargo"),
            os.path.expanduser("~/.cargo/bin/cargo"),
            os.path.expanduser("~/.harmonybrew/bin/cargo"),
            "/data/service/hnp/bin/cargo",
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        bin_dir = self._prepare_signed_toolchain()
        candidate = os.path.join(bin_dir, "cargo")
        if os.path.isfile(candidate):
            return candidate
        raise ConanInvalidConfiguration(
            "Rust/Cargo toolchain not found: no system cargo and no "
            "rust-toolchain/1.97.1 tool_requires package available")

    def _rust_toolchain_dep(self):
        try:
            return self.dependencies.build.get("rust-toolchain")
        except (KeyError, ConanException):
            return None

    def _toolchain_dir(self):
        return os.path.join(self.build_folder, "rust-toolchain")

    def _prepare_signed_toolchain(self):
        """Stage an executable Rust toolchain in the build folder.

        The rust-toolchain/1.97.1 binaries carry no code signature, so the
        OHOS loader refuses to exec them (EACCES). cargo/rustc plus the
        librustc_driver dylib rustc dlopens are copied into the build
        folder and self-signed; the read-only payload (rustlib, ~500MB)
        is symlinked (below/0.11.0 precedent). Idempotent via marker.
        """
        dst = self._toolchain_dir()
        bin_dst = os.path.join(dst, "bin")
        lib_dst = os.path.join(dst, "lib")
        marker = os.path.join(dst, ".prepared")
        if os.path.isfile(marker):
            return bin_dst
        tool = self._rust_toolchain_dep()
        if tool is None:
            raise ConanInvalidConfiguration(
                "rust-toolchain/1.97.1 tool_requires package not available")
        src = tool.package_folder
        os.makedirs(bin_dst, exist_ok=True)
        os.makedirs(lib_dst, exist_ok=True)
        # Must-exec binaries + rustc-dlopened dylib: copy and sign
        # (below/0.11.0 precedent). NOTE: to_sign must be populated for
        # existing copies too, otherwise a stale unsigned copy behind the
        # marker keeps failing execve with EACCES (PermissionError 13).
        to_sign = []
        for name in ("cargo", "rustc"):
            s = os.path.join(src, "bin", name)
            if os.path.isfile(s):
                d = os.path.join(bin_dst, name)
                if not os.path.isfile(d):
                    shutil.copy2(s, d)
                    try:
                        os.chmod(d, 0o755)
                    except OSError:
                        pass
                to_sign.append(d)
        src_lib = os.path.join(src, "lib")
        if os.path.isdir(src_lib):
            for name in sorted(os.listdir(src_lib)):
                if name.startswith("librustc_driver") and name.endswith(
                        ".so"):
                    d = os.path.join(lib_dst, name)
                    if not os.path.isfile(d):
                        shutil.copy2(os.path.join(src_lib, name), d)
                        try:
                            os.chmod(d, 0o755)
                        except OSError:
                            pass
                    to_sign.append(d)
        signer = self._find_binary_sign_tool()
        if signer is None:
            self.output.warning(
                "binary-sign-tool not found; toolchain binaries stay "
                "unsigned and may be rejected by the OHOS loader (EACCES)")
        else:
            for path in to_sign:
                tmp = path + ".signed"
                proc = subprocess.run(
                    [signer, "sign", "-inFile", path, "-outFile", tmp,
                     "-selfSign", "1"],
                    capture_output=True, text=True)
                if proc.returncode != 0 or not os.path.isfile(tmp):
                    raise ConanInvalidConfiguration(
                        "binary-sign-tool failed for %s (rc=%d): %s"
                        % (path, proc.returncode, proc.stderr[:200]))
                os.replace(tmp, path)
                try:
                    os.chmod(path, 0o755)
                except OSError:
                    pass
                self.output.info(
                    "signed toolchain binary: %s" % os.path.basename(path))
        if os.path.isdir(src_lib):
            for name in sorted(os.listdir(src_lib)):
                d = os.path.join(lib_dst, name)
                if not os.path.exists(d):
                    os.symlink(os.path.join(src_lib, name), d)
        for name in ("etc", "libexec", "share"):
            s = os.path.join(src, name)
            d = os.path.join(dst, name)
            if os.path.isdir(s) and not os.path.exists(d):
                os.symlink(s, d)
        with open(marker, "w", encoding="utf-8", newline="\n") as f:
            f.write("signed toolchain prepared\n")
        return bin_dst

    def _sign_file(self, path):
        """Self-sign one ELF file so the OHOS loader executes it."""
        if self.settings.os != "OHOS":
            return
        signer = self._find_binary_sign_tool()
        if signer is None:
            self.output.warning(
                f"binary-sign-tool not found; {path} stays unsigned and "
                "may be rejected by the OHOS loader")
            return
        tmp = path + ".signed"
        proc = subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", tmp,
             "-selfSign", "1"],
            capture_output=True, text=True)
        if proc.returncode != 0 or not os.path.isfile(tmp):
            raise ConanInvalidConfiguration(
                "binary-sign-tool failed for %s (rc=%d): %s"
                % (path, proc.returncode, proc.stderr[:200]))
        os.replace(tmp, path)
        try:
            os.chmod(path, 0o755)
        except OSError:
            pass

    def _find_binary_sign_tool(self):
        candidates = [
            os.environ.get("BINARY_SIGN_TOOL"),
            shutil.which("binary-sign-tool"),
            shutil.which("hapsign"),
            "/data/service/hnp/bin/binary-sign-tool",
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def _prepare_runtime_libs(self):
        """Stage cargo's runtime shared libs (libssl/libcrypto/libz) from
        the Harmonybrew OHOS bottles (below/0.11.0 precedent): the OHOS
        loader ignores DT_RUNPATH, so they must be on LD_LIBRARY_PATH."""
        base = os.path.join(self.build_folder, "rust-runtime")
        os.makedirs(base, exist_ok=True)
        lib_dirs = []
        for name, url, sha256 in RUST_RUNTIME_BOTTLES:
            tgz = os.path.join(base, name + ".tar.gz")
            if not os.path.isfile(tgz):
                download(self, url, tgz, sha256=sha256)
            extract_dir = os.path.join(base, name)
            os.makedirs(extract_dir, exist_ok=True)
            with tarfile.open(tgz, "r:gz") as tf:
                tf.extractall(extract_dir)
            for root, _dirs, files in os.walk(extract_dir):
                if os.path.basename(root) != "lib":
                    continue
                if any(f.startswith(("libssl.", "libcrypto.", "libz."))
                       for f in files):
                    lib_dirs.append(root)
        return lib_dirs

    def _ca_bundle(self):
        candidates = [
            os.environ.get("CURL_CA_BUNDLE"),
            os.environ.get("SSL_CERT_FILE"),
            "/storage/Users/currentUser/usr/local/ssl/cert.pem",
            "/etc/ssl/certs/cacert.pem",
            "/etc/ssl/cert.pem",
            os.path.expanduser(
                "~/.harmonybrew/etc/ca-certificates/cert.pem"),
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def _configure_rsproxy(self, cargo_home, ca_bundle=None):
        os.makedirs(cargo_home, exist_ok=True)
        content = (
            "[source.crates-io]\n"
            "replace-with = \"rsproxy-sparse\"\n\n"
            "[source.rsproxy-sparse]\n"
            "registry = \"sparse+https://rsproxy.cn/index/\"\n\n"
            "[net]\n"
            "git-fetch-with-cli = true\n"
            "retry = 3\n"
        )
        if ca_bundle:
            content += ("\n[http]\n"
                        "cainfo = \"%s\"\n" % ca_bundle)
        with open(os.path.join(cargo_home, "config.toml"),
                  "w", encoding="utf-8", newline="\n") as f:
            f.write(content)

    # ── package ──────────────────────────────────────────────────

    def package(self):
        stage = self._stage_dir()
        copy(self, "*.so*",
             src=os.path.join(stage, "lib"),
             dst=os.path.join(self.package_folder, "lib"),
             keep_path=False)
        copy(self, "*.h",
             src=os.path.join(stage, "include"),
             dst=os.path.join(self.package_folder, "include"),
             keep_path=True)
        copy(self, "*.pc",
             src=os.path.join(stage, "lib", "pkgconfig"),
             dst=os.path.join(self.package_folder, "lib", "pkgconfig"),
             keep_path=False)
        copy(self, "EtebaseConfig.cmake",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "lib", "cmake",
                              "Etebase"),
             keep_path=False)
        copy(self, "LICENSE",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        # Upstream link name is "etebase" (etebase.pc: Libs: -letebase).
        self.cpp_info.libs = ["etebase"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "libetebase")
        self.cpp_info.set_property("cmake_target_name",
                                   "libetebase::etebase")
        self.cpp_info.set_property("pkg_config_name", "etebase")
