#!/usr/bin/env python3
"""Conan recipe — libmurmurhash 1.6 (vendored CMake build, no autotools)

Upstream v1.6 tag archive ships only configure.ac + Makefile.am (no
generated configure). Three bootstrapping attempts failed on the HMBS
preflight image:

1. `autoreconf --install --force` via tool_requires automake/libtool:
   `/bin/sh: autoreconf: inaccessible or not found` (autoreconf lives in
   the autoconf package, not on PATH; pulling autoconf would drag in
   m4/perl which break on readonly /tmp and HMDFS getcwd quirks).
2. Direct `cc` compile with the compiler path taken from
   `tools.build:compiler_executables`: the conf value
   (`/data/service/hnp/bin/clang`) is not executable on the preflight
   host, so the first compile failed with exit 127.
3. Vendored CMake + plain CMakeToolchain: CMake aborts because the
   toolchain-inherited `CMAKE_C_COMPILER=/data/service/hnp/bin/clang`
   is broken in the preflight sandbox.

The library itself is two pure-C translation units (PMurHash.c +
murmurhash.c, no config.h dependency, no external libs) and the upstream
test harness is two tiny mmap-based binaries (test/mmh.c, test/mmh_old.c)
diffed against test/almostempty.hash (== upstream `make check`). This
revision keeps the minimal vendored CMakeLists.txt (precedent
murmurhash3/0.0.1) but generate() probes for a working compiler on PATH
and then patches the generated conan_toolchain.cmake: the previous
revision proved that assigning tc.cache_variables["CMAKE_C_COMPILER"]
is ineffective -- the OHOS CMakeToolchain re-resolves the compiler from
profile conf (tools.build:compiler_executables) during generate() and
overwrites the user value, so CMake still received the broken
/data/service/hnp/bin/clang even though the probe had found a working
clang. This revision therefore keeps CMakeToolchain for flags/sysroot
but rewrites the broken compiler path inside the emitted toolchain file
(a post-generation file patch, not a cache-variable override).
HMBS guarantees cmake/make/ninja/python3 on PATH.
"""

import json
import os
import shutil
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, export_conandata_patches, get, save


_CMAKE_LISTS = """cmake_minimum_required(VERSION 3.15)
project(libmurmurhash C)

option(BUILD_SHARED_LIBS "Build shared library" OFF)
set(CMAKE_C_STANDARD 11)

add_library(murmurhash PMurHash.c murmurhash.c)
target_include_directories(murmurhash PUBLIC ${CMAKE_CURRENT_SOURCE_DIR})
set_target_properties(murmurhash PROPERTIES OUTPUT_NAME murmurhash)

add_executable(mmh test/mmh.c)
target_link_libraries(mmh PRIVATE murmurhash)
target_include_directories(mmh PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

add_executable(mmh_old test/mmh_old.c)
target_link_libraries(mmh_old PRIVATE murmurhash)
target_include_directories(mmh_old PRIVATE ${CMAKE_CURRENT_SOURCE_DIR})

install(TARGETS murmurhash ARCHIVE DESTINATION lib LIBRARY DESTINATION lib)
# NOTE (R38/L0k): library-only install on purpose -- no runtime bindir
# so the package is not misdetected as a CLI tool requiring commands.json.
# mmh/mmh_old are upstream-check helpers built in build() but never installed.
install(FILES murmurhash.h DESTINATION include)
"""


def _probe_compiler(conanfile, kind):
    """Return the first compiler candidate that really executes (compiles
    a trivial TU). PATH lookup comes first on purpose: profile conf
    (tools.build:compiler_executables) is known-stale in the preflight
    sandbox (/data/service/hnp/bin/clang not executable there), so it is
    only a last-resort fallback. Raises if none works (then the failure
    is an environment fault, not a recipe bug)."""
    try:
        conf = conanfile.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
    except Exception:
        conf = {}
    home = os.path.expanduser("~")
    if kind == "c":
        # NOTE: PATH-first ordering is deliberate (differs from the
        # previous conf-first probe which still failed downstream).
        raw = [shutil.which("clang"), shutil.which("cc"),
               shutil.which("aarch64-linux-ohos-clang"),
               os.path.join(home, "usr", "local", "bin", "clang"),
               "/storage/Users/currentUser/usr/local/bin/clang",
               os.environ.get("CC"),
               conf.get("c"),
               "/data/service/hnp/bin/clang",
               shutil.which("gcc"), "clang", "cc"]
        src_name, lang_flag = "probe.c", None
        code = "int probe_main(void){return 0;}\n"
    else:
        raw = [shutil.which("clang++"), shutil.which("c++"),
               shutil.which("aarch64-linux-ohos-clang++"),
               os.path.join(home, "usr", "local", "bin", "clang++"),
               "/storage/Users/currentUser/usr/local/bin/clang++",
               os.environ.get("CXX"),
               conf.get("cpp"),
               "/data/service/hnp/bin/clang++",
               shutil.which("g++"), "clang++", "c++"]
        src_name, lang_flag = "probe.cpp", None
        code = "int probe_main(){return 0;}\n"
    seen = set()
    cands = [c for c in raw if c and not (c in seen or seen.add(c))]
    tmp = (os.environ.get("TMPDIR") or os.environ.get("TMP")
           or os.environ.get("TEMP") or tempfile.gettempdir())
    try:
        os.makedirs(tmp, exist_ok=True)
    except Exception:
        pass
    src = os.path.join(tmp, f"hmbs_{kind}_{os.getpid()}_{src_name}")
    try:
        with open(src, "w", encoding="utf-8") as f:
            f.write(code)
    except Exception:
        src = None
    try:
        for cand in cands:
            obj = src + ".o" if src else os.path.join(tmp, "hmbs_probe.o")
            cmd = [cand]
            if lang_flag:
                cmd.append(lang_flag)
            if src:
                cmd += [src, "-c", "-o", obj]
            else:
                continue
            try:
                proc = subprocess.run(cmd, capture_output=True, timeout=120)
            except Exception as e:
                conanfile.output.info(f"compiler probe {cand!r}: exec failed ({e})")
                continue
            if proc.returncode == 0 and os.path.isfile(obj):
                try:
                    os.remove(obj)
                except Exception:
                    pass
                conanfile.output.info(f"compiler probe {cand!r}: works")
                return cand
            conanfile.output.info(
                f"compiler probe {cand!r}: rc={proc.returncode} "
                f"err={(proc.stderr or b'')[:200]!r}")
        raise ConanInvalidConfiguration(
            f"no working {'C' if kind == 'c' else 'C++'} compiler found "
            f"(tried {cands}); preflight toolchain unavailable")
    finally:
        for p in (src, (src + ".o") if src else None):
            try:
                if p and os.path.isfile(p):
                    os.remove(p)
            except Exception:
                pass


def _patch_generated_toolchain(conanfile, good_c, good_cxx):
    """Rewrite stale compiler paths inside the emitted conan_toolchain.cmake.

    Previous revision proved tc.cache_variables["CMAKE_C_COMPILER"] is
    overwritten by the OHOS toolchain logic during generate(), so the
    only reliable hook is a post-generation file patch. Only exact
    stale path substrings are replaced (never flags/sysroot/target
    settings); if the toolchain already points at a working compiler,
    the file is left untouched.
    """
    try:
        conf = conanfile.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
    except Exception:
        conf = {}
    stale = [p for p in (conf.get("c"), conf.get("cpp"),
                         "/data/service/hnp/bin/clang",
                         "/data/service/hnp/bin/clang++") if p]
    # Drop stale entries that are actually executable (not stale at all).
    stale = [p for p in dict.fromkeys(stale)
             if not (os.path.isfile(p) and os.access(p, os.X_OK))]
    if not stale:
        return
    roots = []
    try:
        gf = getattr(conanfile, "generators_folder", None)
        if gf:
            roots.append(gf)
    except Exception:
        pass
    try:
        if getattr(conanfile, "build_folder", None):
            roots.append(conanfile.build_folder)
    except Exception:
        pass
    patched = 0
    for root in roots:
        if not root or not os.path.isdir(root):
            continue
        for dirpath, _dirnames, filenames in os.walk(root):
            if "conan_toolchain.cmake" not in filenames:
                continue
            tc_path = os.path.join(dirpath, "conan_toolchain.cmake")
            try:
                with open(tc_path, "r", encoding="utf-8", errors="strict") as f:
                    text = f.read()
            except Exception as e:
                conanfile.output.warning(f"toolchain patch: cannot read {tc_path}: {e}")
                continue
            orig = text
            for bad in stale:
                if bad in text:
                    good = good_c if "++" not in os.path.basename(bad) else good_cxx
                    # clang++ stale path maps to C++ compiler, plain clang to C.
                    if bad.endswith("++"):
                        good = good_cxx
                    else:
                        good = good_c
                    text = text.replace(bad, good)
            if text != orig:
                try:
                    with open(tc_path, "w", encoding="utf-8") as f:
                        f.write(text)
                    patched += 1
                    conanfile.output.info(
                        f"toolchain patch: replaced {stale} with "
                        f"C={good_c!r} CXX={good_cxx!r} in {tc_path}")
                except Exception as e:
                    conanfile.output.warning(f"toolchain patch: cannot write {tc_path}: {e}")
    if patched == 0:
        conanfile.output.info(f"toolchain patch: no stale entry {stale} found in toolchain files")


class LibmurmurhashConan(ConanFile):
    name = "libmurmurhash"
    version = "1.6"
    description = "Portable MurmurHash implementation, non-cryptographic hash library (MurmurHash3 x86/x64 variants)"
    license = "LicenseRef-public-domain"
    homepage = "https://github.com/kloetzl/libmurmurhash"
    url = "https://github.com/kloetzl/libmurmurhash"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"

    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }

    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.get_safe("shared"):
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libmurmurhash is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # NOTE: do NOT set tc.cache_variables["CMAKE_C_COMPILER"]: proven
        # ineffective (toolchain re-resolves from profile conf and drops
        # the user value; CMake still got /data/service/hnp/bin/clang).
        # Instead generate first, then patch the emitted toolchain file.
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = self.options.shared
        tc.generate()
        good_c = _probe_compiler(self, "c")
        good_cxx = _probe_compiler(self, "cpp")
        _patch_generated_toolchain(self, good_c, good_cxx)
        # Belt and braces for any direct compiler spawn outside CMake.
        try:
            os.environ["CC"] = good_c
            os.environ["CXX"] = good_cxx
        except Exception:
            pass

    def _ensure_tmpdir(self):
        # HMBS injects a writable TMPDIR (readonly /tmp on device).
        tmp = os.environ.get("TMPDIR") or os.environ.get("TMP") or os.environ.get("TEMP")
        fb = os.environ.get("HMBS_AUTOCONF_MKTEMP_FALLBACK")
        if fb and fb not in ("0", "1") and os.path.isdir(fb):
            tmp = fb
        if not tmp or not os.path.isdir(tmp):
            tmp = os.path.join(self.build_folder, "tmp")
        try:
            os.makedirs(tmp, exist_ok=True)
        except Exception:
            pass
        os.environ["TMPDIR"] = tmp
        os.environ["TMP"] = tmp
        os.environ["TEMP"] = tmp
        return tmp

    def _find_built_prog(self, name):
        cands = [
            os.path.join(self.build_folder, name),
            os.path.join(self.build_folder, "build-release", name),
        ]
        for root, _dirs, files in os.walk(self.build_folder):
            if name in files:
                cands.append(os.path.join(root, name))
        for cand in cands:
            if os.path.isfile(cand):
                return cand
        return None

    def _run_upstream_checks(self):
        """Run mmh/mmh_old on test/almostempty and byte-compare against
        test/almostempty.hash (== upstream `make check`). Shell-free:
        binaries run via subprocess, outputs compared in Python, temp files
        live in build_folder (never /tmp)."""
        src = self.source_folder
        out = self.build_folder
        for f in ("PMurHash.c", "murmurhash.c", "murmurhash.h",
                  os.path.join("test", "mmh.c"), os.path.join("test", "mmh_old.c"),
                  os.path.join("test", "almostempty"), os.path.join("test", "almostempty.hash")):
            if not os.path.isfile(os.path.join(src, f)):
                raise RuntimeError(f"expected upstream file missing: {f}")
        for f in (os.path.join("test", "almostempty"), os.path.join("test", "almostempty.hash")):
            sz = os.path.getsize(os.path.join(src, f))
            if sz == 0:
                raise RuntimeError(f"upstream fixture empty: {f}")
            self.output.info(f"upstream fixture {f}: {sz} bytes")
        mmh = self._find_built_prog("mmh")
        mmh_old = self._find_built_prog("mmh_old")
        if not mmh or not mmh_old:
            raise RuntimeError(f"test binaries missing: mmh={mmh} mmh_old={mmh_old}")
        fixture = os.path.join(src, "test", "almostempty")
        with open(os.path.join(src, "test", "almostempty.hash"), "rb") as f:
            expected = f.read()
        if not expected.strip():
            raise RuntimeError("upstream reference hash file is empty")
        passed = 0
        for prog, label in ((mmh, "mmh"), (mmh_old, "mmh_old")):
            proc = subprocess.run([prog, fixture], capture_output=True, timeout=60)
            if proc.returncode != 0:
                raise RuntimeError(f"{label} exited {proc.returncode}: {(proc.stderr or b'')[:500]!r}")
            got = proc.stdout or b""
            self.output.info(f"{label} output: {len(got)} bytes")
            if not got.strip():
                raise RuntimeError(f"{label} produced empty output (fixture decode broken?)")
            if got.strip() != expected.strip():
                raise RuntimeError(f"{label} hash mismatch: got {got[:80]!r} expected {expected[:80]!r}")
            passed += 1
        return {
            "status": "passed",
            "framework": "make-check",
            "command": "./mmh|./mmh_old test/almostempty | diff test/almostempty.hash - (via vendored CMake build)",
            "discovered": 2,
            "executed": 2,
            "passed": passed,
            "failed": 0,
            "skipped": 0,
        }

    def build(self):
        self._ensure_tmpdir()
        save(self, os.path.join(self.source_folder, "CMakeLists.txt"), _CMAKE_LISTS)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if can_run(self):
            res = self._run_upstream_checks()
        else:
            res = {
                "status": "skipped",
                "framework": "make-check",
                "command": "./mmh|./mmh_old test/almostempty | diff test/almostempty.hash - (via vendored CMake build)",
                "discovered": 2,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 2,
                "reason": "cross-build: test binaries not runnable on build host",
            }
        msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(res, ensure_ascii=False)
        print(msg, flush=True)
        self.output.info(msg)
        # Persist for test_package re-emit (build() is skipped on cache hit).
        try:
            save(self, os.path.join(self.build_folder, "upstream_test_result.json"),
                 json.dumps(res, ensure_ascii=False, indent=2))
        except Exception as e:
            self.output.warning(f"failed to persist upstream result: {e}")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "NOLICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        pc = (
            "prefix=/\n"
            "exec_prefix=${prefix}\n"
            "libdir=${exec_prefix}/lib\n"
            "includedir=${prefix}/include\n"
            "\n"
            "Name: libmurmurhash\n"
            "Version: 1.6\n"
            "Description: Portable MurmurHash Implementation\n"
            "Libs: -L${libdir} -lmurmurhash\n"
            "Cflags: -I${includedir}\n"
        )
        save(self, os.path.join(self.package_folder, "lib", "pkgconfig", "libmurmurhash.pc"), pc)
        try:
            res = os.path.join(self.build_folder, "upstream_test_result.json")
            if os.path.isfile(res):
                copy(self, "upstream_test_result.json", src=self.build_folder,
                     dst=os.path.join(self.package_folder, "res"))
        except Exception as e:
            self.output.warning(f"failed to package upstream result: {e}")

    def package_info(self):
        self.cpp_info.libs = ["murmurhash"]

        self.cpp_info.set_property("cmake_file_name", "libmurmurhash")
        self.cpp_info.set_property("cmake_target_name", "libmurmurhash::libmurmurhash")
        self.cpp_info.set_property("pkg_config_name", "libmurmurhash")

        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH",
            os.path.join(self.package_folder, "lib"),
        )
