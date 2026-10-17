#!/usr/bin/env python3
"""Test package for achilles/3 — consumer-side verification of the installed
application.

Upstream ships no test suite at all (see MANIFEST.yml for the counting
evidence), so these are the complemented consumer tests required by the
delivery spec.  They genuinely exercise the installed ``bin/achilles`` and the
GL/GLU/SDL stack it renders through (R34): a CLI test, a real headless
simulation run, and a C++ probe that drives the OSMesa/GLU/SDL path itself.
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment

# The simulator needs the offscreen GL path plus a windowless SDL video driver.
_RUN_ENV = {
    "SDL_VIDEODRIVER": "dummy",
    "SDL_AUDIODRIVER": "dummy",
}


class AchillesTestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # VirtualRunEnv is required: the packaged binary has no RUNPATH baked for
    # the consumer's cache layout, so the run environment must supply the
    # library search path (same requirement as the glu test package).
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # The application links these directly; the probe also needs them.
        # mesa is required directly (not only transitively through glu) so its
        # GL/OSMesa headers are exported to this consumer.
        self.requires("glu/9.0.3")
        self.requires("mesa/24.3.4.1")
        self.requires("sdl/1.2.15")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.warning("target platform cannot run — skipping execution tests")
            return

        dep = self.dependencies[self.tested_reference_str]
        bindir = os.path.join(dep.package_folder, "bin")
        achilles = os.path.join(bindir, "achilles")
        if not os.path.isfile(achilles):
            raise ConanException(f"installed command missing: {achilles}")

        env = Environment()
        for key, value in _RUN_ENV.items():
            env.define(key, value)

        with env.vars(self).apply():
            # ── 1. CLI interface: -v / -h / --version / --help ──
            script = os.path.join(self.recipe_folder, "test_cli.py")
            self.run(
                f'"{sys.executable}" "{script}" "{bindir}"',
                env="conanrun",
            )

            # ── 2. Real headless simulation run (main loop + OSMesa draw) ──
            sim = os.path.join(self.recipe_folder, "test_simulation.py")
            self.run(
                f'"{sys.executable}" "{sim}" "{achilles}"',
                env="conanrun",
            )

            # ── 3. C++ consumer probe of the GL/GLU/SDL stack ──
            probe = os.path.join(self.cpp.build.bindirs[0], "test_gl_stack")
            self.run(probe, env="conanrun")
