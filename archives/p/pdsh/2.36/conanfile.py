import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class PdshConan(ConanFile):
    name = "pdsh"
    version = "2.36"
    description = "Parallel remote shell program — execute commands on multiple hosts in parallel"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/chaos/pdsh"
    url = ""  # CI fills this

    package_type = "application"  # R38: command-line tool

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass  # No mandatory third-party deps; pthreads is system-provided

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--with-ssh")
        tc.configure_args.append("--with-exec")
        # config.guess (2018) doesn't recognize HarmonyOS; force build triplet
        tc.configure_args.append("--build=aarch64-unknown-linux-gnu")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        # E011: HMDFS umask 077 → 022 (configure generates temp dirs with
        # restrictive permissions on HMDFS, causing config.status to fail)
        configure = os.path.join(self.source_folder, "configure")
        if os.path.isfile(configure):
            with open(configure) as f:
                content = f.read()
            if "umask 077" in content:
                with open(configure, "w") as f:
                    f.write(content.replace("umask 077", "umask 022"))

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = ["lib", "lib/pdsh"]
