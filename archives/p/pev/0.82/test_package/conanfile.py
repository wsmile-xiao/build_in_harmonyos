#!/usr/bin/env python3
"""Smoke test for pev 0.82 (application package).

Checks, in order:
1. `readpe -V` runs (L2-style version smoke; proves the OpenSSL NEEDED
   entries resolve — libpe is statically linked per patch 0003);
2. a minimal but well-formed PE32 image generated at test time by the
   tracked test source `pe32_sample.py` is parsed by `readpe` and hashed
   by `pehash -a sha512` (libpe OpenSSL EVP hashing);
3. `readpe -f json` works — the json output plugin is dlopen'd from the
   compile-time-baked PLUGINSDIR (<package>/lib/pev/plugins), so this
   exercises the plugin directory the tools hard-require
   (include/common.h PEV_INITIALIZE exits when it is missing).
"""

import os
import sys
import tempfile

from conan import ConanFile
from conan.tools.build import can_run


class PevTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        dep = self.dependencies["pev"]
        bin_dir = dep.cpp_info.bindirs[0]
        readpe = os.path.join(bin_dir, "readpe")
        pehash = os.path.join(bin_dir, "pehash")

        # 1. version smoke — also proves the OpenSSL NEEDED entries
        #    resolve at load time (libpe itself is statically linked,
        #    patch 0003)
        self.run('"{}" -V'.format(readpe), env="conanrun")

        # minimal PE32 sample generated at test time by the tracked test
        # source pe32_sample.py (CI L0c), into a scratch dir — never next
        # to the test_package sources (that would drop a binary into the
        # recipe folder)
        scratch = tempfile.mkdtemp(prefix="pev-test-")
        sample = os.path.join(scratch, "pev_smoke.exe")
        generator = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "pe32_sample.py"
        )
        self.run(
            '"{}" "{}" "{}"'.format(sys.executable, generator, sample),
            env="conanrun",
        )

        # 2. header parse + libpe/OpenSSL hashing
        self.run('"{}" "{}"'.format(readpe, sample), env="conanrun")
        self.run('"{}" -a sha512 "{}"'.format(pehash, sample), env="conanrun")

        # 3. dlopen'd output plugin (json) from the baked PLUGINSDIR
        self.run('"{}" -f json "{}"'.format(readpe, sample), env="conanrun")
