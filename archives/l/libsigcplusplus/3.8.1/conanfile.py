#!/usr/bin/env python3
"""Conan recipe for libsigcplusplus 3.8.1 — libsigc++ 3 (sigc++-3.0 ABI).

Package "libsigcplusplus" carries upstream libsigc++ 3.8.1 (typesafe
callback system for standard C++).  It is the 3.x line of libsigc++ and
coexists with the archived 2.x packages (libsigc/2.x, libsigc++/2.10.8,
libsigc-2/2.12.2) in this repository — different package name, different
major ABI line (kitemmodels5/KF6 style precedent).

The built artefacts keep upstream names: shared/static library
libsigc-3.0, headers under include/sigc++-3.0, generated config header
under lib/sigc++-3.0/include, pkg-config module sigc++-3.0.

Upstream ships Autotools, Meson and CMake build files in parallel; this
recipe uses Meson (same choice as the archived libsigc-2/2.12.2 recipe,
matching the upstream reference build system).

Upstream ships 42 unit tests (tests/test_*.cc registered in
tests/meson.build); they are built and run via meson.test() whenever the
target can run binaries.
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run, check_min_cppstd
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class _PosixPrefixMeson(Meson):
    @property
    def _prefix(self):
        # Conan derives C:/ from the Windows build machine, but Meson
        # validates this value for the OHOS target. Installation remains
        # isolated by Meson's --destdir argument in Meson.install().
        return "/"


class LibsigcplusplusConan(ConanFile):
    name = "libsigcplusplus"
    version = "3.8.1"
    description = "libsigc++ implements a typesafe callback system (signals/slots) for standard C++"
    license = "LGPL-3.0-or-later"
    homepage = "https://github.com/libsigcplusplus/libsigcplusplus"
    url = "https://github.com/libsigcplusplus/libsigcplusplus"
    topics = ("signal", "slot", "callback", "libsigc++", "sigc++-3.0", "c++")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libsigcplusplus supports Linux and OHOS targets, got {self.settings.os}"
            )
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        check_min_cppstd(self, 17)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        if str(self.settings.os) == "OHOS":
            # The OHOS clang wrapper (usr/local/bin style) prepends
            # -Wl,--code-sign to every driver invocation.  Meson's
            # compile-only probes add -Werror=unused-command-line-argument,
            # so the code-sign flag kills the gcc/msvc
            # _template_specialization_operator_overload checks and leaves
            # SIGC_TEMPLATE_SPECIALIZATION_OPERATOR_OVERLOAD undefined
            # (sun_forte_workaround fallout in base.h/adaptor_trait.h).
            # -Qunused-arguments suppresses that driver error and is a no-op
            # for SDK clang without cfg injection.
            tc.extra_cflags.append("-Qunused-arguments")
            tc.extra_cxxflags.append("-Qunused-arguments")
        tc.project_options["default_library"] = (
            "shared" if self.options.shared else "static"
        )
        # Release tarball has no .git directory, so maintainer-mode's
        # default 'if-git-build' never activates; pin it to false anyway.
        tc.project_options["maintainer-mode"] = "false"
        tc.project_options["build-documentation"] = "false"
        tc.project_options["build-manual"] = "false"
        tc.project_options["validation"] = "false"
        tc.project_options["build-pdf"] = "false"
        tc.project_options["build-examples"] = "false"
        tc.project_options["build-tests"] = "true"
        tc.project_options["benchmark"] = "false"
        tc.project_options["wrap_mode"] = "nodownload"
        tc.generate()
        self._inject_meson_archiver()

    def _inject_meson_archiver(self):
        # Meson's machine file lacks ar/ranlib on the OHOS SDK; derive them
        # from tools.build:compiler_executables (same pattern as libsigc-2).
        executables = self.conf.get(
            "tools.build:compiler_executables",
            default={},
            check_type=dict,
        ) or {}
        ar = executables.get("ar")
        ranlib = executables.get("ranlib")
        if not ar:
            compiler = executables.get("cpp") or executables.get("c") or ""
            bindir = os.path.dirname(compiler)
            suffix = ".exe" if os.name == "nt" else ""
            candidate = os.path.join(bindir, "llvm-ar" + suffix) if bindir else ""
            if candidate and os.path.isfile(candidate):
                ar = candidate
                candidate_ranlib = os.path.join(bindir, "llvm-ranlib" + suffix)
                if os.path.isfile(candidate_ranlib):
                    ranlib = candidate_ranlib

        machine_file = next(
            (
                os.path.join(self.generators_folder, filename)
                for filename in (
                    "conan_meson_cross.ini",
                    "conan_meson_native.ini",
                )
                if os.path.isfile(os.path.join(self.generators_folder, filename))
            ),
            None,
        )
        if not ar or not machine_file:
            return
        with open(machine_file, encoding="utf-8") as handle:
            content = handle.read()
        if "\nar =" in content or "[binaries]" not in content:
            return
        binaries = "[binaries]\nar = '{}'\n".format(ar.replace("\\", "/"))
        if ranlib:
            binaries += "ranlib = '{}'\n".format(ranlib.replace("\\", "/"))
        with open(machine_file, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content.replace("[binaries]\n", binaries, 1))

    def build(self):
        meson = _PosixPrefixMeson(self)
        meson.configure()
        meson.build()
        if can_run(self):
            meson.test()
        else:
            self.output.info(
                "cross-building: 42 upstream tests compiled but cannot run"
            )

    def package(self):
        _PosixPrefixMeson(self).install()
        self._materialize_shared_library_aliases()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def _materialize_shared_library_aliases(self):
        if not self.options.shared:
            return
        libdir = os.path.join(self.package_folder, "lib")
        versioned = os.path.join(libdir, "libsigc-3.0.so.0.0.0")
        if not os.path.isfile(versioned):
            raise RuntimeError(f"Missing installed shared library: {versioned}")
        for alias in ("libsigc-3.0.so.0", "libsigc-3.0.so"):
            destination = os.path.join(libdir, alias)
            if not os.path.exists(destination):
                shutil.copy2(versioned, destination)

    def package_info(self):
        self.cpp_info.libs = ["sigc-3.0"]
        # Headers: include/sigc++-3.0/sigc++/*.h plus the generated
        # sigc++config.h under lib/sigc++-3.0/include (upstream layout).
        self.cpp_info.includedirs = [
            os.path.join("include", "sigc++-3.0"),
            os.path.join("lib", "sigc++-3.0", "include"),
        ]
        self.cpp_info.set_property("cmake_file_name", "libsigcplusplus")
        self.cpp_info.set_property("cmake_target_name", "libsigcplusplus::libsigcplusplus")
        self.cpp_info.set_property("pkg_config_name", "sigc++-3.0")
