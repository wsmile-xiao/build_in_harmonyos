#!/usr/bin/env python3
"""test_package consumer for vtk 9.3.0 — validates the VTK package on OHOS aarch64."""

import os
import shlex
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.build import cross_building
from conan.tools.env import VirtualRunEnv

from vtk_runtime import create_runtime, runtime_directory, stage_runtime


def _find_working_ninja():
    """First ninja on PATH that actually runs.

    A stale/broken ninja earlier in PATH (device-image copy without the
    exec bit, device-verified 2026-09-05) shadows a good one; CMake's
    find_program would pick the broken one and fail at project() with
    "permission denied".  Mirror of the main recipe's probe.
    """
    seen = set()
    for d in os.environ.get("PATH", "").split(os.pathsep):
        if not d:
            continue
        cand = os.path.join(d, "ninja")
        if cand in seen:
            continue
        seen.add(cand)
        if not os.path.isfile(cand):
            continue
        try:
            if subprocess.run([cand, "--version"], capture_output=True,
                              timeout=30).returncode == 0:
                return cand
        except Exception:
            continue
    return None


class VTKTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # Same generators as the former `generators` attribute, but we need
        # an explicit generate() to pin a working ninja via
        # CMAKE_MAKE_PROGRAM (the device's PATH holds a broken ninja that
        # would otherwise fail the test_package configure step).
        tc = CMakeToolchain(self)
        vtk = self.dependencies["vtk"]
        tc.variables["VTK_TEST_RENDERING"] = bool(vtk.options.rendering)
        tc.variables["VTK_TEST_EGL"] = self.settings.os == "OHOS"
        if self.settings.os == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_CROSSCOMPILING"] = "FALSE"
            if vtk.options.shared:
                tc.cache_variables["VTK_TEST_RUNTIME"] = str(create_runtime(self))
                tc.extra_exelinkflags.append("-Wl,--disable-new-dtags")
        generator_conf = self.conf.get("tools.cmake.cmaketoolchain:generator",
                                       default="") or ""
        if generator_conf == "Ninja":
            ninja = _find_working_ninja()
            if ninja:
                tc.cache_variables["CMAKE_MAKE_PROGRAM"] = ninja
            else:
                self.output.warning("Ninja generator requested but no "
                                    "working ninja found on PATH")
        tc.generate()
        CMakeDeps(self).generate()
        run_env = VirtualRunEnv(self)
        if self.settings.os == "OHOS" and vtk.options.shared:
            environment = run_env.environment()
            # The package-cache libraries are intentionally untouched. On
            # HiShell's shared volume they cannot supply executable mappings.
            # Keep all dependency environment entries but search signed copies
            # before the automatic Conan package-cache LD_LIBRARY_PATH entry.
            environment.prepend_path("LD_LIBRARY_PATH", str(runtime_directory(self)))
            environment.vars(self, scope="run").save_script("vtk_test_runtime")
        else:
            run_env.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info("Cross-built consumer requires execution on the target device")
            return
        vtk = self.dependencies["vtk"]
        if self.settings.os == "OHOS" and vtk.options.shared:
            stage_runtime(self, os.path.join(vtk.package_folder, "lib"))
        run_env = ("vtk_test_runtime" if self.settings.os == "OHOS" and vtk.options.shared
                   else "conanrun")
        programs = ["test_vtk"]
        if vtk.options.rendering:
            programs.extend(["test_vtk_render", "test_vtk_viewports"])
        quote = subprocess.list2cmdline if os.name == "nt" else shlex.join
        for program in programs:
            binary = os.path.join(self.cpp.build.bindirs[0], program)
            self.output.info("[STEP] run %s success path" % program)
            self.run(quote([binary]), env=run_env)
            if program == "test_vtk_viewports":
                continue
            self.output.info("[STEP] run %s negative assertion" % program)
            ret = self.run(quote([binary, "--expect-fail"]),
                           env=run_env, ignore_errors=True)
            if ret != 1:
                raise ConanException("%s negative assertion returned %s; expected 1" %
                                     (program, ret))
            self.output.info("[PASS] %s positive=0 and negative=1" % program)
