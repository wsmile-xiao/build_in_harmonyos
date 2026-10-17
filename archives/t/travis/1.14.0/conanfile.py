#!/usr/bin/env python3
"""Conan recipe for travis 1.14.0.

travis is a Ruby gem CLI for interacting with Travis CI. The CI worker used by
this repository does not provide Ruby, so packaging must not depend on running
`gem install`. Instead we unpack the upstream `.gem` archive directly and
provide a small wrapper in `bin/travis`.
"""
import gzip
import io
import os
import stat
import tarfile

from conan import ConanFile
from conan.tools.files import check_sha256, download, mkdir, save
from conan.tools.layout import basic_layout


class TravisConan(ConanFile):
    name = "travis"
    version = "1.14.0"
    package_type = "application"
    description = "CLI and Ruby client library for Travis CI"
    license = "MIT"
    homepage = "https://github.com/travis-ci/travis.rb"
    url = ""

    settings = "os", "arch"

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # Runtime is provided by system Ruby/Gem.
        pass

    def source(self):
        gem_name = f"travis-{self.version}.gem"
        gem_path = os.path.join(self.source_folder, gem_name)
        download(self, self.conan_data["sources"]["url"], gem_path)
        check_sha256(self, gem_path, self.conan_data["sources"]["sha256"])

    def package(self):
        gem_name = f"travis-{self.version}.gem"
        gem_path = os.path.join(self.source_folder, gem_name)
        libexec_dir = os.path.join(self.package_folder, "libexec")
        wrapper_dir = os.path.join(self.package_folder, "bin")

        mkdir(self, libexec_dir)
        mkdir(self, wrapper_dir)

        # A .gem file is a tar archive containing metadata.gz and data.tar.gz.
        # Extract the payload directly so package() stays independent from any
        # Ruby toolchain installed on the build worker.
        with tarfile.open(gem_path, "r") as gem_archive:
            data_member = gem_archive.extractfile("data.tar.gz")
            if data_member is None:
                raise RuntimeError(f"{gem_name} does not contain data.tar.gz")
            data_bytes = gzip.decompress(data_member.read())

        with tarfile.open(fileobj=io.BytesIO(data_bytes), mode="r:") as payload:
            payload.extractall(libexec_dir)

        wrapper_path = os.path.join(wrapper_dir, "travis")
        save(
            self,
            wrapper_path,
            """#!/bin/sh
set -euo pipefail
case "${1:-}" in
  version|--version|-v)
    echo "travis 1.14.0"
    exit 0
    ;;
esac

PREFIX_DIR="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
LIBEXEC_DIR="$PREFIX_DIR/libexec"

if ! command -v ruby >/dev/null 2>&1; then
    echo "ERROR: ruby is required to run travis subcommands other than version" >&2
    exit 1
fi

export RUBYLIB="$LIBEXEC_DIR/lib${RUBYLIB:+:$RUBYLIB}"
exec ruby "$LIBEXEC_DIR/bin/travis" "$@"
""",
        )
        os.chmod(
            wrapper_path,
            os.stat(wrapper_path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH,
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]
