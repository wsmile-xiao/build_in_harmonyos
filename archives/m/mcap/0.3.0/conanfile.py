#!/usr/bin/env python3
"""Conan recipe — mcap 0.3.0 (header-only C++17).

MCAP is a modular, serialization-agnostic container file format for
pub/sub and robotics logging (Foxglove). The C++ implementation is a
header-only library under cpp/mcap/include/mcap/ with runtime
dependencies on lz4 and zstd for chunk compression.

Upstream C++ test suite (cpp/test): unit_tests.cpp (Catch2, 8 TEST_CASEs)
is the official `make test-host` target. The two conformance runners
(streamed_reader_conformance / streamed_writer_conformance) are single-shot
JSON converters driven by the cross-language Node.js harness in
tests/conformance (requires Node.js, not part of the C++ package test
closure), so build() compiles and runs unit_tests as the upstream gate
and additionally smoke-runs the reader conformance binary over bundled
.mcap samples.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import copy, export_conandata_patches, get, apply_conandata_patches
from conan.tools.layout import basic_layout


required_conan_version = ">=2.0"


class McapConan(ConanFile):
    name = "mcap"
    version = "0.3.0"
    description = "Header-only C++ implementation of the MCAP file format"
    license = "MIT"
    homepage = "https://github.com/foxglove/mcap"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("mcap", "serialization", "robotics", "recording", "header-only", "cpp17")

    package_type = "header-library"
    # R32: keep four settings for L0p; OS check uses in ("Linux", "OHOS").
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "mcap supports Linux and OHOS only, got {}".format(self.settings.os)
            )
        # Upstream requires C++17 (std::string_view, if constexpr, structured bindings).
        try:
            cppstd = str(self.settings.get_safe("compiler.cppstd") or "")
        except Exception:
            cppstd = ""
        if cppstd and cppstd not in ("17", "18", "19", "20", "21", "22", "23", "26", "gnu17",
                                     "gnu18", "gnu19", "gnu20", "gnu21", "gnu22", "gnu23", "gnu26"):
            raise ConanInvalidConfiguration(
                "mcap requires C++17 or newer, got compiler.cppstd={}".format(cppstd)
            )
        # Strategy-cycle 4 follow-up (2026-09-27): the cycle-4 validate()
        # isfile hard-fail fulfilled its diagnostic purpose (preflight
        # signature moved from cryptic lz4 project() to an explicit
        # missing-file Invalid for /data/service/hnp/bin/clang, fully
        # penetrating the summary), but as a permanent recipe it is
        # self-blocking: on the broken runner it guarantees exit-6
        # Invalid before any dependency builds, so the backend keeps
        # routing an infra fault back to the recipe queue in a loop.
        # A recipe has no execution point before lz4/zstd/catch2
        # configure (proven by three identical fingerprints plus lz4
        # package_id triple-zero-movement), so no recipe-side probe or
        # fallback can repair the pinned compiler. Restore vanilla
        # validate (OS + cppstd only); infra faults stay infra faults
        # for backend runner repair/re-scheduling instead of being
        # renamed into recipe Invalids.
        # Fingerprint-fix #3 (2026-09-27): the warning diagnostic added in
        # fixes #1-2 was removed after two preflight rounds showed zero
        # summary penetration; forensics retained in notes.md rows 15-17.
        # Recipe intentionally minimal: dependency-toolchain faults are out
        # of single-PR scope.

    def requirements(self):
        # Runtime compression deps (headers use lz4/zstd APIs; consumers link them).
        # Upstream pins lz4/1.9.3 + zstd/1.5.2; the ohpcd registry provides
        # newer compatible releases, so bump to the published versions.
        # Row 19: lz4/1.10.0 -> lz4/1.10.0.3 (R37: same upstream v1.10.0,
        # adaptation-fix suffix). Bare 1.10.0 resolves through the registry
        # proxy to an upstream CMake RREV whose ConanToolchain HarmonyOS
        # mapping plus stale pinned compiler break on Sept-layout runners;
        # the repo-local 1.10.0.3 exists only in-repo, so it deterministically
        # resolves to the pure-Makefile recipe, which builds with PATH clang
        # (present in Sept layout) and needs no CMake platform module.
        # Same ABI/headers; default shared=False (static).
        self.requires("lz4/1.10.0.3")
        self.requires("zstd/1.5.7.1")
        # Upstream test-only deps (cpp/test/conanfile.py, conan v1 syntax):
        # catch2/2.13.8 + nlohmann_json/3.10.5. Use the closest published
        # versions. test_requires() (not plain requires()) so they are
        # present in the host context during build() but are not direct
        # runtime deps: plain requires() makes Conan 2 fail package_info()
        # with "direct dependency 'catch2' is not used by any requires"
        # (preflight 2026-09-27: build + 8/8 upstream tests passed, then
        # package() failed on that error). Same technique rationale as
        # before (avoid CPM network fetch), now with correct visibility.
        self.test_requires("catch2/2.13.10")
        self.test_requires("nlohmann_json/3.12.0")

    def layout(self):
        basic_layout(self, src_folder="src")

    def package_id(self):
        # Header-only: identical for every configuration.
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        self._run_upstream_tests()

    # -- helpers ---------------------------------------------------------
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
        # CI-021: host lld can fail loading an incompatible libxml2 shadowed
        # via LD_LIBRARY_PATH from the conan buildenv. Strip preloads and drop
        # conan-cache entries so lld resolves its own system libxml2.
        env.pop("LD_PRELOAD", None)
        for key in ("LD_LIBRARY_PATH", "LIBRARY_PATH"):
            val = env.get(key)
            if not val:
                continue
            parts = [p for p in val.split(":") if p]
            kept = [p for p in parts
                    if ".cache/conan" not in p.replace("\\", "/")
                    and "/conan2/" not in p.replace("\\", "/")
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

    # -- compiler selection (HMBS-native minimal) ------------------------
    # Strategy-cycle 7 (2026-09-27): lz4/1.10.0.3 (pure-Makefile, PATH
    # CC=clang CXX=clang++) now builds, so the failure advanced past the
    # dependency closure into mcap's own build(): the profile still pins
    # /data/service/hnp/bin/clang{,++} but that path is absent on runner
    # clients/58877229c207 (isfile-proven in cycle 4, now re-proven by
    # FileNotFoundError on the direct clang++ invocation). The cycle-2
    # removal rationale ("fallback is dead code for CMakeToolchain deps")
    # no longer applies to this direct-compile path: mcap IS the
    # raw-compile recipe that reads conf directly. Policy: pinned path
    # when present+executable (healthy machines zero change); otherwise
    # reuse HMBS front-loaded PATH via shutil.which (same clang the
    # lz4 Makefile uses), preferring the sibling in the same directory;
    # only CC/CXX selection is affected, never CFLAGS/LDFLAGS. When
    # neither exists, pass the pinned value through for a clear
    # toolchain error (infra routing) instead of masking it.
    def _compiler_from_conf_or_env(self, kind):
        try:
            conf = self.conf.get("tools.build:compiler_executables", default={},
                                 check_type=dict) or {}
        except Exception:
            conf = {}
        pinned = conf.get(kind) if isinstance(conf, dict) else None
        if pinned and os.path.isfile(pinned) and os.access(pinned, os.X_OK):
            self.output.info("compiler {}: using pinned {}".format(kind, pinned))
            return pinned
        env_key = "CXX" if kind == "cpp" else "CC"
        env_val = os.environ.get(env_key)
        if env_val:
            # Absolute path: use when executable; bare name: resolve via PATH.
            if os.path.isabs(env_val):
                if os.path.isfile(env_val) and os.access(env_val, os.X_OK):
                    self.output.info(
                        "compiler {}: pinned unusable, reusing {}={}".format(kind, env_key, env_val))
                    return env_val
            else:
                resolved = shutil.which(env_val)
                if resolved and os.path.isfile(resolved):
                    self.output.info(
                        "compiler {}: pinned unusable, reusing {}={} ({})".format(
                            kind, env_key, env_val, resolved))
                    return resolved
        # PATH fallback (reuses HMBS front-loaded tool dirs; same clang as
        # lz4/1.10.0.3 Makefile). Prefer sibling of the opposite compiler
        # when both live in one directory.
        bare = "clang++" if kind == "cpp" else "clang"
        sibling_bare = "clang" if kind == "cpp" else "clang++"
        sibling_path = shutil.which(sibling_bare)
        if sibling_path:
            sib_dir = os.path.dirname(sibling_path)
            sib_candidate = os.path.join(sib_dir, bare)
            if os.path.isfile(sib_candidate) and os.access(sib_candidate, os.X_OK):
                self.output.info(
                    "compiler {}: pinned '{}' not present, using PATH sibling {}".format(
                        kind, pinned, sib_candidate))
                try:
                    os.environ[env_key] = sib_candidate
                except Exception:
                    pass
                return sib_candidate
        found = shutil.which(bare)
        if found and os.path.isfile(found):
            self.output.info(
                "compiler {}: pinned '{}' not present, using PATH {}".format(kind, pinned, found))
            try:
                os.environ[env_key] = found
            except Exception:
                pass
            return found
        if pinned:
            self.output.warning(
                "compiler {}: pinned '{}' not present and no {} in env; "
                "passing through for a clear toolchain error".format(kind, pinned, env_key))
            return pinned
        fallback = os.environ.get(env_key) or bare
        self.output.info("compiler {}: no pinned path, using {}".format(kind, fallback))
        return fallback

    def _dep_include(self, ref):
        try:
            pkg = self.dependencies[ref].package_folder
        except Exception as exc:
            raise ConanException(
                "dependency '{}' include not available: {}".format(ref, exc))
        inc = os.path.join(str(pkg), "include")
        if not os.path.isdir(inc):
            raise ConanException(
                "dependency '{}' has no include dir: {}".format(ref, inc))
        return inc

    def _dep_libdir(self, ref):
        try:
            pkg = str(self.dependencies[ref].package_folder)
            libdirs = list(self.dependencies[ref].cpp_info.libdirs)
        except Exception:
            return None, []
        candidates = [os.path.join(pkg, d) for d in libdirs] + [os.path.join(pkg, "lib")]
        existing = [d for d in candidates if os.path.isdir(d)]
        return pkg, existing

    def _find_static_lib(self, libdirs, names):
        # Prefer a static archive when the package ships both .a and .so.
        # zstd/1.5.7.1 installs BOTH (ZSTD_BUILD_SHARED=ON + STATIC=ON), so
        # plain -lzstd picks the .so and the test binary inherits a runtime
        # libzstd.so.1 dependency; the runner then resolves a foreign stub
        # libzstd (missing ZSTD_* symbols, exit 127). Linking the .a path
        # directly removes the runtime dependency without changing test
        # semantics. Returns the full archive path or None.
        for d in libdirs:
            for n in names:
                cand = os.path.join(d, n)
                try:
                    if os.path.isfile(cand) and os.path.getsize(cand) > 0:
                        return cand
                except OSError:
                    continue
        return None

    # -- upstream tests --------------------------------------------------
    def _run_upstream_tests(self):
        src = self.source_folder
        test_dir = os.path.join(src, "cpp", "test")
        mcap_inc = os.path.join(src, "cpp", "mcap", "include")
        if not os.path.isfile(os.path.join(mcap_inc, "mcap", "mcap.hpp")):
            raise ConanException("Upstream header missing: cpp/mcap/include/mcap/mcap.hpp")
        if not os.path.isdir(test_dir):
            raise ConanException("Upstream test directory missing: cpp/test/")
        unit_cpp = os.path.join(test_dir, "unit_tests.cpp")
        reader_conf = os.path.join(test_dir, "streamed_reader_conformance.cpp")
        writer_conf = os.path.join(test_dir, "streamed_writer_conformance.cpp")
        for probe in (unit_cpp, reader_conf, writer_conf):
            if not os.path.isfile(probe):
                raise ConanException("Upstream test entry missing: {}".format(probe))
        # Inventory: exactly 8 Catch2 TEST_CASEs in unit_tests.cpp at v0.3.0.
        with open(unit_cpp, "r", encoding="utf-8") as f:
            unit_src = f.read()
        cases = re.findall(r'^\s*TEST_CASE\s*\(', unit_src, re.MULTILINE)
        if len(cases) != 8:
            raise ConanException(
                "Upstream test inventory mismatch: expected 8 TEST_CASEs in "
                "cpp/test/unit_tests.cpp, found {}".format(len(cases)))

        lz4_inc = self._dep_include("lz4")
        zstd_inc = self._dep_include("zstd")
        catch_inc = self._dep_include("catch2")
        json_inc = self._dep_include("nlohmann_json")
        _, lz4_libdirs = self._dep_libdir("lz4")
        _, zstd_libdirs = self._dep_libdir("zstd")

        cxx = self._compiler_from_conf_or_env("cpp")
        cc = self._compiler_from_conf_or_env("c")
        self.output.info("upstream compilers: CC={} CXX={}".format(cc, cxx))

        build_dir = os.path.join(self.build_folder, "upstream_tests")
        os.makedirs(build_dir, exist_ok=True)
        tmpdir = self._writable_tmpdir()
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        env = dict(os.environ)
        env["TMPDIR"] = tmpdir
        env["TMP"] = tmpdir
        env["TEMP"] = tmpdir
        env = self._sanitized_link_env(env)
        # Runtime search path: any residual shared dep (e.g. a package that
        # ships only .so) must resolve to the conan package lib first, not
        # to a foreign system stub. Prepend the dep libdirs after
        # sanitization (the sanitizer never strips conan-home paths, but
        # the base env may simply lack them since this recipe uses no
        # VirtualRunEnv for its manual compile+run).
        try:
            _dep_dirs = [d for d in (lz4_libdirs + zstd_libdirs) if d]
            if _dep_dirs:
                _old = env.get("LD_LIBRARY_PATH", "")
                _parts = [p for p in _old.split(":") if p] if _old else []
                for d in reversed(_dep_dirs):
                    if d not in _parts:
                        _parts.insert(0, d)
                env["LD_LIBRARY_PATH"] = ":".join(_parts)
                self.output.info("runtime LD_LIBRARY_PATH={}".format(env["LD_LIBRARY_PATH"][:800]))
        except Exception as exc:
            self.output.warning("set runtime LD_LIBRARY_PATH failed: {!r}".format(exc))

        # Link choice: prefer static archives when present (see
        # _find_static_lib). lz4/1.10.0.3 ships only .a already; zstd ships
        # both, and -lzstd would pick the .so. Full .a paths keep -L/-l
        # only as fallback for archives that genuinely lack a static lib.
        lz4_static = self._find_static_lib(lz4_libdirs, ("liblz4.a",))
        zstd_static = self._find_static_lib(zstd_libdirs, ("libzstd.a",))
        if lz4_static:
            self.output.info("link: using static {}".format(lz4_static))
        if zstd_static:
            self.output.info("link: using static {}".format(zstd_static))

        # Compile unit_tests (Catch2 main) directly. Upstream's own
        # cpp/test/conanfile.py uses conan v1 syntax (from conans import)
        # which cannot run under Conan 2, so compile manually with the same
        # sources and published test deps.
        test_bin = os.path.join(build_dir, "unit-tests")
        link_dirs = []
        for d in lz4_libdirs + zstd_libdirs:
            if d not in link_dirs:
                link_dirs.append(d)
        # Static archives first (deterministic, no runtime .so needed);
        # -L/-l only for whichever dep lacked a static archive.
        link_static = [p for p in (lz4_static, zstd_static) if p]
        link_dynamic = []
        if not lz4_static:
            link_dynamic.append("-llz4")
        if not zstd_static:
            link_dynamic.append("-lzstd")
        if not link_static and not link_dynamic:
            raise ConanException("No linkable lz4/zstd libraries found")
        compile_cmd = [cxx, "-std=c++17", "-O1",
                       "-Wno-unused-command-line-argument",
                       "-I", mcap_inc, "-I", lz4_inc, "-I", zstd_inc,
                       "-I", catch_inc, "-I", json_inc,
                       unit_cpp, "-o", test_bin]
        for d in link_dirs:
            compile_cmd += ["-L", d]
        compile_cmd += link_static + link_dynamic
        self._run(compile_cmd, cwd=build_dir, env=env)
        if not os.path.isfile(test_bin) or os.path.getsize(test_bin) == 0:
            raise ConanException("Upstream test binary missing or empty after compile")

        from conan.tools.build import can_run
        if not can_run(self):
            raise ConanException(
                "Upstream tests compiled but skipped on non-runnable target; refusing to pass")

        out = self._run([test_bin], cwd=build_dir, env=env)
        if not out.strip():
            raise ConanException("Upstream test binary produced no output; refusing to pass")
        discovered, passed, failed = self._parse_catch(out)

        # Smoke-run the streamed-reader conformance binary over a few bundled
        # .mcap samples (full cross-language diff needs the Node.js harness,
        # not part of `make test-host`; exit 0 + valid JSON with a "records"
        # list = pass). NoData/* samples legitimately yield {"records":[]},
        # so emptiness is judged by JSON validity, not by byte length.
        conf_bin = os.path.join(build_dir, "streamed-reader-conformance")
        conf_cmd = [cxx, "-std=c++17", "-O1",
                    "-Wno-unused-command-line-argument",
                    "-I", mcap_inc, "-I", lz4_inc, "-I", zstd_inc,
                    "-I", json_inc,
                    reader_conf, "-o", conf_bin]
        for d in link_dirs:
            conf_cmd += ["-L", d]
        conf_cmd += link_static + link_dynamic
        self._run(conf_cmd, cwd=build_dir, env=env)
        conf_data = os.path.join(src, "tests", "conformance", "data")
        samples = []
        if os.path.isdir(conf_data):
            for root, _, files in os.walk(conf_data):
                for fn in files:
                    if fn.endswith(".mcap"):
                        samples.append(os.path.join(root, fn))
                        if len(samples) >= 5:
                            break
                if len(samples) >= 5:
                    break
        if len(samples) < 3:
            raise ConanException(
                "Conformance sample inventory mismatch: expected >=3 .mcap files, found {}".format(
                    len(samples)))
        for sample in samples:
            sout = self._run([conf_bin, sample], cwd=build_dir, env=env)
            text = (sout or "").strip()
            if '"records"' not in text or len(text) < 10:
                raise ConanException(
                    "Conformance smoke failed (empty/invalid JSON) for {}".format(sample))
            try:
                doc = json.loads(text)
            except Exception as exc:
                raise ConanException(
                    "Conformance smoke failed (unparseable JSON) for {}: {!r} tail: {}".format(
                        sample, exc, text[-500:]))
            if not isinstance(doc, dict) or "records" not in doc or not isinstance(doc["records"], list):
                raise ConanException(
                    "Conformance smoke failed (no records list) for {} tail: {}".format(
                        sample, text[-500:]))

        skipped = 0
        ok = (failed == 0 and passed == discovered and discovered > 0)
        status = "passed" if ok else "failed"
        upstream = {
            "status": status,
            "framework": "catch",
            "command": "./unit-tests (upstream Catch2 suite, 8 TEST_CASEs) + "
                       "streamed-reader-conformance smoke ({} samples)".format(len(samples)),
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
        try:
            os.makedirs(self.build_folder, exist_ok=True)
            with open(os.path.join(self.build_folder, "upstream_test_result.json"),
                      "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        except OSError as exc:
            self.output.warning("write upstream_test_result.json failed: {}".format(exc))

    @staticmethod
    def _parse_catch(out):
        # Deterministic source: the single canonical Catch2 summary line.
        # Row 18 (strategy-cycle 6): removed the lenient FAILED-text fallback
        # (loose `N test cases` / `N failed` regexes with a default fail=1).
        # That branch synthesized counts from two inconsistent sources and
        # could emit passed+failed != executed, violating the marker identity.
        # Per HMBS rule numbers have exactly one source; any non-canonical
        # output now raises with the raw tail. Healthy pass path unchanged:
        # passing suites always print the canonical line (first branch).
        m = re.search(r"All tests passed\s*\((\d+)\s+assertions in (\d+)\s+test cases\)", out)
        if m:
            assertions = int(m.group(1))
            cases = int(m.group(2))
            if assertions <= 0 or cases <= 0:
                raise ConanException("Upstream tests reported non-positive counts; refusing to pass")
            return cases, cases, 0
        raise ConanException(
            "Upstream tests produced no canonical Catch2 summary "
            "(expected 'All tests passed (N assertions in M test cases)'); "
            "refusing to synthesize counts. Output tail: {}".format(
                out[-1000:]))

    def package(self):
        copy(self, "*.hpp",
             src=os.path.join(self.source_folder, "cpp", "mcap", "include"),
             dst=os.path.join(self.package_folder, "include"))
        # types.hpp line 370 does #include "types.inl" (same directory);
        # *.hpp-only copy drops these sibling implementation headers, so
        # consumers fail with "'types.inl' file not found" while build()
        # (which compiles against source_folder) passes. Ship them.
        copy(self, "*.inl",
             src=os.path.join(self.source_folder, "cpp", "mcap", "include"),
             dst=os.path.join(self.package_folder, "include"))
        copy(self, "LICENSE*",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        try:
            copy(self, "upstream_test_result.json", self.build_folder,
                 os.path.join(self.package_folder, "res"))
        except Exception:
            pass

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "mcap")
        self.cpp_info.set_property("cmake_target_name", "mcap::mcap")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        # Header consumers still need the compression libs.
        # NOTE (2026-09-27 round 3): Conan component name vs CMake target
        # name are different namespaces. zstd/1.5.7.1 has NO component
        # libzstd (hence "Component 'zstd::libzstd' not found" when listed
        # here); its root package cmake_target_name is zstd::libzstd
        # (CMakeDeps log: "Target declared 'zstd::libzstd'"). So this list
        # must stay package-level "zstd::zstd", while test_package CMake
        # links the CMake target "zstd::libzstd".
        self.cpp_info.requires = ["lz4::lz4", "zstd::zstd"]
