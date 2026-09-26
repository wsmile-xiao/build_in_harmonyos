#!/usr/bin/env python3
import os

from conan import ConanFile


class IsoqlogTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # isoqlog is an application: the consumer test runs the installed
        # binary as a real user would (direvent/5.5 precedent) and asserts on
        # the HTML reports it produces.  The binary is passed by absolute path
        # so the test genuinely depends on this package's artifact.
        pkg_folder = self.dependencies["isoqlog"].package_folder
        bin_path = os.path.join(pkg_folder, "bin", "isoqlog")
        script = os.path.join(self.source_folder, "test.sh")
        # /bin/sh is the POSIX shell that exists both on the device and on the
        # CI worker; hnp bash is not guaranteed to be installed.
        cmd = f'/bin/sh "{script}" "{bin_path}" "{pkg_folder}"'
        # On the shared adaptation device the tested binary must run under a hard
        # RSS budget.  The executor is a toolbelt script that lives on that device,
        # not in this recipe, so CI runs the bare command while the device injects
        # it through ISOQLOG_MEMCAP.  Measured on the device with memcap-run.py:
        # whole 12-assertion round peaks at 11 MB under --probe and 10 MB while the
        # recipe's test() runs it, so the 64 MB budget below leaves ~6x headroom
        # (memcap-probe.log:17, memcap-test.log:74 and :76; see MANIFEST.yml max_rss_*).
        memcap = os.environ.get("ISOQLOG_MEMCAP")
        if memcap:
            cmd = f'{memcap} --mb 64 -- {cmd}'
        self.run(cmd, env="conanrun")
