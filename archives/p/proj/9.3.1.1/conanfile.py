#!/usr/bin/env python3
"""Conan recipe — proj 9.3.1.1 (cmake)

Cartographic projections library (needed by gdal → simple-tiles).
R37: Conan recipe over archived 9.3.1 (cmd-pkgs / no Conan).
OHOS: ohos.toolchain + SQLITE3_* cache vars; ENABLE_CURL/TIFF off (no curl recipe).
"""
import glob
import os
import re
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    collect_libs,
    download,
    export_conandata_patches,
    get,
)


class ProjConan(ConanFile):
    name = "proj"
    version = "9.3.1.1"
    description = "Cartographic projections and coordinate transformations library"
    license = "MIT"
    homepage = "https://proj.org/"
    url = ""
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # PROJ requires SQLite3 (lib). TIFF/CURL optional — disabled (no curl Conan yet).
        self.requires("sqlite3/3.49.1")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _ensure_googletest_tarball(self):
        """Fetch googletest via mirror URLs into build_folder (not git).

        GitCode PR CI applies a text .diff; binary blobs cannot be patched, so
        the tarball must not live in the recipe tree.
        """
        dest_dir = os.path.join(self.build_folder, "cmake")
        os.makedirs(dest_dir, exist_ok=True)
        gtest = os.path.join(dest_dir, "googletest-1.11.0.tar.gz")
        if os.path.isfile(gtest):
            return gtest
        data = self.conan_data["googletest"]
        urls = data["url"] if isinstance(data["url"], (list, tuple)) else [data["url"]]
        sha = data["sha256"]
        last_err = None
        for url in urls:
            try:
                download(self, url, gtest, sha256=sha)
                return gtest
            except Exception as exc:  # noqa: BLE001 — try next mirror
                last_err = exc
                self.output.warning("googletest download failed from {}: {}".format(url, exc))
                if os.path.isfile(gtest):
                    os.remove(gtest)
        raise ConanInvalidConfiguration(
            "无法下载 googletest 1.11.0（已试镜像 {}）: {}".format(urls, last_err)
        )

    def _inject_local_googletest(self):
        """Point unit-test ExternalProject at a local tarball (no direct GitHub)."""
        gtest = self._ensure_googletest_tarball()
        inj = os.path.join(self.source_folder, "test", "googletest", "CMakeLists.txt.in")
        if not os.path.isfile(inj):
            return
        sha = self.conan_data["googletest"]["sha256"]
        open(inj, "w").write(
            (
                "cmake_minimum_required(VERSION 3.16)\n"
                "project(googletest-download NONE)\n"
                "include(ExternalProject)\n"
                "ExternalProject_Add(googletest\n"
                '  URL "file://{url}"\n'
                "  URL_HASH SHA256={sha}\n"
                "  DOWNLOAD_NO_PROGRESS ON\n"
                '  SOURCE_DIR        "${{PROJ_BINARY_DIR}}/googletest-src"\n'
                '  BINARY_DIR        "${{PROJ_BINARY_DIR}}/googletest-build"\n'
                '  CONFIGURE_COMMAND ""\n'
                '  BUILD_COMMAND     ""\n'
                '  TEST_COMMAND      ""\n'
                '  INSTALL_COMMAND   ""\n'
                ")\n"
            ).format(url=gtest, sha=sha)
        )

    def _ohos_toolchain(self):
        ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list)
        ndk = os.environ.get("OHOS_NDK_HOME", "") or os.environ.get("OHOS_SDK_HOME", "")
        candidates = list(ut)
        if ndk:
            candidates.append(os.path.join(ndk, "native/build/cmake/ohos.toolchain.cmake"))
            candidates.append(os.path.join(ndk, "build/cmake/ohos.toolchain.cmake"))
        candidates.append("/opt/ohos-sdk-6.1/native/build/cmake/ohos.toolchain.cmake")
        candidates += sorted(
            glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/build/cmake/ohos.toolchain.cmake")
        )
        for cand in candidates:
            if cand and os.path.isfile(cand):
                return cand
        raise ConanInvalidConfiguration(
            "找不到 ohos.toolchain.cmake：设 OHOS_SDK_HOME / OHOS_NDK_HOME 或 profile user_toolchain"
        )

    def build(self):
        apply_conandata_patches(self)
        # Download googletest via conandata mirrors into build_folder and
        # rewrite ExternalProject to file:// (avoids GitHub at cmake time;
        # also keeps the .tar.gz out of git so PR .diff can apply). Must run
        # before parent cmake configure (.in is used by configure_file).
        self._inject_local_googletest()
        # Cross Docker: shared OHOS binaries mostly SIGSEGV under qemu-aarch64;
        # GIGS gtests segfault, CLI tests (test83+) can hang for hours. Skip
        # BUILD_TESTING here; re-enable on native OHOS.
        sqlite = self.dependencies["sqlite3"]
        sqlite_pkg = sqlite.package_folder
        sqlite_inc = os.path.join(sqlite_pkg, "include")
        sqlite_lib = os.path.join(sqlite_pkg, "lib", "libsqlite3.a")
        if not os.path.isfile(sqlite_lib):
            hits = glob.glob(os.path.join(sqlite_pkg, "lib", "libsqlite3.so*"))
            if hits:
                sqlite_lib = hits[0]
        # sqlite3 CLI must run on the build host (generates proj.db; tests).
        # Native OHOS: Conan sqlite3 packages a same-arch bin/sqlite3 — prefer
        # that when PATH has no system CLI (CI workers often lack apt sqlite3).
        exe_sqlite3 = self._find_host_sqlite3()
        if not exe_sqlite3 or not os.path.isfile(exe_sqlite3):
            raise ConanInvalidConfiguration(
                "需要宿主机可执行的 sqlite3 CLI（生成 proj.db）。"
                "原生 OHOS：确保依赖 sqlite3 包含 bin/sqlite3；"
                "交叉 Linux 宿主机：apt install sqlite3 或放入 PATH/~/tmp/sqlite3"
            )

        bdir = os.path.join(self.build_folder, "build-ohos")
        cmake = self._cmake_bin()
        shared = "ON" if self.options.shared else "OFF"
        # PROJ data install rules bake CMAKE_INSTALL_PREFIX at configure time;
        # ohos.toolchain defaults it to /usr/local → proj.db lands outside the package.
        # Set prefix to package_folder now so share/proj is packaged correctly.
        defs = [
            '-DCMAKE_TOOLCHAIN_FILE="{}"'.format(self._ohos_toolchain()),
            "-DOHOS_ARCH=arm64-v8a",
            "-DCMAKE_BUILD_TYPE={}".format(self.settings.build_type),
            '-DCMAKE_INSTALL_PREFIX="{}"'.format(self.package_folder),
            "-DCMAKE_INSTALL_LIBDIR=lib",
            "-DCMAKE_INSTALL_DATAROOTDIR=share",
            "-DBUILD_SHARED_LIBS={}".format(shared),
            "-DBUILD_TESTING=ON",
            "-DBUILD_APPS=ON",
            "-DBUILD_PROJSYNC=OFF",  # needs CURL
            "-DBUILD_EXAMPLES=OFF",
            "-DENABLE_TIFF=OFF",
            "-DENABLE_CURL=OFF",
            "-DNLOHMANN_JSON_ORIGIN=internal",
            "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
            '-DCMAKE_C_FLAGS="-Wno-unused-command-line-argument"',
            '-DCMAKE_CXX_FLAGS="-Wno-unused-command-line-argument"',
            '-DEXE_SQLITE3="{}"'.format(exe_sqlite3),
            '-DSQLITE3_INCLUDE_DIR="{}"'.format(sqlite_inc),
            '-DSQLITE3_LIBRARY="{}"'.format(sqlite_lib),
        ]
        # Cross FIND_ROOT_PATH_MODE=ONLY: force both so cache vars stick.
        defs.append("-DCMAKE_FIND_ROOT_PATH_MODE_INCLUDE=BOTH")
        defs.append("-DCMAKE_FIND_ROOT_PATH_MODE_LIBRARY=BOTH")
        defs.append("-DCMAKE_FIND_ROOT_PATH_MODE_PACKAGE=BOTH")
        defs.append("-DCMAKE_FIND_ROOT_PATH_MODE_PROGRAM=BOTH")

        self.run('{cm} -B "{bd}" -S "{src}" {defs}'.format(
            cm=cmake, bd=bdir, src=self.source_folder, defs=" ".join(defs)))
        # -j1 to avoid make's recursive jobserver FIFO creation: HMDFS/SELinux
        # rejects mkfifo in all candidate TMPDIRs (/tmp read-only, HMFS
        # Operation not permitted). -j1 build is slow but safe.
        self.run('{cm} --build "{bd}" -j1'.format(
            cm=cmake, bd=bdir))
        # ctest ENVIRONMENT property REPLACES the parent env (PATH included).
        # Inject host sqlite3 CLI + PROJ_TEST_TMPDIR (patches 0002/0003). Patch
        # 0004 makes testprojinfo use `grep -E` so toybox accepts `|` alternation;
        # PATH still prefers GNU grep when available (belt-and-suspenders).
        self._inject_test_env_path(bdir, exe_sqlite3)
        # BUILD_TESTING=ON: full upstream ctest suite (56 cases). Mirrored
        # googletest (conandata) supplies GTest on native OHOS. Failures here
        # surface as non-zero exit so W3 (finish) can HANDOFF on regression.
        ctest = os.path.join(os.path.dirname(cmake), "ctest")
        if not os.path.isfile(ctest):
            ctest = shutil.which("ctest") or "ctest"
        self.run('{ct} --test-dir "{bd}" --output-on-failure'.format(
            ct=ctest, bd=bdir))

    def _sqlite3_cli_runs(self, path):
        """Return True if path is an sqlite3 CLI that runs on this build host."""
        if not path or not os.path.isfile(path):
            return False
        try:
            out = subprocess.run(
                [path, "--version"],
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
            return out.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            return False

    def _find_host_sqlite3(self):
        """Locate a host-runnable sqlite3 CLI for proj.db generation and tests.

        Search order: PATH → common host paths → Conan sqlite3 package bin/.
        Package CLI is OHOS aarch64; on native OHOS CI it runs; on Linux
        cross hosts it is skipped by the --version probe (wrong ELF).
        """
        candidates = []
        which = shutil.which("sqlite3")
        if which:
            candidates.append(which)
        home_tmp = os.path.join(os.path.expanduser("~"), "tmp", "sqlite3")
        candidates += [
            "/usr/bin/sqlite3",
            home_tmp,
            "/storage/Users/currentUser/tmp/sqlite3",
            "/data/service/hnp/bin/sqlite3",
            os.path.join(os.path.expanduser("~"), "usr", "local", "bin", "sqlite3"),
        ]
        try:
            pkg = self.dependencies["sqlite3"].package_folder
            if pkg:
                candidates.append(os.path.join(pkg, "bin", "sqlite3"))
        except (KeyError, AttributeError, TypeError):
            pass
        seen = set()
        for cand in candidates:
            if not cand or cand in seen:
                continue
            seen.add(cand)
            if self._sqlite3_cli_runs(cand):
                return cand
        return None

    def _resolve_test_tmpdir(self):
        """Pick a writable temp dir for ctest scripts (HMDFS cwd is unreliable).

        Prefer PROJ_TEST_TMPDIR / TMPDIR / ~/tmp. Never hard-code a per-host
        path into patches; inject the chosen absolute path via ctest ENVIRONMENT.
        OHOS /tmp is often read-only (R10), so ~/tmp is preferred over /tmp.
        """
        candidates = [
            os.environ.get("PROJ_TEST_TMPDIR"),
            os.environ.get("TMPDIR"),
            os.path.join(os.path.expanduser("~"), "tmp"),
            "/storage/Users/currentUser/tmp",
        ]
        for d in candidates:
            if not d:
                continue
            try:
                os.makedirs(d, exist_ok=True)
                probe = os.path.join(d, ".proj_write_probe")
                with open(probe, "w", encoding="utf-8") as f:
                    f.write("ok")
                os.remove(probe)
                return os.path.abspath(d)
            except OSError:
                continue
        # Last resort: still return ~/tmp even if probe failed (scripts mkdir -p).
        fallback = os.path.abspath(os.path.join(os.path.expanduser("~"), "tmp"))
        self.output.warning(
            "no verified writable PROJ_TEST_TMPDIR; using {}".format(fallback)
        )
        try:
            os.makedirs(fallback, exist_ok=True)
        except OSError:
            pass
        return fallback

    def _is_gnu_grep(self, grep_path):
        """Return True if grep_path's --version banner contains 'GNU'.

        Do not use a BRE `\\|` probe: toybox grep keeps `A\\|B` on its literal
        fast path (no match), but other probes can false-positive. Require the
        GNU banner so we never prepend /system/bin (toybox) ahead of hnp.
        """
        if not grep_path or not os.path.isfile(grep_path):
            return False
        try:
            out = subprocess.run(
                [grep_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            banner = (out.stdout or "") + (out.stderr or "")
            return "GNU" in banner
        except (OSError, subprocess.TimeoutExpired):
            return False

    def _find_gnu_grep(self):
        """Locate a GNU grep binary (optional; patch 0004 uses grep -E).

        Prefer known OHOS hnp install before shutil.which — the recipe Python
        process may not have buildenv PATH, so which() often returns toybox
        under /system/bin or /data/app/bin.
        """
        candidates = [
            "/data/service/hnp/bin/grep",
            "/usr/bin/grep",
            "/bin/grep",
            "/usr/local/bin/grep",
            "/opt/homebrew/bin/grep",
            os.path.join(os.path.expanduser("~"), "usr", "local", "bin", "grep"),
        ]
        which = shutil.which("grep")
        if which:
            candidates.append(which)
        seen = set()
        for cand in candidates:
            if not cand or cand in seen:
                continue
            seen.add(cand)
            if self._is_gnu_grep(cand):
                return cand
        return None

    def _inject_test_env_path(self, bdir, sqlite3_exe=None):
        """Inject PATH + PROJ_TEST_TMPDIR into ctest ENVIRONMENT.

        ProjTest.cmake sets `ENVIRONMENT "PROJ_...;PROJ_DATA=..."` which
        replaces parent env (incl. PATH / TMPDIR). Several test scripts need:

          * `sqlite3` — host CLI for testprojinfo's PROJ_AUX_DB sub-test.
          * GNU `grep` — optional belt-and-suspenders; patch 0004 switches
            testprojinfo to `grep -E` so toybox also accepts `|` alternation.
          * `PROJ_TEST_TMPDIR` — absolute writable dir for patches 0002/0003
            (HMDFS cwd under ctest makes relative paths / empty $PWD fail).

        Missing optional PATH entries emit warnings and degrade; PROJ_TEST_TMPDIR
        always gets a best-effort absolute path. Expand the real process PATH
        into the ENVIRONMENT string (do not leave literal `$ENV{PATH}` for
        ctest — safer across cmake/ctest versions).
        """
        test_tmpdir = self._resolve_test_tmpdir()

        sqlite_dir = ""
        if sqlite3_exe and os.path.isfile(sqlite3_exe):
            sqlite_dir = os.path.dirname(os.path.abspath(sqlite3_exe))
        else:
            found = self._find_host_sqlite3()
            if found:
                sqlite_dir = os.path.dirname(os.path.abspath(found))
            else:
                self.output.warning(
                    "host sqlite3 not found; testprojinfo PROJ_AUX_DB may fail"
                )

        gnu_grep = self._find_gnu_grep()
        gnu_dir = ""
        if gnu_grep:
            gnu_dir = os.path.dirname(os.path.abspath(gnu_grep))
        else:
            # Still prepend hnp bin when present — may hold GNU grep even if
            # --version probe failed (codesign/sandbox during recipe run).
            hnp_bin = "/data/service/hnp/bin"
            if os.path.isdir(hnp_bin):
                gnu_dir = hnp_bin
            self.output.warning(
                "GNU grep not confirmed (tried hnp, /usr/bin, /bin, PATH); "
                "prepending {} and relying on patch 0004 grep -E".format(
                    gnu_dir or "(none)"
                )
            )

        # Concrete PATH for ctest ENVIRONMENT (semicolon-separated env list).
        base_path = os.environ.get("PATH", "/data/service/hnp/bin:/system/bin:/bin")
        prefix_parts = [p for p in (gnu_dir, sqlite_dir) if p]
        path_value = ":".join(prefix_parts + [base_path]) if prefix_parts else base_path
        env_prefix = "PATH={};PROJ_TEST_TMPDIR={}".format(path_value, test_tmpdir)

        ctestf = os.path.join(bdir, "test", "cli", "CTestTestfile.cmake")
        if not os.path.isfile(ctestf):
            return
        with open(ctestf, "r", encoding="utf-8") as f:
            content = f.read()
        # Strip prior injections so re-runs replace rather than stack prefixes.
        stripped = re.sub(
            r'ENVIRONMENT "(?:PATH=[^;]*;)*(?:PROJ_TEST_TMPDIR=[^;]*;)*',
            'ENVIRONMENT "',
            content,
        )
        new = re.sub(
            r'ENVIRONMENT "((?:[^;"]+;)*[^;"]+)"',
            lambda m: 'ENVIRONMENT "' + env_prefix + ';' + m.group(1) + '"',
            stripped,
        )
        if new != content:
            with open(ctestf, "w", encoding="utf-8") as f:
                f.write(new)

    def _cmake_bin(self):
        conf = self.conf.get("tools.cmake:cmake_program", default=None)
        candidates = [
            conf,
            "/opt/ohos-sdk-6.1/native/build-tools/cmake/bin/cmake",
            shutil.which("cmake"),
        ]
        for c in candidates:
            if c and os.path.isfile(c):
                return c
        raise ConanInvalidConfiguration("找不到 cmake（设 tools.cmake:cmake_program 或 OHOS SDK）")

    def package(self):
        bdir = os.path.join(self.build_folder, "build-ohos")
        cmake = self._cmake_bin()
        # Prefix already set at configure; still pass --prefix as a safety net.
        self.run('{cm} --install "{bd}" --prefix "{pf}"'.format(
            cm=cmake, bd=bdir, pf=self.package_folder))
        data = os.path.join(self.package_folder, "share", "proj")
        if not os.path.isfile(os.path.join(data, "proj.db")):
            raise ConanInvalidConfiguration(
                "package missing share/proj/proj.db — check CMAKE_INSTALL_PREFIX"
            )
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        candidates_objcopy = [
            "/data/service/hnp/bin/llvm-objcopy",
            shutil.which("llvm-objcopy") or "",
        ]
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = ce.get("c") or ""
        if cc:
            candidates_objcopy.insert(0, os.path.join(os.path.dirname(cc), "llvm-objcopy"))
        objcopy = next((p for p in candidates_objcopy if p and os.path.isfile(p)), None)
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool not found; skip OHOS codesign (cross/SDK env)")
            return
        for so in sos:
            if objcopy:
                self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=so))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=so))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "PROJ")
        self.cpp_info.set_property("cmake_target_name", "PROJ::proj")
        self.cpp_info.set_property("pkg_config_name", "proj")
        self.cpp_info.libs = collect_libs(self) or ["proj"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.requires = ["sqlite3::sqlite3"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
        # proj.db lives under share/proj
        data = os.path.join(self.package_folder, "share", "proj")
        if os.path.isdir(data):
            self.runenv_info.define_path("PROJ_DATA", data)
            self.buildenv_info.define_path("PROJ_DATA", data)
