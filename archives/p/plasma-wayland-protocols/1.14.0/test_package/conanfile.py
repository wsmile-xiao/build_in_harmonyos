#!/usr/bin/env python3
"""test_package for plasma-wayland-protocols — consumer-side verification.

Three layers of real consumption of the installed artifacts (R34):

  1. build(): a genuine CMake consumer project runs
     find_package(PlasmaWaylandProtocols 1.9.0 CONFIG REQUIRED) — exactly what
     kwayland5/5.116.0 does — and fails the configure step if
     PLASMA_WAYLAND_PROTOCOLS_DIR is unset/empty or if any of the 22 protocol
     XML files kwayland5 needs is absent.

     The same project also builds `plasma_e2e` (e2e/plasma_e2e.c), whose protocol
     bindings are generated at build time from the XML this package installs
     (e2e/gen_protocol.py).  That generator is the *only* place the protocol is
     described: a missing or malformed XML, or a message it cannot translate
     exactly, fails the build rather than silently producing empty code.

  2. test() — layer A: resolves PLASMA_WAYLAND_PROTOCOLS_DIR by evaluating the
     native PlasmaWaylandProtocolsConfig.cmake with `cmake -P`, then validates
     every protocol XML (non-empty, well-formed, <protocol name=...> with
     <interface name=... version=...> children) and prints a machine-readable
     tally `assertions=N failures=0`, exiting non-zero on any failure.

  3. test() — layer B (rule 12, 鸿蒙特有测试): runs the compiled end-to-end
     consumer flow, i.e. the generated bindings really speaking the protocol over
     libwayland on an AF_UNIX socketpair (server: wl_display_create +
     wl_client_create + wl_global_create; client: wl_display_connect_to_fd +
     registry + bind + fetchStates; server handler replies through the generated
     event sender; payload compared unchanged; destructor request verified too).
     The binary itself prints `assertions=N failures=M` and exits non-zero on any
     failed stage, so ctest records a real failure.

The wayland library is a *test-only* requirement: the package under test has no
runtime dependency on it (it is a data-only package), and the flow needs
libwayland-client/server merely as the transport that makes the generated
protocol code demonstrably work end to end.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, CMakeDeps, cmake_layout
from conan.tools.env import Environment


class PlasmaWaylandProtocolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Test-only: the end-to-end flow speaks the generated protocol over a
        # real libwayland client/server.  libwayland-client and -server are taken
        # by explicit path in CMakeLists.txt because the other libraries the same
        # package ships (libwayland-cursor/-egl) are ELFs the OHOS loader rejects.
        self.requires("wayland/1.22.0", transitive_headers=True)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        tc.user_presets_path = False
        # The flow needs the interpreter that will run gen_protocol.py and the
        # wayland include/lib directories; hand them to CMake explicitly so the
        # build does not depend on how the consumer environment is laid out.
        tc.cache_variables["PWP_PYTHON"] = self._python()
        wayland = self.dependencies["wayland"]
        tc.cache_variables["PWP_WAYLAND_INCLUDE_DIR"] = os.path.join(
            wayland.package_folder, "include")
        tc.cache_variables["PWP_WAYLAND_LIB_DIR"] = os.path.join(
            wayland.package_folder, "lib")
        tc.generate()

    @staticmethod
    def _python():
        import shutil
        import sys
        return shutil.which("python3") or shutil.which("python") or sys.executable

    def _runtime_env(self):
        """LD_LIBRARY_PATH covering the tested package and every dependency.

        libwayland-client/server need their own lib dir; the tested package is
        data-only but is included so the XML path is resolvable from the binary's
        working directory where relevant.
        """
        env = Environment()
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                lib_dir = os.path.join(dep.package_folder, "lib")
                if os.path.isdir(lib_dir):
                    env.prepend_path("LD_LIBRARY_PATH", lib_dir)
        # /system/lib64 must stay reachable: the OHOS SDK's libc++ lives there.
        if os.path.isdir("/system/lib64"):
            env.append_path("LD_LIBRARY_PATH", "/system/lib64")
        return env

    def build(self):
        # Runs find_package(PlasmaWaylandProtocols CONFIG REQUIRED) + the
        # protocol completeness assertions at CMake configure time, then compiles
        # the end-to-end flow (whose protocol bindings are generated from the XML
        # this package installs).
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        pkg_folder = self.dependencies["plasma-wayland-protocols"].package_folder

        # Layer A: XML inventory + containment, machine-readable tally.
        script = os.path.join(self.source_folder, "test_protocols.sh")
        self.run(f'bash "{script}" "{pkg_folder}"', env="conanrun")

        if not can_run(self):
            self.output.info("cross-build: skipping the end-to-end execution layer")
            return

        # Layer B: the compiled flow, run through ctest so a failed stage is a
        # real test failure.  Passing the XML explicitly makes the binary check
        # that the file installed in the package is the one its bindings were
        # generated from.
        env = self._runtime_env()
        with env.vars(self).apply():
            self.run(
                'ctest --test-dir "{0}" --output-on-failure'.format(self.build_folder)
            )
