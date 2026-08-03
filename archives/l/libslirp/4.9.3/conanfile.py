#!/usr/bin/env python3
"""Conan recipe for libslirp 4.9.3."""

import os
import shlex
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import build_jobs, can_run
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import MesonToolchain


class LibslirpConan(ConanFile):
    name = "libslirp"
    version = "4.9.3"
    description = "User-mode TCP/IP stack used by virtual machines and tools"
    license = "BSD-3-Clause"
    homepage = "https://gitlab.freedesktop.org/slirp/libslirp"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires(
            "glib/2.84.0",
            transitive_headers=True,
            transitive_libs=True,
        )

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def _resolve_tool(self, tool):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler = compiler_executables.get("c", "")
        compiler_path = shutil.which(compiler) or compiler
        compiler_dir = os.path.dirname(compiler_path)
        compiler_name = os.path.basename(compiler_path)
        version_suffix = (
            compiler_name[len("clang") :]
            if compiler_name.startswith("clang")
            else ""
        )

        candidates = [compiler_executables.get(tool)]
        if compiler_dir:
            candidates.extend(
                [
                    os.path.join(
                        compiler_dir, f"llvm-{tool}{version_suffix}"
                    ),
                    os.path.join(compiler_dir, f"llvm-{tool}"),
                    os.path.join(compiler_dir, tool),
                ]
            )
        if version_suffix:
            candidates.append(f"llvm-{tool}{version_suffix}")
        candidates.extend((f"llvm-{tool}", tool))

        for candidate in candidates:
            if candidate:
                resolved = shutil.which(candidate)
                if resolved:
                    return resolved

        raise ConanInvalidConfiguration(
            f"required build tool was not found: {tool}"
        )

    def generate(self):
        PkgConfigDeps(self).generate()
        toolchain = MesonToolchain(self)
        toolchain.project_options["default_library"] = (
            "shared" if self.options.shared else "static"
        )
        toolchain.project_options["static"] = not bool(self.options.shared)
        toolchain.project_options["wrap_mode"] = "nodownload"
        toolchain.pkg_config_path = self.generators_folder
        toolchain.generate()

        if self.settings.os in ("Linux", "OHOS"):
            ar = self._resolve_tool("ar")
            ranlib = self._resolve_tool("ranlib")
            native_file = os.path.join(
                self.generators_folder, MesonToolchain.native_filename
            )
            if os.path.isfile(native_file):
                with open(native_file, encoding="utf-8") as handle:
                    content = handle.read()
                if "\nar =" not in content and "[binaries]" in content:
                    archive_tools = (
                        "[binaries]\nar = '{}'\nranlib = '{}'\n".format(
                            ar, ranlib
                        )
                    )
                    content = content.replace(
                        "[binaries]\n", archive_tools, 1
                    )
                    with open(native_file, "w", encoding="utf-8") as handle:
                        handle.write(content)

    def build(self):
        self._run_meson(
            "setup "
            f"{self._meson_machine_args()} "
            f"{shlex.quote(self.build_folder)} "
            f"{shlex.quote(self.source_folder)} --prefix=/"
        )
        self._run_meson(
            f"compile -C {shlex.quote(self.build_folder)} "
            f"-j{build_jobs(self)}"
        )
        if can_run(self):
            if str(self.settings.os) == "OHOS":
                if self.options.shared:
                    self._sign_elf_for_ohos(
                        os.path.join(self.build_folder, "libslirp.so")
                    )
                for test_name in ("pingtest", "ncsitest"):
                    self._sign_elf_for_ohos(
                        os.path.join(self.build_folder, test_name)
                    )
            self._run_meson(
                f"test -C {shlex.quote(self.build_folder)} "
                "--no-rebuild --print-errorlogs"
            )

    def package(self):
        self._run_meson(
            f"install -C {shlex.quote(self.build_folder)} "
            f"--destdir {shlex.quote(self.package_folder)}"
        )
        if str(self.settings.os) == "OHOS" and self.options.shared:
            self._sign_elf_for_ohos(
                os.path.join(self.package_folder, "lib", "libslirp.so")
            )

    def _sign_elf_for_ohos(self, path):
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        readelf = "/data/service/hnp/bin/llvm-readelf"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(path):
            raise ConanInvalidConfiguration(f"ELF input is missing: {path}")
        if any(not os.path.isfile(tool) for tool in (objcopy, readelf, signer)):
            raise ConanInvalidConfiguration(
                "HarmonyOS ELF signing tools are required for target execution"
            )

        clean_path = f"{path}.codesign-clean"
        signed_path = f"{path}.signed"
        for temporary in (clean_path, signed_path):
            if os.path.exists(temporary):
                os.remove(temporary)
        try:
            self.run(
                f"{shlex.quote(objcopy)} --remove-section .codesign "
                f"{shlex.quote(path)} {shlex.quote(clean_path)}"
            )
            self.run(
                f"{shlex.quote(signer)} sign -inFile {shlex.quote(clean_path)} "
                f"-outFile {shlex.quote(signed_path)} -selfSign 1"
            )
            sections = subprocess.run(
                [readelf, "-SW", signed_path],
                check=True,
                capture_output=True,
                text=True,
                timeout=30,
            ).stdout
            if sections.count(".codesign") != 1:
                raise ConanInvalidConfiguration(
                    f"signed ELF has invalid .codesign count: {path}"
                )
            os.remove(path)
            os.replace(signed_path, path)
            os.chmod(path, 0o755)
        finally:
            for temporary in (clean_path, signed_path):
                if os.path.exists(temporary):
                    os.remove(temporary)

    def _meson_machine_args(self):
        arguments = []
        cross_file = os.path.join(
            self.generators_folder, MesonToolchain.cross_filename
        )
        native_file = os.path.join(
            self.generators_folder, MesonToolchain.native_filename
        )
        if os.path.isfile(cross_file):
            arguments.extend(("--cross-file", shlex.quote(cross_file)))
        if os.path.isfile(native_file):
            arguments.extend(("--native-file", shlex.quote(native_file)))
        if not arguments:
            raise ConanInvalidConfiguration("Meson machine file is missing")
        return " ".join(arguments)

    def _run_meson(self, arguments):
        python = shlex.quote(sys.executable)
        self.run(f"{python} -m mesonbuild.mesonmain {arguments}")

    def package_info(self):
        self.cpp_info.libs = ["slirp"]
        self.cpp_info.requires = ["glib::glib"]
        self.cpp_info.includedirs = ["include", "include/slirp"]
        self.cpp_info.set_property("cmake_file_name", "libslirp")
        self.cpp_info.set_property("cmake_target_name", "libslirp::slirp")
        self.cpp_info.set_property("pkg_config_name", "slirp")
        if self.settings.os == "Windows":
            self.cpp_info.system_libs = ["ws2_32", "iphlpapi"]
