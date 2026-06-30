#!/usr/bin/env python3
"""Conan test_package — Perl module test (L1).

Verifies that Net::NTP is properly packaged and loadable.
"""
import os
import glob

from conan import ConanFile


class PerlnetntpTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Get the package folder of the dependency (Conan 2.x API)
        pkg_folder = self.dependencies["perl-net-ntp"].package_folder
        # Find NTP.pm in the package
        pm_files = glob.glob(os.path.join(pkg_folder, "**", "NTP.pm"), recursive=True)
        if not pm_files:
            raise Exception("NTP.pm not found in package")
        ntp_pm = pm_files[0]
        self.output.info("Found NTP.pm at: {}".format(ntp_pm))

        # Verify file content
        with open(ntp_pm) as f:
            content = f.read()
        assert "package Net::NTP" in content, "NTP.pm: 'package Net::NTP' not found"
        assert "1.5" in content, "NTP.pm: version 1.5 not found in source"
        self.output.info("NTP.pm content verified: package Net::NTP version 1.5")

        # Write a test script and run it to verify the module loads
        lib_dir = os.path.dirname(os.path.dirname(ntp_pm))
        test_script = os.path.join(self.build_folder, "test_ntp.pl")
        with open(test_script, "w") as f:
            f.write("use Net::NTP;\n")
            f.write("my $v = $Net::NTP::VERSION;\n")
            f.write('die "version mismatch: got $v" unless $v eq "1.5";\n')
            f.write('print "OK: Net::NTP v$v\n";\n')
        self.run('perl -I"{}" "{}"'.format(lib_dir, test_script), env="conanrun")
