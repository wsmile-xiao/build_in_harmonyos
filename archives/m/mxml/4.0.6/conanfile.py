"""Mini-XML 4.0.6 for HarmonyOS PC."""

import os
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import copy, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class MxmlConan(ConanFile):
    name = "mxml"
    version = "4.0.6"
    package_type = "library"
    description = "Small C99 XML parsing and writing library"
    homepage = "https://www.msweet.org/mxml/"
    license = "Apache-2.0"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def layout(self):
        # Upstream's Makefile.in compiles source basenames from its current
        # directory; an out-of-source configure leaves make unable to find
        # mxml-attr.c. Keep Conan's generators in ./conan but build in place.
        basic_layout(self, build_folder=".")

    def source(self):
        source = dict(self.conan_data["sources"][self.version])
        local_archive = os.environ.get("MXML_SOURCE_ARCHIVE")
        if local_archive:
            archive = Path(local_archive).resolve(strict=True)
            if not archive.is_file():
                raise ConanInvalidConfiguration("local source archive is not a file")
            source["url"] = archive.as_uri()
            source["filename"] = archive.name
        get(self, **source, strip_root=True)

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            # The target compiler reports this exact tuple. The shipped
            # config.sub accepts linux-ohos, while config.guess does not
            # classify HarmonyOS uname.
            toolchain.configure_args.extend([
                "--build=aarch64-unknown-linux-ohos",
                "--host=aarch64-unknown-linux-ohos",
            ])
        # Preserve upstream's libmxml4 ABI and pkg-config module: Yoshimi
        # searches mxml4 before its legacy mxml fallback.
        toolchain.configure_args.append(
            "--enable-shared" if self.options.shared else "--disable-shared"
        )
        # Upstream's testmxml target links the static archive even in a
        # shared build, so retain it rather than silently dropping tests.
        toolchain.configure_args.append("--enable-static")
        toolchain.generate()
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    @staticmethod
    def _sign_elf(path):
        signer = shutil.which("binary-sign-tool")
        readelf = shutil.which("llvm-readelf") or shutil.which("readelf")
        if not signer or not readelf:
            raise ConanInvalidConfiguration("ELF signer and readelf are required on OHOS")
        original = Path(path)
        pending = original.with_name(original.name + ".mxml-signing")
        signed = original.with_name(original.name + ".mxml-signed")
        if pending.exists() or signed.exists():
            raise ConanInvalidConfiguration("stale signing sibling: {}".format(original))
        try:
            shutil.copy2(original, pending)
            subprocess.run([signer, "sign", "-inFile", str(pending),
                            "-outFile", str(signed), "-selfSign", "1"],
                           check=True, capture_output=True, text=True, timeout=40)
            sections = subprocess.run([readelf, "-S", str(signed)], check=True,
                                      capture_output=True, text=True, timeout=20)
            if ".codesign" not in sections.stdout:
                raise ConanException("signed ELF has no .codesign section")
            os.chmod(signed, original.stat().st_mode)
            os.replace(signed, original)
        finally:
            for temporary in (pending, signed):
                if temporary.exists():
                    temporary.unlink()

    def build(self):
        environment = Environment()
        if str(self.settings.os) == "OHOS":
            configure = os.path.join(self.build_folder, "configure")
            replace_in_file(self, configure,
                            'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&',
                            'tmp="${TMPDIR:-.}/conf$$-$RANDOM"; (umask 007 && mkdir "$tmp") &&',
                            strict=True)
            replace_in_file(self, configure, 'tmp=./conf$$-$RANDOM',
                            'tmp="${TMPDIR:-.}/conf$$-$RANDOM"', strict=True)
            replace_in_file(self, configure, '(umask 077 && mkdir "$tmp")',
                            '(umask 007 && mkdir "$tmp")', strict=True)
            scratch = Path(self.build_folder, ".autoconf-tmp")
            previous_umask = os.umask(0o007)
            try:
                scratch.mkdir(mode=0o770, exist_ok=False)
            finally:
                os.umask(previous_umask)
            environment.define("TMPDIR", str(scratch))
        autotools = Autotools(self)
        with environment.vars(self).apply():
            autotools.configure()
            autotools.make(args=["-j1"])
        if str(self.settings.os) == "OHOS":
            self._sign_elf(os.path.join(self.build_folder, "testmxml"))
        # This is the complete registered upstream suite: three file/string/
        # descriptor comparison groups, each exercising testmxml's API checks.
        autotools.make(target="test", args=["-j1"])
        self.output.info("UPSTREAM_3_OF_3_PASS")

    def package(self):
        Autotools(self).install()
        if str(self.settings.os) == "OHOS" and self.options.shared:
            self._sign_elf(os.path.join(self.package_folder, "lib", "libmxml4.so.2"))
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        copy(self, "NOTICE", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["mxml4"]
        self.cpp_info.includedirs = ["include/libmxml4"]
        self.cpp_info.set_property("pkg_config_name", "mxml4")
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
