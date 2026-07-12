#!/usr/bin/env python3
"""Conan recipe for ffprobe 8.1.2 on HarmonyOS PC (aarch64).

ffprobe is a media stream analysis tool from the FFmpeg project.
This recipe builds only ffprobe (ffmpeg and ffplay are disabled).

Source: FFmpeg 8.1.2 tarball (ffprobe is part of FFmpeg source)
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, chdir
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class FfprobeConan(ConanFile):
    name = "ffprobe"
    version = "8.1.2"
    description = "ffprobe - media stream analysis tool from FFmpeg"
    license = "GPL-2.0-or-later"
    homepage = "https://ffmpeg.org"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # R33: Get compiler from Conan profile conf
        compiler_executables = self.conf.get("tools.build:compiler_executables", default={})
        cc = compiler_executables.get("c", "clang") if compiler_executables else "clang"

        configure_cmd = (
            f'./configure'
            f' --cc={cc}'
            f' --prefix=/'
            f' --enable-gpl'
            f' --disable-doc'
            f' --disable-shared'
            f' --enable-static'
            f' --disable-vulkan'
            f' --disable-ffmpeg'
            f' --disable-ffplay'
            # Reduce build scope to avoid OOM (Error 137 / Signal 9)
            # ffprobe only needs demuxers, decoders, parsers, protocols
            f' --disable-encoders'
            f' --disable-muxers'
            f' --disable-bsfs'
            f' --disable-avdevice'
            f' --disable-avfilter'
        )

        with chdir(self, self.source_folder):
            self.run(configure_cmd, env="conanbuild")
            self.run("make -j1", env="conanbuild")

    def package(self):
        with chdir(self, self.source_folder):
            self.run(f'make install DESTDIR={self.package_folder}', env="conanbuild")
        # Sign ELF binaries for HarmonyOS (required for execution)
        bin_dir = os.path.join(self.package_folder, "bin")
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        is_ohos = self.settings.os == "OHOS"
        if os.path.isdir(bin_dir):
            for name in os.listdir(bin_dir):
                fpath = os.path.join(bin_dir, name)
                if not os.path.isfile(fpath):
                    continue
                try:
                    # Step 1: Remove old .codesign section
                    r_obj = subprocess.run(
                        [objcopy, "--remove-section", ".codesign", fpath],
                        capture_output=True, timeout=10)
                    if r_obj.returncode != 0:
                        self.output.warn(f"objcopy failed for {name} (rc={r_obj.returncode}), skipping signing")
                        if is_ohos:
                            raise RuntimeError(f"objcopy failed on HarmonyOS, ELF signing is required: {name}")
                        continue
                    # Step 2: Sign with binary-sign-tool
                    tmp = fpath + ".signed.tmp"
                    r = subprocess.run(
                        [sign_tool, "sign", "-inFile", fpath, "-outFile", tmp, "-selfSign", "1"],
                        capture_output=True, timeout=30)
                    if r.returncode == 0 and os.path.exists(tmp):
                        os.replace(tmp, fpath)
                        os.chmod(fpath, 0o755)
                    else:
                        msg = f"ELF signing failed for {name} (rc={r.returncode})"
                        if is_ohos:
                            raise RuntimeError(msg)
                        self.output.warn(msg)
                except subprocess.TimeoutExpired:
                    msg = f"ELF signing timed out for {name}"
                    if is_ohos:
                        raise RuntimeError(msg)
                    self.output.warn(msg)
                except (FileNotFoundError, PermissionError) as e:
                    msg = f"ELF signing tool error for {name}: {e}"
                    if is_ohos:
                        raise RuntimeError(msg)
                    self.output.warn(msg)

    def package_info(self):
        # Only list libraries actually built (avdevice/avfilter/postproc disabled)
        self.cpp_info.libs = [
            "avformat", "avcodec",
            "avutil", "swscale", "swresample",
        ]
        self.cpp_info.bindirs = ["bin"]
