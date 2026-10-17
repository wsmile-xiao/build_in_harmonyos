"""Build and execute an OHOS FASTQ consumer from sickle's real output."""
import gzip
import os
import platform
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.layout import basic_layout


class SickleTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def _run_target(self, executable):
        if str(self.settings.os) == "OHOS" and platform.machine() not in ("aarch64", "arm64"):
            qemu = shutil.which("qemu-aarch64")
            if not qemu:
                raise ConanInvalidConfiguration("qemu-aarch64 needed to run OHOS consumer on x86")
            return shlex.quote(qemu) + " " + shlex.quote(executable)
        return shlex.quote(executable)

    def build(self):
        os.makedirs(self.build_folder, exist_ok=True)
        sickle = os.path.join(self.dependencies["sickle"].package_folder, "bin", "sickle")
        input_path = os.path.join(self.build_folder, "input.fastq.gz")
        output_path = os.path.join(self.build_folder, "trimmed.fastq")
        # gzip input exercises the published zlib linkage, not a mocked CLI.
        with gzip.open(input_path, "wb") as out:
            out.write(b"@good\nACGTACGT\n+\nIIII!!!!\n@drop\nTTTT\n+\n!!!!\n")
        self.run(self._run_target(sickle) + " se -t sanger -q 20 -l 1 -f "
                 + shlex.quote(input_path) + " -o " + shlex.quote(output_path))
        # CLI-produced FASTQ becomes a compiled-in header of the consumer.
        with open(output_path, "rb") as result:
            data = result.read()
        with open(os.path.join(self.build_folder, "generated_fastq.h"), "w", encoding="ascii") as header:
            header.write("static const unsigned char fastq_result[] = {" +
                         ",".join(str(value) for value in data) + ",0};\n")
        cc = (self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}).get("c", "cc")
        source = os.path.join(self.source_folder, "consumer.c")
        target = os.path.join(self.build_folder, "consumer")
        self.run(" ".join((shlex.quote(cc), "-std=c11", "-static" if str(self.settings.os) == "OHOS" else "",
                           "-I" + shlex.quote(self.build_folder), shlex.quote(source), "-o", shlex.quote(target))))

    def test(self):
        self.run(self._run_target(os.path.join(self.build_folder, "consumer")))
