#!/usr/bin/env python3
"""Conan recipe for unpaper 7.0.0 on HarmonyOS PC (aarch64).

unpaper is a post-processing tool for scanned sheets of paper. It deskews,
crops and cleans page scans, reading/writing PBM/PPM/PGM/PNG images through
FFmpeg's libavformat/libavcodec/libavutil.

OHOS-specific adaptations:
  - FFmpeg is available neither as a Conan package nor as a system library on
    OHOS, so a minimal *static* FFmpeg (avformat/avcodec/avutil/swresample,
    with zlib-backed PNG) is built in-tree from the official FFmpeg 8.1.2
    tarball, exposing only the image codecs unpaper needs (ppm/pgm/pbm/png/
    rawvideo decoders+encoders, image2 muxer/demuxer, file protocol).
  - FFmpeg's configure receives a portability patch adding a `harmonyos`
    target_os case (same FFmpeg 8.1.2 as the ffprobe recipe).
  - The upstream Meson build is intentionally bypassed: Meson would also
    require sphinx-build (man page) and pytest+PIL (test suite), neither of
    which is present on the OHOS worker. unpaper's five C sources are instead
    compiled directly and statically linked against the just-built FFmpeg,
    exactly the sources/flags upstream's meson.build compiles.
  - zlib (PNG codec dependency) is taken from the Conan zlib/1.3.1 requirement.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, patch, chdir, export_conandata_patches
from conan.tools.layout import basic_layout


class UnpaperConan(ConanFile):
    name = "unpaper"
    version = "7.0.0"
    package_type = "application"
    description = "Post-processing tool for scanned sheets of paper (deskew, crop, clean)"
    license = "GPL-2.0-only"
    homepage = "https://github.com/unpaper/unpaper"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # zlib enables FFmpeg's PNG codec (unpaper reads/writes PNG scans).
        self.requires("zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        # unpaper sources live at the source-folder root.
        get(self, **self.conan_data["sources"]["unpaper"], strip_root=True)
        # FFmpeg sources are placed in a sibling subfolder and built from there.
        get(
            self,
            **self.conan_data["sources"]["ffmpeg"],
            strip_root=True,
            destination=os.path.join(self.source_folder, "ffmpeg"),
        )

    def _cc(self):
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        return ce.get("c") or "clang"

    def _pkg_config(self, pkgconfig_dir, *args):
        pc = shutil.which("pkg-config") or "/data/service/hnp/bin/pkg-config"
        env = dict(os.environ, PKG_CONFIG_PATH=pkgconfig_dir)
        return subprocess.check_output([pc, *args], env=env, text=True).strip()

    def _extend_path_for_coreutils(self):
        # FFmpeg's configure directly invokes `tr`, `uname`, `grep`, `mktemp`,
        # etc. The OHOS rootfs may ship GNU coreutils outside the default PATH
        # (supplemental builds live in e.g. /root/usr/local/bin); FFmpeg's
        # limited bundled grep also chokes on some inputs, so we prefer the GNU
        # tools by prepending any such directory. No-op when the tools are
        # already on PATH (e.g. the real OHOS worker).
        current = os.environ.get("PATH", "").split(os.pathsep)
        for candidate in ("/root/usr/local/bin", "/usr/local/bin", "/system/bin"):
            if candidate in current:
                continue
            if os.path.isfile(os.path.join(candidate, "tr")):
                os.environ["PATH"] = candidate + os.pathsep + os.environ.get("PATH", "")
                self.output.info(f"coreutils: prepended {candidate} to PATH")
                return

    def build(self):
        self._extend_path_for_coreutils()
        cc = self._cc()
        ff_src = os.path.join(self.source_folder, "ffmpeg")
        ff_prefix = os.path.join(self.build_folder, "ffmpeg_prefix")

        zlib = self.dependencies["zlib"].cpp_info
        zinc = zlib.includedirs[0] if zlib.includedirs else ""
        zlib_libdir = zlib.libdirs[0] if zlib.libdirs else ""

        # 1) portability patch: teach FFmpeg configure about `harmonyos`.
        patch_file = os.path.join(
            self.source_folder, "patches", "0001-ffmpeg-configure-harmonyos.patch"
        )
        if os.path.isfile(patch_file):
            patch(self, base_path=ff_src, patch_file=patch_file)

        # 2) configure a minimal static FFmpeg (image codecs only).
        with chdir(self, ff_src):
            extra_cflags = f"-I{zinc}" if zinc else ""
            extra_ldflags = f"-L{zlib_libdir}" if zlib_libdir else ""
            configure_cmd = (
                "./configure"
                f" --cc={cc}"
                f" --prefix={ff_prefix}"
                " --disable-everything"
                " --enable-decoder=ppm,pgm,pbm,png,rawvideo"
                " --enable-encoder=ppm,pgm,pbm,png,rawvideo"
                " --enable-demuxer=image2,image2pipe"
                " --enable-muxer=image2,image2pipe"
                " --enable-protocol=file"
                " --enable-parser=png"
                " --enable-zlib"
                f" --extra-cflags={extra_cflags}"
                f" --extra-ldflags={extra_ldflags}"
                " --disable-doc --disable-programs --disable-shared --enable-static"
                " --disable-avdevice --disable-avfilter --disable-swscale"
                # OHOS SDK ships an incomplete vulkan.h (missing vulkan_beta.h);
                # --disable-everything does not stop autodetect, so disable it
                # explicitly (same as the ffprobe recipe). unpaper's ppm/pgm/pbm/
                # png codecs are pure software and never use vulkan hwaccel.
                " --disable-vulkan"
            )
            self.run(configure_cmd, env="conanbuild")
            self.run("make -j2", env="conanbuild")
            self.run("make install", env="conanbuild")

        # 3) generate version.h (upstream meson does this via configure_file).
        with open(os.path.join(self.source_folder, "version.h.in")) as fh:
            version_in = fh.read()
        version_h = os.path.join(self.build_folder, "version.h")
        with open(version_h, "w") as fh:
            fh.write(version_in.replace("@version@", self.version))

        # 4) FFmpeg compile/link flags via pkg-config (correct static dep order).
        pkgconfig_dir = os.path.join(ff_prefix, "lib", "pkgconfig")
        av_cflags = self._pkg_config(
            pkgconfig_dir, "--static", "--cflags", "libavformat", "libavcodec", "libavutil"
        )
        av_libs = self._pkg_config(
            pkgconfig_dir, "--static", "--libs", "libavformat", "libavcodec", "libavutil"
        )

        # 5) compile unpaper's five C sources (same set/flags as meson.build).
        sources = ["file.c", "imageprocess.c", "parse.c", "tools.c", "unpaper.c"]
        objects = []
        for src in sources:
            obj = os.path.join(self.build_folder, src.replace(".c", ".o"))
            objects.append(obj)
            self.run(
                f'"{cc}" -std=c11 -D_POSIX_C_SOURCE=200809L -Werror=int-conversion'
                f' {av_cflags} -I"{self.source_folder}" -I"{self.build_folder}"'
                f' -c "{os.path.join(self.source_folder, src)}" -o "{obj}"',
                env="conanbuild",
            )

        # 6) statically link the unpaper binary (-L<zlib> so -lz resolves).
        zlib_ld = f'-L"{zlib_libdir}"' if zlib_libdir else ""
        unpaper_bin = os.path.join(self.build_folder, "unpaper")
        self.run(
            f'"{cc}" -static -o "{unpaper_bin}" {zlib_ld}'
            f' {" ".join(objects)} {av_libs}',
            env="conanbuild",
        )

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        copy(self, "unpaper", src=self.build_folder, dst=bin_dir)
        self._sign_elf(os.path.join(bin_dir, "unpaper"))

    def _sign_elf(self, path):
        # ELF signing is mandatory to execute on HarmonyOS. The signing tools
        # only exist on the real CI/release worker; when absent (e.g. the local
        # build container) skip gracefully and let the worker sign. On the
        # worker the tools are always present, so a signing failure there is a
        # hard error (an unsigned binary cannot run in test_package).
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not (os.path.isfile(sign_tool) and os.path.isfile(objcopy)):
            self.output.warning("ELF signing tools not found; skipping (CI/release worker will sign).")
            return
        subprocess.run(
            [objcopy, "--remove-section", ".codesign", path],
            check=True, capture_output=True, timeout=10,
        )
        tmp = path + ".signed.tmp"
        r = subprocess.run(
            [sign_tool, "sign", "-inFile", path, "-outFile", tmp, "-selfSign", "1"],
            capture_output=True, timeout=30,
        )
        if r.returncode == 0 and os.path.exists(tmp):
            os.replace(tmp, path)
            os.chmod(path, 0o755)
        else:
            raise RuntimeError(f"ELF signing failed for {os.path.basename(path)} (rc={r.returncode})")

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
