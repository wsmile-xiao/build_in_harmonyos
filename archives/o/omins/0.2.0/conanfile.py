#!/usr/bin/env python3
"""Conan recipe — Omins 0.2.0 LADSPA plugins (Autotools)."""

import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class OminsConan(ConanFile):
    name = "omins"
    version = "0.2.0"
    description = "LADSPA plugins for modular synthesizers"
    license = "GPL-2.0-or-later"
    homepage = "https://www.nongnu.org/om-synth/omins.html"
    url = "https://www.nongnu.org/om-synth/omins.html"
    topics = ("ladspa", "audio", "plugin", "synthesizer", "dsp")
    package_type = "shared-library"

    settings = "os", "compiler", "build_type", "arch"

    _expected_plugins = (
        "adenv.so",
        "adenv_lvl.so",
        "comparison_4440.so",
        "dahdsr_fexp.so",
        "dahdsr_hexp.so",
        "fast_crossfade_4410.so",
        "formant_filter_4300.so",
        "hz_voct_4200.so",
        "masher_4310.so",
        "multiplexer_4420.so",
        "power_4400.so",
        "prob_switch_2667.so",
        "range_trans_4210.so",
        "sample_and_hold_4430.so",
        "signal_abs_2669.so",
        "slew_limiter_2743.so",
        "slide_2741.so",
        "waveguide_mesh_2670.so",
    )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("ladspa-sdk/1.17")

    def build_requirements(self):
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("omins supports Linux and OHOS")
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        deps = AutotoolsDeps(self)
        deps.generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--with-ladspa-dir=/lib/ladspa")
        if self.settings.os == "OHOS":
            tc.configure_args.extend(
                (
                    "--build=aarch64-unknown-linux-gnu",
                    "--host=aarch64-unknown-linux-ohos",
                )
            )
        tc.generate()
        if self.settings.os == "OHOS":
            shell = Environment()
            shell.define_path("CONFIG_SHELL", "/system/bin/sh")
            shell.define_path("SHELL", "/system/bin/sh")
            shell.vars(self, scope="build").save_script("omins_ohos_shell")

    def _relax_configure_umask(self):
        """Make config.status scratch files readable on HarmonyOS HMDFS."""
        configure = os.path.join(self.source_folder, "configure")
        with open(configure, encoding="utf-8", errors="surrogateescape") as src:
            text = src.read()
        occurrences = text.count("umask 077")
        if occurrences == 0:
            raise ConanException(
                "generated configure no longer contains the expected umask 077"
            )
        with open(configure, "w", encoding="utf-8", errors="surrogateescape") as dst:
            dst.write(text.replace("umask 077", "umask 022"))
        self.output.info(
            "configure: changed {} scratch-directory umask occurrence(s) "
            "from 077 to 022".format(occurrences)
        )

    def build(self):
        apply_conandata_patches(self)
        self.run("autoreconf -fi", cwd=self.source_folder, env="conanbuild")
        if self.settings.os == "OHOS":
            self._relax_configure_umask()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        autotools.make(target="check", args=["-j1"])

    def package(self):
        plugin_src = os.path.join(self.build_folder, "src", ".libs")
        built = tuple(
            sorted(
                os.path.basename(path)
                for path in glob.glob(os.path.join(plugin_src, "*.so"))
            )
        )
        if built != self._expected_plugins:
            raise ConanException(
                "unexpected Omins plugin set: expected {}, got {}".format(
                    list(self._expected_plugins), list(built)
                )
            )
        plugin_dst = os.path.join(self.package_folder, "lib", "ladspa")
        os.makedirs(plugin_dst, exist_ok=True)
        for plugin in self._expected_plugins:
            source = os.path.realpath(os.path.join(plugin_src, plugin))
            if not os.path.isfile(source):
                raise ConanException("missing libtool module target: {}".format(source))
            shutil.copy2(source, os.path.join(plugin_dst, plugin))
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.resdirs = ["lib/ladspa"]
        self.runenv_info.prepend_path(
            "LADSPA_PATH", os.path.join(self.package_folder, "lib", "ladspa")
        )
