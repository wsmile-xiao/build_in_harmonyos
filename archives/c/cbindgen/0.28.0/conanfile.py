#!/usr/bin/env python3
"""Conan recipe - cbindgen 0.28.0 (Cargo)."""

import os
import shlex
import sys

import certifi
from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import build_jobs, cross_building
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.layout import basic_layout


class CbindgenConan(ConanFile):
    name = "cbindgen"
    version = "0.28.0"
    description = "Generate C, C++ and Cython declarations from public Rust APIs"
    license = "MPL-2.0", "Apache-2.0"
    homepage = "https://github.com/mozilla/cbindgen"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = ("test_package/cython_launcher.c", "test_package/cargo_launcher.c",
                       "test_package/rust_runtime.py", "licenses/*")

    def requirements(self):
        # Crate/workspace inputs use cargo metadata at runtime.
        self.requires("rust-toolchain/1.97.1", run=True, headers=False, libs=False)

    def build_requirements(self):
        self.tool_requires("rust-toolchain/1.97.1")
        self.tool_requires("openssl/3.5.6.1.1")

    def layout(self):
        basic_layout(self, src_folder="src")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("Linux or OHOS is required")
        if str(self.settings.arch) != "armv8" or cross_building(self):
            raise ConanInvalidConfiguration("Use a native armv8 Rust toolchain and test runner")
        if self.settings.build_type != "Release":
            raise ConanInvalidConfiguration("This package uses the Cargo release profile")

    def source(self):
        get(self, **self.conan_data["sources"], filename="cbindgen-0.28.0.tar.gz", strip_root=True)
        get(self, **self.conan_data["test_sources"]["cython"], strip_root=True,
            destination=os.path.join(self.source_folder, "test-tools", "cython"))

    def generate(self):
        VirtualBuildEnv(self).generate()
        compilers = self.conf.get("tools.build:compiler_executables", default={})
        self._write_environment(compilers.get("c", "clang"), compilers.get("cpp", "clang++"))

    def _write_environment(self, cc, cxx):
        rust = self.dependencies.build["rust-toolchain"].package_folder
        env = Environment()
        env.prepend_path("PATH", os.path.join(rust, "bin"))
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(rust, "lib"))
        for key in ("CFLAGS", "CXXFLAGS", "CPPFLAGS", "LDFLAGS", "CPATH",
                    "C_INCLUDE_PATH", "CPLUS_INCLUDE_PATH", "LIBRARY_PATH",
                    "CARGO_BUILD_TARGET", "CBINDGEN_TEST_NO_COMPILE", "RUSTC_BOOTSTRAP"):
            env.unset(key)
        values = {
            "CARGO": os.path.join(self.build_folder, "cargo-runtime", "cargo-launcher"),
            "CBINDGEN_RUST_ROOT": rust,
            "CBINDGEN_OPENSSL_DIR": os.path.join(self.build_folder, "cargo-runtime"),
            "RUSTC": os.path.join(self.build_folder, "cargo-runtime", "rustc-launcher"),
            "CBINDGEN_RUST_CACHE": os.path.join(self.build_folder, "rust-exec-cache"),
            "CBINDGEN_RUNTIME_PYTHON": sys.executable,
            "CBINDGEN_RUNTIME_HELPER": os.path.join(self.export_sources_folder, "test_package", "rust_runtime.py"),
            "CBINDGEN_SIGN_TOOL": os.path.join(os.path.dirname(cc), "binary-sign-tool"),
            "CARGO_HOME": os.path.join(self.build_folder, "cargo-home"),
            "CARGO_TARGET_DIR": os.path.join(self.build_folder, "target"),
            "CARGO_BUILD_JOBS": str(min(build_jobs(self), 2)),
            "TMPDIR": os.path.join(self.build_folder, "tmp"),
            "CC": cc, "CXX": cxx,
            "RUSTFLAGS": "-C linker=" + cc,
            "CARGO_TARGET_AARCH64_UNKNOWN_LINUX_OHOS_LINKER": cc,
            "CARGO_HTTP_CAINFO": certifi.where(),
            "CBINDGEN_TEST_VERIFY": "1",
            "CYTHON": os.path.join(self.build_folder, "cython-launcher"),
            "CBINDGEN_CYTHON_PYTHON": sys.executable,
            "CBINDGEN_CYTHON_SCRIPT": os.path.join(
                self.source_folder, "test-tools", "cython", "cython.py"),
        }
        for name, value in values.items():
            env.define(name, value)
        os.makedirs(values["TMPDIR"], exist_ok=True)
        env.vars(self, scope=None).save_script("cbindgen_env")
        tests = Environment()
        # Unchanged upstream expansion fixtures require -Zunpretty.
        # Bootstrap is applied only to tests, never production build or runenv.
        tests.define("RUSTC_BOOTSTRAP", "1")
        tests.define("CFLAGS", "-Wno-non-c-typedef-for-linkage")
        tests.define("CXXFLAGS", "-Wno-non-c-typedef-for-linkage")
        tests.vars(self, scope=None).save_script("cbindgen_tests")

    def build(self):
        apply_conandata_patches(self)
        rust = self.dependencies.build["rust-toolchain"].package_folder
        cargo = shlex.quote(os.path.join(self.build_folder, "cargo-runtime", "cargo-launcher"))
        cc = self.conf.get("tools.build:compiler_executables", default={}).get("c", "clang")
        self._cargo_runtime(cc)
        launcher = os.path.join(self.export_sources_folder, "test_package", "cython_launcher.c")
        self.run(shlex.join([cc, "-std=c11", "-Wall", "-Wextra", "-Werror", launcher,
                             "-o", os.path.join(self.build_folder, "cython-launcher")]),
                 env=["conanbuild", "cbindgen_env"])
        self.run(cargo + " build --locked --release --bin cbindgen",
                 cwd=self.source_folder, env=["conanbuild", "cbindgen_env"])
        self.run(cargo + " test --locked --release --lib --bins --tests -- --test-threads=1",
                 cwd=self.source_folder, env=["conanbuild", "cbindgen_env", "cbindgen_tests"])

    def _cargo_runtime(self, cc):
        # rust-toolchain/1.97.1's Cargo needs libssl.so/libcrypto.so. Relink the
        # published PIC archives into a private directory; no system prefix or
        # public Conan lib directory receives an OpenSSL shared object.
        from pathlib import Path
        openssl = Path(self.dependencies.build["openssl"].package_folder)
        runtime = Path(self.build_folder) / "cargo-runtime"
        runtime.mkdir(exist_ok=True)
        for name in ("crypto", "ssl"):
            archive = next(openssl.rglob("lib" + name + ".a"))
            command = [cc, "-shared", "-Wl,-z,relro,-z,now", "-Wl,-soname,lib" + name + ".so",
                       "-Wl,--whole-archive", str(archive), "-Wl,--no-whole-archive",
                       "-ldl", "-pthread"]
            if name == "ssl":
                command += ["-L" + str(runtime), "-lcrypto"]
            command += ["-o", str(runtime / ("lib" + name + ".so"))]
            self.run(shlex.join(command), env=["conanbuild", "cbindgen_env"])
        launcher = os.path.join(self.export_sources_folder, "test_package", "cargo_launcher.c")
        self.run(shlex.join([cc, "-std=c11", "-Wall", "-Wextra", "-Werror", "-Wl,-z,relro,-z,now",
                             launcher, "-o", str(runtime / "cargo-launcher")]),
                 env=["conanbuild", "cbindgen_env"])
        copy(self, "cargo-launcher", str(runtime), str(runtime / "rustc-bin"))
        os.replace(runtime / "rustc-bin" / "cargo-launcher", runtime / "rustc-launcher")
        os.rmdir(runtime / "rustc-bin")

    def package(self):
        binary = os.path.join(self.build_folder, "target", "release", "cbindgen")
        if not os.path.isfile(binary):
            raise ConanInvalidConfiguration("Cargo did not produce the expected executable")
        copy(self, "cbindgen", os.path.dirname(binary), os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE", self.source_folder, os.path.join(self.package_folder, "licenses"))
        copy(self, "*.so", os.path.join(self.build_folder, "cargo-runtime"),
             os.path.join(self.package_folder, "libexec", "cbindgen"))
        copy(self, "cargo-launcher", os.path.join(self.build_folder, "cargo-runtime"),
             os.path.join(self.package_folder, "libexec", "cbindgen"))
        copy(self, "rustc-launcher", os.path.join(self.build_folder, "cargo-runtime"),
             os.path.join(self.package_folder, "libexec", "cbindgen"))
        copy(self, "rust_runtime.py", os.path.join(self.export_sources_folder, "test_package"),
             os.path.join(self.package_folder, "libexec", "cbindgen"))
        copy(self, "LICENSE.openssl", os.path.join(self.export_sources_folder, "licenses"),
             os.path.join(self.package_folder, "licenses"))
        for name in ("README.md", "docs.md", "template.toml"):
            copy(self, name, self.source_folder, os.path.join(self.package_folder, "share", "cbindgen"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        runtime = os.path.join(self.package_folder, "libexec", "cbindgen")
        rust = self.dependencies["rust-toolchain"].package_folder
        self.runenv_info.define("CARGO", os.path.join(runtime, "cargo-launcher"))
        self.runenv_info.define("RUSTC", os.path.join(runtime, "rustc-launcher"))
        self.runenv_info.define("CBINDGEN_RUST_ROOT", rust)
        self.runenv_info.define("CBINDGEN_OPENSSL_DIR", runtime)
        self.runenv_info.define("CBINDGEN_RUNTIME_PYTHON", sys.executable)
        self.runenv_info.define("CBINDGEN_RUNTIME_HELPER", os.path.join(runtime, "rust_runtime.py"))
        cc = self.conf.get("tools.build:compiler_executables", default={}).get("c", "/data/service/hnp/bin/clang")
        self.runenv_info.define("CBINDGEN_SIGN_TOOL", os.path.join(os.path.dirname(cc), "binary-sign-tool"))
        self.runenv_info.define("CARGO_HTTP_CAINFO", certifi.where())
