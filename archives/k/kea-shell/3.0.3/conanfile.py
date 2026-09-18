#!/usr/bin/env python3
"""Conan recipe — kea-shell 3.0.3 (ISC Kea REST client).

``kea-shell`` is the text client ISC Kea ships for the REST interface of its
servers; its sources live in ``src/bin/shell`` of the Kea 3.0.3 release tarball.
The target is a **Python 3 script tool**: the upstream Meson target declares no
compilation and no ``dependencies:``/``link_with:`` at all.  Its sole build
action is ``configure_file()`` -- expanding ``kea-shell.in`` into the
``kea-shell`` script (interpreter, version, module directory) and copying the
two helper modules ``kea_conn.py`` / ``kea_connector3.py``.

The recipe therefore stops after the upstream configure phase, which is the step
that produces the artefact, and packages the generated script together with its
modules.  There is nothing to compile and nothing to link for this package.

Kea builds as a single Meson project, so ``meson setup`` still evaluates the
project-level dependency gate in the top-level ``meson.build`` (boost is
required without a fallback, openssl is the mandatory default crypto back-end,
log4cplus comes from a wrap fallback).  Those dependencies are declared here
because the upstream configure step cannot run without them; they are consumed
by the configure probes only and are not linked into the shipped artefact, so
``package_info()`` does not propagate them to consumers.

Platform adaptation lives in ``patches/``: the Meson system-name normalization
(OpenHarmony is reported as ``harmonyos``, which Kea's platform branch does not
recognize) and the interpreter line of the generated script (upstream embeds the
absolute path of the build machine's ``python3``).
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class KeaShellConan(ConanFile):
    name = "kea-shell"
    version = "3.0.3"
    description = ("ISC Kea 3.0.3 REST client (kea-shell) for the Kea control "
                   "channels over HTTP/HTTPS")
    license = "MPL-2.0"
    homepage = "https://www.isc.org/kea/"
    url = "https://gitlab.isc.org/isc-projects/kea"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"
    options = {"tests": [True, False]}
    default_options = {"tests": True}

    # Upstream Meson test target covering this package: the Python unit test of
    # the two modules kea-shell ships (src/bin/shell/tests/meson.build, suite
    # 'python-tests').  The twelve 'shell-tests' process scripts drive kea-shell
    # against the Kea server binaries (kea-ctrl-agent / kea-d2 / kea-dhcp4 /
    # kea-dhcp6); those binaries are separate targets of the same Meson project
    # and are not part of this package, so their suite is not run from this
    # recipe.
    upstream_test_targets = ("shell_unittest.py",)

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # Project-level configure gate of the Kea Meson build.  boost must be
        # pinned: the 1.90/1.91 packages miss boost/interprocess,
        # boost/circular_buffer and other headers that Kea probes for with
        # required: true.
        self.requires("boost/1.85.0")
        self.requires("log4cplus/2.2.0.1")
        self.requires("openssl/3.5.8.1")

    def build_requirements(self):
        # Kea needs meson >= 1.10: the boost packages ship no libboost_system,
        # which only resolves through the header-only module fallback added in
        # meson 1.10.
        self.tool_requires("meson/1.11.0")
        if self.options.tests:
            self.test_requires("gtest/1.17.0.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        tc.project_options["tests"] = "enabled" if self.options.tests else "disabled"
        # Optional back-ends: no Conan dependency is provided for them, disable
        # them explicitly so the configure does not depend on host-side probes.
        tc.project_options["crypto"] = "openssl"
        tc.project_options["mysql"] = "disabled"
        tc.project_options["postgresql"] = "disabled"
        tc.project_options["netconf"] = "disabled"
        tc.project_options["krb5"] = "disabled"
        # The OHOS musl <pthread.h> does not declare pthread_setcancelstate(),
        # which boost/core/detail/sp_thread_sleep.hpp calls (used through
        # Boost.Asio).  The upstream escape hatch keeps the boost probes
        # compiling.
        tc.extra_cxxflags.append("-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE")
        # Meson probes the static linker in project(); the CI workers do not
        # expose llvm-ar/llvm-ranlib on PATH, so derive them from the configured
        # compiler location.
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c") if compilers else None
        if cc:
            tool_dir = os.path.dirname(cc)
            tc.binaries["ar"] = os.path.join(tool_dir, "llvm-ar")
            tc.binaries["ranlib"] = os.path.join(tool_dir, "llvm-ranlib")
        tc.generate()
        # Meson runs compile-and-run feature probes during configure (log4cplus,
        # openssl, boost), so the shared dependencies must be resolvable at run
        # time while configuring.
        env = Environment()
        for dep in self.dependencies.values():
            for libdir in dep.cpp_info.libdirs:
                env.append_path("LD_LIBRARY_PATH", libdir)
        env.vars(self).save_script("conanbuildenv-kea-runtime")

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        # Kea's Meson project is configured as a whole.  The shell target has no
        # compilation step: configure_file() already writes the kea-shell script
        # and its modules into the build tree during this call.
        meson.configure()
        if self.options.tests:
            self.run('meson test -v -C "{}" {}'.format(
                self.build_folder, " ".join(self.upstream_test_targets)))

    def package(self):
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        # kea-shell and its two modules are installed together: the generated
        # script appends the build-time PKGPYTHONDIR to sys.path, which is not a
        # location a Conan package can own, so the modules sit next to the
        # script where CPython's script-directory sys.path entry finds them.
        shell_dir = os.path.join(self.build_folder, "src", "bin", "shell")
        bin_dir = os.path.join(self.package_folder, "bin")
        for name in ("kea-shell", "kea_conn.py", "kea_connector3.py"):
            copy(self, name, src=shell_dir, dst=bin_dir)
        os.chmod(os.path.join(bin_dir, "kea-shell"), 0o755)

    def package_info(self):
        # Command-line tool: nothing to link or include, only PATH for the
        # binary and for the helper modules it imports.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        # The tool imports the two modules from its own directory, which would
        # otherwise make CPython cache bytecode inside the package folder.
        self.runenv_info.define("PYTHONDONTWRITEBYTECODE", "1")
