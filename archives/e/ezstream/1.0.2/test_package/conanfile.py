#!/usr/bin/env python3
"""test_package — ezstream 1.0.2 consumer-side validation (R34).

ezstream is a CLI application: the package ships the `ezstream`,
`ezstream-cfgmigrate` and `ezstream-file.sh` executables. The consumer
test therefore executes the installed binaries (see test_ezstream.sh)
and asserts their observable behaviour:

  1. `ezstream -V` prints "ezstream version 1.0.2".
  2. `ezstream -c <valid.xml>` parses a real 1.0.2-format XML config
     (libxml2 code path) and attempts to reach the configured Icecast
     server — the expected "Couldn't connect" failure on a test box
     proves the configure -> parse -> connect pipeline works.
  3. `ezstream -c <broken.xml>` surfaces a libxml2 parser error.
  4. `ezstream-cfgmigrate -h` prints its usage banner.
"""

import os

from conan import ConanFile
from conan.tools.build import can_run


class EzstreamTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Nothing to compile: the package ships executables; the test
        # exercises them directly through test_ezstream.sh.
        pass

    def test(self):
        if not can_run(self):
            return
        bin_dir = self.dependencies["ezstream"].cpp_info.bindirs[0]
        script = os.path.join(self.source_folder, "test_ezstream.sh")
        datadir = self.source_folder

        # The binaries link shared libs from the dependency graph plus the
        # OHOS libc++_shared runtime; expose those on LD_LIBRARY_PATH for
        # the child process (VirtualRunEnv covers conan-managed deps, the
        # extra entry covers libc++_shared from the OHOS toolchain).
        paths = []
        for _, dep in self.dependencies.items():
            for d in dep.cpp_info.aggregated_components().libdirs:
                if d not in paths:
                    paths.append(d)
        # Ask the compiler where libc++_shared.so lives (works across
        # symlink and CI worker SDK layouts), fall back to the legacy
        # realpath-based candidate.
        import subprocess
        compilers = self.conf.get("tools.build:compiler_executables", default={}) or {}
        # Prefer the C++ compiler; derive from the C compiler when the
        # profile only declares that one (same LLVM bin dir).
        cxx = str(compilers.get("cpp", "") or compilers.get("c", ""))
        if cxx and os.path.isfile(cxx):
            try:
                out = subprocess.run(
                    [cxx, "-print-file-name=libc++_shared.so"],
                    capture_output=True, text=True, timeout=60,
                ).stdout.strip()
            except (OSError, subprocess.TimeoutExpired):
                out = ""
            if out and "error" not in out.lower() and os.path.isabs(out):
                out = os.path.normpath(out)
                if os.path.isfile(out):
                    d = os.path.dirname(out)
                    if d not in paths:
                        paths.append(d)
                    cxx = ""  # found; skip fallback
        if cxx and os.path.isfile(cxx):
            cc_real = os.path.realpath(cxx)
            cand = os.path.join(
                os.path.dirname(os.path.dirname(cc_real)),
                "lib", "aarch64-linux-ohos",
            )
            if os.path.isdir(cand) and cand not in paths:
                paths.append(cand)
        if paths:
            existing = os.environ.get("LD_LIBRARY_PATH", "")
            os.environ["LD_LIBRARY_PATH"] = (
                os.pathsep.join(paths) + (os.pathsep + existing if existing else "")
            )

        self.run(
            f'sh "{script}" "{bin_dir}" "{datadir}"',
            cwd=self.build_folder,
        )
