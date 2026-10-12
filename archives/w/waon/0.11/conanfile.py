#!/usr/bin/env python3
"""Conan recipe — waon 0.11 (WaoN, a Wave-to-Notes transcriber).

WaoN converts a PCM WAV file into a Standard MIDI File by running a sliding
FFT over the signal and emitting note on/off events. Upstream ships three
targets: `waon` (offline transcriber), `pv` (phase-scope viewer, needs
libao/jack/ncurses) and `gwaon` (GTK2 GUI). OHOS has no GTK2/libao/jack
artifacts, so only `waon` is built — the same "library/tool subset the
platform can actually run" precedent as wildmidi (WANT_PLAYER=OFF).

Upstream 0.11 has no automated test suite at all (`grep -n "^check\|test"
Makefile*` → no test target, no tests/ directory), so the upstream ledger is
0 and the delivered verification is the consumer test in test_package/, which
synthesises a 440 Hz WAV, transcribes it with the packaged binary and parses
the resulting MIDI stream.

Build: upstream hand-written Makefile.waon (patched to honour the flags
conan exports, and to drop the x86-only -march=pentium).
License: GPL-2.0-or-later.
"""
import os
import shutil
import tarfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, download, export_conandata_patches
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class WaonConan(ConanFile):
    name = "waon"
    version = "0.11"
    description = "WaoN — a Wave-to-Notes transcriber (WAV to Standard MIDI File)"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/kichiki/WaoN"
    url = "https://github.com/kichiki/WaoN"

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"os={self.settings.os} not supported")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("fftw/3.3.11")
        self.requires("libsndfile/1.2.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        # 本机实测：conan 2.29.1 的 get() 走自带解压分支时报 `Unzip failed`
        # （错误正文为空）；而 toybox unzip 与 `tar x -f ... --no-same-owner`
        # 单独跑都正常，所以不是解压器坏了，具体触发点未定位。这里下载用
        # download()（带 sha256 校验）+ python tarfile 解包，不依赖外部解压器，
        # 设备与 CI 同一条路径。
        sources = self.conan_data["sources"]
        tgz = os.path.join(self.source_folder, "waon-0.11.tar.gz")
        download(self, url=sources["url"], filename=tgz, sha256=sources["sha256"])
        with tarfile.open(tgz, "r:gz") as archive:
            try:
                archive.extractall(self.source_folder, filter="data")
            except TypeError:  # python without tarfile extraction filters
                archive.extractall(self.source_folder)
        os.remove(tgz)
        wrapper = os.path.join(self.source_folder, "WaoN-0.11")
        if os.path.isdir(wrapper):  # github archive wraps the tree in a tag dir
            for entry in os.listdir(wrapper):
                shutil.move(os.path.join(wrapper, entry),
                            os.path.join(self.source_folder, entry))
            os.rmdir(wrapper)

    def generate(self):
        AutotoolsToolchain(self).generate()
        # AutotoolsDeps 的分工（本机 conan 2.29.1 实测）：依赖头目录进 CFLAGS、
        # -L 进 LDFLAGS、而 -lsndfile -lfftw3 ... 进 LIBS —— 上游链接行不引用
        # $(LIBS) 就会 undefined symbol，补丁 0001 第 4 处就是补这个。
        AutotoolsDeps(self).generate()
        VirtualBuildEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        makefile = os.path.join(self.source_folder, "Makefile.waon")
        if not os.path.exists(makefile):
            raise ConanException("Makefile.waon missing after patch apply")
        self.run("make -f Makefile.waon waon", cwd=self.source_folder,
                 env="conanbuild")

    def package(self):
        binpath = os.path.join(self.source_folder, "waon")
        if not os.path.exists(binpath):
            raise ConanException("waon was not produced by the build")
        copy(self, "waon", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # executable-only package; consumers locate it through bindirs
        self.cpp_info.bindirs = ["bin"]
