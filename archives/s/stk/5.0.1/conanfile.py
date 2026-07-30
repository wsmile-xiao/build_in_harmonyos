#!/usr/bin/env python3
"""Conan recipe for stk 5.0.1.

STK's portable DSP classes live in src/. Realtime backends and examples are
left out so the package has no ALSA/JACK/CoreAudio/device dependency on OHOS.
"""
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.layout import basic_layout


class StkConan(ConanFile):
    name = "stk"
    version = "5.0.1"
    description = "Audio signal synthesis and processing toolkit in C++"
    license = "MIT"
    homepage = "https://ccrma.stanford.edu/software/stk/"
    url = "https://ccrma.stanford.edu/software/stk/"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")
        self.folders.build = "."

    def requirements(self):
        pass

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _compiler(self):
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        return compilers.get("cpp", "clang++")

    def _build_triplet(self):
        arch = str(self.settings.arch)
        arch_map = {
            "x86": "i686",
            "x86_64": "x86_64",
            "armv7": "arm",
            "armv8": "aarch64",
            "armv8.3": "aarch64",
            "riscv64": "riscv64",
        }
        return f"{arch_map.get(arch, arch)}-unknown-linux-gnu"

    def build(self):
        apply_conandata_patches(self)

        cxx = self._compiler()
        config_shell = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        os.environ["CXX"] = cxx
        os.environ["CONFIG_SHELL"] = config_shell

        configure_args = [
            "--disable-realtime",
            "--disable-shared",
            "--enable-static",
            "--prefix=/",
        ]
        if str(self.settings.os) == "OHOS":
            # HMDFS rejects Autotools config.status temp files created with umask 077.
            replace_in_file(
                self,
                os.path.join(self.source_folder, "configure"),
                "umask 077",
                "umask 022",
            )
            configure_args.append(f"--build={self._build_triplet()}")

        self.run(
            f'"{config_shell}" ./configure {" ".join(configure_args)}',
            cwd=self.source_folder,
        )
        self.run("make -C src -j1", cwd=self.source_folder)

    def package(self):
        copy(self, "libstk.a", src=os.path.join(self.source_folder, "src"),
             dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        portable_headers = [
            "ADSR.h", "Asymp.h", "BandedWG.h", "BeeThree.h", "BiQuad.h",
            "Blit.h", "BlitSaw.h", "BlitSquare.h", "BlowBotl.h",
            "BlowHole.h", "BowTable.h", "Bowed.h", "Brass.h",
            "Chorus.h", "Clarinet.h", "Cubic.h", "Delay.h", "DelayA.h",
            "DelayL.h", "Drummer.h", "Echo.h", "Effect.h", "Envelope.h",
            "FM.h", "FMVoices.h", "FileLoop.h", "FileRead.h",
            "FileWrite.h", "FileWvIn.h", "FileWvOut.h", "Filter.h",
            "Fir.h", "Flute.h", "FormSwep.h", "FreeVerb.h", "Function.h",
            "Generator.h", "Granulate.h", "Guitar.h", "HevyMetl.h",
            "Iir.h", "Instrmnt.h", "JCRev.h", "JetTable.h",
            "LentPitShift.h", "Mandolin.h", "Mesh2D.h", "MidiFileIn.h",
            "Modal.h", "ModalBar.h", "Modulate.h", "Moog.h", "NRev.h",
            "Noise.h", "OnePole.h", "OneZero.h", "PRCRev.h",
            "PercFlut.h", "Phonemes.h", "PitShift.h", "Plucked.h",
            "PoleZero.h", "Recorder.h", "ReedTable.h", "Resonate.h",
            "Rhodey.h", "Sampler.h", "Saxofony.h", "Shakers.h",
            "Simple.h", "SineWave.h", "SingWave.h", "Sitar.h",
            "Skini.h", "Sphere.h", "StifKarp.h", "Stk.h", "TapDelay.h",
            "TubeBell.h", "Twang.h", "TwoPole.h", "TwoZero.h",
            "Vector3D.h", "VoicForm.h", "Voicer.h", "Whistle.h",
            "Wurley.h", "WvIn.h", "WvOut.h",
        ]
        include_src = os.path.join(self.source_folder, "include")
        include_dst = os.path.join(self.package_folder, "include", "stk")
        for header in portable_headers:
            copy(self, header, src=include_src, dst=include_dst, keep_path=False)
        copy(self, "*", src=os.path.join(self.source_folder, "rawwaves"),
             dst=os.path.join(self.package_folder, "share", "stk", "rawwaves"),
             keep_path=True)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["stk"]
        self.cpp_info.system_libs = ["m"]
