#!/usr/bin/env python3
"""Conan recipe for mdf2iso 0.3.1."""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Mdf2isoConan(ConanFile):
    name = "mdf2iso"
    version = "0.3.1"
    description = "Tool to convert Alcohol 120% MDF disk images to ISO images"
    license = "GPL-2.0-or-later"
    homepage = "https://www.nongnu.org/mdf2iso/"
    url = ""
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _sign_binary_if_needed(self, bin_path):
        if str(self.settings.os) != "OHOS":
            return

        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        tmp_signed = bin_path + ".signed"
        subprocess.run(
            [
                sign_tool,
                "sign",
                "-inFile",
                bin_path,
                "-outFile",
                tmp_signed,
                "-selfSign",
                "1",
            ],
            check=True,
        )
        os.replace(tmp_signed, bin_path)
        os.chmod(bin_path, 0o755)

    def _built_binary(self):
        candidates = [
            os.path.join(self.build_folder, "src", "mdf2iso"),
            os.path.join(self.source_folder, "src", "mdf2iso"),
        ]
        for candidate in candidates:
            if os.path.exists(candidate):
                os.chmod(candidate, 0o755)
                return candidate
        raise ConanException("mdf2iso binary was not produced by make")

    def _run_upstream_tests(self):
        binary = self._built_binary()
        work_dir = os.path.join(self.build_folder, "upstream-test")
        os.makedirs(work_dir, exist_ok=True)
        test_binary = os.path.join(work_dir, "mdf2iso")
        shutil.copy2(binary, test_binary)
        os.chmod(test_binary, 0o755)
        self._sign_binary_if_needed(test_binary)

        test_dir = os.path.join(self.source_folder, "test")
        upstream_tests = [
            ("TEST.mdf", 370688),
            ("TEST2.mdf", 370688),
        ]
        for filename, expected_size in upstream_tests:
            source_path = os.path.join(test_dir, filename)
            output_path = os.path.join(work_dir, filename.replace(".mdf", ".iso"))
            if os.path.exists(output_path):
                os.remove(output_path)

            self.output.info(f"Running upstream fixture test: {filename}")
            self.run(f'"{test_binary}" "{source_path}" "{output_path}"')
            if not os.path.exists(output_path):
                raise ConanException(f"upstream test did not create {output_path}")
            actual_size = os.path.getsize(output_path)
            if actual_size != expected_size:
                raise ConanException(
                    f"upstream test {filename} produced {actual_size} bytes, expected {expected_size}"
                )
            self.output.info(f"Upstream fixture test passed: {filename}")

    def generate(self):
        tc = AutotoolsToolchain(self)
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        tc.configure_args.append(f"CONFIG_SHELL={bash}")
        tc.configure_args.append("--prefix=/")
        if str(self.settings.os) == "OHOS":
            tc.configure_args.append("--host=aarch64-linux-ohos")
            tc.extra_ldflags.append("-fuse-ld=bfd")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make()
        self._run_upstream_tests()

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        bin_path = os.path.join(self.package_folder, "bin", "mdf2iso")
        if os.path.exists(bin_path):
            os.chmod(bin_path, 0o755)
        if os.path.exists(bin_path):
            self._sign_binary_if_needed(bin_path)
        copy(self, "gpl.txt", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
