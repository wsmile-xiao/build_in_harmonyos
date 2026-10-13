import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class RsetConan(ConanFile):
    name = "rset"
    version = "3.3"
    description = "Remote Staging Execution Tool: configure systems using any scripting language"
    license = "ISC"
    homepage = "https://github.com/eradman/rset"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # rset is a self-contained C tool: no third-party dependencies
        pass

    def build_requirements(self):
        pass

    def layout(self):
        # Everything happens in the source folder (plain Makefile project)
        self.folders.source = "."
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        # R32: OHOS reports os=OHOS, keep Linux-compatible builds allowed
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanException(f"rset supports Linux/OHOS, got {self.settings.os}")

    def build(self):
        apply_conandata_patches(self)
        # R33: never read ${CC}/${CFLAGS} from the shell environment; the
        # compiler comes from the Conan toolchain conf. rset's ./configure is
        # a plain sh script (no --prefix); it honours CC and TARGET_OS.
        config_shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        try:
            cc = self.conf.get("tools.build:compiler_executables:c", check_type=str)
        except ConanException:
            # older profiles may define the conf as a plain dict
            compilers = self.conf.get("tools.build:compiler_executables", {}) or {}
            cc = compilers.get("c", "clang") if isinstance(compilers, dict) else "clang"
        # OHOS is musl-based Linux: strlcpy/arc4random probe succeeds and the
        # Makefile.linux port is selected (matches Makefile.linux behaviour).
        self.run(f'TARGET_OS=Linux CC="{cc}" {config_shell} ./configure', env="conanbuild")
        # R9: -j1 (HMDFS forbids make jobserver FIFOs)
        self.run(f"make CC=\"{cc}\" -j1", env="conanbuild")

    def package(self):
        # Install explicitly instead of `make install` (avoids install(1)
        # availability/PATH differences across workers).
        src = self.source_folder
        bin = os.path.join(self.package_folder, "bin")
        for prog in ("rset", "miniquark", "renv", "rinstall", "rsub",
                     "labelgrep", "rexec-summary"):
            copy(self, prog, src, bin, keep_path=False)
        copy(self, "LICENSE", src, os.path.join(self.package_folder, "licenses"))
        copy(self, "*.1", src, os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "*.5", src, os.path.join(self.package_folder, "share", "man", "man5"))
        if self.settings.os == "OHOS":
            # E077: OHOS refuses to exec ELF files without a .codesign section
            for prog in ("rset", "miniquark"):
                self._sign_ohos_elf(os.path.join(bin, prog))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []

    @staticmethod
    def _sign_ohos_elf(path):
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(path):
            raise ConanException(f"Missing packaged executable: {path}")
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("Required OHOS signing tools are missing")
        output = path + ".signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", output, "-selfSign", "1"],
            check=True,
            timeout=60,
        )
        sections = subprocess.run(
            [readelf, "-SW", output],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException("Signed packaged executable has invalid .codesign count")
        os.chmod(output, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(output, path)
