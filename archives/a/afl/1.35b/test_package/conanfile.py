#!/usr/bin/env python3
"""Conan test recipe for afl — tool-type package smoke test (shell-style)."""
import os
import shutil
import subprocess
import sys
import time

from conan import ConanFile


class TestAflConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Build a tiny stdin-processing "fuzz target" that the afl tools
        # will drive. It does not link against afl (afl is a tool package,
        # not a library) — the real package usage is exercised in test().
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c", "clang")
        test_src = os.path.join(self.source_folder, "test_afl.c")
        test_bin = os.path.join(self.build_folder, "test_afl")
        self.run('{} -O0 -o "{}" "{}"'.format(cc, test_bin, test_src))

    def test(self):
        seed = os.path.join(self.source_folder, "seed.txt")
        test_bin = os.path.join(self.build_folder, "test_afl")

        # 1. afl-gotcpu: CPU affinity/benchmark tool, must exit 0.
        self.run("afl-gotcpu", env="conanrun")

        # 2. afl-showmap: fork/exec the target via stdin. On aarch64 the
        #    map stays empty (no instrumentation — classic afl's afl-as
        #    injection is x86-only), but the fork/exec/wait chain and the
        #    mmap-based shared memory must work; -q skips the
        #    "No instrumentation detected" FATAL that only fires in
        #    verbose mode. Absolute paths are used because the test()
        #    cwd is not guaranteed to be the build folder.
        #    -m none is REQUIRED: the default 50 MB RLIMIT_AS is applied
        #    to the forked child which already inherits the large virtual
        #    address space of the conan/python parent, so execve fails
        #    with ENOMEM ("Unable to execute").
        map_out = os.path.join(self.build_folder, "map.out")
        self.run(
            'afl-showmap -q -m none -o "{}" -- "{}" < "{}"'.format(
                map_out, test_bin, seed
            ),
            env="conanrun",
        )

        # 3. afl-fuzz dumb mode (-n): bounded 10s run against the target.
        #    The out/queue directory must be created with the initial seed,
        #    proving the fuzzer actually started (mmap shm + fork + UI off
        #    on a non-tty all work on OHOS). -m none for the same reason
        #    as afl-showmap above (inherited-VA vs RLIMIT_AS).
        in_dir = os.path.join(self.build_folder, "in")
        out_dir = os.path.join(self.build_folder, "out")
        os.makedirs(in_dir, exist_ok=True)
        shutil.copy(seed, os.path.join(in_dir, "seed.txt"))

        cmd = 'afl-fuzz -n -m none -i "{}" -o "{}" -- "{}"'.format(
            in_dir, out_dir, test_bin
        )
        full_env = dict(os.environ)
        full_env.update(self.dependencies["afl"].runenv_info.vars(self))
        try:
            proc = subprocess.Popen(
                cmd, shell=True, env=full_env, cwd=self.build_folder,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            time.sleep(10)
            proc.kill()
            proc.wait()
        except Exception as exc:
            print("FAIL: afl-fuzz smoke could not start: {}".format(exc))
            sys.exit(1)

        queue = os.path.join(out_dir, "queue")
        if not os.path.isdir(queue) or not os.listdir(queue):
            print("FAIL: afl-fuzz did not create out/queue (fuzzer did not start)")
            sys.exit(1)
        print("PASS: afl-fuzz -n created out/queue with initial seed")
