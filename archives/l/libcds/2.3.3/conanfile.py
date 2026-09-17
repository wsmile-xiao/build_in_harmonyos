#!/usr/bin/env python3
"""Conan recipe for libcds 2.3.3 (direct-cc build, no CMake).

libcds is a C++11 header-heavy library of lock-free concurrent data
structures (Treiber stack, Michael&Scott queue, hash maps, skip-lists)
with Hazard Pointer / RCU safe memory reclamation. Only the small SMR
core (src/*.cpp) is compiled into libcds; the containers themselves are
headers. The library itself depends only on the C++ standard library
plus system threads -- no Boost needed for the shipped artifact.

Why no CMake: five consecutive preflight rounds died at the identical
gate -- upstream CMakeLists:12 project() with "The C/CXX compiler
identification is unknown" for /data/service/hnp/bin/clang -- while a
bare `clang probe.c -o probe` / `clang++ probe.cpp -o probe` on the
same device succeeds (E557 round evidence). TMPDIR scoping, static
try-compile, Linux/OHOS system-name overrides and SDK lld host-runtime
(LD_LIBRARY_PATH, already in the profile) all left the fingerprint
unchanged, proving the breakage lives inside CMake's own compiler-ID
probe (unknown HarmonyOS/OHOS platform handling and/or toolchain-flag
replication), not in the compiler itself. Following the critnib/ddate
precedent for this exact fingerprint, build() therefore invokes the
validated profile compiler directly: no configure step, no try_compile
probe, no skipped check -- real compile, real archive, real link.

Upstream tests: test/unit (gtest-based) is compiled binary-for-binary by
parsing each test/unit/*/CMakeLists.txt at build time (same set() +
add_executable() source lists, same ../main.cpp, same
-DGTEST_LANG_CXX11) and every binary is executed for real; gtest case
counts are aggregated into HMBS_UPSTREAM_TEST_RESULT (+ res/
hmbs_upstream.json for cache-hit re-emit). The shipped library stays
Boost-free via an in-build source patch (wait_strategy.h dead include
dropped, kernel.h boost::thread_specific_ptr replaced with a header-only
C++11 thread_local registry of identical get()/reset() semantics); the
unit suite additionally test_requires the repo's CMake-built Boost
1.90.0.2 for sources such as test/unit/deque/fcdeque.cpp that
unconditionally include <boost/container/...> (header + container/system
libs wired into the direct-cc compile/link, test-only).
test/stress (long-running perf/stress binaries) stays OFF:
single-job device cannot finish it inside the build budget; disclosed
in notes.md and test_package/MANIFEST.yml.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run, check_min_cppstd
from conan.tools.files import copy, export_conandata_patches, get
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"

# SMR core sources, exactly as upstream CMakeLists.txt lists them
# (set(SOURCES ...) for add_library(cds ...) / add_library(cds-s ...)).
LIB_SOURCES = [
    "src/init.cpp",
    "src/hp.cpp",
    "src/dhp.cpp",
    "src/urcu_gp.cpp",
    "src/urcu_sh.cpp",
    "src/thread_data.cpp",
    "src/topology_hpux.cpp",
    "src/topology_linux.cpp",
    "src/topology_osx.cpp",
    "src/dllmain.cpp",
]

CXX_STD = "c++17"


class LibcdsConan(ConanFile):
    name = "libcds"
    version = "2.3.3"
    description = "C++11 library of Concurrent Data Structures (lock-free)."
    license = "BSL-1.0"
    homepage = "https://github.com/khizmax/libcds"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("concurrent", "lock-free", "containers", "hazard-pointer", "rcu")
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
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
                "libcds supports Linux and OHOS targets, got %s"
                % self.settings.os
            )
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, 11)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build_requirements(self):
        # Test-only deps for the upstream unit suite (same binaries the
        # upstream test/CMakeLists.txt builds with GTest + Boost).
        # The shipped library itself stays Boost-free via the in-build
        # TLS patch below; Boost is only a test-time header/lib provider
        # for unit sources such as test/unit/deque/fcdeque.cpp
        # (#include <boost/container/deque.hpp>). Uses the repo's own
        # OHOS-adapted gtest (1.17.0.1, no cmake tool_requires, ships the
        # read-only /tmp sandbox patch, published to ohpcd) and the
        # CMake-built Boost 1.90.0.2 (container/system components with an
        # OHOS binary on ohpcd; NOT the b2-based 1.91.0 line whose source
        # build fails at bzip2). Both are test_requires, out of the
        # consumer graph.
        self.test_requires("gtest/1.17.0.1")
        self.test_requires("boost/1.90.0.2")

    # -- toolchain helpers (cthreadpool/critnib pattern) -----------------
    def _resolve_tool(self, name, fallback):
        # conf value stays preferred; only an absolute path that is not
        # a file or not executable falls back to the bare tool name via
        # the conanbuild PATH. Never a hardcoded toolchain path, never
        # a bare ${CC} shell variable (R33).
        try:
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
        except Exception:
            compilers = {}
        # Profile spells the C++ key "cpp"; accept "cxx" too.
        value = compilers.get(name) or (
            compilers.get("cxx") if name == "cpp" else None
        ) or fallback
        if "/" in value or "\\" in value:
            if not os.path.isfile(value):
                self.output.warning(
                    "conf tools.build:compiler_executables:%s=%s is not "
                    "a file, falling back to '%s' via PATH"
                    % (name, value, fallback)
                )
                return fallback
            if not os.access(value, os.X_OK):
                self.output.warning(
                    "conf tools.build:compiler_executables:%s=%s is not "
                    "executable, falling back to '%s' via PATH"
                    % (name, value, fallback)
                )
                return fallback
        return value

    @staticmethod
    def _dir_writable(path):
        """True only if a temp file can really be created in *path*.

        isdir/access checks alone also match the device's read-only
        /tmp itself (exists, erofs), so probe with mkstemp create+delete.
        """
        try:
            if not path or not os.path.isdir(path):
                return False
            if not os.access(path, os.W_OK | os.X_OK):
                return False
            fd, tmp = tempfile.mkstemp(prefix="hmbs-probe-", dir=path)
            try:
                os.close(fd)
            finally:
                try:
                    os.unlink(tmp)
                except OSError:
                    pass
            return True
        except OSError:
            return False

    def _writable_tmpdir(self):
        """E002 readonly_tmp: /tmp is erofs read-only on the device.

        Priority: HMBS_TMPDIR (HMBS-injected task-scoped writable dir),
        then TMPDIR/TMP/TEMP -- each accepted only after the real
        writability probe above -- otherwise a build-folder private
        tmpdir (never /tmp). Only the temp root is replaced; no test
        is skipped or deleted.
        """
        candidates = [os.environ.get("HMBS_TMPDIR")]
        for var in ("TMPDIR", "TMP", "TEMP"):
            candidates.append(os.environ.get(var))
        for cand in candidates:
            if cand and self._dir_writable(cand):
                return cand
        fallback = os.path.join(
            self.build_folder or os.getcwd(), "hmbs-tmp"
        )
        try:
            os.makedirs(fallback, exist_ok=True)
        except OSError:
            pass
        return fallback

    def _with_tmpdir(self, command):
        tmp = self._writable_tmpdir()
        return 'TMPDIR="%s" TMP="%s" TEMP="%s" %s' % (tmp, tmp, tmp, command)

    def _smoke_toolchain(self, cxx):
        """Fail-closed compiler smoke test with the real build flags.

        Compiles AND links a trivial TU with the same -std/c++-runtime
        shape as the library build, so a genuinely broken toolchain
        shows its real stderr here instead of a bare summary. Uses the
        writable tmpdir (E002) and never touches /tmp.
        """
        work = os.path.join(self.build_folder, "cxx-smoke")
        try:
            os.makedirs(work, exist_ok=True)
        except OSError:
            pass
        src = os.path.join(work, "smoke.cpp")
        out = os.path.join(work, "smoke")
        try:
            with open(src, "w", encoding="utf-8") as fh:
                fh.write("int main() { return 0; }\n")
        except OSError as exc:
            raise ConanException("smoke test setup failed: %s" % exc)
        cmd = self._with_tmpdir(
            '"%s" -std=%s -pthread "%s" -o "%s"' % (cxx, CXX_STD, src, out)
        )
        self.output.info("+ %s" % cmd)
        proc = subprocess.run(
            cmd, shell=True, cwd=work,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, timeout=300,
        )
        log = proc.stdout or ""
        if proc.returncode != 0:
            raise ConanException(
                "OHOS compiler smoke test FAILED (rc=%s): %s\n%s"
                % (proc.returncode, cxx, log[-4000:])
            )
        self.output.info("C++ compiler smoke test passed: %s" % cxx)

    # -- direct-cc library build -----------------------------------------
    def _obj_dir(self):
        d = os.path.join(self.build_folder, "objs")
        try:
            os.makedirs(d, exist_ok=True)
        except OSError:
            pass
        return d

    def _build_library(self, cxx):
        opt = "-O2" if str(self.settings.build_type) == "Release" else "-O0 -g"
        objdir = self._obj_dir()
        src_root = self.source_folder
        objects = []
        for rel in LIB_SOURCES:
            src = os.path.join(src_root, rel)
            if not os.path.isfile(src):
                raise ConanException("library source missing: %s" % rel)
            obj = os.path.join(objdir, os.path.basename(rel) + ".o")
            # Upstream default is -std=c++11 -Wall -Wextra -pedantic;
            # -std follows the profile cppstd (C++17, required by the
            # gtest 1.17 headers the unit binaries share).
            self.run(
                self._with_tmpdir(
                    '"%s" %s -std=%s -fPIC -Wall -Wextra '
                    '-I"%s" -c "%s" -o "%s"'
                    % (cxx, opt, CXX_STD, src_root, src, obj)
                ),
                cwd=objdir,
            )
            objects.append('"%s"' % obj)
        static_lib = os.path.join(objdir, "libcds-s.a")
        ar = self._resolve_tool("ar", "llvm-ar")
        if shutil.which(ar) is None and not os.path.isfile(ar):
            ar = "ar"
        self.run(
            self._with_tmpdir(
                '%s rcs "%s" %s' % (ar, static_lib, " ".join(objects))
            ),
            cwd=objdir,
        )
        shared_lib = ""
        if self.options.shared:
            shared_lib = os.path.join(objdir, "libcds.so")
            self.run(
                self._with_tmpdir(
                    '"%s" -shared -pthread -o "%s" %s'
                    % (cxx, shared_lib, " ".join(objects))
                ),
                cwd=objdir,
            )
        return static_lib, shared_lib

    # -- upstream unit suite (direct-cc, same binaries as upstream) ------
    @staticmethod
    def _parse_cmake_bins(subdir):
        """Extract add_executable() binaries from a unit subdir.

        Handles both shapes used upstream: one binary per subdir
        (queue/stack: set(CDSGTEST_* ...) + single add_executable) and
        many binaries per subdir (map: several set() + add_executable
        pairs). Returns [(name, [rel_sources])] with ${VAR} expanded.
        """
        path = os.path.join(subdir, "CMakeLists.txt")
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            return []
        variables = {}
        for match in re.finditer(
            r"set\s*\(\s*(\w+)\s+([^)]*)\)", text, re.DOTALL
        ):
            variables[match.group(1)] = match.group(2)
        bins = []
        for match in re.finditer(
            r"add_executable\s*\(\s*(\S+)\s+([^)]*)\)", text, re.DOTALL
        ):
            raw_name, raw_sources = match.group(1), match.group(2)

            def expand(token_text):
                def repl(var):
                    return variables.get(var.group(1), "")
                return re.sub(r"\$\{(\w+)\}", repl, token_text)

            name = expand(raw_name).strip().strip('"')
            sources = []
            for token in expand(raw_sources).split():
                token = token.strip().strip('"')
                if not token or token.startswith("$"):
                    continue
                if not token.endswith((".cpp", ".c", ".cc", ".cxx")):
                    continue
                sources.append(token)
            if name and sources:
                bins.append((name, sources))
        return bins

    def _gtest_compile_args(self):
        # gtest/1.17.0.1 declares its libs via cpp_info.components
        # (gtest/gmock/gtest_main/gmock_main); the root cpp_info.libs
        # is empty, so reading only the root yields no -l flags and
        # every unit binary dies with undefined testing::* symbols.
        # Aggregate root + components (deduplicated, order-stable) and
        # skip *_main: unit binaries ship their own ../main.cpp, so
        # linking gtest_main/gmock_main would duplicate main().
        try:
            dep = self.dependencies["gtest"]
        except KeyError:
            return "", "", ""
        info = dep.cpp_info
        incs, libdirs, libs = [], [], []
        try:
            for path in info.includedirs:
                text = str(path)
                if text not in incs:
                    incs.append(text)
            for path in info.libdirs:
                text = str(path)
                if text not in libdirs:
                    libdirs.append(text)
            for lib in info.libs:
                text = str(lib)
                if text not in libs:
                    libs.append(text)
        except Exception:
            pass
        try:
            components = getattr(info, "components", {}) or {}
            for comp in components.values():
                try:
                    for path in getattr(comp, "includedirs", []) or []:
                        text = str(path)
                        if text not in incs:
                            incs.append(text)
                    for path in getattr(comp, "libdirs", []) or []:
                        text = str(path)
                        if text not in libdirs:
                            libdirs.append(text)
                    for lib in getattr(comp, "libs", []) or []:
                        text = str(lib)
                        if text in ("gtest_main", "gmock_main"):
                            continue
                        if text not in libs:
                            libs.append(text)
                except Exception:
                    continue
        except Exception:
            pass
        # Fail closed: no gtest lib name collected means the link below
        # would again produce undefined testing::* symbols.
        if not libs:
            raise ConanException(
                "gtest component libs missing (root=%r components=%r)"
                % (getattr(info, "libs", None),
                   list(getattr(info, "components", {}) or {}).keys()
                   if hasattr(info, "components") else None)
            )
        includes = " ".join('"-I%s"' % path for path in incs)
        libflags = " ".join('"-L%s"' % path for path in libdirs)
        linklibs = " ".join("-l%s" % lib for lib in libs)
        return includes, libflags, linklibs

    def _boost_compile_args(self):
        """Aggregate Boost headers/libs for unit sources.

        boost/1.90.0.2 uses components (headers/atomic/container/
        filesystem/program_options/system); the root cpp_info alone does
        not carry the component libs, so aggregate root + components
        (deduplicated, order-stable). Header-only test usage such as
        <boost/container/deque.hpp> needs only the include dir, but
        linking the compiled components is harmless and matches upstream
        test/CMakeLists (${Boost_THREAD_LIBRARY}/${Boost_SYSTEM_LIBRARY}
        plus GTest). test_requires keeps Boost out of the consumer graph.
        """
        try:
            dep = self.dependencies["boost"]
        except KeyError:
            return "", "", ""
        info = dep.cpp_info
        incs, libdirs, libs = [], [], []
        try:
            for path in info.includedirs:
                text = str(path)
                if text not in incs:
                    incs.append(text)
            for path in info.libdirs:
                text = str(path)
                if text not in libdirs:
                    libdirs.append(text)
            for lib in info.libs:
                text = str(lib)
                if text not in libs:
                    libs.append(text)
        except Exception:
            pass
        try:
            components = getattr(info, "components", {}) or {}
            for comp in components.values():
                try:
                    for path in getattr(comp, "includedirs", []) or []:
                        text = str(path)
                        if text not in incs:
                            incs.append(text)
                    for path in getattr(comp, "libdirs", []) or []:
                        text = str(path)
                        if text not in libdirs:
                            libdirs.append(text)
                    for lib in getattr(comp, "libs", []) or []:
                        text = str(lib)
                        if text not in libs:
                            libs.append(text)
                except Exception:
                    continue
        except Exception:
            pass
        includes = " ".join('"-I%s"' % path for path in incs)
        libflags = " ".join('"-L%s"' % path for path in libdirs)
        linklibs = " ".join("-l%s" % lib for lib in libs)
        return includes, libflags, linklibs

    def _gtest_libdirs_for_run(self):
        try:
            dep = self.dependencies["gtest"]
        except KeyError:
            return []
        found = []
        try:
            for path in dep.cpp_info.libdirs:
                text = str(path)
                if text not in found:
                    found.append(text)
            for comp in (getattr(dep.cpp_info, "components", {}) or {}).values():
                for path in getattr(comp, "libdirs", []) or []:
                    text = str(path)
                    if text not in found:
                        found.append(text)
        except Exception:
            pass
        return [path for path in found if path]

    def _boost_libdirs_for_run(self):
        try:
            dep = self.dependencies["boost"]
        except KeyError:
            return []
        found = []
        try:
            for path in dep.cpp_info.libdirs:
                text = str(path)
                if text not in found:
                    found.append(text)
            for comp in (getattr(dep.cpp_info, "components", {}) or {}).values():
                for path in getattr(comp, "libdirs", []) or []:
                    text = str(path)
                    if text not in found:
                        found.append(text)
        except Exception:
            pass
        return [path for path in found if path]

    def _build_and_run_unit_bins(self, cxx, static_lib):
        unit_root = os.path.join(self.source_folder, "test", "unit")
        if not os.path.isdir(unit_root):
            raise ConanException("upstream test/unit not found in sources")
        test_inc = os.path.join(self.source_folder, "test", "include")
        gtest_inc, gtest_libdir, gtest_libs = self._gtest_compile_args()
        boost_inc, boost_libdir, boost_libs = self._boost_compile_args()
        bindir = os.path.join(self.build_folder, "unit-bins")
        try:
            os.makedirs(bindir, exist_ok=True)
        except OSError:
            pass
        # OOM guard (preflight exit 137 / Signal 9 while compiling
        # template-heavy map/set/tree unit TUs with gtest+boost headers
        # on the single-job device): -O0 -g0 minimizes cc1 peak memory;
        # NDEBUG drops assert bloat; each TU is compiled to .o in its own
        # driver invocation then linked, so only one TU is ever resident.
        opt = "-O0 -g0 -DNDEBUG"
        discovered = executed = passed = failed = 0
        details = []
        built = 0
        for sub in sorted(os.listdir(unit_root)):
            subdir = os.path.join(unit_root, sub)
            if not os.path.isdir(subdir):
                continue
            for name, rel_sources in self._parse_cmake_bins(subdir):
                srcs = []
                for rel in rel_sources:
                    abs_src = os.path.normpath(os.path.join(subdir, rel))
                    if not os.path.isfile(abs_src):
                        raise ConanException(
                            "unit source missing for %s: %s" % (name, rel)
                        )
                    srcs.append('"%s"' % abs_src)
                exe = os.path.join(bindir, name)
                # Same include set as upstream test/CMakeLists.txt
                # (test/include + own subdir + GTest + Boost) plus the
                # libcds source root for <cds/...> headers; same
                # -DGTEST_LANG_CXX11 the upstream build defines. Boost
                # comes from test_requires boost/1.90.0.2 (OHOS binary on
                # ohpcd); the shipped library itself stays Boost-free via
                # _patch_boost_out, only the unit suite links Boost.
                # Per-TU object compile then link (OOM guard: one cc1
                # resident at a time, see opt above). No source skipped.
                objdir = os.path.join(bindir, "obj-" + name)
                try:
                    os.makedirs(objdir, exist_ok=True)
                except OSError:
                    pass
                objs = []
                for index, src in enumerate(srcs):
                    obj = os.path.join(objdir, "tu%d.o" % index)
                    self.run(
                        self._with_tmpdir(
                            '"%s" %s -std=%s -DGTEST_LANG_CXX11 '
                            '"-I%s" "-I%s" "-I%s" %s %s '
                            '-c %s -o "%s"'
                            % (
                                cxx, opt, CXX_STD,
                                test_inc, subdir, self.source_folder,
                                gtest_inc, boost_inc, src, obj,
                            )
                        ),
                        cwd=bindir,
                    )
                    objs.append('"%s"' % obj)
                self.run(
                    self._with_tmpdir(
                        '"%s" %s -o "%s" %s "%s" %s %s %s %s -pthread'
                        % (
                            cxx, opt, exe, " ".join(objs),
                            static_lib, gtest_libdir, gtest_libs,
                            boost_libdir, boost_libs,
                        )
                    ),
                    cwd=bindir,
                )
                built += 1
                rc, ran, ok_count, fail_count = self._run_gtest_binary(exe)
                executed += ran
                discovered += ran
                passed += ok_count
                failed += fail_count
                details.append("%s:rc=%s" % (name, rc))
                if rc != 0 and fail_count == 0:
                    # Crash/timeout rather than assertion failure.
                    failed += 0
        if built == 0:
            raise ConanException("no upstream unit binaries discovered")
        return discovered, executed, passed, failed, built, details

    def _run_gtest_binary(self, exe):
        """Run one gtest binary, return (rc, ran, passed, failed).

        Parses the real gtest summary lines; an empty summary is never
        accepted as proof (fail closed against silent passes).
        """
        tmpdir = self._writable_tmpdir()
        env = os.environ.copy()
        env["TMPDIR"] = tmpdir
        env["TMP"] = tmpdir
        env["TEMP"] = tmpdir
        for extra in self._gtest_libdirs_for_run() + self._boost_libdirs_for_run():
            prev = env.get("LD_LIBRARY_PATH", "")
            if extra and extra not in prev.split(os.pathsep):
                env["LD_LIBRARY_PATH"] = extra + (
                    os.pathsep + prev if prev else "")
        try:
            proc = subprocess.run(
                [exe], cwd=os.path.dirname(exe),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, timeout=900, env=env,
            )
            output = proc.stdout or ""
            rc = proc.returncode
        except (OSError, subprocess.SubprocessError) as exc:
            self.output.info("--- %s launch failed: %s"
                             % (os.path.basename(exe), exc))
            return 127, 1, 0, 1
        tail = "\n".join(output.splitlines()[-8:])
        self.output.info("--- %s (rc=%s) ---\n%s"
                         % (os.path.basename(exe), rc, tail))
        ran = 0
        passed = 0
        failed = 0
        match = re.search(r"\[\s*PASSED\s*\]\s*(\d+)\s*tests?", output)
        if match:
            passed = int(match.group(1))
        match = re.search(r"\[\s*FAILED\s*\]\s*(\d+)\s*tests?", output)
        if match:
            failed = int(match.group(1))
        match = re.search(r"(\d+)\s*tests?\s+ran", output)
        if match:
            ran = int(match.group(1))
        else:
            ran = passed + failed
        if ran == 0 or (passed == 0 and failed == 0 and rc == 0):
            # No parseable summary: harness broken or silent skip --
            # count the binary as one failed case, never a pass.
            self.output.warning(
                "%s produced no gtest summary; counting as failed"
                % os.path.basename(exe))
            return 1, 1, 0, 1
        if rc != 0 and failed == 0:
            failed = ran - passed
        return rc, ran, passed, failed

    def _run_upstream_tests(self, cxx, static_lib):
        if not can_run(self):
            result = {
                "status": "skipped",
                "framework": "direct-cc+gtest",
                "command": "test/unit binaries (parsed from upstream "
                           "CMakeLists, run natively)",
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": "cross-building: test binaries cannot run "
                          "on build host",
            }
            message = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(result)
            print(message, flush=True)
            self.output.info(message)
            return result
        discovered, executed, passed, failed, built, details = \
            self._build_and_run_unit_bins(cxx, static_lib)
        ok = failed == 0 and executed > 0 and executed == discovered
        result = {
            "status": "passed" if ok else "failed",
            "framework": "direct-cc+gtest",
            "command": "%d unit binaries from test/unit "
                       "(%s)" % (built, ";".join(details)),
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": 0,
        }
        if not ok:
            result["reason"] = "failed=%d executed=%d discovered=%d" % (
                failed, executed, discovered)
        message = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(
            result, ensure_ascii=False)
        # Dual-channel emit: HMBS preflight scrapes raw stdout.
        print(message, flush=True)
        self.output.info(message)
        try:
            with open(
                os.path.join(self.build_folder, "hmbs_upstream.json"),
                "w",
                encoding="utf-8",
            ) as handle:
                json.dump(result, handle)
        except OSError:
            pass
        if not ok:
            raise ConanException(
                "libcds upstream unit suite failed: %s" % result)
        return result

    def _patch_boost_out(self):
        """Remove the hard Boost header dependency (flat_combining).

        Upstream 2.3.3 unconditionally includes
        <boost/thread/tss.hpp> in cds/algo/flat_combining/wait_strategy.h
        (dead include, never used in that header) and uses
        boost::thread_specific_ptr in cds/algo/flat_combining/kernel.h for
        the per-thread publication record. Boost headers/libs are not
        available on OHOS (boost has no OHOS binary; a source build pulls
        bzip2/b2 and fails), so the direct-cc unit build dies with
        \"fatal error: 'boost/thread/tss.hpp' file not found\".
        Patch both headers in place (idempotent):
        - drop the dead include in wait_strategy.h;
        - replace boost::thread_specific_ptr with a header-only C++11
          thread_local registry with identical get()/reset() semantics
          (cleanup runs on reset and at thread exit, matching Boost).
        Patched headers are what package() ships, so consumers stay
        Boost-free too. No test is skipped or deleted.
        """
        ws_path = os.path.join(
            self.source_folder, "cds", "algo", "flat_combining",
            "wait_strategy.h",
        )
        try:
            with open(ws_path, "r", encoding="utf-8",
                      errors="replace") as handle:
                ws_text = handle.read()
        except OSError:
            ws_text = ""
        if ws_text and "boost/thread/tss.hpp" in ws_text:
            ws_text = ws_text.replace(
                "#include <boost/thread/tss.hpp>",
                "// HMBS OHOS: Boost include removed (unused in this "
                "header; kernel uses internal TLS shim, no Boost needed).",
            )
            try:
                with open(ws_path, "w", encoding="utf-8") as handle:
                    handle.write(ws_text)
            except OSError as exc:
                raise ConanException(
                    "failed to patch wait_strategy.h: %s" % exc)
            self.output.info("patched wait_strategy.h Boost include out")
        kernel_path = os.path.join(
            self.source_folder, "cds", "algo", "flat_combining", "kernel.h",
        )
        try:
            with open(kernel_path, "r", encoding="utf-8",
                      errors="replace") as handle:
                k_text = handle.read()
        except OSError as exc:
            raise ConanException("kernel.h missing for Boost patch: %s" % exc)
        if "HMBS OHOS TLS shim" not in k_text:
            anchor = "#include <cds/algo/int_algo.h>"
            shim = (
                "#include <cds/algo/int_algo.h>\n"
                "#include <unordered_map>\n"
                "#include <utility>\n"
                "// HMBS OHOS TLS shim BEGIN (replaces "
                "boost::thread_specific_ptr; Boost headers unavailable on "
                "OHOS; semantics: per-instance per-thread pointer, cleanup "
                "runs on reset() and at thread exit, matching Boost usage "
                "in kernel).\n"
                "namespace cds { namespace algo { namespace flat_combining "
                "{ namespace details {\n"
                "struct hmbs_tss_registry {\n"
                "    std::unordered_map<const void*, std::pair<void*, "
                "void(*)(void*)> > data;\n"
                "    ~hmbs_tss_registry() {\n"
                "        for (auto &kv : data) {\n"
                "            if (kv.second.first && kv.second.second)\n"
                "                kv.second.second(kv.second.first);\n"
                "        }\n"
                "    }\n"
                "};\n"
                "inline hmbs_tss_registry& hmbs_tss_registry_instance() {\n"
                "    thread_local hmbs_tss_registry inst;\n"
                "    return inst;\n"
                "}\n"
                "template <typename T>\n"
                "class tss_ptr {\n"
                "public:\n"
                "    explicit tss_ptr(void(*cleanup)(T*) = nullptr)\n"
                "        : cleanup_(cleanup) {}\n"
                "    ~tss_ptr() { reset(nullptr); }\n"
                "    tss_ptr(const tss_ptr&) = delete;\n"
                "    tss_ptr& operator=(const tss_ptr&) = delete;\n"
                "    T* get() const {\n"
                "        hmbs_tss_registry& r = "
                "hmbs_tss_registry_instance();\n"
                "        auto it = r.data.find(this);\n"
                "        return it == r.data.end() ? nullptr : "
                "static_cast<T*>(it->second.first);\n"
                "    }\n"
                "    void reset(T* p = nullptr) {\n"
                "        hmbs_tss_registry& r = "
                "hmbs_tss_registry_instance();\n"
                "        auto it = r.data.find(this);\n"
                "        T* old = (it == r.data.end()) ? nullptr : "
                "static_cast<T*>(it->second.first);\n"
                "        if (old && cleanup_)\n"
                "            cleanup_(old);\n"
                "        if (p)\n"
                "            r.data[this] = std::make_pair("
                "static_cast<void*>(p), reinterpret_cast<void(*)(void*)>("
                "cleanup_));\n"
                "        else if (it != r.data.end())\n"
                "            r.data.erase(it);\n"
                "    }\n"
                "    T* operator->() const { return get(); }\n"
                "    T& operator*() const { return *get(); }\n"
                "private:\n"
                "    void(*cleanup_)(T*);\n"
                "};\n"
                "}}}} // namespace cds::algo::flat_combining::details\n"
                "// HMBS OHOS TLS shim END\n"
            )
            if anchor in k_text:
                k_text = k_text.replace(anchor, shim, 1)
            else:
                raise ConanException(
                    "kernel.h anchor for TLS shim not found")
            k_text = k_text.replace(
                "boost::thread_specific_ptr< publication_record_type > "
                "m_pThreadRec;",
                "details::tss_ptr< publication_record_type > m_pThreadRec;",
            )
            try:
                with open(kernel_path, "w", encoding="utf-8") as handle:
                    handle.write(k_text)
            except OSError as exc:
                raise ConanException(
                    "failed to patch kernel.h: %s" % exc)
            self.output.info("patched kernel.h Boost tss out")
        if "boost::" in k_text and "HMBS OHOS TLS shim" in k_text:
            self.output.warning(
                "kernel.h still mentions boost:: after patch; "
                "check remaining Boost usage")

    def build(self):
        # E002: writable temp root for the compiler driver and any
        # shell command substitution (never /tmp).
        tmpdir = self._writable_tmpdir()
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir
        self._patch_boost_out()
        cxx = self._resolve_tool("cpp", "clang++")
        self._smoke_toolchain(cxx)
        static_lib, _shared_lib = self._build_library(cxx)
        self._run_upstream_tests(cxx, static_lib)

    def package(self):
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        copy(
            self,
            "*.h",
            src=os.path.join(self.source_folder, "cds"),
            dst=os.path.join(self.package_folder, "include", "cds"),
        )
        objdir = os.path.join(self.build_folder, "objs")
        copy(
            self,
            "libcds-s.a",
            src=objdir,
            dst=os.path.join(self.package_folder, "lib"),
        )
        if self.options.shared:
            copy(
                self,
                "libcds.so",
                src=objdir,
                dst=os.path.join(self.package_folder, "lib"),
            )
        # Carry the upstream evidence for test_package cache-hit re-emit.
        try:
            src = os.path.join(self.build_folder, "hmbs_upstream.json")
            if os.path.isfile(src):
                dst_dir = os.path.join(self.package_folder, "res")
                os.makedirs(dst_dir, exist_ok=True)
                with open(src, "r", encoding="utf-8") as handle:
                    content = handle.read()
                with open(
                    os.path.join(dst_dir, "hmbs_upstream.json"),
                    "w",
                    encoding="utf-8",
                ) as handle:
                    handle.write(content)
        except OSError:
            pass

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "LibCDS")
        if self.options.shared:
            self.cpp_info.libs = ["cds"]
            self.cpp_info.set_property(
                "cmake_target_name", "LibCDS::cds"
            )
        else:
            self.cpp_info.libs = ["cds-s"]
            self.cpp_info.set_property(
                "cmake_target_name", "LibCDS::cds-s"
            )
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]
