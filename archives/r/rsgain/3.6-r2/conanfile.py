#!/usr/bin/env python3
"""Conan recipe for rsgain 3.6-r2 on HarmonyOS PC (aarch64).

rsgain is a ReplayGain 2.0 loudness normalizer that tags audio files with
ReplayGain information. It supports MP3, FLAC, Ogg Vorbis, Opus, MP4/M4A (AAC),
WMA, WAV, AIFF, WavPack, APE, TAK and Musepack formats.

OHOS-specific adaptations:
  - All 5 dependencies (FFmpeg, taglib, libebur128, inih, fmt) are built
    in-tree from their official source tarballs, statically linked into
    the rsgain binary. None of them exist as Conan packages on OHOS yet.
  - FFmpeg's configure receives a portability patch adding a `harmonyos`
    target_os case (same approach as the unpaper/ffprobe recipes).
  - The upstream CMake build is intentionally bypassed: CMake would require
    pkg-config files for all dependencies, which complicates the embedded
    build. rsgain's five C++ sources are instead compiled directly and
    statically linked against all just-built dependencies, exactly the
    sources/flags upstream's CMakeLists.txt compiles.
  - config.h is generated manually (replacing CMake's configure_file).
  - OHOS clang 15 doesn't support C++23 std::format, so the fmt library
    is always built and used (USE_STD_FORMAT is never defined).
  - The resulting ELF binary is signed for HarmonyOS execution.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, copy, chdir, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class RsgainConan(ConanFile):
    name = "rsgain"
    version = "3.6-r2"
    package_type = "application"
    description = "ReplayGain 2.0 loudness normalizer"
    license = "BSD-2-Clause"
    homepage = "https://github.com/complexlogic/rsgain"
    url = ""

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def source(self):
        # rsgain sources live at the source-folder root.
        get(self, **self.conan_data["sources"]["rsgain"], strip_root=True)
        # Dependency sources are placed in sibling subfolders and built from there.
        for dep in ("ffmpeg", "taglib", "libebur128", "inih", "fmt"):
            get(
                self,
                **self.conan_data["sources"][dep],
                strip_root=True,
                destination=os.path.join(self.source_folder, dep),
            )

    def _cc(self):
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        return ce.get("c") or "clang"

    def _cxx(self):
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        return ce.get("cxx") or "clang++"

    def _pkg_config(self, pkgconfig_dir, *args):
        pc = shutil.which("pkg-config") or "/data/service/hnp/bin/pkg-config"
        env = dict(os.environ, PKG_CONFIG_PATH=pkgconfig_dir)
        return subprocess.check_output([pc, *args], env=env, text=True, timeout=30).strip()

    def _extend_path_for_coreutils(self):
        # FFmpeg's configure directly invokes `tr`, `uname`, `grep`, `mktemp`,
        # etc. The OHOS rootfs may ship GNU coreutils outside the default PATH.
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
        cxx = self._cxx()
        prefix = os.path.join(self.build_folder, "prefix")

        # Apply all patches declared in conandata.yml (FFmpeg harmonyos
        # portability patch + preset runtime path patch). base_path for
        # each patch is specified in conandata.yml.
        apply_conandata_patches(self)

        # ============================================================
        # 1) Build FFmpeg 8.1.2 (minimal static, audio codecs only)
        # ============================================================
        ff_src = os.path.join(self.source_folder, "ffmpeg")
        ff_prefix = os.path.join(prefix, "ffmpeg")

        with chdir(self, ff_src):
            configure_cmd = (
                "./configure"
                f" --cc={cc}"
                f" --prefix={ff_prefix}"
                " --disable-everything"
                # Decoders for all rsgain-supported audio formats
                " --enable-decoder=mp3float,flac,vorbis,opus,aac"
                " --enable-decoder=wmav1,wmav2"
                " --enable-decoder=pcm_s16le,pcm_s24le,pcm_s32le,pcm_f32le"
                " --enable-decoder=alac,wavpack,ape,tak"
                " --enable-decoder=mpc7,mpc8"
                # Demuxers
                " --enable-demuxer=mp3,flac,ogg,mov,mp4,aiff,wav,wv,ape,mpc,asf"
                # Parsers
                " --enable-parser=mpegaudio,flac,vorbis,opus,aac,aac_latm"
                # Protocols
                " --enable-protocol=file"
                # Filters (aresample needed for audio resampling to libebur128 format)
                " --enable-filter=aresample"
                # Enable swresample (needed for audio resampling)
                " --enable-swresample"
                # Build options
                " --disable-doc --disable-programs --disable-shared --enable-static"
                " --disable-avdevice --disable-avfilter --disable-swscale"
                # OHOS only ships shared libz/libiconv; disable to avoid -static
                # link errors (no libz.a / libiconv.a available on the system).
                " --disable-zlib --disable-iconv"
                # OHOS SDK ships an incomplete vulkan.h; disable explicitly.
                " --disable-vulkan"
            )
            self.run(configure_cmd, env="conanbuild")
            self.run("make -j2", env="conanbuild")
            self.run("make install", env="conanbuild")

        # ============================================================
        # 2) Build fmt 10.2.1 (CMake, static)
        # ============================================================
        fmt_src = os.path.join(self.source_folder, "fmt")
        fmt_prefix = os.path.join(prefix, "fmt")
        fmt_build = os.path.join(self.build_folder, "fmt_build")
        os.makedirs(fmt_build, exist_ok=True)
        with chdir(self, fmt_build):
            self.run(
                f'cmake "{fmt_src}"'
                f" -DCMAKE_C_COMPILER={cc}"
                f" -DCMAKE_CXX_COMPILER={cxx}"
                f" -DCMAKE_INSTALL_PREFIX={fmt_prefix}"
                " -DCMAKE_BUILD_TYPE=Release"
                " -DFMT_DOC=OFF -DFMT_TEST=OFF -DFMT_CUDA=OFF"
                " -DBUILD_SHARED_LIBS=OFF",
                env="conanbuild",
            )
            self.run("make -j2", env="conanbuild")
            self.run("make install", env="conanbuild")

        # ============================================================
        # 3) Build inih r58 (direct compile, static library)
        # ============================================================
        # inih r58 ships ini.c (C) at root and cpp/INIReader.cpp (C++ wrapper).
        # rsgain uses the C++ wrapper (includes <ini.h>), so we compile both
        # into a single static library.
        inih_src = os.path.join(self.source_folder, "inih")
        inih_prefix = os.path.join(prefix, "inih")
        inih_libdir = os.path.join(inih_prefix, "lib")
        inih_incdir = os.path.join(inih_prefix, "include")
        os.makedirs(inih_libdir, exist_ok=True)
        os.makedirs(inih_incdir, exist_ok=True)

        inih_obj = os.path.join(self.build_folder, "ini.o")
        inih_cpp_obj = os.path.join(self.build_folder, "INIReader.o")
        self.run(
            f'"{cc}" -c -O2 -I"{inih_src}"'
            f' -o "{inih_obj}"'
            f' "{os.path.join(inih_src, "ini.c")}"',
            env="conanbuild",
        )
        self.run(
            f'"{cxx}" -std=c++20 -c -O2'
            f' -I"{inih_src}" -I"{os.path.join(inih_src, "cpp")}"'
            f' -o "{inih_cpp_obj}"'
            f' "{os.path.join(inih_src, "cpp", "INIReader.cpp")}"',
            env="conanbuild",
        )
        ar = shutil.which("ar") or "/data/service/hnp/bin/llvm-ar"
        self.run(
            f'"{ar}" rcs "{os.path.join(inih_libdir, "libinih.a")}"'
            f' "{inih_obj}" "{inih_cpp_obj}"',
            env="conanbuild",
        )
        # Install headers
        copy(self, "ini.h", src=inih_src, dst=inih_incdir)
        copy(self, "INIReader.h", src=os.path.join(inih_src, "cpp"), dst=inih_incdir)

        # ============================================================
        # 4) Build libebur128 1.2.6 (CMake, static)
        # ============================================================
        ebur_src = os.path.join(self.source_folder, "libebur128")
        ebur_prefix = os.path.join(prefix, "libebur128")
        ebur_build = os.path.join(self.build_folder, "ebur_build")
        os.makedirs(ebur_build, exist_ok=True)
        with chdir(self, ebur_build):
            self.run(
                f'cmake "{ebur_src}"'
                f" -DCMAKE_C_COMPILER={cc}"
                f" -DCMAKE_INSTALL_PREFIX={ebur_prefix}"
                " -DCMAKE_BUILD_TYPE=Release"
                " -DCMAKE_POLICY_VERSION_MINIMUM=3.5"
                " -DBUILD_SHARED_LIBS=OFF"
                " -DENABLE_TESTS=OFF",
                env="conanbuild",
            )
            self.run("make -j2", env="conanbuild")
            self.run("make install", env="conanbuild")

        # ============================================================
        # 5) Build taglib 2.3 (CMake, static)
        # ============================================================
        tag_src = os.path.join(self.source_folder, "taglib")
        tag_prefix = os.path.join(prefix, "taglib")
        tag_build = os.path.join(self.build_folder, "tag_build")
        os.makedirs(tag_build, exist_ok=True)
        with chdir(self, tag_build):
            self.run(
                f'cmake "{tag_src}"'
                f" -DCMAKE_C_COMPILER={cc}"
                f" -DCMAKE_CXX_COMPILER={cxx}"
                f" -DCMAKE_INSTALL_PREFIX={tag_prefix}"
                " -DCMAKE_BUILD_TYPE=Release"
                " -DBUILD_SHARED_LIBS=OFF"
                " -DBUILD_TESTING=OFF"
                " -DBUILD_EXAMPLES=OFF"
                # OHOS lacks libz.a; disable zlib to keep -static linking clean.
                " -DWITH_ZLIB=OFF",
                env="conanbuild",
            )
            self.run("make -j2", env="conanbuild")
            self.run("make install", env="conanbuild")

        # ============================================================
        # 6) Generate config.h (replaces CMake's configure_file)
        # ============================================================
        config_h = os.path.join(self.build_folder, "config.h")
        with open(config_h, "w") as fh:
            fh.write(
                '#define PROJECT_NAME "rsgain"\n'
                '#define EXECUTABLE_TITLE "rsgain"\n'
                '#define PROJECT_VERSION "3.6"\n'
                '#define PROJECT_URL "https://github.com/complexlogic/rsgain"\n'
                f'#define BUILD_DATE "2026-07-22"\n'
            )

        # ============================================================
        # 7) Get FFmpeg compile/link flags via pkg-config
        # ============================================================
        pkgconfig_dir = os.path.join(ff_prefix, "lib", "pkgconfig")
        av_cflags = self._pkg_config(
            pkgconfig_dir, "--static", "--cflags",
            "libavformat", "libavcodec", "libswresample", "libavutil"
        )
        av_libs = self._pkg_config(
            pkgconfig_dir, "--static", "--libs",
            "libavformat", "libavcodec", "libswresample", "libavutil"
        )

        # ============================================================
        # 8) Compile rsgain's C++ sources
        # ============================================================
        rsgain_src = os.path.join(self.source_folder, "src")
        sources = ["rsgain.cpp", "scan.cpp", "output.cpp", "tag.cpp", "easymode.cpp"]

        # Collect all include paths
        include_dirs = [
            f"-I{rsgain_src}",                    # for source files + "external/CRC.h"
            f"-I{self.build_folder}",             # for config.h
            f"-I{fmt_prefix}/include",            # for <fmt/core.h>, <fmt/chrono.h>
            f"-I{inih_prefix}/include",           # for <ini.h>
            f"-I{ebur_prefix}/include",           # for <ebur128.h>
            f"-I{tag_prefix}/include",            # for <taglib/taglib.h> etc.
        ]

        objects = []
        for src in sources:
            obj = os.path.join(self.build_folder, src.replace(".cpp", ".o"))
            objects.append(obj)
            self.run(
                f'"{cxx}" -std=c++20 -O2 -D_GNU_SOURCE'
                f' {av_cflags}'
                f' {" ".join(include_dirs)}'
                f' -c "{os.path.join(rsgain_src, src)}" -o "{obj}"',
                env="conanbuild",
            )

        # ============================================================
        # 9) Statically link rsgain binary
        # ============================================================
        # Library order for static linking: rsgain objects, then dependencies
        # in dependency order (dependents before dependencies).
        lib_paths = [
            f"-L{ff_prefix}/lib",
            f"-L{fmt_prefix}/lib",
            f"-L{inih_prefix}/lib",
            f"-L{ebur_prefix}/lib",
            f"-L{tag_prefix}/lib",
        ]

        rsgain_bin = os.path.join(self.build_folder, "rsgain")
        self.run(
            f'"{cxx}" -static -o "{rsgain_bin}"'
            f' {" ".join(objects)}'
            f' {" ".join(lib_paths)}'
            f' -ltag -lebur128 -linih -lfmt'
            f' -lpthread -lm -ldl'
            f' {av_libs}',
            env="conanbuild",
        )

    def package(self):
        # Binary
        bin_dir = os.path.join(self.package_folder, "bin")
        copy(self, "rsgain", src=self.build_folder, dst=bin_dir)
        self._sign_elf(os.path.join(bin_dir, "rsgain"))

        # Presets
        presets_src = os.path.join(self.source_folder, "config", "presets")
        presets_dst = os.path.join(self.package_folder, "share", "rsgain", "presets")
        if os.path.isdir(presets_src):
            copy(self, "*.ini", src=presets_src, dst=presets_dst)

        # Man page
        man_src = os.path.join(self.source_folder, "docs")
        man_dst = os.path.join(self.package_folder, "share", "man", "man1")
        copy(self, "rsgain.1", src=man_src, dst=man_dst)

    def _sign_elf(self, path):
        # ELF signing is mandatory to execute on HarmonyOS. The signing tools
        # only exist on the real CI/release worker; when absent (e.g. the local
        # build container) skip gracefully and let the worker sign.
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        if not (os.path.isfile(sign_tool) and os.path.isfile(objcopy)):
            self.output.warning("ELF signing tools not found; skipping (CI/release worker will sign).")
            return
        try:
            r = subprocess.run(
                [objcopy, "--remove-section", ".codesign", path],
                capture_output=True, timeout=10,
            )
            if r.returncode != 0:
                self.output.warning(
                    f"ELF signature cleanup failed for {os.path.basename(path)} "
                    f"(rc={r.returncode}); keeping original binary"
                )
                return
        except (subprocess.TimeoutExpired, OSError) as exc:
            self.output.warning(
                f"ELF signature cleanup failed for {os.path.basename(path)}; "
                f"keeping original binary: {exc}"
            )
            return
        tmp = path + ".signed.tmp"
        try:
            r = subprocess.run(
                [sign_tool, "sign", "-inFile", path, "-outFile", tmp, "-selfSign", "1"],
                capture_output=True, text=True, timeout=30,
            )
            if r.returncode == 0 and os.path.exists(tmp):
                os.replace(tmp, path)
                os.chmod(path, 0o755)
                return
            details = "\n".join(
                output.strip() for output in (r.stdout, r.stderr) if output and output.strip()
            ) or "no output"
            self.output.warning(
                f"ELF signing failed for {os.path.basename(path)} "
                f"(rc={r.returncode}); keeping unsigned binary:\n{details}"
            )
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes) else exc.stdout or ""
            stderr = exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else exc.stderr or ""
            details = "\n".join(
                output.strip() for output in (stdout, stderr) if output and output.strip()
            ) or "no output"
            self.output.warning(
                f"ELF signing timed out for {os.path.basename(path)}; "
                f"keeping unsigned binary:\n{details}"
            )
        except OSError as exc:
            self.output.warning(
                f"ELF signing could not start for {os.path.basename(path)}; "
                f"keeping unsigned binary: {exc}"
            )
        finally:
            if os.path.exists(tmp):
                os.unlink(tmp)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
