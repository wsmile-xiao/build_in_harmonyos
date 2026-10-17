"""Liblouis Braille translation library for OpenHarmony PC."""

import os
import shlex
from pathlib import Path

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, get, save
from conan.tools.gnu import AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.microsoft import unix_path


class LiblouisConan(ConanFile):
    name = "liblouis"
    version = "3.38.0"
    description = "Braille translator and back-translator"
    license = "LGPL-2.1-or-later"
    homepage = "https://liblouis.io/"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "patches/*"
    win_bash = True

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # The upstream YAML test suite and lou_checkyaml need libyaml.
        self.requires("libyaml/0.2.5", run=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        source = dict(self.conan_data["sources"][self.version])
        local_archive = os.environ.get("LIBLOUIS_SOURCE_ARCHIVE")
        if local_archive:
            archive = Path(local_archive).resolve(strict=True)
            if not archive.is_file():
                raise ValueError("LIBLOUIS_SOURCE_ARCHIVE must be a regular file")
            source["url"] = archive.as_uri()
            source["filename"] = archive.name
        get(self, **source, strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        AutotoolsToolchain(self).generate()
        AutotoolsDeps(self).generate()
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    def _run_build_command(self, command):
        # The CI profile can reset TMPDIR to HMDFS after entering conanbuild.
        # A command-local assignment wins over that profile and keeps
        # config.status's private 0700 files on the local /data filesystem.
        if self.settings.os == "OHOS":
            command = "TMPDIR=/data/storage/el2/base/cache " + command
        self.run(command, cwd=self.source_folder, env="conanbuild")

    def build(self):
        configure = unix_path(self, os.path.join(self.source_folder, "configure"))
        args = [
            "--build=aarch64-unknown-linux-ohos",
            "--host=aarch64-unknown-linux-ohos",
            "--prefix=/",
            "--libdir=/lib",
            "--with-yaml=yes",
            "--enable-shared" if self.options.shared else "--disable-shared",
            "--disable-static" if self.options.shared else "--enable-static",
        ]
        self._run_build_command("sh {} {}".format(
            shlex.quote(configure), " ".join(args)))
        self._run_build_command("make -j2")
        if can_run(self):
            launcher = os.path.join(self.build_folder, "ohos-test-launcher.sh")
            save(self, launcher, """#!/bin/sh
set -eu
test "$#" -gt 0
case "$1" in
    */*) test_dir=${1%/*} ;;
    *) test_dir=. ;;
esac
test_name=${1##*/}
case "$test_name" in
    *.pl)
        interpreter=$(command -v perl)
        exec timeout -k 5 180 "$interpreter" "$@"
        ;;
esac
if test -f "$test_dir/.libs/$test_name"; then
    exec timeout -k 5 180 /system/bin/sh "$@"
fi
exec timeout -k 5 180 "$@"
""")
            launcher = shlex.quote(unix_path(self, launcher))
            yaml_launcher = os.path.join(self.build_folder, "ohos-yaml-launcher.sh")
            save(self, yaml_launcher, """#!/bin/sh
set -eu
test "$#" -eq 1
yaml_test=$1
case "$yaml_test" in
    */braille-specs/*)
        LOUIS_TABLEPATH=${LOUIS_TABLEPATH}/tables
        export LOUIS_TABLEPATH
        ;;
esac
tool=$(command -v lou_checkyaml)
exec timeout -k 5 180 /system/bin/sh "$tool" "$yaml_test"
""")
            yaml_launcher = shlex.quote(unix_path(self, yaml_launcher))
            self._run_build_command(
                'make check -j1 LOG_COMPILE="/system/bin/sh {}" '
                'YAML_LOG_COMPILER="/system/bin/sh {}"'.format(
                    launcher, yaml_launcher))

    def package(self):
        package = shlex.quote(unix_path(self, self.package_folder))
        self._run_build_command("make install DESTDIR={}".format(package))
        copy(self, "COPYING.LESSER", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["louis"]
        self.cpp_info.set_property("cmake_file_name", "liblouis")
        self.cpp_info.set_property("cmake_target_name", "liblouis::liblouis")
        self.runenv_info.define(
            "LOUIS_TABLEPATH",
            os.path.join(self.package_folder, "share", "liblouis", "tables"),
        )
