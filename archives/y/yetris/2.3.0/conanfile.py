"""Conan recipe for yetris 2.3.0 on HarmonyOS PC (arm64, OHOS).

yetris is a customizable ncurses Tetris clone. The 2.3.0 tag ships a plain
GNU Makefile (no cmake, no test/check target - N_static=0, documented in
test_package/MANIFEST.yml). Upstream links -lncurses, while the ohpcd
ncurses package provides the wide build only (libncursesw.a), so build()
overrides the LDFLAGS/CFLAGS_PLATFORM make variables instead of patching
the Makefile. -Wno-narrowing is added because clang (unlike gcc) errors on
the upstream char aggregate initializers in PieceDefinitions.cpp.

    CXXFLAGS    = $(CDEBUG) -g -Wall -Wextra $(CFLAGS_PLATFORM)
    LDFLAGS     = -lncurses $(LDFLAGS_PLATFORM)

    $(CXX) $(OBJECTS) $(COMMANDER_OBJS) -o bin/$(EXE) $(LIBSDIR) $(LDFLAGS)

The consumer test_package exercises the packaged binary through its real
CLI contract (--help / --version), asserted on output content and exit code.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

required_conan_version = ">=1.52.0"


class YetrisConan(ConanFile):
    name = "yetris"
    version = "2.3.0"
    description = "Customizable Tetris clone for the terminal (ncurses)"
    homepage = "https://github.com/alexdantas/yetris"
    url = "https://github.com/alexdantas/yetris"
    license = "GPL-3.0-or-later"
    topics = ("tetris", "game", "terminal", "ncurses")
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version],
            destination=self.source_folder, strip_root=True)

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        # ncurses TUI: upstream links -lncurses (Makefile LDFLAGS).
        self.requires("ncurses/6.6")

    def _dep_dir(self, name, kind):
        """Absolute cpp_info dir of a dependency (cpp_info entries are
        relative to package_folder)."""
        dep = self.dependencies.get(name)
        d = getattr(dep.cpp_info, kind)[0]
        return d if os.path.isabs(d) else os.path.join(dep.package_folder, d)

    def generate(self):
        VirtualBuildEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                "yetris currently supports only OHOS armv8"
            )

        src = self.source_folder.replace("\\", "/")
        ncurses_inc = self._dep_dir("ncurses", "includedirs")
        ncurses_lib = self._dep_dir("ncurses", "libdirs")
        # The ohpcd make binary carries a built-in default CXX pointing at
        # its build-time CI SDK path (nonexistent off-CI), and this Makefile
        # does not define CC/CXX - pass both explicitly from the profile
        # conf. CFLAGS_PLATFORM feeds -I into $(CXXFLAGS); LDFLAGS is fully
        # overridden to swap the missing -lncurses for the wide build
        # libncursesw.a shipped by the ohpcd ncurses package.
        compilers = self.conf.get("tools.build:compiler_executables", default={})
        cc = compilers.get("c", "clang")
        cxx = compilers.get("cpp", "clang++")
        self.run(
            f"cd '{src}' && make -j1 CC='{cc}' CXX='{cxx}' "
            f"CFLAGS_PLATFORM=\"-I{ncurses_inc} -Wno-narrowing\" "
            f"LDFLAGS=\"-L{ncurses_lib} -lncursesw\"",
            env="conanbuild",
        )
        if not os.path.isfile(os.path.join(src, "bin", "yetris")):
            raise ConanException("yetris binary was not produced by make")

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        # Upstream `make install` also wants a man page pipeline; the binary
        # is the package payload, installed manually (HMDFS-safe).
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        shutil.copy(os.path.join(self.source_folder, "bin", "yetris"),
                    os.path.join(bin_dir, "yetris"))
        shutil.copymode(os.path.join(self.source_folder, "bin", "yetris"),
                        os.path.join(bin_dir, "yetris"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
