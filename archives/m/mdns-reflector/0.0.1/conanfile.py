#!/usr/bin/env python3
"""Conan recipe for mdns-reflector 0.0.1.

mdns-reflector is a lightweight multicast DNS (mDNS) reflector by
Yuxiang Zhu (upstream https://github.com/pbkhrv/mdns-reflector).  It is a
single pure-C executable built with CMake (>= 3.14) using only libc
sockets (IPv4/IPv6 multicast, epoll on Linux, kqueue on BSD/macOS).

Upstream has no git tag for 0.0.1; the version comes from
mdns-reflector.spec (`Version: 0.0.1`) and matches the Debian packaging
`0.0.1+git20230914.4b4cd3b-2.1`.  The source archive is therefore pinned
to commit 4b4cd3b196f09b507d9a32c7488491bbd5071ba6, the exact commit
Debian packaged for the 0.0.1 series.

Upstream ships no test suite (no tests/ directory, no add_test /
enable_testing in either CMakeLists.txt); see notes.md for the inventory
evidence.  As an in-build smoke check the freshly built binary is run
with `-h` and must print the version banner and usage, and an
argument-less invocation must exit non-zero.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class MdnsReflectorConan(ConanFile):
    name = "mdns-reflector"
    version = "0.0.1"
    description = "Lightweight and performant multicast DNS (mDNS) reflector with zone based reflection and IPv6 support"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/pbkhrv/mdns-reflector"
    url = "https://github.com/pbkhrv/mdns-reflector"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.ref} supports native Linux/OHOS builds only"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def _built_binary(self):
        candidate = os.path.join(self.build_folder, "src", "mdns-reflector")
        if not os.path.isfile(candidate):
            candidate = os.path.join(self.build_folder, "mdns-reflector")
        if not os.path.isfile(candidate):
            raise ConanInvalidConfiguration(
                "the build did not produce the mdns-reflector executable"
            )
        return candidate

    def _run_smoke_check(self, binary):
        # Upstream test-suite inventory (see notes.md): 0 tests shipped.
        # Smoke checks below are our own, they exercise argv parsing only
        # and need no network interfaces or multicast permissions.
        result = subprocess.run(
            [binary, "-h"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            raise ConanInvalidConfiguration(
                f"mdns-reflector -h exited {result.returncode}: {result.stderr}"
            )
        if "mDNS Reflector version" not in result.stdout:
            raise ConanInvalidConfiguration(
                f"unexpected -h output: {result.stdout!r}"
            )
        result = subprocess.run(
            [binary],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            raise ConanInvalidConfiguration(
                "mdns-reflector without arguments should fail (usage error)"
            )

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # No upstream test suite exists; run the smoke checks instead.
        self._run_smoke_check(self._built_binary())

    def _sign_ohos_elf(self, path):
        if str(self.settings.os) != "OHOS":
            return
        objcopy = (
            shutil.which("llvm-objcopy")
            or "/data/service/hnp/bin/llvm-objcopy"
        )
        signer = (
            shutil.which("binary-sign-tool")
            or "/data/service/hnp/bin/binary-sign-tool"
        )
        if os.path.isfile(objcopy):
            subprocess.run(
                [objcopy, "--remove-section", ".codesign", path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        if not os.path.isfile(signer):
            self.output.warning(
                "binary-sign-tool not found; skipping OHOS ELF self-signing"
            )
            return
        signed = path + ".signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", signed,
             "-selfSign", "1"],
            check=True,
        )
        os.replace(signed, path)
        os.chmod(path, 0o755)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        binary = os.path.join(self.package_folder, "bin", "mdns-reflector")
        if not os.path.isfile(binary):
            raise ConanInvalidConfiguration(
                f"install did not place the executable at {binary}"
            )
        self._sign_ohos_elf(binary)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # Command-line tool: expose the bin dir for consumers.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
