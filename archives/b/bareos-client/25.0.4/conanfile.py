#!/usr/bin/env python3
"""Conan recipe — bareos-client 25.0.4 (CMake, universal file-daemon client).

Bareos (https://www.bareos.org) is an open-source backup suite. This recipe
builds upstream's "universal client" configuration: the file daemon
(bareos-fd) with its support libraries, without director/storage daemons.

Build strategy (standard CMake + Conan mechanisms only):
- -DBUILD_UNIVERSAL_CLIENT=ON: upstream's portable-client preset. It forces
  client-only, disables python/gfapi/jansson/lzo/capability/bconsole and
  static runtime libs, so only OpenSSL + ZLIB remain as conan requirements.
- CPM packages (cli11/fmt/gsl/expected/utfcpp/xxhash) are vendored as source
  tarballs (conandata.yml `deps`, aevol/9.4.0 precedent) and injected via
  CPM_<NAME>_SOURCE, so configure never touches the network.
- googletest 1.14.0 is vendored, built and installed into a build-local
  prefix exposed via GTest_ROOT, so the upstream gtest suite
  (core/src/tests, registered with ctest as "gtest:*") really runs.
- ctest runs in build(); its output is parsed and reported as a single
  HMBS_UPSTREAM_TEST_RESULT=<json> line. Any failure fails the build.
"""
import glob
import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, download, export_conandata_patches, get, unzip


class BareosClientConan(ConanFile):
    name = "bareos-client"
    version = "25.0.4"
    description = "Bareos backup suite — universal file-daemon client (bareos-fd)"
    license = "AGPL-3.0-only"
    homepage = "https://www.bareos.org"
    url = "https://github.com/bareos/bareos"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    # Vendored CPM/build dependencies: conandata key -> CPM_<NAME>_SOURCE var.
    _CPM_SOURCES = (
        ("cli11", "CPM_CLI11_SOURCE"),
        ("fmt", "CPM_fmt_SOURCE"),
        ("gsl", "CPM_Microsoft.GSL_SOURCE"),
        ("expected", "CPM_tl-expected_SOURCE"),
        ("utfcpp", "CPM_utf8cpp_SOURCE"),
        ("xxhash", "CPM_xxHash_SOURCE"),
    )

    def requirements(self):
        self.requires("openssl/3.5.6")
        self.requires("zlib/1.3.1")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "bareos-client is only supported on Linux/OHOS, "
                "got %s" % self.settings.os
            )

    def layout(self):
        cmake_layout(self)

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        # Local zlib/1.3.1 sets only cpp_info.libs=["z"] (no
        # cmake_file_name/target). Without remapping, CMakeDeps emits
        # zlib-config.cmake with target zlib::zlib, while upstream calls
        # find_package(ZLIB REQUIRED) and links ZLIB::ZLIB -> generate-time
        # "Target ZLIB::ZLIB not found". Remap to the canonical names so
        # the generated ZLIBConfig.cmake provides ZLIB::ZLIB.
        deps.set_property("zlib", "cmake_file_name", "ZLIB")
        deps.set_property("zlib", "cmake_target_name", "ZLIB::ZLIB")
        deps.set_property("zlib", "cmake_find_mode", "config")
        deps.generate()
        tc = CMakeToolchain(self)
        # Upstream portable-client preset (forces client-only, drops
        # python/gfapi/jansson/lzo/capability/bconsole).
        tc.variables["BUILD_UNIVERSAL_CLIENT"] = True
        # Static internal libs: the shipped bareos-fd must not depend on
        # unshipped libbareos*.so files.
        tc.variables["BUILD_SHARED_LIBS"] = False
        # No web UI (needs npm) and no cluster systemtests in a client build.
        tc.variables["ENABLE_WEBUI"] = False
        tc.variables["ENABLE_SYSTEMTESTS"] = False
        # OHOS has no sys/acl.h; upstream configure FATAls otherwise.
        tc.variables["acl"] = False
        # OHOS sysroot provides sys/xattr.h (so HAVE_XATTR would be set) but
        # matches none of the xattr backends (AIX/Darwin/Linux/Sun): the
        # generic BuildXattrStreams/ParseXattrStreams entry points then
        # reference undefined os_build/os_parse/os_default symbols.
        # Upstream declares option(xattr ...) but core/CMakeLists.txt ignores
        # it; build() applies a line-number-independent reset (mirroring the
        # acl block) so this OFF takes the !HAVE_XATTR stub path (kErrorFatal).
        tc.variables["xattr"] = False
        # OHOS provides no gettext/libintl: with the default ENABLE_NLS=1,
        # baconfig.h maps T_(s) to gettext((s)) but gettext stays undeclared
        # and the whole core/src/lib fails (-Werror). Upstream natively
        # supports disabling NLS (cmake/BareosSetVariableDefaults.cmake:
        # ENABLE_NLS CACHE STRING "1"/"0"; core/CMakeLists.txt itself does
        # `set(ENABLE_NLS 0)` for AIX); with 0, baconfig.h falls back to
        # `#define T_(s) (s)` plus textdomain/bindtextdomain/setlocale stubs.
        tc.variables["ENABLE_NLS"] = "0"
        # OHOS libc defines EOWNERDEAD but lacks the pthread robust-mutex
        # APIs (pthread_mutexattr_setrobust/pthread_mutex_consistent), so
        # the bundled lmdb (core/src/lmdb/mdb.c, MDB_USE_ROBUST defaults
        # to 1) fails with -Werror implicit declarations. Upstream mdb.c
        # documents -DMDB_USE_ROBUST=0 for such platforms, and every robust
        # call site is guarded by MDB_ROBUST_SUPPORTED, so the locks safely
        # degrade to plain mutexes. Injected via the toolchain (applies to
        # the lmdb target as well) instead of patching
        # core/src/lmdb/CMakeLists.txt: a hand-written patch hunk header
        # miscount broke apply_conandata_patches with "Failed to parse
        # patch" in preflight.
        tc.preprocessor_definitions["MDB_USE_ROBUST"] = "0"
        # Offline CPM injection (prepared in build() before configure).
        for key, var in self._CPM_SOURCES:
            tc.variables[var] = self._cpm_dir(key).replace("\\", "/")
        # Vendored googletest prefix (built + installed in build()).
        tc.variables["GTest_ROOT"] = self._gtest_install_dir().replace("\\", "/")
        # Prefer conan-provided OpenSSL/ZLIB over any system copies.
        openssl = self.dependencies["openssl"]
        zlib = self.dependencies["zlib"]
        tc.variables["OPENSSL_ROOT_DIR"] = openssl.package_folder.replace("\\", "/")
        tc.variables["ZLIB_ROOT"] = zlib.package_folder.replace("\\", "/")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        self._fix_xattr_option()
        self._fix_stdcppfs_link()
        self._fix_fvec_tmpfile()
        self._fix_backtrace_export_dynamic()
        self._prepare_cpm_sources()
        self._build_gtest()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    def package(self):
        fd = self._find_built_fd()
        if fd is None:
            raise ConanException(
                "built bareos-fd binary not found under %s" % self.build_folder
            )
        self.output.info("packaging bareos-fd from %s" % fd)
        copy(self, "bareos-fd", src=os.path.dirname(fd),
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        try:
            os.chmod(os.path.join(self.package_folder, "bin", "bareos-fd"), 0o755)
        except OSError as exc:
            self.output.warning("chmod kept failing (ignored): %s" % exc)
        lic = os.path.join(self.source_folder, "LICENSE.txt")
        if os.path.isfile(lic):
            copy(self, "LICENSE.txt", src=self.source_folder,
                 dst=os.path.join(self.package_folder, "licenses"),
                 keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.conf_info.define("user.bareos-client:exe",
                              os.path.join(self.package_folder, "bin", "bareos-fd"))

    # ── helpers ─────────────────────────────────────────────────────

    def _fix_xattr_option(self):
        """Respect -Dxattr=OFF without a context-sensitive patch.

        Upstream declares option(xattr ...) but core/CMakeLists.txt sets
        HAVE_XATTR purely on sys/xattr.h detection, ignoring it; on OHOS the
        header exists yet no AIX/Darwin/Linux/Sun backend matches, leaving
        os_build/os_parse/os_default symbols undefined in xattr.cc. Two
        hand-written patch revisions (hunk headers @@ -280 / @@ -589) both
        failed apply_conandata_patches with "hunk doesn't match / source
        file is different" because the surrounding acl-block context shifts.
        Instead of a third patch, append a NOT-xattr reset right after the
        distinctive `set(have_xattr YES)` line (substring match, no line
        numbers): with -Dxattr=OFF this unsets HAVE_XATTR so xattr.cc takes
        the !HAVE_XATTR stub path; with -Dxattr=ON the guard is false and
        behaviour is unchanged.
        """
        path = os.path.join(self.source_folder, "core", "CMakeLists.txt")
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        anchor = "set(have_xattr YES)"
        reset = (anchor + "\nif(NOT xattr)\n  unset(HAVE_XATTR)\n"
                 "  set(have_xattr NO)\nendif()")
        if anchor in text and "unset(HAVE_XATTR)" not in text:
            text = text.replace(anchor, reset, 1)
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(text)
            self.output.info("xattr option respected via recipe text edit")
        elif "unset(HAVE_XATTR)" not in text:
            raise ConanException(
                "xattr anchor 'set(have_xattr YES)' not found in %s" % path)

    def _fix_stdcppfs_link(self):
        """Drop the GNU-only -lstdc++fs on Clang/libc++ toolchains.

        Upstream core/src/tests/CMakeLists.txt links dedupable_volume_test
        with `$<$<NOT:$<PLATFORM_ID:FreeBSD>>:stdc++fs>`. On OHOS
        (clang-15 + libc++ + lld) that generator expression is true, so the
        link line gets `-lstdc++fs`, but libc++ ships no such library --
        stdc++fs is a libstdc++ (GNU) transitional library for GCC < 9
        only (libc++ provides <filesystem> in the main c++ library).
        lld then fails with `unable to find library -lstdc++fs`
        (preflight: dedupable_volume_test link, 94%). Restrict the link to
        `$<$<CXX_COMPILER_ID:GNU>:stdc++fs>` via substring replacement (no
        line numbers, same approach as _fix_xattr_option): GNU behaviour
        unchanged, Clang/AppleClang never links it. Anchor missing raises
        so a silent no-op cannot mask an upstream rename.
        """
        old = "$<$<NOT:$<PLATFORM_ID:FreeBSD>>:stdc++fs>"
        new = "$<$<CXX_COMPILER_ID:GNU>:stdc++fs>"
        fixed = 0
        for dirpath, _dirnames, filenames in os.walk(self.source_folder):
            for name in filenames:
                if not name.endswith((".txt", ".cmake")):
                    continue
                path = os.path.join(dirpath, name)
                try:
                    with open(path, encoding="utf-8") as handle:
                        text = handle.read()
                except (OSError, UnicodeDecodeError):
                    continue
                if old in text:
                    text = text.replace(old, new)
                    with open(path, "w", encoding="utf-8",
                              newline="\n") as handle:
                        handle.write(text)
                    fixed += 1
                    self.output.info("stdc++fs link restricted to GNU: %s"
                                     % os.path.relpath(path,
                                                       self.source_folder))
        if fixed == 0:
            raise ConanException(
                "stdc++fs anchor '%s' not found under %s" % (old,
                                                             self.source_folder))

    def _fix_fvec_tmpfile(self):
        """Use TMPDIR-aware temp file in fvec gtest fixture (OHOS /tmp RO).

        Upstream core/src/tests/fvec.cc SetUp() uses std::tmpfile(), which
        hardcodes P_tmpdir ("/tmp"). HMBS preflight runs with a read-only
        /tmp (preflight.sh[306]: "can't create temporary file
        /tmp/shou6alf.tmp: Read-only file system"; HMBS injects a writable
        TMPDIR/TMP/TEMP instead) so tmpfile() returns NULL; the following
        fileno(NULL) then SEGFAULTs all 5 fvec_fixture tests
        (preflight: 84-88 SEGFAULT). Keep the test semantics (anonymous
        file-backed fvec) and only replace the temp-file root: try
        std::tmpfile() first, fall back to mkstemp() under
        $TMPDIR/$TMP/$TEMP, and ASSERT non-null so a future failure
        reports Failed instead of crashing with Exception. The NUL
        terminator is copied via the c_str() range (no '\\0' char literal:
        clang -Wnull-character fires on push_back('\\0') under -Werror).
        """
        path = os.path.join(self.source_folder, "core", "src", "tests",
                            "fvec.cc")
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        old_setup = ("  void SetUp() override\n  {\n"
                     "    backing = std::unique_ptr<FILE, file_closer>"
                     "(std::tmpfile());\n"
                     "    rand_ints = gen_rand_ints(100);\n  }")
        new_setup = ("  void SetUp() override\n  {\n"
                     "    FILE* tmp = std::tmpfile();\n"
                     "    if (!tmp) {\n"
                     '      const char* d = std::getenv("TMPDIR");\n'
                     '      if (!d) d = std::getenv("TMP");\n'
                     '      if (!d) d = std::getenv("TEMP");\n'
                     '      if (!d || !*d) d = "/tmp";\n'
                     '      std::string tmpl = std::string(d) + "/fvecXXXXXX";\n'
                     "      std::vector<char> buf(tmpl.c_str(), tmpl.c_str() + tmpl.size() + 1);\n"
                     "      int mfd = mkstemp(buf.data());\n"
                     '      if (mfd >= 0) { tmp = fdopen(mfd, "w+b"); '
                     "if (!tmp) { close(mfd); } }\n"
                     "    }\n"
                     "    ASSERT_TRUE(tmp != nullptr)\n"
                     '      << "tmpfile() and mkstemp($TMPDIR) both failed; '
                     '/tmp is read-only on OHOS, TMPDIR="\n'
                     '      << (std::getenv("TMPDIR") ? std::getenv("TMPDIR") '
                     ': "(null)");\n'
                     "    backing = std::unique_ptr<FILE, file_closer>(tmp);\n"
                     "    rand_ints = gen_rand_ints(100);\n  }")
        if old_setup in text:
            text = text.replace(old_setup, new_setup, 1)
            self.output.info("fvec tmpfile made TMPDIR-aware via recipe edit")
        elif "mkstemp(buf.data())" in text:
            # Migrate the first-generation fix (push_back('\0'), rejected
            # by clang -Wnull-character under -Werror) to the c_str()
            # range copy when an already-patched source is reused.
            if "buf.push_back" in text:
                text = text.replace(
                    "std::vector<char> buf(tmpl.begin(), tmpl.end());",
                    "std::vector<char> buf(tmpl.c_str(), tmpl.c_str() + tmpl.size() + 1);",
                    1)
                text = text.replace("      buf.push_back('\\0');\n", "", 1)
                self.output.info("fvec tmpfile fix migrated off '\\0' literal")
            else:
                self.output.info("fvec tmpfile fix already applied, skipping")
        else:
            raise ConanException(
                "fvec SetUp anchor not found in %s" % path)
        # Ensure required headers for getenv/string/mkstemp/fdopen.
        added = []
        if "#include <cstdlib>" not in text:
            text = text.replace("#include <cstdio>",
                                "#include <cstdio>\n#include <cstdlib>", 1)
            added.append("cstdlib")
        if "#include <string>" not in text:
            text = text.replace("#include <cstdio>",
                                "#include <cstdio>\n#include <string>", 1)
            added.append("string")
        if "std::vector<char> buf" in text and "#include <vector>" not in text:
            # mkstemp template buffer; upstream may only pull <vector>
            # transitively, so include it explicitly.
            text = text.replace("#include <cstdio>",
                                "#include <cstdio>\n#include <vector>", 1)
            added.append("vector")
        if "mkstemp" in text and "#include <unistd.h>" not in text:
            # mkstemp/fdopen/close declarations (POSIX).
            text = text.replace('#include "stored/backends/dedupable/fvec.h"',
                                '#include "stored/backends/dedupable/fvec.h"'
                                "\n#include <unistd.h>", 1)
            added.append("unistd.h")
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        if added:
            self.output.info("fvec.cc headers added: %s" % ",".join(added))

    def _fix_backtrace_export_dynamic(self):
        """Export test_backtrace symbols so dladdr() can resolve them.

        Upstream test_backtrace.cc expects Backtrace(0,1)[0] to contain
        "Backtrace" via dladdr()+demangle. dladdr() resolves through the
        dynamic symbol table; without --export-dynamic the main-executable
        symbols stay local and dladdr falls back to "unknown", failing the
        assertion on OHOS/lld while passing on GNU toolchains that export
        more aggressively. Appending LINKER:--export-dynamic to the
        test_backtrace target (substring edit, no line numbers) keeps GNU
        behaviour unchanged and makes the OHOS result genuine. Anchor
        missing raises so a silent no-op cannot mask an upstream rename.
        """
        path = os.path.join(self.source_folder, "core", "src", "tests",
                            "CMakeLists.txt")
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        anchor = ("bareos_add_test(test_backtrace "
                  "LINK_LIBRARIES Bareos::Lib GTest::gtest_main)")
        if "export-dynamic" in text:
            self.output.info("test_backtrace export-dynamic already set")
            return
        if anchor not in text:
            raise ConanException(
                "test_backtrace anchor not found in %s" % path)
        fix = (anchor + "\n  if(TARGET test_backtrace)\n"
               "    target_link_options(test_backtrace PRIVATE "
               "\"LINKER:--export-dynamic\")\n  endif()")
        text = text.replace(anchor, fix, 1)
        with open(path, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        self.output.info("test_backtrace linked with --export-dynamic")

    def _cpm_dir(self, key):
        return os.path.join(self.build_folder, "cpm-sources", key)

    def _gtest_src_dir(self):
        return os.path.join(self.build_folder, "gtest-src")

    def _gtest_bin_dir(self):
        return os.path.join(self.build_folder, "gtest-bin")

    def _gtest_install_dir(self):
        return os.path.join(self.build_folder, "gtest-install")

    def _prepare_cpm_sources(self):
        """Download + extract vendored CPM tarballs (offline configure)."""
        for key, _var in self._CPM_SOURCES:
            dest = self._cpm_dir(key)
            ready = os.path.join(dest, ".ohos-cpm-ready")
            if os.path.isfile(ready):
                continue
            entry = self.conan_data["deps"][key]
            archive_dir = os.path.join(self.build_folder, "cpm-archives")
            os.makedirs(archive_dir, exist_ok=True)
            tarball = os.path.join(archive_dir, entry["filename"])
            if not os.path.isfile(tarball):
                download(self, entry["url"], tarball, sha256=entry["sha256"])
            tmp = dest + "-extract"
            shutil.rmtree(tmp, ignore_errors=True)
            shutil.rmtree(dest, ignore_errors=True)
            os.makedirs(tmp, exist_ok=True)
            unzip(self, tarball, tmp)
            subdirs = sorted(d for d in glob.glob(os.path.join(tmp, "*"))
                             if os.path.isdir(d))
            if len(subdirs) != 1:
                raise ConanException(
                    "expected a single top dir in %s, got %s"
                    % (entry["filename"], subdirs)
                )
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.move(subdirs[0], dest)
            shutil.rmtree(tmp, ignore_errors=True)
            with open(ready, "w") as marker:
                marker.write("ready\n")
            self.output.info("cpm source ready: %s -> %s" % (key, dest))

    def _conan_toolchain_file(self):
        hits = glob.glob(os.path.join(self.build_folder, "**",
                                      "conan_toolchain.cmake"), recursive=True)
        if not hits:
            raise ConanException(
                "conan_toolchain.cmake not found under %s" % self.build_folder
            )
        return hits[0]

    def _gtest_config_installed(self):
        hits = glob.glob(os.path.join(self._gtest_install_dir(), "**",
                                      "GTestConfig.cmake"), recursive=True)
        return bool(hits)

    def _build_gtest(self):
        """Build + install vendored googletest for find_package(GTest)."""
        if self._gtest_config_installed():
            self.output.info("vendored googletest already installed, skipping")
            return
        entry = self.conan_data["deps"]["googletest"]
        archive_dir = os.path.join(self.build_folder, "cpm-archives")
        os.makedirs(archive_dir, exist_ok=True)
        tarball = os.path.join(archive_dir, entry["filename"])
        if not os.path.isfile(tarball):
            download(self, entry["url"], tarball, sha256=entry["sha256"])
        src = self._gtest_src_dir()
        if not os.path.isdir(src) or not glob.glob(os.path.join(src, "*")):
            shutil.rmtree(src, ignore_errors=True)
            os.makedirs(src, exist_ok=True)
            unzip(self, tarball, src)
            subdirs = sorted(d for d in glob.glob(os.path.join(src, "*"))
                             if os.path.isdir(d))
            if len(subdirs) != 1:
                raise ConanException(
                    "expected a single top dir in %s" % entry["filename"]
                )
            for item in os.listdir(subdirs[0]):
                shutil.move(os.path.join(subdirs[0], item), src)
            os.rmdir(subdirs[0])
        bin_dir = self._gtest_bin_dir()
        prefix = self._gtest_install_dir()
        toolchain = self._conan_toolchain_file()
        self.run('cmake -S "%s" -B "%s" '
                 '-DCMAKE_TOOLCHAIN_FILE="%s" '
                 '-DCMAKE_BUILD_TYPE=Release '
                 '-DCMAKE_INSTALL_PREFIX="%s"' % (src, bin_dir, toolchain, prefix))
        self.run('cmake --build "%s"' % bin_dir)
        self.run('cmake --install "%s"' % bin_dir)
        if not self._gtest_config_installed():
            raise ConanException(
                "googletest install did not produce GTestConfig.cmake "
                "under %s" % prefix
            )

    def _find_built_fd(self):
        for dirpath, _dirnames, filenames in os.walk(self.build_folder):
            if "CMakeFiles" in dirpath:
                continue
            if "bareos-fd" not in filenames:
                continue
            candidate = os.path.join(dirpath, "bareos-fd")
            try:
                with open(candidate, "rb") as blob:
                    if blob.read(4) == b"\x7fELF":
                        return candidate
            except OSError:
                continue
        return None

    def _ctest_dir(self):
        """Directory holding CTestTestfile.cmake (ctest must run there)."""
        for dirpath, _dirnames, filenames in os.walk(self.build_folder):
            if "CTestTestfile.cmake" in filenames:
                # Prefer the top-level test dir (fewest path components).
                return dirpath
        return self.build_folder

    def _run_upstream_tests(self):
        """Run ctest, parse per-test results, emit the evidence marker."""
        log_path = os.path.join(self.build_folder, "ctest-ohos.log")
        test_dir = self._ctest_dir()
        self.output.info("ctest dir: %s" % test_dir)
        try:
            self.run('ctest --output-on-failure > "%s" 2>&1' % log_path,
                     cwd=test_dir)
            returncode = 0
        except ConanException:
            returncode = 1
        log = ""
        if os.path.isfile(log_path):
            with open(log_path, encoding="utf-8", errors="replace") as log_file:
                log = log_file.read()
        passed = failed = timeout = skipped = 0
        for line in log.splitlines():
            if "Test #" not in line:
                continue
            # NB: SEGFAULT crashes report "***Exception: SegFault", not
            # "***Failed"; both must count as failed or the marker
            # undercounts (passed==discovered while ctest rc==1).
            if "Passed" in line:
                passed += 1
            elif "Timeout" in line:
                timeout += 1
            elif "Skipped" in line or "SKIP_RETURN_CODE" in line:
                skipped += 1
            elif ("Failed" in line or "Exception" in line
                  or "SegFault" in line or "SEGFAULT" in line
                  or "Timeout" in line):
                failed += 1
            else:
                # Unknown per-test status (e.g. "***Not Run"): never
                # silently count as passed; fail loudly instead.
                failed += 1
        discovered = passed + failed + timeout + skipped
        executed = passed + failed + timeout
        ok = (returncode == 0 and discovered > 0
              and failed == 0 and timeout == 0 and executed > 0)
        marker = {
            "status": "passed" if ok else "failed",
            "framework": "ctest",
            "command": "ctest --output-on-failure",
            "discovered": discovered,
            "executed": executed,
            "passed": passed,
            "failed": failed + timeout,
            "skipped": skipped,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT="
                         + json.dumps(marker, separators=(",", ":")))
        if not ok:
            tail = "\n".join(log.splitlines()[-40:])
            raise ConanException(
                "upstream ctest failed (rc=%d, discovered=%d, passed=%d, "
                "failed=%d, skipped=%d):\n%s"
                % (returncode, discovered, passed,
                   failed + timeout, skipped, tail)
            )
