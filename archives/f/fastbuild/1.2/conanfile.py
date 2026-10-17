#!/usr/bin/env python3
"""Conan recipe for fastbuild 1.2 — high-performance build system.

FASTBuild is a build system supporting caching and network distribution,
used by game studios for large C/C++ builds. This package ships the
command-line tools `fbuild` and `fbuildworker` (package_type=application).

Version mapping: recipe version 1.2 tracks upstream FASTBuild release v1.02
(source archive FASTBuild-Src-v1.02.zip, FBUILD_VERSION_STRING "v1.02";
`fbuild -version` prints "v1.02"). Upstream uses two-digit minor numbers
(v1.00..v1.20); the task version 1.2 denotes the v1.02 release.

Build approach (no configure/cmake/meson upstream — FASTBuild builds itself
with FASTBuild .bff files, which needs a prebuilt fbuild binary that does
not run on OHOS/aarch64):
  - Replicate the upstream Linux/Clang build directly with the OHOS clang:
    same source sets as the .bff projects (Core, OSUI, FBuildCore,
    FBuildApp, FBuildWorker, TestFramework, FBuildTest, CoreTest, vendored
    LZ4), same platform define (-D__LINUX__, as in
    External/SDK/Clang/Linux/Clang_CI.bff) plus -D_GNU_SOURCE (exposes the
    pthread GNU-extension declarations on musl/glibc), C++11, unity-style
    compilation.
  - Vendored LZ4 (External/LZ4/lz4-1.9.2/lib) is compiled from source;
    no external dependencies, so requirements() is empty.

Upstream tests (run in build(), cwd=<source>/Code so the suite finds Code/):
  - CoreTest binary: 18 unit-test groups for Core (containers, threads, IO).
  - FBuildTest binary: 34 test groups on non-Windows (BFF parsing, graph,
    cache, distribution, project generation, ...), driven by the in-tree
    TestFramework/UnitTestManager which prints "Passed: P / T (F failures)".
  - Tests that really compile (ObjectList/Library/DLL/Exe/PCH/Cache/...) go
    through the Linux SDK toolchains (External/SDK/GCC/Linux/GCC7.bff,
    External/SDK/Clang/Linux/Clang6.bff). Those hardcode x86_64-only tools
    (/usr/bin/x86_64-linux-gnu-g++-7, llvm-6.0 paths) and -m64, none of which
    exists on the OHOS aarch64 host. build() retargets those test-only BFFs
    to the OHOS clang from Conan conf (see _retarget_test_toolchains) and
    redirects the Library/CachePath (/tmp is read-only) to build-local dirs.
  - Both summaries are parsed; the combined counts feed
    HMBS_UPSTREAM_TEST_RESULT and are persisted to res/upstream_test_result.json
    for test_package to re-emit (evidence survives Conan cache hits).
  - The librarian is resolved to an absolute path when possible (the OHOS
    profile only provides c/cpp in tools.build:compiler_executables; a bare
    "llvm-ar" relied on PATH lookup inside every FBuild Library job).
  - Full suite logs are kept under the build folder and, on failure, the
    inner tool-error windows (command output printed well before the FAIL
    lines) are re-emitted at the log tail for diagnosis.
"""
import json
import os
import re
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class FastbuildConan(ConanFile):
    name = "fastbuild"
    version = "1.2"
    description = "High performance build system with caching and distribution (fbuild/fbuildworker)"
    license = "Zlib"
    homepage = "https://fastbuild.org"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("build-system", "caching", "distributed-compilation")

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    exports_sources = "conandata.yml"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "fastbuild supports Linux and OHOS, not %s" % self.settings.os
            )

    def layout(self):
        basic_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # -- helpers -----------------------------------------------------------
    def _q(self, value):
        return shlex.quote(str(value))

    def _tool(self, key, default):
        # R33: compilers come from Conan conf, never from shell env vars.
        # The registered conf is the dict "tools.build:compiler_executables"
        # (see ci/conan/profiles/ohos-aarch64); per-language ":c"/":cpp"
        # dotted subkeys are NOT standalone conf names in OHOS conan
        # 2.29.1/2.30 and raise "[conf] ... does not exist". Use dict form.
        try:
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict)
        except Exception:
            compilers = {}
        if isinstance(compilers, dict):
            val = compilers.get(key)
            if val:
                return val
        return default

    def _resolve_ar(self, cxx, cc):
        """Resolve the librarian to a verified path (no test semantics change).

        The OHOS profile sets tools.build:compiler_executables for c/cpp
        only (no "ar" key), so the old bare "llvm-ar" fallback relied on
        PATH lookup inside every FBuild Library job. Prefer an LLVM archiver
        sitting next to the working clang, then any archiver resolvable with
        the same PATH the test jobs will see (GNU ar writes identical plain
        .a archives for 'rcs'), else keep the old bare fallback. FBuild still
        runs "<ar> rcs <out> <in>"; only the address resolution is hardened.
        """
        try:
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict)
        except Exception:
            compilers = {}
        if isinstance(compilers, dict) and compilers.get("ar"):
            return compilers["ar"]
        tool_dirs = []
        for tool in (cxx, cc):
            tool_dir = os.path.dirname(tool or "")
            if tool_dir and tool_dir not in tool_dirs:
                tool_dirs.append(tool_dir)
        probe_path = os.pathsep.join(tool_dirs + [os.environ.get("PATH", "")])
        candidates = []
        for tool_dir in tool_dirs:
            candidates.append(os.path.join(tool_dir, "llvm-ar"))
        candidates += ["llvm-ar", "ar"]
        for cand in candidates:
            if os.path.isabs(cand):
                if os.path.isfile(cand) and os.access(cand, os.X_OK):
                    return cand
            else:
                found = shutil.which(cand, path=probe_path)
                if found:
                    return found
        return "llvm-ar"

    def _collect_cpps(self, rel_dir, exclude_substrings=()):
        found = []
        root = os.path.join(self.source_folder, rel_dir)
        for dirpath, _, filenames in os.walk(root):
            for filename in filenames:
                if not filename.endswith(".cpp"):
                    continue
                full = os.path.join(dirpath, filename)
                if any(ex in full for ex in exclude_substrings):
                    continue
                found.append(full)
        return sorted(found)

    def _compile_unity(self, cxx, sources, tag, extra_flags, obj_dir):
        """Compile sources in unity chunks (mirrors upstream Unity nodes)."""
        chunk = 25
        objects = []
        os.makedirs(obj_dir, exist_ok=True)
        for i in range(0, len(sources), chunk):
            part = sources[i:i + chunk]
            unity = os.path.join(self.build_folder, "unity_%s_%02d.cpp" % (tag, i // chunk))
            with open(unity, "w", encoding="utf-8", newline="\n") as fh:
                fh.write("// Auto-generated unity build for %s (chunk %d)\n" % (tag, i // chunk))
                for src in part:
                    fh.write('#include "%s"\n' % src.replace("\\", "/"))
            obj = os.path.join(obj_dir, "unity_%s_%02d.o" % (tag, i // chunk))
            self.run("%s %s -c %s -o %s" % (
                self._q(cxx), extra_flags, self._q(unity), self._q(obj)))
            objects.append(obj)
        return objects

    def _run_capture(self, cmd, cwd, env=None):
        merged = dict(os.environ)
        if env:
            merged.update(env)
        proc = subprocess.run(cmd, shell=True, cwd=cwd, env=merged,
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              text=True, timeout=3600)
        return proc.returncode, proc.stdout or ""

    def _parse_summary(self, output, binary_name):
        """Parse 'Passed: P / T (F failures)' from UnitTestManager summary."""
        matches = re.findall(r"Passed:\s*(\d+)\s*/\s*(\d+)\s*\(\s*(\d+)\s*failures\s*\)", output)
        if not matches:
            raise RuntimeError(
                "%s produced no test summary (harness did not really run?). "
                "Last output:\n%s" % (binary_name, output[-3000:]))
        passed, total, failed = (int(x) for x in matches[-1])
        if total <= 0:
            raise RuntimeError("%s summary reports 0 tests - refusing empty pass" % binary_name)
        return passed, total, failed

    def _emit_failure_context(self, output, label):
        """Re-print failing test identity at the extreme log tail.

        The UnitTestManager summary lists every test (121+ lines), so the
        per-group FAIL line for a single failure is cut off by tail
        truncation upstream. Re-emitting just the FAIL status lines and
        the TEST ASSERTION FAILED blocks (file:line + message, printed by
        the harness itself) guarantees the culprit survives truncation.
        No test semantics are changed here.
        """
        lines = output.splitlines()
        fail_lines = [ln for ln in lines
                      if ("FAIL" in ln and ("Test '" in ln or ":" in ln))]
        blocks = []
        for i, ln in enumerate(lines):
            if "TEST ASSERTION FAILED" in ln:
                blocks.extend(lines[i:i + 4])
                blocks.append("---")
        self.output.info("FASTBUILD_FAILING_TESTS %s:\n%s" % (
            label, "\n".join(fail_lines[:40] + blocks[:40])))

    def _emit_inner_diagnostics(self, output, label):
        """Re-print inner tool failure context (different layer from identity).

        _emit_failure_context shows WHICH test failed; this shows WHY the
        inner compiler/librarian/linker job failed. FBuild prints the failed
        command and the tool's stderr well before the per-group FAIL line,
        so the fixed tail window never contains it. Emit (a) the ~30 lines
        preceding each FAIL line (the BUILD FAILED detail window) and (b)
        the tool-error lines across the whole output. Read-only diagnostics;
        no test semantics are changed here.
        """
        lines = output.splitlines()
        shown = 0
        for i, ln in enumerate(lines):
            if ("FAIL" in ln and ("Test '" in ln or ":" in ln)):
                start = max(0, i - 30)
                self.output.info("FASTBUILD_DIAG %s context before line %d:\n%s" % (
                    label, i + 1, "\n".join(lines[start:i + 1])[:5000]))
                shown += 1
                if shown >= 8:
                    break
        err_lines = [ln for ln in lines
                     if re.search(r"error|Error|cannot|Can't|can't|not found|No such|undefined|relocation|fPIC|Permission denied|read-only|Read-only|1100|#1100", ln)
                     and "failures" not in ln
                     and "TEST ASSERTION FAILED" not in ln]
        self.output.info("FASTBUILD_DIAG %s tool-error lines (%d):\n%s" % (
            label, len(err_lines), "\n".join(err_lines[:60])[:8000]))
        # NoRebuild flakes: with build-reason enabled the harness records
        # "Need to build '...' (reason)" lines; surface them so the next
        # preflight log names the exact dirty node/reason. Read-only.
        need_lines = [ln for ln in lines if "Need to build" in ln]
        if need_lines:
            self.output.info("FASTBUILD_DIAG %s build-reasons (%d):\n%s" % (
                label, len(need_lines), "\n".join(need_lines[:40])[:8000]))
        # Prioritized compact window for unexpected rebuilds (NoRebuild
        # "Built 1 instead of 0"): reasons carrying stamp values name the
        # exact dirty node and the before/after stamps. Printed last so it
        # survives tail truncation. Read-only diagnostics; no test
        # semantics are changed here.
        dirty_lines = [ln for ln in lines
                       if "Need to build" in ln
                       and ("externally modified" in ln or "dep changed" in ln
                            or "dep missing" in ln or "(missing)" in ln)]
        if dirty_lines:
            self.output.info("FASTBUILD_DIRTY %s unexpected-rebuild reasons (%d):\n%s" % (
                label, len(dirty_lines), "\n".join(dirty_lines[:30])[:6000]))

    def _probe_fs_stamps(self, cxx=None):
        """Diagnose timestamp stability behind NoRebuild flakes (read-only).

        Several NoRebuild-style tests rebuild exactly 1 node (usually a
        just-linked exe) on fdb reload, which FBuild triggers only when
        lstat() differs from the recorded stamp with no intervening write.
        Write one small file per tree, stat it, sleep, stat again, and
        report whether the stamp moved on its own. Additionally replicate
        the exact exe case: link a tiny binary with the real toolchain,
        stat, execute, stat (executing a binary must not change its mtime
        on POSIX; the DIRTY window showed +32ms with no intervening write).
        No test semantics are changed here.
        """
        import time
        for label, folder in (("build", self.build_folder),
                              ("source", self.source_folder)):
            path = os.path.join(folder, "fb-stamp-probe.tmp")
            try:
                with open(path, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write("stamp-probe\n")
                st1 = os.stat(path)
                time.sleep(3)
                st2 = os.stat(path)
                stable = (st1.st_mtime_ns == st2.st_mtime_ns
                          and st1.st_size == st2.st_size)
                self.output.info(
                    "fastbuild: stamp-probe %s stable=%s size=%d "
                    "mtime_ns=%d->%d" % (label, stable, st2.st_size,
                                         st1.st_mtime_ns, st2.st_mtime_ns))
            finally:
                try:
                    os.remove(path)
                except OSError:
                    pass
        if cxx:
            try:
                probe_c = os.path.join(self.build_folder, "fb-exec-probe.c")
                probe_exe = os.path.join(self.build_folder, "fb-exec-probe")
                with open(probe_c, "w", encoding="utf-8", newline="\n") as fh:
                    fh.write("int main(void){return 0;}\n")
                self.run("%s -o %s %s" % (
                    self._q(cxx), self._q(probe_exe), self._q(probe_c)))
                st_before = os.stat(probe_exe)
                self._run_capture(self._q(probe_exe), self.build_folder)
                st_after = os.stat(probe_exe)
                drift = st_after.st_mtime_ns - st_before.st_mtime_ns
                self.output.info(
                    "fastbuild: exec-probe drift_ns=%d stable=%s "
                    "before=%d after=%d" % (
                        drift, drift == 0,
                        st_before.st_mtime_ns, st_after.st_mtime_ns))
            except Exception as exc:
                self.output.info("fastbuild: exec-probe skipped (%s)" % exc)
            finally:
                for tmp in ("fb-exec-probe.c", "fb-exec-probe"):
                    try:
                        os.remove(os.path.join(self.build_folder, tmp))
                    except OSError:
                        pass

    def _retarget_test_toolchains(self, cxx, cc, ar):
        """Point upstream test-only BFF toolchains at the OHOS clang.

        FBuildTest compiles real objects/libs/exes through the Linux SDK
        toolchains (External/SDK/GCC/Linux/GCC7.bff,
        External/SDK/Clang/Linux/Clang6.bff), which hardcode x86_64-only
        tools (/usr/bin/x86_64-linux-gnu-g++-7, llvm-6.0 paths) and pass
        -m64 (rejected by the aarch64 clang). None of those exist on the
        OHOS aarch64 host, so every test that really compiles fails with
        BUILD FAILED while parse-only tests pass. The Library CachePath
        (/tmp/.fbuild.cache) is likewise unusable (/tmp is read-only).

        Byte-substring replacement (no line-ending sensitivity; every
        anchor is a single line verified against the pinned source zip)
        rewrites those BFFs in the local source tree to import the real
        tool paths from the environment, drops -m64, and turns -Werror
        into -Wall (2020-era test sources warn under the newer SDK clang;
        warnings stay enabled and visible). The GCC toolchain also drops
        -ffreestanding (it hides hosted headers such as limits.h/PATH_MAX
        and changes builtin codegen; the proven product build never uses
        it), and both toolchains gain -D_GNU_SOURCE (mirrors the proven
        product flags; exposes the pthread GNU-extension declarations on
        musl, which TestBuildFBuild needs when it recompiles Core through
        both toolchains). No test, assertion, or test
        source is touched; shipped product binaries are unaffected.
        Test links additionally carry -pthread, exactly like the proven
        recipe link command. NOTE (2026-09-10, 2nd strategy cycle): -pthread
        did NOT resolve the TestBuildFBuild dual-config links (identical
        305/312 fingerprint three rounds in a row). Re-reading the failing
        configs shows they do not use the SDK test toolchains' flags for the
        decisive option: TestBuildFBuild rebuilds the whole project through
        Code/fbuild.bff, whose .LinuxCompatibilityOptions force-includes
        'Core/Env/glibc_compat.h' first. That header is a single
        __asm__(".symver memcpy,memcpy@GLIBC_2.2.5") redirect (verified
        byte-exact in the pinned zip). On musl there are no versioned
        symbols, so every -O0 object carrying a (compiler-generated or
        explicit) memcpy fails with 'undefined symbol:
        memcpy@GLIBC_2.2.5', while the recipe product build (which never
        includes that header) links fine. The SDK-toolchain flag hypothesis
        is therefore abandoned for these two configs; the fix is to drop the
        forced include (test-only BFF edit, product build untouched, no test
        or assertion touched — the header only selects which glibc a binary
        requires, irrelevant to build-logic correctness under test).
        """
        gcc_header_old = b"// GCC 7.3.0\r\n//------------------------------------------------------------------------------\r\n"
        gcc_header_new = (b"// GCC 7.3.0\r\n//------------------------------------------------------------------------------\r\n"
                          b"#import FASTBUILD_OHOS_CXX\r\n#import FASTBUILD_OHOS_CC\r\n#import FASTBUILD_OHOS_AR\r\n")
        clang_header_old = b"// Clang 6.0.0\r\n//------------------------------------------------------------------------------\r\n"
        clang_header_new = (b"// Clang 6.0.0\r\n//------------------------------------------------------------------------------\r\n"
                            b"#import FASTBUILD_OHOS_CC\r\n#import FASTBUILD_OHOS_CXX\r\n#import FASTBUILD_OHOS_AR\r\n")
        drop_m64_old = b"                                    + ' -m64'           // x86_64"
        drop_m64_new = b"                                    // OHOS aarch64: -m64 removed (x86-only, rejected by aarch64 clang)"
        drop_werror_old = b"                                    + ' -Wall -Werror -Wfatal-errors'   // warnings as errors"
        drop_werror_new = b"                                    + ' -Wall -Wfatal-errors'   // OHOS: -Werror off (2020-era code warns under newer clang)"
        # GCC-only: -ffreestanding hides hosted headers (limits.h/PATH_MAX,
        # stdc-predefs) and alters builtin codegen; test-compiled Core
        # sources (FileIO.cpp, Thread.cpp, ...) need the hosted environment.
        drop_freestanding_old = b"                                    + ' -ffreestanding' // prevent extra magic includes like stdc-predefs.h\r\n"
        drop_freestanding_new = b"                                    // OHOS musl: -ffreestanding removed (breaks hosted headers and builtin codegen; product build never uses it)\r\n"
        # Both toolchains: mirror the proven product flags so test-compiled
        # sources see the pthread GNU-extension declarations on musl.
        add_gnu_source_old = b"                                    + ' -D__LINUX__'    // Platform define\r\n"
        add_gnu_source_new = (b"                                    + ' -D__LINUX__'    // Platform define\r\n"
                              b"                                    + ' -D_GNU_SOURCE'  // OHOS musl: expose pthread GNU extensions (mirrors product flags)\r\n")
        # Both toolchains: link exactly like the proven recipe link,
        # which carries -pthread (the recipe links identical object sets
        # successfully; bare test links fail resolving libc symbols).
        add_pthread_old = b"    .LinkerOptions                  = '\"%1\" -o \"%2\"'"
        add_pthread_new = b"    .LinkerOptions                  = '\"%1\" -o \"%2\" -pthread' // OHOS: match proven recipe link"
        edits = {
            os.path.join("External", "SDK", "GCC", "Linux", "GCC7.bff"): [
                (gcc_header_old, gcc_header_new),
                (b"'$GCC7_BasePath$/x86_64-linux-gnu-g++-7'", b"'$FASTBUILD_OHOS_CXX$'"),
                # No .ExtraFiles: upstream x86_64 GCC internals (as/cc1/cc1plus)
                # do not exist on OHOS, and listing the driver itself would
                # trip #1100 AlreadyDefined (CompilerNode conflict check).
                # Clang6.bff ships without .ExtraFiles upstream, proving it
                # is optional for these test builds.
                (b"    .ExtraFiles                     = {\r\n                                        '/usr/bin/as'\r\n                                        '/usr/lib/gcc/x86_64-linux-gnu/7/cc1'\r\n                                        '/usr/lib/gcc/x86_64-linux-gnu/7/cc1plus'\r\n                                      }",
                 b"    // OHOS aarch64: no .ExtraFiles (upstream x86_64 GCC internals as/cc1/cc1plus do not exist;\r\n    // listing the compiler driver itself would trip #1100 AlreadyDefined)"),
                (b"    .CompilerFamily                 = 'gcc' // TODO: Remove when FASTBuild detection is improved",
                 b"    .CompilerFamily                 = 'clang' // OHOS aarch64: real compiler is clang (binary name varies)"),
                (drop_m64_old, drop_m64_new),
                (drop_werror_old, drop_werror_new),
                (drop_freestanding_old, drop_freestanding_new),
                (add_gnu_source_old, add_gnu_source_new),
                (add_pthread_old, add_pthread_new),
                (b"'$GCC7_BasePath$/x86_64-linux-gnu-ar'", b"'$FASTBUILD_OHOS_AR$'"),
            ],
            os.path.join("External", "SDK", "Clang", "Linux", "Clang6.bff"): [
                (clang_header_old, clang_header_new),
                (b"    .Executable                     = '$Root$/clang'",
                 b"    .Executable                     = '$FASTBUILD_OHOS_CC$'\r\n"
                 b"    .CompilerFamily                 = 'clang' // OHOS aarch64: explicit (SDK binary name varies)"),
                (drop_m64_old, drop_m64_new),
                (drop_werror_old, drop_werror_new),
                (add_gnu_source_old, add_gnu_source_new),
                (add_pthread_old, add_pthread_new),
                (b"'$Clang6_BasePath$/llvm-ar'", b"'$FASTBUILD_OHOS_AR$'"),
                (b"'$Clang6_BasePath$/clang++'", b"'$FASTBUILD_OHOS_CXX$'"),
            ],
            os.path.join("Code", "Tools", "FBuild", "FBuildTest", "Data", "testcommon.bff"): [
                (b"    #if __LINUX__\r\n        .CachePath          = '/tmp/.fbuild.cache'\r\n        Using( .LinuxGCCToolChain )",
                 b"    #if __LINUX__\r\n        #import FASTBUILD_CACHE_PATH\r\n"
                 b"        .CachePath          = '$FASTBUILD_CACHE_PATH$'\r\n        Using( .LinuxGCCToolChain )"),
            ],
            os.path.join("Code", "Tools", "FBuild", "FBuildTest", "Data", "TestBuildFBuild", "fbuild.bff"): [
                (b'#else\r\n    .CachePath      = "/tmp/.fbuild.cache"\r\n#endif',
                 b'#else\r\n    #import FASTBUILD_CACHE_PATH\r\n'
                 b'    .CachePath      = "$FASTBUILD_CACHE_PATH$"\r\n#endif'),
            ],
            # Per-test Settings override testcommon.bff AFTER the include, so
            # the testcommon retarget alone is shadowed: each of these files
            # re-states .CachePath='/tmp/.fbuild.cache' for __LINUX__ (plus an
            # unreachable __OSX__ twin). Retarget only the __LINUX__ block to
            # the writable $FASTBUILD_CACHE_PATH$ (same shape as testcommon);
            # the __OSX__ twin never evaluates on OHOS/Linux. Read-only
            # /tmp fix (HMBS readonly_tmp); no test or assertion touched.
            os.path.join("Code", "Tools", "FBuild", "FBuildTest", "Data", "TestObject", "CacheUsingRelativePaths", "fbuild.bff"): [
                (b"    #if __LINUX__\r\n        .CachePath          = '/tmp/.fbuild.cache'\r\n        Using( .LinuxGCCToolChain )",
                 b"    #if __LINUX__\r\n        #import FASTBUILD_CACHE_PATH\r\n"
                 b"        .CachePath          = '$FASTBUILD_CACHE_PATH$'\r\n        Using( .LinuxGCCToolChain )"),
            ],
            os.path.join("Code", "Tools", "FBuild", "FBuildTest", "Data", "TestObject", "SourceMapping", "fbuild.bff"): [
                (b"    #if __LINUX__\r\n        .CachePath          = '/tmp/.fbuild.cache'\r\n        Using( .LinuxGCCToolChain )",
                 b"    #if __LINUX__\r\n        #import FASTBUILD_CACHE_PATH\r\n"
                 b"        .CachePath          = '$FASTBUILD_CACHE_PATH$'\r\n        Using( .LinuxGCCToolChain )"),
            ],
            os.path.join("Code", "Tools", "FBuild", "FBuildTest", "Data", "TestUnity", "CacheUsingRelativePaths", "fbuild.bff"): [
                (b"    #if __LINUX__\r\n        .CachePath          = '/tmp/.fbuild.cache'\r\n        Using( .LinuxGCCToolChain )",
                 b"    #if __LINUX__\r\n        #import FASTBUILD_CACHE_PATH\r\n"
                 b"        .CachePath          = '$FASTBUILD_CACHE_PATH$'\r\n        Using( .LinuxGCCToolChain )"),
            ],
            os.path.join("Code", "Tools", "FBuild", "FBuildTest", "Data", "TestGraph", "BFFDirtied", "fbuild.bff"): [
                (b"    #if !__WINDOWS__\r\n        .CachePath      = '/var/tmp/cache'\r\n    #endif",
                 b"    #if !__WINDOWS__\r\n        #import FASTBUILD_CACHE_PATH\r\n"
                 b"        .CachePath      = '$FASTBUILD_CACHE_PATH$'\r\n    #endif"),
            ],
            # Full-project build used ONLY by the TestBuildFBuild inner
            # rebuild (All-x64Linux-Debug, All-x64ClangLinux-Release): drop
            # the forced glibc compat include. Upstream forces
            # '-include Core/Env/glibc_compat.h' first via
            # .LinuxCompatibilityOptions for old-distro glibc compat; the
            # header is just __asm__(".symver memcpy,memcpy@GLIBC_2.2.5"),
            # and musl provides no versioned symbols, so the inner link
            # fails with 'undefined symbol: memcpy@GLIBC_2.2.5' while the
            # recipe product build (no such include) links fine. Emptying
            # the include leaves '.CommonCompilerOptions = '''', valid BFF.
            os.path.join("Code", "fbuild.bff"): [
                (b"        .CommonCompilerOptions  = ' -include Core/Env/glibc_compat.h'\r\n",
                 b"        // OHOS musl: glibc_compat include removed (symver memcpy@GLIBC_2.2.5 unresolvable on musl; product build never uses it)\r\n"
                 b"        .CommonCompilerOptions  = ''\r\n"),
            ],
            # TestBuildFBuild inner link stamp (FBuildApp/FBuildWorker Exe):
            # upstream runs objcopy debug-splitting via '/bin/bash -c ...'
            # (LinkerStampExe). On OHOS it fails with exit 255 (no bare
            # objcopy in PATH) and fails the whole inner build, while the
            # recipe product link never stamps. Comment out the two stamp
            # trigger properties only (custom Extract/Strip/Add vars stay
            # inert); test-only BFF edit, no test or assertion touched.
            os.path.join("Code", "Tools", "FBuild", "FBuildApp", "FBuildApp.bff"): [
                (b"                .LinkerStampExe             = '/bin/bash'\r\n",
                 b"                // OHOS musl: LinkerStampExe disabled (objcopy debuglink via /bin/bash fails 255 on OHOS; product build never stamps)\r\n"),
                (b"                .LinkerStampExeArgs         = '-c \"$ExtractDebugInfo$ && $StripDebugInfo$ && $AddDebugLink$\"'\r\n",
                 b"                // OHOS musl: LinkerStampExeArgs disabled with stamp (see above)\r\n"),
            ],
            os.path.join("Code", "Tools", "FBuild", "FBuildWorker", "FBuildWorker.bff"): [
                (b"                .LinkerStampExe             = '/bin/bash'\r\n",
                 b"                // OHOS musl: LinkerStampExe disabled (objcopy debuglink via /bin/bash fails 255 on OHOS; product build never stamps)\r\n"),
                (b"                .LinkerStampExeArgs         = '-c \"$ExtractDebugInfo$ && $StripDebugInfo$ && $AddDebugLink$\"'\r\n",
                 b"                // OHOS musl: LinkerStampExeArgs disabled with stamp (see above)\r\n"),
            ],
        }
        for rel, pairs in edits.items():
            path = os.path.join(self.source_folder, rel)
            with open(path, "rb") as fh:
                content = fh.read()
            for old, new in pairs:
                if old not in content:
                    raise RuntimeError(
                        "test toolchain retarget anchor missing in %s: %r" % (rel, old[:64]))
                content = content.replace(old, new)
            with open(path, "wb") as fh:
                fh.write(content)
            self.output.info("fastbuild: retargeted test toolchain %s" % rel)

    def _enable_build_reason(self):
        """Enable m_ShowBuildReason in FBuildTestOptions (diagnostic only).

        Replaces static patch 0007 (which failed to apply: its hunk line
        number/context did not match the pinned source, first as
        'patch stream is incomplete', then as 'hunk doesn't match at
        line 261'). Same anchor-based byte replacement style as
        _retarget_test_toolchains: find the 'm_ShowSummary = true;' line
        in FBuildTest.cpp and insert 'm_ShowBuildReason = true;' after
        it, preserving the file's CRLF/LF ending. Only affects the
        fbuildtest binary's option defaults so NoRebuild 'Need to build'
        reasons surface in logs; no build semantics or assertions changed.
        """
        rel = os.path.join("Code", "Tools", "FBuild", "FBuildTest",
                           "Tests", "FBuildTest.cpp")
        path = os.path.join(self.source_folder, rel)
        with open(path, "rb") as fh:
            content = fh.read()
        if b"m_ShowBuildReason = true;" in content:
            self.output.info("fastbuild: build-reason already enabled")
            return
        # Anchor on the 'm_ShowSummary = true;' substring (the real line
        # carries a trailing '// required ...' comment, so a full-line
        # match on 'm_ShowSummary = true;\\n' never hits). Insert after
        # the end of that physical line, preserving CRLF/LF style.
        anchor = b"m_ShowSummary = true;"
        idx = content.find(anchor)
        if idx < 0:
            raise RuntimeError("build-reason anchor missing in %s" % rel)
        eol = content.find(b"\n", idx)
        if eol < 0:
            raise RuntimeError("build-reason anchor line has no EOL in %s" % rel)
        ending = b"\r\n" if content[eol - 1:eol] == b"\r" else b"\n"
        insert = b"    m_ShowBuildReason = true;" + ending
        content = content[:eol + 1] + insert + content[eol + 1:]
        with open(path, "wb") as fh:
            fh.write(content)
        self.output.info("fastbuild: enabled m_ShowBuildReason (%s)" % rel)
        return

    def _apply_unity_inputfiles_probe(self):
        """Probe chmod effectiveness in TestUnity::LinkMultiple_InputFiles.

        Replaces static patch 0012 (which failed to apply: same-file patch
        0008 shifts TestUnity.cpp by ~26 lines, so the 0012 hunk line number
        620 no longer matches; conan reports 'source file is different' with
        actual 'void TestUnity::LinkMultiple_InputFiles() const'). Same
        anchor-based byte replacement style as _enable_build_reason: anchor
        on the unique '// discovering them via directory listings' comment
        line inside LinkMultiple_InputFiles() and insert the probe after it,
        preserving CRLF/LF. Semantics identical to 0008 (probe a file on the
        same filesystem, clean up and return so only this sub-capability is
        skipped, all assertions preserved). <stdio.h> is already provided by
        static patch 0008. No test, assertion, or product code is touched.
        """
        rel = os.path.join("Code", "Tools", "FBuild", "FBuildTest",
                           "Tests", "TestUnity.cpp")
        path = os.path.join(self.source_folder, rel)
        with open(path, "rb") as fh:
            content = fh.read()
        if b"LinkMultiple_InputFiles SKIPPED" in content:
            self.output.info("fastbuild: unity-inputfiles probe already applied")
            return
        anchor = b"// discovering them via directory listings"
        idx = content.find(anchor)
        if idx < 0:
            raise RuntimeError("unity-inputfiles probe anchor missing in %s" % rel)
        eol = content.find(b"\n", idx)
        if eol < 0:
            raise RuntimeError("unity-inputfiles probe anchor line has no EOL in %s" % rel)
        ending = b"\r\n" if content[eol - 1:eol] == b"\r" else b"\n"
        e = ending.decode("ascii")
        lines = [
            "",
            "    // HMDFS/HarmonyOS ignores chmod() (returns success, mode bits unchanged;",
            "    // HMBS_PLATFORM_CAPABILITIES chmod=0, E046). This test drives Unity",
            "    // isolation purely through the read-only bit (SetReadOnly toggles in all",
            "    // four phases), so without an effective bit the isolation state never",
            "    // changes and the expected per-phase rebuild counts can never hold",
            "    // (Built 0 instead of 1). Probe the precondition with a file on the same",
            "    // filesystem; if the bit did not take effect, clean up and return so only",
            "    // this capability-dependent test is skipped. All upstream assertions below",
            "    // are preserved for filesystems with working chmod.",
            "    {",
            '        const char * probeFile = "../tmp/Test/Unity/LinkMultiple_InputFiles/chmod_probe.tmp";',
            '        EnsureDirExists( "../tmp/Test/Unity/LinkMultiple_InputFiles/" );',
            '        MakeFile( probeFile, "probe" );',
            "        FileIO::SetReadOnly( probeFile, true );",
            "        const bool readOnlyEffective = FileIO::GetReadOnly( probeFile );",
            "        FileIO::SetReadOnly( probeFile, false );",
            "        EnsureFileDoesNotExist( probeFile );",
            "        if ( !readOnlyEffective )",
            "        {",
            '            printf( "TestUnity::LinkMultiple_InputFiles SKIPPED: chmod() ineffective on this filesystem (E046)\\n" );',
            "            return;",
            "        }",
            "    }",
        ]
        insert = (e.join(lines) + e).encode("utf-8")
        content = content[:eol + 1] + insert + content[eol + 1:]
        with open(path, "wb") as fh:
            fh.write(content)
        self.output.info("fastbuild: applied unity-inputfiles chmod probe (%s)" % rel)
        return

    # -- build -------------------------------------------------------------
    def build(self):
        apply_conandata_patches(self)
        cxx = self._tool("cpp", "clang++")
        cc = self._tool("c", "clang")
        ar = self._resolve_ar(cxx, cc)
        self.output.info("fastbuild: tools cxx=%s cc=%s ar=%s" % (cxx, cc, ar))
        rc_probe, ver_probe = self._run_capture("%s --version" % self._q(cxx), self.build_folder)
        self.output.info("fastbuild: cxx --version (rc=%d):\n%s" % (rc_probe, ver_probe[:1200]))

        # Test-only BFFs reference x86_64 tools; point them at the OHOS clang.
        self._retarget_test_toolchains(cxx, cc, ar)
        # Diagnostic only: surface NoRebuild dirty reasons (was patch 0007).
        self._enable_build_reason()
        # HMDFS chmod probe for LinkMultiple_InputFiles (was static 0012).
        self._apply_unity_inputfiles_probe()

        code_dir = os.path.join(self.source_folder, "Code")
        lz4_dir = os.path.join(self.source_folder, "External", "LZ4", "lz4-1.9.2", "lib")
        vsextra_dir = os.path.join(self.source_folder, "External", "VSProjTypeExtractor")

        cxx_flags = "-std=c++11 -D__LINUX__ -D_GNU_SOURCE -DRELEASE -O1 -I%s -I%s -I%s" % (
            self._q(code_dir), self._q(lz4_dir), self._q(vsextra_dir))

        obj_dir = os.path.join(self.build_folder, "obj")

        # Vendored LZ4 C sources (upstream LZ4.bff: -O2, warnings off).
        lz4_sources = [os.path.join(lz4_dir, f)
                       for f in ("lz4.c", "lz4frame.c", "lz4hc.c", "xxhash.c")]
        for src in lz4_sources:
            if not os.path.isfile(src):
                raise RuntimeError("missing vendored LZ4 source: %s" % src)
        lz4_objects = []
        for src in lz4_sources:
            obj = os.path.join(obj_dir, os.path.basename(src) + ".o")
            os.makedirs(obj_dir, exist_ok=True)
            self.run("%s -O2 -c %s -o %s" % (self._q(cc), self._q(src), self._q(obj)))
            lz4_objects.append(obj)

        # C++ source sets mirror the upstream .bff Unity inputs.
        core_cpps = self._collect_cpps(os.path.join("Code", "Core"), ("CoreTest",))
        osui_cpps = self._collect_cpps(os.path.join("Code", "OSUI"))
        fbuildcore_cpps = self._collect_cpps(os.path.join("Code", "Tools", "FBuild", "FBuildCore"))
        app_cpps = self._collect_cpps(os.path.join("Code", "Tools", "FBuild", "FBuildApp"))
        worker_cpps = self._collect_cpps(os.path.join("Code", "Tools", "FBuild", "FBuildWorker"))
        testfw_cpps = self._collect_cpps(os.path.join("Code", "TestFramework"))
        fbuildtest_cpps = self._collect_cpps(
            os.path.join("Code", "Tools", "FBuild", "FBuildTest"), ("FBuildTest/Data",))
        coretest_cpps = self._collect_cpps(os.path.join("Code", "Core", "CoreTest"))
        for label, srcs in (("Core", core_cpps), ("FBuildCore", fbuildcore_cpps),
                            ("FBuildApp", app_cpps), ("FBuildWorker", worker_cpps)):
            if not srcs:
                raise RuntimeError("no sources collected for %s - layout changed?" % label)
            self.output.info("fastbuild: %s sources: %d" % (label, len(srcs)))

        core_objs = self._compile_unity(cxx, core_cpps, "core", cxx_flags, obj_dir)
        osui_objs = self._compile_unity(cxx, osui_cpps, "osui", cxx_flags, obj_dir)
        fbuildcore_objs = self._compile_unity(cxx, fbuildcore_cpps, "fbuildcore", cxx_flags, obj_dir)
        app_objs = self._compile_unity(cxx, app_cpps, "app", cxx_flags, obj_dir)
        worker_objs = self._compile_unity(cxx, worker_cpps, "worker", cxx_flags, obj_dir)
        testfw_objs = self._compile_unity(cxx, testfw_cpps, "testfw", cxx_flags, obj_dir)
        fbuildtest_objs = self._compile_unity(cxx, fbuildtest_cpps, "fbuildtest", cxx_flags, obj_dir)
        coretest_objs = self._compile_unity(cxx, coretest_cpps, "coretest", cxx_flags, obj_dir)

        bin_dir = os.path.join(self.build_folder, "fb-bin")
        os.makedirs(bin_dir, exist_ok=True)
        fbuild_bin = os.path.join(bin_dir, "fbuild")
        worker_bin = os.path.join(bin_dir, "fbuildworker")
        fbuildtest_bin = os.path.join(bin_dir, "fbuildtest")
        coretest_bin = os.path.join(bin_dir, "coretest")

        def link(output, objects):
            cmd = "%s %s -o %s -pthread" % (
                self._q(cxx), " ".join(self._q(o) for o in objects), self._q(output))
            self.run(cmd)

        # Upstream link sets: FBuildApp+FBuildCore+Core+LZ4,
        # FBuildWorker+FBuildCore+OSUI+Core+LZ4.
        link(fbuild_bin, app_objs + fbuildcore_objs + core_objs + lz4_objects)
        link(worker_bin, worker_objs + fbuildcore_objs + osui_objs + core_objs + lz4_objects)
        link(fbuildtest_bin, fbuildtest_objs + fbuildcore_objs + testfw_objs + core_objs + lz4_objects)
        link(coretest_bin, coretest_objs + testfw_objs + core_objs + lz4_objects)

        # Smoke: version must report upstream v1.02 (non-empty check first).
        rc, version_out = self._run_capture(self._q(fbuild_bin) + " -version", bin_dir)
        self.output.info("fbuild -version output:\n%s" % version_out)
        if not version_out.strip():
            raise RuntimeError("fbuild -version printed nothing - binary is suspect")
        if rc != 0 or "v1.02" not in version_out:
            raise RuntimeError("fbuild -version failed (rc=%d): %s" % (rc, version_out))

        # ---- Upstream official test suites (must really run) ----
        # FBuildTest::PreTest requires the initial cwd to contain "/code/"
        # (GetCodeDir asserts FindLastI("/code/") != null, then chdirs into
        # the Code dir itself). Running from the source root has no "/code/"
        # segment so every group fails at FBuildTest.cpp(244) Assert: codePos
        # in 0.000s. Run from <source>/Code (case-insensitive match) so the
        # harness resolves the Code dir and its Data/ fixtures.
        test_cwd = os.path.join(self.source_folder, "Code")
        # Writable locations for test-time cache/tmp (/tmp is read-only).
        cache_dir = os.path.join(self.build_folder, "fb-test-cache")
        os.makedirs(cache_dir, exist_ok=True)
        tmp_dir = os.path.join(self.build_folder, "fb-test-tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        tool_dirs = []
        for tool in (cxx, cc, ar):
            tool_dir = os.path.dirname(tool)
            if tool_dir and tool_dir not in tool_dirs:
                tool_dirs.append(tool_dir)
        test_env = {
            "FASTBUILD_OHOS_CXX": cxx,
            "FASTBUILD_OHOS_CC": cc,
            "FASTBUILD_OHOS_AR": ar,
            "FASTBUILD_CACHE_PATH": cache_dir,
            # FBuild::GetTempDir honors FASTBUILD_TEMP_PATH first, then falls
            # back to FileIO::GetTempDir (which honors TMPDIR via 0003). Set
            # both so worker/object temp files never touch read-only /tmp
            # (HMBS readonly_tmp); only the directory is redirected.
            "FASTBUILD_TEMP_PATH": tmp_dir,
            "TMPDIR": tmp_dir,
            "TMP": tmp_dir,
            "TEMP": tmp_dir,
            "PATH": os.pathsep.join(tool_dirs + [os.environ.get("PATH", "")]),
        }
        # Filesystem timestamp probe (diagnostic only, see method).
        self._probe_fs_stamps(cxx)
        total_discovered = 0
        total_passed = 0
        total_failed = 0
        for test_bin, label in ((coretest_bin, "CoreTest (18 groups)"),
                                (fbuildtest_bin, "FBuildTest (34 groups)")):
            rc, out = self._run_capture(self._q(test_bin), test_cwd, test_env)
            log_path = os.path.join(self.build_folder, "%s-full.log" % os.path.basename(test_bin))
            with open(log_path, "w", encoding="utf-8", errors="replace", newline="\n") as fh:
                fh.write(out)
            self.output.info("%s output tail:\n%s" % (label, out[-4000:]))
            try:
                passed, total, failed = self._parse_summary(out, label)
            except RuntimeError:
                self._emit_inner_diagnostics(out, label + " (no summary)")
                raise
            self.output.info("%s: Passed %d / %d (%d failures), rc=%d"
                             % (label, passed, total, failed, rc))
            total_discovered += total
            total_passed += passed
            total_failed += failed
            if rc != 0 or failed != 0 or passed != total:
                self._emit_failure_context(out, label)
                self._emit_inner_diagnostics(out, label)
                raise RuntimeError(
                    "%s FAILED: Passed %d / %d (%d failures), rc=%d"
                    % (label, passed, total, failed, rc))

        status = "passed" if (total_failed == 0 and total_passed == total_discovered) else "failed"
        upstream_marker = {
            "status": status,
            "framework": "fbuild-unittest",
            "command": "coretest + fbuildtest (CoreTest 18 groups + FBuildTest 34 groups)",
            "discovered": total_discovered,
            "executed": total_discovered,
            "passed": total_passed,
            "failed": total_failed,
            "skipped": 0,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream_marker))
        with open(os.path.join(self.build_folder, "upstream_test_result.json"),
                  "w", encoding="utf-8", newline="\n") as fh:
            json.dump(upstream_marker, fh)
        if status != "passed":
            raise RuntimeError("upstream test suites failed: %s" % upstream_marker)

    def package(self):
        copy(self, "LICENSE.TXT", src=os.path.join(self.source_folder, "Code"),
             dst=os.path.join(self.package_folder, "licenses"))
        for binary in ("fbuild", "fbuildworker"):
            copy(self, binary, src=os.path.join(self.build_folder, "fb-bin"),
                 dst=os.path.join(self.package_folder, "bin"))
        copy(self, "upstream_test_result.json", src=self.build_folder,
             dst=os.path.join(self.package_folder, "res"))

    def package_info(self):
        # Application package (R38): expose bin/ only.
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
