#!/usr/bin/env python3
"""Conan test_package for wrapsrv 1.0.0 (R34/PF3: executes the real binary).

The delivered ``wrapsrv`` CLI is exercised end to end:

* usage / CLI contract (exit code + exact stderr text)
* the full SRV pipeline: DNS SRV answer parsing (ns_initparse/ns_parserr),
  RFC 2782 priority + weight selection, ``%h`` / ``%p`` substitution and the
  real execution of the resulting command line
* negative DNS paths: NXDOMAIN rcode, empty answer section, and a live lookup
  against the platform resolver

The DNS transport is the only stubbed layer: ``res_stub.c`` is compiled into a
throwaway ``LD_PRELOAD`` object that returns a canned, byte-accurate DNS
response.  Everything downstream of ``res_query()`` is the delivered upstream
code.  A live SRV lookup is not reproducible on a CI worker (no DNS, and an
SRV-capable authoritative server cannot be bound on port 53 without root), so
this seam is what makes the pipeline assertable instead of merely "not
crashing".
"""
import os
import shutil
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class WrapsrvTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        self.folders.build = "."

    def build(self):
        # The test drives the packaged binary through test_wrapsrv.sh; the DNS
        # transport shim is compiled by test() into a temp dir so that no build
        # residue lands in the repository.
        pass

    def test(self):
        if not can_run(self):
            raise ConanException(
                "can_run() is False: refusing to report a green test without "
                "executing the packaged wrapsrv binary."
            )

        script = os.path.join(self.source_folder, "test_wrapsrv.sh")
        if not os.path.isfile(script):
            raise ConanException(f"Test script not found: {script}")

        workdir = tempfile.mkdtemp(prefix="wrapsrv-resstub-")
        try:
            shim_src = os.path.join(workdir, "res_stub.c")
            with open(os.path.join(self.source_folder, "res_stub.c"), encoding="utf-8") as fh:
                shim_src_text = fh.read()
            with open(shim_src, "w", encoding="utf-8") as fh:
                fh.write(shim_src_text)

            shim_so = os.path.join(workdir, "libwrapsrvresstub.so")
            self.run(
                f'"{self._c_compiler()}" -shared -fPIC -O2 -o "{shim_so}" "{shim_src}"',
                cwd=workdir,
            )

            # Any non-zero exit (including an execution problem such as
            # "Operation not permitted") fails the test on purpose: it must be
            # visible in CI instead of being downgraded to a green skip.
            self.run(
                f'WRAPSRV_RES_STUB="{shim_so}" bash "{script}"', env="conanrun"
            )
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

    def _c_compiler(self):
        executables = self.conf.get("tools.build:compiler_executables",
                                    default={}, check_type=dict)
        return executables.get("c") or "clang"
