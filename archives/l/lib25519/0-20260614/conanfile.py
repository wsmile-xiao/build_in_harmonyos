#!/usr/bin/env python3
"""Conan recipe — lib25519 0-20260614 (custom ./configure + Makefile).

Upstream build system: ./configure (python3 script) + scripts-build/ + Makefile,
same djb family as libcpucycles (archives/l/libcpucycles/20260625), whose recipe
is the structural model for this file:
  - ./configure generates a build/<arch>/ tree (Makefile, compilers, dispatch).
    All probes are compile-only (try-*.c are compiled, never executed as target
    binaries), so cross compilation is safe.
  - make builds ofiles + static lib + shared lib + command tools into
    build/<arch>/package/ (include/lib25519.h, lib/lib25519.a,
    lib/lib25519.so.1 + lib25519.so symlink, bin/lib25519-*, man pages).
  - make install (scripts-build/install) is NOT used: like libcpucycles, it
    creates tempfile.TemporaryDirectory inside the setgid install target, which
    fails on the OHOS hmfs mount semantics (umask 077 + setgid -> EACCES).
    The recipe collects build/<arch>/package/ directly (install performs no
    compilation, only copy2 + rename, so this is semantically equivalent).

OHOS specifics beyond the libcpucycles model:
  1. Toolchain injection: upstream configure reads no environment variable
     (no getenv in configure); the only compiler source is compilers/default
     (one "<command> <flags>" per line, probed with --version, first usable
     line wins). build() prepends the profile-configured OHOS clang in the
     same format, keeping upstream candidate lines as fallback. Only the
     Conan build-cache copy is modified. Because the make-phase compiles do
     not reliably inherit the -I/-L flags from that line, build() additionally
     exposes the private staging dirs via C_INCLUDE_PATH/CPATH/LIBRARY_PATH
     (read by the clang driver itself, independent of the wrapper scripts).
  2. librandombytes is not yet published in this registry. The static archive
     only holds an undefined randombytes() reference, but the shared link
     (scripts/sharedlib lib25519 -lrandombytes) and the command tools need the
     symbol resolved. build() stages helpers/randombytes.{h,c} (OHOS
     getrandom(2) + /dev/urandom fallback, fail-closed) into a private staging
     dir, archives it to librandombytes.a, and appends -I/-L for that dir to
     the prepended compiler line. The shared library therefore statically
     embeds the helper (no DT_NEEDED on an external librandombytes), and the
     helper is never installed. Replace with a real requires() once
     librandombytes is published. The same staging dir carries a minimal
     cpucycles.h + stub libcpucycles.a for the *unpackaged* benchmark tool
     command/lib25519-speed only (the sole consumer of <cpucycles.h> /
     -lcpucycles; neither the library nor lib25519-test references it), so
     plain `make` succeeds; the stub is never installed or packaged.
  3. Upstream tests (command/lib25519-test, SUPERCOP-style known-answer tests
     plus the lib25519-fulltest wrapper) exist and are executed: after make,
     build() runs the 13 operation splits from the upstream `api` file
     (verify/32 ... sign/ed25519), each of which must print
     "all tests succeeded" and exit 0. The valgrind data-flow variant is
     skipped (valgrind is unavailable on OHOS; configure gets --no-valgrind).
     Evidence is persisted to res/upstream_test_result.json in the package and
     re-emitted by test_package (cache-hit safe).
  4. ifunc dispatch: OHOS uses the musl loader, which cannot resolve
     GNU IFUNC relocations. Upstream's compile-only probe (dispatch/ifunc.do:
     compile ifunc-test.c + readelf grep IFUNC) still succeeds under OHOS
     clang, so the default --tryifunc selects the ifunc resolver and every
     lib25519_* symbol fails at load time ("symbol not found" under musl).
     build() therefore passes --no-tryifunc explicitly, forcing the upstream
     constructor dispatch (function-pointer + __attribute__((constructor))),
     which is the documented musl-compatible alternative.
"""

import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, get


class Lib25519Conan(ConanFile):
    name = "lib25519"
    version = "0-20260614"
    description = "X25519 key exchange and Ed25519 signatures using Curve25519"
    topics = ("curve25519", "x25519", "ed25519", "cryptography", "signatures")
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    homepage = "https://lib25519.cr.yp.to"
    license = "MIT"
    # Both package layouts are really produced: package/lib/lib25519.a via
    # scripts/staticlib and package/lib/lib25519.so.1 via scripts/sharedlib,
    # so shared=True/False both have real artifacts behind them.
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        copy(self, "helpers/*", src=self.recipe_folder, dst=self.export_sources_folder)

    def requirements(self):
        # Zero Conan dependencies (W0): libcpucycles is only needed by the
        # upstream speed tool (not built/packaged); librandombytes is not yet
        # published, so build() stages the private helpers/ implementation
        # instead of requiring it.
        pass

    # Upstream release behind the Debian-style snapshot version 0-20260614.
    _UPSTREAM_VERSION = "20260614"
    # configure --host value for OHOS aarch64 (platform.machine() aarch64
    # already sanitizes to arm64; passed explicitly for the record).
    _ARCH = "arm64"
    # Flags appended after the configured compiler on the prepended
    # compilers/default line (identical base to the upstream clang line;
    # OHOS clang wrapper already carries --sysroot/--target).
    _CC_FLAGS = "-Wall -fPIC -fwrapv -Qunused-arguments -O2"
    # The 13 (operation, primitive) pairs from the upstream `api` file; each
    # is one lib25519-test split and must independently report success.
    _UPSTREAM_SPLITS = [
        ("verify", "32"),
        ("hashblocks", "sha512"),
        ("hash", "sha512"),
        ("pow", "inv25519"),
        ("powbatch", "inv25519"),
        ("nP", "montgomery25519"),
        ("nPbatch", "montgomery25519"),
        ("nG", "merged25519"),
        ("nG", "montgomery25519"),
        ("mGnP", "ed25519"),
        ("multiscalar", "ed25519"),
        ("dh", "x25519"),
        ("sign", "ed25519"),
    ]

    def source(self):
        # strip_root: tarball unpacks lib25519-20260614/; strip so that
        # ./configure runs with cwd=source_folder.
        get(self, strip_root=True, **self.conan_data["sources"][self.version][0])

    def _cc(self):
        # Usable-compiler resolution: prefer the profile conf absolute path
        # only when it exists (preflight workers may carry a stale
        # /data/service/hnp/bin/clang); HMBS prepends the real tool dirs to
        # PATH, so fall back to PATH lookup for clang/cc. Never fail closed
        # on a stale conf path while a usable compiler exists on PATH.
        conf = self.conf.get("tools.build:compiler_executables")
        cc = conf.get("c") if conf else None
        if cc and os.path.isabs(str(cc)):
            if os.path.isfile(str(cc)) and os.access(str(cc), os.X_OK):
                return str(cc)
            self.output.warning(
                f"configured C compiler '{cc}' not found; falling back to PATH lookup"
            )
        elif cc:
            resolved = shutil.which(str(cc).split()[0])
            if resolved and os.path.isfile(resolved):
                return resolved
        for cand in ("clang", "cc", "gcc"):
            resolved = shutil.which(cand)
            if resolved and os.path.isfile(resolved):
                self.output.info(
                    f"using PATH C compiler '{resolved}' (conf c='{cc}')"
                )
                return resolved
        raise ConanException(
            f"no usable C compiler found (conf c='{cc}'; PATH lookup for clang/cc/gcc failed)"
        )

    def _ar(self):
        conf = self.conf.get("tools.build:compiler_executables")
        ar = conf.get("ar") if conf else None
        for cand in ([ar] if ar else []) + ["llvm-ar", "ar"]:
            resolved = shutil.which(cand)
            if resolved and os.path.isfile(resolved):
                return resolved
        raise ConanException("no archive tool (llvm-ar/ar) found for helper staging")

    def _stage_randombytes(self):
        # Build helpers/randombytes.c into a private static archive so the
        # upstream shared link (-lrandombytes) and command tools resolve.
        # Also stages a minimal cpucycles.h + stub libcpucycles.a used ONLY
        # by the unpackaged benchmark tool command/lib25519-speed (the sole
        # consumer of <cpucycles.h>/-lcpucycles; the library itself and
        # lib25519-test never reference cpucycles). The stub lets plain
        # `make` finish; it is never installed or packaged.
        # Returns (include_dir, lib_dir) for compiler flag injection.
        stage = os.path.join(self.build_folder, "rb_stage")
        inc_dir = os.path.join(stage, "include")
        lib_dir = os.path.join(stage, "lib")
        os.makedirs(inc_dir, exist_ok=True)
        os.makedirs(lib_dir, exist_ok=True)
        shutil.copy(
            os.path.join(self.export_sources_folder, "helpers", "randombytes.h"),
            os.path.join(inc_dir, "randombytes.h"),
        )
        obj = os.path.join(stage, "randombytes.o")
        archive = os.path.join(lib_dir, "librandombytes.a")
        cc = self._cc()
        self.run(f'"{cc}" -c -O2 -fPIC -o "{obj}" '
                 f'"{os.path.join(self.export_sources_folder, "helpers", "randombytes.c")}"')
        ar = self._ar()
        self.run(f'"{ar}" crs "{archive}" "{obj}"')
        # Benchmark-only cpucycles shim (see method docstring above).
        with open(os.path.join(inc_dir, "cpucycles.h"), "w", encoding="utf-8") as f:
            f.write("#pragma once\nlong long cpucycles(void);\n")
        stub_c = os.path.join(stage, "cpucycles_stub.c")
        with open(stub_c, "w", encoding="utf-8") as f:
            f.write("long long cpucycles(void){return 0;}\n")
        # FIX 2026-09-15: lib25519-speed needs the full cpucycles API
        # (cpucycles/persecond/implementation); overwrite the minimal shim
        # above with complete dummies. Uses chr(10) to avoid backslash escapes.
        with open(os.path.join(inc_dir, "cpucycles.h"), "w", encoding="utf-8") as f:
            f.write("#pragma once" + chr(10) + "long long cpucycles(void);" + chr(10) + "long long cpucycles_persecond(void);" + chr(10) + "const char *cpucycles_implementation(void);" + chr(10))
        with open(stub_c, "w", encoding="utf-8") as f:
            f.write("long long cpucycles(void){return 0;}" + chr(10) + "long long cpucycles_persecond(void){return 0;}" + chr(10) + "const char *cpucycles_implementation(void){return \"stub\";}" + chr(10))
        stub_obj = os.path.join(stage, "cpucycles_stub.o")
        stub_lib = os.path.join(lib_dir, "libcpucycles.a")
        self.run(f'"{cc}" -c -O2 -fPIC -o "{stub_obj}" "{stub_c}"')
        self.run(f'"{ar}" crs "{stub_lib}" "{stub_obj}"')
        return inc_dir, lib_dir

    def _export_staging_env(self, inc_dir, lib_dir):
        # The make-phase wrapper scripts (scripts/compile, scripts/sharedlib)
        # do not reliably carry the -I/-L flags embedded in the
        # compilers/default line, so expose the private staging dirs through
        # the compiler driver's own search-path variables, which clang
        # honours regardless of the wrapper scripts. Idempotent and
        # append-safe across rebuilds.
        for var, val in (("C_INCLUDE_PATH", inc_dir),
                         ("CPATH", inc_dir),
                         ("LIBRARY_PATH", lib_dir)):
            cur = os.environ.get(var, "")
            parts = [p for p in cur.split(os.pathsep) if p] if cur else []
            if val not in parts:
                os.environ[var] = os.pathsep.join([val] + parts)

    def _prepend_configured_compiler(self, inc_dir, lib_dir):
        # Same mechanism as libcpucycles: upstream configure only reads
        # compilers/default. Prepend the OHOS clang line (plus staging -I/-L
        # for the vendored randombytes); keep upstream lines as fallback.
        # Only the Conan build-cache copy is modified.
        cc = self._cc()
        line = f"{cc} {self._CC_FLAGS} -I{inc_dir} -L{lib_dir}"
        path = os.path.join(self.source_folder, "compilers", "default")
        with open(path, encoding="utf-8") as f:
            content = f.read()
        if content.startswith(line + "\n"):
            return  # idempotent across rebuilds
        with open(path, "w", encoding="utf-8") as f:
            f.write(line + "\n" + content)

    def _package_tree(self):
        # build/<arch>/package, resolving through the build/0 symlink when
        # present (configure symlinks 0 -> <arch>).
        zero = os.path.join(self.source_folder, "build", "0", "package")
        if os.path.isdir(zero):
            return os.path.realpath(zero)
        return os.path.join(self.source_folder, "build", self._ARCH, "package")

    def generate(self):
        pass

    def build(self):
        inc_dir, lib_dir = self._stage_randombytes()
        self._export_staging_env(inc_dir, lib_dir)
        self._prepend_configured_compiler(inc_dir, lib_dir)
        # --host=arm64 selects the arm64 (+portable) implementations added in
        # 20260614; --no-valgrind uses the normal headers (valgrind data-flow
        # tests unavailable on OHOS); --trim is upstream default (kept).
        # --no-tryifunc forces constructor dispatch: the musl loader on OHOS
        # cannot resolve GNU IFUNC symbols (see module docstring point 4);
        # the compile-only probe would otherwise select ifunc and break
        # every lib25519-test split at load time.
        self.run(
            f"./configure --prefix={self.package_folder} --host={self._ARCH} --no-valgrind --no-tryifunc",
            cwd=self.source_folder,
        )
        # R9: serial build on CI workers.
        self.run("make -j1", cwd=self.source_folder)
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        # Run each upstream `api` operation split through the freshly built
        # lib25519-test binary. Every split must print "all tests succeeded"
        # and exit 0. Logs are spooled to build_folder (never /tmp, which is
        # read-only on HarmonyOS workers) and parsed from disk.
        # OHOS loader notes (HMBS stale_runtime_library/readonly_tmp):
        # LD_LIBRARY_PATH is ignored by the OHOS loader, so the test binary
        # can resolve lib25519 symbols against a stale system library instead
        # of the just-built package/lib/lib25519.so.1 ("symbol not found"
        # for every lib25519_* symbol). Prefix each test invocation with
        # LD_PRELOAD=<fresh lib25519.so.1> (test-only, never exported
        # globally) while keeping LD_LIBRARY_PATH for loaders that honour
        # it. TMPDIR/TMP/TEMP are pointed at a writable build_folder dir.
        pkg = self._package_tree()
        test_bin = os.path.join(pkg, "bin", "lib25519-test")
        lib_dir = os.path.join(pkg, "lib")
        if not os.path.isfile(test_bin):
            raise ConanException(f"upstream test binary not built: {test_bin}")
        lib_so1 = os.path.join(lib_dir, "lib25519.so.1")
        if not os.path.isfile(lib_so1):
            # Fall back to the unversioned symlink target if the versioned
            # file is missing; log the directory for the next diagnosis.
            try:
                self.output.info(
                    f"upstream lib dir listing: {sorted(os.listdir(lib_dir))}"
                )
            except OSError as exc:
                self.output.info(f"upstream lib dir unreadable: {exc}")
            raise ConanException(f"upstream shared lib not built: {lib_so1}")
        try:
            self.output.info(
                f"upstream lib dir listing: {sorted(os.listdir(lib_dir))}"
            )
        except OSError as exc:
            self.output.info(f"upstream lib dir unreadable: {exc}")
        # Diagnostic: prove the fresh shared lib really exports the dispatch
        # symbols the test needs. If this grep fails, the next failure is a
        # broken build (not a stale-loader issue).
        for nm_cand in ("llvm-nm", "nm"):
            nm_tool = shutil.which(nm_cand)
            if not nm_tool:
                continue
            try:
                self.run(
                    f'"{nm_tool}" -D "{lib_so1}" 2>&1 | '
                    f'grep -E "lib25519_sign_ed25519$|lib25519_nG_montgomery25519$" '
                    f'|| echo "NM_DIAG: expected symbols not found in {lib_so1}"',
                    cwd=self.source_folder,
                )
                break
            except Exception as exc:
                self.output.info(f"nm diagnostic ({nm_cand}) failed: {exc}")
                break
        tmpdir = os.path.join(self.build_folder, "upstream_tmp")
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        discovered = len(self._UPSTREAM_SPLITS)
        passed = 0
        failed = 0
        for op, prim in self._UPSTREAM_SPLITS:
            log_path = os.path.join(self.build_folder, f"upstream_{op}_{prim}.log")
            try:
                self.run(
                    f'TMPDIR="{tmpdir}" TMP="{tmpdir}" TEMP="{tmpdir}" '
                    f'LD_LIBRARY_PATH="{lib_dir}" LD_PRELOAD="{lib_so1}" '
                    f'"{test_bin}" {op} {prim} '
                    f'> "{log_path}" 2>&1',
                    cwd=self.source_folder,
                )
                rc = 0
            except Exception:
                rc = 1
            ok = False
            try:
                with open(log_path, "r", encoding="utf-8", errors="replace") as f:
                    out = f.read()
                ok = rc == 0 and "all tests succeeded" in out
                self.output.info(f"upstream split {op}/{prim}: {'PASS' if ok else 'FAIL'}")
                if not ok:
                    self.output.info(f"--- {op}/{prim} output tail ---\n" + out[-2000:])
            except OSError as exc:
                self.output.info(f"upstream split {op}/{prim}: FAIL (unreadable log: {exc})")
            if ok:
                passed += 1
            else:
                failed += 1
        result = {
            "status": "passed" if failed == 0 else "failed",
            "framework": "lib25519-test",
            "command": "lib25519-test <op> <prim> for 13 api operation splits",
            "discovered": discovered,
            "executed": discovered,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
        }
        with open(os.path.join(self.build_folder, "upstream_test_result.json"),
                  "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False))
        if failed:
            raise ConanException(f"upstream lib25519-test failed: {passed}/{discovered} splits passed")

    def package(self):
        # Bypass upstream make install (hmfs setgid/tmp failure, see module
        # docstring); collect build/<arch>/package/ directly (copy+rename
        # only, no compilation inside install). CLI tools under bin/ are
        # intentionally not packaged: they are thin upstream wrappers and
        # would pull an L2 CLI contract; the Conan package ships the C API.
        pkg = self._package_tree()
        copy(self, "lib25519.h", os.path.join(pkg, "include"),
             os.path.join(self.package_folder, "include"))
        lib_dst = os.path.join(self.package_folder, "lib")
        if self.options.shared:
            copy(self, "lib25519.so*", os.path.join(pkg, "lib"), lib_dst)
        else:
            copy(self, "lib25519.a", os.path.join(pkg, "lib"), lib_dst)
        # Upstream test evidence for test_package re-emission (cache-hit safe).
        copy(self, "upstream_test_result.json", self.build_folder,
             os.path.join(self.package_folder, "res"))

    def package_info(self):
        self.cpp_info.libs = ["25519"]
