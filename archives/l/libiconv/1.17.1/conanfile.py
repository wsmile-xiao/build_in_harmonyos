#!/usr/bin/env python3
"""Conan recipe — libiconv 1.17.1 (GNU charset conversion library).

R26: System-level library, build static only to avoid polluting /lib.
R32: Supports both Linux and OHOS platforms.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibiconvConan(ConanFile):
    name = "libiconv"
    version = "1.17.1"
    description = "GNU charset conversion library"
    license = "LGPL-2.1"
    homepage = "https://www.gnu.org/software/libiconv/"
    url = "https://www.gnu.org/software/libiconv/"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def config_options(self):
        if self.options.shared:
            raise ConanInvalidConfiguration(
                "libiconv is provided as a static library on OHOS"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _mktemp_wrapper(self):
        wrapper_dir = os.path.join(self.build_folder, "mktemp-wrapper")
        os.makedirs(wrapper_dir, exist_ok=True)
        wrapper = os.path.join(wrapper_dir, "mktemp")
        real_mktemp = shutil.which("mktemp")
        if not real_mktemp:
            raise ConanInvalidConfiguration(
                "mktemp is required for secure configure temporary directories"
            )
        script = f'''#!/bin/sh
real_mktemp="{real_mktemp}"
want_dir=0
for arg in "$@"; do
  case "$arg" in
    -d|--directory) want_dir=1 ;;
  esac
done
[ "$want_dir" -eq 1 ] || exec "$real_mktemp" "$@"
parent=""
template=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    -d|--directory) want_dir=1 ;;
    -p|--tmpdir)
      shift
      [ "$#" -gt 0 ] || exit 2
      parent="$1"
      ;;
    --suffix=*) exit 2 ;;
    --) shift; [ "$#" -eq 1 ] || exit 2; template="$1"; break ;;
    -*) exit 2 ;;
    *) [ -z "$template" ] || exit 2; template="$1" ;;
  esac
  shift
done
if [ "$want_dir" -eq 0 ]; then
  exec "$real_mktemp" "$@"
fi
if [ -z "$template" ]; then
  parent="${{parent:-${{TMPDIR:-/tmp}}}}"
  template="$parent/tmp.XXXXXX"
elif [ -n "$parent" ]; then
  template="$parent/$template"
fi
base=$(dirname "$template")
name=$(basename "$template")
case "$name" in *XXXXXX*) ;; *) exit 2 ;; esac
random=$(od -An -N16 -tx1 /dev/urandom | tr -d ' \\n') || exit 1
[ "${{#random}}" -eq 32 ] || exit 1
candidate="$base/$(printf '%s' "$name" | sed "s/XXXXXX/$random/")"
(umask 077 && mkdir "$candidate") || exit 1
chmod u+rwx "$candidate" || exit 1
printf '%s\\n' "$candidate"
'''
        with open(wrapper, "w", encoding="utf-8") as handle:
            handle.write(script)
        os.chmod(wrapper, 0o755)
        return wrapper_dir

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--enable-static")
        tc.configure_args.append("--disable-shared")
        env = tc.environment()
        env.prepend_path("PATH", self._mktemp_wrapper())
        tc.generate(env=env)

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        self.run("make -j1 check", cwd=self.build_folder, env="conanbuild")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        for la_file in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(la_file)

    def package_info(self):
        self.cpp_info.libs = ["iconv", "charset"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_target_name", "libiconv::libiconv")
