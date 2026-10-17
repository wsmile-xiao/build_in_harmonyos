import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import VirtualBuildEnv
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class TestPackageConan(ConanFile):
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
        # provides ncursesw.pc so test.sh can link the static Ada library
        PkgConfigDeps(self).generate()

    def build(self):
        # basic_layout puts the cwd in its own folder, so address the script
        # by absolute path.
        #
        # The Ada search paths are passed EXPLICITLY: the
        # ADA_INCLUDE_PATH/ADA_OBJECTS_PATH that libncursesada publishes
        # through package_info.buildenv_info belong to a HOST requirement and
        # are not guaranteed to be part of the test_package's conanbuild env.
        dep = self.dependencies["libncursesada"]
        adainclude = os.path.join(dep.package_folder, "share", "ada", "adainclude")
        adalib = os.path.join(dep.package_folder, "lib", "ada", "adalib")
        # ncurses flags come from the cpp_info instead of pkg-config:
        # PkgConfigDeps only writes the .pc files and does NOT extend
        # PKG_CONFIG_PATH (E468), so `pkg-config ncursesw` falls back to the
        # HOST ncursesw.pc and yields "-lncursesw -ltinfo" with no -L, which
        # then fails with `ld: cannot find -lncursesw / -ltinfo`.
        ncurses = self.dependencies.get("ncurses")
        nclibdir = ""
        nclibs = ""
        if ncurses is not None:
            dirs = [d for d in ncurses.cpp_info.libdirs if d]
            nclibdir = dirs[0] if dirs else ""
            nclibs = " ".join("-l" + lib for lib in ncurses.cpp_info.libs)
        script = os.path.join(self.source_folder, "test.sh")
        self.run('bash "{}" "{}" "{}" "{}" "{}"'.format(
            script, adainclude, adalib, nclibdir, nclibs),
                 env="conanbuild")

    def _consumer(self):
        return os.path.join(self.source_folder, "ncursesada-consumer")

    def test(self):
        if not can_run(self):
            self.output.warning("Consumer cannot run on this host; build-only check.")
            return
        exe = self._consumer()
        if not os.path.isfile(exe):
            raise ConanInvalidConfiguration("Ada consumer was not built")
        if str(self.settings.os) == "OHOS":
            self._sign_executable(exe)
        cmd = 'python3 "{}" "{}"'.format(
            os.path.join(self.source_folder, "run_pty.py"), exe)
        self.run(cmd, env="conanbuild", cwd=self.source_folder)

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

