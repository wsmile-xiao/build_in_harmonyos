#!/usr/bin/env python3
"""Conan recipe for audio-resampler 0.7 — OHOS (OpenHarmony) aarch64 adaptation.

Upstream: https://github.com/dbry/audio-resampler (tag 0.7)
Sinc-based audio resampling engine + ART command-line tool (BSD-3-Clause).

OHOS adaptations:
- The upstream Makefile is hardcoded for Intel gcc (`-mavx2`), which clang
  on aarch64 does not accept; this recipe drives the flat C source tree
  directly with the validated profile compiler (no -mavx2, no configure
  step — upstream ships no configure/install/check targets).
- The library modules (resampler/workers/biquad/decimator/extrapolator/
  stretch) are archived into libaudio-resampler.a so downstream consumers
  can link the public API; the upstream CLI tools art/art64 are built and
  packaged into bin/.
- Upstream test tools artest (32-bit path) and artest64 (64-bit path) are
  built and actually run (round-trip inverse-resample verification, diff
  RMS check); a real failure ("fatal error in resample results") aborts
  conan create.
"""
import glob as _glob
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.layout import basic_layout


class AudioResamplerConan(ConanFile):
    name = "audio-resampler"
    version = "0.7"
    description = "Sinc-based audio resampling engine and ART command-line tool"
    license = "BSD-3-Clause"
    homepage = "https://github.com/dbry/audio-resampler"
    url = "https://github.com/dbry/audio-resampler"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "audio-resampler is only supported on Linux/OHOS, not %s" % self.settings.os
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        self._ensure_writable_tmp()

    def _ensure_writable_tmp(self):
        # Device /tmp is read-only; clang spills temp files via $TMPDIR.
        # Ensure TMPDIR/TMP/TEMP all point at a writable dir (prefer the
        # injected value, else build_folder/tmp).
        import tempfile
        cand = (
            os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
        )
        ok = bool(cand) and os.path.isdir(cand) and os.access(cand, os.W_OK)
        if not ok:
            cand = os.path.join(self.build_folder, "tmp")
            try:
                os.makedirs(cand, exist_ok=True)
            except Exception:
                cand = tempfile.gettempdir()
        for k in ("TMPDIR", "TMP", "TEMP"):
            os.environ[k] = cand
        self.output.info("Using writable TMPDIR=%s" % cand)

    def _validated_cc(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cand = (compilers.get("c") or "").strip()
        if cand:
            if os.path.isfile(cand) and os.access(cand, os.X_OK):
                return cand
            self.output.warning(
                "conf c compiler '%s' not usable, falling back to PATH lookup" % cand)
        path_cc = shutil.which("clang") or shutil.which("cc") or "clang"
        self.output.info("Using C compiler from PATH: %s" % path_cc)
        return path_cc

    def _validated_ar(self):
        ar = shutil.which("llvm-ar") or shutil.which("ar") or "ar"
        self.output.info("Using archiver: %s" % ar)
        return ar

    def _run_cmd(self, cmd, cwd, extra_env=None):
        env = os.environ.copy()
        if extra_env:
            env.update(extra_env)
        self.output.info("+ %s" % cmd)
        proc = subprocess.run(
            cmd, shell=True, cwd=cwd,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, timeout=2400, env=env,
        )
        out = proc.stdout or ""
        if proc.returncode != 0:
            self.output.info(out[-8000:])
            raise ConanException(
                "command failed (rc=%s): %s\n%s" % (proc.returncode, cmd, out[-4000:]))
        return out

    def _smoke_test_cc(self, cc):
        # Trivial TU first so a genuinely broken toolchain shows its real
        # stderr here instead of a confusing downstream failure.
        work = os.path.join(self.build_folder, "cc-smoke")
        os.makedirs(work, exist_ok=True)
        src = os.path.join(work, "smoke.c")
        with open(src, "w") as f:
            f.write("int main(void){return 0;}\n")
        out = os.path.join(work, "smoke")
        self._run_cmd('"%s" "%s" -o "%s"' % (cc, src, out), cwd=work)
        self._run_cmd('"%s"' % out, cwd=work)
        self.output.info("C compiler smoke test passed: %s" % cc)

    def _obj_dir(self):
        d = os.path.join(self.build_folder, "objs")
        os.makedirs(d, exist_ok=True)
        return d

    def build(self):
        self._ensure_writable_tmp()
        cc = self._validated_cc()
        ar = self._validated_ar()
        self._smoke_test_cc(cc)
        objdir = self._obj_dir()
        src = self.source_folder
        opt = "-O3" if str(self.settings.build_type) == "Release" else "-O0 -g"
        base_flags = (
            "%s -fPIC -Wall -fno-signed-zeros -fno-trapping-math "
            "-fassociative-math -DENABLE_THREADS -DENABLE_EXTRAPOLATION -I\"%s\""
            % (opt, src)
        )

        # 1) Library objects + archive (resampler engine modules).
        lib_sources = [
            "resampler.c", "workers.c", "biquad.c", "decimator.c",
            "extrapolator.c", "stretch.c",
        ]
        objs = []
        for name in lib_sources:
            obj = os.path.join(objdir, name.replace(".c", ".o"))
            self._run_cmd(
                '"%s" %s -c "%s" -o "%s"' % (
                    cc, base_flags, os.path.join(src, name), obj),
                cwd=objdir)
            objs.append(obj)
        static_lib = os.path.join(objdir, "libaudio-resampler.a")
        self._run_cmd('"%s" rcs "%s" %s' % (
            ar, static_lib, " ".join('"%s"' % o for o in objs)), cwd=objdir)
        if self.options.shared:
            shared_lib = os.path.join(objdir, "libaudio-resampler.so")
            self._run_cmd(
                '"%s" -shared -fPIC -o "%s" %s -lm -pthread' % (
                    cc, shared_lib, " ".join('"%s"' % o for o in objs)),
                cwd=objdir)

        # 2) CLI tools: ART (32-bit) and ART64 (64-bit data path).
        tool_flags = base_flags + " -lm -pthread"
        for name, extra in (("art", ""), ("art64", "-DPATH_WIDTH=64")):
            self._run_cmd(
                '"%s" %s %s "%s" "%s" "%s" "%s" "%s" "%s" "%s" -o "%s"' % (
                    cc, extra, tool_flags,
                    os.path.join(src, "art.c"), os.path.join(src, "stretch.c"),
                    os.path.join(src, "resampler.c"), os.path.join(src, "extrapolator.c"),
                    os.path.join(src, "decimator.c"), os.path.join(src, "workers.c"),
                    os.path.join(src, "biquad.c"), os.path.join(objdir, name)),
                cwd=objdir)

        # 3) Upstream test tools + real runs (see _run_upstream_tests).
        self._run_upstream_tests(cc, tool_flags, src, objdir)

    def _run_upstream_tests(self, cc, tool_flags, src, objdir):
        """Build and run the upstream ARTEST verification tools.

        Upstream declares no ctest/meson/autotools test registry — the only
        test entry is artest.c compiled twice: artest (32-bit artsample_t)
        and artest64 (-DPATH_WIDTH=64). Each run performs a forward resample
        + inverse resample round trip on a synthesized 1 kHz tone and reports
        "fatal error in resample/inverse resample results" on mismatch; the
        residual diff RMS is printed (~-147 dB) as the correctness signal.
        """
        discovered = 2
        executed = 0
        passed = 0
        failed = 0
        details = []
        if not can_run(self):
            self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
                "status": "skipped", "framework": "direct-cc",
                "command": "artest/artest64 round-trip (-s44k -d48k -n3 -i -m -h)",
                "discovered": discovered, "executed": 0, "passed": 0,
                "failed": 0, "skipped": 2,
                "reason": "cross-building: test binaries cannot run on build host",
            }, ensure_ascii=False))
            return
        for name, extra in (("artest", ""), ("artest64", "-DPATH_WIDTH=64")):
            binpath = os.path.join(objdir, name)
            self._run_cmd(
                '"%s" %s %s "%s" "%s" "%s" "%s" "%s" "%s" -o "%s"' % (
                    cc, extra, tool_flags,
                    os.path.join(src, "artest.c"), os.path.join(src, "resampler.c"),
                    os.path.join(src, "extrapolator.c"), os.path.join(src, "decimator.c"),
                    os.path.join(src, "workers.c"), os.path.join(src, "biquad.c"),
                    binpath),
                cwd=objdir)
            proc = subprocess.run(
                '"%s" -s44k -d48k -n3 -i -m -h' % binpath, shell=True, cwd=objdir,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, timeout=2400, env=os.environ.copy())
            out = proc.stdout or ""
            executed += 1
            fatal = "fatal error" in out.lower()
            ok = proc.returncode == 0 and not fatal
            self.output.info(
                "--- %s (rc=%s, fatal=%s) ---\n%s" % (name, proc.returncode, fatal, out[-3000:]))
            details.append("%s:rc=%s" % (name, proc.returncode))
            if ok:
                passed += 1
            else:
                failed += 1
        status = "passed" if (failed == 0 and executed == 2) else "failed"
        result = {
            "status": status, "framework": "direct-cc",
            "command": "artest/artest64 -s44k -d48k -n3 -i -m -h (%s)" % ";".join(details),
            "discovered": discovered, "executed": executed,
            "passed": passed, "failed": failed, "skipped": 0,
        }
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result))
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result, ensure_ascii=False))
        if status != "passed":
            raise ConanException("audio-resampler upstream tests failed: %s" % result)

    def package(self):
        headers = ["resampler.h", "workers.h", "biquad.h", "decimator.h",
                   "extrapolator.h", "stretch.h"]
        for h in headers:
            copy(self, h, src=self.source_folder, dst=os.path.join(self.package_folder, "include"))
        objdir = os.path.join(self.build_folder, "objs")
        copy(self, "libaudio-resampler.a", src=objdir, dst=os.path.join(self.package_folder, "lib"))
        if self.options.shared:
            for pat in ("libaudio-resampler.so*",):
                for f in _glob.glob(os.path.join(objdir, pat)):
                    copy(self, os.path.basename(f), src=objdir, dst=os.path.join(self.package_folder, "lib"))
        for tool in ("art", "art64"):
            copy(self, tool, src=objdir, dst=os.path.join(self.package_folder, "bin"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = ["audio-resampler"]
        self.cpp_info.system_libs = ["m", "pthread"]
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bindir):
            self.runenv_info.prepend_path("PATH", bindir)
