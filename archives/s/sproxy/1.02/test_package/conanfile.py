#!/usr/bin/env python3
"""Consumer test for sproxy/1.02.

Runs the installed Perl proxy for real: start bin/sproxy, send HTTP requests
through it to a local origin server and check both the forwarded responses and
the URL log sproxy writes (see test_sproxy.py).
"""
from conan import ConanFile


class SproxyTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        import os
        dep = self.dependencies[self.tested_reference_str]
        script = os.path.join(self.source_folder, "test_sproxy.py")
        self.run(f'python3 "{script}" "{dep.package_folder}" "{self.build_folder}"',
                 env="conanrun")
