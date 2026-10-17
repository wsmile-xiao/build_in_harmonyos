"""VolPack volume-rendering library, built and tested on native HarmonyOS PC."""

import os
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, replace_in_file, rm
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class VolpackConan(ConanFile):
    name = "volpack"
    version = "1.0b3"
    description = "Stanford software volume-rendering library"
    license = "BSD-3-Clause"
    homepage = "https://graphics.stanford.edu/software/volpack/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    exports_sources = "test_ohos/*", "LICENSE.BSD-3-Clause"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        source = dict(self.conan_data["sources"])
        local_archive = os.environ.get("VOLPACK_SOURCE_ARCHIVE")
        if local_archive:
            archive = Path(local_archive).resolve(strict=True)
            source["url"] = archive.as_uri()
            source["filename"] = archive.name
        get(self, **source, strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            ["--enable-shared" if self.options.shared else "--disable-shared",
             "--disable-static" if self.options.shared else "--enable-static"]
        )
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        if self.settings.os == "OHOS":
            # HMDFS can remap the owner of Autoconf's mode-0700 scratch
            # directory, leaving config.status unable to write its sed files.
            configure_path = os.path.join(self.source_folder, "configure")
            private_mktemp = 'tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&'
            private_mkdir = '(umask 077 && mkdir "$tmp")'
            configure_text = Path(configure_path).read_text(encoding="utf-8")
            if (configure_text.count(private_mktemp) != 1
                    or configure_text.count(private_mkdir) != 1):
                raise ValueError("unexpected Autoconf temporary-directory template")
            replace_in_file(self, configure_path, private_mktemp,
                            'tmp=./conf$$-$RANDOM; (umask 007 && mkdir "$tmp") &&')
            replace_in_file(self, configure_path, private_mkdir,
                            '(umask 007 && mkdir "$tmp")')
        env = Environment()
        env.define_path("TMPDIR", self.build_folder)
        with env.vars(self).apply():
            autotools = Autotools(self)
            autotools.configure()
            autotools.make(args=["-j1"])
            autotools.make(target="check", args=["-j1"])
            if can_run(self):
                script = os.path.join(self.export_sources_folder, "test_ohos", "run_ohos_test.sh")
                self.run('sh "{}" "{}" "{}"'.format(
                    script, self.build_folder, self.source_folder), env="conanbuild")

    def package(self):
        Autotools(self).install()
        # Debian's original Makefile installs the library and man pages but
        # omits the public header; a consumer package must provide it.
        copy(self, "volpack.h", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE.BSD-3-Clause", src=self.export_sources_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        rm(self, "*.la", folder=os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["volpack"]
        self.cpp_info.system_libs = ["m"]
        self.cpp_info.set_property("cmake_file_name", "volpack")
        self.cpp_info.set_property("cmake_target_name", "volpack::volpack")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("VolPack has been verified on Linux and OHOS")
