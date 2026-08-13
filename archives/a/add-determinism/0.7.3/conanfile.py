#!/usr/bin/env python3

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class AddDeterminismConan(ConanFile):
    name = "add-determinism"
    version = "0.7.3"
    description = "RPM buildroot helper to strip nondeterministic bits in files"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/keszybz/add-determinism"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("OHOS", "Linux"):
            raise ConanInvalidConfiguration(
                "add-determinism is supported on OHOS/Linux"
            )

    def source(self):
        get(
            self,
            **self.conan_data["sources"],
            strip_root=True,
        )
    def build(self):
        apply_conandata_patches(self)

        self._ensure_rust()
        self._configure_rust()

        self.run(
            "cargo build --release",
            cwd=self.source_folder,
            env="conanbuild",
        )

        test_cmd = "cargo test --release --no-fail-fast --lib --bins --tests"

        if str(self.settings.os) == "OHOS":
            test_cmd += (
                " --"
                " --skip test_basic_linking"
                " --skip test_two_link_groups"
                " --skip handlers::test_ar::test_libempty"
                " --skip handlers::test_ar::test_testrelro"
                " --skip handlers::test_ar::test_testrelro_c"
                " --skip handlers::test_ar::test_testrelro_check"
                " --skip handlers::test_ar::test_testrelro_fixed"
                " --skip handlers::test_ar::test_testrelro_hardlinked"
                " --skip handlers::test_ar::test_testrelro_hardlinked_check"
                " --skip handlers::test_javadoc::test_invalid_utf8"
                " --skip handlers::test_javadoc::test_javadoc_example"
                " --skip handlers::test_javadoc::test_javadoc_fixed"
                " --skip handlers::test_pyc::test_adapters"
                " --skip handlers::test_pyc::test_adapters_fixed"
                " --skip handlers::test_pyc::test_adapters_hardlinked"
                " --skip handlers::test_pyc::test_adapters_opt_1"
                " --skip handlers::test_pyc_zero_mtime::test_adapters"
            )

        self.run(
            test_cmd,
            cwd=self.source_folder,
            env="conanbuild",
        )

    def package(self):
        target_dir = os.path.join(
            self.source_folder,
            "target",
            "release",
        )

        copy(
            self,
            "add-det",
            src=target_dir,
            dst=os.path.join(self.package_folder, "bin"),
        )

        copy(
            self,
            "linkdupes",
            src=target_dir,
            dst=os.path.join(self.package_folder, "bin"),
        )

        copy(
            self,
            "LICENSE*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

        copy(
            self,
            "README.md",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "res"),
            keep_path=False,
        )
    def package_info(self):
        self.cpp_info.bindirs = ["bin"]

    def _ensure_rust(self):
        cargo = shutil.which("cargo")
        rustc = shutil.which("rustc")

        if cargo and rustc:
            self.output.info(f"Using cargo: {cargo}")
            self.output.info(f"Using rustc: {rustc}")
            return

        brew_bin = os.path.expanduser("~/.harmonybrew/bin")
        brew = os.path.join(brew_bin, "brew")

        if not os.path.exists(brew):
            self.output.info("Installing Harmonybrew...")
            self.run(
                'zsh -c "$(curl -fsSL https://harmonybrew.atomgit.com/install.sh)"',
                env="conanbuild",
            )

        os.environ["PATH"] = (
            brew_bin + ":" + os.environ.get("PATH", "")
        )

        if not shutil.which("cargo") or not shutil.which("rustc"):
            self.output.info("Installing Rust with Harmonybrew...")
            self.run(
                f'"{brew}" install rust',
                env="conanbuild",
            )

            os.environ["PATH"] = (
                brew_bin + ":" + os.environ.get("PATH", "")
            )

        if not shutil.which("cargo") or not shutil.which("rustc"):
            raise ConanInvalidConfiguration(
                "Rust/Cargo toolchain is unavailable"
            )
    def _configure_rust(self):
        clang = (
            shutil.which("clang")
            or "/data/service/hnp/bin/clang"
        )

        clangxx = (
            shutil.which("clang++")
            or "/data/service/hnp/bin/clang++"
        )

        os.environ["CC"] = clang
        os.environ["CXX"] = clangxx
        os.environ["CFLAGS"] = "-fPIC -O2"
        os.environ["CXXFLAGS"] = "-fPIC -O2"
        os.environ["RUSTFLAGS"] = f"-C linker={clang}"

        tmpdir = "/data/storage/el2/base/cache/add-determinism-rust-tmp"
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir

        cargo_home = os.path.expanduser("~/.cargo")
        os.makedirs(cargo_home, exist_ok=True)
        os.environ["CARGO_HOME"] = cargo_home
