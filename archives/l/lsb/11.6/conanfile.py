#!/usr/bin/env python3
"""Conan recipe for lsb 11.6 (lsb_release and init-script helpers)."""

import os
import shutil
import stat

from conan import ConanFile
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class LsbConan(ConanFile):
    name = "lsb"
    version = "11.6"
    description = "Linux Standard Base release detection and init-script helper utilities"
    license = "GPL-2.0-only"
    homepage = "https://wiki.linuxfoundation.org/lsb/start"
    url = "https://salsa.debian.org/debian/lsb"
    topics = ("lsb", "lsb_release", "init-scripts")
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)
        copy(self, "files/debian.csv", src=self.recipe_folder, dst=self.export_sources_folder)
        # Keep the recipe-local path layout expected by build() and package().
        copy(
            self,
            "files/debian.csv",
            src=self.recipe_folder,
            dst=os.path.join(self.export_sources_folder, "files"),
        )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _python(self):
        for candidate in (os.environ.get("PYTHON"), shutil.which("python3"), shutil.which("python")):
            if candidate:
                return candidate
        raise RuntimeError("Python 3 is required to build and test lsb")

    def _shim_dir(self, python, test_dir):
        # The upstream test doubles start with ``#!/usr/bin/python3``; the OHOS
        # image has no /usr/bin/python3, so run them through the interpreter
        # this recipe already resolved. The upstream files stay untouched.
        shim_dir = os.path.join(self.build_folder, "test-bin")
        os.makedirs(shim_dir, exist_ok=True)
        for name in ("apt-cache", "dpkg-query"):
            shim = os.path.join(shim_dir, name)
            target = os.path.join(test_dir, name)
            with open(shim, "w", encoding="utf-8", newline="\n") as handle:
                handle.write('#!/bin/sh\nexec "%s" "%s" "$@"\n' % (python, target))
            os.chmod(shim, 0o755)
        return shim_dir

    def build(self):
        apply_conandata_patches(self)

        executable_files = (
            "lsb_release",
            "lsbinstall",
            "install_initd",
            "remove_initd",
            "test/lsb-test.sh",
            "test/apt-cache",
            "test/dpkg-query",
        )
        for relative_path in executable_files:
            path = os.path.join(self.source_folder, relative_path)
            os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

        python = self._python()
        test_dir = os.path.join(self.source_folder, "test")
        distro_info = os.path.join(self.export_sources_folder, "files", "debian.csv")
        shim_dir = self._shim_dir(python, test_dir)
        # Conan 2 resolves ``env=`` to generated environment scripts, so hand the
        # test environment to the shell inline instead.
        test_path = os.pathsep.join([shim_dir, test_dir])
        test_env = (
            f'PATH="{test_path}{os.pathsep}$PATH" '
            f'PYTHONPATH="{self.source_folder}" '
            f'LSB_DISTRO_INFO="{distro_info}"'
        )

        self.run(
            f'{test_env} {python} -m unittest discover -s test -p "test_*.py" -v',
            cwd=self.source_folder,
        )
        self.run(f'{test_env} sh test/lsb-test.sh "{self.source_folder}"', cwd=self.source_folder)

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        lib_dir = os.path.join(self.package_folder, "lib", "lsb")
        man1_dir = os.path.join(self.package_folder, "share", "man", "man1")
        man8_dir = os.path.join(self.package_folder, "share", "man", "man8")
        data_dir = os.path.join(self.package_folder, "share", "lsb", "distro-info")

        copy(self, "lsb_release", src=self.source_folder, dst=bin_dir)
        copy(self, "lsb_release.py", src=self.source_folder, dst=bin_dir)
        copy(self, "lsbinstall", src=self.source_folder, dst=bin_dir)
        copy(self, "install_initd", src=self.source_folder, dst=bin_dir)
        copy(self, "remove_initd", src=self.source_folder, dst=bin_dir)
        copy(self, "initdutils.py", src=self.source_folder, dst=bin_dir)
        copy(self, "init-functions", src=self.source_folder, dst=lib_dir)
        copy(self, "*", src=os.path.join(self.source_folder, "init-functions.d"), dst=os.path.join(lib_dir, "init-functions.d"))
        copy(self, "lsb_release.1", src=self.source_folder, dst=man1_dir)
        copy(self, "lsb.8", src=self.source_folder, dst=man8_dir)
        copy(self, "copyright", src=os.path.join(self.source_folder, "debian"), dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "debian.csv", src=os.path.join(self.export_sources_folder, "files"), dst=data_dir)

        for name in ("lsb_release", "lsbinstall", "install_initd", "remove_initd"):
            path = os.path.join(bin_dir, name)
            os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            self._rewrite_shebang(path)

    def _rewrite_shebang(self, path):
        # The upstream commands start with ``#!/usr/bin/python3``, which does
        # not exist on HarmonyOS. ``/usr/bin/env`` is present and finds the
        # interpreter on PATH, so replace only that first line and leave the
        # rest of each upstream command untouched.
        with open(path, encoding="utf-8") as handle:
            lines = handle.readlines()
        if not lines or not lines[0].startswith("#!") or "python3" not in lines[0]:
            return
        lines[0] = "#!/usr/bin/env python3\n"
        with open(path, "w", encoding="utf-8", newline="") as handle:
            handle.writelines(lines)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.prepend_path("PYTHONPATH", os.path.join(self.package_folder, "bin"))
        self.runenv_info.define_path("LSB_DISTRO_INFO", os.path.join(self.package_folder, "share", "lsb", "distro-info", "debian.csv"))
