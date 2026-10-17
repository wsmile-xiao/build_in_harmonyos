#!/usr/bin/env python3
"""Consumer test for libflorist (FLORIST / POSIX.5 Ada bindings).

What it does
------------
Compiles and runs `src/florist_consumer.adb`, an Ada program that really calls
the packaged bindings (Get_Process_ID/Image, Is_Environment_Variable,
Environment_Value_Of, Is_Directory) and asserts their results, then links it
against the packaged `libflorist.a` with the GNAT toolchain.

Why the paths are resolved explicitly
-------------------------------------
libflorist distributes Ada *specifications* plus the static archive, so a
consumer needs:

  * the flat `<package>/floristlib` directory on the Ada source search path
    (-I) and on the linker search path (-aL / -lflorist), and
  * the GNAT runtime search paths (ADA_INCLUDE_PATH / ADA_OBJECTS_PATH) and
    GCC_EXEC_PREFIX exported, otherwise gnatmake aborts with
    "fatal error, run-time library not installed correctly".

OHOS additionally refuses to exec an unsigned ELF, so the built consumer is
signed with the SDK tools before it is run.
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.layout import basic_layout


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        # Same OHOS/armv8-only Ada toolchain as the package under test.
        self.tool_requires("gcc-ada/9.5.0")
        self.tool_requires("binutils/2.46.0")

    def layout(self):
        basic_layout(self)

    # ------------------------------------------------------------------ tools
    def _dep_bindir(self, name):
        dep = self.dependencies.build.get(name)
        if dep is None or not dep.package_folder:
            return ""
        for candidate in list(dep.cpp_info.bindirs or []) + ["bin"]:
            path = os.path.join(dep.package_folder, candidate)
            if os.path.isdir(path):
                return path
        return ""

    def _tool(self, name):
        bindir = self._dep_bindir("gcc-ada")
        path = os.path.join(bindir, name) if bindir else ""
        if path and os.path.isfile(path):
            return path
        return shutil.which(name) or name

    def _ada_root(self):
        bindir = self._dep_bindir("gcc-ada")
        if not bindir:
            return ""
        folder = os.path.dirname(bindir)
        import glob
        for root in sorted(glob.glob(os.path.join(folder, "lib", "gcc", "*", "*"))):
            if os.path.isdir(os.path.join(root, "adainclude")):
                return root
        return ""

    def _find_ohos_tool(self, name):
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        compiler_dir = os.path.dirname(compilers.get("cpp", ""))
        candidates = [
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        ]
        return next((p for p in candidates if p and os.path.isfile(p)), "")

    # ---------------------------------------------------------------- generate
    def generate(self):
        VirtualBuildEnv(self).generate()
        env = Environment()
        for bindir in (self._dep_bindir("binutils"), "/data/service/hnp/bin",
                       self._dep_bindir("gcc-ada")):
            if bindir:
                env.prepend_path("PATH", bindir)
        ada_root = self._ada_root()
        if ada_root:
            env.define("ADA_INCLUDE_PATH", os.path.join(ada_root, "adainclude"))
            env.define("ADA_OBJECTS_PATH", os.path.join(ada_root, "adalib"))
        bindir = self._dep_bindir("gcc-ada")
        if bindir:
            env.define("GCC_EXEC_PREFIX",
                       os.path.join(os.path.dirname(bindir), "lib", "gcc") + os.sep)
        env.define("CONFIG_SHELL", "/bin/sh")
        env.define("SHELL", "/bin/sh")
        # HMDFS: never write scratch files into the default (read-only) tmpdir.
        tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp, exist_ok=True)
        for name in ("TMPDIR", "TMP", "TEMP"):
            env.define(name, tmp)
        env.vars(self).save_script("florist_consumer_env")

    def _env(self):
        return ["conanbuild", "florist_consumer_env"]

    def _consumer(self):
        return os.path.join(self.build_folder, "florist_consumer")

    # ------------------------------------------------------------------- build
    def build(self):
        dep = self.dependencies[self.tested_reference_str]
        # The package installs Ada specs + libflorist.a into a flat directory
        # (see package_info(): includedirs/libdirs = ["floristlib"]).
        florist_dir = os.path.join(dep.package_folder, "floristlib")
        if not os.path.isdir(florist_dir):
            raise ConanInvalidConfiguration(
                "packaged floristlib directory not found: {}".format(florist_dir))
        if not os.path.isfile(os.path.join(florist_dir, "libflorist.a")):
            raise ConanInvalidConfiguration(
                "libflorist.a is missing from {}".format(florist_dir))

        ada_root = self._ada_root()
        ada_include = os.path.join(ada_root, "adainclude") if ada_root else ""
        ada_objects = os.path.join(ada_root, "adalib") if ada_root else ""

        # The build is driven by test.sh: the CI L0c gate accepts a test source
        # only for the extensions .c/.cpp/.cc/.cxx/.sh/.py, so an Ada-only
        # test_package needs a shell entry point (same approach as the
        # libncursesada recipe).
        # $5 is the work dir for compiler intermediates: gnatmake writes .o/.ali
        # next to the compiled unit, so it must be a path inside the Conan build
        # folder, never the recipe source tree.
        work_dir = os.path.join(self.build_folder, "consumer-build")
        self.run(
            'bash "{}" "{}" "{}" "{}" "{}" "{}"'.format(
                os.path.join(self.source_folder, "test.sh"),
                florist_dir, ada_include, ada_objects, self._consumer(),
                work_dir),
            env=self._env())
        if not os.path.isfile(self._consumer()):
            raise ConanInvalidConfiguration(
                "consumer program was not produced by test.sh")

    # -------------------------------------------------------------------- test
    def test(self):
        if not can_run(self):
            self.output.warning("Consumer cannot run on this host; build-only check.")
            return
        exe = self._consumer()
        if str(self.settings.os) == "OHOS":
            self._sign_executable(exe)
        self.run(shlex.quote(exe), env=self._env())

    def _sign_executable(self, executable):
        """OHOS refuses to exec an unsigned ELF (E489/E517)."""
        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanInvalidConfiguration(
                "OHOS consumer execution requires llvm-objcopy and "
                "binary-sign-tool")
        original_mode = os.stat(executable).st_mode
        temporary = executable + ".signing"
        try:
            shutil.copy2(executable, temporary)
            self.run('"{}" --remove-section .codesign "{}"'.format(
                objcopy, temporary))
            self.run('"{}" sign -inFile "{}" -outFile "{}" -selfSign 1'.format(
                signer, temporary, temporary))
            os.chmod(temporary, original_mode)
            os.replace(temporary, executable)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)
