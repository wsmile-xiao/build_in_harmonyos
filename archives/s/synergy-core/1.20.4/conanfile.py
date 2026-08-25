#!/usr/bin/env python3
"""Conan recipe for Synergy Core 1.20.4 on OpenHarmony PC."""

import os
import re
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    mkdir,
    rmdir,
)


required_conan_version = ">=2.0"


class SynergyCoreConan(ConanFile):
    name = "synergy-core"
    version = "1.20.4"
    description = "Keyboard and mouse sharing utility"
    license = "GPL-2.0-only WITH LicenseRef-OpenSSL-Exception"
    homepage = "https://symless.com/synergy"
    url = "https://github.com/symless/synergy"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("aws-lc/5.5.0")

    def validate(self):
        if self.settings.os != "OHOS":
            raise ConanInvalidConfiguration("This recipe targets OpenHarmony PC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

        extra = self.conan_data["synergy_extra"]
        get(
            self,
            **extra,
            strip_root=True,
            destination=os.path.join(self.source_folder, "ext", "synergy-extra"),
        )

        googletest = self.conan_data["test_sources"]["googletest"]
        get(
            self,
            **googletest,
            strip_root=True,
            destination=os.path.join(
                self.source_folder, "subprojects", "googletest-1.17.0"
            ),
        )

    def generate(self):
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        tc.generator = "Ninja"
        tc.variables["CMAKE_SYSTEM_NAME"] = "OHOS"
        tc.variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        tc.variables["BUILD_SHARED_LIBS"] = False
        tc.variables["BUILD_GUI"] = False
        tc.variables["BUILD_INSTALLER"] = False
        tc.variables["BUILD_TESTS"] = True
        tc.variables["BUILD_UNIFIED"] = True
        tc.variables["SYSTEM_GTEST"] = False
        tc.variables["ENABLE_COVERAGE"] = False
        tc.variables["USE_CLI11"] = False
        tc.variables["USE_TOMLPLUSPLUS"] = False
        tc.variables["SYNERGY_ENABLE_ACTIVATION"] = False
        tc.variables["SYNERGY_VERSION_CHECK"] = False
        tc.variables["SYNERGY_VERSION_RELEASE"] = True
        tc.variables["CMAKE_SKIP_RPATH"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        self.conf.define("tools.build:jobs", 1)
        cmake.build()
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        if not can_run(self):
            self.output.info(
                "cross-building: 174 upstream tests compiled for target execution"
            )
            return

        test_binaries = [
            os.path.join(self.build_folder, "bin", "unittests"),
            os.path.join(self.build_folder, "bin", "integtests"),
        ]
        self._sign_paths(test_binaries, required=True)

        test_tmpdir = os.path.join(self.build_folder, "upstream-test-tmp")
        rmdir(self, test_tmpdir)
        mkdir(self, test_tmpdir)
        test_env = Environment()
        test_env.define("TEST_TMPDIR", test_tmpdir)
        test_env.define("TMPDIR", test_tmpdir)
        test_env.define("TMPPREFIX", test_tmpdir)
        with test_env.vars(self).apply():
            for binary in test_binaries:
                report = os.path.join(
                    self.build_folder,
                    "{}.json".format(os.path.basename(binary)),
                )
                self.run(
                    shlex.join(
                        [
                            binary,
                            "--gtest_color=no",
                            f"--gtest_output=json:{report}",
                        ]
                    )
                )

    def package(self):
        CMake(self).install()
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        copy(
            self,
            "LICENSE_EXCEPTION",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

        packaged_binaries = [
            os.path.join(self.package_folder, "bin", "synergy-core")
        ]
        self._sign_paths(packaged_binaries, required=can_run(self))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]

    def _sign_paths(self, paths, required):
        paths = sorted(
            path
            for path in paths
            if os.path.isfile(path) and not os.path.islink(path)
        )
        if not paths:
            raise ConanException("No OHOS ELF executable was found to sign")

        objcopy = self._find_ohos_tool("objcopy", llvm=True)
        readelf = self._find_ohos_tool("readelf", llvm=True)
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not readelf or not signer:
            message = (
                "OHOS ELF signing requires llvm-objcopy, llvm-readelf, and "
                "binary-sign-tool"
            )
            if required:
                raise ConanInvalidConfiguration(message)
            self.output.warning(f"{message}; packaged executables remain unsigned")
            return

        for path in paths:
            self._sign_elf_atomically(path, objcopy, readelf, signer)

    def _sign_elf_atomically(self, path, objcopy, readelf, signer):
        with open(path, "rb") as stream:
            if stream.read(4) != b"\x7fELF":
                raise ConanException(f"Signing input is not an ELF file: {path}")

        original_mode = os.stat(path).st_mode & 0o777
        temporary = f"{path}.signing-{os.getpid()}"
        if os.path.lexists(temporary):
            raise ConanException(f"Signing temporary path already exists: {temporary}")

        try:
            shutil.copy2(path, temporary)
            sections = self._run_tool([readelf, "-SW", temporary])
            count = self._codesign_count(sections)
            if count > 1:
                raise ConanException(
                    f"Input ELF contains multiple .codesign sections: {path}"
                )
            if count == 1:
                self._run_tool(
                    [objcopy, "--remove-section", ".codesign", temporary]
                )
                if self._codesign_count(
                    self._run_tool([readelf, "-SW", temporary])
                ):
                    raise ConanException(
                        f"Unable to remove the existing .codesign section: {path}"
                    )

            self.run(
                shlex.join(
                    [
                        signer,
                        "sign",
                        "-inFile",
                        temporary,
                        "-outFile",
                        temporary,
                        "-selfSign",
                        "1",
                    ]
                ),
                quiet=True,
            )
            sections = self._run_tool([readelf, "-SW", temporary])
            sizes = re.findall(
                r"\]\s+\.codesign\s+\S+\s+\S+\s+\S+\s+([0-9a-fA-F]+)\s+",
                sections,
            )
            if (
                self._codesign_count(sections) != 1
                or len(sizes) != 1
                or int(sizes[0], 16) <= 0
            ):
                raise ConanException(
                    f"Signed ELF has an invalid .codesign section: {path}"
                )

            os.chmod(temporary, original_mode | 0o055)
            os.replace(temporary, path)
        finally:
            if os.path.lexists(temporary):
                os.remove(temporary)

    @staticmethod
    def _run_tool(arguments):
        completed = subprocess.run(
            arguments,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
        if completed.returncode != 0:
            raise ConanException(
                "OHOS ELF tool failed ({}): {}\n{}{}".format(
                    completed.returncode,
                    " ".join(arguments),
                    completed.stdout,
                    completed.stderr,
                )
            )
        return completed.stdout

    @staticmethod
    def _codesign_count(section_text):
        return sum(
            1
            for line in section_text.splitlines()
            if re.search(r"\]\s+\.codesign\s", line)
        )

    def _find_ohos_tool(self, tool, llvm=False):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compiler_executables.get("cpp") or compiler_executables.get(
            "c", ""
        )
        compiler_path = shutil.which(compiler) or compiler
        compiler_dir = os.path.dirname(compiler_path)
        compiler_name = os.path.basename(compiler_path)
        version_suffix = (
            compiler_name[len("clang") :]
            if compiler_name.startswith("clang")
            else ""
        )

        candidates = [compiler_executables.get(tool)]
        names = []
        if llvm:
            if version_suffix:
                names.append(f"llvm-{tool}{version_suffix}")
            names.append(f"llvm-{tool}")
        else:
            names.append(tool)
        for name in names:
            if compiler_dir:
                candidates.append(os.path.join(compiler_dir, name))
            candidates.append(os.path.join("/data/service/hnp/bin", name))
            candidates.append(name)

        for candidate in candidates:
            if not candidate:
                continue
            resolved = shutil.which(candidate) or candidate
            if os.path.isfile(resolved):
                return os.path.abspath(resolved)
        return ""
