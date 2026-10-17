#!/usr/bin/env python3
"""Conan recipe for the jdupes duplicate-file finder."""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class JdupesConan(ConanFile):
    name = "jdupes"
    version = "1.31.1"
    description = "Command-line duplicate file finder"
    license = "MIT"
    homepage = "https://codeberg.org/jbruchon/jdupes"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"jdupes is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def requirements(self):
        self.requires("libjodycode/4.1.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _shell(self):
        shell = os.environ.get("CONFIG_SHELL")
        if shell and (not os.path.isabs(shell) or os.path.exists(shell)):
            return shell
        if self.settings.os == "OHOS":
            return shutil.which("bash") or "bash"
        return shell or shutil.which("sh") or "sh"

    def _compiler_vars(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c", "clang")
        ar = compilers.get("ar", "llvm-ar")
        ranlib = compilers.get("ranlib", "llvm-ranlib")
        dep = self.dependencies["libjodycode"]
        include_dirs = getattr(dep.cpp_info, "includedirs", []) or []
        library_dirs = getattr(dep.cpp_info, "libdirs", []) or []
        include_flags = " ".join(f"-I{path}" for path in include_dirs)
        library_flags = " ".join(f"-L{path}" for path in library_dirs)
        values = [
            f"CC={shlex.quote(cc)}",
            f"AR={shlex.quote(ar)}",
            f"RANLIB={shlex.quote(ranlib)}",
            "IGNORE_NEARBY_JC=1",
            f"CFLAGS_EXTRA={shlex.quote(include_flags)}",
            f"LDFLAGS_EXTRA={shlex.quote(library_flags)}",
            f"SHELL={shlex.quote(self._shell())}",
        ]
        return " ".join(values), library_dirs

    @staticmethod
    def _ld_prefix(library_dirs):
        if not library_dirs:
            return ""
        path = os.pathsep.join(library_dirs)
        return f"LD_LIBRARY_PATH={shlex.quote(path)}:$LD_LIBRARY_PATH "

    def build(self):
        apply_conandata_patches(self)
        make_vars, library_dirs = self._compiler_vars()
        command = (
            f"{self._ld_prefix(library_dirs)}"
            f"make -C {shlex.quote(self.source_folder)} {make_vars} -j1"
        )
        self.run(command, env="conanbuild")

        # The upstream test target invokes this script; call it through the
        # resolved shell because the OHOS image does not guarantee /bin/sh.
        test_script = os.path.join(self.source_folder, "test.sh")
        self.run(
            f"{self._ld_prefix(library_dirs)}{shlex.quote(self._shell())} "
            f"{shlex.quote(test_script)}",
            env="conanbuild",
        )

    def package(self):
        make_vars, _ = self._compiler_vars()
        make_vars += " PREFIX=/ DESTDIR=" + shlex.quote(self.package_folder)
        # The OHOS image has mkdir/cp but does not provide the GNU install
        # utility.  The upstream Makefile exposes both copy commands, so use
        # cp without changing upstream source behavior.
        make_vars += " INSTALL_PROGRAM=cp INSTALL_DATA=cp"
        self.run(
            f"make -C {shlex.quote(self.source_folder)} {make_vars} install -j1",
            env="conanbuild",
        )

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
