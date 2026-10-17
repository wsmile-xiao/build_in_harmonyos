"""Conan recipe for the upstream plptools 1.0.26 release distribution."""

import os
import re
import shutil
import stat
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, get
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PlptoolsConan(ConanFile):
    name = "plptools"
    version = "1.0.26"
    package_type = "application"
    description = "EPOC/Psion serial-link command-line tools"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/plptools/plptools"
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "patches/*"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("plptools supports Linux and OHOS")

    def requirements(self):
        self.requires("readline/8.3")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        source = dict(self.conan_data["sources"][self.version])
        local_archive = os.environ.get("PLPTOOLS_SOURCE_ARCHIVE")
        if local_archive:
            archive = Path(local_archive).resolve(strict=True)
            if not archive.is_file():
                raise ConanInvalidConfiguration("PLPTOOLS_SOURCE_ARCHIVE is not a file")
            source["url"] = archive.as_uri()
            source["filename"] = archive.name
        get(self, **source, strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        readline_header = Path(self.dependencies["readline"].package_folder,
                               "include", "readline", "readline.h")
        header = readline_header.read_text(encoding="utf-8")
        match = re.search(r"^\s*#\s*define\s+RL_READLINE_VERSION\s+(0x[0-9A-Fa-f]+|[0-9]+)",
                          header, re.MULTILINE)
        if not match or int(match.group(1), 0) < 0x0403:
            raise ConanInvalidConfiguration("readline header does not prove version >= 4.3")
        AutotoolsDeps(self).generate()
        VirtualBuildEnv(self).generate()
        toolchain = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            # config.guess does not recognize HarmonyOS, and unsigned test
            # programs cannot execute. Distinct accepted GNU triples avoid
            # both the guess and the native-run probe.
            toolchain.configure_args.append("--build=aarch64-unknown-linux-gnu")
            toolchain.configure_args.append("--host=aarch64-unknown-linux-musl")
            # AX_LIB_READLINE uses AC_RUN_IFELSE and hardcodes the cross
            # branch to 'no'. The pinned dependency's header above proves
            # the version without executing an unsigned conftest.
            toolchain.configure_args.append("ax_cv_lib_readline_version_ok=yes")
        toolchain.configure_args.extend(["--disable-nls", "--disable-gcc-warnings"])
        toolchain.generate()
        VirtualRunEnv(self).generate()

    @staticmethod
    def _sign_elf(path):
        signer = shutil.which("binary-sign-tool")
        readelf = shutil.which("llvm-readelf")
        objcopy = shutil.which("llvm-objcopy")
        if not all((signer, readelf, objcopy)):
            raise ConanInvalidConfiguration("missing OHOS ELF signing tools")
        pending = path.with_name(path.name + ".plptools-signing")
        signed = path.with_name(path.name + ".plptools-signed")
        if pending.exists() or signed.exists():
            raise ConanInvalidConfiguration("stale plptools signing sibling")
        try:
            shutil.copy2(path, pending)
            before = subprocess.run(
                [readelf, "-S", str(pending)], capture_output=True, text=True,
                check=True, timeout=10,
            ).stdout
            if re.search(r"\s\.codesign\s", before):
                subprocess.run(
                    [objcopy, "--remove-section", ".codesign", str(pending)],
                    check=True, timeout=10,
                )
            subprocess.run(
                [signer, "sign", "-inFile", str(pending), "-outFile", str(signed), "-selfSign", "1"],
                check=True, capture_output=True, timeout=40,
            )
            after = subprocess.run(
                [readelf, "-S", str(signed)], capture_output=True, text=True,
                check=True, timeout=10,
            ).stdout
            if len(re.findall(r"\s\.codesign\s", after)) != 1:
                raise ConanInvalidConfiguration("signed plptools ELF lacks one .codesign section")
            signed.chmod(stat.S_IMODE(path.stat().st_mode) | stat.S_IXUSR)
            os.replace(signed, path)
        finally:
            for temporary in (pending, signed):
                if temporary.exists():
                    temporary.unlink()

    def build(self):
        tools = Autotools(self)
        tools.configure()
        tools.make(args=["-j2"])
        # This release has no registered TESTS/check_PROGRAMS.
        tools.make(target="check", args=["-j2"])
        self.output.info("UPSTREAM_BUILD_PASS: plptools make and make check")

    def package(self):
        Autotools(self).install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        package = Path(self.package_folder).resolve()
        if str(self.settings.os) == "OHOS":
            for directory in ("bin", "sbin", "lib"):
                root = package / directory
                if not root.is_dir():
                    continue
                for path in root.rglob("*"):
                    if path.is_file() and not path.is_symlink():
                        with path.open("rb") as stream:
                            is_elf = stream.read(4) == b"\x7fELF"
                        if is_elf:
                            self._sign_elf(path)
                for path in root.rglob("*"):
                    if path.is_symlink():
                        target = path.resolve(strict=True)
                        if not target.is_relative_to(package):
                            raise ConanInvalidConfiguration("package symlink escapes package")
                        path.unlink()
                        shutil.copy2(target, path)
        for name in ("ncpd", "plpftp", "plpprintd", "sisinstall"):
            if not any((package / sub / name).is_file() for sub in ("bin", "sbin")):
                raise ConanInvalidConfiguration("missing upstream command: " + name)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = ["lib/plptools"]
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib", "plptools")
        )
