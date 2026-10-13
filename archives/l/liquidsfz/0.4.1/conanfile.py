#!/usr/bin/env python3
"""Conan recipe for the liquidsfz SFZ sampler library on HarmonyOS."""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, copy, get, save
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class LiquidsfzConan(ConanFile):
    name = "liquidsfz"
    version = "0.4.1"
    description = "SFZ sampler library"
    license = "MPL-2.0"
    homepage = "https://github.com/swesterfeld/liquidsfz"
    url = "https://github.com/swesterfeld/liquidsfz"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        patch_dir = os.path.join(self.recipe_folder, "patches")
        if os.path.isdir(patch_dir):
            copy(self, "*.patch", src=patch_dir,
                 dst=os.path.join(self.export_sources_folder, "patches"))

    def requirements(self):
        self.requires("libsndfile/1.2.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(["--without-jack", "--without-lv2", "--without-fftw"])
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--enable-static", "--disable-shared"])
        tc.generate()

    @staticmethod
    def _sign_test(path):
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        readelf = shutil.which("llvm-readelf") or "/data/service/hnp/bin/llvm-readelf"
        if not os.path.isfile(path):
            raise ConanException(f"Missing upstream test: {path}")
        signed = path + ".signed"
        subprocess.run([signer, "sign", "-inFile", path, "-outFile", signed,
                        "-selfSign", "1"], check=True, timeout=60)
        sections = subprocess.run([readelf, "-SW", signed], check=True,
                                  capture_output=True, text=True, timeout=30).stdout
        if sections.count(".codesign") != 1:
            raise ConanException(f"Invalid test signature: {path}")
        os.chmod(signed, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(signed, path)
        os.chmod(path, 0o755)

    def build(self):
        autotools = Autotools(self)
        configure = os.path.join(self.source_folder, "configure")
        if str(self.settings.os) == "OHOS":
            # HMDFS refuses writes inside mktemp directories created with
            # umask 077. Override mktemp for configure, leaving upstream
            # generated files untouched.
            wrapper_dir = os.path.join(self.build_folder, "ohos-tools")
            os.makedirs(wrapper_dir, exist_ok=True)
            wrapper = os.path.join(wrapper_dir, "mktemp")
            save(self, wrapper, '#!/bin/sh\numask 027\nexec /usr/bin/mktemp "$@"\n')
            os.chmod(wrapper, 0o755)
            # The OHOS build profile selects bash, which fails getcwd() on
            # HMDFS. config.guess from this release also predates HarmonyOS.
            self.run(f'env PATH="{wrapper_dir}:$PATH" CONFIG_SHELL=/bin/sh '
                     f'SHELL=/bin/sh /bin/sh "{configure}" '
                     f'{autotools._configure_args} '
                     '--build=aarch64-unknown-linux-gnu '
                     '--host=aarch64-unknown-linux-gnu')
        else:
            autotools.configure()
        autotools.make(args=["-j1"])
        if can_run(self):
            if str(self.settings.os) == "OHOS":
                for name in ("testsynth", "testsfzreader"):
                    self._sign_test(os.path.join(self.build_folder, "tests", name))
            autotools.make(target="check", args=["-j1"])

    def package(self):
        Autotools(self).install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["liquidsfz"]
        self.cpp_info.set_property("pkg_config_name", "liquidsfz")
