#!/usr/bin/env python3
"""Conan recipe for the SWFTools 0.9.2 command-line suite."""

import os
import shlex
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import load_toolchain_args
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain


class SwftoolsConan(ConanFile):
    name = "swftools"
    version = "0.9.2"
    description = "Command-line tools for creating and manipulating SWF files"
    license = "GPL-2.0-or-later"
    homepage = "http://www.swftools.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    _tools = (
        "wav2swf",
        "png2swf",
        "swfcombine",
        "swfstrings",
        "swfextract",
        "swfdump",
        "swfc",
        "swfbbox",
        "font2swf",
        "swfrender",
        "as3compile",
        "swfbytes",
        "ttftool",
    )

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"swftools supports Linux and OHOS, got {self.settings.os}"
            )
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("OHOS builds require armv8/aarch64")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("zlib/1.3.1")

    def layout(self):
        # Upstream explicitly rejects --srcdir, so configure and make must run
        # in the copied source tree.
        self.folders.source = "."
        self.folders.build = "."
        self.folders.generators = "conan"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True, verify=True)

    def generate(self):
        deps = AutotoolsDeps(self)
        deps.generate()

        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.append("--disable-lame")
        if str(self.settings.os) == "OHOS":
            # The 2010 config.guess does not know HarmonyOS. This is a native
            # build, so host defaults to the supplied Linux-compatible triplet.
            toolchain.configure_args.append("--build=aarch64-unknown-linux-gnu")
        toolchain.generate()

        env = Environment()
        tmpdir = os.environ.get("TMPDIR")
        if not tmpdir:
            tmpdir = os.path.join(self.build_folder, ".conan-tmp")
            os.makedirs(tmpdir, exist_ok=True)
        env.define("TMPDIR", tmpdir)

        # Keep the first port intentionally small and reproducible. These
        # probes otherwise pick up undeclared host libraries when available.
        disabled_probes = {
            "ac_cv_lib_pdf_PDF_open_file": "no",
            "ac_cv_header_pdflib_h": "no",
            "ac_cv_lib_jpeg_jpeg_write_raw_data": "no",
            "ac_cv_header_jpeglib_h": "no",
            "ac_cv_lib_ungif_DGifOpen": "no",
            "ac_cv_lib_gif_DGifOpen": "no",
            "ac_cv_header_gif_lib_h": "no",
            "ac_cv_lib_zzip_zzip_file_open": "no",
            "ac_cv_header_zzip_lib_h": "no",
            "ac_cv_path_FREETYPE_CONFIG": "",
            "ac_cv_lib_freetype_FT_Init_FreeType": "no",
            "ac_cv_header_ft2build_h": "no",
            "ac_cv_header_freetype_freetype_h": "no",
            "ac_cv_lib_fontconfig_FcInit": "no",
            "ac_cv_header_fontconfig_h": "no",
            "ac_cv_lib_fftw3f_fftwf_plan_dft_r2c_2d": "no",
            "ac_cv_header_fftw3_h": "no",
            "ac_cv_prog_AVIFILE_CONFIG": "",
            "ac_cv_path_RUBY": "",
            "ac_cv_header_ruby_h": "no",
        }
        for key, value in disabled_probes.items():
            env.define(key, value)
        env.vars(self, scope="build").save_script("swftools_build")

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        if str(self.settings.os) == "OHOS":
            configure = os.path.join(self.source_folder, "configure")
            configure_args = load_toolchain_args(self.generators_folder).get(
                "configure_args", ""
            )
            command = shlex.join(["sh", configure])
            if configure_args:
                command = f"{command} {configure_args}"
            self.run(command, cwd=self.build_folder, env="conanbuild")
        else:
            autotools.configure()
        autotools.make(args=["-j1"])

        bin_src = os.path.join(self.build_folder, "src")
        missing = [
            tool for tool in self._tools
            if not os.path.isfile(os.path.join(bin_src, tool))
        ]
        if missing:
            raise ConanInvalidConfiguration(
                "swftools build did not produce: " + ", ".join(missing)
            )

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["-j1"])

        bin_src = os.path.join(self.build_folder, "src")
        bin_dst = os.path.join(self.package_folder, "bin")
        # Upstream builds but does not install these two diagnostic tools.
        for tool in ("swfbytes", "ttftool"):
            copy(
                self,
                tool,
                src=bin_src,
                dst=bin_dst,
                keep_path=False,
            )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

        missing = [
            tool for tool in self._tools
            if not os.path.isfile(os.path.join(bin_dst, tool))
        ]
        if missing:
            raise ConanInvalidConfiguration(
                "swftools package is missing: " + ", ".join(missing)
            )

        if str(self.settings.os) == "OHOS":
            self._sign_binaries(bin_dst)
        for tool in self._tools:
            os.chmod(os.path.join(bin_dst, tool), 0o755)

    def _sign_binaries(self, bin_dir):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        sign_tool = executables.get(
            "sign_tool", "/data/service/hnp/bin/binary-sign-tool"
        )
        objcopy = executables.get(
            "objcopy", "/data/service/hnp/bin/llvm-objcopy"
        )
        if not os.path.isfile(sign_tool):
            raise ConanInvalidConfiguration(
                f"HarmonyOS binary signing tool not found: {sign_tool}"
            )
        if not os.path.isfile(objcopy):
            raise ConanInvalidConfiguration(
                f"HarmonyOS objcopy tool not found: {objcopy}"
            )

        for tool in self._tools:
            binary = os.path.join(bin_dir, tool)
            subprocess.run(
                [objcopy, "--remove-section", ".codesign", binary],
                check=True,
            )
            signed = binary + ".signed"
            subprocess.run(
                [
                    sign_tool,
                    "sign",
                    "-inFile",
                    binary,
                    "-outFile",
                    signed,
                    "-selfSign",
                    "1",
                ],
                check=True,
            )
            os.replace(signed, binary)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
