#!/usr/bin/env python3
"""Conan test_package for midish 1.4.0 on HarmonyOS PC.

Verifies the installed package from a consumer point of view:
  - the installed `midish` interpreter really works: its version is reported,
    the packaged example song (share/examples/midish/sample.msh) is loaded, the
    song is saved back to a .msh file and exported as a Standard MIDI File
    (the exported file must start with the SMF "MThd" header), and the saved
    song is loaded again;
  - test_package/ohos_test.cpp is the HarmonyOS-specific test: a pipe whose
    writer closes must make the installed `midish -b` terminate (the
    POLLHUP-only end-of-file behaviour of this platform), plus the installed
    layout/ELF checks.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class MidishTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        env = Environment()
        if self.settings.os == "OHOS":
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        with env.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build()

    def _run_script(self, midish, workdir, script, log_name):
        script_path = os.path.join(workdir, log_name + ".mshcmd")
        log_path = os.path.join(workdir, log_name + ".log")
        with open(script_path, "w") as handle:
            handle.write(script)
        self.run(
            '"{}" -b < "{}" > "{}" 2>&1'.format(midish, script_path, log_path)
        )
        with open(log_path) as handle:
            return handle.read()

    def test(self):
        tested = self.dependencies.get(self.tested_reference_str.split("/")[0])
        prefix = tested.package_folder
        midish = os.path.join(prefix, "bin", "midish")
        sample = os.path.join(prefix, "share", "examples", "midish", "sample.msh")
        workdir = os.path.join(self.build_folder, "run")
        os.makedirs(workdir, exist_ok=True)
        saved = os.path.join(workdir, "song.msh")
        exported = os.path.join(workdir, "song.mid")

        env = Environment()
        if self.settings.os == "OHOS":
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        with env.vars(self).apply():
            # --- consumer workflow: load package sample, save, export SMF ---
            script = 'version\nload "{sample}"\nsave "{saved}"\nexport "{exported}"\n'.format(
                sample=sample, saved=saved, exported=exported
            )
            output = self._run_script(midish, workdir, script, "export")
            if "midish 1.4.0" not in output:
                raise ConanException(
                    "installed midish did not report its version:\n" + output
                )
            for path in (saved, exported):
                if not os.path.isfile(path) or os.path.getsize(path) == 0:
                    raise ConanException("missing/empty output file " + path)
            with open(exported, "rb") as handle:
                header = handle.read(4)
            if header != b"MThd":
                raise ConanException(
                    "exported file is not a Standard MIDI File (header={!r})".format(
                        header
                    )
                )
            self.output.info(
                "consumer workflow ok: version + load sample.msh + save .msh + export SMF (MThd) "
                "(exported {} bytes)".format(os.path.getsize(exported))
            )

            # --- reload the saved song -------------------------------------
            reload_script = 'load "{saved}"\nprint "reloaded"\n'.format(saved=saved)
            reload_output = self._run_script(
                midish, workdir, reload_script, "reload"
            )
            if "reloaded" not in reload_output:
                raise ConanException(
                    "saved song could not be loaded again:\n" + reload_output
                )
            self.output.info("consumer workflow ok: saved .msh reloaded")

            # --- HarmonyOS-specific test + registered ctest entries ---------
            env2 = Environment()
            env2.define("MIDISH_PREFIX", prefix)
            if self.settings.os == "OHOS":
                env2.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
            with env2.vars(self).apply():
                cmake = CMake(self)
                cmake.test()
                bindir = self.cpp.build.bindirs[0]
                self.run(
                    os.path.join(bindir, "test_midish_ohos"), env="conanrun"
                )
