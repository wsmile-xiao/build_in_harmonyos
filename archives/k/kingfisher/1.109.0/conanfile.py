#!/usr/bin/env python3
"""Conan 2.x recipe — kingfisher 1.109.0 (MongoDB secret scanning CLI, Rust/cargo).

Upstream: https://github.com/mongodb/kingfisher (Apache-2.0)
Build system: cargo (Rust 2024 edition, rust-version 1.96)

OHOS notes (all verified on this device unless marked otherwise):
  * R47 language preflight: the repository is Rust/cargo; adapting under the
    truthful `--lang rust` task language (same precedent as
    archives/c/crunch64/0.6.2 and archives/c/cargo-bash-completions/1.97.0).
  * Toolchain: cargo/rustc come from Harmonybrew (`~/.harmonybrew/bin`).
    The OHOS worker ships no Rust toolchain (hint_rules.json:toolchain_rust).
  * migmaalloc `override`: upstream enables the mimalloc `override` feature,
    which sets MI_MALLOC_OVERRIDE and replaces the system malloc/free. On
    HarmonyOS that conflicts with the platform allocator and the process dies
    with SIGSEGV (exit 139) before main() — knowledge entry E210. Patch
    0001 drops the feature (mimalloc stays a normal allocator). Verified:
    exit 139 -> exit 0.
  * vendored Vectorscan (crates.io `vectorscan-rs` 0.0.6, `vendor/vectorscan-rs`)
    builds real C++ via CMake and needs Boost >= 1.61 headers plus the OHOS SDK
    CMake toolchain; otherwise the link fails on undefined
    aws_lc_*_bignum_* / ChaCha20_ctr32_neon symbols.
  * aws-lc-sys (pulled by rustls/aws-lc-rs) must be configured through the OHOS
    SDK toolchain, otherwise it derives ARCH=generic and silently drops every
    s2n-bignum .S assembly file, leaving undefined aws_lc_0_41_0_bignum_* and
    ChaCha20/AES symbols at link time (same class as martin/1.13.0 and
    hf-mount/0.9.0).
  * OHOS ELF binaries must be signed with binary-sign-tool, otherwise execution
    is refused ("Operation not permitted").
  * R51 upstream tests: run in build(); three environment-dependent cases are
    declared exempt in test_package/MANIFEST.yml with concrete technical reasons.
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration, ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class KingfisherConan(ConanFile):
    name = "kingfisher"
    version = "1.109.0"
    description = ("MongoDB's blazingly fast and accurate secret scanning and "
                   "validation tool")
    license = "Apache-2.0"
    homepage = "https://github.com/mongodb/kingfisher"
    url = "https://cnb.cool/ohpcd/ohos-pc-archives/-/tree/main/archives/k/kingfisher/1.109.0"
    topics = ("secrets", "scanner", "security", "cli", "rust")

    # R38: the build produces the `kingfisher` executable -> commands.json is
    # declared at the software level (archives/k/kingfisher/commands.json).
    package_type = "application"

    # L0p / PF8: the OHOS profile requires all four settings.
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: platform checks must accept OHOS as well as Linux.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")
        if str(self.settings.arch) not in ("armv8", "aarch64"):
            raise ConanInvalidConfiguration(
                f"arch={self.settings.arch} not supported (OHOS aarch64 only)")

    def build_requirements(self):
        """Declare the Boost headers the vendored Vectorscan engine needs.

        CI evidence (PR #14239): the worker has no Boost headers, and
        `brew install boost` cannot run there (`brew` fails with
        `Error loading shared library libncursesw.so.6`, Conan Error 127).
        boost/1.85.0 is a published artifact whose package_id for this profile
        (32b74e3e19b062f993e717bc9d8150ae65c2c340) was verified to carry the
        FULL header tree — including boost/icl/interval_set.hpp and
        boost/multi_array.hpp, which the vendored Vectorscan engine includes.
        (boost/1.91.0.1.3 is trimmed: it has boost/regex.hpp but NOT
        icl/multi_array, which made the Vectorscan build fail.)  Like the
        other candidates it has NO bin/ directory, so it cannot shadow PATH.
        """
        self.tool_requires("boost/1.85.0")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── toolchain / environment ────────────────────────────────────────────
    def _ensure_rust_toolchain(self):
        """Return a cargo path, installing Harmonybrew Rust when absent."""
        if shutil.which("cargo"):
            return "cargo"
        brew_bin = os.path.expanduser("~/.harmonybrew/bin")
        if os.path.isfile(os.path.join(brew_bin, "cargo")):
            os.environ["PATH"] = brew_bin + os.pathsep + os.environ.get("PATH", "")
            return "cargo"
        if not os.path.isfile(os.path.join(brew_bin, "brew")):
            # Harmonybrew has to bootstrap itself first (dua-cli precedent).
            self.run(
                'zsh -c "$(curl -fsSL https://harmonybrew.atomgit.com/install.sh)"',
                env="conanbuild",
            )
        self.run(f"{os.path.join(brew_bin, 'brew')} install rust", env="conanbuild")
        os.environ["PATH"] = brew_bin + os.pathsep + os.environ.get("PATH", "")
        if not shutil.which("cargo"):
            raise ConanInvalidConfiguration("cargo is required to build kingfisher")
        return "cargo"

    def _prepare_cc_linker(self):
        """cargo/CMake look up `cc`/`c++`, but OHOS only ships clang/clang++."""
        clang = shutil.which("clang") or "/data/service/hnp/bin/clang"
        clangxx = shutil.which("clang++") or "/data/service/hnp/bin/clang++"
        shim = os.path.join(self.build_folder, "cc-shim")
        os.makedirs(shim, exist_ok=True)
        for name, target in (("cc", clang), ("c++", clangxx)):
            link = os.path.join(shim, name)
            # R5: SELinux rejects ln -sf; remove then create, and verify.
            if os.path.lexists(link):
                os.remove(link)
            os.symlink(target, link)
            if not os.path.lexists(link):
                raise ConanException(f"failed to create linker shim {link}")
        os.environ["PATH"] = shim + os.pathsep + os.environ.get("PATH", "")
        os.environ["CC"] = clang
        os.environ["CXX"] = clangxx
        os.environ.setdefault("CFLAGS", "-fPIC -O2")
        os.environ.setdefault("CXXFLAGS", "-fPIC -O2")
        # cargo does not honour CC for linking; pass it to rustc explicitly.
        os.environ["RUSTFLAGS"] = f"-C linker={clang}"
        return clang

    def _prepare_boost(self):
        """Vectorscan (vendored C++) needs Boost >= 1.61 headers.

        Preferred source is the declared `boost` dependency (published artifact,
        no PATH shadowing). Harmonybrew is only a fallback for local workers
        that already have it; installing it via brew is NOT attempted because
        `brew` itself fails on the CI worker (libncursesw.so.6).
        """
        def _usable(cand):
            return bool(cand) and os.path.isfile(
                os.path.join(cand, "include", "boost", "version.hpp"))

        candidates = []
        try:
            candidates.append(self.dependencies.build["boost"].package_folder)
        except (KeyError, ConanException):
            pass
        candidates += [
            os.path.expanduser("~/.harmonybrew"),
            os.path.expanduser("~/.harmonybrew/opt/boost"),
        ]
        for cand in candidates:
            if _usable(cand):
                os.environ["BOOST_ROOT"] = cand
                inc = os.path.join(cand, "include")
                for var in ("CPATH", "CPLUS_INCLUDE_PATH"):
                    prev = os.environ.get(var, "")
                    os.environ[var] = inc + (os.pathsep + prev if prev else "")
                # CI evidence (build #66511): registry Boost <= 1.91 predates the
                # `!defined(__OHOS__)` guard that current upstream has, so
                # boost/core/detail/sp_thread_sleep.hpp calls
                # pthread_setcancelstate(), which OHOS bionic does not provide:
                #   error: use of undeclared identifier 'pthread_setcancelstate'
                # The vendored Vectorscan engine compiles via its own CMake
                # invocation that does NOT inherit CFLAGS/CXXFLAGS, so a header
                # overlay placed FIRST on the include path is used instead of
                # relying on -D flags (CPATH/CPLUS_INCLUDE_PATH are honoured by
                # the compiler driver and take precedence over -isystem).
                overlay = self._write_boost_ohos_overlay(inc)
                if overlay:
                    for var in ("CPATH", "CPLUS_INCLUDE_PATH"):
                        prev = os.environ.get(var, "")
                        os.environ[var] = overlay + (os.pathsep + prev if prev else "")
                # Boost's official opt-out, for consumers that do read the flags.
                flag = "-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE"
                for var in ("CFLAGS", "CXXFLAGS", "CPPFLAGS"):
                    prev = os.environ.get(var, "")
                    if flag not in prev:
                        os.environ[var] = (prev + " " if prev else "") + flag
                return
        raise ConanInvalidConfiguration(
            "Boost >= 1.61 headers are required by the vendored Vectorscan "
            "engine; expected include/boost/version.hpp plus icl/multi_array "
            "from the declared boost/1.85.0 dependency")

    def _write_boost_ohos_overlay(self, boost_include):
        """Patch Boost's OHOS-incompatible pthread_setcancelstate guard.

        Registry Boost <= 1.91 lacks the `!defined(__OHOS__)` guard present in
        current upstream, so `boost/core/detail/sp_thread_sleep.hpp` calls
        pthread_setcancelstate(), which bionic does not provide.  Vendored
        Vectorscan builds through its own CMake invocation that does not take
        CFLAGS/CXXFLAGS, so the fix is a one-header overlay returned for
        placement FIRST on the include path (verified locally: with the Conan
        headers alone the error reproduces; with this overlay on CPATH the same
        translation unit compiles).

        Returns the overlay root, or None when the header is absent / already
        guarded / unexpected so the caller never breaks a working build.
        """
        rel = os.path.join("boost", "core", "detail", "sp_thread_sleep.hpp")
        src = os.path.join(boost_include, rel)
        if not os.path.isfile(src):
            return None
        try:
            with open(src, encoding="utf-8") as handle:
                original = handle.read()
        except OSError:
            return None

        old = "#if defined(BOOST_HAS_PTHREADS) && !defined(__ANDROID__) && !defined(BOOST_SP_NO_PTHREAD_SETCANCELSTATE)"
        new = "#if defined(BOOST_HAS_PTHREADS) && !defined(__ANDROID__) && !defined(__OHOS__) && !defined(BOOST_SP_NO_PTHREAD_SETCANCELSTATE)"
        if new in original or old not in original:
            return None  # already OHOS-aware, or shape changed: leave untouched

        overlay = os.path.join(self.build_folder, "boost-ohos-overlay")
        dst = os.path.join(overlay, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "w", encoding="utf-8") as handle:
            handle.write(original.replace(old, new))
        self.output.info("Boost headers need an OHOS guard patch; using a "
                         "local overlay for sp_thread_sleep.hpp")
        return overlay

    def _prepare_ohos_sdk(self):
        """Locate the OHOS SDK and expose it to aws-lc-sys' CMake builder."""
        if os.environ.get("OHOS_SDK_NATIVE"):
            return os.environ["OHOS_SDK_NATIVE"]
        for sdk in (
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native",
            "/data/service/hnp/ohos-sdk.org/ohos-sdk/ohos/native",
        ):
            if os.path.isfile(os.path.join(sdk, "build/cmake/ohos.toolchain.cmake")):
                os.environ["OHOS_SDK_NATIVE"] = sdk
                return sdk
        raise ConanInvalidConfiguration(
            "OHOS SDK native toolchain is required for aws-lc-sys (set OHOS_SDK_NATIVE)")

    def _prepare_aws_lc_toolchain(self, sdk, ar):
        """Build the CMake toolchain overlay aws-lc-sys needs on OHOS.

        The SDK toolchain assigns CMAKE_SYSTEM_PROCESSOR as a plain variable and
        writes `set(UNIX TRUE CACHE BOOL FROCE)` (typo: FROCE, not FORCE), so
        CMake ends up without a system processor; aws-lc then derives
        ARCH=generic and skips all s2n-bignum assembly, which surfaces as
        undefined aws_lc_0_41_0_bignum_* / ChaCha20 / AES symbols at link time.
        Pinning the processor into the cache restores ARCH=aarch64.
        """
        fix_dir = os.path.join(self.build_folder, "ohos-toolchain-fix")
        os.makedirs(fix_dir, exist_ok=True)

        # The SDK ships llvm-ar but no llvm-ranlib; provide a wrapper.
        ranlib = os.path.join(fix_dir, "llvm-ranlib")
        with open(ranlib, "w", encoding="utf-8") as handle:
            handle.write(f'#!/bin/sh\nexec "{ar}" s "$@"\n')
        os.chmod(ranlib, 0o755)

        overlay = os.path.join(fix_dir, "aws-lc-ohos-toolchain.cmake")
        with open(overlay, "w", encoding="utf-8") as handle:
            handle.write(
                f'include("{os.path.join(sdk, "build/cmake/ohos.toolchain.cmake")}")\n'
                'set(CMAKE_SYSTEM_PROCESSOR "aarch64" CACHE STRING "OHOS target" FORCE)\n'
                'set(UNIX TRUE CACHE BOOL "OHOS is unix-like" FORCE)\n'
                f'set(CMAKE_RANLIB "{ranlib}" CACHE FILEPATH "" FORCE)\n'
                f'set(CMAKE_C_COMPILER_RANLIB "{ranlib}" CACHE FILEPATH "" FORCE)\n'
                f'set(CMAKE_ASM_COMPILER_RANLIB "{ranlib}" CACHE FILEPATH "" FORCE)\n'
            )
        os.environ["AWS_LC_SYS_CMAKE_TOOLCHAIN_FILE_aarch64_unknown_linux_ohos"] = overlay
        os.environ["AWS_LC_SYS_CMAKE_TOOLCHAIN_FILE"] = overlay
        os.environ["AR_aarch64_unknown_linux_ohos"] = ar
        os.environ["RANLIB_aarch64_unknown_linux_ohos"] = ranlib

    def _prepare_runtime_libs(self):
        """cargo/rustc link libssl/libcrypto/libz from the Harmonybrew prefix,
        whose DT_RUNPATH the OHOS musl loader ignores (aki en/agent-browser
        precedent). Put those directories on LD_LIBRARY_PATH up front."""
        libs = []
        for cand in (
            os.path.expanduser("~/.harmonybrew/opt/openssl@3/lib"),
            os.path.expanduser("~/.harmonybrew/lib"),
        ):
            if os.path.isdir(cand):
                libs.append(cand)
        if libs:
            prev = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
                libs + ([prev] if prev else []))

    def generate(self):
        # A writable TMPDIR is required: OHOS /tmp is read-only (E002/R10).
        tmp = os.environ.get("TMPDIR")
        if not tmp or not os.path.isdir(tmp):
            tmp = os.path.join(os.path.expanduser("~"), "tmp", "kingfisher")
            os.makedirs(tmp, exist_ok=True)
            os.environ["TMPDIR"] = tmp
        # Supply a CA bundle when the worker has none, so cargo's TLS works.
        if not os.environ.get("SSL_CERT_FILE"):
            for ca in (
                os.path.join(os.path.expanduser("~"), "usr/local/ssl/cert.pem"),
                "/etc/ssl/certs/cacert.pem",
                os.path.expanduser("~/.harmonybrew/etc/ca-certificates/cert.pem"),
            ):
                if os.path.isfile(ca):
                    os.environ["SSL_CERT_FILE"] = ca
                    os.environ["CURL_CA_BUNDLE"] = ca
                    break

    def _write_cargo_config(self):
        """Pin a registry mirror.

        Direct access to index.crates.io is too slow on this worker (cargo
        aborts with `spurious network error: transfer too slow`). A project
        level .cargo/config.toml replaces crates.io with the rsproxy sparse
        mirror; the CA bundle is set explicitly because the worker cargo has
        no default trust store.
        """
        cargo_dir = os.path.join(self.source_folder, ".cargo")
        os.makedirs(cargo_dir, exist_ok=True)
        ca = os.environ.get("SSL_CERT_FILE", "")
        lines = [
            "[source.crates-io]",
            'replace-with = "rsproxy-sparse"',
            "",
            "[source.rsproxy-sparse]",
            'registry = "sparse+https://rsproxy.cn/index/"',
            "",
            "[net]",
            "git-fetch-with-cli = true",
            "retry = 5",
        ]
        if ca:
            lines += ["", "[http]", f'cainfo = "{ca}"', "check-revoke = false"]
        with open(os.path.join(cargo_dir, "config.toml"), "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")

    def _write_git_test_config(self):
        """Isolate HOME for the upstream Git tests so libgit2 accepts the repos.

        libgit2 refuses to open a repository whose owner differs from the
        current uid, and the worker's temp directories are group-owned
        (uid 20001006 / gid 1006): the Git tests then fail with
        `repository path '…' is not owned by current user; code=Owner (-36)`.

        libgit2 reads the global git config from $HOME/.gitconfig and does NOT
        honour GIT_CONFIG_GLOBAL (verified on this device: setting it alone
        leaves the failure in place). So HOME is redirected to a scratch dir
        holding `safe.directory = *`, while CARGO_HOME is pinned to the real
        cargo home so the registry cache and toolchain are still reused.
        """
        real_home = os.path.expanduser("~")
        fake_home = os.path.join(self.build_folder, "test-home")
        os.makedirs(fake_home, exist_ok=True)
        with open(os.path.join(fake_home, ".gitconfig"), "w", encoding="utf-8") as handle:
            handle.write("[safe]\n\tdirectory = *\n")
        os.environ["HOME"] = fake_home
        os.environ.setdefault("CARGO_HOME", os.path.join(real_home, ".cargo"))
        return fake_home

    def build(self):
        apply_conandata_patches(self)

        cargo = self._ensure_rust_toolchain()
        clang = self._prepare_cc_linker()
        ar = shutil.which("llvm-ar") or "/data/service/hnp/bin/llvm-ar"
        sdk = self._prepare_ohos_sdk()
        self._prepare_aws_lc_toolchain(sdk, ar)
        self._prepare_runtime_libs()
        self._prepare_boost()
        self._write_cargo_config()
        self._write_git_test_config()

        # Cargo must run inside the source tree (it searches upwards for
        # Cargo.toml) with an explicit target dir so artefacts land predictably.
        target_dir = os.path.join(self.build_folder, "target")
        # R49 spirit: build-scoped private paths only.  The shared
        # $HOME/.cache/tmp is owned by the CI harness and can be removed by a
        # concurrent task, which is exactly how rustc died on CI build #74999
        # (release binary had already built in 21m31s):
        #   error: couldn't create a temp dir: No such file or directory
        #     (os error 2) at .../target/release/deps/rustc2wTSif
        #   error: could not compile `kingfisher` (test "int_jwt_provider")
        private_tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(private_tmp, exist_ok=True)
        # Defensive: ensure the target tree exists before cargo writes into it.
        os.makedirs(os.path.join(target_dir, "release", "deps"), exist_ok=True)
        env_prefix = (
            f'CARGO_TARGET_DIR="{target_dir}" '
            f'CARGO_NET_GIT_FETCH_WITH_CLI=true '
            f'TMPDIR="{private_tmp}" '
        )
        self.run(f"{env_prefix}{cargo} build --release --locked", cwd=self.source_folder)

        # ── R51 upstream test suite (three-step method) ────────────────────
        # CI builds #74999 / #81716 both died while *compiling* the 44
        # integration-test binaries (elapsedTime≈2830s, exit -1, no message at
        # all) — the classic SIGKILL/OOM signature: rustc is killed before it
        # can print anything.  Each test binary links the whole aws-sdk /
        # mongodb dependency tree, so default parallelism (one rustc per CPU)
        # has a very high peak RSS.  CARGO_BUILD_JOBS bounds it; the release
        # `cargo build` phase above already succeeds at default parallelism, so
        # only the test phase is constrained.
        test_env = env_prefix + "CARGO_BUILD_JOBS=2 "
        # Fourth environment-dependent case, surfaced once the suite actually
        # ran (CI build #82118: elapsedTime=8514s, 19 `test result` lines,
        # 49 passed / 0 failed, failing only on this target):
        #   * int_s3::test_visit_public_bucket — calls
        #     `visit_bucket_objects("awsglue-datasets", …)` against the public
        #     AWS S3 endpoint and asserts an object body, so it needs outbound
        #     HTTPS to AWS.  Same class as the two network cases above; its
        #     source is left untouched and only the test name is skipped here.
        self.run(
            f"{test_env}{cargo} test --release --no-fail-fast -- "
            f"--skip test_github_remote_scan "
            f"--skip test_update_clone "
            f"--skip library_crates_work_from_external_project "
            f"--skip test_visit_public_bucket",
            cwd=self.source_folder,
        )

        self.output.info(f"kingfisher built with linker {clang}")

    def _sign_elf(self, path):
        """OHOS refuses to execute unsigned ELF binaries."""
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.exists(sign_tool):
            self.output.warning("binary-sign-tool not found; skipping ELF signing")
            return
        self.run(f"{objcopy} --remove-section .codesign {path} || true")
        self.run(f"{sign_tool} sign -inFile {path} -outFile {path}.signed -selfSign 1")
        shutil.move(f"{path}.signed", path)
        os.chmod(path, 0o755)

    def package(self):
        binary = os.path.join(self.build_folder, "target", "release", "kingfisher")
        if not os.path.isfile(binary):
            raise ConanException(f"kingfisher binary not found at {binary}")
        copy(self, "kingfisher", os.path.dirname(binary),
             os.path.join(self.package_folder, "bin"))
        installed = os.path.join(self.package_folder, "bin", "kingfisher")
        if str(self.settings.os) == "OHOS":
            self._sign_elf(installed)
        for doc in ("LICENSE", "NOTICE", "THIRD_PARTY_NOTICES"):
            copy(self, doc, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
