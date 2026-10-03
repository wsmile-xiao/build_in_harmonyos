"""Exercise libregfi's published range-list API on the target device."""

import os
import re
import shlex
import shutil
import stat
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration


class ReglookupTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("talloc/2.4.4")

    def test(self):
        package = self.dependencies[self.tested_reference_str].package_folder
        talloc = self.dependencies["talloc"].cpp_info
        cc = self.conf.get("tools.build:compiler_executables", default={}).get("c", "clang")
        source = Path(self.source_folder, "test.c")
        executable = Path(self.build_folder, "reglookup-consumer")
        args = [cc, "-I" + os.path.join(package, "include", "regfi")]
        args += ["-I" + directory for directory in talloc.includedirs]
        args += [source, "-o", executable, "-L" + os.path.join(package, "lib")]
        args += ["-L" + directory for directory in talloc.libdirs]
        args += ["-lregfi", "-ltalloc", "-lm", "-lpthread",
                 "-Wl,-rpath," + os.path.join(package, "lib")]
        self.run(shlex.join(str(arg) for arg in args))
        if str(self.settings.os) == "OHOS":
            signer = shutil.which("binary-sign-tool")
            readelf = shutil.which("llvm-readelf")
            if not signer or not readelf:
                raise ConanInvalidConfiguration("missing consumer signing tools")
            signed = executable.with_name(executable.name + ".signed")
            subprocess.run([signer, "sign", "-inFile", str(executable),
                            "-outFile", str(signed), "-selfSign", "1"],
                           check=True, capture_output=True, timeout=40)
            result = subprocess.run([readelf, "-S", str(signed)],
                                    check=True, capture_output=True, text=True, timeout=10)
            if len(re.findall(r"\s\.codesign\s", result.stdout)) != 1:
                raise ConanInvalidConfiguration("consumer signature missing")
            signed.chmod(stat.S_IMODE(executable.stat().st_mode) | stat.S_IXUSR)
            os.replace(signed, executable)
        self.run(shlex.quote(str(executable)), env="conanrun")
        self.output.info("REGLOOKUP_CONSUMER_PASS: range_list public API")
