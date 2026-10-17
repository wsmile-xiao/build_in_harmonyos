#!/usr/bin/env python3
"""Conan recipe — oclgrind 26.03.1 (CMake)"""

import json
import os
import re
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class OclgrindConan(ConanFile):
    name = "oclgrind"
    version = "26.03.1"
    description = "OpenCL device simulator and debugger"
    license = "BSD-3-Clause"
    homepage = "https://github.com/jrprice/Oclgrind"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("readline/8.3")
        # LLVM>=18 + Clang dev files come from the repo clang package
        # (ccls/0.20250306.8 tracked precedent uses requires("clang/22.1.8");
        # ccls notes record clang/22.1.8 as published to the ohpcd artifact
        # repo, shipping libclang-cpp/libLLVM + headers + LLVM/Clang CMake
        # configs + lib/clang/22 resource headers incl. opencl-c.h).
        # Upstream oclgrind explicitly supports LLVM>=22 (CMakeLists
        # VERSION_GREATER_EQUAL 22.0 CLANG_LIBS branch).
        self.requires("clang/22.1.8")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "oclgrind only supports Linux/OHOS, got: {}".format(self.settings.os))
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                "OHOS builds require armv8/aarch64, got: {}".format(self.settings.arch))

    # NOTE: no LLVM>=18 fail-fast gate here anymore. LLVM 22 + Clang dev
    # files are guaranteed present via requires("clang/22.1.8") (ccls
    # precedent, ohpcd-published), so CMake find_package(LLVM) resolves
    # from the dependency package (wired in generate()). A user-provided
    # LLVM>=18 via -c user.oclgrind:llvm_dir=<prefix> or LLVM_DIR/CLANG_ROOT
    # env still overrides the package (see generate()).

    def layout(self):
        cmake_layout(self)

    def source(self):
        # PF7/R39: keep the single official URL (CI build_and_test.sh adds
        # the gh-proxy mirror fallback automatically). Harden against真机
        # github ConnectTimeout with explicit retries instead of a mirror
        # list: same reliability goal, different route from the reverted
        # mirror-list attempt, no blacklisted domain in-recipe.
        last_exc = None
        for attempt in range(1, 6):
            try:
                get(self, **self.conan_data["sources"], strip_root=True)
                return
            except Exception as exc:
                last_exc = exc
                self.output.warning(
                    "oclgrind source download attempt %d/5 failed: %s"
                    % (attempt, exc))
        raise last_exc

    def generate(self):
        # Harden TMPDIR first: toolchain generation itself may spill temp
        # files; verified writable dir must win before any cmake work.
        self._ensure_writable_tmpdir()
        # Ninja wired through the toolchain (not only cmake.generator in
        # build()): OHOS /bin/sh is execute-only, GNU Makefiles stat it and
        # fail (E009/E011, E346); Ninja execs the compiler directly.
        # SDL2_image/2.6.0.1 merged precedent uses the same constructor form.
        tc = CMakeToolchain(self, generator="Ninja")
        tc.variables["CMAKE_BUILD_TYPE"] = str(self.settings.build_type)
        try:
            readline_pkg = self.dependencies["readline"]
            tc.variables["READLINE_DIR"] = readline_pkg.package_folder.replace("\\", "/")
        except Exception:
            pass
        # LLVM>=18 wiring (ccls/0.20250306.8 pattern): user conf/env
        # override wins when provided (-c user.oclgrind:llvm_dir=<prefix>
        # or LLVM_DIR/CLANG_ROOT env); otherwise use the required
        # clang/22.1.8 package folder, which ships LLVM 22 + Clang dev
        # files (headers, clang-cpp, lib/clang/22/include/opencl-c.h,
        # bin/clang). CMAKE_PREFIX_PATH points at the package so
        # find_package(LLVM/Clang) hits the package\'s own LLVMConfig.cmake
        # / ClangConfig.cmake (ccls lesson: never let generated configs
        # shadow them).
        try:
            _conf_llvm_dir = self.conf.get("user.oclgrind:llvm_dir", default=None)
        except Exception:
            _conf_llvm_dir = None
        _llvm_dir = _conf_llvm_dir or os.environ.get("LLVM_DIR", "")
        _clang_root = os.environ.get("CLANG_ROOT", "")
        if not _llvm_dir or not _clang_root:
            try:
                _clang_pkg = self.dependencies["clang"].package_folder.replace("\\", "/")
            except Exception:
                _clang_pkg = ""
            if _clang_pkg:
                if not _llvm_dir:
                    _llvm_dir = _clang_pkg + "/lib/cmake/llvm"
                if not _clang_root:
                    _clang_root = _clang_pkg
        if _llvm_dir:
            tc.cache_variables["LLVM_DIR"] = _llvm_dir.replace("\\", "/")
        if _clang_root:
            tc.cache_variables["CLANG_ROOT"] = _clang_root.replace("\\", "/")
            tc.variables["CMAKE_PREFIX_PATH"] = _clang_root.replace("\\", "/")
        # Conf absolute compiler path fallback (naga/1.0 precedent):
        # conf stays preferred; only when a pathed value is not a file
        # or not executable do we override with the bare tool name so it
        # resolves via conanbuild PATH (harmonybrew clang on workers
        # where /data/service/hnp is not listable). No bypass: the real
        # project() probe still runs, just with a reachable compiler.
        c_fallback = self._conf_compiler_fallback("c", "clang")
        cxx_fallback = self._conf_compiler_fallback("cpp", "clang++")
        if c_fallback:
            tc.cache_variables["CMAKE_C_COMPILER"] = c_fallback
        if cxx_fallback:
            tc.cache_variables["CMAKE_CXX_COMPILER"] = cxx_fallback
        # NOTE: no CMAKE_SYSTEM_NAME override here. Forcing Linux via
        # tc.variables never took effect (variables land inside the toolchain
        # file after system determination; only cache_variables reach the
        # command line in time), and it drops the OHOS sysroot/flags the
        # profile toolchain sets. Upstream only checks
        # `STREQUAL "Windows"` / `UNIX AND NOT APPLE`, both of which behave
        # correctly under HarmonyOS, so keep the native OHOS system name
        # (ls-hpack/2.3.5 merged precedent builds clean on OHOS unforced).
        # NOTE: no CMAKE_C/CXX_COMPILER_WORKS or TRY_COMPILE_TARGET_TYPE
        # bypass (fail-closed boundary): the real compiler probe must
        # pass on its own; the SDK lld host runtime below makes it pass.
        tc.generate()
        # Readonly /tmp ([readonly_tmp] platform diagnosis). Reuse the
        # HMBS-injected task-scoped TMPDIR/TMP/TEMP chain and explicitly
        # propagate it into the conanbuild environment (audtty/hunspell
        # precedent): try-compile and clang temp files no longer fall back
        # to the read-only /tmp. Plain os.environ can be filtered by the
        # toolchain env, hence the Environment script.
        tmp_base = self._ensure_writable_tmpdir()
        env = Environment()
        for var in ("TMPDIR", "TMP", "TEMP"):
            env.define(var, tmp_base)
        if c_fallback:
            env.define("CC", c_fallback)
        if cxx_fallback:
            env.define("CXX", cxx_fallback)
        # OHOS lld host runtime (E266): prepend the existing SDK llvm/lib
        # so the SDK lld finds libxml2.so.16 during the CMake project()
        # compiler probe. Same conanbuild script that carries TMPDIR.
        llvm_lib = self._ohos_sdk_llvm_lib()
        if llvm_lib:
            env.prepend_path("LD_LIBRARY_PATH", llvm_lib)
            self.output.warning(
                "OHOS lld runtime: using SDK llvm/lib {}".format(llvm_lib))
        else:
            self.output.warning(
                "OHOS lld runtime: no SDK llvm/lib found under toolchain/SDK globs; {}".format(
                    self._sdk_base_listing()))
        # Host shared-lib runtime for upstream tests (scoped, NOT global):
        # oclgrind links libclang-cpp/libLLVM (clang/22.1.8, shared) +
        # readline (shared). Link time resolves via CMAKE_PREFIX_PATH/-L,
        # but plain cpp_info libdirs do not land on LD_LIBRARY_PATH
        # (no runenv_info), so ctest children need them at runtime.
        # They MUST NOT be prepended to the global conanbuild script:
        # CI #43874 proves /data/service/hnp/bin/cmake itself needs
        # libc++_shared.so, and prepending the clang package libdir first
        # shadows it ("Error loading shared library libc++_shared.so" +
        # hundreds of St4__n1 relocating failures, Error 127 before any
        # CMake log). Dep/built libdirs are scoped to the ctest Popen env
        # only (see _run_upstream_tests); here only the SDK llvm/lib
        # (lld's libxml2, E266) stays global.
        env.vars(self).save_script("oclgrind_tmpdir")

    def _host_dep_libdirs(self):
        # Existing host-dependency libdirs (clang/readline) for the ctest
        # runtime. Generic over lib/lib64; missing packages are skipped.
        dirs = []
        try:
            deps = self.dependencies
        except Exception:
            return dirs
        for _name in ("clang", "readline", "ncurses"):
            try:
                _folder = deps[_name].package_folder
            except Exception:
                continue
            if not _folder:
                continue
            for _sub in ("lib", "lib64"):
                _cand = os.path.join(_folder, _sub)
                try:
                    _isdir = os.path.isdir(_cand)
                except OSError:
                    _isdir = False
                if _isdir and _cand not in dirs:
                    dirs.append(_cand)
        return dirs

    @staticmethod
    def _runtime_lib_shadowed(basename):
        # Shared-lib families owned by the system toolchain: exposing a
        # dep copy via LD_LIBRARY_PATH hijacks EVERY binary in the Popen
        # tree, including ctest itself. CI #44391/#44560 prove the clang
        # package libdir ships a libc++_shared.so ABI-incompatible with
        # /data/service/hnp/bin/ctest ("Error loading shared library
        # libc++_shared.so" + hundreds of relocating failures, 0 cases
        # parsed) no matter where the dir sits in LD_LIBRARY_PATH order
        # (prepend tried first, append second, identical collapse).
        low = basename.lower()
        return low.startswith(
            ("libc++", "libstdc++", "libunwind", "libc++abi", "libgcc"))

    def _stage_test_runtime_libs(self, dep_libdirs, built_libdirs):
        # New route (different from prepend/append): publish ONLY the
        # needed runtime libs into one staging dir and expose just that
        # dir. Shadowing families (libc++/libstdc++/unwind) are never
        # staged, so ctest keeps resolving the system C++ runtime via
        # default search while children resolve libclang-cpp/libLLVM/
        # libreadline/liboclgrind via staging. Symlink preferred
        # (cheap); file copy fallback where symlink is unsupported.
        # Read-only walk of dep/build dirs, never raises, never skips a
        # test.
        import shutil as _shutil
        stage = os.path.join(self.build_folder, "oclgrind-test-libs")
        try:
            os.makedirs(stage, exist_ok=True)
        except OSError as exc:
            self.output.warning(
                "OHOS test runtime: staging dir unavailable {}: {}".format(
                    stage, exc))
            return ""
        staged = 0
        for src_dir in (dep_libdirs or []) + (built_libdirs or []):
            try:
                names = os.listdir(src_dir)
            except OSError:
                continue
            for name in names:
                if ".so" not in name:
                    continue
                if self._runtime_lib_shadowed(name):
                    continue
                src = os.path.join(src_dir, name)
                dst = os.path.join(stage, name)
                try:
                    if os.path.lexists(dst):
                        continue
                    if not (os.path.isfile(src) or os.path.islink(src)):
                        continue
                except OSError:
                    continue
                try:
                    try:
                        os.symlink(src, dst)
                    except (OSError, AttributeError, NotImplementedError):
                        _shutil.copy2(src, dst)
                    staged += 1
                except OSError as exc:
                    self.output.warning(
                        "OHOS test runtime: stage {} -> {} failed: {}".format(
                            src, dst, exc))
        self.output.warning(
            "OHOS test runtime: staged {} lib(s) into {}".format(
                staged, stage))
        return stage if staged else ""

    def _built_lib_dirs(self, build_folder, test_dir=""):
        # Directories holding the just-built liboclgrind(.so) for the
        # ctest runtime. Build-tree executables (oclgrind-kernel,
        # oclgrind-exe, rt_* samples) link against liboclgrind.so /
        # liboclgrind-rt.so via DT_NEEDED; on OHOS the build RPATH does
        # not resolve the sibling library, so the musl loader reports
        # "Error relocating <exe>: oclgrind::...: symbol not found" for
        # every oclgrind symbol (this round's new evidence). Prepending
        # these dirs to LD_LIBRARY_PATH lets the loader find the
        # just-built libs. Capped walk, read-only, never fails.
        dirs = []
        for cand in (test_dir, build_folder):
            if cand and cand not in dirs:
                try:
                    if os.path.isdir(cand):
                        dirs.append(cand)
                except OSError:
                    continue
        if not build_folder:
            return dirs
        try:
            for root, _dirs, files in os.walk(build_folder):
                for name in files:
                    if name.startswith("liboclgrind") and ".so" in name:
                        if root not in dirs:
                            dirs.append(root)
                        break
                if len(dirs) > 12:
                    break
        except OSError:
            pass
        return dirs

    def _conf_compiler_fallback(self, kind, bare):
        # naga/1.0 precedent, adapted: conf preferred; only a pathed
        # value that is not a file or not executable falls back to the
        # bare tool name resolved via conanbuild PATH. Returns bare on
        # fallback, None to keep toolchain default.
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
        # Hardened for [readonly_tmp]: probe each candidate for actual
        # writability (mkdir + write probe) instead of assuming makedirs
        # success. Prior form used setdefault + makedirs without a write
        # probe, so a read-only HMBS/system TMPDIR (e.g. under /tmp on
        # erofs workers) was kept silently and later clang/cmake temp
        # files fell back to read-only /tmp. Chain: HMBS-injected
        # TMPDIR/TMP/TEMP first, then build_folder/tmp, then $HOME/tmp.
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
                # Python caches TMPDIR in tempfile.tempdir at first use;
                # reset it so conan/cmake subprocess temp files follow the
                # verified writable dir instead of stale /tmp.
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
        # Override (not setdefault): a pre-existing read-only /tmp value
        # must not survive. Verified writable dir wins for all three vars.
        tmp_base = self._writable_tmpdir()
        for var in ("TMPDIR", "TMP", "TEMP"):
            os.environ[var] = tmp_base
        return tmp_base

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
        # 1) Toolchain-derived: from the configured OHOS clang realpath
        # (ls-hpack/2.3.5 merged precedent, minimal form). Handles SDK
        # version drift where the fixed 26.0.0.18 path no longer exists.
        # No worker-specific hardcoding: purely derived from active conf.
        try:
            # conf access needs instance, so try env PATH resolution here;
            # full conf-derived path is added by caller when available.
            import shutil
            for tool in (shutil.which("clang") or "", "/data/service/hnp/bin/clang"):
                if tool and os.path.isfile(tool):
                    real = os.path.realpath(tool)
                    llvm_root = os.path.dirname(os.path.dirname(real))
                    candidates.append(os.path.join(llvm_root, "lib"))
                    # SDK layout: .../ohos/native/llvm/bin/lld -> .../llvm/lib
                    # wrapper realpath may be .../hnp/bin/clang -> walk up
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

    def _prepare_ohos_lld_env(self):
        # zstd form (plain os.environ): visible to the cmake subprocess
        # even if a build script is sourced without the conanbuild
        # fragment. Complements the generate() Environment script.
        if str(self.settings.os) != "OHOS":
            return
        # NOTE: only the SDK llvm/lib (lld's libxml2, E266) is prepended
        # globally here. Host dep libdirs (clang/readline) and just-built
        # tree libdirs are scoped to the ctest Popen env only: CI #43874
        # proves prepending the clang package libdir globally shadows the
        # libc++_shared.so that /data/service/hnp/bin/cmake itself needs
        # (Error 127 before any CMake log).
        llvm_lib = self._ohos_sdk_llvm_lib()
        if not llvm_lib:
            self.output.warning(
                "OHOS lld runtime: no SDK llvm/lib found, "
                "skipping LD_LIBRARY_PATH prepend; sdk bases: {}".format(
                    self._sdk_base_listing()))
            return
        current = os.environ.get("LD_LIBRARY_PATH", "")
        entries = [p for p in current.split(os.pathsep) if p] if current else []
        if llvm_lib not in entries:
            os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
                [llvm_lib] + entries)
        self.output.info(
            "OHOS lld runtime: prepended {} to LD_LIBRARY_PATH".format(
                llvm_lib))

    @staticmethod
    def _sdk_base_listing():
        import shutil
        parts = []
        try:
            cc = shutil.which("clang") or "/data/service/hnp/bin/clang"
            parts.append("which-clang=" + (cc or "(none)"))
            if cc and os.path.isfile(cc):
                parts.append("realpath=" + os.path.realpath(cc))
        except Exception as exc:
            parts.append("clang-locate-failed=" + str(exc))
        for base in ("/data/service/hnp",
                     "/data/service/hnp/ohos-sdk.org"):
            try:
                entries = sorted(os.listdir(base)) if os.path.isdir(base) else ["(missing)"]
            except OSError as exc:
                entries = ["(list-failed: {})".format(exc)]
            parts.append(base + ": " + ",".join(entries[:10]))
        return "; ".join(parts)

    def _bad_conf_compilers(self):
        # Return {bad_absolute_path: bare_name} for conf/env compilers
        # that contain a separator but are not file/executable.
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
        # Different route: preset cacheVariables and configure -D are both
        # overridden by the profile OHOS toolchain file content itself
        # (preflight proved WARN fired yet CMAKE_C_COMPILER stayed
        # absolute). Patch the generated conan_toolchain.cmake /
        # CMakePresets.json on disk so the toolchain no longer points at
        # the unreachable absolute path. Returns patched file count.
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

    def _dump_cmake_logs(self):
        # CMake 4.x no longer writes CMakeError.log/CMakeOutput.log for
        # failed project() probes; the record is
        # CMakeFiles/<ver>/CMakeConfigureLog.yaml (+ CMakeCache.txt).
        # Prior round proved this: tree showed only CMakeConfigureLog.yaml
        # and empty CompilerIdC/tmp. Dump the YAML failed events at
        # error level (focused summaries omit info) and embed into the
        # exception so the next round carries the true compiler error.
        hits = []
        yaml_hits = []
        try:
            for root, _dirs, files in os.walk(self.build_folder):
                for name in files:
                    full = os.path.join(root, name)
                    if name in ("CMakeError.log", "CMakeOutput.log"):
                        hits.append(full)
                    elif name == "CMakeConfigureLog.yaml":
                        yaml_hits.append(full)
                    elif name in ("CMakeCache.txt", "cmake.check_cache"):
                        hits.append(full)
        except OSError:
            pass
        tail_lines = []
        for path in sorted(set(hits))[:4]:
            try:
                with open(path, encoding="utf-8", errors="replace") as log_file:
                    lines = log_file.read().splitlines()
            except OSError:
                continue
            self.output.error("=== {} (last {} lines) ===".format(path, min(60, len(lines))))
            for line in lines[-60:]:
                self.output.error(line)
            tail_lines += lines[-40:]
        for path in sorted(set(yaml_hits))[:2]:
            try:
                with open(path, encoding="utf-8", errors="replace") as log_file:
                    text = log_file.read()
            except OSError:
                continue
            lines = text.splitlines()
            # Extract failed events: keep event blocks containing
            # failed/error/broken + surrounding context.
            keep = []
            for idx, line in enumerate(lines):
                low = line.lower()
                if ("failed" in low or "error" in low or "broken" in low
                        or "not able to compile" in low):
                    start = max(0, idx - 15)
                    end = min(len(lines), idx + 40)
                    keep += lines[start:end]
                    keep.append("---")
                    if len(keep) > 220:
                        break
            excerpt = keep[-220:] if keep else lines[-120:]
            self.output.error("=== {} (filtered {} lines) ===".format(path, len(excerpt)))
            for line in excerpt[-120:]:
                self.output.error(line)
            tail_lines += excerpt[-80:]
        tail = "\n".join(tail_lines[-160:])
        if not tail:
            # No CMake logs at all (probe failed before logging or preset
            # binaryDir outside build_folder): list the tree so the next
            # round can see where configure actually ran.
            try:
                tree = []
                for root, dirs, files in os.walk(self.build_folder):
                    level = root.replace(self.build_folder, "").count(os.path.sep)
                    if level > 4:
                        dirs[:] = []
                        continue
                    tree.append(root + " dirs=" + ",".join(dirs[:8])
                                + " files=" + ",".join(files[:12]))
                    if len(tree) > 40:
                        break
                listing = "\n".join(tree) or "(build_folder empty/missing)"
            except OSError as exc:
                listing = "build tree walk failed: {}".format(exc)
            self.output.error("oclgrind: no CMakeError/Output.log under build_folder; tree:\n" + listing)
            tail = "no CMakeError/Output.log found. build tree:\n" + listing
        return tail

    def build(self):
        apply_conandata_patches(self)
        self._ensure_writable_tmpdir()
        self._prepare_ohos_lld_env()
        # Mirror generate() fallback into the live process so the cmake
        # subprocess sees reachable CC/CXX even if the conanbuild script
        # fragment is not sourced (zstd plain-os.environ form).
        try:
            c_fb = self._conf_compiler_fallback("c", "clang")
            cxx_fb = self._conf_compiler_fallback("cpp", "clang++")
            if c_fb:
                os.environ["CC"] = c_fb
            if cxx_fb:
                os.environ["CXX"] = cxx_fb
        except Exception:
            c_fb = None
            cxx_fb = None
        cmake = CMake(self)
        # Generator agrees with the toolchain preset (Ninja); OHOS hmmac
        # sandbox rejects Make SHELL=/bin/sh try-compile (E346).
        cmake.generator = "Ninja"
        # tc.cache_variables alone did not override: the profile OHOS
        # toolchain file still forces /data/service/hnp/bin/clang (see
        # preflight: fallback WARN fired yet CMAKE_C_COMPILER stayed
        # absolute). Command-line -D via configure(variables=...) wins
        # over the toolchain file, so pass the fallback here as well.
        conf_vars = {}
        if c_fb:
            conf_vars["CMAKE_C_COMPILER"] = c_fb
        if cxx_fb:
            conf_vars["CMAKE_CXX_COMPILER"] = cxx_fb
        # Toolchain-file patch route: rewrite the unreachable absolute
        # compiler inside the generated toolchain/preset files before
        # configure, so project() no longer execs the bad path.
        try:
            self._patch_toolchain_compiler()
        except Exception:
            pass
        try:
            cmake.configure(variables=conf_vars or None)
        except Exception as exc:
            tail = self._dump_cmake_logs()
            raise ConanException(
                "oclgrind cmake configure failed ({}). "
                "CMakeError.log tail:\n{}".format(exc, tail or "(empty)"))
        # Signal-9 (SIGKILL/OOM) guard: force serial Ninja build. The
        # default Ninja parallelism scales with nproc and each oclgrind
        # TU includes heavy LLVM/Clang headers, so parallel compile
        # peaks workers into the OOM killer on the constrained worker
        # (wxWidgets/3.2.6 merged precedent: cmake.build(cli_args=["-j1"])
        # for the OHOS parallel constraint; HMBS also injects
        # tools.build:jobs=1, this is defense-in-depth inside the recipe
        # so a missing conf can never reintroduce parallel OOM).
        cmake.build(cli_args=["-j1"])
        self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Run upstream ctest suite and emit HMBS evidence marker.

        Source audit (v26.03.1 tag):
        - tests/kernels/TESTS lists 90 kernel sim cases run via
          tests/run_test.py + oclgrind-kernel.
        - tests/runtime/CMakeLists.txt registers 5 rt_* tests.
        - tests/apps/CMakeLists.txt registers 2 app_* tests.
        Total: 97 ctest cases, framework ctest, command ctest.
        Numbers below come from the actual ctest output, never from
        this comment.
        """
        build_folder = self.build_folder
        test_dir = self._ctest_binary_dir(build_folder)
        log_path = os.path.join(build_folder, "ctest-oclgrind.log")
        cmd = ["ctest", "--output-on-failure"]
        self.output.info(
            "Running upstream tests: {} (cwd={})".format(" ".join(cmd), test_dir)
        )
        # Scoped test runtime (CI #43874, CI #44391/#44560): ONLY the
        # staging dir goes into a COPY of the environment passed to the
        # ctest Popen (env=test_env), never into global os.environ and
        # never the raw clang package libdir. Raw-dir prepend was tried
        # first (ctest killed, CI #43874 lesson for cmake), raw-dir
        # append second (identical collapse in CI #44560: "Error loading
        # shared library libc++_shared.so (needed by ctest)" + hundreds
        # of relocating failures, 0 cases parsed) — proving position in
        # LD_LIBRARY_PATH is irrelevant: LD_LIBRARY_PATH is searched
        # before default paths, so any visible clang libc++ hijacks
        # ctest itself. The staging dir holds only the needed SONAMEs
        # (libclang-cpp/libLLVM/libreadline/liboclgrind/...) with the
        # libc++/libstdc++/unwind families excluded, so ctest resolves
        # the system C++ runtime normally while children resolve the
        # staged libs. Just-built tree libs: oclgrind-kernel/
        # oclgrind-exe/rt_* link against ./liboclgrind.so via DT_NEEDED;
        # OHOS build RPATH does not resolve the sibling lib, so the musl
        # loader reports "Error relocating <exe>: oclgrind::...: symbol
        # not found" without them. No test skipped, no assertion touched.
        test_env = dict(os.environ)
        _ld_entries = [p for p in test_env.get("LD_LIBRARY_PATH", "").split(os.pathsep) if p]
        _dep_libdirs = self._host_dep_libdirs()
        for _dep_lib in _dep_libdirs:
            self.output.warning(
                "OHOS test runtime: staging from dep libdir {}".format(_dep_lib))
        _built_libdirs = self._built_lib_dirs(build_folder, test_dir)
        for _built_lib in _built_libdirs:
            self.output.warning(
                "OHOS test runtime: staging from built libdir {}".format(_built_lib))
        _stage = self._stage_test_runtime_libs(_dep_libdirs, _built_libdirs)
        if _stage and _stage not in _ld_entries:
            _ld_entries.append(_stage)
        test_env["LD_LIBRARY_PATH"] = os.pathsep.join(_ld_entries)
        self.output.warning(
            "OHOS test runtime: LD_LIBRARY_PATH={}".format(
                test_env.get("LD_LIBRARY_PATH", "(empty)")))
        return_code = 1
        output_text = ""
        try:
            proc = subprocess.Popen(
                cmd,
                cwd=test_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env=test_env,
            )
            lines = []
            assert proc.stdout is not None
            for line in proc.stdout:
                lines.append(line)
                sys.stdout.write(line)
                sys.stdout.flush()
            return_code = proc.wait()
            output_text = "".join(lines)
        except FileNotFoundError as exc:
            reason = "ctest executable not found: {!r}".format(exc)
            self._emit_ctest_marker(0, 0, 0, 0, 0, "failed", reason)
            raise ConanException("oclgrind upstream tests failed: " + reason)
        try:
            with open(log_path, "w", encoding="utf-8") as log_file:
                log_file.write(output_text)
        except OSError:
            pass
        discovered, executed, passed, failed, skipped = self._parse_ctest_output(output_text)
        status = "failed"
        reason = ""
        if discovered > 0 and executed == discovered and failed == 0 and skipped == 0 and return_code == 0:
            status = "passed"
        elif discovered == 0:
            reason = "no ctest cases parsed from ctest output"
        elif return_code != 0 and failed == 0 and passed == 0:
            reason = "ctest exited with code {} but no per-test counts parsed".format(return_code)
        elif failed > 0:
            reason = "ctest reports {} failed case(s)".format(failed)
        elif skipped > 0:
            reason = "ctest reports {} skipped case(s)".format(skipped)
        elif executed != discovered:
            reason = "ctest executed {}/{} discovered cases".format(executed, discovered)
        self._emit_ctest_marker(discovered, executed, passed, failed, skipped, status, reason)
        if status != "passed":
            # Diagnostic surfacing (different strategy from prior rounds):
            # the focused preflight summary truncates the middle of the
            # ctest output, so per-test failure text never reaches the
            # next round. Emit the first-failure excerpt at error level
            # and embed it plus a runtime probe into the exception text
            # (exception text always surfaces). No test is skipped.
            excerpt = self._ctest_failure_excerpt(output_text)
            try:
                probe = self._probe_test_runtime(test_dir, test_env)
            except Exception as exc:
                probe = "probe-error={!r}".format(exc)
            self.output.error("=== oclgrind first-failure excerpt ===")
            for _line in excerpt.splitlines()[-60:]:
                self.output.error(_line)
            self.output.error(
                "=== oclgrind runtime probe: {} ===".format(probe))
            raise ConanException(
                "oclgrind upstream tests did not pass: {}; probe: {}; "
                "excerpt:\n{}".format(reason, probe, excerpt))

    @staticmethod
    def _ctest_failure_excerpt(text, max_lines=60):
        # First "***Failed" test block + trailing summary. Capped so the
        # exception text stays small but still carries the true error.
        lines = text.splitlines()
        first_fail = -1
        for idx, line in enumerate(lines):
            if "***Failed" in line or "***Timeout" in line:
                first_fail = idx
                break
        if first_fail >= 0:
            tail = lines[-15:] if len(lines) > 15 else []
            head_budget = max(10, max_lines - 1 - len(tail))
            start = max(0, first_fail - 3)
            head = lines[start:start + head_budget]
            excerpt = head + ["---"] + tail
        else:
            excerpt = lines[-max_lines:] if len(lines) > max_lines else lines
        return "\n".join(excerpt[:max_lines]) or "(empty ctest output)"

    def _probe_test_runtime(self, test_dir, test_env=None):
        # Distinguish "binary cannot start" (loader/signing/permission)
        # from "kernels fail to compile" (PCH/clang). Cheap, read-only.
        notes = []
        pch_dir = os.path.join(test_dir, "include", "oclgrind")
        try:
            if os.path.isdir(pch_dir):
                entries = sorted(os.listdir(pch_dir))
            else:
                entries = ["(missing-dir)"]
        except OSError as exc:
            entries = ["(list-failed: {})".format(exc)]
        notes.append("PCH_DIR={} files={}".format(
            pch_dir, ",".join(entries[:12])))
        kern = ""
        try:
            for root, _dirs, files in os.walk(test_dir):
                if "oclgrind-kernel" in files:
                    kern = os.path.join(root, "oclgrind-kernel")
                    break
        except OSError:
            pass
        notes.append("KERNEL_BIN={}".format(kern or "(not-found)"))
        if kern:
            try:
                proc = subprocess.run(
                    [kern, "--version"],
                    capture_output=True, text=True, timeout=60,
                    env=test_env if test_env is not None else None)
                out = ((proc.stdout or "") + (proc.stderr or "")).strip()
                notes.append("KERNEL_VERSION rc={} out={!r}".format(
                    proc.returncode, out[-400:]))
            except Exception as exc:
                notes.append("KERNEL_VERSION probe-failed={!r}".format(exc))
        return "; ".join(notes)

    @staticmethod
    def _ctest_binary_dir(build_folder):
        # cmake_layout + preset 下二进制与 CTestTestfile 落在 build/<config>
        # 子目录, 直接在 build_folder 跑 ctest 会报 "no tests found"。
        # 搜索首个含 CTestTestfile.txt 的目录, 找不到则回退 build_folder。
        try:
            for root, _dirs, files in os.walk(build_folder):
                if "CTestTestfile.txt" in files:
                    return root
        except OSError:
            pass
        return build_folder

    @staticmethod
    def _parse_ctest_output(text):
        """Parse ctest output into (discovered, executed, passed, failed, skipped)."""
        passed_tests = set()
        failed_tests = set()
        timeout_tests = set()
        skipped_tests = set()
        for match in re.finditer(r"^\s*\d+/\d+\s+Test\s+#\d+:\s+(\S+)\s.*?\bPassed\b", text, re.MULTILINE):
            passed_tests.add(match.group(1))
        for match in re.finditer(r"^\s*\d+/\d+\s+Test\s+#\d+:\s+(\S+)\s.*?\*\*\*Failed\b", text, re.MULTILINE):
            failed_tests.add(match.group(1))
        for match in re.finditer(r"^\s*\d+/\d+\s+Test\s+#\d+:\s+(\S+)\s.*?\*\*\*Timeout\b", text, re.MULTILINE):
            timeout_tests.add(match.group(1))
        for match in re.finditer(r"^\s*\d+/\d+\s+Test\s+#\d+:\s+(\S+)\s.*?\*\*\*Skipped\b", text, re.MULTILINE):
            skipped_tests.add(match.group(1))
        # Summary line: "97% tests passed, 3 tests failed out of 97" or
        # "100% tests passed, 0 tests failed out of 97".
        summary = re.search(r"(\d+)% tests passed,\s*(\d+) tests? failed out of (\d+)", text)
        if summary:
            total = int(summary.group(3))
            failed = int(summary.group(2))
            passed = total - failed
            # Skipped details appear as separate lines; keep parsed skips.
            skipped = len(skipped_tests)
            # Timeouts count as failures.
            failed += len(timeout_tests - failed_tests)
            executed = passed + failed
            discovered = total
            # Reconcile with per-test sets when available.
            if passed_tests or failed_tests:
                passed = len(passed_tests - failed_tests - timeout_tests)
                failed = len((failed_tests | timeout_tests) - set())
                executed = passed + failed + skipped
                discovered = max(total, executed + skipped)
            return (discovered, executed, passed, failed, skipped)
        # Fallback: "tests passed" without summary (older CTest).
        if passed_tests or failed_tests or timeout_tests or skipped_tests:
            passed = len(passed_tests - failed_tests - timeout_tests)
            failed = len(failed_tests | timeout_tests)
            skipped = len(skipped_tests)
            discovered = passed + failed + skipped
            executed = passed + failed
            return (discovered, executed, passed, failed, skipped)
        return (0, 0, 0, 0, 0)

    def _emit_ctest_marker(self, discovered, executed, passed, failed, skipped, status, reason):
        marker = {
            "status": status,
            "framework": "ctest",
            "command": "ctest --output-on-failure",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        if reason:
            marker["reason"] = reason
        # Direct stdout print (not only self.output.info): focused preflight
        # summaries can truncate info-level lines, and cached build() runs
        # skip this entirely (see package()/test_package re-emit below).
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False), flush=True)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))
        # Persist for test_package re-emit on cached runs: conan skips
        # build() entirely when the binary is cached ("Already installed"),
        # leaving the gate without upstream evidence. package() ships this
        # JSON; test_package re-prints it on EVERY run (abuild-sudo/naga
        # precedent). Numbers come from this real ctest run.
        try:
            result_path = os.path.join(self.build_folder, "upstream_test_result.json")
            with open(result_path, "w", encoding="utf-8") as handle:
                json.dump(marker, handle, ensure_ascii=False)
        except OSError as exc:
            self.output.warning(
                "could not persist upstream_test_result.json: {}".format(exc))
        return marker

    def package(self):
        cmake = CMake(self)
        cmake.generator = "Ninja"
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        # Ship the upstream ctest evidence so test_package can re-emit it
        # when build() is skipped on a cached binary.
        try:
            src_json = os.path.join(self.build_folder, "upstream_test_result.json")
            if os.path.isfile(src_json):
                copy(self, "upstream_test_result.json", src=self.build_folder,
                     dst=os.path.join(self.package_folder, "res"))
        except Exception as exc:
            self.output.warning(
                "could not package upstream_test_result.json: {}".format(exc))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "oclgrind")
        self.cpp_info.set_property("cmake_target_name", "oclgrind::oclgrind")
        self.cpp_info.libs = ["oclgrind", "oclgrind-rt"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "dl", "pthread"]
