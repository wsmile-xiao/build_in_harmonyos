#!/usr/bin/env python3
"""Conan recipe for jmeters 0.4.5 (upstream jMeters, Fons Adriaensen).

jMeters is a JACK client offering software models of classic analogue level
meters (VU, BBC/EBU/DIN PPM, stereo correlation).  Upstream is a bare
Makefile application: the only build file is source/Makefile (no configure
script, no CMake, no autotools) and there is no test/check target.  The
build produces one executable, `jmeters`, plus the PNG meter faces in
share/jmeters/.

This recipe follows the in-tree precedent for the same upstream family,
archives/z/zita/0.2.2 (same author, same bare-Makefile shape, almost the
same dependency set), and archives/a/aeolus/0.10.4 / archives/a/aliki/0.3.0
for the consumer-side test.

OHOS portability notes (see notes.md):
  - Upstream hardcodes `CXXFLAGS += -march=native`; patches/0001 strips it so
    the Conan profile (ohos-aarch64) controls code generation.
  - The build environment on HarmonyOS PC has no executable bare `install`
    on PATH (and ~/usr/local/bin/install is not executable, so it also
    shadows /bin/install); the patch turns the install rule into $(INSTALL)
    and package() passes INSTALL=/bin/install.
  - clthreads.h guards `pthread_cancel` (absent in the OHOS libc) behind
    CLTHREADS_NO_PTHREAD_CANCEL; the build passes that macro.
  - The Makefile probes freetype2 cflags with `pkgconf`, which is not on the
    OHOS PATH; every dependency's include/lib dir is injected through
    CPPFLAGS/LDFLAGS in the build environment instead.  The Makefile
    accumulates its own flags with `+=`, so they must stay in the environment
    rather than on the make command line.
  - Dependency versions are pinned to the published OHOS recipes; the
    libx11/libxext/fontconfig overrides mirror zita 0.2.2 (the published
    cairo/clxclient layers pin those versions).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class JmetersConan(ConanFile):
    name = "jmeters"
    version = "0.4.5"
    description = "jMeters 0.4.5: JACK audio level meters (VU, BBC/EBU/DIN PPM, correlation) with an X11/Cairo GUI"
    license = "GPL-2.0-or-later"
    homepage = "https://kokkinizita.linuxaudio.org/linuxaudio/"
    url = "https://kokkinizita.linuxaudio.org/linuxaudio/"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("clthreads/2.4.0")
        self.requires("clxclient/3.9.2")
        self.requires("jack/1.9.22")
        self.requires("libsndfile/1.2.2")
        self.requires("libpng/1.6.58")
        self.requires("cairo/1.18.4.1")
        self.requires("freetype/2.14.3")
        # --- version unification forced by the published OHOS recipes ---
        # clxclient/3.9.2 pins libxft/2.3.8; cairo's OHOS layer pins
        # libx11/libxext 6.4.0; the libxft chain pulls fontconfig 2.18.3.
        self.requires("libxft/2.3.8", override=True)
        self.requires("libx11/6.4.0", override=True)
        self.requires("libxext/6.4.0", override=True)
        self.requires("fontconfig/2.18.3", override=True)

    def layout(self):
        basic_layout(self)

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("jmeters/0.4.5 supports Linux and OHOS only")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _sdk_llvm_lib_dir(self, cxx):
        """E132: the SDK's lld dynamically needs libxml2.so.16, whose RUNPATH
        uses $ORIGIN/../lib; musl's loader does not expand $ORIGIN there, so on
        some workers linking fails unless the SDK llvm/lib dir is on
        LD_LIBRARY_PATH.  Returns that dir (empty when not applicable).  We must
        keep lld: binaries linked with the GNU ld from
        /data/service/hnp/bin/ld fail with Permission denied at run time in the
        OHOS sandbox."""
        try:
            real = os.path.realpath(cxx)
        except OSError:
            return ""
        llvm_lib = os.path.join(os.path.dirname(os.path.dirname(real)), "lib")
        if os.path.isfile(os.path.join(llvm_lib, "libxml2.so.16")):
            return llvm_lib
        return ""

    def generate(self):
        VirtualBuildEnv(self).generate()
        # Inject every host dependency's include/lib dirs through the build
        # environment; the Makefile accumulates CPPFLAGS/LDFLAGS with `+=`.
        env = Environment()
        incs, libs = [], []
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue  # tool requires have no host package folder
            for inc in dep.cpp_info.includedirs or []:
                incs.append("-I" + os.path.join(dep.package_folder, inc))
            for libdir in dep.cpp_info.libdirs or []:
                libs.append("-L" + os.path.join(dep.package_folder, libdir))
        if incs:
            env.append("CPPFLAGS", " ".join(incs))
        if libs:
            env.append("LDFLAGS", " ".join(libs))
        env.append("CXXFLAGS", "-DCLTHREADS_NO_PTHREAD_CANCEL")
        env.vars(self).save_script("jmeters_deps_env")

    def build(self):
        apply_conandata_patches(self)
        # R33: the compiler comes from the Conan profile conf, never from a
        # bare shell ${CXX} (empty on CI/release workers).
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cxx = compilers.get("cpp") or "clang++"
        source_dir = os.path.join(self.source_folder, "source")
        env_prefix = ""
        llvm_lib = self._sdk_llvm_lib_dir(cxx)
        if llvm_lib:
            env_prefix = 'export LD_LIBRARY_PATH="{}:${{LD_LIBRARY_PATH:-}}"; '.format(llvm_lib)
        # R9: -j1.  Target `jmeters` (the only artifact of this package).
        self.run(
            env_prefix + 'make -C "{}" -j1 CXX="{}" jmeters'.format(source_dir, cxx),
            env=["conanbuild", "jmeters_deps_env"],
        )

    def package(self):
        source_dir = os.path.join(self.source_folder, "source")
        # PREFIX=/ -> bin/jmeters and share/jmeters/*.png under DESTDIR.
        # The install rule needs the source/ and share/ sibling layout that
        # upstream ships (`../share/*`), which strip_root=True preserves.
        self.run(
            'make -C "{}" install DESTDIR="{}" PREFIX=/ INSTALL=/bin/install'.format(
                source_dir, self.package_folder
            ),
            env=["conanbuild", "jmeters_deps_env"],
        )

    def package_info(self):
        # Application package: no cpp_info.libs.  The packaged artifact is the
        # jmeters executable (declared through commands.json per R38).
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
