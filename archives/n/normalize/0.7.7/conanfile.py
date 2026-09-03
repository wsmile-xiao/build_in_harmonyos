#!/usr/bin/env python3
"""Conan recipe for normalize 0.7.7 — audio volume normalization CLI.

normalize is a command-line tool (C, autotools) that measures and adjusts the
volume level of audio files.  It links against the audiofile library for
multi-format file I/O.  Artifacts: bin/normalize, bin/normalize-mp3 wrapper
script and man pages (R38: commands.json declares the executables).

HarmonyOS notes:
  * The 2005-era config.guess does not recognise `aarch64:HarmonyOS:*:*`
    (uname -s = HarmonyOS) — patched to emit aarch64-unknown-linux-gnu so the
    native run of configure stays in non-cross mode (correct endianness and
    type sizes are measured, not guessed).
  * configure's config.status creates its scratch dir with `umask 077`;
    on HMDFS that yields a dir owned by another uid that the build user cannot
    write into ("Permission denied" on confstatXXXXXX) — patched to umask 000.
  * audiofile is packaged as a static lib built from mixed C/C++ objects; the
    C link driver omits libc++, so -lc++ is appended to LIBS.
  * The bundled AM_PATH_AUDIOFILE macro locates audiofile through the legacy
    `audiofile-config` script (not pkg-config).  The packaged audiofile does
    not ship one, so generate() writes a private shim that reports the flags
    for the conan-installed audiofile package.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class NormalizeConan(ConanFile):
    name = "normalize"
    version = "0.7.7"
    description = "Audio volume normalization tool (wav/aiff/au/etc.)"
    license = "GPL-2.0-or-later"
    homepage = "https://savannah.nongnu.org/projects/normalize/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("audio", "volume", "normalize", "wav")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"normalize is adapted for Linux/OHOS, got {self.settings.os}"
            )
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                f"normalize/0.7.7 is validated for OHOS armv8, got {self.settings.arch}"
            )

    def requirements(self):
        # audiofile provides the multi-format audio I/O backend.
        self.requires("audiofile/0.3.6")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        # audiofile's legacy AM_PATH_AUDIOFILE macro needs an `audiofile-config`
        # script on PATH (or $AUDIOFILE_CONFIG); the packaged audiofile does not
        # ship one, so write a private shim pointing at the conan dependency.
        af = self.dependencies["audiofile"]
        af_pkg = af.package_folder
        shim_dir = os.path.join(self.build_folder, "prefix", "bin")
        os.makedirs(shim_dir, exist_ok=True)
        shim = os.path.join(shim_dir, "audiofile-config")
        with open(shim, "w", encoding="utf-8") as f:
            f.write("#!/bin/sh\n")
            f.write(f'prefix="{af_pkg}"\n')
            f.write('case "$1" in\n')
            f.write("  --prefix|--exec-prefix) echo \"$prefix\" ;;\n")
            f.write('  --version) echo "0.3.6" ;;\n')
            f.write('  --cflags) echo "-I$prefix/include" ;;\n')
            f.write('  --libs) echo "-L$prefix/lib -laudiofile" ;;\n')
            f.write("  *) exit 1 ;;\n")
            f.write("esac\n")
        os.chmod(shim, 0o755)

        tc = AutotoolsToolchain(self)
        env = tc.environment()
        env.prepend_path("PATH", shim_dir)
        env.define("AUDIOFILE_CONFIG", shim)
        # libaudiofile.a embeds C++ objects; the C driver drops -lc++, so keep
        # it in LIBS (evaluated after the static archives on the link line).
        env.define("LIBS", "-lc++")
        tc.generate(env=env)

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j2"])
        # Upstream functional suite (8/16/24-bit WAV round-trips).  Requires
        # running the freshly built binaries; on OHOS this is a native run.
        autotools.make(target="check", args=["-j2"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
