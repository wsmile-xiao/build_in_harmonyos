#!/usr/bin/env python3
"""Conan recipe — lzop 1.04 (Autotools).

lzop is a file compressor which is very similar to gzip. It uses the LZO
data compression library for compression services.
"""
import os
import re

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout


# install wrapper (E098/E174 family): the HMBS install shim accepts only
# single-file two-arg invocations (`[ $# -eq 2 ] || exit 64`, EX_USAGE),
# while automake's install-dist_docDATA batches ALL dist_doc_DATA files into
# one `$(INSTALL_DATA) $$files $(docdir)` call -> Error 64. This wrapper
# copies SRC... DEST (DEST may be a directory), same precedent as the
# install shims in chicken 5.4.0 / slang 2.3.3.
_INSTALL_WRAPPER = r"""#!/bin/sh
# install wrapper — multi-file install replacement for HarmonyOS (E098/E174)
set -e
while [ $# -gt 0 ]; do
  case "$1" in
    -c) shift ;;
    -m) shift 2 ;;
    -d) shift ;;
    -g|-o|-t) shift 2 ;;
    -*) shift ;;
    *) break ;;
  esac
done
n=$#
if [ "$n" -lt 2 ]; then
  echo "install-wrapper: expected SRC... DEST" >&2
  exit 1
fi
eval "dest=\"\${$n}\""
i=1
while [ "$i" -lt "$n" ]; do
  eval "s=\"\${$i}\""
  if [ -d "$dest" ]; then
    cp -f "$s" "$dest/" || exit 1
  else
    cp -f "$s" "$dest" || exit 1
  fi
  i=$((i+1))
done
"""


class LzopConan(ConanFile):
    name = "lzop"
    version = "1.04"
    description = "lzop is a file compressor which is very similar to gzip"
    license = "GPL-2.0-or-later"
    homepage = "https://www.lzop.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    # CLI tool, not a library (R38: commands.json declared at software level)
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # lzop links against the LZO compression library (configure.ac checks lzo2)
        self.requires("lzo2/2.10")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # AutotoolsDeps: feed -I/-L/-l from lzo2 into configure/make
        deps = AutotoolsDeps(self)
        deps.generate()
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # HMDFS: getcwd() fails inside some Conan build dirs (broken parent
        # path chain), which makes autoconf's `ac_pwd=\`pwd\`` sanity check
        # die with "configure: error: working directory cannot be determined".
        # Seed $PWD and chdir to the build folder so bash's pwd builtin
        # resolves the cwd logically (same workaround as sipcalc/libclastfm).
        bf = self.build_folder
        if os.path.isdir(bf):
            os.chdir(bf)
            os.environ["PWD"] = bf
        autotools = Autotools(self)
        autotools.configure()
        # R9: single job — parallel make hits HMDFS jobserver fifo EPERM (E074)
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        # HMBS install shim rejects multi-file installs (EX_USAGE 64):
        # automake's install-dist_docDATA batches all dist_doc_DATA files
        # into one `$(INSTALL_DATA) $$files $(docdir)` call. Redirect
        # INSTALL_DATA to a multi-file-capable wrapper (chicken 5.4.0 /
        # slang 2.3.3 precedent).
        wrapper = os.path.join(self.build_folder, "install-wrapper.sh")
        with open(wrapper, "w", encoding="utf-8", newline="\n") as f:
            f.write(_INSTALL_WRAPPER)
        os.chmod(wrapper, 0o755)
        makefile = os.path.join(self.build_folder, "Makefile")
        with open(makefile, "r", encoding="utf-8") as f:
            content = f.read()
        content = re.sub(
            r"^INSTALL_DATA\s*=.*$",
            "INSTALL_DATA = {}".format(wrapper),
            content,
            flags=re.MULTILINE,
        )
        with open(makefile, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        autotools.install()

    def package_info(self):
        # Standalone binary, no library to link against
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
