#!/usr/bin/env python3
"""Conan recipe — proj 9.8.1 (cmake)

Cartographic projections and coordinate transformations library.
OHOS: ohos.toolchain + SQLite3_* cache vars; ENABLE_CURL/TIFF off (no curl recipe).

Upstream tests: BUILD_TESTING=ON runs the full upstream ctest suite.
PROJ 9.8.1 resolves GTest through CMake FetchContent (v1.15.2); the recipe
pre-fetches that release and points FETCHCONTENT_SOURCE_DIR_GOOGLETEST at the
extracted tree so the unit tests build without network access.
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
    unzip,
)


class ProjConan(ConanFile):
    name = "proj"
    version = "9.8.1"
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

    def _ensure_googletest_source(self):
        """Fetch and extract googletest 1.15.2 into build_folder.

        PROJ 9.8.1 resolves GTest via CMake FetchContent; pointing
        FETCHCONTENT_SOURCE_DIR_GOOGLETEST at this tree keeps the configure step
        fully offline. The archive is never vendored in git: GitCode PR CI
        applies a text .diff and cannot carry binary blobs.
        """
        dest_dir = os.path.join(self.build_folder, "gtest")
        src_dir = os.path.join(dest_dir, "googletest-1.15.2")
        marker = os.path.join(src_dir, "CMakeLists.txt")
        if os.path.isfile(marker):
            return src_dir
        os.makedirs(dest_dir, exist_ok=True)
        archive = os.path.join(dest_dir, "googletest-1.15.2.zip")
        data = self.conan_data["googletest"]
        urls = data["url"] if isinstance(data["url"], (list, tuple)) else [data["url"]]
        sha = data["sha256"]
        last_err = None
        for url in urls:
            try:
                download(self, url, archive, sha256=sha)
                break
            except Exception as exc:  # noqa: BLE001 — try the next mirror
                last_err = exc
                self.output.warning(
                    "googletest download failed from {}: {}".format(url, exc)
                )
                if os.path.isfile(archive):
                    os.remove(archive)
        else:
            raise ConanInvalidConfiguration(
                "无法下载 googletest 1.15.2（已试镜像 {}）: {}".format(urls, last_err)
            )
        unzip(self, archive, destination=src_dir, strip_root=True)
        if not os.path.isfile(marker):
            raise ConanInvalidConfiguration(
                "googletest 解压后缺少 CMakeLists.txt: {}".format(src_dir)
            )
        return src_dir

    def _ohos_toolchain(self):
        ut = self.conf.get("tools.cmake.cmaketoolchain:user_toolchain", default=[], check_type=list)
        ndk = os.environ.get("OHOS_NDK_HOME", "") or os.environ.get("OHOS_SDK_HOME", "")
        candidates = list(ut)
        if ndk:
            candidates.append(os.path.join(ndk, "native/build/cmake/ohos.toolchain.cmake"))
            candidates.append(os.path.join(ndk, "build/cmake/ohos.toolchain.cmake"))
        # Derive from the configured C compiler: <sdk>/native/llvm/bin/clang ->
        # <sdk>/native/build/cmake/ohos.toolchain.cmake (harmonybrew SDK layout).
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = ce.get("c") or ""
        if cc:
            native_dir = os.path.abspath(os.path.join(os.path.dirname(cc), "..", ".."))
            candidates.append(os.path.join(native_dir, "build", "cmake", "ohos.toolchain.cmake"))
        candidates += sorted(glob.glob(os.path.join(
            os.path.expanduser("~"), ".harmonybrew", "opt", "ohos-sdk@*",
            "native", "build", "cmake", "ohos.toolchain.cmake")))
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
        # Pre-fetch googletest and hand it to CMake FetchContent (no network).
        gtest_src = self._ensure_googletest_source()
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
            '-DSQLite3_INCLUDE_DIR="{}"'.format(sqlite_inc),
            '-DSQLite3_LIBRARY="{}"'.format(sqlite_lib),
            # No route to the connectivity probe host on the OHOS worker; the
            # local GTest tree (patch 0002) satisfies the unit-test dependency.
            "-DTESTING_USE_NETWORK=OFF",
            "-DUSE_EXTERNAL_GTEST=OFF",
            '-DFETCHCONTENT_SOURCE_DIR_GOOGLETEST="{}"'.format(gtest_src),
            # OHOS: cmake install rewrites RUNPATH, invalidating the toolchain
            # code signature. Skip RPATH rewriting so the signed .so stays valid.
            "-DCMAKE_SKIP_INSTALL_RPATH=ON",
        ]
        # Cross FIND_ROOT_PATH_MODE=ONLY: force both so cache vars stick.
        defs.append("-DCMAKE_FIND_ROOT_PATH_MODE_INCLUDE=BOTH")
        defs.append("-DCMAKE_FIND_ROOT_PATH_MODE_LIBRARY=BOTH")
        defs.append("-DCMAKE_FIND_ROOT_PATH_MODE_PACKAGE=BOTH")
        defs.append("-DCMAKE_FIND_ROOT_PATH_MODE_PROGRAM=BOTH")

        self._configure(cmake, bdir, defs)
        # ctest ENVIRONMENT property REPLACES the parent env (PATH included).
        # Inject host sqlite3 CLI + PROJ_TEST_TMPDIR (patch 0003).
        self._inject_test_env_path(bdir, exe_sqlite3)
        # BUILD_TESTING=ON: full upstream ctest suite. Failures here surface as
        # non-zero exit so a regression is never silently ignored.
        ctest = os.path.join(os.path.dirname(cmake), "ctest")
        if not os.path.isfile(ctest):
            ctest = shutil.which("ctest") or "ctest"
        self.run('{ct} --test-dir "{bd}" --output-on-failure'.format(
            ct=ctest, bd=bdir))

    def _configure(self, cmake, bdir, defs):
        """Configure with Ninja when available, else fall back to make -j1.

        `make -jN` (N>1) creates a jobserver FIFO under TMPDIR; HMDFS/SELinux
        rejects mkfifo, so the default generator must build serially. Ninja does
        not use a jobserver, which keeps parallel builds available on OHOS.
        """
        src = self.source_folder
        ninja = shutil.which("ninja")
        if ninja:
            cmd = '{cm} -B "{bd}" -S "{src}" -G Ninja {defs}'.format(
                cm=cmake, bd=bdir, src=src, defs=" ".join(defs))
            if self.run(cmd, ignore_errors=True) == 0:
                self.run('{cm} --build "{bd}" -j 4'.format(cm=cmake, bd=bdir))
                return
            self.output.warning("Ninja configure failed; retrying with the default generator")
            if os.path.isdir(bdir):
                shutil.rmtree(bdir)
        self.run('{cm} -B "{bd}" -S "{src}" {defs}'.format(
            cm=cmake, bd=bdir, src=src, defs=" ".join(defs)))
        self.run('{cm} --build "{bd}" -j1'.format(cm=cmake, bd=bdir))

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
        """Return True if grep_path's --version banner contains 'GNU'."""
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
        """Locate a GNU grep binary (optional; keeps CLI tests on GNU semantics).

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

          * `sqlite3` — host CLI for test_projinfo.sh's PROJ_AUX_DB sub-test.
          * GNU `grep` — CLI tests that rely on GNU grep semantics.
          * `PROJ_TEST_TMPDIR` — absolute writable dir for patch 0003 (HMDFS
            cwd under ctest makes relative sqlite paths fail).

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
                    "host sqlite3 not found; test_projinfo.sh PROJ_AUX_DB may fail"
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
                "prepending {}".format(gnu_dir or "(none)")
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
        self._resign_packaged_elfs()

    def _find_elf_tool(self, prog):
        """Locate an OHOS SDK tool (llvm-objcopy / binary-sign-tool).

        Search order: PATH -> hnp (CI worker) -> the SDK the configured compiler
        came from -> harmonybrew ohos-sdk installs. Never hard-code a host path:
        build nodes differ, and CI signs from /data/service/hnp/bin while a
        harmonybrew SDK keeps the tools under <sdk>/bin and <sdk>/toolchains/lib.
        """
        candidates = [shutil.which(prog) or "", "/data/service/hnp/bin/{}".format(prog)]
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = ce.get("c") or ""
        if cc:
            llvm_bin = os.path.dirname(cc)
            sdk_root = os.path.abspath(os.path.join(llvm_bin, "..", "..", ".."))
            candidates += [
                os.path.join(llvm_bin, prog),
                os.path.join(sdk_root, "bin", prog),
                os.path.join(sdk_root, "toolchains", "lib", prog),
            ]
        for brew_root in ("opt", "Cellar"):
            for sub in ("bin", "toolchains/lib", "native/llvm/bin"):
                candidates += sorted(glob.glob(os.path.join(
                    os.path.expanduser("~"), ".harmonybrew", brew_root,
                    "ohos-sdk@*", *sub.split("/"), prog)))
                candidates += sorted(glob.glob(os.path.join(
                    os.path.expanduser("~"), ".harmonybrew", brew_root,
                    "ohos-sdk@*", "*", sub, prog)))
        for cand in candidates:
            if cand and os.path.isfile(cand):
                return cand
        return None

    def _resign_packaged_elfs(self):
        """Re-sign every packaged ELF per the E077 four-step flow.

        `cmake --install` rewrites DT_RUNPATH in the installed copy, which
        invalidates the .codesign section the toolchain linker stamped into the
        build-tree file. The OHOS kernel then rejects the package: exec gives
        "Operation not permitted", dlopen gives "Permission denied" — even for a
        byte-identical-looking copy, so only re-signing fixes it. Order is
        mandatory: remove the stale section, sign, restore the exec bit (signing
        resets the mode to 750).
        """
        targets = []
        for pat in ("lib/**/*.so", "lib/**/*.so.*", "bin/*"):
            targets += glob.glob(
                os.path.join(self.package_folder, *pat.split("/")), recursive=True)
        elfs = [t for t in dict.fromkeys(targets)
                if os.path.isfile(t) and not os.path.islink(t)]
        if not elfs:
            return
        signer = self._find_elf_tool("binary-sign-tool")
        if not signer:
            raise ConanInvalidConfiguration(
                "打包件需要 binary-sign-tool 重新签名：cmake --install 改写了 DT_RUNPATH，"
                "原 .codesign 失效后 OHOS 内核拒绝加载（Operation not permitted）。"
                "请安装 ohos-sdk 或将 binary-sign-tool 加入 PATH。")
        objcopy = self._find_elf_tool("llvm-objcopy")
        for elf in elfs:
            if objcopy:
                self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(
                    oc=objcopy, f=elf))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(
                sg=signer, f=elf))
            os.chmod(elf, 0o755)
        self.output.info("re-signed {} packaged ELF file(s) with {}".format(
            len(elfs), signer))

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
