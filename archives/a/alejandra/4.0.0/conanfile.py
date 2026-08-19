#!/usr/bin/env python3
"""Conan 2.x recipe for Alejandra 4.0.0."""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class AlejandraConan(ConanFile):
    name = "alejandra"
    version = "4.0.0"
    description = "The Uncompromising Nix Code Formatter"
    license = "Unlicense"
    homepage = "https://github.com/kamadorueda/alejandra"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Alejandra supports Linux and OHOS only, got {self.settings.os}"
            )
        if str(self.settings.arch) != "armv8" and str(self.settings.os) == "OHOS":
            raise ConanInvalidConfiguration("Alejandra for OHOS requires armv8")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    @staticmethod
    def _find_tool(name):
        candidates = [
            shutil.which(name),
            os.environ.get(name.upper()),
            os.environ.get(f"HNP_{name.upper()}"),
            f"/data/service/hnp/bin/{name}",
            os.path.expanduser(f"~/.harmonybrew/bin/{name}"),
            os.path.expanduser(f"~/.cargo/bin/{name}"),
            f"/storage/Users/currentUser/usr/local/bin/{name}",
        ]
        for candidate in candidates:
            if not candidate:
                continue
            real_candidate = candidate + ".real"
            if os.path.isfile(real_candidate):
                candidate = real_candidate
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
        return None

    def _bootstrap_rust_toolchain(self):
        base = os.path.join(self.build_folder, "rust-toolchain")
        os.makedirs(base, exist_ok=True)
        for bottle in self.conan_data["rust_toolchain"]:
            get(
                self,
                url=bottle["url"],
                sha256=bottle["sha256"],
                destination=base,
                keep_permissions=True,
                strip_root=False,
            )

        cargo = None
        rustc = None
        lib_dirs = []
        for root, _dirs, files in os.walk(base):
            if cargo is None and "cargo.real" in files:
                cargo = os.path.join(root, "cargo.real")
            if rustc is None:
                if "rustc.real" in files:
                    rustc = os.path.join(root, "rustc.real")
                elif "rustc" in files:
                    rustc = os.path.join(root, "rustc")
            if os.path.basename(root) == "lib" and (
                {"libssl.so", "libcrypto.so", "libz.so"} & set(files)
            ):
                lib_dirs.append(root)
            if not os.environ.get("SSL_CERT_FILE"):
                for cert_name in ("cert.pem", "cacert.pem"):
                    cert = os.path.join(root, cert_name)
                    if os.path.isfile(cert):
                        os.environ["SSL_CERT_FILE"] = cert
                        os.environ["CURL_CA_BUNDLE"] = cert
                        break

        if not cargo or not rustc:
            raise ConanInvalidConfiguration(
                "Harmonybrew Rust bottle did not contain cargo and rustc"
            )
        if lib_dirs:
            existing = os.environ.get("LD_LIBRARY_PATH")
            if existing:
                lib_dirs.append(existing)
            os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(lib_dirs)
        os.environ["PATH"] = os.pathsep.join(
            [os.path.dirname(cargo), os.path.dirname(rustc), os.environ.get("PATH", "")]
        )
        os.environ["CARGO"] = cargo
        os.environ["RUSTC"] = rustc
        return cargo, rustc

    def _ensure_ca_bundle(self):
        if str(self.settings.os) != "OHOS":
            return None

        ca_bottle = next(
            (
                bottle
                for bottle in self.conan_data["rust_toolchain"]
                if "ca-certificates-" in bottle["url"]
            ),
            None,
        )
        if not ca_bottle:
            raise ConanInvalidConfiguration(
                "the checksum-pinned CA certificate bottle is missing"
            )

        base = os.path.join(self.build_folder, "ca-certificates")
        os.makedirs(base, exist_ok=True)
        get(
            self,
            url=ca_bottle["url"],
            sha256=ca_bottle["sha256"],
            destination=base,
            keep_permissions=True,
            strip_root=False,
        )
        for root, _dirs, files in os.walk(base):
            for cert_name in ("cert.pem", "cacert.pem"):
                if cert_name in files:
                    return os.path.join(root, cert_name)
        raise ConanInvalidConfiguration(
            "CA certificate bottle did not contain cert.pem or cacert.pem"
        )

    def _build_environment(self):
        cargo = self._find_tool("cargo")
        rustc = self._find_tool("rustc")
        if (not cargo or not rustc) and str(self.settings.os) == "OHOS":
            cargo, rustc = self._bootstrap_rust_toolchain()
        if not cargo or not rustc:
            raise ConanInvalidConfiguration(
                "the Rust toolchain (cargo and rustc) is required"
            )
        ca_bundle = None
        for candidate in (
            os.environ.get("SSL_CERT_FILE"),
            "/storage/Users/currentUser/usr/local/ssl/cert.pem",
            "/etc/ssl/certs/cacert.pem",
            "/etc/ssl/cert.pem",
            os.path.expanduser(
                "~/.harmonybrew/etc/ca-certificates/cert.pem"
            ),
        ):
            if candidate and os.path.isfile(candidate):
                ca_bundle = candidate
                break
        if not ca_bundle:
            ca_bundle = self._ensure_ca_bundle()

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

        cc_alias_dir = os.path.join(self.build_folder, ".ccbin")
        os.makedirs(cc_alias_dir, exist_ok=True)
        for name in ("cc", "gcc"):
            alias = os.path.join(cc_alias_dir, name)
            if not os.path.lexists(alias):
                os.symlink(cc, alias)

        cargo_config_dir = os.path.join(self.source_folder, ".cargo")
        os.makedirs(cargo_config_dir, exist_ok=True)
        with open(
            os.path.join(cargo_config_dir, "config.toml"),
            "w",
            encoding="utf-8",
        ) as handle:
            if str(self.settings.os) == "OHOS":
                handle.write(
                    "[target.aarch64-unknown-linux-ohos]\n"
                    f'linker = "{cc}"\n'
                )
            handle.write(
                '[source.crates-io]\nreplace-with = "rsproxy-sparse"\n'
                '[source.rsproxy-sparse]\n'
                'registry = "sparse+https://rsproxy.cn/index/"\n'
                "[net]\nretry = 10\n"
                "[http]\ntimeout = 600\nlow-speed-limit = 1\n"
                f'cainfo = "{ca_bundle}"\n'
            )

        env = dict(os.environ)
        env.update(
            {
                "CARGO": cargo,
                "RUSTC": rustc,
                "CC": cc,
                "CXX": cxx,
                "CC_aarch64_unknown_linux_ohos": cc,
                "CXX_aarch64_unknown_linux_ohos": cxx,
                "RUSTFLAGS": f"-C linker={cc}",
                "CARGO_TARGET_DIR": os.path.join(self.build_folder, "target"),
                "CARGO_NET_RETRY": "10",
                "CARGO_HTTP_TIMEOUT": "600",
                "CARGO_HTTP_CAINFO": ca_bundle,
                "SSL_CERT_FILE": ca_bundle,
                "CURL_CA_BUNDLE": ca_bundle,
                "CARGO_BUILD_JOBS": "1",
                "TMPDIR": tmpdir,
                "TMP": tmpdir,
                "TEMP": tmpdir,
            }
        )
        env["PATH"] = os.pathsep.join(
            [
                cc_alias_dir,
                os.path.dirname(cargo),
                os.path.dirname(rustc),
                env.get("PATH", ""),
            ]
        )
        return cargo, rustc, env

    def build(self):
        apply_conandata_patches(self)
        cargo, rustc, env = self._build_environment()

        target = None
        if str(self.settings.os) == "OHOS":
            target = "aarch64-unknown-linux-ohos"
            rustc_info = subprocess.run(
                [rustc, "-vV"],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            ).stdout
            if f"host: {target}" not in rustc_info:
                raise ConanInvalidConfiguration(
                    f"rustc must target {target}; received:\n{rustc_info}"
                )

        manifest = os.path.join(self.source_folder, "Cargo.toml")
        target_arg = f" --target={target}" if target else ""
        saved_env = dict(os.environ)
        os.environ.update(env)
        try:
            self.run(
                f'"{cargo}" build --release --locked{target_arg} '
                f'--manifest-path="{manifest}"',
                env="conanbuild",
            )
            self.run(
                f'"{cargo}" test --release --locked{target_arg} '
                f'--manifest-path="{manifest}" -p alejandra --test fmt',
                env="conanbuild",
            )
            self.run(
                f'"{cargo}" test --release --locked{target_arg} '
                f'--manifest-path="{manifest}" -p alejandra_cli --test cli',
                env="conanbuild",
            )
        finally:
            os.environ.clear()
            os.environ.update(saved_env)

    def package(self):
        target = (
            "aarch64-unknown-linux-ohos"
            if str(self.settings.os) == "OHOS"
            else ""
        )
        release_dir = os.path.join(
            self.build_folder, "target", target, "release"
        )
        copy(
            self,
            "alejandra",
            release_dir,
            os.path.join(self.package_folder, "bin"),
        )
        copy(
            self,
            "UNLICENSE",
            self.source_folder,
            os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
