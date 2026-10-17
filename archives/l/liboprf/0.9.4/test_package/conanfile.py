#!/usr/bin/env python3
"""Conan test_package for liboprf 0.9.4.

Compiles test_oprf.c against the packaged libraries (liboprf +
liboprf-noiseXK plus the vendored libsodium shipped in the same package)
and runs it. The binary performs two real OPRF round-trips and prints one
CHECK-OK line per check; the marker counts those lines so the numbers come
from the actual test output. A second self.run() under the conanrun
environment proves the binary also executes through the standard consumer
run environment (cyrus-sasl-login precedent).
"""
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException

CONSUMER_CHECK_COUNT = 2


class LiboprfTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _resolve_cc(self):
        # PATH-first probing (same policy as the main recipe): the profile
        # absolute hnp path is only trusted after --version proves it runs.
        # Prevents Error 127 on runners where the baked path is missing.
        import shutil as _shutil
        import subprocess as _sp
        cands = []
        try:
            conf_cc = self.conf.get("tools.build:compiler_executables:c", check_type=str)
        except Exception:
            conf_cc = None
        if conf_cc:
            cands.append(conf_cc)
        for name in ("cc", "clang"):
            try:
                found = _shutil.which(name)
            except Exception:
                found = None
            if found and found not in cands:
                cands.append(found)
        for fb in ("cc", "clang"):
            if fb not in cands:
                cands.append(fb)
        for cand in cands:
            try:
                p = _sp.run([cand, "--version"], stdout=_sp.PIPE,
                            stderr=_sp.STDOUT, timeout=30)
                if p.returncode == 0:
                    self.output.info("test_package selected cc=%s" % cand)
                    return cand
                self.output.info("test_package cc unusable: %s exit=%d" % (cand, p.returncode))
            except Exception as exc:
                self.output.info("test_package cc unusable: %s: %s" % (cand, exc))
        return cands[0] if cands else "clang"

    def _exe_dir(self):
        """Directory proven executable for the test binary.

        Prior rounds proved two locations non-executable with EPERM: the
        synced code-tree output (.../liboprf-0.9.4/test_package/test_oprf)
        and the HMBS runtime TMPDIR copy (.../runtime/.../tmp/test_oprf_run)
        -- the latter EPERM also shows a Python copyfile loses the compiler
        -set exec bit and chmod=0 cannot restore it. The upstream suite
        (dkg/tv1/... built under conan-home/p/b/.../build-release) executes
        fine, so prefer the Conan cache base build dir, which shares that
        mount. Falls back to build_folder only when unavailable.
        """
        try:
            base = getattr(self, "base_build_folder", None)
            if base and os.path.isdir(str(base)):
                if os.path.abspath(str(base)) != os.path.abspath(str(self.build_folder)):
                    self.output.info("test_package exe dir: base_build_folder=%s" % base)
                    return str(base)
        except Exception as exc:
            self.output.info("exe dir probe skipped: %s" % exc)
        return str(self.build_folder)

    def _exe_candidates(self):
        seen = []
        for d in (self._exe_dir(), str(self.build_folder)):
            if d and d not in seen:
                seen.append(d)
        return [os.path.join(d, "test_oprf") for d in seen]

    def build(self):
        # R33: compiler from Conan conf, never ${CC}/${CFLAGS} in self.run().
        cc = self._resolve_cc()
        pkg = self.dependencies["liboprf"]
        # cpp_info include/lib dirs cover both liboprf and the vendored
        # sodium headers/libs shipped in the same package (no external
        # libsodium requires).
        includes = list(pkg.cpp_info.includedirs)
        libdirs = list(pkg.cpp_info.libdirs)
        src = os.path.join(self.source_folder, "test_oprf.c")
        out = os.path.join(self._exe_dir(), "test_oprf")
        try:
            os.makedirs(os.path.dirname(out), exist_ok=True)
        except OSError:
            pass
        self.output.info("test_package output: %s" % out)
        cmd = '"%s" -O2 -o "%s" "%s"' % (cc, out, src)
        for inc in includes:
            cmd += ' -I"%s"' % inc
        # Prefer explicit static archives by absolute path when the package
        # carries them (shared=False default). Linking `-loprf` would prefer
        # any lingering liboprf.so, and the OHOS loader ignores
        # LD_LIBRARY_PATH, so the test fell back to a stale system
        # liboprf.so.0 ("symbol not found", rc=127). Absolute .a paths
        # remove the runtime dependency entirely; shared packages fall back
        # to -L/-l below and rely on LD_PRELOAD in _run_env().
        static_libs = []
        try:
            base = str(pkg.package_folder)
            for libname in ("liboprf.a", "liboprf-noiseXK.a", "libsodium.a"):
                found = None
                for entry in libdirs:
                    cand = entry if os.path.isabs(entry) else os.path.join(base, entry)
                    cand = os.path.join(cand, libname)
                    if os.path.isfile(cand):
                        found = cand
                        break
                if found:
                    static_libs.append(found)
        except Exception as exc:
            self.output.warning("static lib probe failed: %s" % exc)
            static_libs = []
        if len(static_libs) == 3:
            for lib in static_libs:
                cmd += ' "%s"' % lib
            self.output.info("test_package linking static archives: %s" % "; ".join(static_libs))
        else:
            for lib in libdirs:
                cmd += ' -L"%s"' % lib
            cmd += " -loprf -loprf-noiseXK -lsodium"
            self.output.info("test_package static archives incomplete, using -l fallback")
        self.run(cmd, env="conanbuild")
        # HMDFS reports chmod=0: best-effort +x so the next test() exec does
        # not hit EPERM when the mode is preserved as 644. Failure is only
        # logged; test() stages to TMPDIR as the real fallback.
        try:
            if os.path.isfile(out):
                os.chmod(out, 0o755)
                self.output.info("[ok] chmod +x test binary (best effort)")
        except Exception as exc:
            self.output.info("chmod test binary skipped: %s" % exc)
        self._sign_ohos_binary(out)

    def _sign_ohos_binary(self, path):
        """Self-sign the freshly linked test ELF for HarmonyOS exec policy.

        Strategy-cycle note: three consecutive rounds assumed a Unix
        mode/location cause (static link, TMPDIR copy, cache-dir output) and
        all failed the same way -- direct exec AND the alternate candidate
        both raised EPERM (PermissionError Errno 1), including the Conan
        cache candidate, while HMBS reports chmod=0 (chmod is a no-op).
        A location/mode cause cannot explain EPERM on every candidate path.
        Per knowledge/DRAFT-cronutils-1.1-raw-makefile-ohos-cli-signing
        (VERIFIED): the HongMeng kernel refuses to execute ELF files without
        a valid .codesign section, and chmod 755 is explicitly NOT sufficient
        (cronutils: "not a plain Unix exec-bit problem"). The remedy is the
        same binary-sign-tool self-sign flow cronutils applies to final OHOS
        ELFs, applied here to the test binary right after linking. The
        signature travels inside the file, so the exec location no longer
        matters. Probe order (conf -> env -> PATH -> worker convention path)
        and the objcopy-then-sign-to-temp-then-replace sequence mirror the
        cronutils recipe; test assertions and the marker caliber are
        untouched.
        """
        try:
            os_label = str(self.settings.os)
        except Exception:
            os_label = ""
        try:
            conf_tool = self.conf.get("user.ohos:sign_tool", default="", check_type=str)
        except Exception:
            conf_tool = ""
        try:
            conf_objcopy = self.conf.get("user.ohos:objcopy", default="", check_type=str)
        except Exception:
            conf_objcopy = ""
        signer = (conf_tool or os.environ.get("OHOS_SIGN_TOOL", "")
                  or shutil.which("binary-sign-tool") or "")
        fallback = "/data/service/hnp/bin/binary-sign-tool"
        if not signer and os_label == "OHOS":
            signer = fallback
        self.output.info("ohos sign probe: os=%s signer=%s" % (os_label, signer or "<none>"))
        if not signer or not os.path.isfile(signer):
            self.output.warning(
                "binary-sign-tool unavailable; skipping OHOS ELF signing, "
                "exec may still hit kernel EPERM")
            return
        objcopy = (conf_objcopy or os.environ.get("OHOS_OBJCOPY", "")
                   or shutil.which("llvm-objcopy")
                   or "/data/service/hnp/bin/llvm-objcopy")
        if objcopy and os.path.isfile(objcopy):
            self.run('"%s" --remove-section .codesign "%s"' % (objcopy, path),
                     ignore_errors=True)
        else:
            self.output.info("llvm-objcopy unavailable; signing over existing sections")
        signed = path + ".signed"
        self.run('"%s" sign -inFile "%s" -outFile "%s" -selfSign 1'
                 % (signer, path, signed))
        if not os.path.isfile(signed):
            raise ConanException("binary-sign-tool produced no output for %s" % path)
        os.replace(signed, path)
        try:
            os.chmod(path, 0o755)
        except Exception as exc:
            self.output.info("chmod signed binary skipped: %s" % exc)
        self._log_codesign(path)
        self.output.info("[ok] OHOS self-signed test binary: %s" % path)

    def _log_codesign(self, path):
        """Best-effort evidence: report whether .codesign section exists."""
        readelf = (shutil.which("llvm-readelf")
                   or "/data/service/hnp/bin/llvm-readelf")
        if not readelf or not os.path.isfile(readelf):
            self.output.info("codesign check skipped (no llvm-readelf)")
            return
        try:
            proc = subprocess.run(
                [readelf, "-S", path], stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, timeout=60)
            out = proc.stdout or ""
            hit = "codesign" in out.lower()
            self.output.info("codesign section present=%s (readelf exit=%d)"
                             % (hit, proc.returncode))
            if not hit:
                self.output.warning("signed binary has no .codesign section: %s" % path)
        except Exception as exc:
            self.output.info("codesign check failed: %s" % exc)

    def _run_env(self):
        """Process environment with every dependency lib dir on LD_LIBRARY_PATH."""
        env = dict(os.environ)
        # HMBS injects a writable TMPDIR (device /tmp is read-only erofs);
        # propagate it so the test process never touches read-only /tmp.
        tmpd = env.get("TMPDIR") or env.get("TMP") or env.get("TEMP")
        if tmpd:
            env["TMPDIR"] = tmpd
            env["TMP"] = tmpd
            env["TEMP"] = tmpd
        lib_dirs = []
        for _ref, dep in self.dependencies.items():
            try:
                folders = dep.cpp_info.libdirs
                base = str(dep.package_folder)
            except Exception:
                continue
            for entry in folders:
                lib_dirs.append(entry if os.path.isabs(entry) else os.path.join(base, entry))
        if lib_dirs:
            prev = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = os.pathsep.join(lib_dirs + ([prev] if prev else []))
        # OHOS loader ignores LD_LIBRARY_PATH (stale_runtime_library); point
        # LD_PRELOAD at this build's shared objects only when they exist.
        # Static-only packages (shared=False default) have no .so, so no
        # PRELOAD is set and the statically linked binary needs nothing.
        try:
            import glob as _glob
            preload = []
            for d in lib_dirs:
                for pat in (os.path.join(d, "liboprf.so*"),
                            os.path.join(d, "liboprf-noiseXK.so*")):
                    try:
                        hits = _glob.glob(pat)
                    except Exception:
                        hits = []
                    for h in hits:
                        if os.path.isfile(h) and h not in preload:
                            preload.append(h)
            if preload:
                prev_pre = env.get("LD_PRELOAD", "")
                env["LD_PRELOAD"] = os.pathsep.join(preload + ([prev_pre] if prev_pre else []))
                self.output.info("test_package LD_PRELOAD=%s" % env["LD_PRELOAD"])
        except Exception as exc:
            self.output.warning("LD_PRELOAD probe failed: %s" % exc)
        return env

    def _reemit_upstream_result(self):
        # Cache-hit rounds skip build(), so the upstream marker emitted
        # there never appears. Re-emit the exact persisted result produced
        # by build(). No re-computation here; missing file only warns,
        # never fakes a pass.
        try:
            dep = self.dependencies["liboprf"]
            pkg = dep.package_folder
        except Exception as exc:
            self.output.warning("upstream re-emit unavailable (no dep): %s" % exc)
            return
        cands = [
            os.path.join(pkg, "share", "liboprf", "hmbs_upstream_result.json"),
            os.path.join(pkg, "share", "hmbs_upstream_result.json"),
        ]
        path = next((p for p in cands if os.path.isfile(p)), None)
        if not path:
            self.output.warning("upstream result file missing in package; not re-emitting")
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            self.output.warning("cannot read upstream result %s: %s" % (path, exc))
            return
        try:
            line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(data, ensure_ascii=False)
        except Exception as exc:
            self.output.warning("cannot encode upstream result: %s" % exc)
            return
        self.output.info(line)
        print(line)

    def _run_test_exe(self, exe):
        """Run exe, trying alternate candidate paths on EPERM/missing."""
        try:
            return subprocess.run(
                [exe], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, timeout=300, env=self._run_env())
        except (PermissionError, FileNotFoundError, OSError) as exc:
            self.output.info("exec failed, trying alternates: %s: %s" % (exe, exc))
            for cand in self._exe_candidates():
                if cand == exe or not os.path.isfile(cand):
                    continue
                self.output.info("retry exec at %s" % cand)
                return subprocess.run(
                    [cand], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, timeout=300, env=self._run_env())
            raise

    def test(self):
        exe = next((c for c in self._exe_candidates() if os.path.isfile(c)), None)
        if not exe:
            raise ConanException(
                "test binary missing, tried: %s" % "; ".join(self._exe_candidates()))
        self.output.info("test_package exec: %s" % exe)
        proc = self._run_test_exe(exe)
        output = proc.stdout or ""
        self.output.info(output[-2000:])
        ok_count = output.count("CHECK-OK:")
        marker = {
            "executed": True,
            "passed": proc.returncode == 0 and ok_count == CONSUMER_CHECK_COUNT,
            "command": exe,
            "discovered": CONSUMER_CHECK_COUNT,
            "passedCount": ok_count,
        }
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
        if not marker["passed"]:
            raise ConanException(
                "consumer test failed: rc=%s ok=%s/%s" % (
                    proc.returncode, ok_count, CONSUMER_CHECK_COUNT))
        # Prove the binary also executes under the standard consumer run env.
        self.run('"%s"' % exe, env="conanrun")
        self.output.info("liboprf consumer test_package passed")
        self._reemit_upstream_result()
