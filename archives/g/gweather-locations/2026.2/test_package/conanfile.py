#!/usr/bin/env python3
"""Conan test_package — consumer verification for gweather-locations.

gweather-locations is a data-only package (no headers, no libraries), so
there is nothing to compile against: the consumer test locates the installed
data set and runs test_locations.py, a pure-python GVariant deserializer
that fully parses Locations.bin and validates magic, structure and
referential integrity. See test_locations.py for the check list.
"""
import os
import sys

from conan import ConanFile


class GweatherLocationsTestConan(ConanFile):
    settings = "os", "arch", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["gweather-locations"]
        pkg = str(dep.package_folder)
        bin_path = os.path.join(pkg, "lib", "gweather-locations", "Locations.bin")
        assert os.path.isfile(bin_path), "Locations.bin missing: %s" % bin_path
        xml_path = os.path.join(pkg, "share", "gweather-locations", "Locations.xml")
        assert os.path.isfile(xml_path), "Locations.xml missing"
        dtd_path = os.path.join(pkg, "share", "gweather-locations", "locations.dtd")
        assert os.path.isfile(dtd_path), "locations.dtd missing"
        pc_path = os.path.join(pkg, "share", "pkgconfig", "gweather-locations.pc")
        assert os.path.isfile(pc_path), "gweather-locations.pc missing"
        with open(pc_path) as f:
            pc = f.read()
        assert "locations_db" in pc, "gweather-locations.pc missing locations_db variable"
        assert "locations_xml" in pc, "gweather-locations.pc missing locations_xml variable"
        script = os.path.join(os.path.dirname(__file__), "test_locations.py")
        py = sys.executable or "python3"
        self.run('"%s" "%s" "%s"' % (py, script, bin_path))
