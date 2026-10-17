#!/usr/bin/env python3
"""Conan test_package — tradcpp 0.5.3 (application).

Runs the *installed* binary on a small traditional-C input and compares the
output with the expected text.  The input relies on semantics that only a
traditional preprocessor has, so the test proves the package does its job
rather than merely starting up:

  * ``concat(abc,def)`` with ``#define concat(a, b) a/**/b`` expands to
    ``abcdef`` — the token-paste idiom of K&R C.
  * ``STR(hello)`` with ``#define STR(x) #x`` yields ``#hello``: a traditional
    preprocessor does not implement the ISO ``#`` stringification operator, so
    the ``#`` is passed through instead of quoting the argument.

The checks themselves live in ``test.sh`` (POSIX sh) and are executed from
here, so the assertions run in a real shell against the installed CLI.
"""
import os

from conan import ConanFile


class TradcppTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # test.sh does the assertions and exits non-zero on failure, which
        # makes self.run() raise.  It is invoked by absolute path (the script
        # lives next to this conanfile, not in the build folder) with the build
        # folder as its working directory.
        script = os.path.join(self.recipe_folder, "test.sh")
        # env="conanrun": the package's bin/ directory is added to the run
        # environment for an application package, so `tradcpp` resolves.
        self.run('sh "{}" "{}"'.format(script, self.build_folder),
                 env="conanrun")
