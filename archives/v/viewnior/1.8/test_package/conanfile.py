#!/usr/bin/env python3
"""Consumer test for viewnior/1.8.

viewnior is a GTK+2 GUI image viewer.  The package ships a headless
`--version` early-exit (patch 0001) so the consumer test can run the real
binary on OHOS build workers without an X server.  The assertions live in
viewnior_test.py so the package ships a real test source file (CI L0c).
"""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class ViewniorTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        dep = self.dependencies["viewnior"]
        binary = os.path.join(dep.cpp_info.bindirs[0], "viewnior")
        test_script = os.path.join(self.source_folder, "viewnior_test.py")
        # env="conanrun" puts the dependency libdirs (gtk2/glib/gdk-pixbuf
        # closure + exiv2's expat/zlib) on LD_LIBRARY_PATH; the child python
        # inherits it so the GTK+2 shared-library closure resolves.
        self.run('"%s" "%s" "%s"' % (sys.executable, test_script, binary),
                 env="conanrun")
