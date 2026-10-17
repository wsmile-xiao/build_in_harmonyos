#!/usr/bin/env python3
"""Consumer test for the installed libcdio 2.3.0 command-line tools.

The upstream binary fixtures (``copying.iso``, ``isofs-m1.bin``) are stored as
gzip+base64 text because GitCode's ``.diff`` endpoint drops binary patch data,
which makes a committed ``.iso``/``.bin`` unapplicable in the CI checkout
step. They are decoded back to the exact upstream bytes before the
comparisons run.
"""
import os
import base64
import gzip
import hashlib
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run


class LibcdioToolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    # name -> sha256 of the decoded upstream bytes
    _BINARY_FIXTURES = {
        "copying.iso": "5bb4ab6b1c8941d3aa2ada6cd93557facf314ffd9194b771a21655012ef95f1e",
        "isofs-m1.bin": "df3a421e25089b3cfd04cf0d402261386a7c299f5cb2d194a187a50800e2a8c0",
    }

    def _materialize_fixtures(self):
        source = os.path.join(self.source_folder, "fixtures")
        # `conan create` runs the test package with source_folder == build_folder,
        # so the decoded copies live in a sibling directory.
        target = os.path.join(self.build_folder, ".libcdio-fixtures")
        os.makedirs(target, exist_ok=True)

        for entry in sorted(os.listdir(source)):
            if entry.endswith(".b64"):
                continue
            shutil.copy2(os.path.join(source, entry), os.path.join(target, entry))

        for name, expected in sorted(self._BINARY_FIXTURES.items()):
            with open(os.path.join(source, name + ".b64"), "rb") as handle:
                decoded = gzip.decompress(base64.b64decode(handle.read()))
            digest = hashlib.sha256(decoded).hexdigest()
            if digest != expected:
                raise ConanInvalidConfiguration(
                    "fixture %s digest mismatch: %s" % (name, digest)
                )
            with open(os.path.join(target, name), "wb") as handle:
                handle.write(decoded)

        return target

    def test(self):
        if not can_run(self):
            raise ConanInvalidConfiguration(
                "libcdio-tools consumer test must run on the target OpenHarmony system"
            )

        dependency = self.dependencies["libcdio-tools"]
        bindir = os.path.join(dependency.package_folder, "bin")
        script = os.path.join(self.source_folder, "test.sh")
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        if not os.path.isfile(bash):
            bash = "/bin/sh"
        fixtures = self._materialize_fixtures()
        self.run(
            '"%s" "%s" "%s" "%s"' % (bash, script, bindir, fixtures),
            env="conanrun",
        )
