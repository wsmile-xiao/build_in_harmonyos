#!/usr/bin/env python3
"""Conan recipe for shntool 3.0.10."""
import os
import shlex
import shutil
import subprocess
import struct

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class ShntoolConan(ConanFile):
    name = "shntool"
    version = "3.0.10"
    description = "Multi-purpose WAVE data processing and reporting utility"
    license = "GPL-2.0-or-later"
    homepage = "http://shnutils.freeshell.org/shntool/"
    url = ""
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _run_checked(self, command, **kwargs):
        retcode = self.run(command, ignore_errors=True, **kwargs)
        if retcode is None or retcode != 0:
            raise RuntimeError(f"Command failed with exit code {retcode}: {command}")

    def _process_output(self, result):
        stdout = result.stdout.decode(errors="replace") if isinstance(result.stdout, bytes) else result.stdout
        stderr = result.stderr.decode(errors="replace") if isinstance(result.stderr, bytes) else result.stderr
        detail = "\n".join(part.strip() for part in (stdout, stderr) if part and part.strip())
        return detail[-2000:] if detail else "<no output>"

    def _patch_configure_umask(self):
        configure_path = os.path.join(self.source_folder, "configure")
        with open(configure_path, "r", encoding="utf-8") as handle:
            content = handle.read()
        patched = content
        replacements = (
            (
                '(umask 077 && mktemp -d "./confXXXXXX")',
                '(umask 022 && mktemp -d "./confXXXXXX")',
            ),
            (
                '(umask 077 && mkdir "$tmp")',
                '(umask 022 && mkdir "$tmp")',
            ),
        )
        found_original = False
        for original, replacement in replacements:
            if original in patched:
                found_original = True
                patched = patched.replace(original, replacement)
        if not found_original:
            if any(replacement in content for _, replacement in replacements):
                return
            raise RuntimeError("Expected Autoconf umask patterns were not found")
        with open(configure_path, "w", encoding="utf-8") as handle:
            handle.write(patched)

    def _elf_has_section(self, path, section_name):
        try:
            with open(path, "rb") as file:
                data = file.read()
        except OSError:
            return True
        if len(data) < 16 or data[:4] != b"\x7fELF":
            return True
        endian = {"\x01": "<", "\x02": ">"}.get(chr(data[5]))
        if not endian:
            return True
        try:
            if data[4] == 1:
                fields = struct.unpack_from(endian + "16sHHIIIIIHHHHHH", data, 0)
                section_header_format = endian + "IIIIIIIIII"
            elif data[4] == 2:
                fields = struct.unpack_from(endian + "16sHHIQQQIHHHHHH", data, 0)
                section_header_format = endian + "IIQQQQIIQQ"
            else:
                return True
            section_offset, section_size = fields[6], fields[11]
            section_count, names_index = fields[12], fields[13]
            header_size = struct.calcsize(section_header_format)
            if section_size < header_size or names_index >= section_count:
                return True

            def section_header(index):
                return struct.unpack_from(
                    section_header_format,
                    data,
                    section_offset + index * section_size,
                )

            names_header = section_header(names_index)
            names_offset, names_size = names_header[4], names_header[5]
            names = data[names_offset:names_offset + names_size]
            for index in range(section_count):
                name_offset = section_header(index)[0]
                if name_offset >= len(names):
                    continue
                end = names.find(b"\x00", name_offset)
                if end == -1:
                    continue
                if names[name_offset:end].decode(errors="replace") == section_name:
                    return True
        except (struct.error, IndexError):
            return True
        return False

    def build(self):
        apply_conandata_patches(self)
        if str(self.settings.os) == "OHOS":
            self._patch_configure_umask()

        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c")
        if not cc:
            if cross_building(self):
                raise ConanInvalidConfiguration(
                    "Cross builds require tools.build:compiler_executables[c] "
                    "to select the target compiler"
                )
            cc = str(self.settings.compiler)
        shell = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "sh"
        build_type_flags = {
            "Debug": "-O0 -g",
            "Release": "-O2 -DNDEBUG",
            "RelWithDebInfo": "-O2 -g -DNDEBUG",
            "MinSizeRel": "-Os -DNDEBUG",
        }
        build_type = str(self.settings.get_safe("build_type") or "Release")
        cflags = f"-fPIC {build_type_flags.get(build_type, build_type_flags['Release'])}"
        quoted_shell = shlex.quote(shell)
        quoted_cc = shlex.quote(cc)
        quoted_cflags = shlex.quote(cflags)

        self._run_checked(
            f"umask 022 && CONFIG_SHELL={quoted_shell} SHELL={quoted_shell} "
            f'./configure --prefix=/ '
            f"CC={quoted_cc} CFLAGS={quoted_cflags}",
            cwd=self.source_folder,
        )
        self._run_checked(
            f"make SHELL={quoted_shell} -j1",
            cwd=self.source_folder,
        )

    def package(self):
        shell = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "sh"
        quoted_shell = shlex.quote(shell)
        quoted_package_folder = shlex.quote(self.package_folder)
        self._run_checked(
            f"make SHELL={quoted_shell} install DESTDIR={quoted_package_folder}",
            cwd=self.source_folder,
        )

        bin_path = os.path.join(self.package_folder, "bin", "shntool")
        if os.path.exists(bin_path):
            os.chmod(bin_path, 0o755)
            if str(self.settings.os) != "OHOS":
                self.output.warning("Skipping OHOS ELF signing on non-OHOS platform")
                return

            sign_tool = "/data/service/hnp/bin/binary-sign-tool"
            objcopy = "/data/service/hnp/bin/llvm-objcopy"
            tmp_signed = bin_path + ".signed"

            try:
                if self._elf_has_section(bin_path, ".codesign"):
                    objcopy_result = subprocess.run(
                        [objcopy, "--remove-section", ".codesign", bin_path],
                        capture_output=True,
                        timeout=10,
                    )
                    if objcopy_result.returncode != 0:
                        raise RuntimeError(
                            f"objcopy failed for shntool (rc={objcopy_result.returncode}): "
                            f"{self._process_output(objcopy_result)}"
                        )
                else:
                    self.output.info("Skipping .codesign removal for unsigned shntool ELF")

                sign_result = subprocess.run(
                    [sign_tool, "sign", "-inFile", bin_path, "-outFile", tmp_signed, "-selfSign", "1"],
                    capture_output=True,
                    timeout=30,
                )
                if sign_result.returncode != 0 or not os.path.exists(tmp_signed):
                    raise RuntimeError(
                        f"ELF signing failed for shntool (rc={sign_result.returncode}): "
                        f"{self._process_output(sign_result)}"
                    )
            except (FileNotFoundError, PermissionError, subprocess.TimeoutExpired) as exc:
                raise RuntimeError(f"ELF signing failed for shntool: {exc}") from exc

            os.replace(tmp_signed, bin_path)
            os.chmod(bin_path, 0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share"]
