#!/usr/bin/env python3
"""Conan recipe for j4-dmenu-desktop 3.2 on HarmonyOS PC."""
import os
import shutil
import subprocess
from pathlib import Path

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.files import copy, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.meson import Meson, MesonToolchain


def _sign_ohos_elf(path):
    """Self-sign a built ELF when the HarmonyOS signing tools are present."""
    try:
        if Path(path).read_bytes()[:4] != b"\x7fELF":
            return
    except OSError:
        return

    signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
    objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
    if not os.path.isfile(signer) or not os.path.isfile(objcopy):
        return

    workdir = os.path.join(os.path.dirname(path), ".ohos-sign")
    os.makedirs(workdir, exist_ok=True)
    unsigned = os.path.join(workdir, os.path.basename(path))
    signed = unsigned + ".signed"
    shutil.copy2(path, unsigned)
    subprocess.run([objcopy, "--remove-section", ".codesign", unsigned],
                   capture_output=True, timeout=15, check=False)
    result = subprocess.run(
        [signer, "sign", "-inFile", unsigned, "-outFile", signed,
         "-selfSign", "1"],
        capture_output=True, text=True, timeout=30, check=False,
    )
    if result.returncode == 0 and os.path.isfile(signed):
        shutil.move(signed, path)
        os.chmod(path, 0o755)
    shutil.rmtree(workdir, ignore_errors=True)


class J4DmenuDesktopConan(ConanFile):
    name = "j4-dmenu-desktop"
    version = "3.2"
    description = "Fast desktop application launcher using dmenu-compatible frontends"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/enkore/j4-dmenu-desktop"
    url = "https://atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("desktop", "launcher", "dmenu")
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # spdlog/1.17.0 is built against external fmt/12.2.0 in the ohpcd
        # repository; declaring both keeps the dependency graph explicit.
        self.requires("fmt/12.2.0")
        self.requires("spdlog/1.17.0")

    def build_requirements(self):
        self.test_requires("catch2/3.8.1")

    def layout(self):
        self.folders.build = "builddir"
        self.folders.generators = "builddir/generators"

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        # The current spdlog/fmt packages expose both include/ and their nested
        # include/spdlog or include/fmt directories.  The nested spdlog path
        # shadows the real <fmt/ranges.h> with spdlog/fmt/ranges.h, so upstream
        # sees no fmt::join.  Only the public include root is required.
        for dep_name in ("fmt", "spdlog", "catch2"):
            dep = self.dependencies.get(dep_name)
            if dep and dep.package_folder:
                dep.cpp_info.includedirs = [
                    os.path.join(dep.package_folder, "include")
                ]
        PkgConfigDeps(self).generate()

        tc = MesonToolchain(self)
        tc.project_options["enable-tests"] = True
        tc.project_options["notify-implementation"] = "inotify"
        tc.project_options["generate-shell-completions"] = "disabled"
        tc.project_options["enabled-shell-completions"] = []
        tc.project_options["override-version"] = self.version
        tc.project_options["split-source"] = True
        tc.project_options["unity"] = "off"
        ar = shutil.which("llvm-ar") or "/data/service/hnp/bin/llvm-ar"
        if os.path.isfile(ar):
            tc.binaries["ar"] = ar
        tc.generate()

    def build(self):
        meson = Meson(self)
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env = Environment()
        env.define("TMPDIR", tmpdir)
        with env.vars(self).apply():
            meson.configure()
            meson.build()

            if can_run(self):
                meson.test()

        if str(self.settings.os) == "OHOS":
            for candidate in (
                os.path.join(self.build_folder, "src", "j4-dmenu-desktop"),
                os.path.join(self.build_folder, "tests", "j4-dmenu-tests"),
            ):
                _sign_ohos_elf(candidate)

    def package(self):
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env = Environment()
        env.define("TMPDIR", tmpdir)
        with env.vars(self).apply():
            Meson(self).install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        if str(self.settings.os) == "OHOS":
            _sign_ohos_elf(os.path.join(
                self.package_folder, "bin", "j4-dmenu-desktop"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
