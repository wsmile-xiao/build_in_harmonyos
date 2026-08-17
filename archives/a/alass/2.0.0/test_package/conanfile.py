import glob
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import get, patch


UPSTREAM_URLS = [
    (
        "https://gh-proxy.com/https://github.com/kaegi/alass/"
        "archive/refs/tags/v2.0.0.tar.gz"
    ),
    "https://github.com/kaegi/alass/archive/refs/tags/v2.0.0.tar.gz",
]
UPSTREAM_SHA256 = (
    "ce88f92c7a427b623edcabb1b64e80be70cca2777f3da4b96702820a6cdf1e26"
)
UPSTREAM_TEST_COMMAND = (
    "cargo test --workspace --release --locked --tests"
)
UPSTREAM_TEST_DISCOVERED = 3

RUST_TOOLCHAIN_BOTTLES = (
    (
        "https://harmonybrew.atomgit.com/bottles/"
        "rust-1.97.1.arm64_ohos.bottle.tar.gz",
        "21b135fd7f403d08752a0fcc2bac70ee9a79909ad0e05e7c3ebbdd9afa66525e",
    ),
    (
        "https://harmonybrew.atomgit.com/bottles/"
        "openssl%403-3.6.3.arm64_ohos.bottle.tar.gz",
        "f773ba9053a6ac7ecf6b5d56e78d24d8386d60327f1f184d11132e965254d285",
    ),
    (
        "https://harmonybrew.atomgit.com/bottles/"
        "zlib-ng-compat-2.3.3_1.arm64_ohos.bottle.tar.gz",
        "1c17a31f8104701bce6b471af8dbbd14bb67d16a504eec087018feb05493a430",
    ),
    (
        "https://harmonybrew.atomgit.com/bottles/"
        "ca-certificates-2026-08-13.arm64_ohos.bottle.tar.gz",
        "2916654bf828a59e1fd9862299300b48c1e5e7cb09fef279d4f78aaf066cd006",
    ),
)


class AlassTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "test.sh", "*.srt", "patches/*"

    def requirements(self):
        self.requires(self.tested_reference_str)

    @staticmethod
    def _find_tool(name):
        rust_candidates = []
        rust_patterns = [
            f"/storage/Users/currentUser/usr/"
            f"rust-*-aarch64-unknown-linux-ohos/bin/{name}",
            os.path.expanduser(
                f"~/usr/rust-*-aarch64-unknown-linux-ohos/bin/{name}"
            ),
        ]
        for pattern in rust_patterns:
            rust_candidates.extend(glob.glob(pattern))

        def rust_version(path):
            match = re.search(
                r"/rust-([0-9]+(?:\.[0-9]+)*)-", path
            )
            if not match:
                return ()
            return tuple(int(part) for part in match.group(1).split("."))

        candidates = [
            shutil.which(name),
            os.environ.get(name.upper()),
            os.environ.get(f"HNP_{name.upper()}"),
            f"/data/service/hnp/bin/{name}",
            os.path.expanduser(f"~/.harmonybrew/bin/{name}"),
            os.path.expanduser(f"~/.cargo/bin/{name}"),
            f"/storage/Users/currentUser/.harmonybrew/bin/{name}",
            f"/storage/Users/currentUser/.cargo/bin/{name}",
        ] + sorted(
            set(rust_candidates), key=rust_version, reverse=True
        )
        for candidate in candidates:
            if not candidate:
                continue
            real_candidate = candidate + ".real"
            if os.path.isfile(real_candidate):
                candidate = real_candidate
            if os.path.isfile(candidate) and os.access(
                candidate, os.X_OK
            ):
                return candidate
        return None

    def _bootstrap_rust_toolchain(self, bottles):
        """Bootstrap checksum-pinned Harmonybrew Rust bottles when CI has
        no provisioned OHOS Rust toolchain.
        """
        if str(self.settings.os) != "OHOS":
            return None, None

        base = os.path.join(self.build_folder, "rust-toolchain")
        os.makedirs(base, exist_ok=True)
        for bottle in bottles:
            if isinstance(bottle, dict):
                url = bottle["url"]
                sha256 = bottle["sha256"]
            else:
                url, sha256 = bottle
            get(
                self,
                url=url,
                sha256=sha256,
                destination=base,
                keep_permissions=True,
                strip_root=False,
            )

        cargo = None
        rustc = None
        for root, _dirs, files in os.walk(base):
            if cargo is None and "cargo.real" in files:
                cargo = os.path.join(root, "cargo.real")
            if rustc is None:
                if "rustc.real" in files:
                    rustc = os.path.join(root, "rustc.real")
                elif "rustc" in files:
                    rustc = os.path.join(root, "rustc")
        if not cargo or not rustc:
            raise ConanInvalidConfiguration(
                "Harmonybrew Rust bottle did not contain cargo/rustc"
            )

        bin_dir = os.path.dirname(cargo)
        lib_dirs = []
        for root, _dirs, files in os.walk(base):
            if os.path.basename(root) != "lib":
                continue
            if {"libssl.so", "libcrypto.so", "libz.so"} & set(files):
                lib_dirs.append(root)
        if lib_dirs:
            existing = os.environ.get("LD_LIBRARY_PATH")
            if existing:
                lib_dirs.append(existing)
            os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(lib_dirs)
        if not os.environ.get("SSL_CERT_FILE"):
            for root, _dirs, _files in os.walk(base):
                for cert_name in ("cert.pem", "cacert.pem"):
                    cert = os.path.join(root, cert_name)
                    if os.path.isfile(cert):
                        os.environ["SSL_CERT_FILE"] = cert
                        os.environ["CURL_CA_BUNDLE"] = cert
                        break
                if os.environ.get("SSL_CERT_FILE"):
                    break

        os.environ["PATH"] = os.pathsep.join(
            [bin_dir, os.environ.get("PATH", "")]
        )
        os.environ["CARGO"] = cargo
        os.environ["RUSTC"] = rustc
        return cargo, rustc

    @staticmethod
    def _parse_test_counts(output):
        passed = failed = ignored = 0
        pattern = re.compile(
            r"test result:\s+\w+\.\s+(\d+) passed;\s+"
            r"(\d+) failed;\s+(\d+) ignored;"
        )
        for match in pattern.finditer(output):
            passed += int(match.group(1))
            failed += int(match.group(2))
            ignored += int(match.group(3))
        return passed, failed, ignored

    def _upstream_source(self):
        source_root = os.path.join(self.build_folder, "upstream")
        manifest = os.path.join(source_root, "Cargo.toml")
        if not os.path.isfile(manifest):
            os.makedirs(source_root, exist_ok=True)
            get(
                self,
                url=UPSTREAM_URLS,
                filename="alass-v2.0.0.tar.gz",
                sha256=UPSTREAM_SHA256,
                destination=source_root,
                strip_root=True,
            )
            patch(
                self,
                base_path=source_root,
                patch_file=os.path.join(
                    self.recipe_folder, "patches",
                    "0001-update-rust-runtime-dependencies.patch",
                ),
            )
        if not os.path.isfile(manifest):
            raise ConanInvalidConfiguration(
                "alass upstream Cargo.toml missing after extraction"
            )
        return source_root

    def _run_upstream_tests(self):
        cargo = self._find_tool("cargo")
        rustc = self._find_tool("rustc")
        if (not cargo or not rustc) and str(self.settings.os) == "OHOS":
            cargo, rustc = self._bootstrap_rust_toolchain(
                RUST_TOOLCHAIN_BOTTLES
            )
        if not cargo or not rustc:
            marker = {
                "status": "environment_gap",
                "framework": "cargo-test",
                "command": UPSTREAM_TEST_COMMAND,
                "discovered": UPSTREAM_TEST_DISCOVERED,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": UPSTREAM_TEST_DISCOVERED,
                "reason": "cargo/rustc not available in the test runner",
            }
            print(
                "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker),
                flush=True,
            )
            raise ConanInvalidConfiguration(
                "Rust/Cargo toolchain is required for upstream tests"
            )

        source_root = self._upstream_source()
        cargo_config_dir = os.path.join(source_root, ".cargo")
        os.makedirs(cargo_config_dir, exist_ok=True)
        with open(
            os.path.join(cargo_config_dir, "config.toml"),
            "w",
            encoding="utf-8",
        ) as handle:
            handle.write(
                '[source.crates-io]\nreplace-with = "rsproxy-sparse"\n'
                '[source.rsproxy-sparse]\n'
                'registry = "sparse+https://rsproxy.cn/index/"\n'
                "[net]\nretry = 10\n"
                "[http]\ntimeout = 600\nlow-speed-limit = 1\n"
            )

        cc = shutil.which("clang") or "/data/service/hnp/bin/clang"
        cxx = shutil.which("clang++") or "/data/service/hnp/bin/clang++"
        tmpdir = (
            os.environ.get("HMBS_TMPDIR")
            or os.environ.get("TMPDIR")
            or os.path.join(self.build_folder, "tmp")
        )
        os.makedirs(tmpdir, exist_ok=True)
        env = dict(os.environ)
        env.update(
            {
                "RUSTC": rustc,
                "CC": cc,
                "CXX": cxx,
                "RUSTFLAGS": f"-C linker={cc}",
                "CARGO_TARGET_DIR": os.path.join(
                    self.build_folder, "upstream-target"
                ),
                "CARGO_NET_RETRY": "10",
                "CARGO_HTTP_TIMEOUT": "600",
                "CARGO_BUILD_JOBS": "1",
                "TMPDIR": tmpdir,
                "TMP": tmpdir,
                "TEMP": tmpdir,
            }
        )
        if not env.get("SSL_CERT_FILE"):
            for ca in (
                "/storage/Users/currentUser/usr/local/ssl/cert.pem",
                "/etc/ssl/certs/cacert.pem",
                "/etc/ssl/cert.pem",
                os.path.expanduser(
                    "~/.harmonybrew/etc/ca-certificates/cert.pem"
                ),
            ):
                if os.path.isfile(ca):
                    env["SSL_CERT_FILE"] = ca
                    env["CURL_CA_BUNDLE"] = ca
                    break
        env["PATH"] = os.pathsep.join(
            [os.path.dirname(cargo), os.path.dirname(rustc), env.get("PATH", "")]
        )
        command = [
            cargo,
            "test",
            "--workspace",
            "--release",
            "--locked",
            "--tests",
        ]
        proc = subprocess.run(
            command,
            cwd=source_root,
            env=env,
            capture_output=True,
            text=True,
            timeout=1800,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        print(output, flush=True)
        passed, failed, ignored = self._parse_test_counts(output)
        executed = passed + failed
        marker = {
            "status": "passed" if proc.returncode == 0 and failed == 0 else "failed",
            "framework": "cargo-test",
            "command": UPSTREAM_TEST_COMMAND,
            "discovered": UPSTREAM_TEST_DISCOVERED,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": ignored,
        }
        print(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker),
            flush=True,
        )
        if (
            proc.returncode != 0
            or failed != 0
            or executed + ignored != UPSTREAM_TEST_DISCOVERED
        ):
            raise ConanInvalidConfiguration(
                "alass upstream tests failed or produced unexpected counts"
            )

    def test(self):
        dependency = self.dependencies["alass"]
        binary = os.path.join(dependency.package_folder, "bin", "alass-cli")
        if not os.path.isfile(binary):
            raise ConanInvalidConfiguration(
                f"packaged alass-cli binary not found: {binary}"
            )
        if not can_run(self):
            raise ConanInvalidConfiguration(
                "alass test_package must run natively on the target"
            )

        shell = shutil.which("bash")
        ohos_bash = "/data/service/hnp/bin/bash"
        if not shell and os.path.isfile(ohos_bash):
            shell = ohos_bash
        shell = shell or shutil.which("sh")
        if not shell:
            raise ConanInvalidConfiguration(
                "bash or sh is required to run the alass test harness"
            )
        script = os.path.join(self.recipe_folder, "test.sh")
        self.run(
            f'"{shell}" "{script}" "{binary}"',
            cwd=self.recipe_folder,
            env="conanrun",
        )
        self._run_upstream_tests()
