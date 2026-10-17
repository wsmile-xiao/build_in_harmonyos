#!/usr/bin/env python3
"""Conan recipe — libphonenumber 8.13.51 (direct-cc, no CMake configure)."""
import glob
import json
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run, check_min_cppstd
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, mkdir
from conan.tools.layout import basic_layout


class LibphonenumberConan(ConanFile):
    name = "libphonenumber"
    version = "8.13.51"
    description = "Google's common C++ library for parsing, formatting and validating international phone numbers"
    license = "Apache-2.0"
    homepage = "https://github.com/google/libphonenumber"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libphonenumber is only supported on Linux/OHOS, not %s" % self.settings.os
            )
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # Dep-graph (strategy cycle 5): protobuf/33.6 is the OHOS-adapted
        # recipe and the exact revision that published grpc/1.70.0 built in
        # official CI, so it is the closest-to-proven graph. The cycle-3
        # downgrade to protobuf/3.17.3 was reverted: the re-run failed
        # identically at its own cmake.configure() project() compiler
        # identification, proving the failure is independent of the protobuf
        # version, while 3.17.3 adds staleness risk (2021-era recipe,
        # cmake_minimum_required(3.1.3) against CMake 4.4.3, forced Ninja +
        # custom bld layout). Unlike cycles 3-4, this cycle no longer forces
        # `protobuf:with_zlib=False`: that override creates a unique
        # protobuf package_id with no cached binary (the proven grpc/brpc
        # graphs both use the default with_zlib=True), forcing an avoidable
        # source build in the preflight sandbox. Keep the default so the
        # requirement resolves to the same graph the published builds used.

    def validate(self):
        check_min_cppstd(self, "17")

    def requirements(self):
        # Strategy cycle 5: back to protobuf/33.6 (OHOS-adapted, CI-proven via
        # published grpc/1.70.0). abseil-cpp stays because upstream
        # cpp/CMakeLists.txt links absl::node_hash_set/strings/
        # synchronization directly (LIBRARY_DEPS). protobuf>=2.4 check in
        # upstream CMake is satisfied.
        self.requires("abseil-cpp/20260107.1", transitive_headers=True)
        self.requires("protobuf/33.6", transitive_headers=True, transitive_libs=True)
        self.requires("icu4c/78", transitive_headers=True, transitive_libs=True)
        self.requires("googletest/1.12.1")
        # Strategy cycle 6: pin zlib to the repo-exclusive 1.3.1.2. The
        # 2026-09-13 preflight proved cycle 5's "default options reuse
        # binaries" hypothesis wrong for zlib: zlib/1.3.1 resolved to a
        # CMake-based foreign recipe revision (build() line 81
        # cmake.configure(), CMakeLists.txt:4 project() wall), while every
        # in-repo zlib recipe (including 1.3.1) is Makefile-based and has no
        # cmake.configure() at all. A repo-exclusive R37 version exists only
        # on ohpcd, so resolution must use the OHOS makefile recipe
        # (./configure --static + make -j1, built 2026-09-08 with make check
        # green), which has no CMake platform wall. zlib 1.3.x is ABI-stable
        # and libphonenumber never uses its gzip streams, so the patch-level
        # bump is safe for protobuf's ZLIB_ROOT linkage.
        self.requires("zlib/1.3.1.2", override=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _writable_tmpdir(self):
        """Prefer the HMBS-provided writable TMPDIR; fall back to build tmp."""
        for key in ("TMPDIR", "TMP", "TEMP"):
            val = os.environ.get(key)
            if val and os.path.isdir(val):
                return val
        return os.path.join(self.build_folder, "test-tmp")

    def _export_writable_tmpdir(self):
        """Mirror the writable tmp root into the real process environment.

        Guarantees inheritance by cmake.configure()/clang/gestest
        subprocesses even if env-file aggregation is delayed or skipped.
        Creates the directory best-effort; never raises.
        """
        tmpdir = self._writable_tmpdir()
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        for key in ("TMPDIR", "TMP", "TEMP", "TEST_TMPDIR"):
            os.environ[key] = tmpdir
        return tmpdir

    def generate(self):
        # Cycle 9: no CMake configure is executed at all (critnib precedent).
        # The 2026-09-13 re-run proved cycle 8's TRY_COMPILE/WORKS bypass
        # ineffective (identical project() identification failure at the new
        # build() line 451, i.e. with the new vars already active), so the
        # configure probe itself must go. Only the temp root is replaced;
        # no test is skipped or deleted.
        self._export_writable_tmpdir()
        tmpdir = self._writable_tmpdir()
        tmp_env = Environment()
        tmp_env.define("TMPDIR", tmpdir)
        tmp_env.define("TMP", tmpdir)
        tmp_env.define("TEMP", tmpdir)
        tmp_env.define("TEST_TMPDIR", tmpdir)
        tmp_env.vars(self, scope="build").save_sh("hmbs_tmpdir_build.sh")
        tmp_env.vars(self, scope="run").save_sh("hmbs_tmpdir_run.sh")
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

    def _cpp_dir(self):
        return os.path.join(self.source_folder, "cpp")

    def _count_upstream_tests(self):
        """Count gtest TEST/TEST_F/TEST_P cases in the upstream test sources.

        Recursive: the suite spans test/phonenumbers/*_test.cc plus
        subdirs (geocoding/*_test.cc, utf/*_test.cc). A top-level-only
        glob undercounts (302 vs 326 executed on device) and trips the
        HMBS discovered/executed consistency gate without any test
        being skipped.
        """
        count = 0
        test_dir = os.path.join(self._cpp_dir(), "test", "phonenumbers")
        pattern = re.compile(r"^\s*TEST(_F|_P)?\s*\(")
        for path in glob.glob(os.path.join(test_dir, "**", "*_test.cc"), recursive=True):
            try:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        if pattern.match(line):
                            count += 1
            except OSError:
                pass
        return count

    def _find_test_binary(self):
        for root, _dirs, files in os.walk(self.build_folder):
            if "libphonenumber_test" in files:
                return os.path.join(root, "libphonenumber_test")
        return None

    def _emit_upstream_result(self, result):
        """Dual-channel emit + persist upstream marker (cache-hit proof).

        cthreadpool/ayatana-ido precedent: `conan create` skips build()
        entirely when the binary is cached ("Already installed!"), so a
        marker printed only in build() disappears on the next preflight.
        Persist the real in-build result to build_folder and ship it via
        package() res/; test_package re-emits it every run. print() +
        output.info dual channel: HMBS scrapes raw stdout.
        """
        text = json.dumps(result)
        try:
            with open(os.path.join(self.build_folder, "upstream_test_result.json"),
                      "w", encoding="utf-8") as _f:
                _f.write(text)
        except OSError:
            pass
        msg = "HMBS_UPSTREAM_TEST_RESULT=" + text
        print(msg, flush=True)
        self.output.info(msg)

    def _run_upstream_tests(self):
        discovered = self._count_upstream_tests()
        test_bin = self._find_test_binary()
        command = "./libphonenumber_test"
        if test_bin is None:
            result = {
                        "status": "failed",
                        "framework": "gtest",
                        "command": command,
                        "discovered": discovered,
                        "executed": 0,
                        "passed": 0,
                        "failed": 0,
                        "skipped": 0,
                        "reason": "libphonenumber_test binary not found in build folder",
                    }
            self._emit_upstream_result(result)
            raise ConanException("libphonenumber_test binary not found")
        try:
            tmpdir = self._writable_tmpdir()
            try:
                os.makedirs(tmpdir, exist_ok=True)
            except OSError:
                pass
            run_env = dict(os.environ)
            run_env["TMPDIR"] = tmpdir
            run_env["TMP"] = tmpdir
            run_env["TEMP"] = tmpdir
            run_env["TEST_TMPDIR"] = tmpdir
            # Authoritative discovered count: ask gtest itself. Static TEST
            # macro grep undercounts value-parameterized expansions
            # (TEST_P/INSTANTIATE expands to N runtime cases per macro),
            # so executed > static count is legitimate. --gtest_list_tests
            # enumerates the expanded cases; use it when available so
            # discovered/executed stay consistent without touching caliber.
            try:
                list_proc = subprocess.run(
                    [test_bin, "--gtest_list_tests"],
                    cwd=os.path.dirname(test_bin),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    timeout=300,
                    env=run_env,
                )
                listed = 0
                for _line in (list_proc.stdout or "").splitlines():
                    if _line.startswith(" ") or _line.startswith("\t"):
                        if _line.strip():
                            listed += 1
                if list_proc.returncode == 0 and listed > 0:
                    if listed != discovered:
                        self.output.info(
                            "upstream discover: static macro count %d, "
                            "gtest list %d; using gtest enumeration"
                            % (discovered, listed))
                    discovered = listed
            except Exception as exc:
                self.output.info(
                    "gtest list fallback to static count %d: %r"
                    % (discovered, exc))
            proc = subprocess.run(
                [test_bin],
                cwd=os.path.dirname(test_bin),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=1800,
                env=run_env,
            )
            output = proc.stdout or ""
            rc = proc.returncode
        except Exception as exc:
            result = {
                        "status": "failed",
                        "framework": "gtest",
                        "command": command,
                        "discovered": discovered,
                        "executed": 0,
                        "passed": 0,
                        "failed": 0,
                        "skipped": 0,
                        "reason": "test harness could not run: %r" % (exc,),
                    }
            self._emit_upstream_result(result)
            raise
        ran = 0
        passed = 0
        failed = 0
        skipped = 0
        m = re.search(r"\[\s*PASSED\s*\]\s*(\d+)\s+tests?\.", output)
        if m:
            passed = int(m.group(1))
        m = re.search(r"\[\s*FAILED\s*\]\s*(\d+)\s+tests?", output)
        if m:
            failed = int(m.group(1))
        m = re.search(r"\[\s*SKIPPED\s*\]\s*(\d+)\s+tests?", output)
        if m:
            skipped = int(m.group(1))
        m = re.search(r"(\d+)\s+tests?\s+from\s+\d+\s+test suites?\s+ran", output)
        if m:
            ran = int(m.group(1))
        else:
            ran = passed + failed + skipped
        if discovered <= 0:
            discovered = ran
        self.output.info(output[-4000:])
        if rc == 0 and failed == 0 and ran > 0 and passed == ran - skipped:
            result = {
                "status": "passed",
                "framework": "gtest",
                "command": command,
                "discovered": discovered,
                "executed": ran,
                "passed": passed,
                "failed": 0,
                "skipped": skipped,
            }
        elif rc == 0 and ran == 0:
            result = {
                "status": "failed",
                "framework": "gtest",
                "command": command,
                "discovered": discovered,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "exit 0 but no gtest tests ran (silent skip)",
            }
        else:
            result = {
                "status": "failed",
                "framework": "gtest",
                "command": command,
                "discovered": discovered,
                "executed": ran,
                "passed": passed,
                "failed": failed if failed else max(1, ran - passed),
                "skipped": skipped,
            }
        self._emit_upstream_result(result)
        if result["status"] != "passed":
            raise ConanException("libphonenumber upstream tests failed")

    def _validated_compilers(self):
        """Resolve validated C/CXX compilers (absolute conf path first)."""
        cxx = cc = None
        try:
            conf = self.conf.get("tools.build:compiler_executables", default=None)
        except Exception:
            conf = None
        if isinstance(conf, dict):
            cand_c = conf.get("c")
            cand_cxx = conf.get("cpp") or conf.get("cxx")
            if cand_c and os.path.isfile(cand_c) and os.access(cand_c, os.X_OK):
                cc = cand_c
            if cand_cxx and os.path.isfile(cand_cxx) and os.access(cand_cxx, os.X_OK):
                cxx = cand_cxx
        if cc is None:
            for name in ("clang", "cc", "gcc"):
                found = shutil.which(name)
                if found:
                    cc = found
                    break
        if cxx is None:
            for name in ("clang++", "c++", "g++"):
                found = shutil.which(name)
                if found:
                    cxx = found
                    break
        return cc, cxx

    def _smoke_test_toolchain(self):
        """Direct-cc smoke test so real toolchain faults surface raw stderr.

        Compiles and links a minimal C and C++ program with the validated
        compilers inside the writable TMPDIR. Compile/link failure raises
        with the original compiler stderr (no masking by
        CMAKE_C_COMPILER_WORKS). Running the binaries is best-effort only:
        the sandbox may lack +x support (HMBS_CAP_CHMOD=0), so a run
        failure never fails the build here.
        """
        if str(self.settings.os) != "OHOS":
            return
        cc, cxx = self._validated_compilers()
        if cc is None or cxx is None:
            raise ConanException(
                "no validated C/CXX compiler (conf tools.build:compiler_executables nor PATH)"
            )
        tmpdir = self._export_writable_tmpdir()
        run_env = dict(os.environ)
        run_env["TMPDIR"] = tmpdir
        run_env["TMP"] = tmpdir
        run_env["TEMP"] = tmpdir
        c_src = os.path.join(tmpdir, "hmbs_cc_smoke.c")
        cxx_src = os.path.join(tmpdir, "hmbs_cxx_smoke.cc")
        c_bin = os.path.join(tmpdir, "hmbs_cc_smoke")
        cxx_bin = os.path.join(tmpdir, "hmbs_cxx_smoke")
        try:
            with open(c_src, "w", encoding="utf-8") as f:
                f.write("int main(void){return 0;}\n")
            with open(cxx_src, "w", encoding="utf-8") as f:
                f.write("int main(){return 0;}\n")
        except OSError as exc:
            raise ConanException("smoke test sources not writable: %r" % (exc,))
        for compiler, src, out in ((cc, c_src, c_bin), (cxx, cxx_src, cxx_bin)):
            proc = subprocess.run(
                [compiler, src, "-o", out],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=300,
                env=run_env,
            )
            log = proc.stdout or ""
            self.output.info("toolchain smoke %s: exit %d\n%s" % (compiler, proc.returncode, log[-2000:]))
            if proc.returncode != 0:
                raise ConanException(
                    "toolchain smoke compile failed for %s (exit %d): %s"
                    % (compiler, proc.returncode, log[-2000:])
                )
        for out in (c_bin, cxx_bin):
            try:
                proc = subprocess.run(
                    [out],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    timeout=60,
                    env=run_env,
                )
                self.output.info("toolchain smoke run %s: exit %d" % (out, proc.returncode))
            except Exception as exc:
                self.output.info("toolchain smoke run skipped for %s: %r" % (out, exc))

    def _dep_flags(self):
        """Assemble include/lib/link items from the real dependency graph.

        Component-aware: googletest/1.12.1 declares its libraries only as
        components (gtest/gmock, no top-level cpp_info.libs), so reading
        only top-level libs drops -lgtest and the test link fails with
        undefined testing:: symbols. Aggregate component libs too. Skip
        *_main components: upstream links TEST_LIBS=phonenumber_testing +
        GTEST_LIB(gtest) because run_tests.cc provides its own main(), so
        linking gtest_main/gmock_main would duplicate main.
        """
        includes, libdirs, libs, systems, defines = [], [], [], [], []

        def _dedup(seq):
            return list(dict.fromkeys(seq))

        for dep in self.dependencies.values():
            try:
                info = dep.cpp_info
            except Exception:
                continue
            includes += list(getattr(info, "includedirs", None) or [])
            libdirs += list(getattr(info, "libdirs", None) or [])
            libs += list(getattr(info, "libs", None) or [])
            systems += list(getattr(info, "system_libs", None) or [])
            defines += list(getattr(info, "defines", None) or [])
            try:
                components = info.components
            except Exception:
                components = None
            if components:
                try:
                    items = list(components.values())
                except Exception:
                    items = []
                for comp in items:
                    try:
                        comp_libs = list(getattr(comp, "libs", None) or [])
                    except Exception:
                        comp_libs = []
                    # run_tests.cc defines main(); *_main would conflict.
                    comp_libs = [l for l in comp_libs if not l.endswith("_main")]
                    libs += comp_libs
                    try:
                        includes += list(getattr(comp, "includedirs", None) or [])
                        libdirs += list(getattr(comp, "libdirs", None) or [])
                        systems += list(getattr(comp, "system_libs", None) or [])
                        defines += list(getattr(comp, "defines", None) or [])
                    except Exception:
                        pass
        return (
            _dedup(includes),
            _dedup(libdirs),
            _dedup(libs),
            _dedup(systems),
            _dedup(defines),
        )

    def _archiver(self):
        for name in ("llvm-ar", "ar"):
            found = shutil.which(name)
            if found:
                return found
        raise ConanException("no archiver found (llvm-ar nor ar on PATH)")

    def _lib_sources(self):
        # Mirrors upstream cpp/CMakeLists.txt SOURCES + GEOCODING_SOURCES for
        # the selected options (USE_ICU_REGEXP=ON, USE_ALTERNATE_FORMATS=ON,
        # USE_LITE_METADATA=OFF, REGENERATE_METADATA=OFF using shipped files).
        src = os.path.join(self._cpp_dir(), "src", "phonenumbers")
        rel = [
            "asyoutypeformatter.cc",
            "base/strings/string_piece.cc",
            "default_logger.cc",
            "logger.cc",
            "phonemetadata.pb.cc",
            "phonenumber.cc",
            "phonenumber.pb.cc",
            "phonenumberutil.cc",
            "regex_based_matcher.cc",
            "regexp_cache.cc",
            "shortnumberinfo.cc",
            "string_byte_sink.cc",
            "stringutil.cc",
            "unicodestring.cc",
            "utf/rune.c",
            "utf/unicodetext.cc",
            "utf/unilib.cc",
            "regexp_adapter_icu.cc",
            "phonenumbermatch.cc",
            "phonenumbermatcher.cc",
            "alternate_format.cc",
            "metadata.cc",
            "short_metadata.cc",
        ]
        geo = [
            "geocoding/area_code_map.cc",
            "geocoding/default_map_storage.cc",
            "geocoding/geocoding_data.cc",
            "geocoding/mapping_file_provider.cc",
            "geocoding/phonenumber_offline_geocoder.cc",
        ]
        return [os.path.join(src, p) for p in rel], [os.path.join(src, p) for p in geo]

    def _test_sources(self):
        # Mirrors upstream TEST_SOURCES for BUILD_GEOCODER=ON + USE_ICU_REGEXP.
        t = os.path.join(self._cpp_dir(), "test", "phonenumbers")
        rel = [
            "asyoutypeformatter_test.cc",
            "logger_test.cc",
            "matcher_test.cc",
            "phonenumberutil_test.cc",
            "regexp_adapter_test.cc",
            "regexp_cache_test.cc",
            "run_tests.cc",
            "shortnumberinfo_test.cc",
            "stringutil_test.cc",
            "test_util.cc",
            "unicodestring_test.cc",
            "utf/unicodetext_test.cc",
            "phonenumbermatch_test.cc",
            "phonenumbermatcher_test.cc",
            "geocoding/area_code_map_test.cc",
            "geocoding/geocoding_data_test.cc",
            "geocoding/geocoding_test_data.cc",
            "geocoding/mapping_file_provider_test.cc",
            "geocoding/phonenumber_offline_geocoder_test.cc",
        ]
        return [os.path.join(t, p) for p in rel]

    def _testing_metadata_source(self):
        # Mirrors upstream cpp/CMakeLists.txt TESTING_LIBRARY_SOURCES: the
        # testing library snapshots SOURCES *before* metadata.cc is appended,
        # then adds test_metadata.cc instead. The unit tests state explicitly
        # ("these tests use the metadata contained in the test metadata file,
        # not the normal metadata file") and encode the small test dataset
        # (e.g. US NATIONAL "650 253 0000" vs real "(650) 253-0000"). Linking
        # the production metadata.cc into libphonenumber_test therefore fails
        # ~74 cases with real-data formatting/validation mismatches. The
        # production archives keep metadata.cc; only the test binary swaps it
        # for test_metadata.cc (same metadata_get/metadata_size symbols, so
        # the two objects must never be linked together).
        src = os.path.join(self._cpp_dir(), "src", "phonenumbers", "test_metadata.cc")
        if not os.path.isfile(src):
            raise ConanException("upstream testing metadata missing: %s" % src)
        try:
            if os.path.getsize(src) <= 0:
                raise ConanException("upstream testing metadata empty: %s" % src)
        except OSError:
            raise ConanException("upstream testing metadata unreadable: %s" % src)
        return src

    def _compile_objects(self, cxx, cc, sources, objdir, includes, defines, env):
        objects = []
        for src in sources:
            if not os.path.isfile(src):
                # Generated files absent from the archive (e.g. a data .cc
                # the CMake build would generate): fail loudly with the
                # concrete path instead of silently changing test caliber.
                raise ConanException("upstream source missing: %s" % src)
            base = os.path.relpath(src, self._cpp_dir()).replace(os.sep, "_")
            obj = os.path.join(objdir, base + ".o")
            is_c = src.endswith(".c") and not src.endswith(".cc")
            compiler = cc if is_c else cxx
            # rune.c is C: clang rejects '-std=c++17' with
            # "invalid argument '-std=c++17' not allowed with 'C'".
            # Mirror upstream (CMake compiles it as C with default std).
            std_flag = [] if is_c else ["-std=c++17"]
            cmd = [compiler] + std_flag + ["-O2", "-fPIC", "-c", src, "-o", obj]
            # Deliberately no -Werror: upstream adds -Wall -Werror for
            # non-Windows, which turns OHOS clang warnings into errors.
            cmd += ["-Wall"]
            cmd += ["-D" + d for d in defines]
            cmd += ["-I" + os.path.join(self._cpp_dir(), "src")]
            cmd += ["-I" + os.path.join(self._cpp_dir(), "test")]
            cmd += ["-I" + d for d in includes if os.path.isdir(d)]
            cmd += ["-DI18N_PHONENUMBERS_USE_ALTERNATE_FORMATS"]
            cmd += ["-DI18N_PHONENUMBERS_USE_STDMUTEX"]
            cmd += ["-DI18N_PHONENUMBERS_USE_ICU_REGEXP"]
            self.output.info("direct-cc: " + " ".join(cmd))
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=900,
                env=env,
            )
            self.output.info((proc.stdout or "")[-2000:])
            if proc.returncode != 0:
                raise ConanException(
                    "direct-cc compile failed for %s (exit %d)" % (src, proc.returncode)
                )
            objects.append(obj)
        return objects

    def _build_geocoding_data(self, cxx, env, includes, defines):
        """Ensure geocoding data .cc files exist (shipped-first, no CMake).

        Cycle 10 (different from cycle 9's hardcoded generator path, which
        the 2026-09-13 re-run proved wrong: tools/cpp has no top-level
        generate_geocoding_data.cc): the upstream archive ships
        pre-generated geocoding_data.cc / geocoding_test_data.cc in the
        source tree (the CMake custom_command OUTPUTs point into
        CMAKE_CURRENT_SOURCE_DIR). If both files exist non-empty, reuse
        them and skip generation. Otherwise build the generator from its
        real sources (tools/cpp/src/cpp-build/*.cc per tools/cpp
        CMakeLists.txt) and run it over resources. Uses only shipped
        upstream sources; no test is skipped.
        """
        cpp_dir = self._cpp_dir()
        out_main = os.path.join(cpp_dir, "src", "phonenumbers", "geocoding", "geocoding_data.cc")
        out_test = os.path.join(cpp_dir, "test", "phonenumbers", "geocoding", "geocoding_test_data.cc")

        def _usable(path):
            try:
                return os.path.isfile(path) and os.path.getsize(path) > 0
            except OSError:
                return False

        if _usable(out_main) and _usable(out_test):
            self.output.info(
                "direct-cc gendata: reusing shipped geocoding_data.cc (%d bytes) and geocoding_test_data.cc (%d bytes)"
                % (os.path.getsize(out_main), os.path.getsize(out_test)))
            return
        tools_dir = os.path.normpath(os.path.join(cpp_dir, "..", "tools", "cpp"))
        gen_srcs = [
            os.path.join(tools_dir, "src", "cpp-build", "generate_geocoding_data.cc"),
            os.path.join(tools_dir, "src", "cpp-build", "generate_geocoding_data_main.cc"),
        ]
        for s in gen_srcs:
            if not os.path.isfile(s):
                found = glob.glob(os.path.join(tools_dir, "**", "generate_geocoding_data*.cc"), recursive=True)
                raise ConanException(
                    "generator source missing: %s (tools dir listing: %s)" % (s, sorted(found)))
        objdir = os.path.join(self.build_folder, "objs-tools")
        try:
            os.makedirs(objdir, exist_ok=True)
        except OSError:
            pass
        gen_bin = os.path.join(objdir, "generate_geocoding_data")
        cmd = [cxx, "-std=c++17", "-O1"] + gen_srcs + ["-o", gen_bin]
        cmd += ["-I" + os.path.join(tools_dir, "src")]
        cmd += ["-I" + os.path.join(cpp_dir, "src")]
        cmd += ["-I" + d for d in includes if os.path.isdir(d)]
        self.output.info("direct-cc generator: " + " ".join(cmd))
        proc = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, timeout=900, env=env,
        )
        self.output.info((proc.stdout or "")[-2000:])
        if proc.returncode != 0:
            raise ConanException("generator build failed (exit %d)" % proc.returncode)
        res_geo = os.path.normpath(os.path.join(cpp_dir, "..", "resources", "geocoding"))
        res_test = os.path.normpath(os.path.join(cpp_dir, "..", "resources", "test", "geocoding"))
        for indir, out, extra in ((res_geo, out_main, []), (res_test, out_test, ["_test"])):
            if _usable(out):
                continue
            cmd = [gen_bin, indir, out] + extra
            self.output.info("direct-cc gendata: " + " ".join(cmd))
            proc = subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, timeout=900, env=env,
            )
            self.output.info((proc.stdout or "")[-2000:])
            if proc.returncode != 0 or not _usable(out):
                raise ConanException("geocoding data generation failed for %s" % indir)

    def _find_protoc(self, env):
        """Locate the protoc binary from the protobuf dep first, PATH second."""
        candidates = []
        try:
            dep = self.dependencies["protobuf"]
            pkg = getattr(dep, "package_folder", None)
            if pkg:
                candidates.append(os.path.join(pkg, "bin", "protoc"))
                try:
                    for b in (getattr(dep.cpp_info, "bindirs", None) or []):
                        candidates.append(os.path.join(pkg, b, "protoc"))
                except Exception:
                    pass
        except Exception:
            pass
        which_protoc = shutil.which("protoc", path=env.get("PATH"))
        if which_protoc:
            candidates.append(which_protoc)
        for cand in candidates:
            try:
                if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
                    return cand
            except OSError:
                continue
        return None

    def _generate_protobuf_sources(self, env):
        """Run protoc for upstream .proto files (replaces CMake's generation).

        Upstream cpp/CMakeLists.txt generates phonemetadata.pb.{h,cc} and
        phonenumber.pb.{h,cc} via protoc; the direct-cc path deleted that
        step, so asyoutypeformatter.cc fails with
        'phonenumbers/phonemetadata.pb.h file not found'. Generate in-source
        under cpp/src (same layout the -I cpp/src compile flags expect) so
        no include change is needed. Only generates; no test is skipped.
        """
        src_root = os.path.join(self._cpp_dir(), "src")
        out_dir = os.path.join(src_root, "phonenumbers")
        # Upstream layout (cpp/CMakeLists.txt): RESOURCES_DIR is
        # <source>/resources, PROTOBUF_SOURCES are
        # resources/phonemetadata.proto + resources/phonenumber.proto, and
        # protoc runs as:
        #   protoc --cpp_out=cpp/src/phonenumbers/ --proto_path=resources ...
        # The previous cycle wrongly globbed cpp/src for *.proto (that tree
        # ships no .proto at all, hence the 'no .proto files found' failure);
        # mirror the CMake paths exactly instead.
        res_dir = os.path.normpath(os.path.join(self._cpp_dir(), "..", "resources"))
        proto_files = [
            os.path.join(res_dir, "phonemetadata.proto"),
            os.path.join(res_dir, "phonenumber.proto"),
        ]
        missing_proto = [p for p in proto_files if not os.path.isfile(p)]
        if missing_proto:
            listing = sorted(glob.glob(os.path.join(res_dir, "*")))[:50]
            raise ConanException(
                "upstream .proto missing: %s (resources listing: %s)"
                % (missing_proto, listing))
        pb_headers = [
            os.path.join(src_root, "phonenumbers", "phonemetadata.pb.h"),
            os.path.join(src_root, "phonenumbers", "phonenumber.pb.h"),
        ]

        def _usable(path):
            try:
                return os.path.isfile(path) and os.path.getsize(path) > 0
            except OSError:
                return False

        if all(_usable(p) for p in pb_headers):
            self.output.info("direct-cc protoc: reusing shipped *.pb.h")
            return
        protoc = self._find_protoc(env)
        if protoc is None:
            raise ConanException(
                "protoc not found (protobuf dep bin nor PATH); "
                "proto files: %s" % proto_files)
        for proto in proto_files:
            self.output.info("direct-cc protoc source: %s (%d bytes)"
                             % (proto, os.path.getsize(proto)))
        cmd = ([protoc, "--cpp_out=" + out_dir, "--proto_path=" + res_dir]
               + proto_files)
        self.output.info("direct-cc protoc: " + " ".join(cmd))
        proc = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, timeout=600, env=env,
        )
        self.output.info((proc.stdout or "")[-2000:])
        if proc.returncode != 0:
            raise ConanException(
                "protoc failed (exit %d)" % proc.returncode)
        missing = [p for p in pb_headers if not _usable(p)]
        if missing:
            generated = sorted(glob.glob(
                os.path.join(src_root, "**", "*.pb.*"), recursive=True))
            raise ConanException(
                "protoc did not produce %s (generated: %s)"
                % (missing, generated))

    def _protobuf_utf8_libs(self):
        """Find utf8_range libs shipped inside the protobuf package.

        protobuf>=30 builds third_party/utf8_range as separate static
        libs (utf8_validity, utf8_range) installed under <pkg>/lib, but
        archives/p/protobuf/33.6 exposes only ["protobuf"] via
        cpp_info.libs, so _dep_flags() misses them and the test link
        fails with undefined utf8_range_IsValid/ValidPrefix referenced
        by libprotobuf.a (generated_message_tctable_lite.cc,
        parse_context.cc). Scan the real package lib dir; fall back to
        the upstream canonical names when the dir is unreadable so the
        failure stays loud instead of silently changing link caliber.
        """
        found = []
        try:
            dep = self.dependencies["protobuf"]
            pkg = getattr(dep, "package_folder", None)
        except Exception:
            pkg = None
        if pkg:
            libdir = os.path.join(pkg, "lib")
            try:
                files = os.listdir(libdir)
            except OSError:
                files = []
            for fn in files:
                low = fn.lower()
                if not low.startswith("libutf8"):
                    continue
                if low.endswith(".a") or low.endswith(".so") or low.endswith(".dylib"):
                    name = fn[3:] if fn.startswith("lib") else fn
                    for ext in (".a", ".so", ".dylib"):
                        if name.endswith(ext):
                            name = name[: -len(ext)]
                            break
                    # Strip version suffixes like .so.1
                    name = name.split(".")[0]
                    if name and name not in found:
                        found.append(name)
            if found:
                self.output.info(
                    "direct-cc utf8_range: found in protobuf lib: %s" % sorted(found))
                # Link validity before range (validity is the lower layer).
                order = {"utf8_validity": 0, "utf8_range": 1}
                found.sort(key=lambda n: order.get(n, 99))
                return found
            self.output.info(
                "direct-cc utf8_range: no libutf8* in %s (listing %d files), "
                "falling back to canonical names" % (libdir, len(files)))
        return ["utf8_validity", "utf8_range"]

    def build(self):
        apply_conandata_patches(self)
        tmpdir = self._export_writable_tmpdir()
        self._smoke_test_toolchain()
        cc, cxx = self._validated_compilers()
        if cc is None or cxx is None:
            raise ConanException("no validated C/CXX compiler for direct build")
        env = dict(os.environ)
        env["TMPDIR"] = tmpdir
        env["TMP"] = tmpdir
        env["TEMP"] = tmpdir
        env["TEST_TMPDIR"] = tmpdir
        includes, libdirs, libs, systems, defines = self._dep_flags()
        for extra in self._protobuf_utf8_libs():
            if extra not in libs:
                libs.append(extra)
        self.output.info("direct-cc link libs (with utf8 fix): %s" % libs)
        self._generate_protobuf_sources(env)
        self._build_geocoding_data(cxx, env, includes, defines)
        objdir = os.path.join(self.build_folder, "objs")
        try:
            os.makedirs(objdir, exist_ok=True)
        except OSError:
            pass
        lib_srcs, geo_srcs = self._lib_sources()
        lib_objs = self._compile_objects(cxx, cc, lib_srcs, objdir, includes, defines, env)
        geo_objs = self._compile_objects(cxx, cc, geo_srcs, objdir, includes, defines, env)
        ar = self._archiver()
        lib_phone = os.path.join(self.build_folder, "libphonenumber.a")
        lib_geo = os.path.join(self.build_folder, "libgeocoding.a")
        for lib, objs in ((lib_phone, lib_objs), (lib_geo, geo_objs)):
            cmd = [ar, "rcs", lib] + objs
            self.output.info("direct-cc archive: " + lib + " (%d objs)" % len(objs))
            proc = subprocess.run(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, timeout=900, env=env,
            )
            self.output.info((proc.stdout or "")[-2000:])
            if proc.returncode != 0:
                raise ConanException("archiving failed for %s" % lib)
        # Upstream test binary: testing library objects + gtest sources. The
        # testing library uses test_metadata.cc INSTEAD of metadata.cc (same
        # symbols, mutually exclusive); linking the production metadata here
        # fails ~74 format/parse cases against test expectations.
        test_objs = self._compile_objects(
            cxx, cc, self._test_sources(), objdir, includes, defines, env
        )
        test_metadata_objs = self._compile_objects(
            cxx, cc, [self._testing_metadata_source()], objdir, includes, defines, env
        )
        # Keep every production object except the real metadata.cc object;
        # short_metadata.cc is shared by both libraries and stays.
        testing_lib_objs = [
            o for o in lib_objs
            if os.path.basename(o) != "src_phonenumbers_metadata.cc.o"
        ] + test_metadata_objs
        self.output.info(
            "direct-cc testing metadata swap: excluded src_phonenumbers_metadata.cc.o, "
            "added %s" % test_metadata_objs)
        test_bin = os.path.join(self.build_folder, "libphonenumber_test")
        cmd = [cxx, "-o", test_bin] + testing_lib_objs + geo_objs + test_objs
        cmd += ["-L" + d for d in libdirs if os.path.isdir(d)]
        if libs:
            cmd += ["-Wl,--start-group"] + ["-l" + lib for lib in libs] + ["-Wl,--end-group"]
        cmd += ["-l" + s for s in systems]
        cmd += ["-pthread"]
        self.output.info("direct-cc link test: " + " ".join(cmd))
        proc = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, timeout=900, env=env,
        )
        self.output.info((proc.stdout or "")[-3000:])
        if proc.returncode != 0:
            raise ConanException("test link failed (exit %d)" % proc.returncode)
        if can_run(self):
            self._run_upstream_tests()
        else:
            # Cross-build: cannot execute, but never go silent (HMBS would
            # judge `incomplete` for a missing marker). Emit explicit failed
            # evidence instead of skipping so the gate sees a loud reason.
            self._emit_upstream_result({
                "status": "failed",
                "framework": "gtest",
                "command": "./libphonenumber_test",
                "discovered": self._count_upstream_tests(),
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "can_run is False, test binary cannot execute here",
            })
            raise ConanException("libphonenumber upstream tests require can_run")

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        # Ship the real in-build upstream result so test_package can re-emit
        # HMBS_UPSTREAM_TEST_RESULT on cache-hit preflights where build() is
        # skipped ("Already installed!"). cthreadpool precedent.
        _upstream_src = os.path.join(self.build_folder, "upstream_test_result.json")
        if os.path.isfile(_upstream_src):
            _res_dir = os.path.join(self.package_folder, "res")
            try:
                os.makedirs(_res_dir, exist_ok=True)
            except OSError:
                pass
            copy(self, "upstream_test_result.json",
                 src=self.build_folder, dst=_res_dir, keep_path=False)
        else:
            self.output.warning("upstream_test_result.json not found in build "
                                "folder; package will lack upstream evidence")
        for lib in ("libphonenumber.a", "libgeocoding.a"):
            src = os.path.join(self.build_folder, lib)
            if os.path.isfile(src):
                copy(self, lib, src=self.build_folder, dst=os.path.join(self.package_folder, "lib"))
        src_inc = os.path.join(self._cpp_dir(), "src", "phonenumbers")
        for root, _dirs, files in os.walk(src_inc):
            for fn in files:
                if fn.endswith(".h"):
                    rel = os.path.relpath(os.path.join(root, fn), os.path.join(self._cpp_dir(), "src"))
                    copy(self, fn, src=root, dst=os.path.join(self.package_folder, "include", os.path.dirname(rel)))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libphonenumber")
        self.cpp_info.libs = ["geocoding", "phonenumber"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs.append("pthread")
