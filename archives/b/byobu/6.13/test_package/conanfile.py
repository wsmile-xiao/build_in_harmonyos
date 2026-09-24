#!/usr/bin/env python3
"""Conan test_package for byobu — verifies the installed scripts work."""
import os
import tempfile

from conan import ConanFile

class ByobuTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["byobu"]
        byobu_prefix = dep.package_folder
        bin_dir = dep.cpp_info.bindirs[0]
        byobu_bin = os.path.join(bin_dir, "byobu")
        self.run("test -e '%s'" % byobu_bin, env="conanrun")
        self.run("test -x '%s'" % byobu_bin, env="conanrun")
        self.run("head -1 '%s' | grep -q '^#!.*sh'" % byobu_bin, env="conanrun")
        self.run("grep -q 'version' '%s'" % byobu_bin, env="conanrun")
        # E058 patch presence: HOME ownership check must be guarded by uname -s
        self.run("grep -q 'uname -s' '%s'" % byobu_bin, env="conanrun")
        col1_bin = os.path.join(bin_dir, "col1")
        self.run("test -x '%s'" % col1_bin, env="conanrun")
        # Functional check: col1 prints the first column of stdin
        # (input via tempfile — test_package runs in-place, never pollute it)
        fd, input_path = tempfile.mkstemp(prefix="byobu_col1_", suffix=".txt")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("a b c\n")
        self.run("'%s' < '%s' | grep -qx 'a'" % (col1_bin, input_path), env="conanrun")
        os.unlink(input_path)
        self.run("test -f '%s/lib/byobu/include/dirs'" % byobu_prefix, env="conanrun")
        self.run("test -f '%s/lib/byobu/include/common'" % byobu_prefix, env="conanrun")
        self.run("test -f '%s/lib/byobu/include/colors'" % byobu_prefix, env="conanrun")
        self.run("test -f '%s/lib/byobu/include/constants'" % byobu_prefix, env="conanrun")
        self.run("test -f '%s/share/byobu/status/status'" % byobu_prefix, env="conanrun")
        self.run("test -f '%s/share/byobu/status/statusrc'" % byobu_prefix, env="conanrun")
        self.run("test -f '%s/etc/byobu/backend'" % byobu_prefix, env="conanrun")
        self.run("test -L '%s/bin/byobu-screen'" % byobu_prefix, env="conanrun")
        self.run("test -L '%s/bin/byobu-tmux'" % byobu_prefix, env="conanrun")
        self.run("test -f '%s/share/man/man1/byobu.1'" % byobu_prefix, env="conanrun")
        self.run("test -n '$BYOBU_PREFIX'", env="conanrun")
