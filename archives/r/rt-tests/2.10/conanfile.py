#!/usr/bin/env python3
"""Conan recipe for rt-tests 2.10 - realtime test suite (cyclictest, signaltest, ...).

Upstream is a hand-written Makefile project (no autotools). OpenHarmony/bionic
adaptations, all reproduced on the device (see notes.md):

* Upstream writes ``#error "Can't run this test without PI Mutex support"`` when
  ``_POSIX_THREAD_PRIO_INHERIT`` is undefined. bionic's <unistd.h> leaves that
  POSIX option macro undefined even though the runtime calls work, so
  ``-D_POSIX_THREAD_PRIO_INHERIT=200809L`` keeps pi_stress instead of disabling it.
* ``get_cpu()`` uses the glibc-only ``getcpu()``; bionic provides
  ``sched_getcpu()`` (its ``__NR_getcpu`` syscall is blocked with SIGSYS), so
  ``-DHAVE_SCHED_GETCPU`` selects the portable path.
* The archive has no libnuma and OHOS exposes no NUMA topology, so rt-tests is
  built ``RT_NO_NUMA`` (the NUMA helpers are stubbed in patches 0001/0005) and
  ``no_libcpupower=1``. cyclictest/signaltest/oslat then omit --numa and
  --deepest-idle-state, which do not exist on OHOS.
* bionic lacks ``pthread_setaffinity_np``/``pthread_getaffinity_np``/
  ``pthread_attr_setaffinity_np`` (patch 0006 adds them via bionic.h, gated so
  only the affinity shims are supplied because bionic *does* have barriers) and
  ``SIGEV_THREAD_ID`` (patch 0003 falls back to SIGEV_SIGNAL).
* The stock CFLAGS carry gcc-only spellings (``-Wno-error=format-truncation=``,
  ``-Wno-nonnull``); under -Werror clang rejects the unknown option outright.
* pmqtest is not built: its POSIX message-queue calls (mq_open/mq_send/...) only
  exist in the *static* libc.a on OHOS, not in the shared libc.so that the
  linker resolves against.

Package contents: the 13 buildable *-tests* binaries under bin/.
"""
import os

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout

# pmqtest is intentionally omitted (POSIX mq_* live only in static libc.a).
BINARIES = [
    "cyclictest", "hackbench", "pip_stress", "pi_stress",
    "ptsematest", "rt-migrate-test", "signaltest", "sigwaittest", "svsematest",
    "cyclicdeadline", "deadline_test", "queuelat", "ssdd", "oslat",
]


class RtTestsConan(ConanFile):
    name = "rt-tests"
    version = "2.10"
    description = "Real-time test suite (cyclictest, signaltest, ...)"
    license = "GPL-2.0-or-later"
    homepage = "https://git.kernel.org/pub/scm/utils/rt-tests/rt-tests.git/"
    url = "https://cnb.cool/ohpcd/ohos-pc-archives/-/tree/main/archives/r/rt-tests/2.10"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        cc = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = str(cc.get("c") or "clang")
        ar = str(cc).replace("clang", "llvm-ar")
        extra = ("-D_POSIX_THREAD_PRIO_INHERIT=200809L -DHAVE_SCHED_GETCPU "
                 "-DRT_NO_NUMA -DPTHREAD_BIONIC")
        self.run(
            "make -j1 " + " ".join(BINARIES) + " PYTHON=echo PYLIB= "
            "RT_NO_NUMA=1 no_libcpupower=1 "
            f'CC="{cc}" AR="{ar}" CFLAGS="-Wall -Wextra -Wno-unused-parameter '
            f'-Wno-sign-compare -Wno-missing-field-initializers {extra}"',
            cwd=self.source_folder,
        )

    def package(self):
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        for name in BINARIES:
            copy(self, name, src=self.source_folder, dst=bin_dir, keep_path=False)
            path = os.path.join(bin_dir, name)
            if os.path.isfile(path):
                os.chmod(path, 0o755)
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
