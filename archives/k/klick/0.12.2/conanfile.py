#!/usr/bin/env python3
"""Conan recipe for klick 0.12.2 — SCons-built JACK metronome.

klick is a command-line JACK metronome (tempomap, pattern language, WAV
sample export). Upstream builds with SCons (top-level SConstruct, no
configure/CMake). The optional OSC (liblo) and RUBBERBAND (rubberband)
features are compiled OFF: liblo and rubberband have no published recipe on
the ohpcd index; core jack/sndfile/samplerate functionality is unaffected
(upstream defaults: RUBBERBAND=False; OSC is opt-out and recorded as a
known limitation in notes.md). The portability patch replaces the built-in
pkg-config probes with the KLICK_DEPFLAGS injection slot (Conan supplies
every include/lib search path explicitly), keeps the -l link list explicit
and defines HAVE_SNDFILE_OGG unconditionally (Conan libsndfile ships
vorbis/ogg). A second portability patch (0002) moves the SConstruct onto the
SCons 4 build-variable API - Variables/PathVariable/BoolVariable plus an
explicit ARGUMENTS hand-off - and lets it take CC/CXX from the environment,
because SCons 4 dropped the legacy Options spellings and no longer pushes
command-line NAME=value pairs into the Environment. A third portability
patch (0003) spells three in-class float/double constants as constexpr,
which is what the C++ standard requires and what clang enforces (g++ only
accepts the bare form as a GNU extension). The compiler comes from the
Conan profile (R33: key "cpp" in tools.build:compiler_executables). boost is
used headers-only upstream (shared_ptr / shared_array / lambda; README:
"Boost (headers only)"), and the compile definitions that the dependencies
declare for their own headers (notably boost/1.84.0's
BOOST_SP_NO_PTHREAD_SETCANCELSTATE) are forwarded to SCons by this recipe:
CMake and Autotools recipes get them from the Conan generators for free, a
hand-rolled SCons command line does not.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class KlickConan(ConanFile):
    name = "klick"
    version = "0.12.2"
    package_type = "application"
    description = "Advanced command-line metronome for JACK"
    license = "GPL-2.0-or-later"
    homepage = "https://das.nasophon.de/klick/"
    url = ""  # CI fills this

    settings = "os", "arch", "compiler", "build_type"

    # SCons build helper (gpsd 3.26 pattern): installed into an isolated
    # prefix in generate() from the configured community index, so build()
    # itself stays free of network/pip calls.
    _SCONS_VERSION = "4.10.1"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("klick supports Linux and OHOS only")
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("klick supports OHOS armv8 only")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # boost is headers-only upstream (shared_ptr / shared_array /
        # lambda; no -lboost link anywhere in SConstruct or sources).
        self.requires("boost/1.84.0", transitive_headers=True)
        self.requires("jack/1.9.22", transitive_headers=True)
        self.requires("libsndfile/1.2.2", transitive_headers=True)
        self.requires("libsamplerate/0.2.2", transitive_headers=True)
        # OSC(True)/RUBBERBAND(False) are optional upstream features built
        # OFF (see module docstring): liblo / rubberband are not published
        # on the ohpcd index (verified 2026-09-26 with a conan list query
        # against the ohpcd remote).

    def layout(self):
        # 刻意不套任何 layout 布局 helper（gpsd 3.26 同款）：SCons 从顶层
        # SConstruct 树内构建，而 conan 的 build()/package() 都以 build_folder
        # 为 cwd 执行（conan/internal/methods.py 里的 chdir）。用布局 helper
        # 会把源码留在 <base>/、把构建挪到 <base>/build-release/，SCons 在空
        # 构建目录里向上找不到 SConstruct，直接 "No SConstruct file found"。
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Isolated install prefix for scons, scoped to this build's env only.
        scons_prefix = os.path.join(self.build_folder, "_scons_env")
        os.makedirs(scons_prefix, exist_ok=True)
        self.run(
            f"python3 -m pip install --quiet --no-input "
            f"--target={scons_prefix} scons=={self._SCONS_VERSION}",
            env="build",
        )
        # OHOS has no /bin/sh — patch scons posix platform to /system/bin/sh.
        # Done once here (in generate) instead of inside build() (R33).
        self.run(
            f"PYTHONPATH={scons_prefix} python3 -c \""
            r"import SCons.Platform.posix as m;"
            r"f=m.__file__;"
            r"s=open(f).read();"
            r"old=r\"env['SHELL']          = 'sh'\";"
            r"new=r\"env['SHELL']          = '/system/bin/sh'\";"
            r"open(f,'w').write(s.replace(old,new) if old in s else s);"
            r"print('patched', f if old in s else '(noop)')"
            "\"",
            env="build",
        )
        vb = VirtualBuildEnv(self)
        vb.generate()
        # Expose scons to subsequent build()/package() via PYTHONPATH.
        env = Environment()
        env.define_path("PYTHONPATH", scons_prefix)
        env.vars(self).save_script("scons_env")

    def _compiler_cxx(self):
        """C++ compiler taken from the Conan profile conf.

        R33: never a bare shell ${CXX} (empty on CI/release workers); the
        profile key in this repository is "cpp" (not "cxx").
        """
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return compilers.get("cpp", "clang++") if compilers else "clang++"

    def _compiler_cc(self):
        """C compiler taken from the Conan profile conf (key "c")."""
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return compilers.get("c", "clang") if compilers else "clang"

    @staticmethod
    def _dependency_defines(cpp_info):
        """Compile definitions a dependency declares for its own headers.

        Both the package level cpp_info and every component carry them;
        boost/1.84.0, for instance, declares
        BOOST_SP_NO_PTHREAD_SETCANCELSTATE on its boost_headers component,
        because the OHOS libc headers do not declare the pthread
        cancellation API that boost/core/detail/sp_thread_sleep.hpp calls.
        """
        defines = list(getattr(cpp_info, "defines", None) or [])
        components = getattr(cpp_info, "components", None)
        try:
            for component in (components or {}).values():
                defines.extend(list(getattr(component, "defines", None) or []))
        except AttributeError:
            pass
        # keep order, drop duplicates (a package may repeat a root define
        # on several components)
        return list(dict.fromkeys(defines))

    def _depflags(self):
        """Flags every declared dependency contributes: -I/-L search paths
        and -D compile definitions.

        They are injected through the KLICK_DEPFLAGS slot added by
        patches/0001-source-SConstruct.patch, which replaces upstream's
        pkg-config probes: Conan supplies every include and lib search path
        and every header-required definition explicitly (the recipe never
        relies on a system .pc db). Forwarding the definitions matters on
        OHOS, where boost/1.84.0 expects consumers to define
        BOOST_SP_NO_PTHREAD_SETCANCELSTATE (see _dependency_defines); the
        generators that hand-rolled SCons builds do not use would normally
        do that.
        """
        depflags = ""
        for _, dependency in self.dependencies.items():
            if not dependency.package_folder:
                continue
            for incdir in dependency.cpp_info.includedirs:
                path = incdir
                if not os.path.isabs(path):
                    path = os.path.join(dependency.package_folder, incdir)
                depflags += " -I" + path
            for libdir in dependency.cpp_info.libdirs:
                path = libdir
                if not os.path.isabs(path):
                    path = os.path.join(dependency.package_folder, libdir)
                depflags += " -L" + path
            for define in self._dependency_defines(dependency.cpp_info):
                depflags += " -D" + define
        return depflags

    def build(self):
        apply_conandata_patches(self)
        # The SCons command line carries the CXX override, the two optional
        # features built OFF (OSC/RUBBERBAND) and PREFIX=/ so that the install
        # step lands bin/ + share/klick at the DESTDIR root.
        # CC/CXX are passed as environment variables, not as SCons command
        # line arguments: probed against SCons 4.10.1 on the build host, a
        # command-line CXX=... only lands in ARGUMENTS and never reaches the
        # Environment, while patch 0002 makes the SConstruct read them from
        # os.environ at Environment() construction time.
        self.run(
            f'KLICK_DEPFLAGS="{self._depflags()}" '
            f'CC="{self._compiler_cc()}" CXX="{self._compiler_cxx()}" '
            f'python3 -m SCons --jobs=2 OSC=0 RUBBERBAND=0 PREFIX=/'
        )

    def package(self):
        # DESTDIR + PREFIX=/ collapses the install onto the Conan package
        # root: <pkg>/bin/klick + <pkg>/share/klick/samples/*.wav (the click
        # sample bank ships with the package, mirroring upstream layout).
        # Same CXX and same KLICK_DEPFLAGS as build(): SCons keys its build
        # cache on the command line, so a bare "clang++" here (or an empty
        # injection slot) would make every object look stale and recompile
        # the whole program inside package().
        self.run(
            f'KLICK_DEPFLAGS="{self._depflags()}" '
            f'CC="{self._compiler_cc()}" CXX="{self._compiler_cxx()}" '
            f'python3 -m SCons install --jobs=2 OSC=0 RUBBERBAND=0 '
            f'PREFIX=/ DESTDIR="{self.package_folder}"'
        )

    def package_info(self):
        # klick is a standalone tool; it exports no libraries for consumers.
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
