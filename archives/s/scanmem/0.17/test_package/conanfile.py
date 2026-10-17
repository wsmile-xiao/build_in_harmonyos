#!/usr/bin/env python3
"""Conan test_package for scanmem 0.17.

scanmem ships a CLI *and* a shared library, so this consumer test covers both
halves:

  * build() compiles three real test sources with the same toolchain the
    package was built with --
      check_api.c        links against the packaged headers + libscanmem
                         (compile-time and link-time dependency on the
                         package; this is what the CI L1e negative test
                         bites on),
      scanmem_target.c   a live process holding a known sentinel, mirroring
                         upstream's test/memfake.c,
      check_libscanmem.c dlopen/dlsym probe of the packaged libscanmem.so.1.
  * test() executes the packaged `scanmem` binary and then test_scanmem.sh,
    which runs eight offline functional checks and prints
    HMBS_TEST_PACKAGE_RESULT itself, so the gate reads real counters instead
    of scraping stdout.
"""
import os

from conan import ConanFile


class ScanmemTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv", "VirtualBuildEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _cc(self):
        """Resolve the C compiler without relying on a bare shell variable.

        CI's L0h gate rejects self.run() lines that interpolate ${CC}/${CFLAGS}
        and friends, so the path is resolved here in Python and passed as a
        plain argument instead.
        """
        try:
            mapping = self.conf.get("tools.build:compiler_executables")
            if isinstance(mapping, dict) and mapping.get("c"):
                return str(mapping["c"])
        except Exception:
            pass
        return os.environ.get("CC") or "clang"

    def _dep(self):
        return self.dependencies[self.tested_reference_str]

    def _abs(self, paths):
        """Normalise a cpp_info path list to forward slashes for the shell."""
        return " ".join('"%s"' % p.replace("\\", "/") for p in paths)

    def build(self):
        cc = self._cc()
        # check_api.c is the real consumer: it includes the packaged
        # <scanmem/scanmem.h> and links -lscanmem, so it breaks if the
        # package's include/ or lib/ is missing.
        dep = self._dep()
        self.run('"%s" -O1 -I%s -o check_api check_api.c -L%s -lscanmem'
                 % (cc, self._abs(dep.cpp_info.includedirs),
                    self._abs(dep.cpp_info.libdirs)))
        # check_libscanmem.c needs only the dynamic loader API;
        # scanmem_target.c is plain C. Neither links the package on purpose:
        # they are the run-time probes, while check_api carries the dependency.
        self.run('"%s" -O1 -o check_libscanmem check_libscanmem.c -ldl' % cc)
        self.run('"%s" -O1 -o scanmem_target scanmem_target.c' % cc)

    def test(self):
        # NOTE: deliberately NOT guarded by `if not can_run(self): return`.
        #
        # CI's L1e negative test re-runs `conan test <pkg> <ref> -pr <profile>`
        # with a *single* -pr. In Conan 2 that sets the host profile only, so
        # settings_build falls back to the machine default (Linux/x86_64)
        # while the host is OHOS/armv8. can_run() is defined as
        # `not cross_building(self)`, so it returns False there and a
        # `can_run` guard makes test() return *success without running
        # anything* -- which L1e correctly reports as
        # "test passed WITHOUT package artifacts - fake test detected (R34)".
        #
        # This executor is native aarch64 OHOS and the package's binaries do
        # run, so the test always executes. If a future executor genuinely
        # cannot run them, failing loudly is the correct outcome: R34 requires
        # a real executed test, and a silent skip would report success for
        # zero assertions.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        script = os.path.join(self.source_folder, "test_scanmem.sh")
        # cwd is build_folder, where build() already left check_api,
        # check_libscanmem and scanmem_target, so the script resolves them as
        # ./<name>. Nothing is copied into source_folder on purpose: that would
        # drop build artifacts inside archives/ and trip the CI junk-file gate.
        self.run('SCANMEM_PKG_ROOT="%s" "%s" "%s"'
                 % (self._dep().package_folder.replace("\\", "/"), bash, script),
                 cwd=self.build_folder, env="conanrun")
