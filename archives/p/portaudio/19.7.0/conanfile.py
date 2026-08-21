#!/usr/bin/env python3
"""Conan recipe for PortAudio 19.7.0."""

import glob
import os
import re
import shutil
import subprocess
import shlex

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PortaudioConan(ConanFile):
    name = "portaudio"
    version = "19.7.0"
    description = "Cross-platform audio I/O library"
    license = "MIT"
    homepage = "https://www.portaudio.com/"
    url = "https://github.com/PortAudio/portaudio"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS support is currently limited to armv8")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.extend(
            [
                "--enable-shared" if self.options.shared else "--disable-shared",
                "--disable-static" if self.options.shared else "--enable-static",
                "--without-alsa",
                "--without-jack",
                "--without-oss",
                "--without-asihpi",
            ]
        )
        if self.settings.os == "OHOS":
            toolchain.configure_args.extend(
                ["--build=aarch64-linux-ohos", "--host=aarch64-linux-ohos"]
            )
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        if self.settings.os == "OHOS":
            # HMDFS blocks direct execution of shebang scripts. Keep the
            # complete Conan-generated argument string, but invoke configure
            # through the platform shell explicitly.
            configure_script = os.path.join(self.source_folder, "configure")
            command = shlex.join(["/system/bin/sh", configure_script])
            if autotools._configure_args:
                command = f"{command} {autotools._configure_args}"
            self.run(command, cwd=self.build_folder)
        else:
            autotools.configure()
        targets = ["-j1", "lib/libportaudio.la"]
        # paqa_errs does not require an audio device. Build it for OHOS even
        # when Conan's cross profile reports can_run=False; the test package
        # executes it after the package is installed on the target device.
        if not self.options.shared and (can_run(self) or self.settings.os == "OHOS"):
            targets.extend(["bin-stamp", "bin/paqa_errs"])
        autotools.make(args=targets)
        if not self.options.shared and can_run(self):
            self._run_upstream_error_test()

    def package(self):
        Autotools(self).install()
        if self.settings.os == "OHOS" and not self.options.shared:
            copy(
                self,
                "paqa_errs",
                src=os.path.join(self.build_folder, "bin"),
                dst=os.path.join(self.package_folder, "tests"),
                keep_path=False,
            )
        copy(
            self,
            "LICENSE.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        if self.settings.os == "OHOS" and self.options.shared:
            self._sign_installed_shared_libraries()

    def package_info(self):
        self.cpp_info.libs = ["portaudio"]
        self.cpp_info.set_property("cmake_file_name", "PortAudio")
        self.cpp_info.set_property("cmake_target_name", "PortAudio::PortAudio")
        self.cpp_info.set_property("pkg_config_name", "portaudio-2.0")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "m", "rt"]

    def _run_upstream_error_test(self):
        executable = os.path.join(self.build_folder, "bin", "paqa_errs")
        if self.settings.os == "OHOS":
            self._sign_ohos_elf(executable, "upstream-test")
        completed = subprocess.run(
            [executable],
            cwd=self.build_folder,
            check=True,
            capture_output=True,
            text=True,
            timeout=120,
        )
        output = completed.stdout + completed.stderr
        self.output.info(output.strip())
        if not re.search(r"QA Report: [0-9]+ passed, 0 failed\.", output):
            raise ConanException("PortAudio paqa_errs did not report zero failures")

    def _sign_installed_shared_libraries(self):
        targets = set()
        for pattern in ("*.so", "*.so.*"):
            targets.update(
                glob.glob(os.path.join(self.package_folder, "lib", pattern))
            )
        for target in sorted(targets):
            if os.path.isfile(target) and not os.path.islink(target):
                self._sign_ohos_elf(target, "package")

    @staticmethod
    def _sign_ohos_elf(path, label):
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(path):
            raise ConanException(f"Missing {label} ELF: {path}")
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("Required OHOS signing tools are missing")
        output = path + ".portaudio-signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", output, "-selfSign", "1"],
            check=True,
            timeout=60,
        )
        sections = subprocess.run(
            [readelf, "-SW", output],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException(f"Signed {label} ELF has invalid .codesign count")
        os.chmod(output, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(output, path)
