import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class HeirloomdoctoolsConan(ConanFile):
    name = "heirloom-doctools"
    version = "191015"
    description = "Heirloom Documentation Tools - traditional Unix document processing tools (troff/nroff/tbl/pic/eqn/refer)"
    license = "CDDL-1.1"
    homepage = "https://github.com/n-t-roff/heirloom-doctools"
    url = "https://github.com/n-t-roff/heirloom-doctools"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # Get compiler from Conan configuration (R33: never use bare shell vars)
        comp = self.conf.get("tools.build:compiler_executables", {}, check_type=dict)
        cc = comp.get("c", "clang")
        # Use CONFIG_SHELL from profile to run configure (E165: /bin/sh may not exist)
        config_shell = os.environ.get("CONFIG_SHELL", "sh")
        self.run(f"{config_shell} ./configure", cwd=self.source_folder)
        # build: 'make' defaults to 'dummy' target which generates cfg.mk + Makefiles, then builds all
        self.run(f"make CC={cc} CFLAGS='-fPIC -O2' -j1", cwd=self.source_folder)

    def package(self):
        # Install using PREFIX override (project uses ROOT + PREFIX variables)
        self.run(f"make PREFIX={self.package_folder} install", cwd=self.source_folder)
        # Create bin/ with symlinks to ucb/ executables for CI compatibility
        # CI checks (L1e destructive test, L2 smoke test, L5 artifact baseline)
        # look for standard bin/ directory; heirloom-doctools uses ucb/ by convention
        ucb_dir = os.path.join(self.package_folder, "ucb")
        bin_dir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(ucb_dir):
            os.makedirs(bin_dir, exist_ok=True)
            for name in os.listdir(ucb_dir):
                src = os.path.join(ucb_dir, name)
                if os.path.isfile(src) and os.access(src, os.X_OK):
                    link = os.path.join(bin_dir, name)
                    try:
                        os.symlink(os.path.join("..", "ucb", name), link)
                    except FileExistsError:
                        pass

    def package_info(self):
        # heirloom-doctools provides command-line tools, not libraries
        # bin/ has symlinks to ucb/ executables; both are valid bindirs
        self.cpp_info.bindirs = ["bin", "ucb"]
        # ucblib contains data files (fonts, macros, etc.) needed at runtime
        self.cpp_info.libdirs = ["ucblib"]
        self.cpp_info.resdirs = ["ucblib", "share"]
