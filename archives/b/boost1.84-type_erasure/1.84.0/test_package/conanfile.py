#!/usr/bin/env python3
"""Conan test_package — boost1.84-type_erasure 1.84.0 L1 smoke test.

Direct-compile consumer test (no CMake): the CMake compiler check
(project()/try-compile) fails on OHOS workers with "is not able to compile
a simple test program" even though the compiler itself works — the recipe's
manual clang++ invocations build the library and all 60 upstream tests, and
adding CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY did not change the
failure. So the consumer is compiled with the same manual clang++ driver
and flags proven by the recipe's upstream-test run, then executed.
Same test source, same 10 assertions, same library linkage — only the
driver changes from CMake to direct clang++. Same approach as the merged
archives/b/baitfisher test_package and the docs/ADAPTATION_GUIDE.md
section 5 test_package template.
"""
import json
import os
import shutil
import subprocess

from conan import ConanFile


class BoostTypeErasureTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _writable_tmpdir(self):
        for var in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
            v = os.environ.get(var)
            if v and v != "0" and v != "/tmp":
                try:
                    os.makedirs(v, exist_ok=True)
                except OSError:
                    pass
                return v
        v = os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK")
        if v and v != "0" and v != "/tmp":
            try:
                os.makedirs(v, exist_ok=True)
            except OSError:
                pass
            if v:
                return v
        base = self.build_folder or os.getcwd()
        cand = os.path.join(base, "tmp_hmbs")
        try:
            os.makedirs(cand, exist_ok=True)
        except OSError:
            return base
        return cand

    def _cxx(self):
        # R33: compiler from Conan conf, never ${CXX} (same rule as the
        # main recipe and the merged baitfisher test_package).
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}) or {}
        candidates = []
        v = compilers.get("cpp")
        if v:
            candidates.append(v)
        ev = os.environ.get("CXX")
        if ev:
            candidates.append(ev.split()[0])
        w = shutil.which("clang++")
        if w:
            candidates.append(w)
        candidates.append("clang++")
        candidates.extend(("/data/service/hnp/bin/clang++",
                           "/storage/Users/currentUser/usr/local/bin/clang++"))
        for cand in candidates:
            if not cand:
                continue
            cand = cand.strip().strip('"').strip("'")
            if not cand:
                continue
            if os.path.isabs(cand):
                if os.path.isfile(cand) and os.access(cand, os.X_OK):
                    return cand
                continue
            w = shutil.which(cand)
            if w and os.path.isfile(w) and os.access(w, os.X_OK):
                return w
        return compilers.get("cpp") or "clang++"

    def _find_libcxx_dir(self):
        """Locate the SDK libc++_shared.so directory via compiler introspection.

        Same approach as the main recipe: no hardcoded SDK version path.
        Used as a runtime LD_LIBRARY_PATH fallback next to the static
        libc++ link flag (mirrors the merged boost1.84-contract setup).
        """
        cxx = self._cxx()
        try:
            out = subprocess.check_output(
                [cxx, "-print-file-name=libc++_shared.so"],
                text=True).strip()
        except Exception as exc:  # noqa: BLE001 - introspection failure is reported below
            self.output.warning(f"libc++_shared.so introspection failed: {exc}")
            return None
        if not out or out == "libc++_shared.so":
            return None
        return os.path.dirname(out)

    def _setup_env(self):
        """Writable tmp + SDK runtime path for direct compiler invocations."""
        tmpdir = self._writable_tmpdir()
        for k in ("TMPDIR", "TMP", "TEMP", "HMBS_TMPDIR"):
            os.environ[k] = tmpdir
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        libcxx_dir = self._find_libcxx_dir()
        if libcxx_dir:
            # OHOS musl loader fails on blank LD_LIBRARY_PATH entries, so
            # every entry is stripped and empties are dropped.
            prev = os.environ.get("LD_LIBRARY_PATH", "")
            parts = [libcxx_dir] + [p.strip() for p in prev.split(":")]
            cleaned = ":".join(p for p in parts if p.strip())
            os.environ["LD_LIBRARY_PATH"] = cleaned
            self.output.info(f"[HMBS tmp] LD_LIBRARY_PATH={cleaned}")
        self.output.info(f"[HMBS tmp] TMPDIR={tmpdir}")
        return tmpdir

    def _test_dependency(self):
        for _, dep in self.dependencies.items():
            try:
                if dep.ref.name == "boost1.84-type_erasure":
                    return dep
            except Exception:
                continue
        for _, dep in self.dependencies.items():
            return dep
        return None

    def _compile_cmd(self, dep):
        cxx = self._cxx()
        if self.settings.build_type == "Debug":
            opt = "-O0 -g"
        else:
            opt = "-O2 -DNDEBUG"
        include_dir = os.path.join(dep.package_folder, "include")
        lib_file = os.path.join(dep.package_folder, "lib",
                                "libboost_type_erasure.a")
        src = os.path.join(self.source_folder, "test_boost_type_erasure.cpp")
        out = os.path.join(self.build_folder, "test_boost_type_erasure")
        if not os.path.isfile(src):
            from conan.errors import ConanException
            raise ConanException(f"test source missing: {src}")
        if not os.path.isfile(lib_file):
            from conan.errors import ConanException
            raise ConanException(f"packaged library missing: {lib_file}")
        # Same proven flags as the recipe build(): C++17 + libc++ +
        # pthread, package defines (incl. the headers-component macro),
        # static libc++ link so the binary runs without extra search paths.
        cmd = (f'"{cxx}" -std=c++17 -stdlib=libc++ -pthread {opt} -fPIC '
               f'-I"{include_dir}" -DBOOST_ALL_NO_LIB '
               f'-DBOOST_TYPE_ERASURE_NO_LIB '
               f'-DBOOST_TYPE_ERASURE_STATIC_LINK '
               f'-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE '
               f'"{src}" "{lib_file}" -static-libstdc++ -o "{out}"')
        return cmd, out

    def build(self):
        self._setup_env()
        dep = self._test_dependency()
        if dep is None:
            from conan.errors import ConanException
            raise ConanException("tested dependency not found")
        self.output.info(
            f"test dependency package_folder: {dep.package_folder}")
        cxx = self._cxx()
        try:
            ver = subprocess.check_output([cxx, "--version"],
                                          text=True).splitlines()
            self.output.info(
                f"test_package compiler: {cxx} "
                f"({ver[0] if ver else 'unknown version'})")
        except Exception as exc:  # noqa: BLE001 - version probe is best-effort
            self.output.warning(
                f"compiler version probe failed for {cxx}: {exc}")
        cmd, _ = self._compile_cmd(dep)
        self.output.info(f"compiling consumer smoke test: {cmd}")
        self.run(cmd)

    def test(self):
        self._setup_env()
        dep = self._test_dependency()
        if dep is None:
            from conan.errors import ConanException
            raise ConanException("tested dependency not found")
        _, bin_path = self._compile_cmd(dep)
        self.output.info(f"Running test_boost_type_erasure: {bin_path}")
        bin_passed = False
        bin_log = ""
        try:
            # Plain inheritance of os.environ (writable TMPDIR + SDK
            # LD_LIBRARY_PATH set above); no VirtualRunEnv aggregation.
            self.run(f'"{bin_path}"')
            bin_passed = True
        except Exception as e:
            bin_log = str(e)
            self.output.error(f"binary run failed: {e}")

        discovered = 1
        passedCount = 1 if bin_passed else 0
        tp_result = {
            "executed": True,
            "passed": bin_passed,
            "command": ("clang++ test_boost_type_erasure.cpp "
                        "-lboost_type_erasure && ./test_boost_type_erasure"),
            "discovered": discovered,
            "passedCount": passedCount,
        }
        print(f"HMBS_TEST_PACKAGE_RESULT={json.dumps(tp_result)}")
        self.output.info(f"HMBS_TEST_PACKAGE_RESULT={json.dumps(tp_result)}")

        # Re-emit the upstream result persisted in the package res/ dir.
        found = False
        for _, dep in self.dependencies.items():
            cand = os.path.join(dep.package_folder, "res",
                                "upstream_test_result.json")
            if os.path.isfile(cand):
                try:
                    txt = open(cand, encoding="utf-8").read().strip()
                    data = json.loads(txt)
                    print(f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(data)}")
                    self.output.info(
                        f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(data)}")
                    found = True
                    self.output.info(
                        f"re-emitted upstream result from {cand}")
                except Exception as e:
                    self.output.warning(
                        f"failed to re-emit upstream json: {e}")
                break
        if not found:
            missing = {
                "status": "failed",
                "framework": "boost.test",
                "command": ("clang++ libs/type_erasure/test/test_*.cpp "
                            "(included/unit_test.hpp) && ./ut_*"),
                "discovered": 60,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "upstream_test_result.json not found in package res/",
            }
            print(f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(missing)}")
            self.output.info(
                f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(missing)} "
                f"(missing evidence)")
            self.output.warning(
                "upstream_test_result.json not found; reporting failed evidence")

        if not bin_passed:
            from conan.errors import ConanException
            raise ConanException(
                f"boost_type_erasure test failed: bin_passed={bin_passed} "
                f"log={bin_log[:1000]}")
