#!/usr/bin/env python3
"""Conan recipe for libfishsound 1.0.1 (autotools).

libfishsound provides a simple API for decoding and encoding Vorbis and
Speex audio within Ogg streams (CSIRO/annodex, Xiph.org).

OHOS adaptation notes (see notes.md):
  - config.guess/config.sub patched for HarmonyOS detection (E007) via
    patches/0001 and 0002 applied from conandata.yml.
  - FLAC codec support is disabled (--disable-flac): published flac recipes
    (1.4.3/1.5.0) pin libogg/1.3.5, which conflicts with the libogg/1.3.6
    required by the published libvorbis/speex recipes (W0 R36 topology).
  - Dependencies are detected by configure via PKG_CHECK_MODULES
    (ogg, vorbis, vorbisenc, speex); PkgConfigDeps generates those modules.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    load,
    save,
)
from conan.tools.env import VirtualBuildEnv
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LibfishsoundConan(ConanFile):
    name = "libfishsound"
    version = "1.0.1"
    description = (
        "Simple programming interface for decoding and encoding Vorbis and "
        "Speex audio in Ogg streams"
    )
    license = "BSD-3-Clause"
    homepage = "https://xiph.org/fishsound/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libfishsound supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        self.requires("libogg/1.3.6")
        self.requires("libvorbis/1.3.7")
        self.requires("speex/1.2.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        # configure finds ogg/vorbis/vorbisenc/speex via PKG_CHECK_MODULES;
        # PkgConfigDeps generates the matching .pc modules into the
        # generators folder and AutotoolsToolchain prepends it to
        # PKG_CONFIG_PATH.
        PkgConfigDeps(self).generate()
        # configure conftest probes need the dependency shared libraries at
        # run time; VirtualBuildEnv exposes their libdirs via LD_LIBRARY_PATH.
        VirtualBuildEnv(self).generate()

        tc = AutotoolsToolchain(self)
        if not self.options.shared:
            tc.configure_args.append("--enable-static")
            tc.configure_args.append("--disable-shared")
        # FLAC codec disabled: see module docstring (W0 dependency topology)
        tc.configure_args.append("--disable-flac")

        # Linkers and in-process conftest probes must resolve the conan
        # dependency libraries: explicit -L plus an rpath so that AC_TRY_LINK
        # binaries run in the clean CI environment.
        for dep in self.dependencies.values():
            for libdir in (dep.cpp_info.libdirs or ["lib"]):
                path = os.path.join(dep.package_folder, libdir)
                tc.extra_ldflags.append(f"-L{path}")
                tc.extra_ldflags.append(f"-Wl,-rpath,{path}")

        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # E129: autoconf config.status uses `umask 077` for its temporary
        # directory; under HMDFS the setgid bit then loses group execute and
        # config.status fails with Permission denied. Relax to 022.
        configure_path = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure_path):
            content = load(self, configure_path)
            if "umask 077" in content:
                save(self, configure_path,
                     content.replace("umask 077", "umask 022"))

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # ── 上游官方测试 (R51) ──
        # src/tests: comment-test, noop, encdec-comments, encdec-audio
        autotools.make(target="check")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # libtool 归档与 macOS 产物不入包（ADAPTATION_GUIDE §4.1 清理约定）；
        # .la 内嵌绝对路径，也是 L5 逐轮差异源
        for pattern in ("*.la", "*.dylib"):
            lib_dir = os.path.join(self.package_folder, "lib")
            if os.path.isdir(lib_dir):
                for name in os.listdir(lib_dir):
                    if name.endswith(pattern):
                        os.remove(os.path.join(lib_dir, name))

    def package_info(self):
        self.cpp_info.libs = ["fishsound"]
        self.cpp_info.set_property("pkg_config_name", "fishsound")
