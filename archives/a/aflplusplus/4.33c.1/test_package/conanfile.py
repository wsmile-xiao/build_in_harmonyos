#!/usr/bin/env python3
"""Conan test recipe for AFLplusplus 4.33c.1 — real usage of the packaged tools.

Red line (R34): every test below genuinely exercises the package — consumer
code compiles against the shipped headers (test_afl.c) and the *packaged
binaries themselves* are executed on a real target program (afl-clang-fast
instrumentation + LLVM passes, afl-showmap coverage capture, afl-fuzz fuzzing
loop, afl-gotcpu). No printf-only stubs: each assertion fails if any packaged
artifact (bin/, lib/afl/, include/) is missing or broken, so the L1e
destructive reverse-verification also fails as intended.
"""
import os
import shutil
import subprocess
import sys
import time

from conan import ConanFile


class TestAflplusplusConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _cc(self):
        # R33: compiler path from Conan conf, never from bare shell env vars.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return compilers.get("c", "clang")

    def _pkg_env(self):
        """Runtime env equivalent to package_info() runenv (PATH + AFL_PATH)."""
        pkg = self.dependencies["aflplusplus"].package_folder
        env = dict(os.environ)
        env["PATH"] = os.path.join(pkg, "bin") + os.pathsep + env.get("PATH", "")
        env["AFL_PATH"] = os.path.join(pkg, "lib", "afl")
        # /tmp is read-only on OHOS (E002) — keep all scratch under build/.
        tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp, exist_ok=True)
        env["TMPDIR"] = tmp
        env["AFL_TMPDIR"] = tmp
        # Non-tty CI friendly fuzzing (no UI, no host tuning checks).
        env["AFL_NO_UI"] = "1"
        env["AFL_SKIP_CPUFREQ"] = "1"
        env["AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES"] = "1"
        env["AFL_NO_CRASH_README"] = "1"
        return env

    def build(self):
        cc = self._cc()
        include_dir = os.path.join(
            self.dependencies["aflplusplus"].package_folder, "include", "afl"
        )
        src_dir = self.source_folder

        # Header-ABI test (consumer code against the packaged headers).
        self.run('{} -I"{}" -o "{}" "{}"'.format(
            cc, include_dir,
            os.path.join(self.build_folder, "test_afl"),
            os.path.join(src_dir, "test_afl.c")))

        # Plain (uninstrumented) fuzz target for the dumb-mode fallback run.
        self.run('{} -O0 -o "{}" "{}"'.format(
            cc,
            os.path.join(self.build_folder, "target_plain"),
            os.path.join(src_dir, "test_target.c")))

    def test(self):
        work = self.build_folder
        src_dir = self.source_folder

        # Seeds with and without the rare 'X' branch of test_target.c.
        seed1 = os.path.join(work, "seed_hello.txt")
        seed2 = os.path.join(work, "seed_X.txt")
        with open(seed1, "w") as fh:
            fh.write("hello world\n")
        with open(seed2, "w") as fh:
            fh.write("X\n")

        passed = 0
        failures = []

        def check(cond, label):
            nonlocal passed
            if cond:
                passed += 1
                print("PASS: {}".format(label))
            else:
                failures.append(label)
                print("FAIL: {}".format(label))

        def cleanup():
            # Run artifacts are temporary — never leave them in the recipe tree.
            for name in ("test_afl", "target_plain", "target_instr",
                         "seed_hello.txt", "seed_X.txt", "map_hello.txt",
                         "map_X.txt", "in", "out", "tmp"):
                path = os.path.join(work, name)
                if os.path.isdir(path):
                    shutil.rmtree(path, ignore_errors=True)
                elif os.path.exists(path):
                    try:
                        os.remove(path)
                    except OSError:
                        pass

        # ── 1. header-ABI test binary (6 assertions inside) ──────────
        self.run(os.path.join(work, "test_afl"), env="conanrun")
        passed += 6
        print("PASS: test_afl header-ABI checks (6 assertions)")

        # ── 2. afl-gotcpu: packaged binary executes and exits 0 ──────
        self.run("afl-gotcpu", env="conanrun")
        passed += 1
        print("PASS: afl-gotcpu executed")

        # ── 3. afl-clang-fast: instrument a consumer target for real
        #       (dispatches on argv[0]; needs the packaged LLVM passes
        #       in AFL_PATH + a working clang via AFL_CC) ─────────────
        target_instr = os.path.join(work, "target_instr")
        self.run('{} -O0 -o "{}" "{}"'.format(
            "afl-clang-fast", target_instr,
            os.path.join(src_dir, "test_target.c")), env="conanrun")
        passed += 1
        print("PASS: afl-clang-fast instrumentation compile")

        # ── 4. afl-showmap: capture real coverage for two inputs ─────
        map1 = os.path.join(work, "map_hello.txt")
        map2 = os.path.join(work, "map_X.txt")
        self.run('afl-showmap -q -m none -o "{}" -- "{}" < "{}"'.format(
            map1, target_instr, seed1), env="conanrun")
        self.run('afl-showmap -q -m none -o "{}" -- "{}" < "{}"'.format(
            map2, target_instr, seed2), env="conanrun")

        m1 = open(map1).read() if os.path.isfile(map1) else ""
        m2 = open(map2).read() if os.path.isfile(map2) else ""
        check(m1.strip() != "", "afl-showmap map non-empty for seed 'hello'")
        check(m2.strip() != "", "afl-showmap map non-empty for seed 'X'")
        # Different inputs take different edges → maps must differ.
        check(m1 != m2, "instrumentation distinguishes inputs (maps differ)")

        # ── 5. afl-fuzz: bounded dumb-mode run against the plain
        #       target (fork/exec + mmap shm + non-tty UI); the fuzzer
        #       must start and seed its queue. -m none is REQUIRED: the
        #       default RLIMIT_AS is applied to the forked child which
        #       already inherits the large VA of the conan/python parent
        #       (same recipe as afl/1.35b test_package) ────────────────
        in_dir = os.path.join(work, "in")
        out_dir = os.path.join(work, "out")
        os.makedirs(in_dir, exist_ok=True)
        with open(os.path.join(in_dir, "seed.txt"), "w") as fh:
            fh.write("hello world\n")

        env = self._pkg_env()
        cmd = 'afl-fuzz -n -m none -i "{}" -o "{}" -- "{}"'.format(
            in_dir, out_dir, os.path.join(work, "target_plain"))
        try:
            proc = subprocess.Popen(
                cmd, shell=True, env=env, cwd=work,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(10)
            proc.kill()
            proc.wait()
        except Exception as exc:
            print("FAIL: afl-fuzz smoke could not start: {}".format(exc))
            cleanup()
            sys.exit(1)

        queue = os.path.join(out_dir, "queue")
        check(os.path.isdir(queue) and bool(os.listdir(queue)),
              "afl-fuzz started and seeded out/queue")

        cleanup()

        # Machine-readable summary (kept in sync with MANIFEST.yml).
        total = passed + len(failures)
        print("\nASSERTIONS: passed={} failed={} total={}".format(
            passed, len(failures), total))
        if failures:
            print("\nFAILURES:")
            for f in failures:
                print("  - {}".format(f))
            sys.exit(1)
        print("\nALL AFLPLUSPLUS CONSUMER TESTS PASSED")
