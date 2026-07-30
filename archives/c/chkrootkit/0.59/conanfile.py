#!/usr/bin/env python3
"""Conan recipe for chkrootkit 0.59."""
import os
import shutil
import subprocess
import tarfile
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, download, replace_in_file
from conan.tools.layout import basic_layout


class ChkrootkitConan(ConanFile):
    name = "chkrootkit"
    version = "0.59"
    description = "Local rootkit detection tool"
    license = "BSD-2-Clause"
    homepage = "https://www.chkrootkit.org/"
    url = ""
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        url = self.conan_data["sources"]["url"]
        expected_sha256 = self.conan_data["sources"]["sha256"]
        archive = os.path.join(self.source_folder, "chkrootkit-0.59.tar.gz")
        download(self, url=url, filename=archive, sha256=expected_sha256)

        tmp_extract = tempfile.mkdtemp(dir=self.source_folder)
        with tarfile.open(archive, "r:gz") as tf:
            tf.extractall(tmp_extract)

        root = os.path.join(tmp_extract, "chkrootkit-0.59")
        if not os.path.isdir(root):
            raise ConanInvalidConfiguration("Unexpected chkrootkit source archive layout")
        for item in os.listdir(root):
            shutil.move(os.path.join(root, item), os.path.join(self.source_folder, item))
        shutil.rmtree(tmp_extract)
        os.unlink(archive)

    def build(self):
        makefile = os.path.join(self.source_folder, "Makefile")
        replace_in_file(self, makefile, "\t@strip $@", "\t@true")
        replace_in_file(self, makefile, "\t\tstrip $@ ;\\", "\t\ttrue ;\\")

        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c", str(self.settings.compiler))
        shell = os.environ.get("CONFIG_SHELL", "sh")
        build_type_flags = {
            "Debug": "-O0 -g",
            "Release": "-O2 -DNDEBUG",
            "RelWithDebInfo": "-O2 -g -DNDEBUG",
            "MinSizeRel": "-Os -DNDEBUG",
        }
        cflags = f"-DHAVE_LASTLOG_H -fPIC {build_type_flags[str(self.settings.build_type)]}"
        self.run(
            f'make sense CC="{cc}" STATIC= CFLAGS="{cflags}" SHELL="{shell}" -j1',
            cwd=self.source_folder,
        )

    def package(self):
        libexec = os.path.join(self.package_folder, "libexec", "chkrootkit")
        bindir = os.path.join(self.package_folder, "bin")
        docdir = os.path.join(self.package_folder, "share", "doc", "chkrootkit")
        os.makedirs(libexec, exist_ok=True)
        os.makedirs(bindir, exist_ok=True)
        os.makedirs(docdir, exist_ok=True)

        copy(self, "chkrootkit", src=self.source_folder, dst=libexec, keep_path=False)
        tools = [
            "chklastlog",
            "chkwtmp",
            "chkproc",
            "chkdirs",
            "check_wtmpx",
            "strings-static",
            "chkutmp",
            "ifpromisc",
        ]
        for tool in tools:
            tool_path = os.path.join(self.source_folder, tool)
            if os.path.exists(tool_path):
                copy(self, tool, src=self.source_folder, dst=libexec, keep_path=False)
                self._sign_binary(os.path.join(libexec, tool))

        for doc in ("README", "README.chklastlog", "README.chkwtmp", "COPYRIGHT", "ACKNOWLEDGMENTS"):
            copy(self, doc, src=self.source_folder, dst=docdir, keep_path=False)

        main_script = os.path.join(libexec, "chkrootkit")
        os.chmod(main_script, 0o755)

        wrapper = os.path.join(bindir, "chkrootkit")
        with open(wrapper, "w", encoding="utf-8", newline="\n") as f:
            f.write("#!/usr/bin/env sh\n")
            f.write("script_dir=$(CDPATH= cd -- \"$(dirname -- \"$0\")\" && pwd)\n")
            f.write("libexec_dir=\"$script_dir/../libexec/chkrootkit\"\n")
            f.write("cd \"$libexec_dir\" || exit 1\n")
            f.write("if [ -n \"${CONFIG_SHELL:-}\" ]; then shell=\"$CONFIG_SHELL\"; ")
            f.write("elif [ -x /data/service/hnp/bin/bash ]; then shell=/data/service/hnp/bin/bash; ")
            f.write("else shell=sh; fi\n")
            f.write("exec \"$shell\" ./chkrootkit \"$@\"\n")
        os.chmod(wrapper, 0o755)

    def _sign_binary(self, bin_path):
        os.chmod(bin_path, 0o755)
        if self.settings.os != "OHOS":
            return

        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        tmp_signed = bin_path + ".signed"

        try:
            objcopy_result = subprocess.run(
                [objcopy, "--remove-section", ".codesign", bin_path],
                capture_output=True,
                timeout=10,
            )
            if objcopy_result.returncode != 0:
                raise RuntimeError(
                    f"objcopy failed for {os.path.basename(bin_path)} "
                    f"(rc={objcopy_result.returncode})"
                )

            sign_result = subprocess.run(
                [sign_tool, "sign", "-inFile", bin_path, "-outFile", tmp_signed,
                 "-selfSign", "1"],
                capture_output=True,
                timeout=30,
            )
            if sign_result.returncode != 0 or not os.path.exists(tmp_signed):
                raise RuntimeError(
                    f"ELF signing failed for {os.path.basename(bin_path)} "
                    f"(rc={sign_result.returncode})"
                )
        except (FileNotFoundError, PermissionError, subprocess.TimeoutExpired) as exc:
            raise RuntimeError(
                f"ELF signing failed for {os.path.basename(bin_path)}: {exc}"
            ) from exc

        os.replace(tmp_signed, bin_path)
        os.chmod(bin_path, 0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["libexec", "share"]
