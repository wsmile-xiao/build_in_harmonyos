#!/usr/bin/env python3
"""Conan test_package for audio-resampler 0.7 — real consumer verification.

Two real executables are compiled against the packaged headers + library:
- test_consumer: single-threaded fixed-ratio 44.1k->48k resample via the
  public resampleFixedRatioInit/resampleProcess API (observable output
  frame count + non-silent peak).
- test_ohos: HarmonyOS-specific test — multithreaded public-API resample
  (RESAMPLE_MULTITHREADED, pthread workers) asserting output_generated
  equals resampleGetExpectedOutput.

Both are actually executed through conan's self.run (conanrun env); a
non-zero exit aborts conan create (self.run raises by default).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class AudioResamplerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def _cc(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cand = (compilers.get("c") or "").strip()
        if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
        if cand:
            self.output.warning(
                "conf c compiler '%s' not usable, falling back to PATH lookup" % cand)
        return shutil.which("clang") or shutil.which("cc") or "clang"

    def build(self):
        inc = os.path.join(self.dependencies["audio-resampler"].package_folder, "include")
        lib = os.path.join(self.dependencies["audio-resampler"].package_folder, "lib")
        for name, src_name in (("test_consumer", "test_consumer.c"),
                               ("test_ohos", "test_ohos.c")):
            exe = os.path.join(self.build_folder, name)
            cmd = '"%s" -Wall -I"%s" "%s" -L"%s" -laudio-resampler -lm -pthread -o "%s"' % (
                self._cc(), inc, os.path.join(self.source_folder, src_name), lib, exe)
            self.run(cmd)
            self.output.info("%s built OK" % name)

    def test(self):
        if not can_run(self):
            self.output.info("cross build: skipping consumer run")
            return
        for name in ("test_consumer", "test_ohos"):
            test_bin = os.path.join(self.build_folder, name)
            try:
                os.chmod(test_bin, 0o755)
            except OSError:
                pass
            self.run('"%s"' % test_bin, env="conanrun")
            self.output.info("%s ran OK (exit 0)" % name)