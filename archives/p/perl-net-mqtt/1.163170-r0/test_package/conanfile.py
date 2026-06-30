#!/usr/bin/env python3
"""Conan test_package for perl-net-mqtt — Perl module file verification.

Verifies that Net::MQTT .pm files are installed in the package.
Also attempts to load the module by setting PERL5LIB.
"""
import os
import glob

from conan import ConanFile


class PerlnetmqttTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass

    def test(self):
        # Verify that the .pm files are installed in the package
        pkg_folder = self.dependencies["perl-net-mqtt"].package_folder
        mqtt_pm = os.path.join(pkg_folder, "lib", "Net", "MQTT", "Constants.pm")
        if os.path.exists(mqtt_pm):
            self.output.success("Net/MQTT/Constants.pm found in package")
        else:
            found = glob.glob(os.path.join(pkg_folder, "**", "Constants.pm"), recursive=True)
            if found:
                self.output.success("Net/MQTT/Constants.pm found at: {}".format(found[0]))
            else:
                raise Exception("Net/MQTT .pm files not found in package")

        # Try to load the module by setting PERL5LIB
        perllib = os.path.join(pkg_folder, "lib")
        self.run(f"PERL5LIB={perllib} perl -MNet::MQTT::Constants -e 'print \"Module loaded OK\\n\"'")
