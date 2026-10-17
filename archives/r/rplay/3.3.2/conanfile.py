"""Rplay 3.3.2 network-audio library and tools for HarmonyOS PC."""

import hashlib
import os
import shutil
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import copy, get, unzip
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class RplayConan(ConanFile):
    name = "rplay"
    version = "3.3.2"
    description = "Network sound library, clients, and server"
    license = "GPL-2.0-or-later"
    homepage = "https://packages.debian.org/source/sid/rplay"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        local_archive = os.environ.get("RPLAY_SOURCE_ARCHIVE")
        if local_archive:
            archive = Path(local_archive).resolve(strict=True)
            with archive.open("rb") as stream:
                actual = hashlib.file_digest(stream, "sha256").hexdigest()
            expected = self.conan_data["sources"][self.version]["sha256"]
            if actual != expected:
                raise ConanException("RPLAY_SOURCE_ARCHIVE SHA-256 mismatch")
            unzip(self, str(archive), destination=self.source_folder, strip_root=True)
        else:
            get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        AutotoolsToolchain(self).generate()
        VirtualBuildEnv(self).generate()

    def build(self):
        source = Path(self.source_folder)
        configure = source / "configure"
        script = configure.read_text(encoding="utf-8")
        old = 'BUILD_TARGETS="$BUILD_TARGETS librplay rplayd rplay rptp doc"'
        if script.count(old) != 1:
            raise ConanException("unexpected rplay configure BUILD_TARGETS layout")
        # The released source has no executable test suite. Building info
        # manuals needs makeinfo/TeX, which are not runtime dependencies.
        configure.write_text(script.replace(old, old.replace(" rptp doc", " rptp"), 1),
                             encoding="utf-8", newline="\n")
        makefile = source / "Makefile.in"
        make_text = makefile.read_text(encoding="utf-8")
        # The release also contains a file literally named "install". Without
        # .PHONY, GNU Make considers the top-level install target up to date.
        install_anchor = "\ninstall:\n"
        if make_text.count(install_anchor) != 1:
            raise ConanException("unexpected rplay install target layout")
        makefile.write_text(
            make_text.replace(install_anchor, "\n.PHONY: install\n\ninstall:\n", 1),
            encoding="utf-8", newline="\n",
        )

        env = Environment()
        # The old configure otherwise guesses OSS from the linux macro and
        # compiles /dev/dsp-specific code. Upstream's generic backend is the
        # supported non-OSS selection; hardware audio is not claimed.
        env.define("RPLAY_TARGET", "generic")
        # The source bundles GSM and rx; pin those branches so host libraries
        # cannot silently enter the package without Conan requirements.
        env.define("ac_cv_lib_gsm_gsm_decode", "no")
        env.define("ac_cv_lib_rx_regncomp", "no")
        env.define("ac_cv_lib_readline_readline", "no")
        # This 1999 Autoconf script otherwise falls back to /lib/cpp on
        # HarmonyOS. That path is absent, so every standard-header probe
        # falsely reports "no" even though Clang compiles C successfully.
        compilers = self.conf.get("tools.build:compiler_executables", default={},
                                  check_type=dict) or {}
        cc = compilers.get("c") or shutil.which("clang") or shutil.which("cc")
        if not cc:
            raise ConanException("rplay needs a C compiler for CPP probes")
        # The target compiler wrapper also injects linker-only arguments.
        # This old configure treats *any* preprocessor stderr as a missing
        # header; suppress only Clang's unused-argument diagnostic here.
        env.define("CPP", f"{cc} -E -Qunused-arguments")
        archiver = shutil.which("llvm-ar") or shutil.which("ar")
        ranlib = shutil.which("llvm-ranlib") or shutil.which("ranlib")
        if not archiver or not ranlib:
            raise ConanException("rplay needs an archiver and ranlib")
        env.define("RANLIB", ranlib)
        prefix = self.package_folder.replace("\\", "/")
        with env.vars(self).apply():
            self.run(f'sh ./configure --prefix="{prefix}"', cwd=self.source_folder,
                     env="conanbuild")
            self.run(f'make -j1 AR="{archiver}"', cwd=self.source_folder,
                     env="conanbuild")

    def package(self):
        self.run("make install -j1", cwd=self.source_folder, env="conanbuild")
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        lib = Path(self.package_folder) / "lib"
        if not (lib / "librplay.a").is_file() or not (lib / "librplay.so").is_file():
            raise ConanException("rplay library output missing after make install")
        if not (Path(self.package_folder) / "include" / "rplay.h").is_file():
            raise ConanException("installed rplay.h missing")
        if self.options.shared:
            (lib / "librplay.a").unlink()
        else:
            (lib / "librplay.so").unlink()

    def package_info(self):
        self.cpp_info.libs = ["rplay"]
        self.cpp_info.set_property("cmake_file_name", "rplay")
        self.cpp_info.set_property("cmake_target_name", "rplay::rplay")
