"""Conan 2 recipe for libmpeg2 0.5.1 on HarmonyOS PC."""

import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, download, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class Libmpeg2Conan(ConanFile):
    name = "libmpeg2"
    version = "0.5.1"
    description = "MPEG-1 and MPEG-2 video decoding library and tools"
    license = "GPL-2.0-or-later"
    homepage = "https://libmpeg2.sourceforge.io/"
    package_type = "library"
    exports_sources = "testdata/*.py"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if str(self.settings.os) == "Windows":
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # basic_layout copies source into the build cache before build();
        # patch here so configure uses the patched copy, not an untouched one.
        apply_conandata_patches(self)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(["--disable-sdl", "--disable-directx"])
        tc.extra_cflags.extend(["-fno-strict-aliasing", "-fwrapv"])
        env = tc.environment()
        if str(self.settings.os) == "OHOS":
            # Old Libtool expects a real linker executable, not clang's
            # unavailable default `ld` symlink on the OHOS toolchain.
            for variable, command in (("LD", "ld.lld"), ("AR", "llvm-ar"),
                                      ("RANLIB", "llvm-ranlib"), ("NM", "llvm-nm"),
                                      ("STRIP", "llvm-strip"), ("OBJDUMP", "llvm-objdump")):
                found = shutil.which(command)
                if not found:
                    raise ConanException("required OHOS tool not found: " + command)
                env.define(variable, found)
        tc.generate(env=env)

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j2"])

        # The upstream regression corpus lives outside the source tarball.
        # Fetch the official CVS snapshot with a pinned digest, restore all
        # 73 stream/reference/dump triples and fail closed on any missing case.
        zip_path = os.path.join(self.build_folder, "libmpeg2-cvs.zip")
        suite = os.path.join(self.build_folder, "mpeg2dec-streams-cvs")
        tests = os.path.join(self.source_folder, "test", "tests")
        scripts = os.path.join(self.source_folder, "testdata")
        decoder = os.path.join(self.build_folder, "src", "mpeg2dec")
        download(self, filename=zip_path, retry=2, retry_wait=5,
                 **self.conan_data["test_sources"])
        subprocess.run([sys.executable, os.path.join(scripts, "extract-cvs-73.py"),
                        "--zip", zip_path, "--tests", tests, "--output", suite],
                       check=True)
        subprocess.run([sys.executable, os.path.join(scripts, "run-upstream-73.py"),
                        "--decoder", decoder, "--data-root", suite,
                        "--manifest", os.path.join(suite, "manifest.tsv"),
                        "--upstream-tests", tests], check=True)

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Link conversion first because it refers to the decoder library.
        self.cpp_info.libs = ["mpeg2convert", "mpeg2"]
