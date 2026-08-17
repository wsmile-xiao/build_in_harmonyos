import glob
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout


UPSTREAM_TEST_COMMAND = (
    "cargo test --workspace --release --locked --tests"
)
UPSTREAM_TEST_DISCOVERED = 3


class AlassConan(ConanFile):
    name = "alass"
    version = "2.0.0"
    description = "Automatic Language-Agnostic Subtitle Synchronization"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/kaegi/alass"
    url = "https://github.com/kaegi/alass"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    exports_sources = "patches/*"

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "alass is supported on Linux and OHOS"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

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

    def _build_env(self):
        cargo = self._find_tool("cargo")
        rustc = self._find_tool("rustc")
        if (not cargo or not rustc) and str(self.settings.os) == "OHOS":
            cargo, rustc = self._bootstrap_rust_toolchain(
                self.conan_data["rust_toolchain"]
            )
        if not cargo or not rustc:
            raise ConanInvalidConfiguration(
                "Rust/Cargo toolchain is required to build alass; "
                "provision the OHOS Rust toolchain before conan create"
            )

        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}
        )
        cc = compiler_executables.get("c") or (
            shutil.which("clang") or "/data/service/hnp/bin/clang"
        )
        cxx = compiler_executables.get("cpp") or (
            shutil.which("clang++") or "/data/service/hnp/bin/clang++"
        )
        tmpdir = (
            os.environ.get("HMBS_TMPDIR")
            or os.environ.get("TMPDIR")
            or os.path.join(self.build_folder, "tmp")
        )
        os.makedirs(tmpdir, exist_ok=True)
        cargo_config_dir = os.path.join(self.source_folder, ".cargo")
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

        env = dict(os.environ)
        env.update(
            {
                "CARGO": cargo,
                "RUSTC": rustc,
                "CC": cc,
                "CXX": cxx,
                "RUSTFLAGS": f"-C linker={cc}",
                "CARGO_TARGET_DIR": os.path.join(self.build_folder, "target"),
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
        tool_dirs = [os.path.dirname(cargo), os.path.dirname(rustc)]
        env["PATH"] = os.pathsep.join(
            tool_dirs + [env.get("PATH", "")]
        )
        return cargo, env

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

    def _run_upstream_tests(self, cargo, env):
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
            cwd=self.source_folder,
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

    def build(self):
        apply_conandata_patches(self)
        cargo, env = self._build_env()
        command = [
            cargo,
            "build",
            "--release",
            "--locked",
            "--package",
            "alass-cli",
        ]
        proc = subprocess.run(
            command,
            cwd=self.source_folder,
            env=env,
            capture_output=True,
            text=True,
            timeout=1800,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        print(output, flush=True)
        if proc.returncode != 0:
            raise ConanException(
                f"cargo build failed with exit code {proc.returncode}"
            )
        self._run_upstream_tests(cargo, env)

    def package(self):
        target_dir = os.path.join(self.build_folder, "target", "release")
        binary = os.path.join(target_dir, "alass-cli")
        if not os.path.isfile(binary):
            raise ConanInvalidConfiguration(
                f"alass-cli binary not found after cargo build: {binary}"
            )
        copy(
            self,
            "alass-cli",
            src=target_dir,
            dst=os.path.join(self.package_folder, "bin"),
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
