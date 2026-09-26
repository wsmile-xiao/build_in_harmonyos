#!/usr/bin/env python3
"""Conan recipe for leaf-md 1.26.1 (HarmonyOS / OpenHarmony PC, aarch64).

leaf (packaged here as ``leaf-md``) is a friendly terminal Markdown previewer
written in Rust.  Upstream: https://github.com/RivoLink/leaf

Adaptation notes
----------------
* Pure Rust/cargo build.  The only C code pulled in comes from the ``onig_sys``
  (oniguruma) and ``ring`` crates, which build their bundled C sources through
  ``cc-rs``.  Those must be pointed at the OHOS clang driver.
* The OHOS aarch64 target is the *native* host target on this platform, so the
  build does not need an explicit ``--target``: ``cargo build --release``
  already produces an ``aarch64-linux-ohos`` executable.  We only need to tell
  cargo which linker to use (the default ``cc`` does not exist in CI).
* The produced ELF is signed with ``binary-sign-tool`` so HarmonyOS executes it.
* The full upstream test suite is executed from ``build()`` so that every CI run
  re-validates it (see test_package/MANIFEST.yml for the declaration).

See notes.md for the adaptation log and reports/test-report.md for results.
"""

import os
import shlex
import shutil
import subprocess
import tarfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout

# OHOS SDK tool locations (same absolute paths used by the other Rust recipes
# in this repository, e.g. tlrc/cargo-nextest/add-determinism).
OHOS_CLANG = "/data/service/hnp/bin/aarch64-unknown-linux-ohos-clang"
OHOS_CLANGXX = "/data/service/hnp/bin/aarch64-unknown-linux-ohos-clang++"
OHOS_SIGN_TOOL = "/data/service/hnp/bin/binary-sign-tool"
OHOS_OBJCOPY = "/data/service/hnp/bin/llvm-objcopy"

BINARY_NAME = "leaf"

RUST_RUNTIME_BOTTLES = (
    (
        "openssl3",
        "https://harmonybrew.atomgit.com/bottles/"
        "openssl%403-3.6.4.arm64_ohos.bottle.tar.gz",
        "e1be73c6c68e29c33ff43761045e43e23e7c369f0fb1a24f40e226ec5cb28f98",
    ),
)


class LeafMdConan(ConanFile):
    name = "leaf-md"
    version = "1.26.1"
    description = "A friendly terminal Markdown previewer (Rust) — OHOS port"
    license = "MIT"
    homepage = "https://github.com/RivoLink/leaf"
    url = "https://github.com/RivoLink/leaf"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    # ---------------------------------------------------------------- sources
    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def build_requirements(self):
        # Use the published OHOS Rust toolchain package instead of downloading
        # mutable Harmonybrew bottles during the package build.
        self.tool_requires("rust-toolchain/1.97.1")

    def validate(self):
        # R32: accept both Linux and OHOS, never compare against "Linux" only.
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "leaf-md is only supported on OHOS/Linux, got "
                f"{self.settings.os}"
            )

    def source(self):
        # get() picks the extraction strategy from the file extension; pin the
        # filename so a mirror URL without an archive suffix still unpacks.
        get(
            self,
            **self.conan_data["sources"],
            filename=f"leaf-md-{self.version}.tar.gz",
            strip_root=True,
        )

    # ------------------------------------------------------------------ build
    def build(self):
        apply_conandata_patches(self)
        self._ensure_rust_toolchain()
        self._configure_cargo()
        self._cargo(["build", "--release", "--locked"])
        self._cargo_test()

    def _target_dir(self):
        """Keep cargo output inside the Conan build folder (not the source)."""
        return os.path.join(self.build_folder, "target")

    def _cargo(self, args, extra_env=""):
        """Run a cargo subcommand with the OHOS toolchain wired up.

        ``CC_aarch64-unknown-linux-ohos`` contains hyphens, so it cannot be
        written as a POSIX shell assignment prefix — it must go through `env`.
        """
        cargo = getattr(self, "_cargo_path", None) or self._find_tool("cargo")
        if not cargo:
            raise ConanException("cargo toolchain is required to build leaf-md")

        parts = [
            "env",
            "-u",
            "LD_LIBRARY_PATH",
            f"CARGO_TARGET_DIR={shlex.quote(self._target_dir())}",
        ]
        runtime_libs = getattr(self, "_cargo_runtime_libs", [])
        if runtime_libs:
            parts.append(
                "LD_LIBRARY_PATH="
                + shlex.quote(os.pathsep.join(runtime_libs))
            )
        rustc = getattr(self, "_rustc_path", None)
        if rustc:
            parts.append(f"RUSTC={shlex.quote(rustc)}")
        ca_bundle = getattr(self, "_cargo_ca_bundle", None)
        if ca_bundle:
            quoted_ca = shlex.quote(ca_bundle)
            parts.extend([
                f"CARGO_HTTP_CAINFO={quoted_ca}",
                f"SSL_CERT_FILE={quoted_ca}",
                f"CURL_CA_BUNDLE={quoted_ca}",
            ])
        if str(self.settings.os) == "OHOS" and os.path.exists(OHOS_CLANG):
            parts.extend(
                [
                    f"CC_aarch64-unknown-linux-ohos={shlex.quote(OHOS_CLANG)}",
                    f"CC_aarch64_unknown_linux_ohos={shlex.quote(OHOS_CLANG)}",
                    f"CC={shlex.quote(OHOS_CLANG)}",
                ]
            )
        if extra_env:
            parts.append(extra_env.strip())
        parts.append(shlex.quote(cargo))
        parts.extend(shlex.quote(str(arg)) for arg in args)
        self.run(" ".join(parts), cwd=self.source_folder)

    def _configure_cargo(self):
        """Write project-level .cargo/config.toml selecting the OHOS linker."""
        cargo_dir = os.path.join(self.source_folder, ".cargo")
        os.makedirs(cargo_dir, exist_ok=True)
        lines = [
            "[build]",
            f'target-dir = "{self._target_dir()}"',
            "",
            "[source.crates-io]",
            'replace-with = "rsproxy-sparse"',
            "",
            "[source.rsproxy-sparse]",
            'registry = "sparse+https://rsproxy.cn/index/"',
            "",
            "[net]",
            "git-fetch-with-cli = true",
            "",
        ]
        if str(self.settings.os) == "OHOS" and os.path.exists(OHOS_CLANG):
            lines += [
                "[target.aarch64-unknown-linux-ohos]",
                f'linker = "{OHOS_CLANG}"',
                "",
            ]
        with open(os.path.join(cargo_dir, "config.toml"), "w") as fh:
            fh.write("\n".join(lines))

    def _cargo_test(self):
        """Run the complete upstream test suite (348 tests, measured)."""
        args = ["test", "--release", "--locked", "--no-fail-fast"]
        self._cargo(args)

    @staticmethod
    def _find_tool(name):
        """Find an OHOS Rust tool, preferring a real bottle binary."""
        candidates = [
            shutil.which(name),
            f"/storage/Users/currentUser/.harmonybrew/bin/{name}",
            f"/storage/Users/currentUser/.cargo/bin/{name}",
            os.path.expanduser(f"~/.harmonybrew/bin/{name}"),
            os.path.expanduser(f"~/.cargo/bin/{name}"),
            f"/data/service/hnp/bin/{name}",
            f"/storage/Users/currentUser/usr/local/bin/{name}",
        ]
        for candidate in candidates:
            if not candidate:
                continue
            real = candidate + ".real"
            if os.path.isfile(real) and os.access(real, os.X_OK):
                candidate = real
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        return None

    def _find_binary_sign_tool(self):
        candidates = [
            os.environ.get("BINARY_SIGN_TOOL"),
            shutil.which("binary-sign-tool"),
            "/data/service/hnp/bin/binary-sign-tool",
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return None

    def _prepare_signed_toolchain(self, tool):
        """Prepare executable Rust tools in a private, signed build directory."""
        root = os.path.join(self.build_folder, "rust-toolchain")
        bin_dir = os.path.join(root, "bin")
        lib_dir = os.path.join(root, "lib")
        marker = os.path.join(root, ".prepared")
        if os.path.isfile(marker):
            return bin_dir, lib_dir

        source_bin = os.path.join(tool.package_folder, "bin")
        source_lib = os.path.join(tool.package_folder, "lib")
        os.makedirs(bin_dir, exist_ok=True)
        os.makedirs(lib_dir, exist_ok=True)
        signer = self._find_binary_sign_tool()
        paths = []
        for name in ("cargo", "rustc"):
            source = os.path.join(source_bin, name)
            destination = os.path.join(bin_dir, name)
            if not os.path.isfile(source):
                raise ConanInvalidConfiguration(
                    f"rust-toolchain/1.97.1 is missing bin/{name}"
                )
            if not os.path.isfile(destination):
                shutil.copy2(source, destination)
            os.chmod(destination, 0o755)
            paths.append(destination)

        if os.path.isdir(source_lib):
            for name in os.listdir(source_lib):
                source = os.path.join(source_lib, name)
                destination = os.path.join(lib_dir, name)
                if name.startswith("librustc_driver") and name.endswith(".so"):
                    if not os.path.isfile(destination):
                        shutil.copy2(source, destination)
                    os.chmod(destination, 0o755)
                    paths.append(destination)
                elif not os.path.exists(destination):
                    os.symlink(source, destination)

        for name in ("etc", "libexec", "share"):
            source = os.path.join(tool.package_folder, name)
            destination = os.path.join(root, name)
            if os.path.isdir(source) and not os.path.exists(destination):
                os.symlink(source, destination)

        if signer:
            for path in paths:
                signed = path + ".signed"
                result = subprocess.run(
                    [signer, "sign", "-inFile", path, "-outFile", signed,
                     "-selfSign", "1"],
                    capture_output=True, text=True,
                )
                if result.returncode != 0 or not os.path.isfile(signed):
                    raise ConanInvalidConfiguration(
                        f"binary-sign-tool failed for {path}: "
                        f"{result.stderr[:200]}"
                    )
                os.replace(signed, path)
                os.chmod(path, 0o755)
        else:
            self.output.warning(
                "binary-sign-tool not found; Rust tools may be rejected by OHOS"
            )

        with open(marker, "w", encoding="utf-8") as output:
            output.write("signed toolchain prepared\\n")
        return bin_dir, lib_dir

    @staticmethod
    def _find_ca_bundle():
        candidates = [
            os.environ.get("CARGO_HTTP_CAINFO"),
            os.environ.get("SSL_CERT_FILE"),
            os.environ.get("CURL_CA_BUNDLE"),
            "/etc/ssl/certs/cacert.pem",
            "/etc/ssl/cert.pem",
            "/storage/Users/currentUser/usr/local/ssl/cert.pem",
            os.path.expanduser("~/.harmonybrew/etc/ca-certificates/cert.pem"),
        ]
        return next((path for path in candidates if path and os.path.isfile(path)), None)

    def _prepare_runtime_libs(self):
        """Download the OHOS runtime libraries required by cargo."""
        from conan.tools.files import download

        base = os.path.join(self.build_folder, "rust-runtime")
        os.makedirs(base, exist_ok=True)
        lib_dirs = []
        for name, url, sha256 in RUST_RUNTIME_BOTTLES:
            archive = os.path.join(base, name + ".tar.gz")
            if not os.path.isfile(archive):
                download(self, url, archive, sha256=sha256)
            extract_dir = os.path.join(base, name)
            os.makedirs(extract_dir, exist_ok=True)
            with tarfile.open(archive, "r:gz") as source:
                source.extractall(extract_dir)
            for root, _dirs, files in os.walk(extract_dir):
                if os.path.basename(root) == "lib" and any(
                    item.startswith(("libssl.", "libcrypto.", "libz."))
                    for item in files
                ):
                    lib_dirs.append(root)
        return lib_dirs

    def _ensure_rust_toolchain(self):
        """Use the published Conan OHOS Rust toolchain or a system toolchain."""
        dependencies = getattr(self, "dependencies", None)
        tool = dependencies.build.get("rust-toolchain") if dependencies else None
        if tool:
            bin_dir, lib_dir = self._prepare_signed_toolchain(tool)
            self._cargo_path = os.path.join(bin_dir, "cargo")
            self._rustc_path = os.path.join(bin_dir, "rustc")
            self._cargo_runtime_libs = [lib_dir] + self._prepare_runtime_libs()
            self._cargo_ca_bundle = self._find_ca_bundle()
            if self._cargo_ca_bundle:
                os.environ["SSL_CERT_FILE"] = self._cargo_ca_bundle
                os.environ["CURL_CA_BUNDLE"] = self._cargo_ca_bundle
            os.environ["PATH"] = bin_dir + ":" + os.environ.get("PATH", "")
            return

        cargo = self._find_tool("cargo")
        rustc = self._find_tool("rustc")
        if cargo and rustc:
            self._cargo_path = cargo
            self._rustc_path = rustc
            os.environ["PATH"] = os.path.dirname(cargo) + ":" + os.environ.get("PATH", "")
            return
        raise ConanInvalidConfiguration(
            "Rust toolchain unavailable: install rust-toolchain/1.97.1 "
            "or provide cargo/rustc"
        )

    # ---------------------------------------------------------------- package
    def package(self):
        release_dir = os.path.join(self._target_dir(), "release")
        binary = os.path.join(release_dir, BINARY_NAME)
        if not os.path.isfile(binary):
            raise ConanException(f"leaf binary not found at {binary}")

        copy(
            self,
            BINARY_NAME,
            release_dir,
            os.path.join(self.package_folder, "bin"),
        )
        copy(
            self,
            "LICENSE*",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        copy(
            self,
            "README.md",
            self.source_folder,
            os.path.join(self.package_folder, "res"),
            keep_path=False,
        )
        self._sign_elf(os.path.join(self.package_folder, "bin", BINARY_NAME))

    def _sign_elf(self, path):
        """Sign the ELF so HarmonyOS lets it execute."""
        if str(self.settings.os) != "OHOS":
            return
        if not os.path.exists(OHOS_SIGN_TOOL):
            self.output.warning(
                "binary-sign-tool not found, skipping ELF signing"
            )
            return
        objcopy = OHOS_OBJCOPY if os.path.exists(OHOS_OBJCOPY) else "llvm-objcopy"
        self.run(f"{objcopy} --remove-section .codesign {path} || true")
        self.run(
            f"{OHOS_SIGN_TOOL} sign -inFile {path} -outFile {path}.signed "
            "-selfSign 1"
        )
        shutil.move(f"{path}.signed", path)
        os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
