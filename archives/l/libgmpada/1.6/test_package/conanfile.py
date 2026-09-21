import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import VirtualBuildEnv
from conan.tools.layout import basic_layout


class LibGmpAdaTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        # Same GNAT toolchain as the package under test.
        self.tool_requires("gcc-ada/9.5.0")
        self.tool_requires("binutils/2.46.0")

    def layout(self):
        basic_layout(self)

    def generate(self):
        VirtualBuildEnv(self).generate()

    def _consumer(self):
        return os.path.join(self.source_folder, "gmpada-consumer")

    def build(self):
        dep = self.dependencies["libgmpada"]
        adainclude = os.path.join(dep.package_folder, "share", "ada", "adainclude")
        adalib = os.path.join(dep.package_folder, "lib", "ada", "adalib")
        static_lib = os.path.join(dep.package_folder, "lib", "libgmpada.a")
        gmp = self.dependencies["gmp"]
        dirs = [d for d in gmp.cpp_info.libdirs if d]
        gmp_libdir = dirs[0] if dirs else ""
        gcc_ada = self.dependencies.build.get("gcc-ada")
        gnatmake = os.path.join(gcc_ada.package_folder, "bin", "gnatmake")
        script = os.path.join(self.source_folder, "test.sh")
        self.run('bash "{}" "{}" "{}" "{}" "{}" "{}"'.format(
            script, gnatmake, adainclude, adalib, static_lib, gmp_libdir),
            env="conanbuild")

    def test(self):
        if not can_run(self):
            self.output.warning("Consumer cannot run on this host; build-only check.")
            return
        exe = self._consumer()
        if not os.path.isfile(exe):
            raise ConanInvalidConfiguration("Ada consumer was not built")
        if str(self.settings.os) == "OHOS":
            self._sign_executable(exe)
        self.run('"{}"'.format(exe), env="conanbuild", cwd=self.source_folder)

    def _sign_executable(self, executable):
        """OHOS refuses exec of unsigned ELFs (E489/E517)."""
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanInvalidConfiguration(
                "OHOS consumer execution requires llvm-objcopy and binary-sign-tool")
        original_mode = os.stat(executable).st_mode
        temporary = "{}.signing".format(executable)
        try:
            shutil.copy2(executable, temporary)
            self.run('"{}" --remove-section .codesign "{}"'.format(objcopy, temporary))
            self.run('"{}" sign -inFile "{}" -outFile "{}" -selfSign 1'.format(
                signer, temporary, temporary))
            os.chmod(temporary, original_mode)
            os.replace(temporary, executable)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)

    def _find_ohos_tool(self, name):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        compiler_dir = os.path.dirname(compilers.get("cpp", ""))
        candidates = [
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        ]
        return next((path for path in candidates if os.path.isfile(path)), "")
