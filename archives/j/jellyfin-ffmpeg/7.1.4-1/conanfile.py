#!/usr/bin/env python3
"""Conan recipe — jellyfin-ffmpeg 7.1.4-1"""
import os
import glob

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class JellyfinFfmpegConan(ConanFile):
    name = "jellyfin-ffmpeg"
    version = "7.1.4-1"
    package_type = "library"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/jellyfin/jellyfin-ffmpeg"
    url = "https://github.com/jellyfin/jellyfin-ffmpeg"
    description = (
        "Jellyfin custom FFmpeg build with GPL+version3+nonfree. "
        "Provides libav* seven libraries and ffmpeg/ffprobe binaries."
    )
    topics = ("ffmpeg", "jellyfin", "video", "audio", "codec", "multimedia")
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    _HNP_BIN = "/data/service/hnp/bin"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def requirements(self):
        self.requires("zlib/1.3.1.1")
        self.requires("bzip2/1.0.8")
        self.requires("xz/5.6.2")
        self.requires("openssl/3.5.6.1.1")
        self.requires("freetype/2.14.3")
        self.requires("harfbuzz/14.2.0.1")
        self.requires("fontconfig/2.18.1.1")
        self.requires("fribidi/1.0.16")
        self.requires("libxml2/2.15.3.1")
        self.requires("gmp/6.3.0")
        self.requires("openh264/2.6.0")
        self.requires("libvpx/1.16.0")
        self.requires("opus/1.5.2.1")
        self.requires("lame/4.0")
        self.requires("libvorbis/1.3.7")
        self.requires("dav1d/1.5.0")
        self.requires("libwebp/1.6.0")
        self.requires("zimg/3.0.6")
        self.requires("fdk-aac/2.0.3")

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        PkgConfigDeps(self).generate()

    def _tool(self, conf_key, fallback_name):
        exes = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        return exes.get(conf_key) or os.path.join(self._HNP_BIN, fallback_name)

    def _jobs(self):
        return self.conf.get("tools.build:jobs", check_type=int) or (os.cpu_count() or 4)

    _CHECKLIB_DEPS = ("zlib", "bzip2", "xz", "lame", "gmp")

    def _dep_incflags(self):
        out = []
        for _d in self._CHECKLIB_DEPS:
            for _i in self.dependencies[_d].cpp_info.includedirs:
                out.append("-I" + _i)
        return out

    def _dep_libflags(self):
        out = []
        for _d in self._CHECKLIB_DEPS:
            for _l in self.dependencies[_d].cpp_info.libdirs:
                out.append("-L" + _l)
        return out

    def _configure_args(self):
        pkg = self.package_folder
        args = [
            "--prefix=" + pkg,
            "--bindir=" + os.path.join(pkg, "bin"),
            "--libdir=" + os.path.join(pkg, "lib"),
            "--shlibdir=" + os.path.join(pkg, "lib"),
            "--incdir=" + os.path.join(pkg, "include"),
            "--datadir=" + os.path.join(pkg, "share", "ffmpeg"),
            "--docdir=" + os.path.join(pkg, "share", "doc", "ffmpeg"),
            "--mandir=" + os.path.join(pkg, "share", "man"),
            "--pkgconfigdir=" + os.path.join(pkg, "lib", "pkgconfig"),
            "--target-os=linux",
            "--arch=aarch64",
            "--cc=" + self._tool("c", "clang"),
            "--cxx=" + self._tool("cpp", "clang++"),
            "--ld=" + self._tool("c", "clang"),
            "--ar=" + os.path.join(self._HNP_BIN, "llvm-ar"),
            "--nm=" + os.path.join(self._HNP_BIN, "llvm-nm"),
            "--ranlib=" + os.path.join(self._HNP_BIN, "llvm-ranlib"),
            "--strip=" + os.path.join(self._HNP_BIN, "llvm-strip"),
            "--disable-autodetect",
            "--enable-pthreads",
            "--enable-zlib",
            "--enable-gpl",
            "--enable-version3",
            "--enable-nonfree",
            "--enable-gmp",
            "--enable-openssl",
            "--enable-libxml2",
            "--enable-libfreetype",
            "--enable-libfribidi",
            "--enable-libfontconfig",
            "--enable-libharfbuzz",
            "--enable-libmp3lame",
            "--enable-libopus",
            "--enable-libvorbis",
            "--enable-libdav1d",
            "--enable-libwebp",
            "--enable-libvpx",
            "--enable-libzimg",
            "--enable-libfdk-aac",
            "--enable-libopenh264",
            "--enable-bzlib",
            "--enable-lzma",
            "--extra-cflags=" + " ".join(["-I" + os.path.join(self.build_folder, "_vkstub")] + self._dep_incflags()),
            "--extra-ldflags=" + " ".join(self._dep_libflags()),
            "--disable-doc",
            "--disable-ffplay",
            "--disable-debug",
            "--disable-stripping",
        ]
        if self.options.shared:
            args.extend(["--enable-shared", "--disable-static"])
        else:
            args.extend(["--disable-shared", "--enable-static"])
        return args

    def build(self):
        apply_conandata_patches(self)

        # Create vulkan_beta.h stub — OHOS Vulkan SDK's vulkan.h
        # includes vulkan_beta.h when VK_ENABLE_BETA_EXTENSIONS is defined
        # (FFmpeg source defines it). OHOS SDK doesn't ship this file.
        _vk = os.path.join(self.build_folder, "_vkstub")
        os.makedirs(_vk, exist_ok=True)
        with open(os.path.join(_vk, "vulkan_beta.h"), "w") as _f:
            _f.write(
                "#ifndef VULKAN_BETA_H_\n"
                "#define VULKAN_BETA_H_ 1\n"
                "#define VK_KHR_portability_subset 1\n"
                "#define VK_KHR_PORTABILITY_SUBSET_EXTENSION_NAME "
                "\"VK_KHR_portability_subset\"\n"
                "#define VK_KHR_PORTABILITY_SUBSET_SPEC_VERSION 1\n"
                "#endif\n"
            )

        for _var in ("CFLAGS", "CXXFLAGS", "CPPFLAGS", "LDFLAGS", "LIBS",
                     "PKG_CONFIG_PATH", "PKG_CONFIG_LIBDIR",
                     "LD_LIBRARY_PATH", "CMAKE_PREFIX_PATH"):
            os.environ.pop(_var, None)
        os.environ["PKG_CONFIG_PATH"] = self.generators_folder

        # Fix fribidi .pc: headers are in include/fribidi/ subdir
        _fribidi_pc = os.path.join(self.generators_folder, "fribidi.pc")
        if os.path.exists(_fribidi_pc):
            with open(_fribidi_pc, encoding="utf-8") as f:
                text = f.read()
            if "-I${includedir}/fribidi" not in text:
                text = text.replace(
                    'Cflags: -I"${includedir}"',
                    'Cflags: -I"${includedir}" -I"${includedir}/fribidi"'
                )
                with open(_fribidi_pc, "w", encoding="utf-8") as f:
                    f.write(text)

        _tmp = os.path.join(self.build_folder, "_tmp")
        os.makedirs(_tmp, exist_ok=True)
        os.environ["TMPDIR"] = _tmp

        os.makedirs(self.build_folder, exist_ok=True)
        _configure = os.path.join(self.source_folder, "configure")
        _args = " ".join('"{}"'.format(a) for a in self._configure_args())
        self.run('PKG_CONFIG_PATH="{}" "{}" {}'.format(
            self.generators_folder, _configure, _args), cwd=self.build_folder)
        self.run("make -j{}".format(self._jobs()), cwd=self.build_folder)

    def package(self):
        self.run("make install", cwd=self.build_folder)
        for _lic in ("LICENSE.md", "COPYING.GPLv2", "COPYING.GPLv3",
                     "COPYING.LGPLv2.1", "COPYING.LGPLv3"):
            copy(self, _lic, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "licenses"))
        self._relocate_pc()
        self._sign_binaries()

    def _relocate_pc(self):
        _lib = os.path.join(self.package_folder, "lib")
        _inc = os.path.join(self.package_folder, "include")
        for pc in glob.glob(os.path.join(_lib, "pkgconfig", "*.pc")):
            with open(pc, encoding="utf-8") as f:
                text = f.read()
            text = text.replace("libdir=" + _lib + "\n", "libdir=${exec_prefix}/lib\n")
            text = text.replace("includedir=" + _inc + "\n", "includedir=${prefix}/include\n")
            with open(pc, "w", encoding="utf-8") as f:
                f.write(text)

    def _is_elf(self, path):
        try:
            with open(path, "rb") as f:
                return f.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _sign_binaries(self):
        # HarmonyOS requires ELF code signatures; install+strip breaks them
        targets = glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(self.package_folder, "lib", "**", "*.so.*"), recursive=True)
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            for name in os.listdir(bindir):
                p = os.path.join(bindir, name)
                if os.path.isfile(p) and not os.path.islink(p) and self._is_elf(p):
                    targets.append(p)
        objcopy = os.path.join(self._HNP_BIN, "llvm-objcopy")
        signer = os.path.join(self._HNP_BIN, "binary-sign-tool")
        for f in targets:
            if os.path.islink(f):
                continue
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=f))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=f))

    def package_info(self):
        _system = ["m", "dl", "pthread"] if self.settings.os in ("Linux", "OHOS") else []

        def _component(name, requires):
            c = self.cpp_info.components[name]
            c.libs = [name]
            c.set_property("pkg_config_name", "lib" + name)
            c.set_property("cmake_target_name", "jellyfin-ffmpeg::" + name)
            c.requires = list(requires)
            c.system_libs = list(_system)
            return c

        _component("avutil", ["gmp::gmp"])
        _component("swresample", ["avutil"])
        _component("swscale", ["avutil"])
        _component("avcodec", ["avutil", "swresample",
                               "zlib::zlib",
                               "openh264::openh264",
                               "libvpx::libvpx",
                               "opus::opus",
                               "lame::lame",
                               "fdk-aac::fdk-aac",
                               "dav1d::dav1d",
                               "libvorbis::libvorbis"])
        _component("avformat", ["avcodec", "avutil", "swresample",
                                "zlib::zlib",
                                "bzip2::bzip2",
                                "xz::xz",
                                "openssl::openssl",
                                "libxml2::libxml2"])
        _component("avfilter", ["avformat", "avcodec", "swscale", "swresample", "avutil",
                                "freetype::freetype",
                                "fontconfig::fontconfig",
                                "harfbuzz::harfbuzz",
                                "fribidi::fribidi",
                                "libwebp::libwebp",
                                "zimg::zimg"])
        _component("avdevice", ["avfilter", "avformat", "avcodec", "avutil"])

        self.cpp_info.set_property("cmake_file_name", "jellyfin-ffmpeg")
        self.cpp_info.bindirs = ["bin"]
