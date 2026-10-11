#!/usr/bin/env python3
"""Conan recipe for paflib 0.3.0 - IBM Power Architecture Facilities Library.

paflib exposes Power Architecture facilities from userspace: the Data Stream
Control Register (DSCR), Event-Based Branching (EBB), the Program Priority
Register (PPR) and the Time Base (TB).  Every one of them is implemented with
PowerPC-only instructions (``mfspr``/``mtspr``, ``or Rx,Rx,Rx``, ``rfebb``) and
a 23 KB PowerPC assembly EBB callback; upstream ``configure.ac`` hard-errors on
any non-PowerPC host.

HarmonyOS/OHOS target is aarch64, so this recipe is a *port*:

* ``common``, ``dsc``, ``tb`` and ``ppr`` are made portable.  On aarch64 there
  is no DSCR/PPR hardware: DSCR reports "not available" (``ENOSYS``) exactly
  like upstream does on Power < ISA 2.05, and the PPR/lock hints become no-ops.
  The Time Base has no aarch64 register either, so ``paf_timing_now()`` falls
  back to ``clock_gettime(CLOCK_MONOTONIC)`` (nanoseconds), which preserves the
  monotonic-tick contract of the API.
* ``ebb`` keeps its full public API but degrades gracefully: without the Power
  ISA 2.07 EBB facility there is no raw Power PMU event to attach, so
  ``paf_ebb_pmu_init*``/``paf_ebb_event_close`` return ``-1`` with ``errno``
  ``ENOSYS`` and the handler/branch entry points return ``EBB_REG_ERR``.
* Every Power-only EBB test is compiled into a stub that prints an explicit
  ``SKIP`` notice and exits 0, so the upstream test count is preserved and no
  test fails for a platform reason.  On Power the original code and tests are
  kept verbatim behind ``#if defined(__powerpc__)``.

The Power-specific assembly callback (``ebb-callback.S``), the direct-DSO
``.interp`` trick (``paf-interp.c``) and the ``__paflib_*_main`` entry points
are not built on aarch64.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get, save)
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"

# Upstream `make check` registers these 13 tests.
UPSTREAM_TESTS = [
    "dsc/tests/test_dsc",
    "ebb/tests/test_ebb",
    "ebb/tests/test_ebb_save_area_env.sh",
    "ebb/tests/test_ebb_pmu",
    "ebb/tests/test_ebb_pmu_reset",
    "ebb/tests/test_ebb_backtrace",
    "ebb/tests/test_ebb_pmu_multi",
    "ebb/tests/test_ebb_pmu_clobber",
    "ebb/tests/test_ebb_child",
    "ebb/tests/test_ebb_clear_on_close",
    "ebb/tests/test_ebb_nohandler",
    "ebb/tests/test_ebb_cpu",
    "tb/tests/test_tb",
]

# EBB test programs and their extra sources.
EBB_TESTS = [
    ("test_ebb", ["ebb/tests/test_ebb.c"], []),
    ("test_ebb_pmu", ["ebb/tests/test_ebb_pmu.c"],
     ["ebb/tests/test_ebb_common.c"]),
    ("test_ebb_pmu_reset", ["ebb/tests/test_ebb_pmu_reset.c"],
     ["ebb/tests/test_ebb_common.c"]),
    ("test_ebb_backtrace", ["ebb/tests/test_ebb_backtrace.c"],
     ["ebb/tests/test_ebb_common.c"]),
    ("test_ebb_pmu_multi", ["ebb/tests/test_ebb_pmu_multi.c"],
     ["ebb/tests/test_ebb_common.c"]),
    ("test_ebb_pmu_clobber", ["ebb/tests/test_ebb_pmu_clobber.c"],
     ["ebb/tests/test_ebb_common.c"]),
    ("test_ebb_child", ["ebb/tests/test_ebb_child.c"],
     ["ebb/tests/test_ebb_common.c"]),
    ("test_ebb_clear_on_close", ["ebb/tests/test_ebb_clear_on_close.c"],
     ["ebb/tests/test_ebb_common.c"]),
    ("test_ebb_nohandler", ["ebb/tests/test_ebb_nohandler.c"],
     ["ebb/tests/test_ebb_common.c"]),
    ("test_ebb_cpu", ["ebb/tests/test_ebb_cpu.c"],
     ["ebb/tests/test_ebb_common.c"]),
]


class PaflibConan(ConanFile):
    name = "paflib"
    version = "0.3.0"
    description = ("IBM Power Architecture Facilities Library "
                   "(DSCR / EBB / PPR / Time Base)")
    license = "MIT"
    homepage = "https://github.com/paflib/paflib"
    url = "https://github.com/paflib/paflib"

    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "paflib OHOS adaptation is validated on Linux/OHOS; got %s"
                % self.settings.os)

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _tool(self, name, fallback):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        return executables.get(name) or fallback

    def build(self):
        apply_conandata_patches(self)

        cc = self._tool("c", "clang")
        ar = self._tool("ar", "llvm-ar")
        src = self.source_folder
        objdir = os.path.join(self.build_folder, "obj")
        os.makedirs(objdir, exist_ok=True)

        # A config.h is normally produced by autoconf; the sources only need
        # the PACKAGE_* macros from it.
        save(self, os.path.join(src, "config.h"),
             '#define PACKAGE_STRING "libpaf 0.3.0"\n'
             '#define PACKAGE_VERSION "0.3.0"\n'
             '#define PACKAGE_BUGREPORT "cseo@linux.vnet.ibm.com"\n')

        common_incs = ["-I%s" % src, "-I%s/common" % src]

        dsc_lib = self._archive(
            cc, ar, objdir, "libpaf-dsc",
            ["dsc/dsc.c", "dsc/hwcap.c", "dsc/init.c", "common/paf-hwcap.c"],
            common_incs + ["-I%s/dsc" % src])
        ebb_lib = self._archive(
            cc, ar, objdir, "libpaf-ebb",
            ["ebb/ebb.c", "ebb/ebb-init.c", "ebb/ebb-hwcap.c",
             "ebb/ebb-hook.c", "common/paf-hwcap.c"],
            common_incs + ["-I%s/ebb" % src])

        self._run_upstream_tests(cc, src, objdir, dsc_lib, ebb_lib)

    def _archive(self, cc, ar, objdir, name, sources, incs):
        outdir = os.path.join(objdir, name)
        os.makedirs(outdir, exist_ok=True)
        objs = []
        for rel in sources:
            obj = os.path.join(outdir, os.path.basename(rel) + ".o")
            self.run('"%s" -O2 -fPIC -Wno-unused-function %s -c "%s" -o "%s"'
                     % (cc, " ".join(incs), os.path.join(self.source_folder, rel),
                        obj))
            objs.append(obj)
        lib = os.path.join(self.build_folder, name + ".a")
        self.run('"%s" rcs "%s" %s' % (ar, lib, " ".join('"%s"' % o for o in objs)))
        return lib

    def _compile(self, cc, objdir, name, sources, incs, libs):
        exe = os.path.join(objdir, name)
        cmd = ('"%s" -O2 -Wno-unused-function %s %s %s -lpthread -o "%s"'
               % (cc, " ".join(incs),
                  " ".join('"%s"' % s for s in sources),
                  " ".join('"%s"' % l for l in libs), exe))
        self.run(cmd)
        return exe

    def _run_upstream_tests(self, cc, src, objdir, dsc_lib, ebb_lib):
        # libpaf-dsc consumer
        exe = self._compile(
            cc, objdir, "test_dsc",
            [os.path.join(src, "dsc/tests/test_dsc.c")],
            ["-I%s" % src, "-I%s/common" % src, "-I%s/dsc" % src],
            [dsc_lib])
        self.run('"%s"' % exe)

        # libpaf-tb (header only)
        exe = self._compile(
            cc, objdir, "test_tb",
            [os.path.join(src, "tb/tests/test_tb.c")],
            ["-I%s" % src, "-I%s/common" % src, "-I%s/tb" % src],
            [])
        self.run('"%s"' % exe)

        # libpaf-ebb programs (Power-only bodies are compiled to SKIP stubs)
        for name, sources, extra in EBB_TESTS:
            incs = ["-I%s" % src, "-I%s/common" % src, "-I%s/ebb" % src,
                    "-I%s/ebb/tests" % src]
            srcs = [os.path.join(src, s) for s in sources + extra]
            exe = self._compile(cc, objdir, name, srcs, incs, [ebb_lib])
            self.run('"%s"' % exe)

        # version entry point / save-area script
        self.run('sh "%s"' % os.path.join(src, "ebb/tests/test_ebb_save_area_env.sh"))

    def package(self):
        include_paf = os.path.join(self.package_folder, "include", "paf")
        for hdr in ("dsc/paf/dsc.h", "ebb/paf/ebb.h", "tb/paf/tb.h",
                    "ppr/paf/ppr.h"):
            copy(self, hdr, self.source_folder, include_paf, keep_path=False)
        for lib in ("libpaf-dsc.a", "libpaf-ebb.a"):
            copy(self, lib, self.build_folder,
                 os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, "COPYING", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)
        copy(self, "dsc/doc/libpaf-dsc.3", self.source_folder,
             os.path.join(self.package_folder, "share", "man", "man3"),
             keep_path=False)
        copy(self, "ebb/doc/libpaf-ebb.3", self.source_folder,
             os.path.join(self.package_folder, "share", "man", "man3"),
             keep_path=False)
        copy(self, "tb/doc/libpaf-tb.3", self.source_folder,
             os.path.join(self.package_folder, "share", "man", "man3"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["paf-dsc", "paf-ebb"]
