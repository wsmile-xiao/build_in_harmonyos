#!/usr/bin/env python3
"""Conan test_package for vor 0.5.8 (application).

vor is an SDL 1.2 game: a full session needs a display (and, for the music, an
audio device).  Upstream parses ``--version``/``--help`` in ``main()`` *before*
touching SDL (``args.c: short_opt('V')`` prints the banner and exits 0), so a
headless consumer suite is possible without patching anything.

What is asserted (all inside test.sh, which keeps the assertion count
machine-readable in the log; L0c requires a test source file in this folder):

  * the CLI surface of the built binary (version banner, help, option errors);
  * that the packaged ``share/vor`` really is the directory the executable
    resolves at run time - proven bidirectionally by hiding it and putting it
    back (``file.c:find_data_dir()`` third candidate = baked DATA_PREFIX);
  * that the dynamically linked SDL 1.2 stack loads (no runtime linker error);
  * the packaged data asset set (59 PNG + bang.wav + mph.xm = 61 files).

What is *not* asserted: opening a window / playing sound.  See notes.md
"运行期能力实测" for the actual observed error string - the display layer is a
disclosed environment limitation, not something this test hides.
"""
import os

from conan import ConanFile


class VorTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if self.settings.os not in ("Linux", "OHOS"):
            return
        package_folder = self.dependencies["vor"].package_folder
        binary = os.path.join(package_folder, "bin", "vor")
        assert os.path.isfile(binary), "vor binary missing at %s" % binary
        datadir = os.path.join(package_folder, "share", "vor")

        script = os.path.join(self.source_folder, "test.sh")
        # test.sh is POSIX-only, and /bin/sh (toybox ash) is the shell that
        # probes clean on HMDFS; the profile's CONFIG_SHELL (hnp bash) prints
        # "job-working-directory: error retrieving current directory: getcwd"
        # noise from inside conan package folders, so it is not used here.
        shell = "/bin/sh" if os.path.exists("/bin/sh") else (
            os.environ.get("CONFIG_SHELL") or "/data/service/hnp/bin/bash")
        # outputs stay inside a private temp dir: conan create runs the test
        # with build_folder == source_folder, so writing here would pollute
        # archives/v/vor/0.5.8/test_package/ (JC4/JC5).
        self.run(
            '"%s" "%s" "%s" "%s"' % (shell, script, binary, datadir),
            env="conanrun",
        )
