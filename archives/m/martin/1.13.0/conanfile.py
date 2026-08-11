#!/usr/bin/env python3
"""Conan 2.x recipe — martin 1.13.0

A tile server able to serve tiles from PostGIS, MBTiles and PMTiles sources.
Source: https://github.com/maplibre/martin (martin-v1.13.0 tag)
Build system: cargo (Rust workspace)
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class MartinConan(ConanFile):
    name = "martin"
    version = "1.13.0"
    description = "Blazing fast and lightweight tile server with PostGIS, MBTiles, and PMTiles support"
    license = "MIT OR Apache-2.0"
    homepage = "https://maplibre.org/martin/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

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
                f"martin supports Linux and OHOS only, got {self.settings.os}"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="martin-1.13.0.tar.gz")

    def generate(self):
        # Create .cargo/config.toml to use clang as linker (OHOS has clang,
        # not cc, in default PATH), keep target dir inside build folder and
        # use the rsproxy sparse registry mirror. CI workers have no CA
        # bundle for crates.io TLS (SSL: unable to get local issuer
        # certificate) and poor direct connectivity, so point cargo at the
        # mirror and set SSL_CERT_FILE to the system CA store.
        cargo_dir = os.path.join(self.build_folder, ".cargo")
        os.makedirs(cargo_dir, exist_ok=True)
        config_path = os.path.join(cargo_dir, "config.toml")
        with open(config_path, "w") as f:
            f.write('[build]\ntarget-dir = "target"\n')
            if str(self.settings.os) == "OHOS":
                f.write(
                    "\n[target.aarch64-unknown-linux-ohos]\n"
                    'linker = "/data/service/hnp/bin/clang"\n'
                )
            f.write(
                "\n[source.crates-io]\n"
                'replace-with = "rsproxy-sparse"\n'
                "\n[source.rsproxy-sparse]\n"
                'registry = "sparse+https://rsproxy.cn/index/"\n'
            )

    def build(self):
        apply_conandata_patches(self)

        # /tmp is read-only and full on OHOS workers; use a writable TMPDIR.
        if str(self.settings.os) == "OHOS":
            tmpdir = os.path.expanduser("~/tmp/martin")
            os.makedirs(tmpdir, exist_ok=True)
            os.environ["TMPDIR"] = tmpdir
            # aws-lc-sys links its static library via llvm-ar; under make -j
            # (cargo's default jobserver) llvm-ar intermittently fails with
            # "Error running link command: no such file or directory" on OHOS.
            # Force serial builds so the link step is reliable.
            os.environ["CARGO_BUILD_JOBS"] = "1"
            os.environ["MAKEFLAGS"] = "-j1"

        # Rust toolchain: prefer Harmonybrew cargo, fall back to PATH.
        # CI workers do not put Harmonybrew on PATH (and conanbuild env
        # resets PATH), so probe several well-known locations explicitly.
        cargo = self._find_cargo()
        if not cargo:
            # Some CI workers (e.g. CI-034) have no Rust toolchain at all;
            # bootstrap it from the Harmonybrew bottles.
            cargo = self._bootstrap_rust_toolchain()
        if cargo:
            os.environ["PATH"] = os.path.dirname(cargo) + ":" + os.environ.get("PATH", "")
        else:
            raise ConanInvalidConfiguration("cargo toolchain is required to build martin")

        # cargo.real dynamically links libssl/libcrypto/libz. Its DT_RUNPATH
        # is ignored by the CI sandbox's musl loader, which then falls back
        # to the system OpenSSL (missing OpenSSL 3.x symbols such as
        # UI_method_get_reader), causing "Error relocating ... symbol not
        # found". Explicitly put the Harmonybrew OpenSSL/zlib on
        # LD_LIBRARY_PATH so the correct libraries are loaded.
        lib_paths = [
            os.path.expanduser("~/.harmonybrew/opt/openssl@3/lib"),
            os.path.expanduser("~/.harmonybrew/opt/zlib-ng-compat/lib"),
        ]
        existing = [p for p in lib_paths if os.path.isdir(p)]
        if existing:
            prev = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = ":".join(existing + ([prev] if prev else []))

        # CI workers have no CA bundle: cargo fails with "SSL certificate
        # verify result: unable to get local issuer certificate". Point
        # SSL_CERT_FILE/CURL_CA_BUNDLE at the system CA store when present.
        if not os.environ.get("SSL_CERT_FILE"):
            for ca in ("/etc/ssl/certs/cacert.pem",
                       os.path.expanduser("~/.harmonybrew/etc/ca-certificates/cert.pem")):
                if os.path.isfile(ca):
                    os.environ["SSL_CERT_FILE"] = ca
                    os.environ["CURL_CA_BUNDLE"] = ca
                    break

        # C toolchain for -sys crates (openssl/aws-lc/sqlite/zstd).
        clang = os.environ.get("CC") or "/data/service/hnp/bin/clang"
        clangxx = os.environ.get("CXX") or "/data/service/hnp/bin/clang++"
        os.environ["CC"] = clang
        os.environ["CXX"] = clangxx
        # Tell rustc to use clang as the linker.
        os.environ["RUSTFLAGS"] = f"-C linker={clang}"

        # aws-lc-sys needs the OHOS SDK cmake toolchain to detect aarch64 and
        # build its assembly files; without it the link fails with undefined
        # chacha/aes symbols. OHOS_SDK_NATIVE is set by the CI worker; fall
        # back to a well-known local SDK layout when available.
        if str(self.settings.os) == "OHOS" and not os.environ.get("OHOS_SDK_NATIVE"):
            for sdk in ("/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native",):
                if os.path.isfile(os.path.join(sdk, "build/cmake/ohos.toolchain.cmake")):
                    os.environ["OHOS_SDK_NATIVE"] = sdk
                    break

        # The OHOS SDK llvm/bin ships llvm-ar but is missing the llvm-ranlib
        # symlink, and the directory is read-only. aws-lc-sys' CMake link
        # script invokes llvm-ranlib and fails with "no such file or
        # directory". Work around it by generating a fixed copy of the
        # toolchain that points CMAKE_AR/CMAKE_RANLIB at the system copies
        # (/data/service/hnp/bin/llvm-ranlib -> llvm-ar), then hand it to
        # aws-lc-sys via the CMAKE_TOOLCHAIN_FILE env var it honors.
        sdk = os.environ.get("OHOS_SDK_NATIVE", "")
        llvm_bin = os.path.join(sdk, "llvm", "bin")
        alt_ranlib = "/data/service/hnp/bin/llvm-ranlib"
        if (
            sdk
            and os.path.isfile(os.path.join(llvm_bin, "llvm-ar"))
            and not os.path.lexists(os.path.join(llvm_bin, "llvm-ranlib"))
            and os.path.lexists(alt_ranlib)
        ):
            tc_src = os.path.join(sdk, "build", "cmake", "ohos.toolchain.cmake")
            tc_dir = os.path.join(self.build_folder, "toolchain-fix")
            os.makedirs(tc_dir, exist_ok=True)
            tc_dst = os.path.join(tc_dir, "ohos.toolchain.cmake")
            shutil.copy2(tc_src, tc_dst)
            plat_src = os.path.join(os.path.dirname(tc_src), "sdk_native_platforms.cmake")
            if os.path.isfile(plat_src):
                shutil.copy2(plat_src, os.path.join(tc_dir, "sdk_native_platforms.cmake"))
            with open(tc_dst) as f:
                content = f.read()
            # The SDK toolchain derives OHOS_SDK_NATIVE from its own
            # directory; the fixed copy lives elsewhere, so pin it.
            content = content.replace(
                'get_filename_component(OHOS_SDK_NATIVE "${CMAKE_CURRENT_LIST_DIR}/../.." ABSOLUTE)',
                f'set(OHOS_SDK_NATIVE "{sdk}")',
            )
            content += (
                "\n# Fix llvm-ranlib missing from the OHOS SDK llvm/bin.\n"
                'set(CMAKE_AR "/data/service/hnp/bin/llvm-ar" CACHE FILEPATH "ar" FORCE)\n'
                f'set(CMAKE_RANLIB "{alt_ranlib}" CACHE FILEPATH "ranlib" FORCE)\n'
            )
            with open(tc_dst, "w") as f:
                f.write(content)
            os.environ["CMAKE_TOOLCHAIN_FILE"] = tc_dst
            os.environ["CMAKE_TOOLCHAIN_FILE_aarch64_unknown_linux_ohos"] = tc_dst

        # martin's default features include `webui` (needs npm/vite, no OHOS
        # native binding), `rendering` (needs maplibre-native C++ tree) and
        # `lambda`; build the server feature set that works on OHOS instead.
        features = ",".join([
            "fonts", "mbtiles", "metrics", "passthrough", "pmtiles",
            "postgres", "sprites", "styles", "geojson", "mlt",
        ])
        # Use the resolved absolute cargo path: the conanbuild env may reset
        # PATH and drop the toolchain directory.
        self.run(
            f'"{cargo}" build --release --no-default-features '
            f"--features {features} --bins",
            env="conanbuild",
        )

    @staticmethod
    def _find_cargo():
        """Locate the Rust cargo binary across well-known OHOS locations.

        CI workers run conan inside a sandboxed profile whose PATH only lists
        system bins, and the conanbuild env resets PATH again, so probe the
        usual Harmonybrew/rustup install dirs explicitly.
        """
        import shutil as _shutil
        candidates = [
            _shutil.which("cargo"),
            "/storage/Users/currentUser/.harmonybrew/bin/cargo",
            "/storage/Users/currentUser/.cargo/bin/cargo",
            os.path.expanduser("~/.harmonybrew/bin/cargo"),
            os.path.expanduser("~/.cargo/bin/cargo"),
            "/data/service/hnp/bin/cargo",
            "/storage/Users/currentUser/usr/local/bin/cargo",
        ]
        for cand in candidates:
            if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
                return cand
        return None

    def _bootstrap_rust_toolchain(self):
        """Download and unpack the Harmonybrew Rust toolchain bottles.

        Some CI workers (e.g. CI-034) have no preinstalled Rust toolchain and
        the sandbox PATH has no cargo; there is also no curl, so use urllib
        to fetch the official OHOS bottles (rust + openssl@3 + zlib-ng-compat)
        and unpack them under the build folder.
        """
        import tarfile
        import urllib.request

        base = os.path.join(self.build_folder, "rust-toolchain")
        os.makedirs(base, exist_ok=True)
        bottles = {
            "rust": "https://harmonybrew.atomgit.com/bottles/rust-1.97.1.arm64_ohos.bottle.tar.gz",
            "openssl3": "https://harmonybrew.atomgit.com/bottles/openssl%403-3.6.3.arm64_ohos.bottle.tar.gz",
            "zlib": "https://harmonybrew.atomgit.com/bottles/zlib-ng-compat-2.3.3_1.arm64_ohos.bottle.tar.gz",
        }
        for name, url in bottles.items():
            tgz = os.path.join(base, name + ".tar.gz")
            if not os.path.isfile(tgz):
                urllib.request.urlretrieve(url, tgz)
            with tarfile.open(tgz, "r:gz") as tf:
                tf.extractall(base)

        cargo_real = None
        for root, _dirs, files in os.walk(base):
            if "cargo.real" in files:
                cargo_real = os.path.join(root, "cargo.real")
                break
        if not cargo_real:
            raise ConanInvalidConfiguration("failed to bootstrap Rust toolchain")

        # cargo.real dynamically links libssl/libcrypto/libz; its DT_RUNPATH
        # is ignored by the CI sandbox's musl loader, so point
        # LD_LIBRARY_PATH at the unpacked openssl/zlib bottles.
        lib_dirs = []
        for root, _dirs, files in os.walk(base):
            if os.path.basename(root) == "lib":
                libs = set(files)
                if libs & {"libssl.so", "libcrypto.so", "libz.so"}:
                    lib_dirs.append(root)
        if lib_dirs:
            prev = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = ":".join(lib_dirs + ([prev] if prev else []))
        return cargo_real

    def package(self):
        target_dir = os.path.join(self.build_folder, "target", "release")
        for binary in ("martin", "martin-cp", "mbtiles"):
            copy(self, binary, target_dir,
                 os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
