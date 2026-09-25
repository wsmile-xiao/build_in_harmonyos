from conan import ConanFile
from conan.tools.files import copy, get, apply_conandata_patches
from conan.tools.layout import basic_layout
from conan.errors import ConanException
import os
import re
import subprocess


class ZorkConan(ConanFile):
    name = "zork"
    version = "1.1.0"
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    license = "MIT"
    url = "https://github.com/devshane/zork"
    homepage = "https://github.com/devshane/zork"
    description = "The Dungeon (Zork I) - classic text adventure game, C implementation"
    topics = ("game", "adventure", "text", "zork", "dungeon")
    build_system = "make"

    def export_sources(self):
        # No patch files needed — all adaptation is done inline in build().
        pass

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def layout(self):
        basic_layout(self, src_folder="src")

    def build(self):
        src = self.source_folder
        datadir = os.path.join(self.package_folder, "share", "zork")
        compiler_executables = self.conf.get("tools.build:compiler_executables", default={})
        cc = compiler_executables.get("c", "cc")

        # Apply conandata patches (none defined — inline patching in this recipe).
        apply_conandata_patches(self)

        # Patch Makefile: replace DATADIR with the package data dir.
        # The dinit.o rule uses -DTEXTFILE=\"$(DATADIR)/dtextc.dat\" which
        # hardcodes /usr/games/lib (nonexistent on OHOS). Setting DATADIR
        # to our package path makes the C string literal resolve correctly.
        makefile = os.path.join(src, "Makefile")
        with open(makefile, "r") as f:
            content = f.read()
        content = content.replace(
            "DATADIR = /usr/games/lib",
            f'DATADIR = {datadir}'
        )
        with open(makefile, "w") as f:
            f.write(content)

        # Write wrapper script to invoke make
        build_script = os.path.join(src, "build_ohos.sh")
        script_content = (
            "#!/bin/sh\n"
            f"cd \"{src}\"\n"
            f"make CC=\"{cc}\" "
            f"TERMFLAG=-DMORE_NONE "
            f"LIBS= \"$@\"\n"
        )
        with open(build_script, "w") as f:
            f.write(script_content)
        os.chmod(build_script, 0o755)

        result = subprocess.run([build_script], cwd=src, capture_output=True, text=True)
        self.output.info(result.stdout)
        if result.returncode != 0:
            self.output.error(result.stderr)
            raise ConanException(f"make failed with exit code {result.returncode}")

    def package(self):
        copy(self, "zork", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "dtextc.dat", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "zork"))
        copy(self, "dungeon.6", src=self.source_folder, dst=os.path.join(self.package_folder, "share", "man", "man6"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
