#!/usr/bin/env python3
"""Conan test_package — lablgtk3 3.1.5

Consumer-view verification on OHOS aarch64 (no native display backend).
The actual probes live in test.sh (driven with an explicit interpreter,
OHOS hmmac refuses direct shebang execution — findlib/1.9.8 pattern):

  T0  package structure: findlib META / .cma / .cmxa / stubs .so / C
      headers, plus the vendored cairo2 and camlp-streams packages
  T1  ocamlfind resolution of lablgtk3 and its vendored dependencies
  T2  OHOS no-display API probe (native ELF): links the lablgtk3 stubs,
      vendored cairo2 and glib, then RUNS pure-glib UTF-8/charset calls —
      no gtk_init() and no display server required (E463/E471 display-test
      classification; OHOS-specific test for the platform adaptation)
  T3  upstream run-test parity: compile a GTK window consumer
      (build only — running it needs a display server, which OHOS lacks)

All OCaml invocations pin OCAMLLIB / OCAMLFIND_CONF / OCAMLPATH explicitly
(no ambient device state).  Everything executes as native ELF because the
OHOS security policy refuses shebang/bytecode executables.
"""
import os

from conan import ConanFile


class Lablgtk3TestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        # toolchain to compile the probes against the installed findlib tree
        self.tool_requires("ocaml/4.14.1.1.4")
        self.tool_requires("findlib/1.9.8")

    def test(self):
        test_sh = os.path.join(self.source_folder, "test.sh")
        pkg_lib = os.path.join(self.dependencies["lablgtk3"].package_folder, "lib")

        ocaml_pkg = self.dependencies.build["ocaml"].package_folder
        ocaml_bin = os.path.join(ocaml_pkg, "bin")
        ocaml_stdlib = os.path.join(ocaml_pkg, "lib", "ocaml")
        findlib_pkg = self.dependencies.build["findlib"].package_folder
        findlib_bin = os.path.join(findlib_pkg, "bin")
        findlib_sitelib = os.path.join(findlib_pkg, "lib", "ocaml")

        self.run(
            '/bin/sh "%s" "%s" "%s" "%s" "%s" "%s" "%s"'
            % (test_sh, pkg_lib, ocaml_bin, ocaml_stdlib,
               findlib_bin, findlib_sitelib, self.build_folder),
            env="conanrun",
        )
