#!/usr/bin/env python3
"""Conan recipe for tinyarray 1.2.5, a CPython C++ extension."""

import glob
import os
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.layout import basic_layout


class TinyarrayConan(ConanFile):
    name = "tinyarray"
    version = "1.2.5"
    description = "Small immutable arrays optimized for Python"
    license = "BSD-3-Clause"
    homepage = "https://gitlab.kwant-project.org/kwant/tinyarray"
    url = "https://gitlab.kwant-project.org/kwant/tinyarray"
    package_type = "python-require"
    settings = "os", "arch", "compiler", "build_type"
    options = {"python_abi": ["3.12", "3.14", "3.15"]}
    default_options = {"python_abi": "3.12"}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        self._freeze_archive_version()
        python = self._python()
        self._check_python_abi(python)

        env = os.environ.copy()
        build_tools = os.path.join(self.build_folder, "build-tools")
        os.makedirs(build_tools, exist_ok=True)
        self._run([python, "-m", "pip", "install", "--disable-pip-version-check",
                   "--no-compile", "--target", build_tools, "setuptools==71.1.0"], env=env)
        env["PYTHONPATH"] = build_tools + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")

        compiler = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        if compiler.get("c"):
            env["CC"] = compiler["c"]
        if compiler.get("cpp"):
            env["CXX"] = compiler["cpp"]
        if compiler.get("ar"):
            env["AR"] = compiler["ar"]
        cxx = compiler.get("cpp") or shutil.which("clang++") or "clang++"
        # The Harmonybrew interpreter's LDSHARED contains -lintl for linking
        # Python itself. That library is not part of an extension's link needs
        # and is absent from the HarmonyOS SDK, so use a clean C++ DSO linker.
        env["LDSHARED"] = cxx + " -shared"
        env["LDCXXSHARED"] = cxx + " -shared"

        self._run([python, "setup.py", "build_ext", "--inplace"], env=env)
        extensions = glob.glob(os.path.join(self.source_folder, "tinyarray*.so"))
        if len(extensions) != 1:
            raise ConanException("expected one tinyarray CPython extension, found {}".format(len(extensions)))

    def _freeze_archive_version(self):
        version_file = os.path.join(self.source_folder, "version")
        with open(version_file, encoding="utf-8") as stream:
            lines = stream.readlines()
        if any(line.strip() == "__use_git__" for line in lines):
            # GitLab tag archives omit .git metadata; setup.py otherwise falls
            # back to the invalid setuptools version string "unknown".
            with open(version_file, "w", encoding="utf-8") as stream:
                stream.write(self.version + "\n")

    def _python(self):
        abi = str(self.options.python_abi)
        candidates = [os.environ.get("HMBS_PYTHON3"), shutil.which("python" + abi),
                      shutil.which("python3"), sys.executable]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                probe = subprocess.run(
                    [candidate, "-c", "import sys; print('%d.%d' % sys.version_info[:2])"],
                    stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
                )
                if probe.returncode == 0 and probe.stdout.strip() == abi:
                    return candidate
        raise ConanException("CPython {} is required; set HMBS_PYTHON3 or install python{}".format(abi, abi))

    def _check_python_abi(self, python):
        probe = subprocess.run(
            [python, "-c", "import sysconfig; print(sysconfig.get_config_var('EXT_SUFFIX') or '')"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        if probe.returncode or not probe.stdout.strip().endswith(".so"):
            raise ConanException("selected CPython does not report an ELF extension suffix: {}".format(probe.stdout))

    def _run(self, command, env=None):
        self.output.info("Running: " + " ".join(command))
        result = subprocess.run(command, cwd=self.source_folder, env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                text=True, errors="replace")
        for line in (result.stdout or "").splitlines():
            self.output.info(line)
        if result.returncode:
            raise ConanException("command exited {}: {}".format(result.returncode, " ".join(command)))

    def package(self):
        abi = str(self.options.python_abi)
        site = os.path.join(self.package_folder, "lib", "python{}".format(abi), "site-packages")
        os.makedirs(site, exist_ok=True)
        for path in glob.glob(os.path.join(self.source_folder, "tinyarray*.so")):
            target = os.path.join(site, os.path.basename(path))
            shutil.copy2(path, target)
            self._sign_ohos_extension(target)
        licenses = os.path.join(self.package_folder, "licenses")
        os.makedirs(licenses, exist_ok=True)
        shutil.copy2(os.path.join(self.source_folder, "LICENSE.rst"),
                     os.path.join(licenses, "LICENSE.rst"))

    def _sign_ohos_extension(self, path):
        if str(self.settings.os) != "OHOS":
            return
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        objcopy_tool = "/data/service/hnp/bin/llvm-objcopy"
        if not os.path.isfile(sign_tool):
            self.output.warning("OHOS code signing skipped: {} not found".format(sign_tool))
            return
        if os.path.isfile(objcopy_tool):
            subprocess.run([objcopy_tool, "--remove-section", ".codesign", path],
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        signed_path = path + ".signed"
        result = subprocess.run(
            [sign_tool, "sign", "-inFile", path, "-outFile", signed_path, "-selfSign", "1"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        if result.returncode or not os.path.isfile(signed_path):
            raise ConanException("OHOS code signing failed for {}: {}".format(path, result.stdout))
        shutil.move(signed_path, path)
        os.chmod(path, 0o755)

    def package_info(self):
        site = os.path.join("lib", "python{}".format(self.options.python_abi), "site-packages")
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("PYTHONPATH", os.path.join(self.package_folder, site))
