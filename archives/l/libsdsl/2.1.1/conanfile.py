#!/usr/bin/env python3
"""Conan recipe — libsdsl 2.1.1 (CMake)."""

import glob
import json
import os
import re
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rm


class LibsdslConan(ConanFile):
    name = "libsdsl"
    version = "2.1.1"
    description = "Succinct data structures library (bitvectors, int-vectors, wavelet trees, CSA/CST)"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/simongog/sdsl-lite"
    url = "https://github.com/simongog/sdsl-lite"
    topics = ("succinct", "data-structures", "bitvector", "wavelet-tree", "csa")

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        # Official release tarball leaves external submodules as empty dirs.
        # Vendor matching releases into the paths external/CMakeLists.txt expects.
        get(self, **self.conan_data["divsufsort"], strip_root=True,
            destination=os.path.join(self.source_folder, "external", "libdivsufsort"))
        get(self, **self.conan_data["googletest"], strip_root=True,
            destination=os.path.join(self.source_folder, "external", "googletest"))
        self._patch_inv_perm_for_cxx17()
        self._patch_bits_for_aarch64()
        self._patch_temp_buffer_tmpdir()

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake 4.x removed compatibility with < 3.5; sdsl-lite 2.1.1 declares
        # cmake_minimum_required(VERSION 2.8.x). Must be a cache variable so it
        # takes effect during CMake's early policy check (tc.variables is too late).
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # CMake has no Platform/HarmonyOS module: with the Conan OHOS
        # toolchain's CMAKE_SYSTEM_NAME=HarmonyOS the compiler ABI probe
        # inside project() fails ("System is unknown to cmake"). OHOS is a
        # Linux-kernel native aarch64 target, so select the Linux platform
        # module (E092; abcmidi/zxc precedent). Cache variables so platform
        # selection sees them.
        if str(self.settings.os) == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = (
                "aarch64" if str(self.settings.arch) == "armv8"
                else str(self.settings.arch)
            )
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        tc.variables["CODE_COVERAGE"] = "OFF"
        tc.variables["GENERATE_DOC"] = "OFF"
        # Profile pins tools.build:compiler_executables to
        # /data/service/hnp/bin/clang(++), but this preflight worker has no
        # such file (sanity: --version Errno 2, exists False) so project()
        # reports "compiler identification is unknown". When the conf path
        # is dangling, fall back to a PATH/SDK-resolved compiler
        # (ayatana-ido precedent). isfile only: HMDFS ignores chmod so
        # os.access(X_OK) is unreliable (R49).
        self._override_broken_conf_compiler(tc)
        # Compiler-ID probe only needs compilation, not a full link.
        # STATIC_LIBRARY skips the link step where the fragile host lld
        # runtime lives (ettercap precedent); real build still links.
        tc.cache_variables["CMAKE_TRY_COMPILE_TARGET_TYPE"] = "STATIC_LIBRARY"
        tc.generate()
        # tc.cache_variables override alone does NOT move the toolchain:
        # preflight proved the generated conan_toolchain.cmake still holds
        # /data/service/hnp/bin/clang(++) even after fallback logging.
        # Patch the emitted file plus CC/CXX so project() sees the live compiler.
        self._patch_toolchain_for_broken_compiler()
        # HMBS readonly /tmp: TMPDIR must land in conanbuild.sh (generate
        # time), not only os.environ in build(). Otherwise CMake compiler
        # probe spawned via aggregated env still sees readonly /tmp.
        try:
            tmp = self._writable_tmpdir()
        except Exception:
            tmp = None
        if tmp:
            env = Environment()
            env.define("TMPDIR", tmp)
            env.define("TMP", tmp)
            env.define("TEMP", tmp)
            for _k in ("HMBS_TMPDIR", "HMBS_AUTOCONF_MKTEMP_FALLBACK", "HMBS_CAP_LOCAL_MKTEMP"):
                _v = os.environ.get(_k)
                if _v:
                    env.define(_k, _v)
            env.vars(self, scope="build").save_script("hmbs_tmpdir")

    def _override_broken_conf_compiler(self, tc):
        try:
            exes = self.conf.get("tools.build:compiler_executables", default=None)
        except Exception:
            exes = None
        conf_c = conf_cxx = None
        if isinstance(exes, dict):
            conf_c = exes.get("c")
            conf_cxx = exes.get("cpp") or exes.get("cxx") or exes.get("c")
        self._hmbs_broken_map = {}
        for key, conf_val, bare in (
            ("CMAKE_C_COMPILER", conf_c, "clang"),
            ("CMAKE_CXX_COMPILER", conf_cxx, "clang++"),
        ):
            try:
                usable = bool(conf_val) and os.path.isfile(str(conf_val))
            except Exception:
                usable = False
            if usable:
                continue
            if conf_val:
                self.output.warning("conf compiler '%s' missing; resolving %s from PATH/SDK" % (conf_val, bare))
            found = self._discover_compiler(bare)
            if found:
                tc.cache_variables[key] = found
                try:
                    self._hmbs_broken_map[str(conf_val)] = found
                except Exception:
                    pass
                self.output.info("compiler fallback %s -> %s" % (key, found))
                ar = self._sibling_tool(found, "llvm-ar" if "clang" in bare else None)
                if ar and key == "CMAKE_C_COMPILER":
                    tc.cache_variables["CMAKE_AR"] = ar
                    self.output.info("ar fallback CMAKE_AR -> %s" % ar)

    def _patch_toolchain_for_broken_compiler(self):
        broken = dict(getattr(self, "_hmbs_broken_map", {}) or {})
        if not broken:
            # generate()/build() may not share instance state; rebuild from conf.
            try:
                exes = self.conf.get("tools.build:compiler_executables", default=None)
            except Exception:
                exes = None
            conf_c = conf_cxx = None
            if isinstance(exes, dict):
                conf_c = exes.get("c")
                conf_cxx = exes.get("cpp") or exes.get("cxx") or exes.get("c")
            for conf_val, bare in ((conf_c, "clang"), (conf_cxx, "clang++")):
                try:
                    usable = bool(conf_val) and os.path.isfile(str(conf_val))
                except Exception:
                    usable = False
                if usable or not conf_val:
                    continue
                found = self._discover_compiler(bare)
                if found:
                    broken[str(conf_val)] = found
            try:
                self._hmbs_broken_map = broken
            except Exception:
                pass
        if not broken:
            return
        paths = []
        try:
            gf = getattr(self, "generators_folder", None)
            if gf:
                paths.append(os.path.join(gf, "conan_toolchain.cmake"))
        except Exception:
            pass
        try:
            for root, _d, files in os.walk(self.build_folder):
                if "conan_toolchain.cmake" in files:
                    p = os.path.join(root, "conan_toolchain.cmake")
                    if p not in paths:
                        paths.append(p)
        except Exception:
            pass
        for p in paths:
            try:
                with open(p, "r", encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
            except Exception as exc:
                self.output.warning("cannot read toolchain %s: %s" % (p, exc))
                continue
            orig = text
            for bad, good in broken.items():
                if bad and bad in text:
                    text = text.replace(bad, good)
            if text != orig:
                try:
                    with open(p, "w", encoding="utf-8") as fh:
                        fh.write(text)
                    self.output.info("patched toolchain %s: %s" % (p, broken))
                except Exception as exc:
                    self.output.warning("cannot patch toolchain %s: %s" % (p, exc))
        # Belt-and-suspenders for any direct compiler spawn: CC/CXX + build-scope script.
        try:
            inv = {v: k for k, v in {"CMAKE_C_COMPILER": "CC", "CMAKE_CXX_COMPILER": "CXX"}.items()}
            env = Environment()
            for bad, good in broken.items():
                pass
            c_map = {}
            for key in ("CMAKE_C_COMPILER", "CMAKE_CXX_COMPILER"):
                for bad, good in broken.items():
                    if (key == "CMAKE_C_COMPILER" and "++" not in good) or (key == "CMAKE_CXX_COMPILER" and "++" in good):
                        c_map[key] = good
            if c_map.get("CMAKE_C_COMPILER"):
                env.define("CC", c_map["CMAKE_C_COMPILER"])
                os.environ["CC"] = c_map["CMAKE_C_COMPILER"]
            if c_map.get("CMAKE_CXX_COMPILER"):
                env.define("CXX", c_map["CMAKE_CXX_COMPILER"])
                os.environ["CXX"] = c_map["CMAKE_CXX_COMPILER"]
            env.vars(self, scope="build").save_script("hmbs_compiler")
        except Exception as exc:
            self.output.warning("cannot save compiler env: %s" % exc)

    def _discover_compiler(self, bare):
        cands = []
        for envk in ("CC", "CXX") if "++" not in bare else ("CXX", "CC"):
            v = os.environ.get(envk)
            if v:
                cands.append(v.split()[0])
        w = shutil.which(bare)
        if w:
            cands.append(w)
        for envk in ("HMBS_CMAKE", "HMBS_MAKE", "HMBS_NINJA", "HMBS_PYTHON3"):
            p = os.environ.get(envk)
            if p:
                cands.append(os.path.join(os.path.dirname(p), bare))
        try:
            cp = self.conf.get("user.hmbs:cmake_path")
            if cp:
                cands.append(os.path.join(os.path.dirname(str(cp)), bare))
        except Exception:
            pass
        for pat in (
            "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/bin/" + bare,
            "/opt/ohos-sdk/ohos/native/llvm/bin/" + bare,
        ):
            try:
                cands.extend(glob.glob(pat))
            except Exception:
                pass
        for d in ("/storage/Users/currentUser/usr/local/bin", "/usr/local/bin", "/usr/bin"):
            cands.append(os.path.join(d, bare))
        try:
            home = os.path.expanduser("~")
            if home:
                cands.append(os.path.join(home, ".harmonybrew", "bin", bare))
        except Exception:
            pass
        for c in cands:
            try:
                if c and os.path.isfile(c):
                    return c
            except Exception:
                continue
        return None

    @staticmethod
    def _sibling_tool(compiler, name):
        if not name:
            return None
        try:
            sib = os.path.join(os.path.dirname(compiler), name)
            if os.path.isfile(sib):
                return sib
        except Exception:
            pass
        return None

    def _writable_tmpdir(self):
        # Priority: HMBS_TMPDIR first (per-task runtime dir), then
        # TMPDIR/TMP/TEMP, then build_folder fallback. Probe with
        # mkstemp real write (HMDFS ignores chmod/os.access).
        for var in ("HMBS_TMPDIR", "TMPDIR", "TMP", "TEMP"):
            d = os.environ.get(var)
            if d and d not in ("/tmp",):
                try:
                    os.makedirs(d, exist_ok=True)
                    fd, probe = tempfile.mkstemp(dir=d)
                    os.close(fd)
                    os.unlink(probe)
                    return d
                except Exception:
                    continue
        try:
            fallback = os.path.join(self.build_folder, ".tmp")
        except Exception:
            fallback = None
        if fallback:
            try:
                os.makedirs(fallback, exist_ok=True)
                fd, probe = tempfile.mkstemp(dir=fallback)
                os.close(fd)
                os.unlink(probe)
                return fallback
            except Exception:
                pass
        return os.environ.get("HMBS_TMPDIR") or os.environ.get("TMPDIR")

    def _ensure_writable_tmpdir(self):
        cand = self._writable_tmpdir()
        if cand:
            try:
                os.makedirs(cand, exist_ok=True)
            except Exception:
                pass
            for key in ("TMPDIR", "TMP", "TEMP"):
                os.environ[key] = cand
            self.output.info("writable TMPDIR selected: %s" % cand)
        return cand

    def _patch_inv_perm_for_cxx17(self):
        # inv_perm_support_test.cpp uses std::random_shuffle, removed in
        # C++17. Upstream forces -std=c++11 via CMAKE_CXX_FLAGS so it
        # normally still compiles, but any Conan-injected -std=c++17 (or a
        # newer default) turns the single call into a hard build error and
        # the binary goes missing (preflight 2026-09-14). Rewrite to
        # std::shuffle with an explicit engine; semantics (a random
        # permutation) are unchanged and C++11 still accepts shuffle.
        # NOTE: keep one evolving engine across the size loop (like the
        # original rand() global state) instead of a fresh engine per
        # iteration, so perms for different sizes are independent.
        path = os.path.join(self.source_folder, "test", "inv_perm_support_test.cpp")
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except Exception as exc:
            self.output.warning("inv_perm patch: cannot read %s: %s" % (path, exc))
            return
        if "random_shuffle" not in text:
            return
        # Insert a single engine before the size loop if not present.
        if "inv_perm_rng" not in text:
            anchor = "for (size_t z=0; z < (1ULL<<20); z=(z+1)*2) {"
            if anchor in text:
                text = text.replace(
                    anchor,
                    "std::mt19937_64 inv_perm_rng(13);\n            " + anchor,
                )
        new = text.replace(
            "random_shuffle(iv.begin(), iv.end());",
            "std::shuffle(iv.begin(), iv.end(), inv_perm_rng);",
        )
        if new == text:
            # Fallback for whitespace variants; keep the change minimal.
            new = text.replace("random_shuffle", "shuffle")
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(new)
            self.output.info("inv_perm patch: random_shuffle -> shuffle (C++17-proof)")
        except Exception as exc:
            self.output.warning("inv_perm patch: cannot write %s: %s" % (path, exc))

    def _patch_bits_for_aarch64(self):
        # v2.1.1 bits.hpp only uses __builtin_popcountll/clzll/ctzll under
        # __SSE4_2__; on aarch64 it falls back to table/generic paths for
        # cnt/sel/hi/lo. The vgteam fork notes "proper support for 64-bit
        # ARM" as an explicit fix: clang on aarch64 provides the same
        # builtins, and the generic lo/sel tables are the most likely
        # source of a single TEST failure with a different libc rand()
        # sequence (preflight 2026-09-14: 66/67). Enable the builtin path
        # on __aarch64__ for the 4 guards (cnt/sel/hi/lo); x86 behavior
        # unchanged. No test semantics altered.
        path = os.path.join(self.source_folder, "include", "sdsl", "bits.hpp")
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except Exception as exc:
            self.output.warning("aarch64 bits patch: cannot read %s: %s" % (path, exc))
            return
        if "__aarch64__" in text:
            return
        # cnt has "#ifdef __SSE4_2__" followed by popcount; sel/hi/lo share
        # the same guard spelling. Expand each to include __aarch64__.
        # EXCEPT the top-of-file "#ifdef __SSE4_2__ / #include <xmmintrin.h>"
        # guard: x86-only header must stay x86-only (no xmmintrin.h on ARM).
        count = text.count("#ifdef __SSE4_2__")
        new = text.replace(
            "#ifdef __SSE4_2__",
            "#if defined(__SSE4_2__) || defined(__aarch64__)",
        )
        new = new.replace(
            "#if defined(__SSE4_2__) || defined(__aarch64__)\n#include <xmmintrin.h>",
            "#ifdef __SSE4_2__\n#include <xmmintrin.h>",
        )
        # The lo() fallback tail uses "#else" after the builtin branch;
        # "#if" pairs with it transparently, no further edit needed.
        if new == text or count < 4:
            self.output.warning("aarch64 bits patch: expected >=4 guards, found %s" % count)
            if new == text:
                return
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(new)
            self.output.info("aarch64 bits patch: enabled builtin cnt/sel/hi/lo on __aarch64__ (%s guards)" % count)
        except Exception as exc:
            self.output.warning("aarch64 bits patch: cannot write %s: %s" % (path, exc))

    def _patch_temp_buffer_tmpdir(self):
        # temp_buffer_test is the single failing suite (preflight 2026-09-14:
        # failed_suites ["int_vector_mapper_test"], failed_cases
        # "int_vector_mapper_test.temp_buffer_test"). Its no-arg
        # temp_file_buffer::create() hardcodes tmp_file("/tmp") via mkstemps,
        # but HMBS workers mount /tmp read-only (preflight.sh: "can't create
        # temporary file /tmp/...: Read-only file system"), so creation throws
        # "could not create temporary file" and the TEST fails. All other
        # mapper tests take temp_dir (writable) and pass. Fix: honor the
        # writable TMPDIR chain hmbs injects (TMPDIR/TMP/TEMP guaranteed,
        # HMBS_TMPDIR best-effort), trying each in order and falling back to
        # /tmp. Sequential getenv checks (no null-terminated pointer array):
        # the previous cands[] loop tested cands[i] as its condition, so a
        # single unset var (nullptr) ended the loop before later entries were
        # tried and silently fell back to read-only /tmp. Assertions and
        # delete-on-close semantics unchanged; no test skipped.
        path = os.path.join(self.source_folder, "include", "sdsl", "int_vector_mapper.hpp")
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except Exception as exc:
            self.output.warning("temp_buffer patch: cannot read %s: %s" % (path, exc))
            return
        if "HMBS_TMPDIR_FALLBACK_V2" in text:
            return
        if "HMBS_TMPDIR" in text and 'auto file_name = tmp_file("/tmp");' not in text:
            # v1 cands[] patch already stamped: cut the lambda back to anchor
            v1mark = "auto file_name = [](){ "
            idx = text.find(v1mark)
            if idx != -1:
                endmark = '}();'
                end = text.find(endmark, idx)
                if end != -1:
                    text = text[:idx] + 'auto file_name = tmp_file("/tmp");' + text[end + len(endmark):]
        old = 'auto file_name = tmp_file("/tmp");'
        if old not in text:
            self.output.warning("temp_buffer patch: anchor not found")
            return
        new = ('auto file_name = [](){ const char* _d = nullptr; '
               '_d = std::getenv("TMPDIR"); if (_d && *_d) { try { return tmp_file(_d); } catch (...) {} } '
               '_d = std::getenv("TMP"); if (_d && *_d) { try { return tmp_file(_d); } catch (...) {} } '
               '_d = std::getenv("TEMP"); if (_d && *_d) { try { return tmp_file(_d); } catch (...) {} } '
               '_d = std::getenv("HMBS_TMPDIR"); if (_d && *_d) { try { return tmp_file(_d); } catch (...) {} } '
               '/*HMBS_TMPDIR_FALLBACK_V2*/ return tmp_file("/tmp"); }();')
        text = text.replace(old, new)
        if "#include <cstdlib>" not in text:
            text = text.replace("#include <cstdio>", "#include <cstdio>\n#include <cstdlib>")
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
            self.output.info("temp_buffer patch: honor HMBS_TMPDIR/TMPDIR for mkstemps")
        except Exception as exc:
            self.output.warning("temp_buffer patch: cannot write %s: %s" % (path, exc))

    def _sdk_llvm_lib_dir(self):
        """Derive OHOS SDK llvm/lib holding libxml2.so.16 (julius precedent).

        clang -print-resource-dir gives <sdk>/llvm/lib/clang/<ver>;
        dirname twice is <sdk>/llvm/lib. Only return when the file
        really exists there, else None (graceful downgrade, no hard path).
        """
        try:
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            )
        except Exception:
            compilers = {}
        cc = (compilers.get("c") if isinstance(compilers, dict) else None) or os.environ.get("CC") or "/data/service/hnp/bin/clang"
        try:
            out = subprocess.check_output(
                [cc, "-print-resource-dir"], stderr=subprocess.DEVNULL, text=True
            ).strip()
        except Exception:
            return None
        libdir = os.path.dirname(os.path.dirname(out))
        if libdir and os.path.isfile(os.path.join(libdir, "libxml2.so.16")):
            return libdir
        return None

    def build(self):
        apply_conandata_patches(self)
        self._ensure_writable_tmpdir()
        self._patch_toolchain_for_broken_compiler()
        sdk_lib = self._sdk_llvm_lib_dir()
        if sdk_lib:
            old = os.environ.get("LD_LIBRARY_PATH", "")
            if sdk_lib not in old.split(os.pathsep):
                os.environ["LD_LIBRARY_PATH"] = sdk_lib + ((":" + old) if old else "")
            self.output.info("Injected SDK llvm/lib into LD_LIBRARY_PATH: %s" % sdk_lib)
        self._log_compiler_sanity()
        cmake = CMake(self)
        try:
            cli = self._compiler_cli_args()
            if cli:
                cmake.configure(cli_args=cli)
            else:
                cmake.configure()
        except Exception:
            self._dump_cmake_probe_logs()
            raise
        cmake.build()
        self._run_upstream_tests()

    def _compiler_cli_args(self):
        args = []
        try:
            broken = getattr(self, "_hmbs_broken_map", {}) or {}
            for bad, good in broken.items():
                if "++" in good:
                    args.append("-DCMAKE_CXX_COMPILER=%s" % good)
                else:
                    args.append("-DCMAKE_C_COMPILER=%s" % good)
            # de-dup, C first
            seen = set()
            out = []
            for a in sorted(args):
                if a not in seen:
                    seen.add(a)
                    out.append(a)
            if out:
                self.output.info("cmake cli compiler override: %s" % " ".join(out))
            return out
        except Exception:
            return []

    def _log_compiler_sanity(self):
        try:
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            )
        except Exception:
            compilers = {}
        cc = (compilers.get("c") if isinstance(compilers, dict) else None) or "/data/service/hnp/bin/clang"
        cxx = (compilers.get("cpp") if isinstance(compilers, dict) else None) or "/data/service/hnp/bin/clang++"
        self.output.info("compiler sanity: TMPDIR=%s" % os.environ.get("TMPDIR"))
        for tool in (cc, cxx, "cmake"):
            try:
                proc = subprocess.run(
                    [tool, "--version"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, timeout=60, check=False,
                )
                first = (proc.stdout or "").splitlines()[:3]
                self.output.info("%s --version rc=%s: %s" % (tool, proc.returncode, " | ".join(first)))
            except Exception as exc:
                self.output.warning("%s --version failed: %s" % (tool, exc))
        for tool in (cc, cxx):
            try:
                self.output.info("exists %s: %s" % (tool, os.path.isfile(tool)))
            except Exception:
                pass

    def _dump_cmake_probe_logs(self):
        # Surface the real compiler error hidden behind the summary line.
        for root, _dirs, files in os.walk(self.build_folder):
            for name in ("CMakeError.log", "CMakeOutput.log"):
                if name in files:
                    path = os.path.join(root, name)
                    try:
                        with open(path, errors="replace") as fh:
                            lines = fh.read().splitlines()
                        tail = "\n".join(lines[-40:])
                        self.output.info("===== %s tail =====\n%s" % (path, tail))
                    except Exception as exc:
                        self.output.warning("cannot read %s: %s" % (path, exc))

    # 10 offline gtest binaries (no .config / no download.config corpora).
    # The other 14 suites need Pizza&Chili downloads (faust/zarathustra/moby)
    # and up to 60 min; they are audited in notes.md, not run here.
    _OFFLINE_TESTS = [
        "bits_test",
        "coder_test",
        "int_vector_buffer_test",
        "int_vector_mapper_test",
        "int_vector_test",
        "inv_perm_support_test",
        "nn_dict_dynamic_test",
        "sd_vector_test",
        "sorted_int_stack_test",
        "sorted_stack_support_test",
    ]

    # Tests whose main() requires a tmp_dir argv[1] (Usage: <exe> tmp_dir).
    # bits/coder/sd_vector take no argument; the other 7 exit(1) with
    # "Usage: ... tmp_dir" when invoked bare (preflight 2026-09-14).
    _TESTS_NEED_TMPDIR = frozenset([
        "int_vector_buffer_test",
        "int_vector_mapper_test",
        "int_vector_test",
        "inv_perm_support_test",
        "nn_dict_dynamic_test",
        "sorted_int_stack_test",
        "sorted_stack_support_test",
    ])

    def _run_upstream_tests(self):
        """Build and run the offline gtest subset, emit HMBS_UPSTREAM_TEST_RESULT."""
        cmake = CMake(self)
        for target in self._OFFLINE_TESTS:
            try:
                cmake.build(target=target)
            except Exception as exc:
                self.output.warning("upstream test build failed (%s): %s" % (target, exc))

        # Writable scratch dir for file-backed suites. Must avoid
        # read-only /tmp on HMBS workers; reuse the probed TMPDIR.
        try:
            base = self._writable_tmpdir()
        except Exception:
            base = None
        if not base:
            base = os.environ.get("TMPDIR") or os.environ.get("HMBS_TMPDIR")
        if not base:
            try:
                base = os.path.join(self.build_folder, ".tmp")
            except Exception:
                base = None
        upstream_tmp = base
        try:
            if upstream_tmp:
                upstream_tmp = os.path.join(base, "upstream_tmp")
                os.makedirs(upstream_tmp, exist_ok=True)
                # Stale files from an aborted run reuse fixed leaf names
                # (e.g. temp_dir+"/int_vector_buffer"); a leftover file
                # with a wrong header can turn the next run's first
                # sub-test into a false failure. Remove regular files at
                # the top level only (never recurse into per-test dirs
                # blindly); per-test dirs are cleaned in _tmp_for below.
                # This does not alter test semantics, only isolation.
                for _entry in os.listdir(upstream_tmp):
                    _p = os.path.join(upstream_tmp, _entry)
                    try:
                        if os.path.isfile(_p) and not os.path.islink(_p):
                            os.unlink(_p)
                    except Exception:
                        pass
        except Exception as exc:
            self.output.warning("cannot create upstream_tmp %s: %s" % (upstream_tmp, exc))
            upstream_tmp = None
        # Per-test subdirs: suites reuse fixed leaf names (e.g. temp_dir +
        # "/int_vector"), so a shared dir risks stale-file collisions when a
        # previous binary aborts. Isolation is cheap and keeps failures real.
        def _tmp_for(name):
            if not upstream_tmp:
                return None
            d = os.path.join(upstream_tmp, name)
            try:
                os.makedirs(d, exist_ok=True)
                for _entry in os.listdir(d):
                    _p = os.path.join(d, _entry)
                    try:
                        if os.path.isfile(_p) and not os.path.islink(_p):
                            os.unlink(_p)
                    except Exception:
                        pass
                return d
            except Exception as exc:
                self.output.warning("cannot create tmp for %s: %s" % (name, exc))
                return upstream_tmp

        discovered = executed = passed = failed = skipped = 0
        commands = []
        per_suite = []
        for name in self._OFFLINE_TESTS:
            exe = self._find_test_binary(name)
            if exe is None:
                self.output.warning("upstream test binary missing: %s" % name)
                try:
                    probe_dir = os.path.join(self.build_folder, "test")
                    self.output.info("test dir listing: %s" % sorted(os.listdir(probe_dir))[:40])
                except Exception as exc:
                    self.output.warning("cannot list test dir: %s" % exc)
                # One explicit rebuild attempt so the compiler error (if any)
                # surfaces in the log instead of a bare "missing" warning.
                try:
                    cmake.build(target=name)
                    exe = self._find_test_binary(name)
                    self.output.info("rebuild %s -> %s" % (name, exe))
                except Exception as exc:
                    self.output.warning("rebuild %s failed: %s" % (name, exc))
                if exe is None:
                    failed += 1
                    per_suite.append((name, 0, 0, 1, "missing-binary"))
                    continue
            tdir = _tmp_for(name)
            commands.append(exe + (" " + tdir if tdir and name in self._TESTS_NEED_TMPDIR else ""))
            # Propagate HMBS TMPDIR so file-backed tests avoid read-only /tmp.
            run_env = dict(os.environ)
            tmpdir = run_env.get("TMPDIR") or run_env.get("TMP") or run_env.get("TEMP")
            if tmpdir:
                run_env["TMPDIR"] = tmpdir
                run_env["TMP"] = tmpdir
                run_env["TEMP"] = tmpdir
            argv = [exe] + ([tdir] if (tdir and name in self._TESTS_NEED_TMPDIR) else [])
            try:
                result = subprocess.run(
                    argv,
                    cwd=self.build_folder,
                    capture_output=True,
                    text=True,
                    timeout=1200,
                    env=run_env,
                )
            except subprocess.TimeoutExpired:
                self.output.error("%s timed out" % name)
                failed += 1
                per_suite.append((name, 0, 0, 1, "timeout"))
                continue
            out = (result.stdout or "") + (result.stderr or "")
            tail = "\n".join(out.splitlines()[-15:])
            self.output.info("%s exit=%s\n%s" % (name, result.returncode, tail))
            d, p, f, s = self._parse_gtest(out)
            # Guard against silent skips: binary must report at least one test.
            if d == 0:
                self.output.warning("%s reported 0 tests, counting as failure" % name)
                failed += 1
                per_suite.append((name, 0, 0, 1, "zero-tests exit=%s" % result.returncode))
                continue
            discovered += d
            executed += d
            passed += p
            failed += f
            skipped += s
            if result.returncode != 0 and f == 0:
                failed += 1
                per_suite.append((name, d, p, 1, "nonzero-exit"))
            else:
                per_suite.append((name, d, p, f, "rc=%s" % result.returncode))
            if f > 0 or (result.returncode != 0 and d > 0):
                # Keep the culprit visible at the tail of the log (HMBS
                # summaries truncate the middle): list every FAILED case.
                fails = [ln.strip() for ln in out.splitlines() if "FAILED" in ln][:20]
                self.output.warning("%s FAILED details: %s" % (name, " | ".join(fails)[:2000]))
            # Stash raw output for tail-visible diagnosis below (no recount).
            try:
                per_suite[-1] = per_suite[-1] + (out,)
            except Exception:
                pass

        # End-of-run table survives HMBS middle-truncation (marker is at the
        # very end, per-suite tails are not). Next round can pinpoint the one
        # failing suite without guessing.
        for entry in per_suite:
            try:
                name, d, p, f, note = entry[:5]
            except Exception:
                continue
            self.output.info("UPSTREAM_SUITE %s discovered=%s passed=%s failed=%s %s" % (name, d, p, f, note))
        # Tail-visible identity + diagnostic retry (new strategy vs prior
        # round's library-only bits guess, which left 66/67 unchanged):
        # HMBS summaries keep the very end (exception message) but drop the
        # middle, so failed suite/case names must live INSIDE the marker and
        # the raised exception. A single retry of failed suites with a fresh
        # tmp dir distinguishes flaky (stale-file/timing) from deterministic
        # failures; retry output is logged only and never alters pass counts.
        fail_cases = []
        try:
            for entry in per_suite:
                try:
                    name, d, p, f, note = entry[:5]
                    out = entry[5] if len(entry) > 5 else ""
                except Exception:
                    continue
                if f > 0:
                    for ln in (out or "").splitlines():
                        s = ln.strip()
                        # Case lines look like "[  FAILED  ] Suite.Test ...";
                        # skip summaries like "[  FAILED  ] 1 test, listed below".
                        if "FAILED" not in s:
                            continue
                        if re.search(r"\d+\s+tests?", s):
                            continue
                        if not re.search(r"\.\w+", s):
                            continue
                        fail_cases.append("%s::%s" % (name, s[:220]))
                        if len(fail_cases) >= 10:
                            break
                    if len(fail_cases) >= 10:
                        break
        except Exception:
            pass
        try:
            _bad = [n for (n, _d, _p, _f, _nt) in [e[:5] for e in per_suite] if _f > 0]
        except Exception:
            _bad = []
        # Diagnostic-only retry of failed suites (does not change counts).
        try:
            for name in list(_bad):
                exe = self._find_test_binary(name)
                if not exe:
                    continue
                rdir = _tmp_for(name + "_retry")
                rargv = [exe] + ([rdir] if (rdir and name in self._TESTS_NEED_TMPDIR) else [])
                try:
                    run_env2 = dict(os.environ)
                    tmpdir2 = run_env2.get("TMPDIR") or run_env2.get("TMP") or run_env2.get("TEMP")
                    if tmpdir2:
                        run_env2["TMPDIR"] = tmpdir2
                        run_env2["TMP"] = tmpdir2
                        run_env2["TEMP"] = tmpdir2
                    rres = subprocess.run(
                        rargv, cwd=self.build_folder, capture_output=True,
                        text=True, timeout=1200, env=run_env2,
                    )
                except subprocess.TimeoutExpired:
                    self.output.warning("UPSTREAM_RETRY %s timed out" % name)
                    continue
                except Exception as exc:
                    self.output.warning("UPSTREAM_RETRY %s error: %s" % (name, exc))
                    continue
                rout = (rres.stdout or "") + (rres.stderr or "")
                rtail = "\n".join(rout.splitlines()[-8:])
                self.output.warning("UPSTREAM_RETRY %s exit=%s\n%s" % (name, rres.returncode, rtail))
        except Exception as exc:
            self.output.warning("UPSTREAM_RETRY harness error: %s" % exc)
        try:
            if _bad:
                self.output.warning("HMBS_UPSTREAM_FAIL_DETAIL=" + json.dumps(
                    {"failed_suites": _bad, "failed_cases": fail_cases[:10]}, ensure_ascii=False))
        except Exception:
            pass

        if failed == 0 and discovered > 0:
            status = "passed"
        elif failed > 0:
            status = "failed"
        else:
            status = "no_tests"
        marker = {
            "status": status,
            "framework": "gtest",
            "command": " ".join(commands),
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
        }
        marker_line = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False)
        self.output.info(marker_line)
        try:
            print(marker_line, flush=True)
        except Exception:
            pass
        # Persist for cache-hit re-emit (abuild-sudo/ayatana-ido precedent):
        # when Conan reuses a cached package, build() is skipped and the
        # marker above never prints. test_package re-emits this JSON every
        # run so the evidence gate still sees real in-build numbers.
        try:
            _rf = os.path.join(self.build_folder, "hmbs_upstream_result.json")
            with open(_rf, "w", encoding="utf-8") as _fh:
                _fh.write(json.dumps(marker, ensure_ascii=False, indent=1))
        except Exception as _exc:
            self.output.warning("cannot persist upstream result: %s" % _exc)
        if status != "passed":
            raise ConanException("upstream offline gtest subset failed: %s" % json.dumps(marker))

    def _find_test_binary(self, name):
        candidates = [
            os.path.join(self.build_folder, "test", name),
            os.path.join(self.build_folder, name),
        ]
        for path in candidates:
            if os.path.isfile(path):
                return path
        # cmake_layout nests the real build dir (e.g. build/Release/test/);
        # fall back to a recursive search so offline suites are found.
        for root, _dirs, files in os.walk(self.build_folder):
            if name in files:
                return os.path.join(root, name)
        return None

    @staticmethod
    def _parse_gtest(out):
        running = 0
        m = re.search(r"Running\s+(\d+)\s+tests?", out)
        if m:
            running = int(m.group(1))
        passed = 0
        m = re.search(r"\[\s*PASSED\s*\]\s+(\d+)\s+tests?", out)
        if m:
            passed = int(m.group(1))
        failed = 0
        m = re.search(r"\[\s*FAILED\s*\]\s+(\d+)\s+tests?", out)
        if m:
            failed = int(m.group(1))
        skipped = 0
        m = re.search(r"\[\s*SKIPPED\s*\]\s+(\d+)\s+tests?", out)
        if m:
            skipped = int(m.group(1))
        discovered = running if running > 0 else passed + failed + skipped
        return discovered, passed, failed, skipped

    def _tmp_compat_shim(self):
        return None

    def package(self):
        cmake = CMake(self)
        cmake.install()
        for pattern in ["*.la", "*.dylib"]:
            rm(self, pattern,
               folder=os.path.join(self.package_folder, "lib"))
        copy(self, "COPYING",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        try:
            _rf = os.path.join(self.build_folder, "hmbs_upstream_result.json")
            if os.path.isfile(_rf):
                shutil.copy2(_rf, os.path.join(self.package_folder, "hmbs_upstream_result.json"))
        except Exception as _exc:
            self.output.warning("cannot package upstream result: %s" % _exc)

    def package_info(self):
        self.cpp_info.libs = ["sdsl", "divsufsort", "divsufsort64"]
        self.cpp_info.set_property("cmake_file_name", "libsdsl")
        self.cpp_info.set_property("cmake_target_name", "libsdsl::libsdsl")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m"]
