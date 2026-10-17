#!/usr/bin/env python3
"""Consumer test for sdl/1.2.15.

Compiles test.c against the packaged SDL 1.2 library and runs a headless
end-to-end exercise of the real subsystems: SDL_Init(VIDEO|TIMER) with the
dummy video driver, SDL_SetVideoMode, surface fill + cross-surface blit,
SDL_Flip, and the timer subsystem (SDL_Delay/SDL_GetTicks).
"""
import os
import shutil
import tempfile

from conan import ConanFile
from conan.tools.build import can_run


class SdlTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        dep = self.dependencies["sdl"]
        cc = os.environ.get("CC", "/data/service/hnp/bin/clang")
        cmd = ['"%s" test.c -o sdl_consumer_test' % cc]
        for inc in dep.cpp_info.includedirs:
            cmd.append('-I"%s"' % inc)
        for libdir in dep.cpp_info.libdirs:
            cmd.append('-L"%s"' % libdir)
        for lib in dep.cpp_info.libs:
            cmd.append("-l%s" % lib)
        cmd.append("-lm -ldl -lpthread")
        self.run(" ".join(cmd))

    def test(self):
        if can_run(self):
            tmpdir = tempfile.mkdtemp(prefix="sdl-test-")
            try:
                self.run('SDL_VIDEODRIVER=dummy ./sdl_consumer_test "%s"' % tmpdir,
                         env="conanrun")
            finally:
                shutil.rmtree(tmpdir, ignore_errors=True)
