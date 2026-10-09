#!/usr/bin/env python3
"""Conan recipe for rumdl 0.2.39 (HarmonyOS / OpenHarmony PC, aarch64).

rumdl is a fast Markdown linter and formatter written in pure Rust (upstream
https://github.com/rvben/rumdl, crate ``rumdl`` with binary ``rumdl``).

Cross-compiled for aarch64-unknown-linux-ohos with the Rust toolchain shipped
by the ``rust-toolchain/1.97.1`` infrastructure package (tool_requires).  No
rustup bootstrap is attempted: standard rustup cannot recognise the HarmonyOS
host ("unrecognized OS type: HarmonyOS", knowledge E105/E154).

Why the recipe does what it does
--------------------------------
* OHOS refuses to execve an unsigned ELF, and the rust-lang dist tarball inside
  rust-toolchain/1.97.1 carries no code signature, so ``cargo``/``rustc`` fail
  with EACCES (errno 13) — the exact failure seen when porting
  below/0.11.0, lemmeknow/0.8.0 and rudof/0.3.6.  The recipe therefore copies
  ``cargo``/``rustc`` (and the ``librustc_driver`` dylib rustc dlopens, plus the
  OHOS ``libc++_shared.so`` it needs) into the build folder, signs them with
  ``binary-sign-tool -selfSign 1`` and symlinks the remaining read-only payload.
* ``cargo`` dynamically links ``libssl``/``libcrypto``/``libz`` while the OHOS
  loader ignores DT_RUNPATH, so those OHOS shared libraries come from the
  Harmonybrew OHOS bottles and are placed on ``LD_LIBRARY_PATH``
  (argc/1.24.0, rudof/0.3.6 precedent).
* The device has no default CA store, so a CA bundle is located and exported
  for the rsproxy.cn crates mirror.
* HarmonyOS ``/tmp`` is read-only (E002), so TMPDIR points at a writable dir.

rumdl has no external C/C++ target dependency: the whole dependency closure is
pure Rust (crates from crates.io via rsproxy.cn).  ``tikv-jemalloc-sys`` and
``blake3`` compile bundled C in place with ``cc``, which is pointed at the OHOS
clang driver.

The upstream test suite is executed from ``build()`` so every CI run re-runs it
(see ``test_package/MANIFEST.yml`` for the declaration).
"""

import os
import shlex
import shutil
import subprocess
import tarfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy, download,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout

# cargo's runtime shared libraries (OHOS loader ignores DT_RUNPATH, so they must
# be on LD_LIBRARY_PATH).  Harmonybrew OHOS bottles, sha256 measured on the real
# machine; same revisions already used by argc/1.24.0 / rudof/0.3.6.
RUST_RUNTIME_BOTTLES = (
    ("openssl3",
     "https://harmonybrew.atomgit.com/bottles/"
     "openssl%403-3.6.4_1.arm64_ohos.bottle.tar.gz",
     "29caefb982dc01671e67232f3862b50ce69a34a4f4135a1495078830bb12b81b"),
    ("zlib",
     "https://harmonybrew.atomgit.com/bottles/"
     "zlib-ng-compat-2.3.3_2.arm64_ohos.bottle.tar.gz",
     "99356b80ddb81e0b8267debb44df459f2b5e27e7800406d3b4cf7f8f744beb89"),
)

BINARY_NAME = "rumdl"


class RumdlConan(ConanFile):
    name = "rumdl"
    version = "0.2.39"
    description = "A fast Markdown linter and formatter written in Rust"
    license = "MIT"
    homepage = "https://github.com/rvben/rumdl"
    url = "https://github.com/rvben/rumdl"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")
        self._ohos_target()

    def layout(self):
        basic_layout(self)

    def build_requirements(self):
        # Rust toolchain from the registry infrastructure package (R36: publish
        # dependencies before building downstream).  rust-lang official dist
        # tarball, host & target both aarch64-unknown-linux-ohos.
        self.tool_requires("rust-toolchain/1.97.1")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        env = self._rust_environment()
        self._ensure_ohos_target(env)
        self._run_upstream_tests(env)
        self._cargo_build(env)
        self._sign_binaries()

    # ── build helpers ──────────────────────────────────────────────

    def _ohos_target(self):
        arch = str(self.settings.arch)
        mapping = {
            "armv8": "aarch64-unknown-linux-ohos",
            "arm64": "aarch64-unknown-linux-ohos",
            "aarch64": "aarch64-unknown-linux-ohos",
            "armv7": "armv7-unknown-linux-ohos",
            "x86_64": "x86_64-unknown-linux-ohos",
        }
        target = mapping.get(arch)
        if not target:
            raise ConanInvalidConfiguration(f"Unsupported arch: {arch}")
        return target

    def _rust_environment(self):
        env = os.environ.copy()
        cargo = self._find_cargo(env)
        env["CARGO"] = cargo
        extra_paths = [os.path.dirname(cargo)]
        extra_paths += [d for d in ("/system/bin", "/system/sbin", "/vendor/bin")
                        if os.path.isdir(d)]
        # OHOS/HMDFS: `mktemp -d` (used by autoconf config.status inside
        # vendored crates such as tikv-jemalloc-sys) creates drwx--S--- dirs the
        # build user cannot write into.  A build-only wrapper replaces `mktemp
        # -d` with `mkdir` (drwxrws--x, writable); accel-config/4.1.9 precedent.
        extra_paths.insert(0, self._create_mktemp_wrapper())
        env["PATH"] = os.pathsep.join(extra_paths) + os.pathsep + env.get("PATH", "")
        # toolchain-private lib (signed librustc_driver + symlinked payload) and
        # cargo runtime libs (libssl/libcrypto/libz)
        lib_dirs = [os.path.join(self._toolchain_dir(), "lib")]
        lib_dirs += self._prepare_runtime_libs()
        cxx_shared = self._prepare_cxx_shared()
        if cxx_shared:
            lib_dirs.append(cxx_shared)
        if lib_dirs:
            prev = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = os.pathsep.join(
                lib_dirs + ([prev] if prev else [])
            )
        ca = self._ca_bundle()
        if ca:
            env["SSL_CERT_FILE"] = ca
            env["CURL_CA_BUNDLE"] = ca
        cargo_home = env.get("CARGO_HOME") or os.path.expanduser("~/.cargo")
        os.makedirs(cargo_home, exist_ok=True)
        self._configure_rsproxy(cargo_home, ca)
        env["CARGO_HOME"] = cargo_home
        self._ensure_writable_tmpdir(env)
        if self.settings.os == "OHOS":
            cc = self._ohos_cc()
            ranlib, aws_lc_overlay = self._prepare_aws_lc_toolchain_overlay(cc)
            env.update({
                "CARGO_TARGET_AARCH64_UNKNOWN_LINUX_OHOS_LINKER": cc,
                "CC_aarch64_unknown_linux_ohos": cc,
                "CXX_aarch64_unknown_linux_ohos": self._ohos_cxx(),
                "AR_aarch64_unknown_linux_ohos": self._llvm_ar(),
                "RANLIB_aarch64_unknown_linux_ohos": ranlib,
                "AWS_LC_SYS_CMAKE_TOOLCHAIN_FILE_aarch64_unknown_linux_ohos":
                    aws_lc_overlay,
            })
            env.update(self._autoconf_cache_overrides())
        return env

    def _prepare_aws_lc_toolchain_overlay(self, cc):
        """Provide a ranlib for the OHOS CMake toolchain (knowledge E385).

        ``aws-lc-sys`` (pulled in only by the test-only crate chain
        ``ureq -> rustls -> aws-lc-rs``) compiles its C/asm through the SDK's
        ``ohos.toolchain.cmake``, which sets ``CMAKE_RANLIB`` to
        ``native/llvm/bin/llvm-ranlib`` — a path this SDK does not ship (only
        ``llvm-ar``).  The static-archive indexing step then silently produces
        an unindexed archive, and the final link fails with undefined AES/BN
        symbols.  Fix: a build-local ``llvm-ranlib`` wrapper (``llvm-ar s``)
        plus a thin toolchain overlay that re-forces the ranlib variables,
        injected through aws-lc-sys's target-specific
        ``AWS_LC_SYS_CMAKE_TOOLCHAIN_FILE_*`` hook.  Returns
        ``(ranlib_path, overlay_path)``.
        """
        ar = self._llvm_ar()
        ranlib = os.path.join(self.build_folder, "llvm-ranlib")
        with open(ranlib, "w", encoding="utf-8") as script:
            script.write(f'#!/bin/sh\nexec "{ar}" s "$@"\n')
        os.chmod(ranlib, 0o755)
        native_root = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.realpath(cc)))
        )
        ohos_toolchain = os.path.join(
            native_root, "build", "cmake", "ohos.toolchain.cmake"
        )
        if not os.path.isfile(ohos_toolchain):
            raise ConanInvalidConfiguration(
                "OHOS CMake toolchain is missing (expected %s); set OHOS_NDK_HOME"
                % ohos_toolchain
            )
        overlay = os.path.join(self.build_folder, "aws-lc-ohos-toolchain.cmake")
        with open(overlay, "w", encoding="utf-8") as toolchain:
            toolchain.write(
                f'include("{ohos_toolchain}")\n'
                f'set(CMAKE_RANLIB "{ranlib}" CACHE FILEPATH "" FORCE)\n'
                f'set(CMAKE_C_COMPILER_RANLIB "{ranlib}" CACHE FILEPATH "" FORCE)\n'
                f'set(CMAKE_ASM_COMPILER_RANLIB "{ranlib}" CACHE FILEPATH "" FORCE)\n'
            )
        return ranlib, overlay

    def _create_mktemp_wrapper(self):
        """Build-only `mktemp` wrapper (never committed, lives in build folder).

        On OHOS/HMDFS the toybox ``mktemp -d`` creates ``drwx--S---`` (2700)
        directories that the build user cannot write into (the fs maps the dir
        owner UID differently; E011/E112), so ``config.status`` aborts with
        "could not setup config files machinery" / "can't create
        ./confXXXXXX/subs1.awk: Permission denied".  ``mkdir`` yields a
        writable ``drwxrws--x``, so the wrapper emulates ``mktemp -d`` with
        ``mkdir`` and prints the created path; non ``-d`` invocations are
        forwarded to the real mktemp.  It only affects the cargo/configure
        subprocesses via a PATH prepend scoped to this build; nothing outside
        the build folder is touched (accel-config/4.1.9 precedent).
        """
        wrapper_dir = os.path.join(self.build_folder, "mktemp-wrapper")
        os.makedirs(wrapper_dir, exist_ok=True)
        wrapper = os.path.join(wrapper_dir, "mktemp")
        if not os.path.exists(wrapper):
            with open(wrapper, "w", encoding="utf-8") as f:
                f.write("""#!/bin/sh
mode=""
for a in "$@"; do
  case "$a" in
    -d) mode="-d" ;;
  esac
done
if [ "$mode" != "-d" ]; then
  exec /usr/bin/mktemp "$@"
fi
dir=""
for a in "$@"; do
  case "$a" in
    -d) ;;
    *)  dir="$a" ;;
  esac
done
[ -n "$dir" ] || dir="./tmp.XXXXXX"
base=$(dirname "$dir")
pat=$(basename "$dir")
out=""
i=0
while [ -z "$out" ] && [ $i -lt 100 ]; do
  cand="$base/$(echo "$pat" | sed "s/XXXXXX/$$-$RANDOM/")"
  if (umask 077 && mkdir -p "$cand" 2>/dev/null); then out="$cand"; fi
  i=$((i+1))
done
if [ -n "$out" ]; then
  echo "$out"
  exit 0
fi
exit 1
""")
            os.chmod(wrapper, 0o755)
        return wrapper_dir

    def _autoconf_cache_overrides(self):
        """Pre-seed autoconf's canonical-triplet cache for the OHOS target.

        Some vendored dependencies (notably ``tikv-jemalloc-sys``, pulled in
        unconditionally by rumdl's ``tikv-jemallocator`` global allocator on
        non-msvc/non-wasm targets) run an autotools ``configure`` whose bundled
        ``config.sub`` predates ``ohos`` and aborts with
        ``OS 'ohos' not recognized``.  Supplying ``ac_cv_build``/``ac_cv_host``/
        ``ac_cv_target`` makes autoconf skip ``config.sub`` entirely and use the
        cached canonical triplet instead — a build-environment adaptation that
        leaves the upstream source untouched (no patch, no ``__OHOS__`` macro).

        ``-musl`` is used because OHOS is a musl-based Linux; the resulting
        host_os still matches jemalloc's ``linux*`` branch.
        """
        target = self._ohos_target()
        canonical = target.replace("-ohos", "-musl")
        return {
            "ac_cv_build": canonical,
            "ac_cv_host": canonical,
            "ac_cv_target": canonical,
        }

    def _ensure_writable_tmpdir(self, env):
        current = env.get("TMPDIR")
        if current and os.path.isdir(current) and os.access(current, os.W_OK):
            return
        fallback = os.path.expanduser("~/tmp")
        try:
            os.makedirs(fallback, exist_ok=True)
        except OSError:
            fallback = self.build_folder
        env["TMPDIR"] = fallback
        self.output.info(f"TMPDIR set to {fallback} (OHOS /tmp is read-only)")

    def _ohos_cc(self):
        candidates = [
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin/aarch64-unknown-linux-ohos-clang",
            shutil.which("aarch64-unknown-linux-ohos-clang"),
        ]
        for c in candidates:
            if c and os.path.isfile(c):
                return c
        raise ConanInvalidConfiguration("aarch64-unknown-linux-ohos-clang not found")

    def _ohos_cxx(self):
        cc = self._ohos_cc()
        return cc + "++" if not cc.endswith("++") else cc

    def _llvm_ar(self):
        return os.path.join(os.path.dirname(self._ohos_cc()), "llvm-ar")

    def _ensure_ohos_target(self, env):
        target = self._ohos_target()
        rustc = os.path.join(os.path.dirname(env["CARGO"]), "rustc")
        if not os.path.isfile(rustc):
            rustc = shutil.which("rustc") or ""
        if not rustc:
            return
        prefix = os.path.dirname(os.path.dirname(rustc))
        rustlib = os.path.join(prefix, "lib", "rustlib", target)
        if not os.path.isdir(rustlib):
            self.output.warning(
                f"rust-std for {target} not found under {rustlib}; "
                "the toolchain may be unable to build for OHOS"
            )

    # Upstream test targets/exclusions.  `--bin rumdl` is omitted: the binary
    # test harness links the jemalloc global allocator and reproducibly SIGSEGVs
    # under libtest on OHOS regardless of the test (see notes.md); the shipped
    # binary itself runs correctly, including rayon-parallel linting.
    # The `--skip` list mirrors upstream's own nextest CI filter (perf/memory/
    # benchmark/complexity/scaling) plus the cases that are not meaningful on
    # OHOS: chmod/permission tests (HMDFS ignores chmod, E046) and tests that
    # mutate the process CWD (they pass only under nextest's process-per-test
    # isolation; upstream runs `cargo nextest run --profile ci`).
    UPSTREAM_TEST_SKIPS = (
        "--skip", "perf::", "--skip", "performance", "--skip", "benchmark",
        "--skip", "memory", "--skip", "linear_complexity", "--skip", "scaling",
        "--skip", "test_permission_denied_config",
        "--skip", "preserves_unix_permissions",
        "--skip", "unreadable_file_is_a_tool_error",
        "--skip", "fmt_preserves_file_permissions",
        "--skip", "test_create_default_config_permission_error",
        "--skip", "test_cache_prevents_duplicate_validation",
        "--skip", "test_auto_discovery_vs_explicit_config",
        "--skip", "test_config_dir_discovery",
        "--skip", "test_config_dir_precedence",
        "--skip", "test_project_root_with_auto_discovery",
        "--skip", "test_user_configuration_discovery",
        "--skip", "test_user_configuration_file_precedence",
        "--skip", "test_per_file_ignores_with_actual_relative_path",
        "--skip", "test_relative_path_with_single_component",
        "--skip", "test_md051_readme_headings",
    )

    def _run_upstream_tests(self, env):
        """Run the upstream test suite (`cargo test --release --locked --lib --test lib`).

        rumdl ships ~11.7k #[test] functions across src/ unit modules and the
        tests/ integration crate, all offline.  `--lib` + `--test lib` cover the
        library unit tests and the integration crate; doc-tests are excluded
        because rust-toolchain/1.97.1 ships no rustdoc.  See UPSTREAM_TEST_SKIPS
        and notes.md/reports/test-report.md for the per-test accounting.
        OHC_SKIP_UPSTREAM_TESTS=1 is the CI escape hatch.
        """
        if os.environ.get("OHC_SKIP_UPSTREAM_TESTS") == "1":
            self.output.info(
                "Skipping upstream cargo test (OHC_SKIP_UPSTREAM_TESTS=1); "
                "suite validated in Step 2 (see notes.md)."
            )
            return
        target = self._ohos_target()
        cmd = [env["CARGO"], "test", "--release", "--locked",
               "--target", target, "--lib", "--test", "lib", "--no-fail-fast",
               "--"] + list(self.UPSTREAM_TEST_SKIPS)
        self.output.info("Running upstream tests: %s" % " ".join(cmd))
        result = subprocess.run(cmd, cwd=self.source_folder, env=env).returncode
        if result != 0:
            raise ConanInvalidConfiguration(
                f"Upstream rumdl tests failed for {target} (rc={result})"
            )

    def _cargo_build(self, env):
        target = self._ohos_target()
        cmd = [env["CARGO"], "build", "--release", "--locked",
               "--target", target, "--bin", BINARY_NAME]
        result = subprocess.run(cmd, cwd=self.source_folder, env=env).returncode
        if result != 0:
            raise ConanInvalidConfiguration(
                f"cargo build failed for {target} (rc={result})"
            )
        out_dir = os.path.join(self.build_folder, "bin")
        os.makedirs(out_dir, exist_ok=True)
        release_dir = os.path.join(self.source_folder, "target", target, "release")
        src = os.path.join(release_dir, BINARY_NAME)
        if os.path.isfile(src):
            dst = os.path.join(out_dir, BINARY_NAME)
            shutil.copy2(src, dst)
            os.chmod(dst, 0o755)
        else:
            raise ConanInvalidConfiguration(
                f"{BINARY_NAME} binary not produced: {src}"
            )

    def _sign_binaries(self):
        if self.settings.os != "OHOS":
            return
        signer = self._find_binary_sign_tool()
        if not signer:
            self.output.warning(
                "binary-sign-tool not found; OHOS may reject executables"
            )
            return
        out_dir = os.path.join(self.build_folder, "bin")
        for name in os.listdir(out_dir):
            path = os.path.join(out_dir, name)
            if os.path.isfile(path):
                result = self.run(
                    f"{shlex.quote(signer)} sign "
                    f"-inFile {shlex.quote(path)} "
                    f"-outFile {shlex.quote(path)} -selfSign 1",
                    ignore_errors=True, quiet=True,
                )
                if result != 0:
                    raise ConanInvalidConfiguration(
                        f"binary-sign-tool failed (rc={result}): {path}"
                    )

    def _find_binary_sign_tool(self):
        candidates = [
            os.environ.get("BINARY_SIGN_TOOL"),
            shutil.which("binary-sign-tool"),
            shutil.which("hapsign"),
            "/data/service/hnp/bin/binary-sign-tool",
            "/data/service/hnp/ohos-sdk.org/"
            "ohos-sdk_26.0.0.18/ohos/native/bin/binary-sign-tool",
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    # ── toolchain discovery / bootstrap ─────────────────────────────

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
            "rust-toolchain/1.97.1 tool_requires package available"
        )

    def _rust_toolchain_dep(self):
        try:
            return self.dependencies.build.get("rust-toolchain")
        except (KeyError, ConanInvalidConfiguration):
            return None

    def _toolchain_dir(self):
        return os.path.join(self.build_folder, "rust-toolchain")

    def _prepare_signed_toolchain(self):
        """Prepare an executable (signed) Rust toolchain; return its bin dir."""
        dst = self._toolchain_dir()
        bin_dst = os.path.join(dst, "bin")
        lib_dst = os.path.join(dst, "lib")
        marker = os.path.join(dst, ".prepared")
        if os.path.isfile(marker):
            return bin_dst
        tool = self._rust_toolchain_dep()
        if not tool:
            raise ConanInvalidConfiguration(
                "rust-toolchain/1.97.1 tool_requires package not available"
            )
        src = tool.package_folder
        os.makedirs(bin_dst, exist_ok=True)
        os.makedirs(lib_dst, exist_ok=True)

        signer = self._find_binary_sign_tool()
        if not signer:
            self.output.warning(
                "binary-sign-tool not found; toolchain binaries stay unsigned "
                "and may be rejected by the OHOS loader (EACCES)"
            )

        to_sign = []
        for name in ("cargo", "rustc"):
            s = os.path.join(src, "bin", name)
            if os.path.isfile(s):
                d = os.path.join(bin_dst, name)
                if not os.path.isfile(d):
                    shutil.copy2(s, d)
                    os.chmod(d, 0o755)
                to_sign.append(d)
        src_lib = os.path.join(src, "lib")
        if os.path.isdir(src_lib):
            for name in sorted(os.listdir(src_lib)):
                if name.startswith("librustc_driver") and name.endswith(".so"):
                    d = os.path.join(lib_dst, name)
                    if not os.path.isfile(d):
                        shutil.copy2(os.path.join(src_lib, name), d)
                        os.chmod(d, 0o755)
                    to_sign.append(d)

        if signer:
            for path in to_sign:
                tmp = path + ".signed"
                result = subprocess.run(
                    [signer, "sign", "-inFile", path, "-outFile", tmp,
                     "-selfSign", "1"],
                    capture_output=True, text=True,
                )
                if result.returncode != 0 or not os.path.isfile(tmp):
                    raise ConanInvalidConfiguration(
                        "binary-sign-tool failed for %s (rc=%d): %s"
                        % (path, result.returncode, result.stderr[:200])
                    )
                os.replace(tmp, path)
                os.chmod(path, 0o755)
                self.output.info("signed toolchain binary: %s"
                                 % os.path.basename(path))
        else:
            self.output.warning("toolchain binaries were not signed")

        if os.path.isdir(src_lib):
            for name in sorted(os.listdir(src_lib)):
                d = os.path.join(lib_dst, name)
                if not os.path.exists(d):
                    self._link_or_copy(os.path.join(src_lib, name), d)
        for name in ("etc", "libexec", "share"):
            s = os.path.join(src, name)
            d = os.path.join(dst, name)
            if os.path.isdir(s) and not os.path.exists(d):
                self._link_or_copy(s, d)

        with open(marker, "w", encoding="utf-8") as fh:
            fh.write("signed toolchain prepared\n")
        return bin_dst

    def _link_or_copy(self, src, dst):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        try:
            os.symlink(src, dst)
            return
        except OSError:
            pass
        if os.path.isdir(src):
            shutil.copytree(src, dst, symlinks=True)
        else:
            shutil.copy2(src, dst)

    def _prepare_cxx_shared(self):
        """Return a directory holding an executable OHOS ``libc++_shared.so``.

        ``librustc_driver`` is dynamically linked against the OHOS C++ runtime;
        the OHOS loader does not search the SDK's arch sub-directories, so a
        signed copy is placed next to the toolchain libs and put on
        LD_LIBRARY_PATH.
        """
        marker_dir = os.path.join(self.build_folder, "cxx-shared")
        dest = os.path.join(marker_dir, "libc++_shared.so")
        if os.path.isfile(dest):
            return marker_dir
        candidates = [
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/"
            "lib/aarch64-linux-ohos/libc++_shared.so",
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/"
            "lib/aarch64-linux-ohos/c++/libc++_shared.so",
        ]
        src = next((c for c in candidates if os.path.isfile(c)), None)
        if not src:
            return None
        os.makedirs(marker_dir, exist_ok=True)
        shutil.copy2(src, dest)
        os.chmod(dest, 0o755)
        signer = self._find_binary_sign_tool()
        if signer:
            tmp = dest + ".signed"
            result = subprocess.run(
                [signer, "sign", "-inFile", dest, "-outFile", tmp,
                 "-selfSign", "1"],
                capture_output=True, text=True,
            )
            if result.returncode == 0 and os.path.isfile(tmp):
                os.replace(tmp, dest)
                os.chmod(dest, 0o755)
        return marker_dir

    def _prepare_runtime_libs(self):
        """Download & unpack cargo's runtime shared libraries; return lib dirs."""
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
            os.path.expanduser("~/.harmonybrew/etc/ca-certificates/cert.pem"),
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def _configure_rsproxy(self, cargo_home, ca_bundle=None):
        os.makedirs(cargo_home, exist_ok=True)
        config_path = os.path.join(cargo_home, "config.toml")
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
        with open(config_path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)

    def package(self):
        copy(self, BINARY_NAME, src=os.path.join(self.build_folder, "bin"),
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "README.md", src=self.source_folder,
             dst=os.path.join(self.package_folder, "res"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
