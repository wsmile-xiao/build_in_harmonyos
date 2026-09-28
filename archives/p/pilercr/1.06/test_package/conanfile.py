"""Build-time pilercr output is compiled into, then verified by, an OHOS consumer."""
import os
import platform
import re
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class PilercrTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def _runner(self):
        if self.settings.arch == "armv8" and platform.machine() not in ("aarch64", "arm64"):
            emulator = shutil.which("qemu-aarch64")
            if not emulator:
                raise ConanInvalidConfiguration("qemu-aarch64 required to run OHOS consumer")
            return shlex.quote(emulator) + " "
        return ""

    def build(self):
        tool = os.path.join(self.dependencies["pilercr"].package_folder, "bin", "pilercr")
        fasta = os.path.join(self.source_folder, "crispr.fa")
        report = os.path.join(self.build_folder, "crispr-report.txt")
        # This is the package's real CLI: its report becomes a compiled C++ input.
        self.run(f"{self._runner()}{shlex.quote(tool)} -in {shlex.quote(fasta)} "
                 f"-out {shlex.quote(report)} -noinfo -quiet")
        text = open(report, encoding="utf-8").read()
        summary = text.split("SUMMARY BY POSITION")[-1]
        match = re.search(r"(?m)^\s*1\s+ohos_pc_crispr\s+(\d+)\s+\d+\s+"
                          r"(\d+)\s+\d+\s+\d+\s+([ACGT]+)\s*$", summary)
        if not match or int(match.group(1)) != 401 or int(match.group(2)) < 3:
            raise ConanInvalidConfiguration("pilercr did not detect the CRISPR array")
        header = os.path.join(self.build_folder, "discovered.h")
        with open(header, "w", encoding="ascii") as out:
            out.write(f'#define DETECTED_POSITION {match.group(1)}\n'
                      f'#define DETECTED_COPIES {match.group(2)}\n'
                      f'#define DETECTED_REPEAT "{match.group(3)}"\n')
        tools = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        tc = AutotoolsToolchain(self).vars()
        cxx = tools.get("cpp") or tc.get("CXX")
        if not cxx:
            raise ConanInvalidConfiguration("C++ compiler missing")
        src = os.path.join(self.source_folder, "consumer.cpp")
        target = os.path.join(self.build_folder, "consumer")
        self.run(f"{shlex.quote(cxx)} -std=c++17 -static -I{shlex.quote(self.build_folder)} "
                 f"{shlex.quote(src)} -o {shlex.quote(target)}")

    def test(self):
        target = os.path.join(self.build_folder, "consumer")
        report = os.path.join(self.build_folder, "crispr-report.txt")
        self.run(f"{self._runner()}{shlex.quote(target)} {shlex.quote(report)}")
