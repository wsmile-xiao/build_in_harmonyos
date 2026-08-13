#!/usr/bin/env python3
"""Conan 2.x recipe — aiken 1.1.23

A modern smart contract platform for Cardano (Rust).
Source: https://github.com/aiken-lang/aiken (tag v1.1.23)
Build system: cargo (Rust workspace, crates/aiken)
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AikenConan(ConanFile):
    name = "aiken"
    version = "1.1.23"
    description = "A modern smart contract platform for Cardano"
    license = "Apache-2.0"
    homepage = "https://aiken-lang.org"
    url = "https://github.com/aiken-lang/aiken"

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        # R32: settings.os check must use in ("Linux", "OHOS")
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"aiken supports Linux and OHOS only, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Ensure Rust toolchain is available (CI workers may not have it pre-installed)
        if not shutil.which("cargo"):
            self._ensure_rust_toolchain()
        # aiken depends on openssl-sys; point pkg-config at the bundled OpenSSL
        brew_prefix = os.path.expanduser("~/.harmonybrew")
        pkgconfig_paths = [
            os.path.join(brew_prefix, "lib", "pkgconfig"),
            os.path.join(brew_prefix, "Cellar", "openssl@3"),
        ]
        if os.path.isdir(os.path.join(brew_prefix, "Cellar", "openssl@3")):
            ssl_dirs = sorted(os.listdir(os.path.join(brew_prefix, "Cellar", "openssl@3")))
            if ssl_dirs:
                pkgconfig_paths.append(
                    os.path.join(brew_prefix, "Cellar", "openssl@3", ssl_dirs[-1], "lib", "pkgconfig")
                )
        env = {
            "PKG_CONFIG_PATH": ":".join(p for p in pkgconfig_paths if os.path.isdir(os.path.dirname(p)))
        }
        with open(os.path.join(self.source_folder, ".cargo-env.sh"), "w") as f:
            for k, v in env.items():
                f.write(f"export {k}={v}\n")

        # CI workers only ship `clang` (no `cc`/`gcc` symlinks in PATH), while
        # rustc's default linker is `cc`. Point cargo at clang explicitly so
        # build scripts and the final binary can be linked on any worker.
        cargo_dir = os.path.join(self.build_folder, ".cargo")
        os.makedirs(cargo_dir, exist_ok=True)
        with open(os.path.join(cargo_dir, "config.toml"), "w") as f:
            # CI workers route to static.crates.io are rate-limited (transfer
            # too slow: 0 bytes in 30s → cargo build fails on dependency fetch).
            # Substitute the default crates.io source with the rsproxy mirror
            # (reachable from HarmonyOS CI workers) so dependency resolution
            # does not stall on the upstream CDN.
            f.write(
                '[source.crates-io]\n'
                'replace-with = "rsproxy-sparse"\n'
                '\n'
                '[source.rsproxy-sparse]\n'
                'registry = "sparse+https://rsproxy.cn/index/"\n'
                '\n'
                '[build]\n'
                'target-dir = "target"\n'
            )
            if str(self.settings.os) == "OHOS":
                f.write(
                    '\n[target.aarch64-unknown-linux-ohos]\n'
                    'linker = "clang"\n'
                )

    def build(self):
        apply_conandata_patches(self)

        # Conan sandbox strips PATH; harmonybrew bin (cargo/rustc/patch) must
        # be re-injected into the process environment so self.run can find them.
        brew_bin = os.path.expanduser("~/.harmonybrew/bin")
        if os.path.isdir(brew_bin):
            os.environ["PATH"] = brew_bin + ":" + os.environ.get("PATH", "")

        # Set writable TMPDIR on OHOS (/tmp is read-only)
        if str(self.settings.os) == "OHOS":
            tmpdir = os.path.expanduser("~/tmp/aiken")
            os.makedirs(tmpdir, exist_ok=True)
            os.environ["TMPDIR"] = tmpdir

        # harmonybrew cargo is dynamically linked against libssl.so/libcrypto.so
        # (OpenSSL 3.x symbols). The CI loader may pick up an older system
        # /usr/lib/libssl.so.3 lacking those symbols → "Error relocating
        # cargo.real: OBJ_nid2sn: symbol not found". Force the loader to prefer
        # harmonybrew's OpenSSL 3.6.3 via LD_LIBRARY_PATH.
        brew_lib = os.path.expanduser("~/.harmonybrew/opt/openssl@3/lib")
        if os.path.isdir(brew_lib):
            existing = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = brew_lib + (":" + existing if existing else "")
            os.environ["DYLD_LIBRARY_PATH"] = os.environ["LD_LIBRARY_PATH"]

        # Ensure Rust toolchain is available (CI workers may not have it pre-installed)
        if not shutil.which("cargo"):
            self._ensure_rust_toolchain()

        # Ensure GNU patch (harmonybrew) is used: toybox patch has no fuzz
        # tolerance, so libquickjs-sys bundled patches fail to apply.
        self._ensure_gnu_patch()

        # CI workers lack `cc`/`gcc`; expose clang under those names so rustc
        # (default linker `cc`) and C build scripts invoking `cc` directly work.
        self._ensure_cc_linker()

        # Load OpenSSL pkg-config paths generated in generate()
        env_file = os.path.join(self.source_folder, ".cargo-env.sh")
        if os.path.isfile(env_file):
            with open(env_file) as f:
                for line in f:
                    if line.startswith("export "):
                        k, v = line[len("export "):].strip().split("=", 1)
                        os.environ[k] = v

        # Build release binary (crates/aiken is the CLI crate)
        self.run("cargo build --release -p aiken", env="conanbuild")

        # Run upstream unit/integration tests natively: host==target on the
        # OHOS worker (no qemu/device needed), so the pass rate is real and
        # CI-verifiable. harmonybrew rust 1.97.1 ships no rustdoc, so doctests
        # are skipped via --tests (aiken_lang has doctests).
        self.run("cargo test --release --workspace --tests", env="conanbuild")

    def package(self):
        # Locate the built binary robustly: cargo puts it under
        # <build>/target/release/aiken, but the exact build folder path
        # depends on conan layout resolution.
        import glob

        found = []
        for root in (self.build_folder, self.source_folder):
            found.extend(
                glob.glob(os.path.join(root, "**", "target", "release", "aiken"), recursive=True)
            )
        assert found, "aiken binary not found under build/source folders"
        src_dir = os.path.dirname(found[0])
        copy(self, "aiken", src_dir, os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "README.md", self.source_folder, os.path.join(self.package_folder, "res"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []

    def _ensure_gnu_patch(self):
        """Ensure GNU patch is in PATH for the cargo build.

        libquickjs-sys 0.9.0's bundled quickjs patches (e.g.
        stack-overflow-signed.patch) have hunks whose context is offset from
        the vendored quickjs source; only GNU patch's fuzz tolerance can apply
        them ("Hunk #1 succeeded at 1587 with fuzz 2 (offset -145)"). toybox
        patch silently skips or fails hard ("Hunk 1 FAILED"), breaking the
        build. CI workers may lack harmonybrew's gpatch, so install it via
        brew when missing, then prepend harmonybrew bin to PATH.
        """
        brew_bin = os.path.expanduser("~/.harmonybrew/bin")
        patch_bin = os.path.join(brew_bin, "patch")
        if not (os.path.isfile(patch_bin) and os.access(patch_bin, os.X_OK)):
            brew = os.path.join(brew_bin, "brew")
            if os.path.isfile(brew):
                self.run(f"{brew} install gpatch", env="conanbuild")
        if os.path.isfile(patch_bin) and os.access(patch_bin, os.X_OK):
            os.environ["PATH"] = brew_bin + ":" + os.environ.get("PATH", "")
            return True
        self.output.warning(
            "GNU patch unavailable; libquickjs-sys bundled patches may fail to apply"
        )
        return False

    def _ensure_cc_linker(self):
        """Expose the active C compiler as `cc`/`gcc` for this build.

        OHOS CI workers only provide `clang` in PATH (no `cc`/`gcc` symlinks).
        rustc links with `cc` by default and some C build scripts invoke `cc`
        directly, so symlink the configured C compiler under those names into
        a writable dir prepended to PATH.
        """
        cc = None
        conf = self.conf.get("tools.build:compiler_executables", default={})
        if isinstance(conf, dict):
            cc = conf.get("c")
        if not cc:
            cc = os.environ.get("CC") or shutil.which("clang") or shutil.which("cc")
        if not cc or os.path.basename(cc) in ("cc", "gcc"):
            return
        bindir = os.path.join(self.build_folder, ".ccbin")
        os.makedirs(bindir, exist_ok=True)
        for name in ("cc", "gcc"):
            link = os.path.join(bindir, name)
            if not os.path.lexists(link):
                os.symlink(cc, link)
        os.environ["PATH"] = bindir + os.pathsep + os.environ.get("PATH", "")

    def _ensure_rust_toolchain(self):
        """Install Rust toolchain via Harmonybrew if cargo is not in PATH."""
        brew_bin = os.path.expanduser("~/.harmonybrew/bin")

        # Check if Harmonybrew Rust is already installed
        if os.path.isfile(os.path.join(brew_bin, "cargo")):
            os.environ["PATH"] = brew_bin + ":" + os.environ.get("PATH", "")
            return

        # Install Harmonybrew if not present
        if not os.path.isfile(os.path.expanduser("~/.harmonybrew/bin/brew")):
            # CI workers' curl may lack CA certs (known issue, cf. siril/imgp):
            # point curl at an existing CA bundle so it can verify the
            # harmonybrew server during install (and the later brew install
            # rust fetch). Persist it in ~/.curlrc too, because brew's own
            # curl subprocesses (e.g. the portable-git bottle fetch during
            # `brew update`) do not reliably inherit SSL_CERT_FILE from the
            # conanbuild env and fail with curl: (60) unable to get local
            # issuer certificate otherwise. The shell `export` prefix is
            # required: os.environ does NOT propagate to brew's grandchild
            # curl (brew resets env), but `export` in the shell command
            # cascades to the whole subprocess tree.
            cacert = None
            for cand in (
                "/etc/ssl/certs/cacert.pem",
                os.path.expanduser("~/usr/local/ssl/cert.pem"),
            ):
                if os.path.isfile(cand):
                    cacert = cand
                    break
            if cacert:
                os.environ["SSL_CERT_FILE"] = cacert
                os.environ["CURL_CA_BUNDLE"] = cacert
                curlrc = os.path.expanduser("~/.curlrc")
                with open(curlrc, "a") as f:
                    f.write(f'cacert = "{cacert}"\n')
                ssl_env = f"export SSL_CERT_FILE={cacert} CURL_CA_BUNDLE={cacert}; "
            else:
                ssl_env = ""
            self.run(
                f'{ssl_env}zsh -c "$(curl -fsSL https://harmonybrew.atomgit.com/install.sh)"',
                env="conanbuild",
            )

        # Install Rust via brew (export prefix cascades SSL_CERT_FILE to brew's
        # curl grandchildren that fetch the rust bottle).
        brew_path = os.path.expanduser("~/.harmonybrew/bin/brew")
        ssl_env = ""
        cacert = os.environ.get("SSL_CERT_FILE")
        if cacert:
            ssl_env = f"export SSL_CERT_FILE={cacert} CURL_CA_BUNDLE={cacert}; "
        self.run(f'{ssl_env}{brew_path} install rust', env="conanbuild")

        # Add to PATH
        os.environ["PATH"] = brew_bin + ":" + os.environ.get("PATH", "")
