#!/usr/bin/env python3
"""Conan test_package — riemann-c-client 1.10.4.

Conan L1 official test: CI runs this automatically via `conan create`.
Consumer-view verification: header discovery, static linking against
libriemann-client (+ transitive protobuf-c), and a protobuf serialization
smoke through the public API.  See MANIFEST.yml for the declared tests.
"""
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


class RiemannCClientTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        import os

        from conan.tools.env import Environment

        # The registry gnutls package declares shared=False yet ships only
        # .so files, so VirtualRunEnv omits it (and any similarly mislabelled
        # package) from LD_LIBRARY_PATH and every gnutls_* relocation fails
        # at load time.  Add the lib dir of every host dependency that really
        # ships shared objects — mechanism-based, not name-based.
        extra = Environment()
        for dep in self.dependencies.host.values():
            libdir = os.path.join(dep.package_folder, "lib")
            if not os.path.isdir(libdir):
                continue
            if any(".so" in entry for entry in os.listdir(libdir)):
                extra.prepend_path("LD_LIBRARY_PATH", libdir)
        extra.vars(self).save_script("extrasharedlibs")

        # ctest under the run environment: consumer binary links the
        # registry's shared gnutls/json-c (env list = conanrun + our fixup).
        self.run(
            "ctest --output-on-failure",
            cwd=self.build_folder,
            env=["conanrun", "extrasharedlibs"],
        )
        # CLI smoke on the target: `riemann-client --help` must exit 0
        # (upstream main() returns EXIT_SUCCESS for --help/-?/--version).
        # NOTE: in a test_package context `self.package_folder` points at the
        # test_package folder itself — the tested package lives in the
        # dependency graph, otherwise this block silently never runs.
        tested = None
        for dep in self.dependencies.host.values():
            if dep.ref.name == "riemann-c-client":
                tested = dep
                break
        if tested is None:
            raise ConanException(
                "CLI smoke not executed: tested package not in dependencies"
            )
        cli = os.path.join(tested.package_folder, "bin", "riemann-client")
        if not os.path.isfile(cli):
            raise ConanException("CLI smoke not executed: {} missing".format(cli))
        self.run(f'"{cli}" --help', env=["conanrun", "extrasharedlibs"])
        self.run(f'"{cli}" --version', env=["conanrun", "extrasharedlibs"])
