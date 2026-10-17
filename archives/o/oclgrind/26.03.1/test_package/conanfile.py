#!/usr/bin/env python3
"""Conan test_package — oclgrind 26.03.1

L1 test: links against the built oclgrind runtime and calls
clGetPlatformIDs, plus runs the oclgrind CLI (--version).
Both prove the package is linkable and executable.
"""

import json
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class OclgrindTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("opencl-headers/2026.05.29")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # 与主包一致: 真机 /tmp 只读, 复用 HMBS 注入的 TMPDIR 链并显式透传
        # 进构建环境, 避免编译器临时文件回退到只读 /tmp。
        # 加固: 逐个探测可写性 (mkdir + 写探针), 覆盖而非 setdefault,
        # 并重置 tempfile.tempdir 缓存, 防止沿用陈旧 /tmp。
        tmp_base = self._ensure_writable_tmpdir()
        env = Environment()
        for var in ("TMPDIR", "TMP", "TEMP"):
            env.define(var, tmp_base)
        # 与主包一致: conf 绝对编译器路径不可访问时回退 bare 工具名。
        c_fallback = self._conf_compiler_fallback("c", "clang")
        cxx_fallback = self._conf_compiler_fallback("cpp", "clang++")
        if c_fallback:
            env.define("CC", c_fallback)
        if cxx_fallback:
            env.define("CXX", cxx_fallback)
        # OHOS lld host runtime (E266, mirrors main recipe): prepend the
        # existing SDK llvm/lib so the SDK lld finds libxml2.so.16 during
        # the test_package CMake compiler probe.
        llvm_lib = self._ohos_sdk_llvm_lib()
        if llvm_lib:
            env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
        env.vars(self).save_script("oclgrind_test_tmpdir")

    # -- OHOS SDK lld host runtime (E266) ------------------------------
    # Merged precedents c-ares/1.34.5, zstd/1.5.6 (+ libgsf/babeltrace):
    # the OHOS SDK lld links libxml2.so.16 dynamically, which the worker
    # sandbox loader path does not contain, so lld fails to start and the
    # CMake project() probe reports the C/CXX compiler
    # (/data/service/hnp/bin/clang) broken. Fix: prepend the existing SDK
    # llvm/lib to LD_LIBRARY_PATH (fixed path + version glob, same paths
    # as c-ares). No compiler-check bypass, no worker-specific hardcoding
    # beyond the merged precedents, no global env pollution.

    @staticmethod
    def _ohos_sdk_llvm_lib():
        import glob
        candidates = []
        # Toolchain-derived first (ls-hpack minimal form): survives SDK
        # version drift; fixed path + glob as fallback (c-ares paths).
        try:
            import shutil
            for tool in (shutil.which("clang") or "", "/data/service/hnp/bin/clang"):
                if tool and os.path.isfile(tool):
                    real = os.path.realpath(tool)
                    llvm_root = os.path.dirname(os.path.dirname(real))
                    candidates.append(os.path.join(llvm_root, "lib"))
                    node = os.path.dirname(real)
                    for _ in range(4):
                        node = os.path.dirname(node)
                        if node in ("", os.path.sep):
                            break
                        candidates.append(os.path.join(node, "llvm", "lib"))
                        candidates.append(os.path.join(
                            node, "ohos", "native", "llvm", "lib"))
        except Exception:
            pass
        candidates += [
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib",
        ]
        sdk_base = os.environ.get(
            "OHOS_SDK_HOME", "/data/service/hnp/ohos-sdk.org")
        try:
            candidates += sorted(glob.glob(
                os.path.join(sdk_base, "*", "ohos", "native", "llvm", "lib")))
        except Exception:
            pass
        for candidate in dict.fromkeys(candidates):
            if candidate and os.path.isdir(candidate):
                return candidate
        return ""

    def _conf_compiler_fallback(self, kind, bare):
        # 与主包一致 (naga/1.0): conf 优先, 含分隔符的绝对路径非文件
        # 或不可执行时告警并回退到 bare 工具名经 PATH 解析。
        import shutil
        exe = None
        try:
            comp_exes = self.conf.get("tools.build:compiler_executables", default=None)
            if isinstance(comp_exes, dict):
                exe = comp_exes.get(kind)
        except Exception:
            exe = None
        if not exe:
            exe = os.environ.get("CC" if kind == "c" else "CXX")
        if not exe:
            return None
        has_sep = (os.path.sep in exe) or (os.path.altsep and os.path.altsep in exe)
        if not has_sep:
            return None
        try:
            is_file = os.path.isfile(exe)
        except OSError:
            is_file = False
        try:
            is_exec = os.access(exe, os.X_OK)
        except OSError:
            is_exec = False
        if is_file and is_exec:
            return None
        try:
            which = shutil.which(bare) or "(not on PATH)"
        except Exception:
            which = "(locate-failed)"
        self.output.warning(
            "OHOS compiler path: conf {}={!r} not file/executable "
            "(isfile={}, x_ok={}), fallback to {!r} via PATH ({})".format(
                kind, exe, is_file, is_exec, bare, which))
        return bare

    def _writable_tmpdir(self):
        import tempfile
        candidates = [
            os.environ.get("TMPDIR"),
            os.environ.get("TMP"),
            os.environ.get("TEMP"),
            os.path.join(self.build_folder, "tmp"),
        ]
        try:
            candidates.append(os.path.join(os.path.expanduser("~"), "tmp"))
        except Exception:
            pass
        for cand in candidates:
            if not cand:
                continue
            try:
                os.makedirs(cand, exist_ok=True)
                probe = os.path.join(cand, ".hmbs_write_probe")
                with open(probe, "w", encoding="utf-8") as probe_file:
                    probe_file.write("ok")
                try:
                    os.remove(probe)
                except OSError:
                    pass
                try:
                    tempfile.tempdir = cand
                except Exception:
                    pass
                return cand
            except OSError:
                continue
        fallback = os.path.join(self.build_folder, "tmp")
        try:
            os.makedirs(fallback, exist_ok=True)
        except OSError:
            pass
        return fallback

    def _ensure_writable_tmpdir(self):
        tmp_base = self._writable_tmpdir()
        for var in ("TMPDIR", "TMP", "TEMP"):
            os.environ[var] = tmp_base
        return tmp_base

    def _bad_conf_compilers(self):
        bad = {}
        for kind, bare in (("c", "clang"), ("cpp", "clang++")):
            exe = None
            try:
                comp_exes = self.conf.get("tools.build:compiler_executables", default=None)
                if isinstance(comp_exes, dict):
                    exe = comp_exes.get(kind)
            except Exception:
                exe = None
            if not exe:
                exe = os.environ.get("CC" if kind == "c" else "CXX")
            if not exe:
                continue
            has_sep = (os.path.sep in exe) or (os.path.altsep and os.path.altsep in exe)
            if not has_sep:
                continue
            try:
                ok = os.path.isfile(exe) and os.access(exe, os.X_OK)
            except OSError:
                ok = False
            if not ok:
                bad[exe] = bare
        return bad

    def _patch_toolchain_compiler(self):
        bad = self._bad_conf_compilers()
        if not bad:
            return 0
        roots = []
        for attr in ("generators_folder", "build_folder"):
            try:
                folder = getattr(self, attr, None)
            except Exception:
                folder = None
            if folder and os.path.isdir(folder):
                roots.append(folder)
        patched = 0
        seen = set()
        for root in roots:
            try:
                for dirpath, _dirs, files in os.walk(root):
                    for name in files:
                        if name not in ("conan_toolchain.cmake", "CMakePresets.json"):
                            continue
                        full = os.path.join(dirpath, name)
                        if full in seen:
                            continue
                        seen.add(full)
                        try:
                            with open(full, encoding="utf-8", errors="replace") as handle:
                                text = handle.read()
                        except OSError:
                            continue
                        new_text = text
                        for bad_path, bare in bad.items():
                            if bad_path in new_text:
                                new_text = new_text.replace(bad_path, bare)
                        if new_text != text:
                            try:
                                with open(full, "w", encoding="utf-8") as handle:
                                    handle.write(new_text)
                                patched += 1
                                self.output.warning(
                                    "OHOS compiler path: patched {} bad->bare {}".format(
                                        full, bad))
                            except OSError as exc:
                                self.output.warning(
                                    "OHOS compiler path: patch failed {}: {}".format(
                                        full, exc))
            except OSError:
                continue
        return patched

    def _prepare_ohos_lld_env(self):
        # zstd form (plain os.environ): visible to the cmake subprocess
        # even if a build script is sourced without the conanbuild
        # fragment. Complements the generate() Environment script.
        if str(self.settings.os) != "OHOS":
            return
        llvm_lib = self._ohos_sdk_llvm_lib()
        if not llvm_lib:
            self.output.info(
                "OHOS lld runtime: no SDK llvm/lib found, "
                "skipping LD_LIBRARY_PATH prepend")
            return
        current = os.environ.get("LD_LIBRARY_PATH", "")
        entries = [p for p in current.split(os.pathsep) if p] if current else []
        if llvm_lib not in entries:
            os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
                [llvm_lib] + entries)
        self.output.info(
            "OHOS lld runtime: prepended {} to LD_LIBRARY_PATH".format(
                llvm_lib))

    def build(self):
        # 与主包一致: OHOS 下默认 Makefiles 因 /bin/sh 被拒而失败 (E346),
        # test_package 同样改用 Ninja。工具链 preset 已为 Ninja, 此处保持一致。
        # 不再强制 CMAKE_SYSTEM_NAME / COMPILER_WORKS: 前者多轮验证未解决
        # compiler broken 且丢掉 OHOS sysroot, 后者违反 fail-closed, 均移除。
        # 改用 E266 的 SDK llvm/lib 前置 (c-ares/zstd 已合入先例)。
        # 另与主包一致: conf 绝对编译器路径失效时回退 bare 名, 保证相位一致。
        self._ensure_writable_tmpdir()
        self._prepare_ohos_lld_env()
        variables = {}
        try:
            c_fb = self._conf_compiler_fallback("c", "clang")
            cxx_fb = self._conf_compiler_fallback("cpp", "clang++")
            if c_fb:
                os.environ["CC"] = c_fb
                variables["CMAKE_C_COMPILER"] = c_fb
            if cxx_fb:
                os.environ["CXX"] = cxx_fb
                variables["CMAKE_CXX_COMPILER"] = cxx_fb
        except Exception:
            pass
        try:
            self._patch_toolchain_compiler()
        except Exception:
            pass
        try:
            oclgrind_pkg = self.dependencies["oclgrind"].package_folder
        except Exception:
            oclgrind_pkg = ""
        if oclgrind_pkg:
            variables["OCLGRIND_PACKAGE_FOLDER"] = oclgrind_pkg.replace("\\", "/")
        cmake = CMake(self)
        cmake.generator = "Ninja"
        cmake.configure(variables=variables or None)
        # 与主包一致: 串行构建防 Signal-9/OOM (wxWidgets 先例)。
        cmake.build(cli_args=["-j1"])

    def test(self):
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindirs[0], "test_oclgrind")
            self.run(bin_path, env="conanrun")
            oclgrind_bin = None
            for dep in self.dependencies.values():
                if getattr(dep.ref, "name", "") == "oclgrind":
                    candidate = os.path.join(dep.package_folder, "bin", "oclgrind")
                    if os.path.isfile(candidate):
                        oclgrind_bin = candidate
                        break
            if oclgrind_bin is None:
                raise Exception("oclgrind binary not found in package bin/")
            self.run("{} --version".format(oclgrind_bin), env="conanrun")
            marker = {
                "executed": True,
                "passed": True,
                "command": bin_path + " + oclgrind --version",
                "discovered": 2,
                "passedCount": 2,
            }
            print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker), flush=True)
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
            # Re-emit upstream evidence on EVERY run: conan skips the main
            # build() (and its live ctest marker) when the binary is cached.
            # The JSON was produced by the real ctest run in build() and
            # shipped in the package res/ dir; re-printing keeps the gate
            # supplied without re-running or faking any test.
            try:
                dep_pkg = None
                for dep in self.dependencies.values():
                    if getattr(dep.ref, "name", "") == "oclgrind":
                        dep_pkg = dep.package_folder
                        break
                if not dep_pkg:
                    raise Exception("oclgrind package folder not found for upstream re-emit")
                result_path = os.path.join(dep_pkg, "res", "upstream_test_result.json")
                if not os.path.isfile(result_path):
                    raise Exception(
                        "upstream_test_result.json not found in package ({}) — "
                        "upstream tests did not run during build(); refusing to pass "
                        "silently".format(result_path))
                with open(result_path, "r", encoding="utf-8") as handle:
                    upstream = json.load(handle)
                print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False), flush=True)
                self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))
            except Exception as exc:
                from conan.errors import ConanException as _HmbsConanException
                raise _HmbsConanException(
                    "oclgrind upstream re-emit failed: {}".format(exc))
