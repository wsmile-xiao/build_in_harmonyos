#!/usr/bin/env python3
"""Conan consumer tests for PCRE2 10.48 libraries and command-line tools."""

import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class Pcre2TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        package_root = self.dependencies["pcre2"].package_folder
        toolchain = CMakeToolchain(self)
        toolchain.variables["PCRE2_PACKAGE_ROOT"] = package_root.replace("\\", "/")
        toolchain.variables["PCRE2_PKGCONFIG_DIR"] = os.path.join(
            package_root, "lib", "pkgconfig"
        ).replace("\\", "/")
        toolchain.variables["PKG_CONFIG_EXECUTABLE"] = self._pkg_config()
        toolchain.generate()

    def _require_package_artifacts(self):
        dependency = self.dependencies["pcre2"]
        package_folder = dependency.package_folder
        required = [
            os.path.join(package_folder, "include", "pcre2.h"),
            os.path.join(package_folder, "include", "pcre2posix.h"),
            os.path.join(package_folder, "lib", "libpcre2-8.a"),
            os.path.join(package_folder, "lib", "libpcre2-16.a"),
            os.path.join(package_folder, "lib", "libpcre2-32.a"),
            os.path.join(package_folder, "lib", "libpcre2-posix.a"),
            os.path.join(package_folder, "bin", "pcre2grep"),
            os.path.join(package_folder, "bin", "pcre2test"),
            os.path.join(package_folder, "bin", "pcre2-config"),
        ]
        required.extend(
            os.path.join(package_folder, "lib", "pkgconfig", pc_name)
            for pc_name in (
                "libpcre2-8.pc",
                "libpcre2-16.pc",
                "libpcre2-32.pc",
                "libpcre2-posix.pc",
            )
        )
        missing = [path for path in required if not os.path.isfile(path)]
        if missing:
            raise ConanInvalidConfiguration(
                "PCRE2 package artifacts are missing: " + ", ".join(missing)
            )
        libtool_archives = []
        for root, _, files in os.walk(os.path.join(package_folder, "lib")):
            libtool_archives.extend(
                os.path.join(root, name) for name in files if name.endswith(".la")
            )
        if libtool_archives:
            raise ConanInvalidConfiguration(
                "PCRE2 package contains non-relocatable libtool metadata: "
                + ", ".join(libtool_archives)
            )
        return {
            "pcre2grep": os.path.join(package_folder, "bin", "pcre2grep"),
            "pcre2test": os.path.join(package_folder, "bin", "pcre2test"),
            "pcre2-config": os.path.join(package_folder, "bin", "pcre2-config"),
        }

    def _pkg_config(self):
        candidates = [
            os.environ.get("PKG_CONFIG"),
            shutil.which("pkg-config"),
            shutil.which("pkgconf"),
        ]
        if str(self.settings.os) == "OHOS":
            candidates.append(
                "/data/service/hnp/pkg-config.org/pkg-config_0.29.2/bin/pkg-config"
            )
        for candidate in candidates:
            if not candidate or not os.path.isfile(candidate):
                continue
            try:
                probe = subprocess.run(
                    [candidate, "--version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=10,
                    check=False,
                )
            except (OSError, subprocess.TimeoutExpired):
                continue
            if probe.returncode == 0 and probe.stdout.strip():
                return candidate
        raise ConanInvalidConfiguration("No runnable pkg-config implementation found")

    @staticmethod
    def _config_shell():
        candidates = [
            "/system/bin/sh",
            shutil.which("sh"),
            shutil.which("bash"),
            "/bin/sh",
        ]
        for candidate in candidates:
            if (
                candidate
                and os.path.isfile(candidate)
                and os.access(candidate, os.X_OK)
            ):
                return candidate
        raise ConanInvalidConfiguration("No executable shell for pcre2-config")

    @staticmethod
    def _capture(command, environment=None):
        try:
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=30,
                check=False,
                env=environment,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise ConanInvalidConfiguration(
                f"Metadata command failed to execute: {command}: {error}"
            ) from error
        if result.returncode != 0 or result.stderr:
            raise ConanInvalidConfiguration(
                f"Metadata command failed: {command}: "
                f"rc={result.returncode}, stderr={result.stderr.strip()}"
            )
        return result.stdout.strip()

    @staticmethod
    def _contains_path_flag(tokens, flag, expected_path):
        expected_real = os.path.realpath(expected_path)
        return any(
            token.startswith(flag)
            and os.path.realpath(token[len(flag) :]) == expected_real
            for token in tokens
        )

    def _verify_discovery_metadata(self, artifacts):
        package_root = self.dependencies["pcre2"].package_folder
        expected_root = os.path.realpath(package_root)
        pkgconfig_dir = os.path.join(package_root, "lib", "pkgconfig")
        environment = os.environ.copy()
        environment["PKG_CONFIG_PATH"] = pkgconfig_dir

        pkg_config = self._pkg_config()
        pc_prefix = self._capture(
            [pkg_config, "--variable=prefix", "libpcre2-8"], environment
        )
        if os.path.realpath(pc_prefix) != expected_root:
            raise ConanInvalidConfiguration(
                f"pkg-config prefix escapes the package: {pc_prefix}"
            )
        pc_cflags = shlex.split(
            self._capture([pkg_config, "--cflags", "libpcre2-8"], environment)
        )
        pc_libs = shlex.split(
            self._capture([pkg_config, "--libs", "--static", "libpcre2-8"], environment)
        )
        expected_include = os.path.join(package_root, "include")
        expected_libdir = os.path.join(package_root, "lib")
        if (
            not self._contains_path_flag(pc_cflags, "-I", expected_include)
            or "-DPCRE2_STATIC" not in pc_cflags
        ):
            raise ConanInvalidConfiguration(
                f"pkg-config returned unexpected Cflags: {pc_cflags}"
            )
        if (
            not self._contains_path_flag(pc_libs, "-L", expected_libdir)
            or "-lpcre2-8" not in pc_libs
        ):
            raise ConanInvalidConfiguration(
                f"pkg-config returned unexpected static Libs: {pc_libs}"
            )

        config = artifacts["pcre2-config"]
        shell = self._config_shell()
        config_prefix = self._capture([shell, config, "--prefix"])
        if os.path.realpath(config_prefix) != expected_root:
            raise ConanInvalidConfiguration(
                f"pcre2-config prefix escapes the package: {config_prefix}"
            )
        config_cflags = shlex.split(self._capture([shell, config, "--cflags"]))
        config_libs = shlex.split(self._capture([shell, config, "--libs8"]))
        if (
            not self._contains_path_flag(config_cflags, "-I", expected_include)
            or "-DPCRE2_STATIC" not in config_cflags
        ):
            raise ConanInvalidConfiguration(
                f"pcre2-config returned unexpected Cflags: {config_cflags}"
            )
        if (
            not self._contains_path_flag(config_libs, "-L", expected_libdir)
            or "-lpcre2-8" not in config_libs
        ):
            raise ConanInvalidConfiguration(
                f"pcre2-config returned unexpected Libs: {config_libs}"
            )
        self.output.info("PCRE2_METADATA_RELOCATION=6/6")

    def build(self):
        artifacts = self._require_package_artifacts()
        self._verify_discovery_metadata(artifacts)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        artifacts = self._require_package_artifacts()
        self._verify_discovery_metadata(artifacts)
        if not can_run(self):
            self.output.info("Target binaries cannot run in this configuration")
            return

        cmake = CMake(self)
        cmake.ctest(cli_args=["--output-on-failure"])

        fixture = os.path.join(self.source_folder, "grep-input.txt")
        self.run(
            "{} -q {} {}".format(
                shlex.quote(artifacts["pcre2grep"]),
                shlex.quote("^alpha-[0-9]+$"),
                shlex.quote(fixture),
            ),
            env="conanrun",
        )
        self.run(
            "{} -C".format(shlex.quote(artifacts["pcre2test"])),
            env="conanrun",
        )
