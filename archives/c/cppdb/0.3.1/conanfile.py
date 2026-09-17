#!/usr/bin/env python3
"""Conan recipe — cppdb 0.3.1 (CMake).

CppDB is a SQL connectivity library (originally part of the CppCMS project).
Only the sqlite3 backend is enabled: it is serverless and runs offline on
HarmonyOS, while the mysql/postgresql/odbc backends need live DB servers.

Layout:
- shared=False (default): sqlite3 backend is baked into libcppdb
  (SQLITE_BACKEND_INTERNAL=ON), no runtime dlopen is needed.
- shared=True: upstream module layout, libcppdb_sqlite3.so is loaded
  at runtime via dlopen (uses @modules_path in tests).

Upstream tests: test_basic / test_backend / test_caching are executed in
build() against sqlite (the offline subset of test/run_test_linux_a.sh).
Numbers are parsed from the real "Tests: N failed: M" output lines.
"""
import json
import os
import re
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, replace_in_file, rm


class CppdbConan(ConanFile):
    name = "cppdb"
    version = "0.3.1"
    description = "SQL connectivity library with a database-independent API (sqlite3 backend)"
    license = ("BSL-1.0", "MIT")
    homepage = "http://cppcms.com/sql/cppdb/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("sql", "database", "sqlite", "cppcms")
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
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

    def requirements(self):
        self.requires("sqlite3/3.49.1")

    def layout(self):
        cmake_layout(self)

    def source(self):
        # SourceForge /download suffix has no file extension, so Conan's
        # get() would fall back to the zip decoder -> BadZipFile. Pass an
        # explicit *.tar.bz2 filename so unzip() selects the tar decoder.
        src = dict(self.conan_data["sources"])
        src.setdefault("filename", "cppdb-0.3.1.tar.bz2")
        get(self, **src, strip_root=True)

    def _abs(self, dep, paths):
        out = []
        for p in paths:
            if not os.path.isabs(p):
                p = os.path.join(dep.package_folder, p)
            out.append(p)
        return out

    def generate(self):
        tc = CMakeToolchain(self)
        # Only the serverless sqlite3 backend can run on HarmonyOS;
        # mysql/postgresql/odbc need live servers, disable them explicitly.
        tc.variables["DISABLE_PQ"] = "ON"
        tc.variables["DISABLE_MYSQL"] = "ON"
        tc.variables["DISABLE_ODBC"] = "ON"
        if self.options.shared:
            # Upstream default: sqlite backend as a loadable module.
            tc.variables["SQLITE_BACKEND_INTERNAL"] = "OFF"
        else:
            # Static: bake the sqlite backend into libcppdb itself.
            tc.variables["SQLITE_BACKEND_INTERNAL"] = "ON"
        # Upstream CMakeLists uses raw find_library/find_path (no
        # find_package support); override its cache variables with the
        # Conan-provided sqlite3 paths (a pre-set find_* variable is
        # kept as-is, so no source patch is needed for this).
        sqlite = self.dependencies["sqlite3"]
        inc = self._abs(sqlite, sqlite.cpp_info.includedirs)[0]
        libdir = self._abs(sqlite, sqlite.cpp_info.libdirs)[0]
        tc.variables["SQLITE3_PATH"] = inc.replace("\\", "/")
        tc.variables["SQLITE3_LIB"] = os.path.join(
            libdir, "libsqlite3.a").replace("\\", "/")
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = (
            "ON" if self.options.get_safe("fPIC", True) else "OFF")
        tc.generate()

    def _find_upstream_bins(self):
        bins = {}
        for want in ("test_basic", "test_backend", "test_caching"):
            for root, _, files in os.walk(self.build_folder):
                if want in files:
                    bins[want] = os.path.join(root, want)
                    break
        missing = [w for w in ("test_basic", "test_backend", "test_caching") if w not in bins]
        if missing:
            raise ConanException("upstream test binaries not built: %s" % ",".join(missing))
        return bins

    def _run_one(self, exe, connstr, env):
        proc = subprocess.run([exe, connstr], capture_output=True, text=True,
                              timeout=300, env=env, cwd=self.build_folder)
        out = (proc.stdout or "") + (proc.stderr or "")
        self.output.info("upstream run: %s\n%s" % (connstr, out))
        return proc.returncode, out

    def _run_upstream_sqlite_suite(self):
        # Offline subset of upstream test/run_test_linux_a.sh: the sqlite3
        # connection string in all 4 option variants, plus test_caching
        # (dummy driver, no database needed at all).
        bins = self._find_upstream_bins()
        exe_dir = os.path.dirname(bins["test_basic"])
        dbdir = os.path.join(self.build_folder, "upstream_db")
        os.makedirs(dbdir, exist_ok=True)
        env = dict(os.environ)
        # HarmonyOS preflight mounts /tmp read-only; sqlite spills temp
        # tables there unless redirected. Only the temp-file root is
        # changed, the upstream binaries and assertions are untouched.
        tmpdir = (env.get("TMPDIR") or env.get("TMP") or env.get("TEMP") or "").strip()
        if not tmpdir or not os.path.isdir(tmpdir):
            tmpdir = dbdir
        env["TMPDIR"] = tmpdir
        env["TMP"] = tmpdir
        env["TEMP"] = tmpdir
        env["SQLITE_TMPDIR"] = tmpdir
        env["LD_LIBRARY_PATH"] = exe_dir + (":" + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH") else "")
        variants = ["", ";@use_prepared=off", ";@pool_size=5",
                    ";@use_prepared=off;@pool_size=5"]
        discovered = 0
        passed = 0
        # test_basic uses a throw-on-failure TEST macro and prints only
        # "Ok": exit 0 proves all 37 static TEST sites passed (6 of them
        # sit in a 2-iteration fetch loop, so 43 dynamic executions).
        # All test_basic variants share ONE db file, exactly like upstream
        # run_test_linux_a.sh reuses test.db for every suffix. test_basic
        # ends with close()+open(same cs) and asserts
        # once_called()==have_pool for pooled variants; the pool reuses the
        # connection only if it was recycled, and any earlier statement
        # error (e.g. DROP TABLE on a fresh file) marks it non-recyclable
        # via throw_guard (frontend.cpp) + dispose() (backend.cpp), so a
        # pooled reopen gets a fresh connection and fails at line 185.
        # Variant 0 leaves the table behind, so pooled variants' DROP
        # succeeds and the pool path is really exercised. Per-variant
        # files would fail pooled variants spuriously - not an OHOS bug.
        basic_db = os.path.join(dbdir, "basic.db")
        if os.path.exists(basic_db):
            os.remove(basic_db)
        for i, suffix in enumerate(variants):
            conn = "sqlite3:db=%s;@modules_path=%s%s" % (basic_db, exe_dir, suffix)
            rc, out = self._run_one(bins["test_basic"], conn, env)
            if rc != 0 or "Ok" not in out:
                raise ConanException("test_basic failed (variant %d): rc=%d" % (i, rc))
            discovered += 37
            passed += 37
        # test_backend / test_caching print "Tests: N failed: M".
        for i, suffix in enumerate(variants):
            db = os.path.join(dbdir, "backend_%d.db" % i)
            if os.path.exists(db):
                os.remove(db)
            conn = "sqlite3:db=%s;@modules_path=%s%s" % (db, exe_dir, suffix)
            rc, out = self._run_one(bins["test_backend"], conn, env)
            m = re.search(r"Tests:\s*(\d+)\s*failed:\s*(\d+)", out)
            if rc != 0 or not m or "Ok" not in out:
                raise ConanException("test_backend failed (variant %d): rc=%d" % (i, rc))
            total, failed = int(m.group(1)), int(m.group(2))
            if failed != 0 or total <= 0:
                raise ConanException("test_backend reported failures (variant %d): %s" % (i, out[-500:]))
            discovered += total
            passed += total - failed
        rc, out = self._run_one(bins["test_caching"], "", env)
        m = re.search(r"Tests:\s*(\d+)\s*failed:\s*(\d+)", out)
        if rc != 0 or not m or "Ok" not in out:
            raise ConanException("test_caching failed: rc=%d" % rc)
        total, failed = int(m.group(1)), int(m.group(2))
        if failed != 0 or total <= 0:
            raise ConanException("test_caching reported failures: %s" % out[-500:])
        discovered += total
        passed += total - failed
        marker = {
            "status": "passed",
            "framework": "custom",
            "command": "test_basic/test_backend (sqlite3 x4 variants) + test_caching",
            "discovered": discovered,
            "executed": discovered,
            "passed": passed,
            "failed": 0,
            "skipped": 0,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker))

    def build(self):
        apply_conandata_patches(self)
        # OHOS musl has no standalone libpthread (pthread lives in libc),
        # so find_library(PTHREAD_LIB pthread) returns NOTFOUND and the
        # unconditional target_link_libraries(cppdb ${PTHREAD_LIB}) fails
        # configure. Done here in Python (not a patch file) so it cannot
        # drift when 0001 shifts line numbers in the same CMakeLists.txt.
        cmakelists = os.path.join(self.source_folder, "CMakeLists.txt")
        with open(cmakelists, encoding="utf-8") as f:
            content = f.read()
        if "\tif(PTHREAD_LIB)" not in content:
            replace_in_file(
                self, cmakelists,
                "\ttarget_link_libraries(cppdb ${PTHREAD_LIB})",
                "\tif(PTHREAD_LIB)\n"
                "\t\ttarget_link_libraries(cppdb ${PTHREAD_LIB})\n"
                "\tendif()",
            )
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Layer 1: run the upstream test suite (sqlite subset, offline).
        self._run_upstream_sqlite_suite()

    def package(self):
        copy(self, "LICENSE_1_0.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "MIT.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()
        libdir = os.path.join(self.package_folder, "lib")
        if self.options.shared:
            rm(self, "*.a", libdir)
        else:
            rm(self, "*.so*", libdir)

    def package_info(self):
        self.cpp_info.libs = ["cppdb"]
        self.cpp_info.set_property("cmake_file_name", "cppdb")
        self.cpp_info.set_property("cmake_target_name", "cppdb::cppdb")
        if not self.options.shared:
            # Static libcppdb.a contains the sqlite backend objects but not
            # sqlite3 itself; consumers must link it as well.
            self.cpp_info.requires = ["sqlite3::sqlite3"]
        if self.settings.os == "Linux":
            self.cpp_info.system_libs = ["dl", "pthread"]
