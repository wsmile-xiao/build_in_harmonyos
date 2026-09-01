import os
import shutil

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class MpgtxConan(ConanFile):
    name = "mpgtx"
    version = "1.3.1"
    description = (
        "mpgtx is a command-line MPEG toolbox: it can split, join, "
        "demultiplex and inspect MPEG audio/video/system streams, and edit "
        "ID3v1 tags (tagmp3)."
    )
    license = "GPL-2.0-only"
    homepage = "https://mpgtx.sourceforge.net/"
    topics = ("mpeg", "mp3", "audio", "video", "splitter", "joiner", "demux", "id3")
    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "largefile": [True, False],
    }
    default_options = {
        "largefile": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        apply_conandata_patches(self)

    def _cxx(self):
        # R33: compiler comes from the Conan conf, never hardcoded paths.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cxx = compilers.get("cpp")
        if cxx:
            return cxx
        # Dynamic fallback for hosts where the conf is not set.
        return shutil.which("clang++") or "clang++"

    def build(self):
        # mpgtx 1.3.1 ships a hand-written configure script (NOT autotools:
        # no configure.ac/Makefile.am), which generates the real Makefile.
        # Hence we drive configure + make directly instead of using
        # AutoToolsBuildEnvironment. The patched configure honors CXX.
        # Environment() + .vars(scope="build") is the Conan 2 way to inject
        # CXX into the build (run() env= accepts only a list in Conan 2).
        env = Environment()
        env.define("CXX", self._cxx())
        with env.vars(self, scope="build").apply():
            args = "--prefix=/usr"
            if not self.options.largefile:
                args += " --no-LFS"
            self.run(f"./configure {args}", cwd=self.source_folder)
            # R9: -j1
            self.run("make -j1", cwd=self.source_folder)

    def package(self):
        # Stage into the package folder via DESTDIR (added by the patch):
        # installs the binary, its 6 symlinks and the man pages under usr/.
        self.run(
            f"make install DESTDIR={self.package_folder}",
            cwd=self.source_folder,
        )

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["usr/bin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "usr", "bin")
        )
