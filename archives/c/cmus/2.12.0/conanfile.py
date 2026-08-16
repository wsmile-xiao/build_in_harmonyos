#!/usr/bin/env python3
"""Conan recipe for cmus 2.12.0, a console music player."""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class CmusConan(ConanFile):
    name = "cmus"
    version = "2.12.0"
    description = "Small, fast and powerful console music player"
    license = "GPL-2.0-or-later"
    homepage = "https://cmus.github.io/"
    url = "https://github.com/cmus/cmus"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires("ncurses/6.5", options={"shared": False})

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"cmus supports Linux and OHOS only, got {self.settings.os}"
            )

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.generate()

    def _configure_args(self):
        ncurses = self.dependencies["ncurses"].cpp_info
        if not ncurses.includedirs or not ncurses.libdirs:
            raise ConanInvalidConfiguration("ncurses does not export include/lib directories")

        ncurses_libs = " ".join(
            os.path.join(ncurses.libdirs[0], f"lib{lib}.a") for lib in ncurses.libs
        )
        args = [
            f"prefix={self.package_folder}",
            f"bindir={os.path.join(self.package_folder, 'bin')}",
            f"datadir={os.path.join(self.package_folder, 'share')}",
            f"libdir={os.path.join(self.package_folder, 'lib')}",
            f"mandir={os.path.join(self.package_folder, 'share', 'man')}",
            f"docdir={os.path.join(self.package_folder, 'share', 'doc', 'cmus')}",
            f"NCURSES_CFLAGS=-I{ncurses.includedirs[0]}",
            f"NCURSES_LIBS={ncurses_libs}",
            "CONFIG_WAV=y",
            "CONFIG_CUE=y",
        ]
        disabled = (
            "AAC ALSA AO ARTS CDDB CDIO COREAUDIO FFMPEG FLAC JACK MAD MIKMOD "
            "MODPLUG MP4 MPC MPRIS OPUS OSS PULSE ROAR SAMPLERATE SNDIO SUN "
            "VORBIS VTX WAVEOUT WAVPACK BASS AAUDIO DISCID"
        )
        args.extend(f"CONFIG_{name}=n" for name in disabled.split())
        return args

    def _work_folder(self):
        # basic_layout copies this in-source Make project to the parent of
        # build-release; cmus does not support an out-of-source build.
        return os.path.dirname(self.build_folder)

    def build(self):
        apply_conandata_patches(self)
        args = " ".join(f"'{arg}'" for arg in self._configure_args())
        # cmus builds and immediately runs Doc/ttman. In a true cross-build,
        # require the build profile to provide a native CC_FOR_BUILD; silently
        # falling back to the target compiler would create an unusable tool.
        if cross_building(self):
            self.run(
                'test -n "${CC_FOR_BUILD:-}" || '
                '{ echo "CC_FOR_BUILD is required for cmus cross-builds" >&2; exit 1; }',
                cwd=self._work_folder(),
                env="conanbuild",
            )
            host_compiler = "$CC_FOR_BUILD"
        else:
            host_compiler = "$CC"
        self.run(
            f'./configure LD="$CC" HOSTCC="{host_compiler}" '
            f'HOSTLD="{host_compiler}" {args}',
            cwd=self._work_folder(),
            env="conanbuild",
        )
        self.run("make -j1", cwd=self._work_folder(), env="conanbuild")

    def package(self):
        work = self._work_folder()
        copy(self, "cmus", src=work,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "cmus-remote", src=work,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "*.so", src=os.path.join(work, "ip"),
             dst=os.path.join(self.package_folder, "lib", "cmus", "ip"))
        # cmus always scans both plugin classes. Keep an empty output-plugin
        # directory for this input-only build so --plugins is warning-free.
        os.makedirs(
            os.path.join(self.package_folder, "lib", "cmus", "op"),
            exist_ok=True,
        )
        copy(self, "*", src=os.path.join(work, "data"),
             dst=os.path.join(self.package_folder, "share", "cmus"))
        copy(self, "*.1", src=os.path.join(work, "Doc"),
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        copy(self, "*.7", src=os.path.join(work, "Doc"),
             dst=os.path.join(self.package_folder, "share", "man", "man7"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        if self.settings.os == "OHOS":
            objcopy = shutil.which("llvm-objcopy")
            signer = shutil.which("binary-sign-tool")
            if not objcopy or not signer:
                raise ConanInvalidConfiguration(
                    "OHOS packaging requires llvm-objcopy and binary-sign-tool"
                )
            artifacts = [
                os.path.join(self.package_folder, "bin", "cmus"),
                os.path.join(self.package_folder, "bin", "cmus-remote"),
                os.path.join(self.package_folder, "lib", "cmus", "ip", "wav.so"),
                os.path.join(self.package_folder, "lib", "cmus", "ip", "cue.so"),
            ]
            for artifact in artifacts:
                if not os.path.isfile(artifact):
                    raise ConanInvalidConfiguration(f"expected artifact missing: {artifact}")
                signed = artifact + ".signed"
                self.run(f'"{objcopy}" --remove-section .codesign "{artifact}"',
                         ignore_errors=True)
                self.run(
                    f'"{signer}" sign -inFile "{artifact}" '
                    f'-outFile "{signed}" -selfSign 1'
                )
                os.replace(signed, artifact)
                os.chmod(artifact, 0o755)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
