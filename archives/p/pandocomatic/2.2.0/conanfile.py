#!/usr/bin/env python3
"""Conan recipe for pandocomatic 2.2.0 — Ruby application (RubyGems).

pandocomatic is a RubyGem application that automates pandoc workflows.
It is NOT a C/C++ library: the platform's C/C++ label must not drive the
build. The package installs four pure-Ruby gems:

  - pandocomatic 2.2.0
  - paru 1.5.2       (pandoc wrapper, runtime dep of pandocomatic)
  - optimist 3.2.1   (CLI option parser, runtime dep)
  - logger 1.7.0     (stdlib-versioned runtime dep, required by gemspec)

Runtime dependencies:
- Ruby >= 3.1. The HarmonyOS PC build environment provides a system Ruby
  runtime at /data/service/hnp/bin/ruby (HNP). ruby/3.4.10 is NOT published
  to the ohpcd artifact registry, so this recipe uses the system Ruby to
  install the gems (same pattern as the existing mlt recipe which consumes
  the system-installed kwalify gem).
- pandoc/3.10.1 (published on ohpcd) is declared so test-time conversion
  has the converter available.
"""
import hashlib
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, download, mkdir
from conan.tools.layout import basic_layout

RUBY_BIN = "/data/service/hnp/bin/ruby"
GEM_BIN = "/data/service/hnp/bin/gem"
RUBY_STDLIB_GEMS = "/data/service/hnp/ruby.org/ruby_3.4.5/lib/ruby/gems/3.4.0"


class PandocomaticConan(ConanFile):
    name = "pandocomatic"
    version = "2.2.0"
    description = "Automate the use of pandoc (Ruby application)"
    license = "GPL-3.0-or-later"
    homepage = "https://heerdebeer.org/Software/markdown/pandocomatic/"
    url = ""
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        # pandoc is published on ohpcd; ruby is provided by HNP system runtime
        self.requires("pandoc/3.10.1")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "pandocomatic requires Ruby + pandoc; supported on Linux/OHOS")
        if self.settings.os == "OHOS":
            if not os.path.isfile(RUBY_BIN) or not os.path.isfile(GEM_BIN):
                raise ConanInvalidConfiguration(
                    "system Ruby runtime (HNP) not found; required on OHOS")

    def layout(self):
        basic_layout(self)

    def source(self):
        for name, meta in self.conan_data["sources"].items():
            dst = os.path.join(self.source_folder, name)
            download(self, meta["url"], dst, verify=False)
            sha = hashlib.sha256(open(dst, "rb").read()).hexdigest()
            if sha != meta["sha256"]:
                raise ConanInvalidConfiguration(
                    f"SHA256 mismatch for {name}: {sha}")

    def build(self):
        # Gems are pure Ruby archives; nothing to compile. Install them into
        # the package gem home so no network is needed at consumption time.
        gem_home = os.path.join(self.build_folder, "gems")
        mkdir(self, gem_home)
        for name in self.conan_data["sources"]:
            self.run(
                f'GEM_HOME="{gem_home}" GEM_PATH="{gem_home}" '
                f'"{GEM_BIN}" install --local '
                f'"{os.path.join(self.source_folder, name)}" '
                f'--install-dir "{gem_home}" --no-document --ignore-dependencies',
            )

    def package(self):
        copy(self, "*", src=os.path.join(self.build_folder, "gems"),
             dst=os.path.join(self.package_folder, "gems"))
        # Bundle the gem files themselves under share for reproducibility.
        copy(self, "*.gem", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "gem"))

    def package_info(self):
        gem_home = os.path.join(self.package_folder, "gems")
        self.runenv_info.define("GEM_HOME", gem_home)
        self.runenv_info.append_path("GEM_PATH", gem_home)
        # System Ruby stdlib gem dir (HNP) so logger/csv stdlib gems resolve.
        if os.path.isdir(RUBY_STDLIB_GEMS):
            self.runenv_info.append_path("GEM_PATH", RUBY_STDLIB_GEMS)
        bin_dir = os.path.join(gem_home, "bin")
        self.runenv_info.prepend_path("PATH", bin_dir)
        self.runenv_info.prepend_path("PATH", os.path.dirname(GEM_BIN))
        self.cpp_info.bindirs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []