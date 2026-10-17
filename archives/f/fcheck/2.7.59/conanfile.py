#!/usr/bin/env python3
"""Conan recipe - fcheck 2.7.59.

fcheck is a pure Perl filesystem baseline checker.  The package installs the
upstream script and a small Perl launcher; there is no native compilation step.
"""
import os
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, save
from conan.tools.layout import basic_layout


class FcheckConan(ConanFile):
    name = "fcheck"
    version = "2.7.59"
    description = "Filesystem baseline integrity checker"
    license = "GPL-2.0-or-later"
    homepage = "http://web.archive.org/web/20050415074059/www.geocities.com/fcheck2000/"
    url = "https://salsa.debian.org/debian/fcheck"
    package_type = "application"

    settings = "os", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("perl/5.42.2", headers=False, libs=False, run=True)

    def layout(self):
        basic_layout(self)

    def configure(self):
        self.settings.rm_safe("os.version")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"fcheck only supports Linux/OHOS style filesystems, got {self.settings.os}")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        VirtualRunEnv(self).generate()

    def build(self):
        apply_conandata_patches(self)
        script = os.path.join(self.source_folder, "fcheck")
        cfg = os.path.join(self.source_folder, "fcheck.cfg")
        if not os.path.isfile(script):
            raise RuntimeError("upstream fcheck script is missing")
        if not os.path.isfile(cfg):
            raise RuntimeError("upstream fcheck.cfg is missing")

        if can_run(self):
            self.run(f'perl -c "{script}"', env="conanrun")
        else:
            self.output.warning("Cannot run host Perl on this build machine; syntax/runtime checks deferred to native OHOS validation")

    def package(self):
        share_dir = os.path.join(self.package_folder, "share", "fcheck")
        bin_dir = os.path.join(self.package_folder, "bin")

        copy(self, "license", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "README", src=self.source_folder, dst=share_dir, keep_path=False)
        copy(self, "install", src=self.source_folder, dst=share_dir, keep_path=False)
        copy(self, "fcheck", src=self.source_folder, dst=share_dir, keep_path=False)

        script = os.path.join(share_dir, "fcheck")
        packaged_script = os.path.join(share_dir, "fcheck.pl")
        os.replace(script, packaged_script)
        os.chmod(packaged_script, os.stat(packaged_script).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)

        sample_cfg = "\n".join(
            [
                "# Package-local sample configuration for fcheck.",
                "# Override with: fcheck -f /path/to/fcheck.cfg <directory>",
                "Directory = .",
                "DataBase = ./fcheck.dbf",
                "Exclusion = ./fcheck.dbf",
                "TimeZone = UTC",
                "FileTyper = /usr/bin/file",
                "Signature = /usr/bin/sha256sum",
                "",
            ]
        )
        save(self, os.path.join(share_dir, "fcheck.cfg"), sample_cfg)

        launcher = """#!/usr/bin/env perl
use strict;
use warnings;
use FindBin qw($Bin);
use File::Spec;

my $script = File::Spec->catfile($Bin, '..', 'share', 'fcheck', 'fcheck.pl');
my $default_config = File::Spec->catfile($Bin, '..', 'share', 'fcheck', 'fcheck.cfg');
my @args = @ARGV;

if (!@args) {
    @args = ('-af', $default_config);
} else {
    if ($args[0] =~ /^-/) {
        if ($args[0] !~ /f/) {
            $args[0] .= 'f';
            splice @args, 1, 0, $default_config;
        }
    } else {
        unshift @args, '-f', $default_config;
    }
}

exec {$^X} $^X, $script, @args;
die "failed to exec $script: $!";
"""
        save(self, os.path.join(bin_dir, "fcheck"), launcher)
        os.chmod(os.path.join(bin_dir, "fcheck"), 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.resdirs = ["share"]
