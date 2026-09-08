#!/usr/bin/env python3
"""Conan recipe — boost1.84-coroutine 1.84.0 (Boost.Coroutine standalone component package).

Boost 1.84.0 component split packaging for HarmonyOS PC (aarch64).
The deprecated Boost.Coroutine (v1) has three compiled sources:
  libs/coroutine/src/detail/coroutine_context.cpp
  libs/coroutine/src/exceptions.cpp
  libs/coroutine/src/posix/stack_traits.cpp
and depends on Boost.Context which itself provides the low-level
fcontext assembler (make/jump/ontop for arm64_aapcs_elf_gas) plus
its own src/posix/stack_traits.cpp.

The b2 build system is incompatible with OHOS (SHELL execution failure,
E068 error pattern), so we compile all translation units manually with
the Conan-provided OHOS clang driver — same approach as boost/1.84.0
and boost1.84-system.

Key facts (verified on the OHOS target):
- Upstream Boost.Context ASM sources for OHOS aarch64 are
  src/asm/make_arm64_aapcs_elf_gas.S / jump_ / ontop_ (elf + aapcs + gas).
- OHOS SDK clang 15 handles .S as assembler-with-cpp without extra flags.
- The compiled static libraries keep the CMake component contract
  `Boost::coroutine` / `Boost::context` and install the full boost/ headers
  directory so the package is self-contained.
- Upstream test suite: 2 runnable executables from libs/coroutine/test/
  (test_asymmetric_coroutine, test_symmetric_coroutine) driven manually
  via included boost.test (no linked test framework needed). Both pass on
  OHOS aarch64.

Upstream: https://github.com/boostorg/coroutine (branch boost-1.84.0)
Boost super-project source: boost_1_84_0.tar.gz (same as boost/1.84.0)
"""
import json
import os
import glob
import signal
import subprocess

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches


class BoostCoroutineConan(ConanFile):
    name = "boost1.84-coroutine"
    version = "1.84.0"
    description = "Boost.Coroutine 1.84.0 组件包（asymmetric/symmetric coroutine，依赖 Boost.Context fcontext，鸿蒙 PC 适配，静态库 + 全量 boost 头文件）"
    license = "BSL-1.0"
    homepage = "https://www.boost.org/doc/libs/1_84_0/libs/coroutine/"
    url = "https://github.com/boostorg/coroutine"
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        pass

    def source(self):
        data = self.conan_data["sources"]
        if isinstance(data, list):
            data = data[0]
        get(self, **data, strip_root=True)

    def generate(self):
        pass

    def _writable_tmpdir(self):
        # HMBS E002: /tmp is read-only erofs on HarmonyOS. Reuse injected
        # HMBS_TMPDIR/TMPDIR/TMP/TEMP if present, else fallback to build_folder/tmp.
        for var in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
            v = __import__("os").environ.get(var)
            if v and v != "0" and v != "/tmp":
                try:
                    __import__("os").makedirs(v, exist_ok=True)
                except OSError:
                    pass
                if __import__("os").path.isdir(v):
                    return v
                return v
        v = __import__("os").environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK")
        if v and v != "0" and v != "/tmp":
            try:
                __import__("os").makedirs(v, exist_ok=True)
            except OSError:
                pass
            if __import__("os").path.isdir(v):
                return v
        base = self.build_folder or self.source_folder or __import__("os").getcwd()
        cand = __import__("os").path.join(base, "tmp_hmbs")
        try:
            __import__("os").makedirs(cand, exist_ok=True)
        except OSError:
            return base
        return cand

    def _cxxflags(self, boost_root):
        if self.settings.build_type == "Debug":
            opt_flags = ["-O0", "-g"]
        else:
            opt_flags = ["-O2", "-DNDEBUG"]
        return " ".join([
            "-std=c++17",
            "-stdlib=libc++",
            *opt_flags,
            "-fPIC",
            f"-I{boost_root}",
            "-DBOOST_ALL_NO_LIB",
            "-DBOOST_SYSTEM_NO_DEPRECATED",
            "-DBOOST_CONTEXT_SOURCE",
            "-DBOOST_COROUTINE_SOURCE",
            "-DBOOST_COROUTINES_SOURCE",
            "-DBOOST_CONTEXT_STATIC_LINK",
            "-DBOOST_COROUTINE_STATIC_LINK",
            "-DBOOST_SP_NO_PTHREAD_SETCANCELSTATE",
        ])

    def _run_cmd(self, cmd, timeout, shell=False, env=None):
        run_env = None
        if env is not None:
            run_env = dict(__import__("os").environ)
            run_env.update(env)
        else:
            run_env = dict(__import__("os").environ)
        for k in ("TMPDIR", "TMP", "TEMP"):
            if k not in run_env or not run_env[k] or run_env[k] == "/tmp" or run_env[k] == "0":
                fallback = __import__("os").environ.get("HMBS_TMPDIR") or __import__("os").environ.get("TMPDIR") or __import__("os").environ.get("TMP") or __import__("os").environ.get("TEMP")
                if fallback and fallback != "0" and fallback != "/tmp":
                    run_env[k] = fallback
        proc = subprocess.Popen(
            cmd, shell=shell, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, stdin=subprocess.DEVNULL, start_new_session=True,
            env=run_env)
        try:
            out, err = proc.communicate(timeout=timeout)
            return proc.returncode, out, err
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                proc.kill()
            out, err = proc.communicate()
            return -1, out, err

    def build(self):
        apply_conandata_patches(self)
        tmpdir = self._writable_tmpdir()
        for k in ("TMPDIR", "TMP", "TEMP"):
            __import__("os").environ[k] = tmpdir
        if "HMBS_TMPDIR" not in __import__("os").environ:
            __import__("os").environ["HMBS_TMPDIR"] = tmpdir
        try:
            __import__("os").makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        self.output.info(f"[HMBS tmp] using writable TMPDIR={tmpdir}")
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cxx = compilers.get("cpp", "clang++")
        ar = compilers.get("ar", "llvm-ar")

        boost_root = self.source_folder
        cxxflags = self._cxxflags(boost_root)

        # -- Compile Boost.Context (fcontext ASM + stack_traits) ----------
        ctx_asm_dir = os.path.join(boost_root, "libs/context/src/asm")
        ctx_src_dir = os.path.join(boost_root, "libs/context/src")
        asm_suffix = "arm64_aapcs_elf_gas.S"
        asm_files = [
            os.path.join(ctx_asm_dir, f"make_{asm_suffix}"),
            os.path.join(ctx_asm_dir, f"jump_{asm_suffix}"),
            os.path.join(ctx_asm_dir, f"ontop_{asm_suffix}"),
        ]
        ctx_objects = []
        obj_dir_ctx = os.path.join(self.build_folder, "obj_context")
        os.makedirs(obj_dir_ctx, exist_ok=True)
        for asm in asm_files:
            if not os.path.isfile(asm):
                self.output.warning(f"Context ASM not found: {asm}")
                continue
            obj = os.path.join(obj_dir_ctx, os.path.basename(asm).replace(".S", ".o"))
            self.run(f"{cxx} {cxxflags} -c {asm} -o {obj}")
            ctx_objects.append(obj)
        ctx_stack = os.path.join(ctx_src_dir, "posix/stack_traits.cpp")
        obj_stack_ctx = os.path.join(obj_dir_ctx, "stack_traits_ctx.o")
        self.run(f"{cxx} {cxxflags} -c {ctx_stack} -o {obj_stack_ctx}")
        ctx_objects.append(obj_stack_ctx)

        lib_context = os.path.join(self.build_folder, "libboost_context.a")
        self.run(f"{ar} rcs {lib_context} {' '.join(ctx_objects)}")

        # -- Compile Boost.Coroutine --------------------------------------
        coro_src_dir = os.path.join(boost_root, "libs/coroutine/src")
        coro_files = [
            os.path.join(coro_src_dir, "detail/coroutine_context.cpp"),
            os.path.join(coro_src_dir, "exceptions.cpp"),
            os.path.join(coro_src_dir, "posix/stack_traits.cpp"),
        ]
        obj_dir_coro = os.path.join(self.build_folder, "obj_coroutine")
        os.makedirs(obj_dir_coro, exist_ok=True)
        coro_objects = []
        for src in coro_files:
            obj = os.path.join(obj_dir_coro, os.path.basename(src).replace(".cpp", ".o"))
            self.run(f"{cxx} {cxxflags} -c {src} -o {obj}")
            coro_objects.append(obj)

        lib_coro = os.path.join(self.build_folder, "libboost_coroutine.a")
        self.run(f"{ar} rcs {lib_coro} {' '.join(coro_objects)}")

        # -- Upstream test integration (b2 incompatible E068) --------------
        self._run_upstream_tests(boost_root, cxx, cxxflags)

    _UPSTREAM_TESTS = [
        "test_asymmetric_coroutine",
        "test_symmetric_coroutine",
    ]

    def _run_upstream_tests(self, boost_root, cxx, cxxflags):
        lib_dir = self.build_folder
        tmpdir = __import__("os").environ.get("TMPDIR") or self._writable_tmpdir()
        test_flags = cxxflags
        report_lines = []
        passed, failed = 0, 0
        patch_dir = os.path.join(self.build_folder, "upstream_test_patched")
        os.makedirs(patch_dir, exist_ok=True)
        for name in self._UPSTREAM_TESTS:
            orig = os.path.join(boost_root, "libs/coroutine/test", name + ".cpp")
            patched = os.path.join(patch_dir, name + ".cpp")
            if os.path.isfile(orig):
                with open(orig, "r", encoding="utf-8", errors="ignore") as fh:
                    content = fh.read()
                content = content.replace(
                    "#include <boost/test/unit_test.hpp>",
                    "#include <boost/test/included/unit_test.hpp>")
                with open(patched, "w", encoding="utf-8") as out:
                    out.write(content)
            else:
                report_lines.append(f"SKIP {name} (source not found)")
                continue
            exe = os.path.join(lib_dir, f"test_{name}")
            src = patched
            cmd_compile = f"TMPDIR='{tmpdir}' TMP='{tmpdir}' TEMP='{tmpdir}' {cxx} {test_flags} -DBOOST_TEST_NO_LIB {src} -L{lib_dir} -lboost_coroutine -lboost_context -o {exe}"
            ret_code, _out, ret_err = self._run_cmd(cmd_compile, timeout=300, shell=True)
            if ret_code != 0:
                failed += 1
                last = ret_err.splitlines()[-1] if ret_err else ""
                report_lines.append(f"COMPILE_FAIL {name}: {last}")
                continue
            run_env = {"TMPDIR": tmpdir, "TMP": tmpdir, "TEMP": tmpdir}
            run_code, _rout, _rerr = self._run_cmd([exe], timeout=120, env=run_env)
            if run_code == 0:
                passed += 1
                report_lines.append(f"PASS {name} rc=0")
            else:
                failed += 1
                snippet = (_rerr or _rout or "")[:500]
                report_lines.append(f"FAIL {name} rc={run_code} out={snippet}")
        total = passed + failed
        report_lines.append(f"TOTAL {total}: {passed} passed / {failed} failed")
        report_path = os.path.join(self.build_folder, "upstream-tests-report.txt")
        with open(report_path, "w", encoding="utf-8") as fh:
            fh.write("\n".join(report_lines) + "\n")
        self.output.info(f"上游测试报告: {report_path} ({passed}/{total} 通过)")
        for line in report_lines:
            if line.startswith(("FAIL", "COMPILE_FAIL", "TOTAL", "PASS")):
                self.output.info(f"[upstream-tests] {line}")
        discovered = len(self._UPSTREAM_TESTS)
        status = "passed" if failed == 0 and passed == discovered else "failed"
        ut_result = {
            "status": status,
            "framework": "boost.test",
            "command": "clang++ libs/coroutine/test/test_*_coroutine.cpp -lboost_coroutine -lboost_context && ./test_*",
            "discovered": discovered,
            "executed": passed + failed,
            "passed": passed,
            "failed": failed,
            "skipped": 0
        }
        json_path = __import__("os").path.join(self.build_folder, "upstream_test_result.json")
        try:
            with open(json_path, "w", encoding="utf-8") as jf:
                json.dump(ut_result, jf)
            self.output.info(f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(ut_result)}")
            print(f"HMBS_UPSTREAM_TEST_RESULT={json.dumps(ut_result)}")
        except OSError as e:
            self.output.warning(f"failed to write upstream_test_result.json: {e}")

    def package(self):
        copy(self, "boost/*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "include"))
        libdir = os.path.join(self.package_folder, "lib")
        for lib_file in glob.glob(os.path.join(self.build_folder, "libboost_*.a")):
            copy(self, os.path.basename(lib_file), src=self.build_folder, dst=libdir)
        for fname in ("upstream_test_result.json", "upstream-tests-report.txt"):
            src = __import__("os").path.join(self.build_folder, fname)
            if __import__("os").path.isfile(src):
                copy(self, fname, src=self.build_folder, dst=__import__("os").path.join(self.package_folder, "res"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "Boost")
        self.cpp_info.set_property("pkg_config_name", "boost_coroutine")
        self.cpp_info.components["boost_headers"].includedirs = ["include"]
        self.cpp_info.components["boost_headers"].defines = ["BOOST_SP_NO_PTHREAD_SETCANCELSTATE"]
        self.cpp_info.components["boost_headers"].set_property("cmake_target_name", "Boost::headers")
        self.cpp_info.components["boost_context"].includedirs = []
        self.cpp_info.components["boost_context"].libs = ["boost_context"]
        self.cpp_info.components["boost_context"].requires = ["boost_headers"]
        self.cpp_info.components["boost_context"].set_property("cmake_target_name", "Boost::context")
        self.cpp_info.components["boost_coroutine"].includedirs = []
        self.cpp_info.components["boost_coroutine"].libs = ["boost_coroutine"]
        self.cpp_info.components["boost_coroutine"].requires = ["boost_headers", "boost_context"]
        self.cpp_info.components["boost_coroutine"].set_property("cmake_target_name", "Boost::coroutine")
        self.cpp_info.components["boost_system"].includedirs = []
        self.cpp_info.components["boost_system"].libs = []
        self.cpp_info.components["boost_system"].requires = ["boost_headers"]
        self.cpp_info.components["boost_system"].set_property("cmake_target_name", "Boost::system")
