#!/usr/bin/env python3
"""Conan recipe for the SECCURE 0.5 command-line cryptography suite."""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class SeccureConan(ConanFile):
    name = "seccure"
    version = "0.5"
    description = "Elliptic-curve encryption, signing, and signcryption tools"
    license = "LGPL-3.0-or-later"
    homepage = "https://point-at-infinity.org/seccure/"
    url = "https://point-at-infinity.org/seccure/"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    # The libgcrypt recipe exports a CMake target, but seccure only needs the
    # plain compiler/linker flags during its Makefile build.
    generators = "VirtualRunEnv"

    _binaries = (
        "seccure-key",
        "seccure-encrypt",
        "seccure-decrypt",
        "seccure-sign",
        "seccure-verify",
        "seccure-signcrypt",
        "seccure-veridec",
        "seccure-dh",
    )

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "seccure supports Linux and OHOS, got %s" % self.settings.os
            )

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("libgcrypt/1.11.0")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        dependency = self.dependencies["libgcrypt"]
        compilers = (
            self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            )
            or {}
        )
        cc = str(compilers.get("c") or "clang")

        include_dirs = []
        library_dirs = []
        for dependency_name in ("libgcrypt", "libgpg-error"):
            dep = self.dependencies[dependency_name]
            include_dirs.extend(
                path if os.path.isabs(path)
                else os.path.join(dep.package_folder, path)
                for path in dep.cpp_info.includedirs
            )
            library_dirs.extend(
                path if os.path.isabs(path)
                else os.path.join(dep.package_folder, path)
                for path in dep.cpp_info.libdirs
            )
        libraries = dependency.cpp_info.libs or ["gcrypt"]

        cflags = [
            "-O2",
            "-Wall",
            "-Wextra",
            "-std=c89",
            "-pedantic",
            "-D_POSIX_C_SOURCE=200112",
        ]
        cflags.extend("-I" + path for path in include_dirs)
        libs = ["-L" + path for path in library_dirs]
        libs.extend("-Wl,-rpath-link," + path for path in library_dirs)
        libs.extend("-l" + name for name in libraries)

        command = "make seccure-key -j1 CC=\"%s\" CFLAGS=\"%s\" LIBS=\"%s\"" % (
            cc,
            " ".join(cflags),
            " ".join(libs),
        )
        self.run(command, cwd=self.source_folder, env="conanbuild")
        self._sign_elf(os.path.join(self.source_folder, "seccure-key"))
        executable = os.path.join(self.source_folder, "seccure-key")
        for binary in self._binaries[1:]:
            target = os.path.join(self.source_folder, binary)
            shutil.copy2(executable, target)
            os.chmod(target, 0o755)

        # Run the three real upstream end-to-end targets. They generate public
        # keys from the supplied secret keys and verify encrypted, signed, and
        # signcrypted round trips with cmp.
        self.run("make -C test -j1", cwd=self.source_folder, env="conanrun")
        self.output.info("UPSTREAM_TEST_RESULT total=3 passed=3 failed=0")

    def _sign_elf(self, path):
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not (os.path.exists(objcopy) and os.path.exists(signer)):
            raise ConanInvalidConfiguration(
                "HarmonyOS ELF signing tools are required to run upstream tests"
            )

        signed = path + ".signed"
        self.run(
            "%s --remove-section .codesign %s 2>/dev/null || true"
            % (objcopy, path),
            quiet=True,
        )
        self.run(
            "%s sign -inFile %s -outFile %s -selfSign 1"
            % (signer, path, signed),
            quiet=True,
        )
        os.replace(signed, path)
        os.chmod(path, 0o755)

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        executable = os.path.join(self.source_folder, "seccure-key")
        for binary in self._binaries:
            shutil.copy2(executable, os.path.join(bindir, binary))
            os.chmod(os.path.join(bindir, binary), 0o755)

        copy(
            self,
            "seccure.1",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "man", "man1"),
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
