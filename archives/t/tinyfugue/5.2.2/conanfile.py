#!/usr/bin/env python3
"""Conan recipe for TinyFugue 5.2.2.

TinyFugue is a programmable terminal MUD client. The upstream build is
Autotools and has three runtime dependencies that matter on OHOS:
PCRE2, zlib, and ncurses termcap support.

The recipe keeps the core terminal client features enabled. Optional wide
character, SSL, Lua, and Python support are disabled because they add ICU,
OpenSSL, Lua, or CPython requirements that are not needed for the base
client package.
"""

import os
import hashlib
import shutil
import ssl
import tarfile
import tempfile
import urllib.request

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class TinyfugueConan(ConanFile):
    name = "tinyfugue"
    version = "5.2.2"
    description = "Programmable terminal MUD client"
    license = "GPL-2.0-only"
    homepage = "https://github.com/ingwarsw/tinyfugue"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("pcre2/10.45")
        self.requires("zlib/1.3.1.1")
        self.requires("ncurses/6.4", options={"shared": False})

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"tinyfugue supports Linux/OHOS only, got {self.settings.os}"
            )

    def layout(self):
        # TinyFugue's generated configure script assembles src/Makefile by
        # reading relative unix/ and src/ fragments. Its upstream build is
        # therefore in-source only and does not support a separate build
        # directory.
        basic_layout(self, build_folder=".")

    def source(self):
        # Avoid depending on curl/wget being present in the minimal OHOS
        # worker. Python is guaranteed by Conan, and the source digest is
        # still pinned in conandata.yml.
        source_data = self.conan_data["sources"]
        urls = source_data["url"]
        if isinstance(urls, str):
            urls = [urls]
        expected_sha256 = source_data["sha256"]
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        with tempfile.TemporaryDirectory(dir=self.source_folder) as temp_dir:
            archive = os.path.join(temp_dir, "upstream.tar.gz")
            last_error = None
            for url in urls:
                request = urllib.request.Request(
                    url, headers={"User-Agent": "ohpcd-conan-source/1.0"}
                )
                try:
                    with urllib.request.urlopen(
                        request, timeout=300, context=context
                    ) as response, open(archive, "wb") as output:
                        shutil.copyfileobj(response, output)
                    break
                except Exception as exc:
                    last_error = exc
            else:
                raise ConanException(
                    f"TinyFugue source download failed for all candidates: {last_error}"
                )

            digest = hashlib.sha256()
            with open(archive, "rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    digest.update(chunk)
            actual_sha256 = digest.hexdigest()
            if actual_sha256 != expected_sha256:
                raise ConanException(
                    "TinyFugue source sha256 mismatch: "
                    f"expected {expected_sha256}, got {actual_sha256}"
                )

            unpack_dir = os.path.join(temp_dir, "unpacked")
            os.makedirs(unpack_dir)
            with tarfile.open(archive, "r:gz") as bundle:
                bundle.extractall(unpack_dir)

            roots = [
                os.path.join(unpack_dir, entry)
                for entry in os.listdir(unpack_dir)
            ]
            if len(roots) != 1 or not os.path.isdir(roots[0]):
                raise ConanInvalidConfiguration(
                    "TinyFugue source archive does not contain a single root directory"
                )
            shutil.copytree(roots[0], self.source_folder, dirs_exist_ok=True)

    def generate(self):
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            [
                "--enable-static",
                "--disable-shared",
                "--disable-widechar",
                "--disable-ssl",
                "--disable-python",
                "--disable-lua",
                "--enable-termcap=ncursesw",
            ]
        )
        tc.extra_ldflags.append("-static")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # The configure script derives TFVER from git metadata, but GitHub
        # source archives have no .git directory. Replace the exact fallback
        # expression instead of carrying a fragile context patch.
        replace_in_file(
            self,
            os.path.join(self.source_folder, "configure"),
            'TFVER=`git describe --tags --always --dirty || echo "development"`',
            'TFVER="5.2.2"',
        )
        # The generated configure script otherwise forces Lua on whenever
        # the option is mentioned, including --disable-lua. Honor the value
        # parsed by Autoconf so the optional Lua interpreter is not probed.
        replace_in_file(
            self,
            os.path.join(self.source_folder, "configure"),
            "enableval=$enable_lua; enable_lua=yes",
            "enableval=$enable_lua; enable_lua=$enableval",
        )
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # Upstream 5.2.2 has no check or test target. Its GitHub workflow runs
        # only configure, make, and make install, so no make check is invented.

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # Normalize the mode on filesystems that preserve POSIX permissions.
        # HMDFS keeps installed files at 0770 and may ignore chmod; the
        # consumer test stages the binary on tmpfs for cross-user execution.
        os.chmod(os.path.join(self.package_folder, "bin", "tf"), 0o755)
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libs = []
