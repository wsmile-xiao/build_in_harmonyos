#!/usr/bin/env python3
"""Conan recipe for libffi 3.5.2 (Autotools, static-only)."""

import hashlib
import os
from pathlib import Path, PurePosixPath
import shlex
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import build_jobs, can_run
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    check_sha256,
    copy,
    download,
    export_conandata_patches,
    replace_in_file,
    rm,
    rmdir,
    unzip,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.microsoft import unix_path


class LibffiConan(ConanFile):
    win_bash = True
    name = "libffi"
    version = "3.5.2"
    description = "Portable Foreign Function Interface library"
    license = "MIT"
    homepage = "https://github.com/libffi/libffi"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}
    exports_sources = "run_upstream_tests.py"
    _no_autotools_regeneration = (
        "MAKE=make",
        "AUTOCONF=true",
        "AUTOHEADER=true",
        "AUTOMAKE=true",
        "ACLOCAL=true",
    )
    _generated_autotools_files = (
        "aclocal.m4",
        "configure",
        "fficonfig.h.in",
        "Makefile.in",
        "include/Makefile.in",
        "testsuite/Makefile.in",
        "man/Makefile.in",
        "doc/Makefile.in",
    )
    _configured_build_scripts = {
        "config.status": 13,
        "Makefile": 11,
        "include/Makefile": 11,
        "testsuite/Makefile": 11,
        "man/Makefile": 11,
        "doc/Makefile": 11,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def validate(self):
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                "libffi's OHOS adaptation is validated only for armv8/AArch64"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        source = self.conan_data["sources"]
        source_archive = os.path.join(
            self.source_folder, "libffi-3.5.2.tar.gz"
        )
        configured_archive = self.conf.get(
            "user.libffi:source_archive", default=None
        )
        if configured_archive:
            configured_archive = os.path.abspath(os.fspath(configured_archive))
            if not os.path.isfile(configured_archive):
                raise ConanInvalidConfiguration(
                    "user.libffi:source_archive does not name a regular file"
                )
            check_sha256(self, configured_archive, source["sha256"])
            if os.path.normcase(configured_archive) != os.path.normcase(
                os.path.abspath(source_archive)
            ):
                shutil.copy2(configured_archive, source_archive)
            check_sha256(self, source_archive, source["sha256"])
        else:
            download(
                self,
                source["url"],
                source_archive,
                sha256=source["sha256"],
            )
        unzip(self, source_archive, destination=self.source_folder, strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.settings.os == "OHOS":
            tc.extra_cflags.append("-funwind-tables")
        tc.configure_args.extend(
            [
                "--disable-shared",
                "--enable-static",
                "--disable-multi-os-directory",
                "--disable-dependency-tracking",
            ]
        )
        tc.generate()

    @staticmethod
    def _resolve_executable(value, label):
        if not value:
            raise ConanInvalidConfiguration(f"missing {label} executable")
        if os.path.isfile(value):
            return value
        parts = shlex.split(value)
        if len(parts) != 1:
            raise ConanInvalidConfiguration(
                f"{label} compiler_executables entry must be an executable path"
            )
        resolved = shutil.which(parts[0])
        if not resolved:
            raise ConanInvalidConfiguration(f"cannot find {label}: {parts[0]}")
        return resolved

    def _resolve_companion_tool(self, compiler, base_name, configured=None):
        if configured:
            return self._resolve_executable(configured, base_name)
        compiler_path = Path(compiler)
        compiler_stem = compiler_path.stem
        executable_suffix = compiler_path.suffix
        version_suffix = ""
        if compiler_stem.startswith("clang-"):
            version_suffix = compiler_stem[len("clang"):]
        names = []
        if version_suffix:
            names.append(f"{base_name}{version_suffix}{executable_suffix}")
        names.append(f"{base_name}{executable_suffix}")
        if executable_suffix:
            names.append(base_name)
        for name in names:
            adjacent = compiler_path.with_name(name)
            if adjacent.is_file():
                return str(adjacent)
            resolved = shutil.which(name)
            if resolved:
                return resolved
        raise ConanInvalidConfiguration(
            f"cannot find {base_name} next to compiler or on PATH"
        )

    def _refresh_generated_timestamps(self):
        release_baseline = 946684800
        for directory, _, filenames in os.walk(self.source_folder):
            for filename in filenames:
                os.utime(
                    os.path.join(directory, filename),
                    (release_baseline, release_baseline),
                )
        for relative in self._generated_autotools_files:
            path = os.path.join(self.source_folder, relative)
            if not os.path.isfile(path):
                raise ConanInvalidConfiguration(
                    f"missing release-generated Autotools file: {relative}"
                )
            os.utime(path, None)

    def _autotools_make_args(self):
        source_root = Path(self.source_folder).as_posix().rstrip("/")
        build_root = Path(self.build_folder).as_posix().rstrip("/")
        return ["--environment-overrides"] + [
            f"--old-file={build_root}/config.status",
        ] + [
            f"--old-file={source_root}/{PurePosixPath(relative).as_posix()}"
            for relative in self._generated_autotools_files
        ]

    def _normalize_configured_paths(self):
        unix_root = unix_path(self, self.source_folder).rstrip("/")
        native_root = Path(self.source_folder).as_posix().rstrip("/")
        if unix_root == native_root:
            return
        for relative, expected_count in self._configured_build_scripts.items():
            path = os.path.join(self.build_folder, relative)
            content = Path(path).read_text(encoding="utf-8")
            actual_count = content.count(unix_root)
            if actual_count != expected_count:
                raise ConanInvalidConfiguration(
                    f"unexpected {relative} source-root count: "
                    f"expected {expected_count}, found {actual_count}"
                )
            replace_in_file(
                self,
                path,
                unix_root,
                native_root,
                strict=True,
            )
            if unix_root in Path(path).read_text(encoding="utf-8"):
                raise ConanInvalidConfiguration(
                    f"source-root replacement left a residue in {relative}"
                )

    def _source_content_digest(self):
        digest = hashlib.sha256()
        source_root = Path(self.source_folder).resolve()
        build_root = Path(self.build_folder).resolve()
        for path in sorted(source_root.rglob("*"), key=lambda item: item.as_posix()):
            if not path.is_file() or path == build_root or build_root in path.parents:
                continue
            relative = path.relative_to(source_root).as_posix().encode("utf-8")
            digest.update(len(relative).to_bytes(4, "big"))
            digest.update(relative)
            with path.open("rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
        return digest.hexdigest()

    def _autotools_environment(self):
        environment = Environment()
        for assignment in self._no_autotools_regeneration:
            name, value = assignment.split("=", 1)
            environment.define(name, value)
        environment.define("MAKEFLAGS", "--environment-overrides")
        environment.define("MAKE", "make " + " ".join(self._autotools_make_args()))
        return environment.vars(self)

    def build(self):
        apply_conandata_patches(self)
        self._refresh_generated_timestamps()
        autotools = Autotools(self)
        autotools.configure()
        if self.settings.os == "OHOS":
            config_header = Path(self.build_folder) / "fficonfig.h"
            cfi_define = "#define HAVE_AS_CFI_PSEUDO_OP 1"
            if config_header.read_text(encoding="utf-8").count(cfi_define) != 1:
                raise ConanInvalidConfiguration(
                    "OHOS AArch64 requires assembler call-frame information"
                )
        source_digest = self._source_content_digest()
        self._normalize_configured_paths()
        if self._source_content_digest() != source_digest:
            raise ConanInvalidConfiguration(
                "generated-path normalization changed source file content"
            )
        with self._autotools_environment().apply():
            autotools.make(args=self._autotools_make_args())

        if self.settings.os == "OHOS":
            runner = os.path.join(self.source_folder, "run_upstream_tests.py")
            archive = os.path.join(self.source_folder, "libffi-3.5.2.tar.gz")
            command = [
                sys.executable,
                runner,
                "--root",
                self.source_folder,
                "--archive",
                archive,
            ]
            if not can_run(self):
                self.output.info(
                    "NOT_RUN LIBFFI_TARGET_UPSTREAM=0/363 "
                    "reason=cross_building; discovery=363/726 required"
                )
                command.append("--discovery-only")
                self.run(
                    " ".join(shlex.quote(argument) for argument in command),
                    env="conanbuild",
                )
                return

            library = os.path.join(self.build_folder, ".libs", "libffi.a")
            digest = hashlib.sha256()
            with open(library, "rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)

            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
            cc = compilers.get("c")
            cxx = compilers.get("cpp")
            cc_path = self._resolve_executable(cc, "C compiler")
            cxx_path = self._resolve_executable(cxx, "C++ compiler")
            objcopy = self._resolve_companion_tool(
                cc_path,
                "llvm-objcopy",
                compilers.get("objcopy")
                or self.conf.get("user.libffi:objcopy", default=None),
            )
            signer = self._resolve_companion_tool(
                cc_path,
                "binary-sign-tool",
                self.conf.get("user.libffi:signer", default=None),
            )
            output = os.path.join(self.build_folder, "upstream-test-results")
            command.extend(
                [
                    "--build",
                    self.build_folder,
                    "--output",
                    output,
                    "--expected-libffi-sha256",
                    digest.hexdigest(),
                    "--jobs",
                    str(min(build_jobs(self), 8)),
                    "--clang",
                    cc_path,
                    "--clangxx",
                    cxx_path,
                    "--objcopy",
                    objcopy,
                    "--signer",
                    signer,
                ]
            )
            self.run(
                " ".join(shlex.quote(argument) for argument in command),
                env="conanbuild",
            )

    def package(self):
        with self._autotools_environment().apply():
            Autotools(self).install(args=self._autotools_make_args())
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["ffi"]
        self.cpp_info.set_property("cmake_file_name", "libffi")
        self.cpp_info.set_property("cmake_target_name", "libffi::libffi")
        self.cpp_info.set_property("pkg_config_name", "libffi")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
