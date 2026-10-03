"""Shairplay library recipe for HarmonyOS PC."""

import base64
import hashlib
import os
import time
from pathlib import Path

from conan import ConanFile
from conan.tools.files import copy, get, patch, unzip
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ShairplayConan(ConanFile):
    name = "shairplay"
    version = "0.9.0-git20180824.096b61a"
    description = "Portable AirPlay server library"
    license = "LGPL-2.1-or-later AND MIT AND BSD-3-Clause"
    homepage = "https://github.com/juhovh/shairplay"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "patches/*", "bootstrap.tar.gz.b64"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        source_archive = os.environ.get("SHAIRPLAY_SOURCE_ARCHIVE")
        if source_archive:
            with open(source_archive, "rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            if digest != self.conan_data["sources"][self.version]["sha256"]:
                raise ValueError("SHAIRPLAY_SOURCE_ARCHIVE checksum mismatch")
            unzip(self, source_archive, destination=self.source_folder, strip_root=True)
        else:
            get(self, **self.conan_data["sources"][self.version], strip_root=True)
        patch(self, patch_file=os.path.join(self.export_sources_folder,
                                             "patches", "0001-check-dns-sd-header-only-without-dlopen.patch"))
        # GitCode's PR diff endpoint omits binary patch data. Keep the pinned
        # bootstrap archive as patchable text and reconstruct it only here.
        encoded = Path(self.export_sources_folder, "bootstrap.tar.gz.b64").read_text(
            encoding="ascii")
        bootstrap = base64.b64decode("".join(encoded.split()), validate=True)
        if hashlib.sha256(bootstrap).hexdigest() != (
                "5445d896f357c7bc37bd1fb1f283470bc37273c29cbdac04234c8e4db0ac6a36"):
            raise ValueError("bootstrap archive checksum mismatch")
        archive_path = Path(self.source_folder, ".bootstrap.tar.gz")
        try:
            archive_path.write_bytes(bootstrap)
            unzip(self, str(archive_path), destination=self.source_folder)
        finally:
            archive_path.unlink(missing_ok=True)
        for executable in ("configure", "config.guess", "config.sub", "compile",
                           "depcomp", "install-sh", "missing", "ltmain.sh"):
            path = os.path.join(self.source_folder, executable)
            os.chmod(path, os.stat(path).st_mode | 0o111)
        # The target has no Autotools. Keep pre-generated files newer than their
        # inputs so Automake does not try to invoke aclocal during `make`.
        source = Path(self.source_folder)
        now = time.time()
        for path in [source / "configure.ac", *source.rglob("Makefile.am"),
                     *(source / "m4").glob("*.m4")]:
            os.utime(path, (now - 120, now - 120))
        for path in [source / "aclocal.m4", source / "configure",
                     source / "config.h.in", *source.rglob("Makefile.in")]:
            os.utime(path, (now - 60, now - 60))

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--without-playfair")
        if not self.options.shared:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
        tc.generate()

    def build(self):
        if self.settings.os == "OHOS":
            # HMDFS assigns temporary directories a different owner. The
            # generated config.status cannot write subs1.awk with umask 077.
            configure = Path(self.source_folder, "configure")
            script = configure.read_text(encoding="utf-8")
            for old, new in (
                ('(umask 077 && mktemp -d "./confXXXXXX")',
                 '(umask 022 && mktemp -d "./confXXXXXX")'),
                ('(umask 077 && mkdir "$tmp")',
                 '(umask 022 && mkdir "$tmp")'),
            ):
                if script.count(old) != 1:
                    raise ValueError(f"unexpected Autoconf temporary directory code: {old}")
                script = script.replace(old, new, 1)
            configure.write_text(script, encoding="utf-8")
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j2"])
        autotools.make(target="check", args=["-j1"])

    def package(self):
        Autotools(self).install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["shairplay"]
        self.cpp_info.set_property("cmake_file_name", "shairplay")
        self.cpp_info.set_property("cmake_target_name", "shairplay::shairplay")
        self.cpp_info.set_property("pkg_config_name", "shairplay")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["dl", "m"]
