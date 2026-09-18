#!/usr/bin/env python3
"""Conan recipe — mapbox-geometry 2.0.3 (header-only C++14)."""

import json
import os
import re
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, export_conandata_patches, get, apply_conandata_patches, replace_in_file
from conan.tools.layout import basic_layout


required_conan_version = ">=2.0"


class MapboxGeometryConan(ConanFile):
    name = "mapbox-geometry"
    version = "2.0.3"
    description = "Header-only C++ geometry types for GeoJSON processing"
    license = "ISC"
    homepage = "https://github.com/mapbox/geometry.hpp"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("geometry", "geojson", "header-only", "c++14")

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("mapbox-variant/1.2.0")

    def layout(self):
        basic_layout(self, src_folder="src")

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)
        get(self, **self.conan_data["sources"]["catch-1.9.6"],
            destination=os.path.join(self.source_folder, "catch-src"),
            strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        self._run_upstream_tests()

    def _writable_tmpdir(self):
        for key in ("TMPDIR", "TMP", "TEMP"):
            val = os.environ.get(key)
            if val and os.path.isdir(val):
                try:
                    fd, probe = tempfile.mkstemp(prefix="hmbs-probe-", dir=val)
                    os.close(fd)
                    os.unlink(probe)
                    return val
                except OSError:
                    continue
        base = getattr(self, "build_folder", None) or tempfile.gettempdir()
        fallback = os.path.join(base, "hmbs-tmp")
        try:
            os.makedirs(fallback, exist_ok=True)
        except OSError:
            pass
        return fallback

    def _run(self, cmd, cwd=None, env=None):
        self.output.info("$ {}".format(" ".join(cmd)))
        result = subprocess.run(cmd, cwd=cwd, env=env or dict(os.environ),
                                capture_output=True, text=True)
        out = (result.stdout or "") + (result.stderr or "")
        if out.strip():
            self.output.info(out.strip()[-6000:])
        if result.returncode != 0:
            raise ConanException(
                "Command failed (exit {}): {}\n{}".format(
                    result.returncode, " ".join(cmd), out[-3000:]))
        return out

    def _sanitized_link_env(self, env):
        # CI-021 lld fails to start with:
        #   Error loading shared library libxml2.so.16 (needed by .../llvm/bin/lld)
        #   xmlFreeDoc / xmlReadMemory ... symbol not found
        # That is the host linker loading an incompatible libxml2 shadowed
        # via LD_LIBRARY_PATH/LD_PRELOAD inherited from the conan buildenv,
        # not a source/flag error. Strip preloads and drop conan-cache
        # entries from the loader path so lld resolves its own system
        # libxml2; test semantics and flags are unchanged.
        env.pop("LD_PRELOAD", None)
        for key in ("LD_LIBRARY_PATH", "LIBRARY_PATH"):
            val = env.get(key)
            if not val:
                continue
            parts = [p for p in val.split(":") if p]
            kept = [p for p in parts
                    if ".cache/conan" not in p.replace("\\\\", "/")
                    and "/conan2/" not in p.replace("\\\\", "/")
                    and not p.startswith(os.path.join(self.build_folder, ""))]
            if kept != parts:
                self.output.info(
                    "sanitized {}: dropped {} conan-cache entr{}".format(
                        key, len(parts) - len(kept),
                        "y" if len(parts) - len(kept) == 1 else "ies"))
            if kept:
                env[key] = ":".join(kept)
            else:
                env.pop(key, None)
        return env

    def _run_upstream_tests(self):
        src = self.source_folder
        test_dir = os.path.join(src, "test")
        if not os.path.isdir(test_dir):
            raise ConanException("Upstream test directory missing: test/")
        sources = sorted(
            os.path.join(test_dir, f) for f in os.listdir(test_dir)
            if f.endswith(".cpp"))
        if len(sources) < 13:
            raise ConanException(
                "Upstream test inventory mismatch: expected >=13 .cpp files, found {}".format(len(sources)))
        for probe in ("test/point.cpp", "test/geometry.cpp", "test/io.cpp", "test/main.cpp"):
            if not os.path.isfile(os.path.join(src, probe)):
                raise ConanException("Upstream test entry missing: {}".format(probe))

        catch_inc = os.path.join(src, "catch-src", "single_include")
        if not os.path.isfile(os.path.join(catch_inc, "catch.hpp")):
            raise ConanException("Vendored Catch header missing: single_include/catch.hpp")
        # OHOS libc++ (new LLVM) enforces URNG result_type to be an unsigned
        # integer type; vendored Catch 1.9.6 declares
        # `typedef std::ptrdiff_t result_type` in RandomNumberGenerator, which
        # trips `static_assert __libcpp_random_is_valid_urng` in <random> via
        # std::shuffle. Retype to unsigned (test harness only, no test logic,
        # ordering semantics, or assertions changed). Idempotent: the conan
        # source cache may be reused across builds.
        catch_hpp = os.path.join(catch_inc, "catch.hpp")
        with open(catch_hpp, "r", encoding="utf-8") as f:
            catch_src = f.read()
        if "typedef std::ptrdiff_t result_type;" in catch_src:
            replace_in_file(self, catch_hpp,
                            "typedef std::ptrdiff_t result_type;",
                            "typedef unsigned int result_type;")
        elif "typedef unsigned int result_type;" not in catch_src:
            raise ConanException(
                "Vendored Catch RandomNumberGenerator signature unrecognized; "
                "cannot apply OHOS libc++ URNG compatibility fix")
        geometry_inc = os.path.join(src, "include")
        if not os.path.isfile(os.path.join(geometry_inc, "mapbox", "geometry.hpp")):
            raise ConanException("Upstream header missing: include/mapbox/geometry.hpp")

        try:
            variant_inc = os.path.join(
                self.dependencies["mapbox-variant"].package_folder, "include")
        except Exception as exc:
            raise ConanException("mapbox-variant dependency include not available: {}".format(exc))
        if not os.path.isfile(os.path.join(variant_inc, "mapbox", "variant.hpp")):
            raise ConanException(
                "mapbox-variant header missing in dependency package: {}".format(variant_inc))

        compilers = {}
        try:
            compilers = self.conf.get("tools.build:compiler_executables", default={},
                                      check_type=dict) or {}
        except Exception:
            compilers = {}
        cxx = (compilers.get("cpp") or os.environ.get("CXX")
               or shutil.which("clang++") or shutil.which("c++") or "clang++")

        build_dir = os.path.join(self.build_folder, "upstream_tests")
        os.makedirs(build_dir, exist_ok=True)
        tmpdir = self._writable_tmpdir()
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        test_bin = os.path.join(build_dir, "unit-tests")
        compile_cmd = ([cxx, "-std=c++14", "-O1",
                        "-Wno-unused-command-line-argument",
                        "-I", geometry_inc, "-I", catch_inc, "-I", variant_inc]
                       + sources + ["-o", test_bin])
        env = dict(os.environ)
        env["TMPDIR"] = tmpdir
        env["TMP"] = tmpdir
        env["TEMP"] = tmpdir
        env = self._sanitized_link_env(env)
        self._run(compile_cmd, cwd=build_dir, env=env)
        if not os.path.isfile(test_bin) or os.path.getsize(test_bin) == 0:
            raise ConanException("Upstream test binary missing or empty after compile")

        from conan.tools.build import can_run
        if not can_run(self):
            self.output.warning(
                "Upstream tests compiled successfully but not executed: "
                "target binaries cannot run in this environment (can_run=False).")
            raise ConanException("Upstream tests compiled but skipped on non-runnable target; refusing to pass")

        out = self._run([test_bin], cwd=build_dir, env=env)
        if not out.strip():
            raise ConanException("Upstream test binary produced no output; refusing to pass")
        discovered, passed, failed = self._parse_catch(out)
        skipped = 0
        ok = (failed == 0 and passed == discovered and discovered > 0)
        status = "passed" if ok else "failed"
        upstream = {
            "status": status,
            "framework": "catch",
            "command": "./unit-tests (upstream Catch suite)",
            "discovered": discovered,
            "executed": discovered,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))
        self._write_upstream_result(upstream)
        if not ok:
            raise ConanException("Upstream tests did not fully pass")

    def _write_upstream_result(self, data):
        # Persist real on-device counts so test_package can re-emit the
        # marker when Conan serves a cached package (build() skipped).
        try:
            os.makedirs(self.build_folder, exist_ok=True)
            with open(os.path.join(self.build_folder, "upstream_test_result.json"),
                      "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        except OSError as exc:
            self.output.warning("write upstream_test_result.json failed: {}".format(exc))

    @staticmethod
    def _parse_catch(out):
        m = re.search(r"All tests passed\s*\((\d+)\s+assertions in (\d+)\s+test cases\)", out)
        if m:
            assertions = int(m.group(1))
            cases = int(m.group(2))
            if assertions <= 0 or cases <= 0:
                raise ConanException("Upstream tests reported non-positive counts; refusing to pass")
            return cases, cases, 0
        m_cases = re.search(r"(\d+)\s+test cases", out)
        m_failed = re.search(r"(\d+)\s+failed", out, re.IGNORECASE)
        if "FAILED" in out or "failed" in out.lower():
            disc = int(m_cases.group(1)) if m_cases else 0
            fail = int(m_failed.group(1)) if m_failed else 1
            return disc if disc else 1, 0, fail
        raise ConanException(
            "Upstream tests produced no Catch summary; refusing to pass. Output tail: {}".format(out[-1000:]))

    def package(self):
        copy(self, "*.hpp",
             src=os.path.join(self.source_folder, "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE*",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        # Persist real upstream counts for cache-hit re-emit via test_package.
        try:
            copy(self, "upstream_test_result.json", self.build_folder,
                 os.path.join(self.package_folder, "res"))
        except Exception:
            pass

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "mapbox-geometry")
        self.cpp_info.set_property("cmake_target_name", "mapbox::geometry")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
