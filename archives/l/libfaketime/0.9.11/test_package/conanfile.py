#!/usr/bin/env python3
"""Conan test_package — libfaketime 0.9.11 behaviour verification.

libfaketime is an LD_PRELOAD payload, so the four probe programs link against
libc only and are *driven* here: each scenario injects the packaged library and
asserts the observable clock/pid/random behaviour through exit codes.
"""
import os
import time

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout

DAY = 86400


class LibfaketimeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    # -- helpers ---------------------------------------------------------
    def _pkg(self):
        return self.dependencies["libfaketime"].package_folder

    def _bin(self, name):
        # cmake_layout puts the binaries in a per-config subdirectory; look for
        # the freshly built probe instead of hardcoding the layout.
        for root, _, files in os.walk(self.build_folder):
            if name in files:
                return os.path.join(root, name)
        raise ConanException(f"probe {name} was not built under {self.build_folder}")

    def _run(self, command, env=None):
        prefix = ""
        if env:
            prefix = " ".join(f'{k}="{v}"' for k, v in env.items()) + " "
        self.run(f"{prefix}{command}", env="conanrun")

    # -- scenarios -------------------------------------------------------
    def test(self):
        pkg = self._pkg()
        lib = os.path.join(pkg, "lib", "faketime", "libfaketime.so.1")
        lib_mt = os.path.join(pkg, "lib", "faketime", "libfaketimeMT.so.1")
        cli = os.path.join(pkg, "bin", "faketime")
        clock = self._bin("clock_probe")
        cond = self._bin("cond_probe")
        abi = self._bin("abi_probe")
        misc = self._bin("misc_probe")
        now = int(time.time())

        # 1. `faketime '<absolute timestamp>' <prog>`: the shipped wrapper resolves
        #    the library from its compile-time PREFIX and offsets all three clock
        #    APIs. The timestamp must be absolute — the wrapper normalises it with
        #    `date -d <spec> +%s`, and OHOS ships toybox date, which rejects every
        #    relative form ("-15d", "15 days ago") with "bad date".
        target = now - 15 * DAY
        spec = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(target))
        self._run(f'"{cli}" "{spec}" "{clock}" --expect {target} --tol 5')

        # 2. Bare LD_PRELOAD with a relative offset.
        self._run(f'"{clock}" --expect {now - 2 * DAY} --tol 5',
                  env={"LD_PRELOAD": lib, "FAKETIME": "-2d"})

        # 3. FAKETIME="@<datetime>" is the upstream "START date" form; it is
        #    resolved in the process's local timezone, so derive the expected
        #    epoch with mktime() instead of hardcoding a UTC value.
        start = "2000-01-01 00:00:00"
        epoch = int(time.mktime(time.strptime(start, "%Y-%m-%d %H:%M:%S")))
        self._run(f'"{clock}" --expect {epoch} --tol 5',
                  env={"LD_PRELOAD": lib, "FAKETIME": f"@{start}"})

        # 4. The threaded build must interpose just as well.
        self._run(f'"{clock}" --expect {now - 3 * DAY} --tol 5',
                  env={"LD_PRELOAD": lib_mt, "FAKETIME": "-3d"})

        # 5. posix timer + pthread_cond_timedwait: the interposers that had to
        #    be re-bound on musl/OHOS. Waits ~1 s of real time on a faked clock.
        self._run(f'"{cond}"', env={"LD_PRELOAD": lib, "FAKETIME": "-15d"})

        # 6. Exported ABI, driven the only way this library can be inspected:
        #    preloaded. 11 public names must resolve *into* libfaketime (libc
        #    answering instead would pass a naive dlsym), the 8 internal
        #    _22/_232/_233 implementations must stay hidden, and the addresses
        #    the dynamic linker bound for this caller's own time()/getpid()/
        #    pthread_cond_timedwait() calls must land in libfaketime too.
        self._run(f'"{abi}" libfaketime.so.1', env={"LD_PRELOAD": lib})

        # 7. FAKE_PID: the library must answer getpid() with FAKETIME_FAKEPID.
        self._run(f'"{misc}" --pid', env={
            "LD_PRELOAD": lib,
            "FAKETIME_FAKEPID": "424242",
        })

        # 8a/8b/8c. FAKE_RANDOM: the seeded stream must be reproducible across
        #     processes (same seed -> same bytes) and the seed must actually be
        #     in play (different seed -> different bytes). The seeds are 64-bit
        #     hex values, following upstream's own test/snippets/*.variable
        #     convention: fakerandom_msws() yields ((i * seed) >> 32) & 0xFF per
        #     byte, so a 16-byte read degenerates to all zeros for any seed
        #     below 2^28 (measured on this device).
        build = self.build_folder
        a1 = os.path.join(build, "seed-a1.hex")
        a2 = os.path.join(build, "seed-a2.hex")
        b1 = os.path.join(build, "seed-b1.hex")
        seed_a = "0x0123456789ABCDEF"
        seed_b = "0xDEADBEEFDEADBEEF"
        for out, seed in ((a1, seed_a), (a2, seed_a), (b1, seed_b)):
            self._run(f'"{misc}" --random --seed "{out}"', env={
                "LD_PRELOAD": lib,
                "FAKERANDOM_SEED": seed,
            })
        with open(a1) as f: stream_a1 = f.read().strip()
        with open(a2) as f: stream_a2 = f.read().strip()
        with open(b1) as f: stream_b1 = f.read().strip()
        if stream_a1 != stream_a2:
            raise ConanException(
                f"FAKE_RANDOM is not deterministic for one seed: {stream_a1} != {stream_a2}")
        if stream_a1 == stream_b1:
            raise ConanException(
                f"FAKERANDOM_SEED has no effect: both seeds produced {stream_a1}")

        # 9. Without a seed the two APIs must fall through to real kernel
        #    entropy (asserted inside the probe).
        self._run(f'"{misc}" --random --seed "{os.path.join(build, "noseed.hex")}"',
                  env={"LD_PRELOAD": lib})

        # 10. Negative control: without the preload the clock must NOT be faked,
        #     so the same --expect value has to make the probe fail.
        ret = 0
        try:
            self._run(f'"{clock}" --expect {target} --tol 5')
        except Exception:
            ret = 1
        if ret != 1:
            raise ConanException(
                "control case failed: clock_probe saw a faked time without LD_PRELOAD")
