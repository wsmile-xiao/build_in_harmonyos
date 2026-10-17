#!/usr/bin/env python3
"""Installed-package API tests for libcanberra-pulse 0.30.

Two consumers link the published libcanberra-pulse/0.30 and drive the public
canberra.h API (no audio device and no PulseAudio server required):
  * libcanberra_api_surface     strong-typed relocation of every exported
                                ca_proplist_* / ca_context_* / ca_strerror
                                symbol plus an error-string sweep.
  * libcanberra_pulse_contract  CA_MAJOR/CA_MINOR/CA_CHECK_VERSION contract,
                                error-code enumeration checks, and the proof
                                that the PulseAudio driver is the backend
                                compiled into libcanberra.so (a pulse build
                                accepts the driver name "pulse" at open time
                                and reports CA_ERROR_NODRIVER for null/alsa,
                                which archives/l/libcanberra/0.30 - built with
                                --with-builtin=null - does the other way
                                round).

Runtime note: libcanberra.so.0 has a DT_NEEDED entry for libpulse.so.0, and
the published pulseaudio/17.0.1 libraries carry no .codesign section, so the
OHOS loader refuses to map them and the consumers abort with "pa_stream_unref:
symbol not found".  The tests therefore resolve libpulse.so.0 and
libpulse-simple.so.0 against the signed platform client libraries
(/system/lib64/libpulseaudio.z.so, /system/lib64/libpulse-simple.z.so); the
plain conanrun run is executed first and only logged, to document the
limitation of the dependency package.
"""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout

SIGNED_PLATFORM_LIBS = {
    "libpulse.so.0": "/system/lib64/libpulseaudio.z.so",
    "libpulse-simple.so.0": "/system/lib64/libpulse-simple.z.so",
}


class LibcanberraPulseTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "*.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            raise ConanException("libcanberra-pulse consumers are not runnable")
        ohos = str(self.settings.os) == "OHOS"
        pulse_sys = None
        if ohos:
            self._check_installed_library()
            pulse_sys = self._platform_pulse_dir()
        for name in ("libcanberra_api_surface", "libcanberra_pulse_contract"):
            executable = os.path.join(self.cpp.build.bindir, name)
            if not ohos:
                self.run(f'"{executable}"', env="conanrun")
                continue
            self._sign_ohos_elf(executable)
            # Document the dependency package as published: without the signed
            # platform client libraries the loader cannot map libpulse.so.0.
            try:
                self.run(f'"{executable}"', env="conanrun", quiet=True)
                self.output.info(f"{name}: plain conanrun run also succeeded")
            except ConanException:
                self.output.info(
                    f"{name}: plain conanrun run cannot resolve the unsigned "
                    "pulseaudio artifact (expected)"
                )
            self.run(
                f'LD_LIBRARY_PATH="{pulse_sys}:$LD_LIBRARY_PATH" "{executable}"',
                env="conanrun",
            )

    def _installed_libcanberra(self):
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        libdir = os.path.join(package_folder, "lib")
        if not os.path.isdir(libdir):
            raise ConanException(f"installed lib/ directory is missing: {libdir}")
        for entry in sorted(os.listdir(libdir)):
            if entry.startswith("libcanberra.so.") and not entry.endswith(".T"):
                return os.path.join(libdir, entry)
        raise ConanException(f"libcanberra.so.0 is missing from {libdir}")

    def _check_installed_library(self):
        """The shared library itself must pin the PulseAudio ABI it uses."""
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(readelf):
            raise ConanException("llvm-readelf is missing")
        library = self._installed_libcanberra()
        dynamic = subprocess.run(
            [readelf, "-d", library], check=True, capture_output=True, text=True, timeout=30
        ).stdout
        if "libpulse.so.0" not in dynamic:
            raise ConanException(
                f"libcanberra.so.0 does not link the PulseAudio client library: {library}"
            )
        if "libcanberra.so.0" not in dynamic:
            raise ConanException(f"libcanberra.so.0 SONAME is wrong: {library}")
        sections = subprocess.run(
            [readelf, "-SW", library], check=True, capture_output=True, text=True, timeout=30
        ).stdout
        if ".codesign" not in sections:
            raise ConanException(f"libcanberra.so.0 has no .codesign section: {library}")
        self.output.info(
            f"libcanberra.so.0 pins DT_NEEDED libpulse.so.0 (pulse backend compiled in): {library}"
        )

    def _platform_pulse_dir(self):
        """Symlink the signed platform PulseAudio clients under their SONAMEs."""
        directory = os.path.join(self.build_folder, "pulse-sys")
        os.makedirs(directory, exist_ok=True)
        for link, target in SIGNED_PLATFORM_LIBS.items():
            if not os.path.isfile(target):
                raise ConanException(
                    f"signed platform PulseAudio client library is missing: {target}"
                )
            path = os.path.join(directory, link)
            if os.path.islink(path) or os.path.exists(path):
                os.remove(path)
            os.symlink(target, path)
        return directory

    def _sign_ohos_elf(self, path):
        signer = shutil.which("binary-sign-tool") or (
            "/data/service/hnp/bin/binary-sign-tool"
        )
        readelf = shutil.which("llvm-readelf") or (
            "/data/service/hnp/bin/llvm-readelf"
        )
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("required OHOS signing tools are missing")
        temporary = f"{path}.signed"
        subprocess.run(
            [
                signer,
                "sign",
                "-inFile",
                path,
                "-outFile",
                temporary,
                "-selfSign",
                "1",
            ],
            check=True,
            timeout=60,
        )
        sections = subprocess.run(
            [readelf, "-SW", temporary],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException(f"signed consumer has invalid .codesign: {path}")
        os.chmod(temporary, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(temporary, path)
