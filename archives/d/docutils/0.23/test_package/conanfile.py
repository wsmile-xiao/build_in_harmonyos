import os
import shutil

from conan import ConanFile


class DocutilsTestConan(ConanFile):
    """docutils test_package — package integrity + CLI smoke test.

    Two-level verification:
      1) Package integrity (hard assert): docutils/__init__.py exists and
         __version__ == "0.23", core module present.
      2) Functional test: rst2html converts reStructuredText to HTML,
         verifying the entry-point script and the docutils API.
    """
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        docutils_pkg = self.dependencies["docutils"]
        site_packages = os.path.join(
            str(docutils_pkg.package_folder), "lib", "python3.12", "site-packages")
        bin_dir = os.path.join(str(docutils_pkg.package_folder), "bin")
        self.output.info("docutils site-packages: " + site_packages)
        py = shutil.which("python3") or "python3"
        test_script = os.path.join(self.source_folder, "test.py")
        self.run('DOCUTILS_SITE_PACKAGES="{sp}" DOCUTILS_BIN="{bd}" {py} "{ts}"'.format(
            sp=site_packages, bd=bin_dir, py=py, ts=test_script))
