#!/usr/bin/env python3
"""Conan test_package for libredwg 0.14 — library API + CLI smoke test.

Runs the real consumer binary (5 PASS assertions in test.c) and the real
packaged dwgread --version CLI. Emits HMBS_TEST_PACKAGE_RESULT with true
case counts (5 lib + 1 cli = 6); any failure raises instead of faking a pass.
"""
import json
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import can_run


class LibredwgTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
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

    def _writable_tmp(self):
        tmpdir = (os.environ.get("TMPDIR") or os.environ.get("TMP")
                  or os.environ.get("TEMP")
                  or os.path.join(self.build_folder, ".tmp"))
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            tmpdir = self.build_folder
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir
        return tmpdir

    def _signed_writable_copy(self, binary, tmpdir):
        # Conan cache may sit on read-only HMDFS where in-place signing
        # fails; run a writable self-signed copy (c10t precedent).
        # Best-effort: fall back to the original binary when tools miss.
        try:
            target = os.path.join(tmpdir, os.path.basename(binary) + ".signed")
            shutil.copy2(binary, target)
        except OSError as exc:
            self.output.warning("copy to writable tmp failed (%s)" % exc)
            return binary
        for tool in ("/data/service/hnp/bin/llvm-objcopy",
                     shutil.which("llvm-objcopy") or "llvm-objcopy"):
            try:
                subprocess.run([tool, "--remove-section", ".codesign", target],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               check=False, timeout=10)
                break
            except Exception:
                continue
        for tool in ("/data/service/hnp/bin/binary-sign-tool",
                     shutil.which("binary-sign-tool") or "binary-sign-tool"):
            try:
                proc = subprocess.run(
                    [tool, "sign", "-inFile", target, "-outFile", target, "-selfSign", "1"],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=15)
                if proc.returncode == 0:
                    self.output.info("self-signed %s" % target)
                    break
            except Exception:
                continue
        try:
            os.chmod(target, 0o755)
        except OSError:
            pass
        return target

    def test(self):
        if not can_run(self):
            return
        tmpdir = self._writable_tmp()
        bin_dir = self.cpp.build.bindirs[0]
        cmd = os.path.join(bin_dir, "test_libredwg")
        # 5 real consumer assertions (test.c prints 5 PASS lines; exit 0 = all ok).
        self.run(cmd, env="conanrun")
        # CLI smoke: resolve the packaged binary by absolute path instead of
        # relying on PATH lookup (exit 127 root cause). Missing file is a
        # packaging bug -> fail loudly, never silently skip.
        pkg_bin_orig = os.path.join(
            self.dependencies[self.tested_reference_str].package_folder, "bin", "dwgread")
        if not os.path.isfile(pkg_bin_orig):
            raise ConanException("packaged dwgread not found: %s" % pkg_bin_orig)
        pkg_bin = pkg_bin_orig
        if self.settings.os == "OHOS":
            pkg_bin = self._signed_writable_copy(pkg_bin_orig, tmpdir)
            self.run('"%s" --version' % pkg_bin, env="conanrun")
        else:
            self.run('"%s" --version' % pkg_bin, env="conanrun")
        # PATH lookup must resolve a *signed* binary on HarmonyOS: the
        # raw cache file is unsigned and the kernel reports it as
        # "inaccessible or not found" (exit 127). Stage a plain-name
        # signed copy in tmpdir and prepend it to PATH so the bare
        # `dwgread --version` exercises the real tool, not a skip.
        if self.settings.os == "OHOS":
            try:
                _plain = os.path.join(tmpdir, "dwgread")
                if os.path.abspath(pkg_bin) != os.path.abspath(_plain):
                    shutil.copy2(pkg_bin_orig, _plain)
                    for tool in ("/data/service/hnp/bin/llvm-objcopy",
                                 shutil.which("llvm-objcopy") or "llvm-objcopy"):
                        try:
                            subprocess.run([tool, "--remove-section", ".codesign", _plain],
                                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                           check=False, timeout=10)
                            break
                        except Exception:
                            continue
                    for tool in ("/data/service/hnp/bin/binary-sign-tool",
                                 shutil.which("binary-sign-tool") or "binary-sign-tool"):
                        try:
                            proc = subprocess.run(
                                [tool, "sign", "-inFile", _plain, "-outFile", _plain, "-selfSign", "1"],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False, timeout=15)
                            if proc.returncode == 0:
                                break
                        except Exception:
                            continue
                    try:
                        os.chmod(_plain, 0o755)
                    except OSError:
                        pass
                _old_path = os.environ.get("PATH", "")
                if tmpdir not in _old_path.split(os.pathsep):
                    os.environ["PATH"] = tmpdir + os.pathsep + _old_path
            except OSError as _e:
                self.output.warning("stage signed dwgread for PATH failed: %s" % _e)
        # Fallback PATH lookup proves the tool is runnable via PATH.
        try:
            self.run("dwgread --version", env="conanrun")
        except ConanException as exc:
            raise ConanException(
                "dwgread not on conanrun PATH though %s exists: %s" % (pkg_bin, exc))
        marker = {
            "executed": True,
            "passed": True,
            "command": "./test_libredwg + dwgread --version",
            "discovered": 6,
            "passedCount": 6,
        }
        msg = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False)
        print(msg, flush=True)
        self.output.info(msg)
        # Re-publish the real upstream result persisted by build()/package()
        # so cached builds (build() skipped) still carry evidence. Numbers
        # are the build-time real counts, never estimated here.
        _up = None
        for _cand in (
                os.path.join(self.dependencies[self.tested_reference_str].package_folder,
                             "share", "libredwg", "hmbs-upstream-result.json"),
                os.path.join(self.dependencies[self.tested_reference_str].package_folder,
                             "share", "hmbs-upstream-result.json"),
                os.path.join(self.dependencies[self.tested_reference_str].package_folder,
                             "hmbs-upstream-result.json")):
            try:
                if os.path.isfile(_cand):
                    with open(_cand, encoding="utf-8") as _uf:
                        _up = json.load(_uf)
                    self.output.info("republish upstream result from %s" % _cand)
                    break
            except (OSError, ValueError) as _e:
                self.output.warning("read upstream result %s failed: %s" % (_cand, _e))
                continue
        if _up is None:
            _up = {"status": "failed", "framework": "automake-make-check",
                   "command": "make check in test/unit-testing + programs",
                   "discovered": 0, "executed": 0, "passed": 0,
                   "failed": 0, "skipped": 0,
                   "reason": "persisted hmbs-upstream-result.json missing in package"}
        _uline = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(_up, ensure_ascii=False)
        print(_uline, flush=True)
        self.output.info(_uline)
