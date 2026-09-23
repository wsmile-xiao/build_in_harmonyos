#!/usr/bin/env python3
"""Consumer test for gnome-autoar 0.5.2."""

import hashlib
import os
import platform
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class OhosMeson(Meson):
    @property
    def _prefix(self):
        if (
            platform.system() == "Windows"
            and str(self._conanfile.settings.os) == "OHOS"
        ):
            return "/"
        return super()._prefix

class GnomeAutoarTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        PkgConfigDeps(self).generate()
        self._localize_dependency_metadata()
        VirtualRunEnv(self).generate()
        MesonToolchain(self).generate()
        self._inject_archiver()
        self._inject_pkg_config()

    def build(self):
        meson = OhosMeson(self)
        meson.configure()
        meson.build()
        meson.install()

    def test(self):
        test_binary = os.path.join(
            self.package_folder, "bin", "test_gnome_autoar"
        )
        if can_run(self):
            if str(self.settings.os) == "OHOS":
                if not self._prepare_ohos_execution(test_binary):
                    return
            self.run(test_binary, env="conanrun")
        else:
            self.output.info("Cross-building: consumer binary is run on OHOS device")

    def _find_ohos_runtime_tool(self, name):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compiler_executables.get("c") or compiler_executables.get("cpp", "")
        compiler_path = shutil.which(compiler) or compiler
        compiler_dir = os.path.dirname(compiler_path)
        candidates = [
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        ]
        for candidate in candidates:
            resolved = shutil.which(candidate) or candidate
            if resolved and os.path.isfile(resolved) and not os.path.islink(resolved):
                return os.path.abspath(resolved)
        return ""

    @staticmethod
    def _file_sha256(path):
        digest = hashlib.sha256()
        with open(path, "rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _run_signing_tool(argv, label):
        completed = subprocess.run(
            argv,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if completed.returncode != 0:
            raise ConanException(
                f"{label} failed ({completed.returncode}): "
                f"{completed.stderr.strip()}"
            )
        return completed.stdout

    def _elf_sections(self, readelf, path):
        output = self._run_signing_tool([readelf, "-S", path], "llvm-readelf")
        if ".note.ohos.ident" not in output:
            raise ConanException(f"ELF platform identity section missing: {path}")
        return output

    def _sign_elf_atomically(self, path, objcopy, readelf, signer):
        if not os.path.isfile(path) or os.path.islink(path):
            raise ConanException(f"unsafe ELF signing input: {path}")
        with open(path, "rb") as stream:
            if stream.read(4) != b"\x7fELF":
                raise ConanException(f"signing input is not ELF: {path}")

        unsigned_sha256 = self._file_sha256(path)
        temporary = f"{path}.unsigned-for-signing"
        signed = f"{path}.signed"
        if os.path.lexists(temporary) or os.path.lexists(signed):
            raise ConanException(f"stale signing transaction beside: {path}")
        try:
            shutil.copy2(path, temporary)
            sections = self._elf_sections(readelf, temporary)
            if ".codesign" in sections:
                self._run_signing_tool(
                    [objcopy, "--remove-section", ".codesign", temporary],
                    "llvm-objcopy",
                )
                self._elf_sections(readelf, temporary)
            self._run_signing_tool(
                [
                    signer,
                    "sign",
                    "-inFile",
                    temporary,
                    "-outFile",
                    signed,
                    "-selfSign",
                    "1",
                ],
                "binary-sign-tool",
            )
            if not os.path.isfile(signed) or os.path.islink(signed):
                raise ConanException(f"signer did not create a regular output: {path}")
            signed_sections = self._elf_sections(readelf, signed)
            if ".codesign" not in signed_sections:
                raise ConanException(f"signed ELF has no .codesign section: {path}")
            os.chmod(signed, 0o755)
            signed_sha256 = self._file_sha256(signed)
            if signed_sha256 == unsigned_sha256:
                raise ConanException(f"ELF signing did not change the file: {path}")
            os.replace(signed, path)
        finally:
            for residue in (temporary, signed):
                if os.path.lexists(residue):
                    os.remove(residue)

    def _prepare_ohos_execution(self, test_binary):
        tools = {
            "objcopy": self._find_ohos_runtime_tool("llvm-objcopy"),
            "readelf": self._find_ohos_runtime_tool("llvm-readelf"),
            "signer": self._find_ohos_runtime_tool("binary-sign-tool"),
        }
        missing = [name for name, path in tools.items() if not path]
        if missing:
            self.output.info(
                "TARGET_RUNTIME_TESTS=NOT_RUN: OHOS signing tools unavailable: "
                + ", ".join(missing)
            )
            self.output.info("CONSUMER_COMPILE_LINK_TESTS=1/1")
            return False
        self._sign_elf_atomically(
            test_binary, tools["objcopy"], tools["readelf"], tools["signer"]
        )
        return True

    def _inject_archiver(self):
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compiler_executables.get("c") or ""
        compiler_directory = (
            os.path.dirname(os.path.normpath(compiler)) if compiler else ""
        )

        ar = compiler_executables.get("ar")
        ranlib = compiler_executables.get("ranlib")
        if compiler_directory:
            if not ar:
                candidate = os.path.join(compiler_directory, "llvm-ar")
                if os.path.isfile(candidate):
                    ar = candidate
            if not ranlib:
                candidate = os.path.join(compiler_directory, "llvm-ranlib")
                if os.path.isfile(candidate):
                    ranlib = candidate

        if not ar:
            return

        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            machine_file = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(machine_file):
                continue
            with open(machine_file, encoding="utf-8") as handle:
                content = handle.read()
            if "[binaries]" not in content:
                continue

            binaries = []
            if "\nar =" not in content:
                binaries.append(f"ar = '{ar}'")
            if ranlib and "\nranlib =" not in content:
                binaries.append(f"ranlib = '{ranlib}'")
            if not binaries:
                continue
            content = content.replace(
                "[binaries]\n", "[binaries]\n" + "\n".join(binaries) + "\n", 1
            )
            with open(machine_file, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)

    def _localize_dependency_metadata(self):
        """Keep Meson link arguments relative on a Windows OHOS host."""
        meson_build_folder = os.path.dirname(self.generators_folder)
        local_root = os.path.join(self.build_folder, "conan-deps")
        for dependency_name in ("glib", "libarchive", "zlib", "xz"):
            try:
                dependency = self.dependencies.get(dependency_name)
            except KeyError:
                continue
            local_dependency = os.path.join(local_root, dependency_name)
            for subdirectory in ("include", "lib"):
                source_directory = os.path.join(
                    dependency.package_folder, subdirectory
                )
                if os.path.isdir(source_directory):
                    destination_directory = os.path.join(
                        local_dependency, subdirectory
                    )
                    if dependency_name == "libarchive" and subdirectory == "lib":
                        os.makedirs(destination_directory, exist_ok=True)
                        for filename in os.listdir(source_directory):
                            if filename.endswith(".a"):
                                shutil.copy2(
                                    os.path.join(source_directory, filename),
                                    os.path.join(destination_directory, filename),
                                )
                    else:
                        shutil.copytree(
                            source_directory,
                            destination_directory,
                            dirs_exist_ok=True,
                        )

            source_prefix = os.path.abspath(dependency.package_folder)
            source_prefixes = {
                source_prefix.replace(os.sep, "/"),
                source_prefix.replace(os.sep, "\\"),
            }
            local_prefix = os.path.relpath(
                local_dependency, meson_build_folder
            ).replace(os.sep, "/")
            for pc_file in os.listdir(self.generators_folder):
                if not pc_file.endswith(".pc"):
                    continue
                pc_path = os.path.join(self.generators_folder, pc_file)
                with open(pc_path, encoding="utf-8") as handle:
                    content = handle.read()
                rewritten = content
                for prefix in source_prefixes:
                    rewritten = rewritten.replace(prefix, local_prefix)
                if dependency_name == "libarchive":
                    rewritten = rewritten.replace(
                        " -larchive",
                        " -Wl,-Bstatic -larchive -Wl,-Bdynamic",
                    )
                if rewritten != content:
                    with open(
                        pc_path, "w", encoding="utf-8", newline="\n"
                    ) as handle:
                        handle.write(rewritten)

    def _inject_pkg_config(self):
        pkg_config = self._pkg_config_command()
        if not pkg_config:
            return

        replacement = (
            f"pkg-config = {list(pkg_config)!r}"
            if isinstance(pkg_config, (list, tuple))
            else f"pkg-config = '{pkg_config}'"
        )
        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            machine_file = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(machine_file):
                continue
            with open(machine_file, encoding="utf-8") as handle:
                content = handle.read()

            rewritten = []
            replaced = False
            for line in content.splitlines(keepends=True):
                if line.startswith(("pkg-config =", "pkgconfig =")):
                    ending = "\n" if line.endswith("\n") else ""
                    rewritten.append(replacement + ending)
                    replaced = True
                else:
                    rewritten.append(line)
            content = "".join(rewritten)
            if not replaced:
                content = content.replace(
                    "[binaries]\n", f"[binaries]\n{replacement}\n", 1
                )
            with open(machine_file, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(content)

    def _pkg_config_command(self):
        pkg_config = self.conf.get("tools.gnu:pkg_config", default=None)
        if not pkg_config or not os.path.isfile(str(pkg_config)):
            pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")
        if not pkg_config:
            return None

        pkg_config = os.path.abspath(str(pkg_config))
        if str(self.settings.os) != "OHOS":
            return pkg_config

        prefix = os.path.dirname(os.path.dirname(pkg_config))
        runtime = os.path.join(prefix, "lib", "libpkgconf.so.7.0.0")
        if not os.path.isfile(runtime):
            return pkg_config

        private_lib = os.path.join(self.generators_folder, "pkgconf-lib")
        os.makedirs(private_lib, exist_ok=True)
        shutil.copy2(runtime, os.path.join(private_lib, "libpkgconf.so.7"))

        wrapper = os.path.join(self.generators_folder, "pkg-config-ohos")
        content = (
            "#!/bin/sh\n"
            f"export LD_LIBRARY_PATH={shlex.quote(private_lib)}"
            "${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}\n"
            f"exec {shlex.quote(pkg_config)} \"$@\"\n"
        )
        with open(wrapper, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        os.chmod(wrapper, 0o755)
        return "/bin/sh", wrapper
