#!/usr/bin/env python3
"""test_package for pd-syslog 0.1 — functional consumer test.

pd-syslog is a Pure Data plugin: there is nothing to link against and no CLI to
execute.  The test therefore:

  1. compiles pd_syslog_test.c for the same target as the package, against the
     Pd API headers re-exported by pd-syslog (i.e. it consumes the package's
     declared interface, not a hand-written include path);
  2. runs it against the packaged syslog.pd_linux.

pd_syslog_test.c is itself the minimal Pure Data runtime: linked with -rdynamic
it defines the nine Pd entry points the plugin imports, so the plugin's Pd
symbols resolve to this process exactly as they do inside a real Pd, and it
interposes openlog/syslog/closelog so the assertions are made on what the plugin
actually forwarded.  The program exits non-zero if any check fails, so
`conan create` fails the package.
"""
import os
import shutil
import tempfile

from conan import ConanFile


class PdSyslogTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    @staticmethod
    def _workdir():
        """Writable scratch directory outside the archive tree.

        E002: /tmp may be read-only, so prefer TMPDIR and then ~/tmp.  Keeping
        the scratch dir out of the repository also keeps the test from writing
        files that the next `git add` would sweep into the PR.
        """
        for root in (os.environ.get("TMPDIR"),
                     os.path.join(os.path.expanduser("~"), "tmp")):
            if root:
                try:
                    os.makedirs(root, exist_ok=True)
                    return tempfile.mkdtemp(prefix="pd-syslog-test-", dir=root)
                except OSError:
                    continue
        return tempfile.mkdtemp(prefix="pd-syslog-test-")

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        pkg = dep.package_folder

        # Locate the packaged plugin, preferring the directory the recipe
        # publishes through cpp_info.libdirs.
        candidates = [os.path.join(pkg, d, "syslog.pd_linux")
                      for d in (dep.cpp_info.libdirs or [])]
        candidates.append(os.path.join(pkg, "lib", "pd-externals", "syslog",
                                       "syslog.pd_linux"))
        plugin = next((c for c in candidates if os.path.isfile(c)), candidates[0])
        if not os.path.isfile(plugin):
            raise Exception(f"packaged plugin not found (looked in {candidates})")

        include_dirs = [d for d in (dep.cpp_info.includedirs or [])
                        if os.path.isfile(os.path.join(d, "m_pd.h"))]
        if not include_dirs:
            raise Exception(
                "pd-syslog did not export the Pd API headers "
                f"(includedirs={list(dep.cpp_info.includedirs or [])})"
            )

        # R33: compiler comes from the Conan profile conf, never from ${CC}.
        executables = self.conf.get("tools.build:compiler_executables",
                                    default={}, check_type=dict)
        cc = executables.get("c") or "clang"

        workdir = self._workdir()
        test_binary = os.path.join(workdir, "pd_syslog_test")
        try:
            includes = " ".join("-I%s" % d for d in include_dirs)
            # -rdynamic is what makes this executable's Pd symbols visible to
            # the dlopen()ed plugin; -ldl is needed by the test itself.
            self.run(
                f'{cc} -std=gnu11 -O1 -Wall -Wextra -fPIC -rdynamic '
                f'{includes} '
                f'"{os.path.join(self.source_folder, "pd_syslog_test.c")}" '
                f'-o "{test_binary}" -ldl'
            )
            # Drive the packaged plugin; exits non-zero if any check fails.
            self.run(f'"{test_binary}" "{plugin}"', env="conanrun")
        finally:
            shutil.rmtree(workdir, ignore_errors=True)
