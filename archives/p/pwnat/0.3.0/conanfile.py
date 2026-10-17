"""Package the upstream pwnat 0.3.0 command-line program."""

import os
import shlex
import shutil
import stat
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class PwnatConan(ConanFile):
    name = "pwnat"
    version = "0.3.0"
    package_type = "application"
    description = "UDP NAT traversal command-line tool"
    license = "GPL-3.0-or-later AND BSD-3-Clause"
    homepage = "https://github.com/samyk/pwnat"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("pwnat supports Linux and OHOS")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        source = dict(self.conan_data["sources"][self.version])
        local_archive = os.environ.get("PWNAT_SOURCE_ARCHIVE")
        if local_archive:
            archive = Path(local_archive).resolve(strict=True)
            if not archive.is_file():
                raise ConanInvalidConfiguration("PWNAT_SOURCE_ARCHIVE is not a file")
            source["url"] = archive.as_uri()
            source["filename"] = archive.name
        get(self, **source, strip_root=True)

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    @staticmethod
    def _sign_elf(path):
        signer = shutil.which("binary-sign-tool")
        readelf = shutil.which("llvm-readelf")
        objcopy = shutil.which("llvm-objcopy")
        if not all((signer, readelf, objcopy)):
            raise ConanInvalidConfiguration("missing OHOS ELF signing tools")
        pending = path.with_name(path.name + ".pwnat-signing")
        signed = path.with_name(path.name + ".pwnat-signed")
        if pending.exists() or signed.exists():
            raise ConanInvalidConfiguration("stale pwnat signing sibling")
        try:
            shutil.copy2(path, pending)
            sections = subprocess.run(
                [readelf, "-S", str(pending)], capture_output=True, text=True,
                check=True, timeout=10,
            ).stdout
            if ".codesign" in sections:
                subprocess.run(
                    [objcopy, "--remove-section", ".codesign", str(pending)],
                    check=True, timeout=10,
                )
            subprocess.run(
                [signer, "sign", "-inFile", str(pending), "-outFile", str(signed),
                 "-selfSign", "1"],
                check=True, capture_output=True, timeout=40,
            )
            after = subprocess.run(
                [readelf, "-S", str(signed)], capture_output=True, text=True,
                check=True, timeout=10,
            ).stdout
            if after.count(".codesign") != 1:
                raise ConanInvalidConfiguration("signed pwnat ELF lacks one .codesign section")
            signed.chmod(stat.S_IMODE(path.stat().st_mode) | stat.S_IXUSR)
            os.replace(signed, path)
        finally:
            for temporary in (pending, signed):
                if temporary.exists():
                    temporary.unlink()

    def build(self):
        for pattern in ("*.c", "*.h", "Makefile"):
            copy(self, pattern, src=self.source_folder, dst=self.build_folder,
                 keep_path=False)
        if str(self.settings.os) == "OHOS":
            # Upstream packet.h also includes the standard <unistd.h> below.
            # The nonstandard sys/unistd.h alias is absent from OHOS's sysroot.
            header = Path(self.build_folder, "packet.h")
            original = header.read_bytes()
            obsolete = b"#include\t<sys/unistd.h>"
            if original.count(obsolete) != 1 or original.count(b"#include\t<unistd.h>") != 1:
                raise ConanInvalidConfiguration("pwnat packet.h include layout changed")
            header.write_bytes(original.replace(obsolete, b"/* use standard unistd.h below */"))
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        self.run(f"make -j1 OS=LINUX CC={shlex.quote(cc)}", cwd=self.build_folder)
        self.output.info("UPSTREAM_BUILD_PASS: pwnat make; no upstream test target")

    def package(self):
        executable = Path(self.build_folder, "pwnat")
        if not executable.is_file():
            raise ConanInvalidConfiguration("upstream pwnat executable is missing")
        copy(self, "pwnat", src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "COPYING-pingtunnel", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # strlcpy.c carries the BSD redistribution notice in its header.
        copy(self, "strlcpy.c", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        if str(self.settings.os) == "OHOS":
            self._sign_elf(Path(self.package_folder, "bin", "pwnat"))

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
