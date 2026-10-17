#!/usr/bin/env python3
"""Conan test_package for pd-iemlib 1.22.3.

Loads the installed iemlib library with the OHOS ``pd`` from the puredata
package and runs twelve assertions:

* five iemlib classes driven directly ([db2v], [v2db], [split] on both
  outlets, [modulo_counter] counting and wrapping), plus the library load
  banner;
* an end-to-end consumer round trip through the packaged abstractions
  [dbtofad] / [fadtodb] (each one internally drives the iemlib C object
  [transf_fader] with its own breakpoint table):
  MIDI-dB 40 -> fader-scale 6 -> MIDI-dB 40;
* three anti-false-green guards, because a Pd object that failed to load
  still answers some messages and could keep the prints above green.
"""
import json
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException

CHECKS = 12


class PdIemlibTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("puredata/0.54.1")

    def _bash(self):
        for candidate in (
            os.environ.get("CONFIG_SHELL"),
            "/storage/Users/currentUser/.harmonybrew/bin/bash",
            "/data/service/hnp/bin/bash",
            "/bin/bash",
        ):
            if candidate and os.path.isfile(candidate):
                return candidate
        return "bash"

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        ext_dir = os.path.join(dep.package_folder, "lib", "pd-externals")
        pd_bin = os.path.join(self.dependencies["puredata"].package_folder,
                              "bin", "pd")
        for path in (pd_bin, os.path.join(ext_dir, "iemlib.pd_linux")):
            if not os.path.isfile(path):
                raise ConanException("required artifact not found: %s" % path)

        here = os.path.dirname(os.path.abspath(__file__))
        patch = os.path.join(here, "test_pd_iemlib.pd")
        script = os.path.join(here, "test_pd_iemlib.sh")
        workdir = os.environ.get("TMPDIR") or os.path.join(os.path.expanduser("~"), "tmp")
        os.makedirs(workdir, exist_ok=True)

        inner = ('PD_BIN=%s EXT_DIR=%s PATCH=%s TMPDIR=%s sh %s'
                 % (shlex.quote(pd_bin), shlex.quote(ext_dir),
                    shlex.quote(patch), shlex.quote(workdir), shlex.quote(script)))
        if self.settings.os == "OHOS":
            command = "%s -c %s" % (shlex.quote(self._bash()), shlex.quote(inner))
        else:
            command = inner
        rc = self.run(command, ignore_errors=True, env="conanrun")

        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": (rc == 0),
            "command": "test_pd_iemlib.sh (pd loads the iemlib library and drives the packaged dbtofad/fadtodb abstractions)",
            "consumer_passed": CHECKS if rc == 0 else 0,
            "consumer_total": CHECKS,
        }))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "skipped",
            "reason": "pd-iemlib has no upstream test suite (only Pd help patches and examples)",
            "discovered": 0, "executed": 0, "passed": 0, "failed": 0, "skipped": 0,
        }))

        if rc != 0:
            raise ConanException("pd-iemlib test failed (rc=%s)" % rc)
