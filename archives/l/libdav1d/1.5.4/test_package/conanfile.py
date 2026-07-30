import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import chdir


class Libdav1dTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["libdav1d"].cpp_info
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = compilers.get("c") or os.environ.get("CC", "cc")
        tmp_dir = os.path.join(self.source_folder, "tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        os.environ["TMP"] = tmp_dir
        os.environ["TEMP"] = tmp_dir
        cc = self._compiler_command(cc)
        includes = " ".join(shlex.quote(f"-I{path}") for path in dep.includedirs)
        libdirs = " ".join(shlex.quote(f"-L{path}") for path in dep.libdirs)
        libs = " ".join(f"-l{lib}" for lib in dep.libs + dep.system_libs)
        with chdir(self, self.source_folder):
            self.run(f"{cc} test_package.c -o test_package {includes} {libdirs} {libs}")

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: skipping run")
            return
        exe_name = "test_package.exe" if self.settings.os == "Windows" else "test_package"
        exe = os.path.join(self.source_folder, exe_name)
        self.run(exe, env="conanrun")

    def _compiler_command(self, compiler):
        if str(self.settings.os) == "OHOS" and self._is_shell_script(compiler):
            shell = os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL") or "/bin/sh"
            return "{} {}".format(shlex.quote(shell), shlex.quote(compiler))
        return shlex.quote(compiler)

    @staticmethod
    def _is_shell_script(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(32).startswith(b"#!")
        except OSError:
            return False
