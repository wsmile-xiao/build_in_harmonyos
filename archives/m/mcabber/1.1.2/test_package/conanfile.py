#!/usr/bin/env python3
"""Conan test_package - mcabber 1.1.2

R34: the packaged software must be substantially exercised.  mcabber installs a
terminal client (``bin/mcabber``) plus dlopen()ed plug-ins (``lib/mcabber/*.so``)
and exposes no library, so the tests run the installed binary and assert on its
real runtime behaviour.

Upstream mcabber 1.1.2 ships no test suite at all (no ``tests/`` directory and
no ``TESTS``/``check_PROGRAMS`` in any ``Makefile.am``), so these are the
supplementary HarmonyOS tests (R51 scenario 3).  Covered:

  1. ``mcabber -h``    binary installed, executable and argv parsing works
  2. ``mcabber -V``    runtime start-up path: the binary must load its
                       glib/loudmouth/ncurses dependency chain and report its
                       compile-time feature set
  3. ``-V`` must report unicode + modules support (configure really found
     ncursesw and the dlopen plug-in feature)
  4. the plug-in directory compiled into the binary (``PKGLIB_DIR``, printed by
     ``-V``) must follow the ``lib/mcabber`` layout the package ships, and that
     packaged directory must hold the four upstream plug-ins -- catches a
     broken plug-in layout, i.e. the classic "modules unavailable" failure
  5. an unknown option must exit non-zero (argument validation path)
  6. packaging hygiene: no libtool ``.la`` archives left in the package
"""
import os
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import load


class McabberTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies[self.tested_reference_str].package_folder

        # 1. usage banner ---------------------------------------------------
        self.run("mcabber -h", env="conanrun")

        # 2. version / compile-time report ----------------------------------
        # The report is written to a scratch directory on purpose: the CI runs
        # the test from the archive's test_package/ folder, so anything written
        # relative to the test source would end up inside the recipe tree.
        version_log = os.path.join(tempfile.gettempdir(), "mcabber-version.txt")
        self.run('mcabber -V > "%s"' % version_log, env="conanrun")
        out = load(self, version_log)
        self.output.info("mcabber -V output:\n" + out)

        # 3. feature report -------------------------------------------------
        lowered = out.lower()
        for token, label in (
            ("installation data directory", "the install data directory"),
            ("unicode support", "ncursesw/unicode support"),
            ("modules support", "dlopen plug-in support"),
        ):
            if token not in lowered:
                raise ConanInvalidConfiguration(
                    "mcabber -V does not report %s; output was:\n%s" % (label, out)
                )

        # 4. the plug-in directory must match the packaged runtime layout -----
        # mcabber dlopen()s its modules from PKGLIB_DIR (an absolute path baked
        # in at configure time; "/lib/mcabber" for conan's `--prefix=/`
        # staging), unless the `modules_dir` setting overrides it.  What the
        # package has to deliver is <package>/lib/mcabber with the four
        # upstream plug-ins, i.e. the same "lib/mcabber" layout the binary was
        # compiled for (consumers point `modules_dir` at it).
        mods_dir = ""
        for line in out.splitlines():
            if "modules directory:" in line.lower():
                mods_dir = line.split(":", 1)[1].strip()
        if not mods_dir:
            raise ConanInvalidConfiguration(
                "mcabber -V did not report a plug-in directory; output was:\n%s" % out
            )
        if not mods_dir.rstrip("/").endswith("lib/mcabber"):
            raise ConanInvalidConfiguration(
                "compiled-in plug-in directory %r does not follow the packaged "
                "lib/mcabber layout" % mods_dir
            )

        packaged_mods = os.path.join(pkg_folder, "lib", "mcabber")
        if not os.path.isdir(packaged_mods):
            raise ConanInvalidConfiguration(
                "the package does not ship the plug-in directory %s" % packaged_mods
            )
        expected = {"libbeep.so", "libfifo.so", "liburlregex.so", "libxttitle.so"}
        found = {name for name in os.listdir(packaged_mods) if name.endswith(".so")}
        missing = expected - found
        if missing:
            raise ConanInvalidConfiguration(
                "plug-ins missing from %s: %s (found %s)"
                % (packaged_mods, sorted(missing), sorted(found))
            )
        self.output.info("plug-ins packaged in %s: %s" % (packaged_mods, sorted(found)))

        # 5. unknown option must fail ---------------------------------------
        try:
            self.run("mcabber --definitely-not-an-option", env="conanrun")
        except Exception:
            pass  # expected: getopt() returns '?' -> main() returns -1
        else:
            raise ConanInvalidConfiguration("mcabber accepted an unknown option")

        # 6. no libtool archives in the package -----------------------------
        leftovers = [
            os.path.join(root, name)
            for root, _, names in os.walk(pkg_folder)
            for name in names
            if name.endswith(".la")
        ]
        if leftovers:
            raise ConanInvalidConfiguration(
                "libtool archives were not removed from the package: %s" % leftovers
            )
