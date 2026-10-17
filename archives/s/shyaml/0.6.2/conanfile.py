import os
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class ShyamlConan(ConanFile):
    name = "shyaml"
    version = "0.6.2"
    description = "Command-line interface for querying YAML"
    license = "BSD-3-Clause"
    homepage = "https://github.com/0k/shyaml"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires("pyyaml/6.0.2", run=True)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _py_site_rel(self):
        return os.path.join(
            "lib",
            f"python{sys.version_info.major}.{sys.version_info.minor}",
            "site-packages",
        )

    def build(self):
        apply_conandata_patches(self)
        src = self.source_folder
        module = os.path.join(src, "shyaml.py")
        if not os.path.isfile(module):
            raise ConanException("upstream shyaml.py is missing from the pinned source archive")

        # This release archive has no .git directory. Its setup.py invokes
        # autogen.sh to substitute %%version%%, and autogen.sh requires git
        # describe --tags. Stage the pure-Python module directly instead.
        staging = os.path.join(self.build_folder, "stage")
        site = os.path.join(staging, self._py_site_rel())
        bindir = os.path.join(staging, "bin")
        os.makedirs(site, exist_ok=True)
        os.makedirs(bindir, exist_ok=True)
        staged_module = os.path.join(site, "shyaml.py")
        shutil.copyfile(module, staged_module)
        with open(staged_module, "r", encoding="utf-8") as handle:
            contents = handle.read()
        contents = contents.replace('__version__ = "%%version%%"', '__version__ = "0.6.2"')
        if '"%%version%%"' in contents:
            raise ConanException("unsubstituted shyaml version placeholder remains")
        with open(staged_module, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(contents)

        # Keep the launcher relocatable and independent of the source-tree symlink.
        launcher = os.path.join(bindir, "shyaml")
        py_site = self._py_site_rel().replace(os.sep, "/")
        with open(launcher, "w", encoding="utf-8", newline="\n") as handle:
            handle.write("#!/usr/bin/env python3\n")
            handle.write("import os\nimport sys\n")
            handle.write("prefix = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))\n")
            handle.write(f"sys.path.insert(0, os.path.join(prefix, {py_site.split('/')[0]!r}, {py_site.split('/')[1]!r}, {py_site.split('/')[2]!r}))\n")
            handle.write("from shyaml import entrypoint\nentrypoint()\n")
        os.chmod(launcher, 0o755)

        # The upstream bin/test script uses Bash arrays and docshtest shell
        # examples. OHOS workers do not provide bash, so run its Python doctest
        # suites directly; the installed CLI is exercised by test_package.
        command = (
            f'cd "{src}" && "{sys.executable}" -m doctest -v shyaml.py && '
            f'"{sys.executable}" -m doctest -v README.rst'
        )
        self.run(command, env="conanrun")
        self._staging_dir = staging

    def package(self):
        copy(self, "*", src=self._staging_dir, dst=self.package_folder)
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        site_packages = os.path.join(self.package_folder, self._py_site_rel())
        self.runenv_info.prepend_path("PYTHONPATH", site_packages)
        self.buildenv_info.prepend_path("PYTHONPATH", site_packages)
        bindir = os.path.join(self.package_folder, "bin")
        self.runenv_info.prepend_path("PATH", bindir)
        self.buildenv_info.prepend_path("PATH", bindir)
