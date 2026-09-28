import os

from conan import ConanFile
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.layout import basic_layout


class MpdasConan(ConanFile):
    name = "mpdas"
    version = "0.4.5"
    description = ("Minimalistic MPD (Music Player Daemon) now-playing "
                   "client that prints the current song and scrobbles it to "
                   "Last.fm / Libre.fm")
    license = "ISC"
    homepage = "https://50hz.ws/mpdas/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("mpd", "scrobbler", "audio", "cli")

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # ohpcd publishes these binaries as plain name/version. Repo-wide the
        # plain form is used 7101 times vs 5 times with @ohpcd/stable, and the
        # user+channel form does not resolve at all: round 1 failed with
        # "ERROR: Package 'libmpdclient/2.23@ohpcd/stable' not resolved:
        # Unable to find ... in remotes" (create-r1.log:63).
        # libmpdclient -> MPD protocol client (used by mpd.cpp)
        # libcurl      -> HTTPS for the audioscrobbler (used by audioscrobbler.cpp)
        self.requires("libmpdclient/2.23")
        self.requires("libcurl/8.5.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _dep_flags(self):
        cflags, ld = [], []
        for ref in ("libmpdclient", "libcurl"):
            info = self.dependencies[ref].cpp_info.aggregated_components()
            cflags += ["-I" + d for d in info.includedirs]
            for d in info.libdirs:
                ld += ["-L" + d, "-Wl,-rpath," + d]
            ld += ["-l" + s for s in info.libs]
            ld += ["-l" + s for s in info.system_libs]
        return " ".join(cflags), " ".join(ld)

    def build(self):
        apply_conandata_patches(self)
        # R33: the compiler comes from the Conan conf, never from bare shell
        # variables. The dotted key form (tools.build:compiler_executables:cpp)
        # raises "does not exist in configuration list" on conan 2.29.1, so the
        # dict form plus .get() is used here.
        compilers = self.conf.get("tools.build:compiler_executables",
                                  check_type=dict, default={}) or {}
        cxx = compilers.get("cpp") or "clang++"
        cflags, ld = self._dep_flags()
        # R9: -j1, because the make jobserver FIFO is unreliable on HMDFS.
        # The upstream Makefile resolves its two dependencies through backticked
        # pkg-config calls; patch 0001 turns those into the overridable
        # DEPS_CFLAGS / DEPS_LIBS variables so the flags come from the Conan
        # dependency graph instead of from .pc files that are not generated in
        # this build. CXXFLAGS keeps its upstream -DCONFDIR / -DVERSION line
        # untouched - both macros are required to compile main.cpp.
        self.run('make -j1 CXX="%s" DEPS_CFLAGS="%s" DEPS_LIBS="%s"'
                 % (cxx, cflags, ld), cwd=self.source_folder)

    def package(self):
        copy(self, "mpdas", self.source_folder,
             os.path.join(self.package_folder, "bin"))
        copy(self, "mpdas.1", self.source_folder,
             os.path.join(self.package_folder, "man", "man1"))
        copy(self, "mpdasrc.example", self.source_folder,
             os.path.join(self.package_folder, "conf"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
