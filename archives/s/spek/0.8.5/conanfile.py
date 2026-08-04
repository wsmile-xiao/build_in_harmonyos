#!/usr/bin/env python3
"""Conan recipe — spek 0.8.5 (Autotools, headless CLI build).

spek is an acoustic spectrum analyser. Upstream is a wxWidgets GUI app;
this recipe builds the headless `spek-cli` via the `--disable-gui` patch.

FFmpeg is not available as a Conan package on OHOS (conancenter tops out
at 7.1.1, and the project has no ffmpeg Conan recipe). Following the
unpaper/7.0.0 pattern, we build a minimal *static* FFmpeg in-tree from
the official 8.1.2 tarball — only the audio demuxers/decoders spek needs
— then hand its pkg-config triplet (libavformat/libavcodec/libavutil)
to spek's configure via the AVFORMAT_CFLAGS/AVFORMAT_LIBS environment
variables (configure.ac uses PKG_CHECK_MODULES, which Honours these
overrides before falling back to pkg-config).
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, patch, chdir
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class SpekConan(ConanFile):
    name = "spek"
    version = "0.8.5"
    description = "Spek - Acoustic spectrum analyser (headless CLI build)"
    license = "GPL-3.0"
    homepage = "https://www.spek.cc/"
    url = "https://github.com/alexkay/spek"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    # FFmpeg harmonyos patch must be exported to the source folder so
    # build()'s patch(self, base_path=ff_src, ...) finds it. Listed here
    # via exports_sources (Conan 2.x idiom) instead of conandata.yml's
    # patches key — apply_conandata_patches would otherwise try to apply
    # it to spek's source root and fail (hunks reference ffmpeg/configure).
    exports_sources = "patches/0001-ffmpeg-configure-harmonyos.patch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # FFmpeg is built in-tree from conandata sources (see build()).
        # No Conan ffmpeg requirement — none exists for OHOS.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        # spek sources at the source-folder root.
        spek_src = {k: v for k, v in self.conan_data["sources"].items() if k != "ffmpeg"}
        get(self, **spek_src, strip_root=True)
        # FFmpeg sources in a sibling ffmpeg/ subfolder.
        get(
            self,
            **self.conan_data["sources"]["ffmpeg"],
            strip_root=True,
            destination=os.path.join(self.source_folder, "ffmpeg"),
        )

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Headless build: skip wxWidgets GUI
        tc.configure_args.append("--disable-gui")
        # R26: System-name libraries default to static
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        tc.generate()

    def _cc(self):
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        return ce.get("c") or "clang"

    def _pkg_config(self, pkgconfig_dir, *args):
        pc = shutil.which("pkg-config") or "/data/service/hnp/bin/pkg-config"
        env = dict(os.environ, PKG_CONFIG_PATH=pkgconfig_dir)
        return subprocess.check_output([pc, *args], env=env, text=True).strip()

    def _extend_path_for_coreutils(self):
        # FFmpeg's configure invokes tr/uname/grep/mktemp directly. The OHOS
        # rootfs may ship GNU coreutils outside the default PATH; FFmpeg's
        # limited bundled grep also chokes on some inputs, so we prefer GNU
        # tools by prepending any such directory. No-op when already on PATH.
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

        # ---- 1) Build a minimal static FFmpeg for audio decode ----
        ff_src = os.path.join(self.source_folder, "ffmpeg")
        ff_prefix = os.path.join(self.build_folder, "ffmpeg_prefix")

        # Portability patch: teach FFmpeg configure about harmonyos.
        ff_patch = os.path.join(
            self.source_folder, "patches", "0001-ffmpeg-configure-harmonyos.patch"
        )
        if os.path.isfile(ff_patch):
            patch(self, base_path=ff_src, patch_file=ff_patch)

        # Minimal audio-only FFmpeg: common demuxers/decoders + parsers,
        # no video/image/subtitle codecs, no programs, no shared libs.
        # spek only needs avformat/avcodec/avutil for decoding + FFT input.
        with chdir(self, ff_src):
            configure_cmd = (
                "./configure"
                f" --cc={cc}"
                f" --prefix={ff_prefix}"
                " --disable-everything"
                # demuxers: common audio containers
                " --enable-demuxer=wav,mp3,flac,ogg,aac,mov,avi,matroska"
                # decoders: spek reads PCM/MP3/FLAC/AAC/Vorbis
                " --enable-decoder=pcm_s16le,pcm_s24le,pcm_f32le,mp3,flac,aac,vorbis"
                # parsers needed by the decoders above
                " --enable-parser=mpegaudio,aac,vorbis,opus"
                # muxer: --disable-everything blanks muxer_list.c which
                # allformats.c unconditionally #includes; null muxer is a
                # no-op sink that satisfies the reference.
                " --enable-muxer=null"
                # protocols: local file + stdin pipe
                " --enable-protocol=file,pipe"
                " --disable-doc"
                " --disable-programs"
                " --disable-shared"
                " --enable-static"
                " --disable-avdevice"
                " --disable-avfilter"
                " --disable-swscale"
                # OHOS SDK ships an incomplete vulkan.h; disable explicitly.
                " --disable-vulkan"
            )
            self.run(configure_cmd, env="conanbuild")
            # -j1: HMDFS does not support make jobserver fifos.
            self.run("make -j1", env="conanbuild")
            self.run("make install", env="conanbuild")

        # ---- 2) Apply spek patches + regenerate configure ----
        apply_conandata_patches(self)
        # Regenerate configure from patched configure.ac.
        # autoconf (not autoreconf -fi) — autopoint is unavailable on CI worker.
        self.run("autoconf", cwd=self.source_folder)
        # E046: HMDFS does not preserve +x on autoconf-generated configure,
        # causing "Permission denied" (exit 126) when Autotools.exec() runs it.
        # chmod every configure we can find in source/build folders.
        for cpath in (
            os.path.join(self.source_folder, "configure"),
            os.path.join(self.build_folder, "configure"),
            os.path.join(os.path.dirname(self.build_folder), "configure"),
        ):
            if os.path.exists(cpath):
                os.chmod(cpath, 0o755)

        # ---- 3) Configure spek with FFmpeg pkg-config overrides ----
        pkgconfig_dir = os.path.join(ff_prefix, "lib", "pkgconfig")
        av_cflags = self._pkg_config(
            pkgconfig_dir, "--static", "--cflags", "libavformat", "libavcodec", "libavutil"
        )
        av_libs = self._pkg_config(
            pkgconfig_dir, "--static", "--libs", "libavformat", "libavcodec", "libavutil"
        )

        # configure.ac uses PKG_CHECK_MODULES for AVFORMAT/AVCODEC/AVUTIL.
        # Setting <NAME>_CFLAGS and <NAME>_LIBS env vars lets configure skip
        # the pkg-config probe entirely (the upstream fallback path).
        tc = AutotoolsToolchain(self)
        configure_args = list(tc.configure_args)
        # generate() adds --disable-gui to its own tc instance, but this
        # build() constructs args_str from a fresh AutotoolsToolchain whose
        # configure_args do NOT include --disable-gui. Without it, configure
        # defaults to build_gui=yes and probes for wxWidgets (absent on OHOS).
        if "--disable-gui" not in configure_args:
            configure_args.append("--disable-gui")
        if not self.options.shared:
            configure_args += ["--enable-static", "--disable-shared"]
        args_str = " ".join(configure_args)
        configure_path = os.path.join(self.source_folder, "configure")

        # Conan 2.x ConanFile.run()'s env arg only accepts a string list
        # (e.g. "conanbuild"), NOT a dict. To inject the FFmpeg pkg-config
        # overrides into configure's environment, mutate os.environ directly
        # before the self.run() call — the subprocess inherits it.
        configure_env = {
            "AVFORMAT_CFLAGS": av_cflags,
            "AVFORMAT_LIBS": av_libs,
            "AVCODEC_CFLAGS": av_cflags,
            "AVCODEC_LIBS": av_libs,
            "AVUTIL_CFLAGS": av_cflags,
            "AVUTIL_LIBS": av_libs,
            # Make sure configure's own pkg-config probes see our FFmpeg.
            "PKG_CONFIG_PATH": pkgconfig_dir + os.pathsep + os.environ.get("PKG_CONFIG_PATH", ""),
        }
        os.environ.update(configure_env)

        # HMDFS noexec: invoke configure via explicit `sh` interpreter to
        # bypass the exec-bit requirement on noexec mounts.
        # OHOS/HMDFS: autoconf's config.status uses `umask 077` which creates
        # temp subdirs (confXXXX/) with 0700 perms — writing subs1.awk inside
        # them gets "Permission denied" on HMDFS → "could not setup config
        # files machinery". Relax to 022 in configure BEFORE running it.
        # Same fix as bmon/4.0, bird2/2.17.4, audit/4.1.2 (project idiom).
        with open(configure_path, "r") as fh:
            cfg = fh.read()
        if "umask 077" in cfg:
            with open(configure_path, "w") as fh:
                fh.write(cfg.replace("umask 077", "umask 022"))

        self.run(
            f'sh "{configure_path}" {args_str}',
            cwd=self.build_folder,
            env="conanbuild",
        )

        # config.status is regenerated by configure with the same umask 077
        # baked in; re-relax it in case make re-invokes config.status.
        # In out-of-source builds config.status lives in build_folder.
        for cs_path in (
            os.path.join(self.build_folder, "config.status"),
            os.path.join(self.source_folder, "config.status"),
        ):
            if os.path.exists(cs_path):
                with open(cs_path, "r") as fh:
                    cs = fh.read()
                if "umask 077" in cs:
                    with open(cs_path, "w") as fh:
                        fh.write(cs.replace("umask 077", "umask 022"))

        autotools = Autotools(self)
        # Neutralize the maintainer-mode autoregen rules: Makefile tries to
        # rebuild aclocal.m4 via aclocal-1.16 (not installed on CI worker),
        # causing Error 127. Stamp skew from patch/autoconf triggers it.
        # Same fix as bmon/4.0:159-160 — override the make vars to ':' (no-op).
        no_regen = ["ACLOCAL=:", "AUTOCONF=:", "AUTOHEADER=:", "AUTOMAKE=:", "MAKEINFO=:"]
        autotools.make(args=["-j1"] + no_regen)

    def package(self):
        autotools = Autotools(self)
        no_regen = ["ACLOCAL=:", "AUTOCONF=:", "AUTOHEADER=:", "AUTOMAKE=:", "MAKEINFO=:"]
        autotools.install(args=no_regen)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
