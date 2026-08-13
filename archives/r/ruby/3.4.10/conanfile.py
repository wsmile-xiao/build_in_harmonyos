#!/usr/bin/env python3
"""Conan recipe for ruby 3.4.10 — Ruby interpreter and core libraries.

Ruby is an Autotools project (configure + make).  On OHOS/PC (aarch64):

- config.guess/config.sub patched (E007/E268) to recognize HarmonyOS and
  accept the `aarch64-unknown-linux-ohos` triplet.
- configure script's config.status temp-dir creation changed from
  `umask 077` to `umask 022`: on HMDFS the setgid dir becomes
  drwx--S--- owned by the mapped uid, which the build user cannot write.
- Extensions fiddle/openssl/psych require libffi/openssl/libyaml, which are
  published on the ohpcd repo and declared below (R36).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import Autotools, AutotoolsToolchain, AutotoolsDeps
from conan.tools.layout import basic_layout


class RubyConan(ConanFile):
    name = "ruby"
    version = "3.4.10"
    description = "Ruby 3.4 interpreter and core libraries"
    license = "Ruby OR BSD-2-Clause"
    homepage = "https://www.ruby-lang.org/"
    url = ""  # CI fills this

    # Ruby is an interpreter with executables (bin/ruby, gem, irb, rake...).
    # R38: commands.json declared at software level (archives/r/ruby/commands.json)
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Published on ohpcd (R36): verified via conan download --only-recipe
        self.requires("libffi/3.5.2")      # fiddle extension
        self.requires("openssl/3.5.6.1.1")  # openssl extension
        self.requires("libyaml/0.2.5")      # psych extension

    def validate(self):
        # R32: settings.os must check in ("Linux", "OHOS"), not == "Linux"
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"ruby is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        # AutotoolsDeps: feed -I/-L from libffi/openssl/libyaml into configure
        deps = AutotoolsDeps(self)
        deps.generate()
        tc = AutotoolsToolchain(self)
        # R26 does NOT apply here: ruby is not a system-name library.
        # ruby needs shared extensions (openssl.so/psych.so/fiddle.so), so we
        # must NOT pass --disable-shared.
        tc.configure_args.append("--prefix=/")
        tc.generate()
        # OHOS loader has no default search path for conan-cached shared libs;
        # configure's conftest runs compiled programs, which fail with
        # "Error loading shared library" unless LD_LIBRARY_PATH points at deps.
        env = Environment()
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                env.prepend_path("LD_LIBRARY_PATH", libdir)
        env.vars(self, scope="build").save_script("conanbuild_runpath")

    def build(self):
        autotools = Autotools(self)
        autotools.configure()
        # R9: single job — parallel make hits HMDFS jobserver fifo EPERM
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        # Ruby is an interpreter: consumers use bin/ruby + gem, not link libruby
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        bin_dir = self.package_folder + "/bin"
        self.buildenv_info.prepend_path("PATH", bin_dir)
        self.runenv_info.prepend_path("PATH", bin_dir)

        # configure --prefix=/ hardcodes $LOAD_PATH to //lib/ruby/... which is
        # not reachable at runtime; export RUBYLIB pointing at the packaged
        # stdlib + arch extension dirs (needed for require "openssl" etc).
        arch_map = {
            "armv8": "aarch64",
            "armv8.3": "aarch64",
            "x86_64": "x86_64",
            "x86": "i686",
        }
        machine = arch_map.get(str(self.settings.arch), str(self.settings.arch))
        osname = "ohos" if self.settings.os == "OHOS" else "linux"
        lib_root = os.path.join(self.package_folder, "lib", "ruby", "3.4.0")
        for ruby_lib_dir in (
            os.path.join(lib_root, f"{machine}-linux-{osname}"),
            lib_root,
        ):
            self.buildenv_info.prepend_path("RUBYLIB", ruby_lib_dir)
            self.runenv_info.prepend_path("RUBYLIB", ruby_lib_dir)
