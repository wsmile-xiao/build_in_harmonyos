#!/usr/bin/env python3
"""Conan recipe for kakasi 2.3.6 (Kanji Kana Simple Inverter).

KAKASI converts Kanji to Hiragana/Katakana/Romaji and ships both the
``kakasi`` command-line filter and the ``libkakasi`` shared library.

UTF-8 input/output is disabled at configure time (``--disable-utf8``)
because HarmonyOS musl ``iconv`` does not implement the EUC-JP <-> UTF-8
conversions that upstream requires, and the repository has no
``libiconv`` Conan package yet. The core EUC-JP/SJIS conversion path does
not depend on ``iconv`` and remains fully functional.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import copy, get, patch
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout

_source_url = "http://kakasi.namazu.org/stable/kakasi-2.3.6.tar.gz"
_source_sha256 = "004276fd5619c003f514822d82d14ae83cd45fb9338e0cb56a44974b44961893"


class KakasiConan(ConanFile):
    name = "kakasi"
    version = "2.3.6"
    description = "KAKASI: Kanji Kana Simple Inverter (Kanji -> Hiragana/Katakana/Romaji)"
    license = "GPL-2.0-or-later"
    homepage = "http://kakasi.namazu.org/"
    url = "http://kakasi.namazu.org/"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        copy(
            self,
            "patches/*.patch",
            self.recipe_folder,
            self.export_sources_folder,
        )

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"kakasi supports Linux and OHOS only, got {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)
        # kakasi's lib/Makefile.am uses relative INCLUDES (-I.. -I../src) that
        # break under an out-of-source VPATH build; build in-source instead.
        self.folders.build = "."

    def source(self):
        get(self, url=_source_url, sha256=_source_sha256, strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # Upstream requires iconv(EUC-JP <-> UTF-8) when UTF-8 is enabled;
        # HarmonyOS musl iconv does not provide those conversions.
        tc.configure_args.append("--disable-utf8")
        tc.configure_args.append(
            "--enable-shared" if self.options.shared else "--disable-shared"
        )
        if self.settings.os == "OHOS":
            # The bundled 2014 config.guess/config.sub do not recognise the
            # HarmonyOS triplet. Portable GNU triplets only steer Autoconf
            # feature detection; the Conan compiler remains OHOS clang.
            # Libtool cannot find a bare `ld`/`ar` in PATH; OHOS uses lld and
            # llvm-ar/llvm-ranlib. Derive their absolute paths from the
            # configured clang location.
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            )
            cc = compilers.get("c") if compilers else None
            tool_dir = os.path.dirname(cc) if cc else "/data/service/hnp/bin"
            tc.configure_args.extend(
                [
                    "--build=aarch64-unknown-linux-gnu",
                    "--host=aarch64-unknown-linux-gnu",
                    f"LD={os.path.join(tool_dir, 'ld.lld')}",
                    f"AR={os.path.join(tool_dir, 'llvm-ar')}",
                    f"RANLIB={os.path.join(tool_dir, 'llvm-ranlib')}",
                ]
            )
            tc.extra_ldflags.append("-fuse-ld=lld")
        tc.generate()

    def build(self):
        patch(
            self,
            patch_file=os.path.join(
                self.export_sources_folder, "patches", "0001-ohos-configure.patch"
            ),
        )
        if self.settings.os == "OHOS":
            # HMDFS may start recipe processes with a restrictive umask.
            os.umask(0)

        autotools = Autotools(self)
        if self.settings.os == "OHOS":
            # HMDFS rejects direct execution of scripts from the Conan build
            # tree even when their mode is 0750. Invoke configure through the
            # platform shell while preserving Conan's generated arguments.
            configure = os.path.join(self.build_folder, "configure")
            self.run(
                f"CONFIG_SHELL=/system/bin/sh SHELL=/system/bin/sh "
                f'/system/bin/sh "{configure}" {autotools._configure_args}',
                env="conanbuild",
                cwd=self.build_folder,
            )
        else:
            autotools.configure()

        # make builds the tools, libkakasi, and generates kanwadict from
        # kakasidict via the just-built mkkanwa (native run on the device).
        autotools.make(args=["-j1"])

        if not cross_building(self):
            # kakasi-6/kakasi-9 exercise -iutf8/-outf8 (excluded: UTF-8 off).
            # kakasi-1 needs GNU echo -e + GNU od (toybox incompatible).
            # kakasi-5/kakasi-7 are upstream-disabled (exit 77 / exit 0).
            # HMDFS does not grant execute permission to the test scripts, so
            # invoke them through sh instead of running ./kakasi-N directly.
            tests_dir = os.path.join(self.build_folder, "tests")
            self.run(
                "for t in kakasi-2 kakasi-3 kakasi-4 kakasi-5 kakasi-7 kakasi-8; "
                "do sh ./$t; rc=$?; [ $rc -eq 0 ] || [ $rc -eq 77 ] || exit 1; done",
                env="conanbuild",
                cwd=tests_dir,
            )

    def package(self):
        autotools = Autotools(self)
        autotools.install(args=["-j1"])
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["kakasi"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
        # The kakasi binary hardcodes $prefix/share/kakasi/{kanwadict,itaijidict};
        # expose the packaged dictionaries via environment overrides.
        self.runenv_info.define(
            "KANWADICTPATH",
            os.path.join(self.package_folder, "share", "kakasi", "kanwadict"),
        )
        self.runenv_info.define(
            "ITAIJIDICTPATH",
            os.path.join(self.package_folder, "share", "kakasi", "itaijidict"),
        )
