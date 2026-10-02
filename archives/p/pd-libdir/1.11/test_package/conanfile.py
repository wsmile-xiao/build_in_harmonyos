#!/usr/bin/env python3
"""test_package for pd-libdir 1.11 — functional consumer test.

pd-libdir is a Pure Data loader plugin, so there is nothing to link against
and no CLI to execute.  The test therefore:

  1. compiles pd_libdir_test.c for the same target as the package, against the
     Pd API headers re-exported by pd-libdir (i.e. it consumes the package's
     declared interface, not a hand-written include path);
  2. runs it against the packaged libdir.pd_linux.

pd_libdir_test.c dlopen()s the real packaged plugin and drives its actual code
(setup(), the registered loader, the meta-file lookup and the "add-to-path"
message) against a minimal Pure Data runtime shim, then asserts 22 checks.
The program exits non-zero if any check fails, so `conan create` fails the
package.
"""
import os
import shutil
import tempfile

from conan import ConanFile


class PdLibdirTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    @staticmethod
    def _workdir():
        """Writable scratch directory outside the archive tree.

        E002: /tmp may be read-only, so prefer TMPDIR and then ~/tmp, matching
        the mktemp convention used by other test_package shell probes.
        """
        for root in (os.environ.get("TMPDIR"), os.path.join(os.path.expanduser("~"), "tmp")):
            if root:
                try:
                    os.makedirs(root, exist_ok=True)
                    return tempfile.mkdtemp(prefix="pd-libdir-test-", dir=root)
                except OSError:
                    continue
        return tempfile.mkdtemp(prefix="pd-libdir-test-")

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        pkg = dep.package_folder

        # Locate the packaged plugin, preferring the directories the recipe
        # publishes through cpp_info.
        candidates = [os.path.join(pkg, d, "libdir.pd_linux")
                      for d in (dep.cpp_info.libdirs or [])]
        candidates.append(os.path.join(pkg, "lib", "libdir", "libdir.pd_linux"))
        plugin = next((c for c in candidates if os.path.isfile(c)), candidates[0])
        if not os.path.isfile(plugin):
            raise Exception(f"packaged plugin not found (looked in {candidates})")

        include_dirs = [d for d in (dep.cpp_info.includedirs or [])
                        if os.path.isfile(os.path.join(d, "m_pd.h"))]
        if not include_dirs:
            raise Exception(
                "pd-libdir did not export the Pd API headers "
                f"(includedirs={list(dep.cpp_info.includedirs or [])})"
            )

        # R33: compiler comes from the Conan profile conf, never from ${CC}.
        executables = self.conf.get("tools.build:compiler_executables",
                                    default={}, check_type=dict)
        cc = executables.get("c") or "clang"

        workdir = self._workdir()
        test_binary = os.path.join(workdir, "pd_libdir_test")
        scratch = os.path.join(workdir, "scratch")
        os.makedirs(scratch, exist_ok=True)
        try:
            includes = " ".join("-I%s" % d for d in include_dirs)
            self.run(
                f'{cc} -std=gnu11 -O1 -Wall -Wextra -fPIC -rdynamic '
                f'{includes} '
                f'"{os.path.join(self.source_folder, "pd_libdir_test.c")}" '
                f'-o "{test_binary}" -ldl'
            )
            # Drive the packaged plugin; exits non-zero if any check fails.
            self.run(f'"{test_binary}" "{plugin}" "{scratch}"', env="conanrun")
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
