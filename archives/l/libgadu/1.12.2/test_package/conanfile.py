#!/usr/bin/env python3
"""Conan test_package — libgadu 1.12.2 (offline consumer test).

L1 test (R34): builds test.c against the installed libgadu and runs it.
test.c performs 4 real offline assertions against public API:
  1. gg_libgadu_version() == "1.12.2"
  2. gg_fix32 double-swap round-trip
  3. gg_fix16 double-swap round-trip
  4. gg_crc32 determinism + input sensitivity

Emits HMBS machine-evidence markers after the real test command and
re-emits the build-time upstream marker (dual-channel, libcacard
precedent) so cache-hit runs still carry upstream evidence.
"""

import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class LibgaduTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # E266 (main-recipe precedent): OHOS SDK lld needs llvm/lib with
        # libxml2.so.16 on LD_LIBRARY_PATH for the CMake compiler probe.
        # Unique script name (never "conanbuild", see libgsf R57 E2BIG).
        if str(self.settings.os) == "OHOS":
            import glob as _glob
            _llvm_lib = ("/data/service/hnp/ohos-sdk.org/"
                         "ohos-sdk_26.0.0.18/ohos/native/llvm/lib")
            if not os.path.isdir(_llvm_lib):
                _cands = sorted(_glob.glob(
                    "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib"))
                _llvm_lib = _cands[0] if _cands else ""
            if _llvm_lib:
                _env = Environment()
                _env.prepend_path("LD_LIBRARY_PATH", _llvm_lib)
                _env.vars(self).save_script("libgadu_test_env")

    def _patch_stale_toolchain_compiler(self):
        """Replace missing profile clang with a usable one (dr_flac precedent).

        The checked-in ohos-aarch64 profile pins CMAKE_C/CXX_COMPILER to
        /data/service/hnp/bin/clang{,++}, stale on some true-machine
        images. Only touch the toolchain file when that absolute path is
        missing; otherwise leave CI behavior unchanged.
        """
        try:
            configured = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
        except Exception:
            configured = {}
        conf_c = configured.get("c")
        conf_cxx = (configured.get("cpp") or configured.get("cxx")
                    or configured.get("c++"))
        stale_paths = [p for p in (conf_c, conf_cxx,
                                   "/data/service/hnp/bin/clang",
                                   "/data/service/hnp/bin/clang++")
                       if p]
        # If every stale candidate already exists, nothing to do (real CI).
        try:
            if all(os.path.isfile(p) for p in
                   ["/data/service/hnp/bin/clang",
                    "/data/service/hnp/bin/clang++"]):
                return False
        except Exception:
            pass
        cc = (conf_c if conf_c and os.path.isfile(conf_c)
              else (shutil.which("clang") or os.environ.get("CC") or "clang"))
        cxx = (conf_cxx if conf_cxx and os.path.isfile(conf_cxx)
               else (shutil.which("clang++") or os.environ.get("CXX")
                     or "clang++"))
        gen = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        if not os.path.isfile(gen):
            return False
        try:
            with open(gen, "r", encoding="utf-8",
                      errors="replace") as handle:
                txt = handle.read()
        except OSError:
            return False
        orig = txt
        for stale in dict.fromkeys(stale_paths):
            if not stale:
                continue
            try:
                if os.path.isfile(stale):
                    continue
            except Exception:
                pass
            if stale.endswith("clang++"):
                txt = txt.replace(stale, cxx)
            elif stale.endswith("clang"):
                txt = txt.replace(stale, cc)
        if txt != orig:
            with open(gen, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(txt)
            self.output.info("libgadu test_package: patched stale compiler "
                             "%s->%s %s->%s" % (conf_c, cc, conf_cxx, cxx))
            return True
        return False

    def build(self):
        self._patch_stale_toolchain_compiler()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        tp_passed = False
        tp_command = "ctest --output-on-failure"
        discovered = 4
        if can_run(self):
            try:
                cmake = CMake(self)
                cmake.test()
                # L0d: also run the binary directly via self.run().
                suffix = ".exe" if self.settings.os == "Windows" else ""
                bin_path = os.path.join(
                    self.cpp.build.bindirs[0], "test_libgadu" + suffix)
                self.run(bin_path, env="conanrun")
                tp_passed = True
                tp_command = bin_path + " (version+fix32+fix16+crc32)"
            except Exception as exc:
                self.output.error("test_libgadu failed: %s" % exc)
                tp_passed = False
        else:
            self.output.warning("Cross build: consumer test not run")

        tp_result = {
            "executed": can_run(self),
            "passed": tp_passed,
            "command": tp_command,
            "discovered": discovered,
            "passedCount": discovered if tp_passed else 0,
        }
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(tp_result),
              flush=True)
        self._reemit_upstream_result()
        if can_run(self) and not tp_passed:
            raise ConanException("test_package consumer tests failed")

    def _reemit_upstream_result(self):
        """Re-emit build-time upstream marker (cache-hit runs skip build())."""
        pkg_folder = ""
        for accessor in ("host", None):
            try:
                if accessor is None:
                    dep = self.dependencies["libgadu"]
                else:
                    dep = getattr(self.dependencies, accessor)["libgadu"]
                pkg_folder = str(dep.package_folder or "")
                if pkg_folder:
                    break
            except Exception:
                continue
        if not pkg_folder:
            self.output.warning(
                "HMBS upstream re-emit: libgadu package folder not found")
            return False
        candidates = [
            os.path.join(pkg_folder, "share", "libgadu",
                         "hmbs_upstream_result.json"),
            os.path.join(pkg_folder, "share", "hmbs_upstream_result.json"),
            os.path.join(pkg_folder, "hmbs_upstream_result.json"),
            os.path.join(pkg_folder, "res", "hmbs_upstream_result.json"),
        ]
        for path in candidates:
            if not os.path.isfile(path):
                continue
            try:
                with open(path, encoding="utf-8") as handle:
                    marker = json.load(handle)
                if not isinstance(marker, dict):
                    raise ValueError("marker is not an object")
                for key in ("status", "framework", "command", "discovered",
                            "executed", "passed", "failed", "skipped"):
                    if key not in marker:
                        raise ValueError("marker missing key: %s" % key)
                self.output.info(
                    "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))
                self.output.info(
                    "HMBS upstream re-emitted from package file: %s" % path)
                return True
            except Exception as exc:
                self.output.warning(
                    "HMBS upstream re-emit failed for %s: %s" % (path, exc))
                return False
        self.output.warning(
            "HMBS upstream re-emit: no persisted result file in package "
            "(expected from a fresh build with the updated recipe; "
            "not fabricating evidence)")
        return False
