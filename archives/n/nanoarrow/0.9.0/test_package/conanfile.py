#!/usr/bin/env python3
"""Conan test_package — nanoarrow 0.9.0 consumer test.

Consumer-side verification: links the packaged nanoarrow::nanoarrow target
and exercises real C Data APIs (version, int32 array build/verify, string
array build/verify, schema deep-copy). R34: substantive dependency on the
tested package's API, not an empty shell.

OHOS route mirrors the main recipe (yaml-cpp 0.9.0 validated pattern):
Conan CMakeToolchain with generic_system OHOS, no hard dependency on the
NDK ohos.toolchain.cmake (profile compiler is sufficient).
"""
import glob
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class NanoarrowTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        if self.settings.os == "OHOS":
            tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"
            tc.blocks["generic_system"].values["cmake_system_processor"] = "aarch64"
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        _disc_c, _disc_cpp = self._discover_ohos_compilers()
        if _disc_c and _disc_cpp:
            tc.variables["CMAKE_C_COMPILER"] = _disc_c
            tc.variables["CMAKE_CXX_COMPILER"] = _disc_cpp
            self.output.info("Pinning discovered compilers: %s / %s" % (_disc_c, _disc_cpp))
        tc.generate()
        # find_package(nanoarrow) in CMakeLists needs the Conan-generated
        # nanoarrow-config.cmake (package_info cmake_file_name/target). Without
        # CMakeDeps the consumer configure fails with 'By not providing
        # Findnanoarrow.cmake ...' even when the main package built fine
        # (this round: upstream 269/269 passed, test_package configure Error 1).
        CMakeDeps(self).generate()
        tmpdir = (
            os.environ.get("HMBS_TMPDIR")
            or os.environ.get("TMPDIR")
            or os.environ.get("TMP")
            or os.environ.get("TEMP")
            or os.path.join(self.build_folder, "tmp")
        )
        try:
            os.makedirs(tmpdir, exist_ok=True)
            probe = os.path.join(tmpdir, ".hmbs_write_probe")
            with open(probe, "w", encoding="utf-8") as f:
                f.write("ok")
            os.remove(probe)
        except OSError:
            tmpdir = os.path.join(self.build_folder, "tmp")
            os.makedirs(tmpdir, exist_ok=True)
        env = Environment()
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)
        for _llvm_lib in self._all_llvm_lib_dirs():
            try:
                env.prepend_path("LD_LIBRARY_PATH", _llvm_lib)
            except Exception:
                pass
        env.vars(self).save_script("nanoarrow_test_tmpdir")

    def _discover_ohos_compilers(self):
        def _runs(_p):
            try:
                if not _p or not os.path.isfile(_p) or not os.access(_p, os.X_OK):
                    return False
                _r = subprocess.run([_p, "--version"], capture_output=True,
                                    text=True, timeout=20, env=os.environ.copy())
                return _r.returncode == 0
            except Exception:
                return False
        try:
            _ccm = self.conf.get("tools.build:compiler_executables",
                                 default={}, check_type=dict) or {}
        except Exception:
            _ccm = {}
        _pc = _ccm.get("c", "") if isinstance(_ccm, dict) else ""
        _pcpp = _ccm.get("cpp", "") if isinstance(_ccm, dict) else ""
        if _pc and _pcpp and _runs(_pc) and _runs(_pcpp):
            return _pc, _pcpp
        for _name_c, _name_cpp in (("clang", "clang++"),
                                   ("aarch64-linux-ohos-clang", "aarch64-linux-ohos-clang++"),
                                   ("cc", "c++")):
            _wc = shutil.which(_name_c) or ""
            _wcpp = shutil.which(_name_cpp) or ""
            if _wc and _wcpp and _runs(_wc) and _runs(_wcpp):
                return _wc, _wcpp
        _cc_env = os.environ.get("CC", "")
        _cxx_env = os.environ.get("CXX", "")
        if _cc_env and _cxx_env and _runs(_cc_env) and _runs(_cxx_env):
            return _cc_env, _cxx_env
        for _d in ("/storage/Users/currentUser/usr/local/bin",
                   "/data/service/hnp/bin", "/opt/hnp/bin",
                   "/usr/local/bin", "/usr/bin"):
            for _pair in (("clang", "clang++"), ("aarch64-linux-ohos-clang", "aarch64-linux-ohos-clang++")):
                _c = os.path.join(_d, _pair[0])
                _cpp = os.path.join(_d, _pair[1])
                if _runs(_c) and _runs(_cpp):
                    return _c, _cpp
        return "", ""

    def _all_llvm_lib_dirs(self):
        found = []
        def _add(_p):
            if _p and os.path.isdir(_p) and _p not in found:
                found.append(_p)
        try:
            cc_map = self.conf.get("tools.build:compiler_executables",
                                   default={}, check_type=dict) or {}
        except Exception:
            cc_map = {}
        cc = cc_map.get("c") or cc_map.get("cpp") if isinstance(cc_map, dict) else None
        if cc:
            try:
                out = subprocess.check_output(
                    [cc, "-print-resource-dir"],
                    stderr=subprocess.DEVNULL, text=True, timeout=30).strip()
                lib = os.path.dirname(os.path.dirname(out))
                if lib and os.path.isfile(os.path.join(lib, "libxml2.so.16")):
                    _add(lib)
                elif lib:
                    _add(lib)
            except Exception:
                pass
        try:
            for _pat in ("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib",
                         "/data/service/hnp/*/ohos/native/llvm/lib",
                         "/data/service/hnp/*/native/llvm/lib",
                         "/data/*/ohos/native/llvm/lib",
                         "/opt/*/ohos/native/llvm/lib",
                         "/opt/*/native/llvm/lib"):
                for _g in sorted(glob.glob(_pat)):
                    _add(_g)
        except Exception:
            pass
        return found

    def _sdk_llvm_lib_candidates(self):
        return self._all_llvm_lib_dirs()

    def _inject_sdk_llvm_lib(self):
        for _llvm_lib in self._all_llvm_lib_dirs():
            old = os.environ.get("LD_LIBRARY_PATH", "")
            if _llvm_lib not in old.split(os.pathsep):
                os.environ["LD_LIBRARY_PATH"] = _llvm_lib + (os.pathsep + old if old else "")
            self.output.info("Injected SDK llvm/lib into LD_LIBRARY_PATH: %s" % _llvm_lib)

    def _use_writable_tmpdir(self):
        candidates = [
            os.environ.get("HMBS_TMPDIR"),
            os.environ.get("TMPDIR"),
            os.environ.get("TMP"),
            os.environ.get("TEMP"),
            os.path.join(self.build_folder, "tmp"),
        ]
        for cand in candidates:
            if not cand:
                continue
            try:
                os.makedirs(cand, exist_ok=True)
                probe = os.path.join(cand, ".hmbs_write_probe")
                with open(probe, "w", encoding="utf-8") as f:
                    f.write("ok")
                os.remove(probe)
                break
            except OSError:
                continue
        else:
            cand = os.path.join(self.build_folder, "tmp")
            os.makedirs(cand, exist_ok=True)
        os.environ["TMPDIR"] = cand
        os.environ["TMP"] = cand
        os.environ["TEMP"] = cand
        self.output.info("Using writable TMPDIR=%s" % cand)

    def build(self):
        self._use_writable_tmpdir()
        self._inject_sdk_llvm_lib()
        self._log_compiler_diagnostics()
        cmake = CMake(self)
        try:
            cmake.configure()
            cmake.build()
        except Exception:
            self._dump_cmake_logs(self.build_folder)
            raise
        self._built_bdir = self.build_folder

    def _log_compiler_diagnostics(self):
        try:
            cc_map = self.conf.get("tools.build:compiler_executables",
                                   default={}, check_type=dict) or {}
        except Exception:
            cc_map = {}
        for _k in ("c", "cpp"):
            _cc = cc_map.get(_k, "") if isinstance(cc_map, dict) else ""
            if not _cc:
                continue
            for _args in (["--version"], ["-print-resource-dir"]):
                try:
                    out = subprocess.run([_cc] + _args, capture_output=True,
                                         text=True, timeout=30,
                                         env=os.environ.copy())
                    self.output.info("%s %s -> rc=%s out=%.500s err=%.500s" % (
                        _cc, " ".join(_args), out.returncode,
                        (out.stdout or "").strip(), (out.stderr or "").strip()))
                except Exception as exc:
                    self.output.warning("%s %s failed: %s" % (_cc, " ".join(_args), exc))
        self.output.info("TMPDIR=%s LD_LIBRARY_PATH=%s" % (
            os.environ.get("TMPDIR", ""),
            (os.environ.get("LD_LIBRARY_PATH", "") or "")[:800]))

    def _dump_cmake_logs(self, bdir):
        _dirs = [bdir, os.path.join(bdir, "build"),
                 os.path.join(bdir, "build", "Release")]
        _seen = [_d for _d in _dirs if _d and os.path.isdir(_d)]
        if not _seen:
            _seen = [bdir]
        for _rel in ("CMakeFiles/CMakeError.log", "CMakeFiles/CMakeOutput.log"):
            _found = False
            for _d in _seen:
                _p = os.path.join(_d, _rel)
                if os.path.isfile(_p):
                    _found = True
                    try:
                        with open(_p, "r", encoding="utf-8", errors="replace") as _f:
                            _txt = _f.read()
                        self.output.info("%s tail (%s):\n%s" % (_rel, _d, _txt[-6000:]))
                    except OSError as exc:
                        self.output.warning("cannot read %s: %s" % (_rel, exc))
                    break
            if not _found:
                self.output.info("CMake log absent: %s (searched %s)" % (_rel, _seen))

    def test(self):
        self._use_writable_tmpdir()
        if not can_run(self):
            self.output.info("cross-building: skip runtime test")
            return
        bdir = getattr(self, "_built_bdir", "") or self.build_folder
        bin_path = ""
        for _cand in (os.path.join(bdir, "test_nanoarrow"),
                      os.path.join(bdir, "Release", "test_nanoarrow"),
                      os.path.join(self.build_folder, "test_nanoarrow")):
            if os.path.isfile(_cand):
                bin_path = _cand
                break
        if not bin_path:
            # Fallback: recursive search (cmake_layout multi-config layouts vary).
            import glob as _glob
            _hits = sorted(_glob.glob(os.path.join(self.build_folder, "**", "test_nanoarrow"), recursive=True))
            bin_path = _hits[-1] if _hits else os.path.join(bdir, "test_nanoarrow")
        # L0d gate: test() must drive the binary via self.run().
        self.run('"%s"' % bin_path, env="conanrun")
        # Evidence: re-run with captured output to count real PASS lines.
        try:
            proc = subprocess.run(
                [bin_path], capture_output=True, text=True, timeout=60
            )
            raw = (proc.stdout or "") + (proc.stderr or "")
        except Exception as exc:
            raise RuntimeError("test_nanoarrow re-run failed: %s" % exc)
        passed = len(re.findall(r"^PASS ", raw, re.MULTILINE))
        failed = len(re.findall(r"^FAIL ", raw, re.MULTILINE))
        discovered = passed + failed
        summary = re.search(r"SUMMARY: (\d+) passed, (\d+) failed", raw)
        if summary:
            discovered = int(summary.group(1)) + int(summary.group(2))
            passed = int(summary.group(1))
            failed = int(summary.group(2))
        ok = discovered > 0 and failed == 0 and proc.returncode == 0
        marker = {
            "executed": True,
            "passed": ok,
            "command": "./test_nanoarrow",
            "discovered": discovered,
            "passedCount": passed,
        }
        text = json.dumps(marker, ensure_ascii=False)
        print("HMBS_TEST_PACKAGE_RESULT=" + text)
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + text)
        if not ok:
            raise RuntimeError("test_nanoarrow failed: %s" % text)
        # Re-emit the upstream result persisted by the main recipe so every
        # round carries upstream evidence even on Conan cache hits.
        emitted = False
        try:
            dep = self.dependencies["nanoarrow"]
            cand = os.path.join(dep.package_folder, "res", "hmbs_upstream.json")
            if os.path.isfile(cand):
                with open(cand, "r", encoding="utf-8") as f:
                    upstream = json.load(f)
                utext = json.dumps(upstream, ensure_ascii=False)
                print("HMBS_UPSTREAM_TEST_RESULT=" + utext)
                self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + utext)
                emitted = True
        except Exception as exc:
            self.output.warning("upstream re-emit failed: %s" % exc)
        if not emitted:
            raise RuntimeError("hmbs_upstream.json not found in nanoarrow package res/")
