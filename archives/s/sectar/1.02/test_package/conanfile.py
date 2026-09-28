"""OHOS CLI consumer: sectar generates C input for an aarch64 build."""
import os
import platform
import shlex
import shutil
import tempfile

from conan import ConanFile


class SectarTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        tool = os.path.join(self.dependencies["sectar"].package_folder, "bin", "sectar")
        compiler = self.conf.get("tools.build:compiler_executables", default={}).get("c")
        if not compiler:
            raise RuntimeError("OHOS C compiler is required for consumer build")
        runner = ""
        if str(self.settings.arch) == "armv8" and platform.machine() not in ("aarch64", "arm64"):
            if not shutil.which("qemu-aarch64"):
                raise RuntimeError("qemu-aarch64 is needed to run the OHOS consumer on x86")
            runner = "qemu-aarch64 "

        with tempfile.TemporaryDirectory(prefix="sectar-consumer-", dir=self.build_folder) as work:
            with open(os.path.join(self.source_folder, "consumer.c"), "rb") as f:
                source = f.read()
            # The upstream format pads with NUL but does not store plaintext length.
            # Align the source so recovered bytes are exactly the original bytes.
            plain = source + b" " * (-len(source) % 32)
            with open(os.path.join(work, "plain.c"), "wb") as f:
                f.write(plain)
            with open(os.path.join(work, "key"), "w", encoding="ascii") as f:
                f.write("0123456789ABCDEF" * 4)  # 256-bit key in hex

            self.run(f"{runner}{shlex.quote(tool)} -k key -e -o cipher.star plain.c", cwd=work)
            self.run(f"{runner}{shlex.quote(tool)} -k key -d -o roundtrip.c cipher.star", cwd=work)
            with open(os.path.join(work, "roundtrip.c"), "rb") as f:
                if f.read() != plain:
                    raise RuntimeError("sectar AES CBC output differs from original C source")
            self.run(f"{shlex.quote(compiler)} -static -o consumer roundtrip.c", cwd=work)
            self.run(f"{runner}./consumer", cwd=work)
