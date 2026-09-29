#!/usr/bin/env python3
"""Consumer checks for the packaged Passenger command layout."""
import configparser
import os
import re
import shutil
import subprocess
import sys


COMMANDS = (
    "passenger",
    "passenger-config",
    "passenger-install-apache2-module",
    "passenger-install-nginx-module",
    "passenger-memory-stats",
    "passenger-status",
)

REQUIRED_LOCATION_FIELDS = (
    "packaging_method",
    "bin_dir",
    "support_binaries_dir",
    "lib_dir",
    "helper_scripts_dir",
    "resources_dir",
    "include_dir",
    "doc_dir",
    "ruby_libdir",
    "node_libdir",
    "apache2_module_path",
    "ruby_extension_source_dir",
    "nginx_module_source_dir",
)

EXPECTED_DIRECTORY_FIELDS = (
    "bin_dir",
    "support_binaries_dir",
    "lib_dir",
    "helper_scripts_dir",
    "resources_dir",
    "include_dir",
    "doc_dir",
    "ruby_libdir",
    "node_libdir",
    "ruby_extension_source_dir",
    "nginx_module_source_dir",
    "build_system_dir",
    "download_cache_dir",
)


class Checks:
    def __init__(self):
        self.total = 0
        self.failures = []

    def check(self, condition, message):
        self.total += 1
        if not condition:
            self.failures.append(message)

    def finish(self):
        passed = self.total - len(self.failures)
        print(
            "PASSENGER_TEST_RESULT "
            f"checks={self.total} passed={passed} failed={len(self.failures)}"
        )
        for failure in self.failures:
            print(f"FAIL: {failure}")
        return 1 if self.failures else 0


def normalized(path):
    return os.path.normcase(os.path.realpath(path))


def run_ruby_command(command, args, locations):
    env = os.environ.copy()
    env["PASSENGER_LOCATION_CONFIGURATION_FILE"] = locations
    result = subprocess.run(
        [command, *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=60,
        env=env,
        check=False,
    )
    output = (result.stdout or "").strip()
    return result.returncode, output


def main(argv):
    if len(argv) < 2:
        raise SystemExit("usage: check_passenger.py <package_folder> [--run]")

    package_folder = os.path.abspath(argv[1])
    should_run = "--run" in argv[2:]
    checks = Checks()

    bin_dir = os.path.join(package_folder, "bin")
    libexec = os.path.join(package_folder, "libexec", "passenger")
    ruby_libdir = os.path.join(libexec, "src", "ruby_supportlib")
    locations = os.path.join(
        ruby_libdir, "phusion_passenger", "locations.ini"
    )
    release_marker = os.path.join(libexec, "resources", "release.txt")

    checks.check(os.path.isdir(bin_dir), f"missing bin directory: {bin_dir}")
    checks.check(os.path.isdir(libexec), f"missing libexec tree: {libexec}")
    checks.check(
        os.path.isdir(ruby_libdir), f"missing Ruby support library: {ruby_libdir}"
    )
    checks.check(os.path.isfile(locations), f"missing locations.ini: {locations}")
    checks.check(
        os.path.isfile(release_marker), f"missing release marker: {release_marker}"
    )
    checks.check(
        os.path.isfile(os.path.join(ruby_libdir, "phusion_passenger.rb")),
        "packaged Ruby tree does not contain phusion_passenger.rb",
    )

    missing_commands = [
        name for name in COMMANDS if not os.path.isfile(os.path.join(bin_dir, name))
    ]
    checks.check(not missing_commands, f"missing command wrappers: {missing_commands}")

    for name in COMMANDS:
        wrapper = os.path.join(bin_dir, name)
        upstream = os.path.join(libexec, "bin", name)
        checks.check(
            os.path.isfile(wrapper) and os.access(wrapper, os.X_OK),
            f"wrapper is missing or not executable: {wrapper}",
        )
        checks.check(
            os.path.isfile(upstream) and os.access(upstream, os.X_OK),
            f"upstream command is missing or not executable: {upstream}",
        )
        if os.path.isfile(wrapper):
            content = open(wrapper, encoding="utf-8").read()
            checks.check(
                content.startswith("#!/bin/sh\n")
                and f"libexec/passenger/bin/{name}" in content,
                f"wrapper does not dispatch to the packaged command: {name}",
            )
        else:
            checks.check(False, f"wrapper content cannot be checked: {name}")

    if os.path.isfile(locations):
        parser = configparser.ConfigParser()
        parser.read(locations, encoding="utf-8")
        checks.check(parser.has_section("locations"), "locations.ini has no [locations]")
        missing_fields = [
            field
            for field in REQUIRED_LOCATION_FIELDS
            if not parser.has_option("locations", field)
        ]
        checks.check(
            not missing_fields, f"locations.ini is missing fields: {missing_fields}"
        )
        checks.check(
            parser.has_option("locations", "build_system_dir")
            and parser.has_option("locations", "download_cache_dir"),
            "locations.ini is missing optional packaging fields",
        )
        if parser.has_option("locations", "packaging_method"):
            checks.check(
                parser.get("locations", "packaging_method") == "homebrew",
                "locations.ini packaging_method is not homebrew",
            )
        if parser.has_option("locations", "ruby_libdir"):
            checks.check(
                normalized(parser.get("locations", "ruby_libdir"))
                == normalized(ruby_libdir),
                "locations.ini ruby_libdir does not point at the packaged tree",
            )
        for field in EXPECTED_DIRECTORY_FIELDS:
            if parser.has_option("locations", field):
                value = parser.get("locations", field)
                checks.check(
                    os.path.isdir(value),
                    f"locations.ini field {field} is not a directory: {value}",
                )
            else:
                checks.check(False, f"locations.ini field cannot be checked: {field}")

    if should_run:
        ruby = shutil.which("ruby")
        checks.check(ruby is not None, "Ruby is required for Passenger runtime checks")
        if ruby:
            returncode, output = run_ruby_command(
                os.path.join(bin_dir, "passenger"), ["--version"], locations
            )
            checks.check(
                returncode == 0 and bool(re.search(r"6\.1\.8", output)),
                f"passenger --version failed: rc={returncode}, output={output[-500:]}",
            )

            returncode, output = run_ruby_command(
                os.path.join(bin_dir, "passenger-config"),
                ["about", "version"],
                locations,
            )
            checks.check(
                returncode == 0 and bool(re.search(r"6\.1\.8", output)),
                "passenger-config about version failed: "
                f"rc={returncode}, output={output[-500:]}",
            )

            returncode, output = run_ruby_command(
                os.path.join(bin_dir, "passenger-config"),
                ["about", "ruby-libdir"],
                locations,
            )
            checks.check(
                returncode == 0 and normalized(output) == normalized(ruby_libdir),
                "passenger-config about ruby-libdir failed: "
                f"rc={returncode}, output={output[-500:]}",
            )

    return checks.finish()


if __name__ == "__main__":
    sys.exit(main(sys.argv))
