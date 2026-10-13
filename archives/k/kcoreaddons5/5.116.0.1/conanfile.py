#!/usr/bin/env python3
"""Conan recipe for kcoreaddons5 5.116.0.1 on HarmonyOS PC.

kcoreaddons (KF5/Qt5) is the KDE Frameworks 5 utility library providing KDE
core add-ons to Qt classes (libKF5CoreAddons.so).

OHOS-specific adaptations (modeled on attica-kf5/5.116.0):
  - KF_IGNORE_PLATFORM_CHECK=TRUE to bypass KDE platform detection (OHOS not
    in KDE platform list)
  - CMAKE_SYSTEM_NAME=Linux: CMake 4.1 has no Platform/HarmonyOS module, so the
    `UNIX` variable is not set and KDE's `if(UNIX)` source selection (kuser_unix,
    kshell_unix, etc.) would silently drop those sources causing undefined
    symbols. OHOS is a POSIX system, so forcing the Linux platform is fully
    compatible and keeps the `_unix.cpp` sources in the build.
  - KDE_INSTALL_USE_QT_SYS_PATHS=OFF: install into kcoreaddons5's own prefix,
    not Qt's.
  - USE_DBUS=OFF: keep the KF5 baseline independent of the Qt DBus split.
  - ecm_install_po_files_as_qm(poqm) disabled via patches/0001-CMakeLists.txt.patch
    because Qt5LinguistTools is not published to ohpcd.
  - src/lib/util/klistopenfilesjob_unix.cpp patched via
    patches/0002-klistopenfilesjob-unix-lsof-fallback.patch: the lsof shipped
    on OHOS images implements no +d directory query (it takes "+d" for a path
    and aborts with "Can't stat +d", listing nothing), so KListOpenFilesJob
    retries against the directory's entries -- the depth-1 search +d describes.
  - BUILD_TESTING=ON (configures the upstream autotests) and build() EXECUTES
    them: after cmake.build() every ctest-registered programme is run and the
    full accounting is printed into the verify log, so the numbers are
    reproducible from the log alone instead of being quoted from an earlier
    exploration run. Platform-limited failures (kusertest has no user/group
    database, kdirwatch hardlink/inotify unavailable, klibexectest's install
    prefix fixture) are reported and classified, NOT hidden and NOT allowed to
    fail `conan create`. Two layers are reported separately and never summed:
    L1 counts programmes (built executables vs ctest registrations vs
    explicitly justified non-tests) and L2 counts the runtime cases each
    programme's QTest "Totals:" line reported. test_package's consumer binary
    is listed separately and is not part of the upstream N.
  - Dependencies: qt5-qtbase/5.15.2 (Qt5Core), ecm/6.20.0 (ECM)
  - ECM_MODULE_PATH set manually because the CMakeDeps-generated ECMConfig
    does not propagate the variable the project's CMakeLists.txt relies on.
  - conan_cmakedeps_paths.cmake created manually because qtbase uses
    cmake_find_mode=none, which prevents CMakeDeps from adding its
    lib/cmake builddir to CMAKE_PREFIX_PATH.
"""
import os
import re
import shutil
import subprocess
import time

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class Kcoreaddons5Conan(ConanFile):
    name = "kcoreaddons5"
    version = "5.116.0.1"
    description = "KDE Frameworks 5 - KDE Core Addons"
    license = "LGPL-2.0-or-later"
    homepage = "https://invent.kde.org/frameworks/kcoreaddons"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)
        # test_shim/identity_shim.c: the getpwuid/getgrgid shim the test
        # environment preloads (see _identity_shim).  Exported with the recipe
        # so the shim is built from the same source revision as the recipe.
        _shim = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_shim")
        if os.path.isdir(_shim):
            _dst = os.path.join(self.export_sources_folder, "test_shim")
            if os.path.isdir(_dst):
                shutil.rmtree(_dst)
            shutil.copytree(_shim, _dst)

    def requirements(self):
        self.requires("qt5-qtbase/5.15.2")

    def build_requirements(self):
        self.tool_requires("ecm/6.20.0")

    def layout(self):
        cmake_layout(self, generator="Ninja")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self, generator="Ninja")
        shared = bool(self.options.shared)
        tc.variables["BUILD_SHARED_LIBS"] = shared
        tc.variables["BUILD_TESTING"] = "ON"
        tc.variables["KF_IGNORE_PLATFORM_CHECK"] = "TRUE"
        tc.variables["KDE_INSTALL_USE_QT_SYS_PATHS"] = "OFF"
        tc.variables["USE_DBUS"] = "OFF"
        tc.variables["BUILD_QCH"] = "OFF"
        # See class docstring: CMake 4.1 lacks Platform/HarmonyOS, so the UNIX
        # platform variable is not set and the _unix.cpp sources get dropped.
        # Force the Linux platform so KDE's `if(UNIX)` source selection keeps
        # kuser_unix.cpp / kshell_unix.cpp / etc. in the build (R32-safe:
        # OHOS is POSIX-compatible, no __OHOS__ macros used anywhere).
        tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        # ...but that also loads the Linux ELF link rules, so CMake gives the
        # build-tree targets a runtime path derived from the libraries they
        # link and then REWRITES it at install time. The rewrite is a relink of
        # an already-signed OHOS binary, so its .codesign no longer matches and
        # the loader refuses the installed copy:
        #   Error loading shared library .../p/lib/libKF5CoreAddons.so.5.116.0: Permission denied
        # The build-tree copy of the same library loads fine; the two differ by
        # 100 bytes of .dynstr, the two runtime-path strings. Every consumer
        # that loads this library from the package at run time is affected.
        # Turning rpath off leaves build tree and install tree in agreement,
        # so CMake has nothing to rewrite and the packaged library stays
        # loadable. Consumers find it through LD_LIBRARY_PATH, which the OHOS
        # loader does honour.
        tc.variables["CMAKE_SKIP_RPATH"] = "ON"

        if str(self.settings.os) == "OHOS":
            # aarch64-linux-ohos target for the OHOS clang toolchain
            targets = {
                "armv8": "aarch64-linux-ohos",
                "x86_64": "x86_64-linux-ohos",
            }
            target = targets.get(str(self.settings.arch))
            if target:
                tc.variables["CMAKE_C_COMPILER_TARGET"] = target
                tc.variables["CMAKE_CXX_COMPILER_TARGET"] = target

        ecm = self.dependencies.build.get("ecm")
        if ecm:
            ecm_share = os.path.join(ecm.package_folder, "share", "ECM")
            tc.variables["ECM_MODULE_PATH"] = ";".join([
                os.path.join(ecm_share, "modules"),
                os.path.join(ecm_share, "find-modules"),
                os.path.join(ecm_share, "kde-modules"),
            ])

        qtbase = self.dependencies.get("qt5-qtbase")
        if qtbase:
            self._prepare_qt_mkspec_compat(qtbase.package_folder)
            qt_pkg = qtbase.package_folder.replace("\\", "/")
            lines = []
            lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{qt_pkg}/lib/cmake")')
            lines.append(f'list(PREPEND CMAKE_LIBRARY_PATH "{qt_pkg}/lib")')
            lines.append(f'list(PREPEND CMAKE_INCLUDE_PATH "{qt_pkg}/include")')
            if ecm:
                ecm_pkg = ecm.package_folder.replace("\\", "/")
                ecm_cmake = os.path.join(ecm_pkg, "share", "ECM", "cmake")
                lines.append(f'list(PREPEND CMAKE_MODULE_PATH "{ecm_cmake}")')
                lines.append(f'list(PREPEND CMAKE_PREFIX_PATH "{ecm_cmake}")')
            lines.append(
                'list(PREPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_LIST_DIR}")'
            )
            lines.append(
                'list(PREPEND CMAKE_PREFIX_PATH "${CMAKE_CURRENT_LIST_DIR}")'
            )
            lines.append("set(CMAKE_FIND_PACKAGE_PREFER_CONFIG ON)")
            lines.append(f'set(CONAN_RUNTIME_LIB_DIRS "{qt_pkg}/lib")')
            paths_file = os.path.join(
                self.generators_folder, "conan_cmakedeps_paths.cmake"
            )
            with open(paths_file, "w", encoding="utf-8") as f:
                f.write("\n".join(lines) + "\n")

        tc.generate()

    @staticmethod
    def _prepare_qt_mkspec_compat(qt_package_folder):
        source = os.path.join(qt_package_folder, "mkspecs")
        expected = os.path.join(
            os.path.dirname(qt_package_folder), "b", "mkspecs"
        )
        if os.path.isdir(source) and not os.path.isdir(expected):
            parent, _ = os.path.split(expected)
            os.makedirs(parent, exist_ok=True)
            import shutil

            shutil.copytree(source, expected)

    def build(self):
        # Platform guard: apply OHOS-specific patches only on OHOS.
        if self.settings.os == "OHOS":
            apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        self._run_upstream_tests()

    # ------------------------------------------------------------------
    # upstream test execution + two-layer accounting
    #
    # BUILD_TESTING=ON only means the autotests were CONFIGURED. The point of
    # running them here is that the resulting log is the evidence: anyone can
    # re-derive both layers from it, rather than trusting a number quoted from
    # a manual exploration session that left no artefact behind.
    # ------------------------------------------------------------------
    # QTest prints exactly one totals line per programme, e.g.
    #   Totals: 41 passed, 4 failed, 0 skipped, 0 blacklisted, 15ms
    # leading whitespace tolerated: a missed totals line would silently
    # downgrade a programme with real counts to "unknown cases"
    _TOTALS_RE = re.compile(
        r"^\s*Totals:\s*(\d+)\s+passed,\s*(\d+)\s+failed,\s*(\d+)\s+skipped",
        re.MULTILINE,
    )
    _TEST_TIMEOUT = 900          # seconds for a single programme
    _SUITE_BUDGET = 3600         # seconds for the whole suite

    # ---- acceptance policy -------------------------------------------------
    # A failing programme does NOT silently pass. Every entry below was written
    # from a real run: the assertion list is the verbatim FAIL! text that run
    # printed, and the probe is re-executed at verdict time, so the excuse has
    # to still be true when it is used. A failure whose text is not listed here
    # -- a new one -- is not excused by a matching programme name.
    _ENV_ALLOWLIST = {
        "kusertest": {
            "why": (
                "the sandbox runs as an anonymous uid that is deliberately "
                "absent from the passwd/group databases, so "
                "KUser(KUser::UseRealUserID) cannot resolve the running user"
            ),
            "probe": "_probe_running_uid_absent",
            "max_failed": 4,
            "assertions": [
                "KUserTest::testKUser() 'user.isValid()' returned FALSE. ()",
                "KUserTest::testKUserGroup() 'group.isValid()' returned FALSE. ()",
                "KUserTest::testKUserId() '!userName.isEmpty()' returned FALSE. ()",
                "KUserTest::testKGroupId() '!groupName.isEmpty()' returned FALSE. ()",
            ],
        },
        "kdirwatch_stat_unittest": {
            "why": "hard links are refused in this environment",
            "probe": "_probe_hardlink_refused",
            "max_failed": 1,
            "assertions": [
                "KDirWatch_UnitTest::testHardlinkChange() "
                "'::link(QFile::encodeName(testFile).constData(), "
                "QFile::encodeName(existingFile).constData()) == 0' "
                "returned FALSE. ()",
            ],
        },
        "kdirwatch_qfswatch_unittest": {
            "why": "hard links are refused in this environment",
            "probe": "_probe_hardlink_refused",
            "max_failed": 1,
            "assertions": [
                "KDirWatch_UnitTest::testHardlinkChange() "
                "'::link(QFile::encodeName(testFile).constData(), "
                "QFile::encodeName(existingFile).constData()) == 0' "
                "returned FALSE. ()",
            ],
        },
    }
    # Baselines from the measured run. A smaller suite, or fewer runtime cases
    # than were actually observed, fails the verification.
    _EXPECTED_REGISTRATIONS = 34
    _MIN_TOTAL_CASES = 524
    # Measured with lsof reachable on the test PATH (what the CI environment
    # exposes): the three lsof cases run and pass, and only the two hard-link
    # cases fail, each excused by its own probe. Where no lsof is on PATH the
    # same suite reports 519 / 2 / 3 -- there the three lsof cases are upstream
    # QSKIPs. Both states are real; these are the CI-equivalent numbers.
    _TOTALS_DOCUMENTED = {"passed": 522, "failed": 2, "skipped": 0}

    # Things that must never silently pass, whatever the allowlist says.
    _FATAL_STATUSES = ("FAIL", "NOT_RUN", "UNKNOWN_CASES")

    _FAIL_LINE_RE = re.compile(r"^\s*FAIL!\s+:\s*(?P<body>.+?)\s*$", re.MULTILINE)

    def _test_env(self):
        """Environment in which the freshly built test programmes can run."""
        env = dict(os.environ)
        paths = []
        for candidate in (os.path.join(self.build_folder, "lib"),
                          os.path.join(self.build_folder, "bin")):
            if os.path.isdir(candidate):
                paths.append(candidate)
        qtbase = self.dependencies.get("qt5-qtbase")
        if qtbase:
            paths.append(os.path.join(qtbase.package_folder, "lib"))
        existing = env.get("LD_LIBRARY_PATH")
        if existing:
            paths.append(existing)
        env["LD_LIBRARY_PATH"] = os.pathsep.join(paths)
        env.setdefault("QT_QPA_PLATFORM", "offscreen")
        # The CI gate and an interactive device shell both run with /system/bin
        # in PATH (the image keeps its tools there); the farm's controlled
        # build PATH does not. Append it when present so the suite resolves
        # the same system tools -- lsof in particular -- from every harness,
        # instead of the gate and a local verify disagreeing on whether lsof
        # exists at all.
        system_bin = "/system/bin"
        path_env = env.get("PATH", "")
        if os.path.isdir(system_bin) \
                and system_bin not in path_env.split(os.pathsep):
            env["PATH"] = path_env + os.pathsep + system_bin if path_env \
                else system_bin
        shim = self._identity_shim()
        if shim:
            env["LD_PRELOAD"] = shim
        return env

    def _identity_shim(self):
        """Build (once) the getpwuid/getgrgid shim for the sandbox uid.

        /etc/passwd has 392 entries but none for the uid this session runs as
        (20020101) nor for its gid, so getpwuid()/getgrgid() return NULL and
        kusertest's user.isValid()/group.isValid()/name assertions fail.  That
        is missing identity *data*, not a library defect; the shim answers the
        lookups about the process's own uid/gid and leaves every other lookup
        to libc (dbus recipe precedent: libnopw.so).
        """
        src = os.path.join(self.source_folder, "test_shim", "identity_shim.c")
        if not os.path.isfile(src):
            return None
        so = os.path.join(self.build_folder, "identity_shim.so")
        if not os.path.isfile(so):
            compilers = self.conf.get("tools.build:compiler_executables",
                                      default={}, check_type=dict)
            cc = compilers.get("c", "clang") if compilers else "clang"
            self.run('%s -shared -fPIC -o "%s" "%s"' % (cc, so, src))
        return so

    # add_test(<name> <command> [args...]) with the name in any of the four
    # forms CMake emits; the remainder up to the closing paren is the command.
    _ADD_TEST_RE = re.compile(
        r"^\s*add_test\(\s*"
        r"(?:\[=\[(?P<bracket>.*?)\]=]|\[\[(?P<bracket2>.*?)\]\]|"
        r"\"(?P<quoted>[^\"]*)\"|(?P<bare>[^\s)]+))"
        r"(?P<rest>.*)\)\s*$"
    )
    _ADD_TEST_NAMED_RE = re.compile(
        r"^\s*add_test\(\s*NAME\s+(?P<name>\S+)\s+COMMAND\s+(?P<cmd>.+?)\s*\)\s*$"
    )

    def _ctest_listing(self):
        """[(name, command)] for every ctest-registered test, whole build tree.

        Parsed straight out of the generated CTestTestfile.cmake instead of
        shelling out to `ctest -N -V`. The first attempt shelled out and got
        nothing back, which surfaced as "0 programmes" -- an empty layer that
        is indistinguishable from a missing tool, the exact confusion this
        accounting exists to prevent.

        Every CTestTestfile.cmake in the build tree is read, at any depth: a
        depth limit would silently drop the registrations of any test that
        lives deeper than the limit, which is the same class of bug.

        A listing that comes back empty, a file that cannot be read, or a
        file that yields no add_test at all while claiming to be a test file,
        all raise: an incomplete programme layer must stop the verification,
        not be reported as a clean zero.
        """
        tests, seen = [], set()
        unreadable, files = [], 0
        root = self.build_folder
        for dirpath, _dirnames, filenames in os.walk(root):
            if "CTestTestfile.cmake" not in filenames:
                continue
            files += 1
            path = os.path.join(dirpath, "CTestTestfile.cmake")
            try:
                with open(path, encoding="utf-8", errors="replace") as fh:
                    content = fh.read()
            except OSError as exc:
                unreadable.append(f"{path}: {exc}")
                continue
            for raw in content.splitlines():
                named = self._ADD_TEST_NAMED_RE.match(raw)
                if named:
                    name, command = named.group("name"), named.group("cmd")
                else:
                    plain = self._ADD_TEST_RE.match(raw)
                    if not plain:
                        continue
                    name = (plain.group("bracket") or plain.group("bracket2")
                            or plain.group("quoted") or plain.group("bare"))
                    command = plain.group("rest").strip()
                if not name or not command or name in seen:
                    continue
                seen.add(name)
                tests.append((name, command))
        self._ctest_files_seen = files

        if unreadable:
            raise ConanException(
                "[upstream] cannot read "
                f"{len(unreadable)} CTestTestfile.cmake file(s): "
                + "; ".join(unreadable[:5])
            )
        if files and not tests:
            raise ConanException(
                f"[upstream] {files} CTestTestfile.cmake file(s) found but not a "
                "single add_test parsed: the discovery parser is broken or the "
                "file format changed. Refusing to report an empty programme layer."
            )
        if not tests:
            raise ConanException(
                "[upstream] no CTestTestfile.cmake under the build tree: "
                "BUILD_TESTING did not register any test, so nothing can be "
                "verified. Refusing to report an empty programme layer."
            )
        if self._EXPECTED_REGISTRATIONS is not None \
                and len(tests) != self._EXPECTED_REGISTRATIONS:
            raise ConanException(
                f"[upstream] {len(tests)} ctest registrations but "
                f"{self._EXPECTED_REGISTRATIONS} expected: the suite changed size."
            )
        return tests

    @staticmethod
    def _command_executable(command):
        """First token of a CTest command line, quotes and args removed.

        add_test writes a quoted absolute path and may add arguments, so the
        raw string cannot be used as a filename: shlex turns
        `"/build/bin/x" "--exe" "/build/bin/y"` into the path that exists.
        """
        import shlex as _shlex

        try:
            parts = _shlex.split(command)
        except ValueError:
            parts = command.split()
        return parts[0] if parts else ""

    @staticmethod
    def _is_executable_programme(path):
        """True for an ELF executable, False for a shared object.

        Plugins such as qtplugin.so carry the executable bit and, being PIE,
        are ET_DYN exactly like the test programmes, so permissions and the ELF
        type cannot separate them -- a first attempt counted three .so files as
        built test programmes. A program interpreter (PT_INTERP) is the thing
        only a runnable programme has.
        """
        try:
            with open(path, "rb") as fh:
                data = fh.read(65536)
        except OSError:
            return False
        if len(data) < 64 or data[:4] != b"\x7fELF" or data[4] != 2:
            return False
        endian = "little" if data[5] == 1 else "big"
        e_phoff = int.from_bytes(data[32:40], endian)
        e_phentsize = int.from_bytes(data[54:56], endian)
        e_phnum = int.from_bytes(data[56:58], endian)
        if e_phentsize <= 0:
            return False
        for index in range(e_phnum):
            offset = e_phoff + index * e_phentsize
            if offset + 4 > len(data):
                return False          # headers past the read window: not a
            if int.from_bytes(data[offset:offset + 4], endian) == 3:
                return True           # PT_INTERP
        return False

    def _built_executables(self):
        """Runnable programmes the build produced, by basename.

        KDE links the autotests into <build>/bin, which is also where ctest's
        commands point, so a bounded look there is both sufficient and cheap on
        the I/O-tight device. Anything found that ctest does not register has
        to be justified below, which is the whole point of counting it.
        """
        found = {}
        bindir = os.path.join(self.build_folder, "bin")
        try:
            entries = sorted(os.listdir(bindir))
        except OSError:
            return found
        for entry in entries:
            path = os.path.join(bindir, entry)
            if os.path.isfile(path) and os.access(path, os.X_OK) \
                    and self._is_executable_programme(path):
                found[entry] = path
        return found

    def _run_one(self, name, command, env, budget_left):
        """Run one programme.

        Returns (status, passed, failed, skipped, note, details). status is one
        of PASS / FAIL / SKIP / NOT_RUN / UNKNOWN_CASES -- never a guess: a
        programme whose output carries no Totals line is reported as UNKNOWN
        cases rather than being credited with a pass rate it did not produce,
        and it stays in the denominator.

        details carries the verbatim FAIL! lines, so a failure is justified by
        the assertion text that produced it instead of by a bare count.
        """
        def no_run(reason):
            return ("NOT_RUN", 0, 0, 0, reason, [])

        if budget_left <= 0:
            return no_run("suite time budget exhausted")
        import shlex as _shlex

        try:
            argv = _shlex.split(command)
        except ValueError:
            argv = command.split()
        exe = argv[0] if argv else ""
        if not exe or not os.path.exists(exe):
            return no_run(f"executable not found: {exe or '<empty>'}")
        timeout = min(self._TEST_TIMEOUT, int(budget_left))
        try:
            # run the full argv: some programmes are given arguments by
            # add_test (e.g. desktoptojsontest is handed the tool to invoke)
            proc = subprocess.run(
                argv, cwd=os.path.dirname(exe), env=env,
                capture_output=True, text=True, timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            return no_run(f"timed out after {timeout}s")
        except OSError as exc:
            return no_run(f"could not start: {exc}")
        out = (proc.stdout or "") + (proc.stderr or "")
        details = [m.group("body") for m in self._FAIL_LINE_RE.finditer(out)]
        match = self._TOTALS_RE.search(out)
        if not match:
            # a loader refusal (missing .so, bad .codesign) lands here: no
            # QTest output at all, which is a failure, not an unknown
            loader = [ln for ln in out.splitlines()
                      if "Error loading shared library" in ln
                      or "symbol not found" in ln]
            if loader:
                return ("UNKNOWN_CASES", 0, 0, 0,
                        f"could not load: {loader[0].strip()[:80]}", details)
            return ("UNKNOWN_CASES", 0, 0, 0,
                    f"no Totals line (rc={proc.returncode})", details)
        passed, failed, skipped = (int(g) for g in match.groups())
        if failed:
            return ("FAIL", passed, failed, skipped,
                    f"rc={proc.returncode}", details)
        if passed == 0 and skipped:
            return ("SKIP", passed, failed, skipped, f"rc={proc.returncode}",
                    details)
        return ("PASS", passed, failed, skipped, f"rc={proc.returncode}", details)

    # ------------------------------------------------------------------
    # evidence: environment probes and unregistered-programme classification
    # ------------------------------------------------------------------
    def _environment_probes(self, env):
        """Record the environment facts a platform exception would cite.

        These run unconditionally and land in the log, so any future allowlist
        entry can point at evidence that was actually collected rather than at
        a claim made in a comment. The lsof probe resolves through the test
        environment's PATH -- the same PATH the programmes get -- so the probe
        and the suite can never disagree on which lsof (if any) is in play.
        """
        probes = []
        try:
            with open("/etc/passwd", encoding="utf-8", errors="replace") as fh:
                passwd = fh.read().strip()
            probes.append(("user/group database",
                           f"/etc/passwd readable, {len(passwd.splitlines())} lines"
                           if passwd else "/etc/passwd is EMPTY"))
        except OSError as exc:
            probes.append(("user/group database", f"/etc/passwd unreadable: {exc}"))
        lsof = None
        try:
            import shutil as _shutil

            lsof = _shutil.which("lsof", path=env.get("PATH"))
            probes.append(("lsof", lsof or "NOT INSTALLED"))
        except Exception as exc:                      # pragma: no cover
            probes.append(("lsof", f"probe failed: {exc}"))
        if lsof:
            # Some image builds ship a reduced lsof without the +d directory
            # query: it takes "+d" for a file name, aborts with "Can't stat +d"
            # and lists nothing. Patch 0002 answers that by querying the
            # directory's entries instead; record which behaviour this machine
            # shows, so the log states why the fallback did or did not engage.
            lsof_dir = os.path.join(self.build_folder, "upstream-probe-lsof")
            try:
                os.makedirs(lsof_dir, exist_ok=True)
                proc = subprocess.run([lsof, "-t", "+d", lsof_dir],
                                      capture_output=True, text=True, timeout=60)
                err = (proc.stderr or "").strip().splitlines()
                reduced = bool(err) and "+d" in err[0]
                probes.append(("lsof +d support",
                               f"no: {err[0][:70]}" if reduced
                               else "yes (directory query understood)"))
            except (OSError, subprocess.SubprocessError) as exc:
                probes.append(("lsof +d support", f"probe failed: {exc}"))
        probe_dir = os.path.join(self.build_folder, "upstream-probe")
        try:
            os.makedirs(probe_dir, exist_ok=True)
            src = os.path.join(probe_dir, "a")
            dst = os.path.join(probe_dir, "b")
            with open(src, "w") as fh:
                fh.write("x")
            if os.path.exists(dst):
                os.unlink(dst)
            os.link(src, dst)
            probes.append(("hard links", "supported in the build tree"))
        except OSError as exc:
            probes.append(("hard links", f"NOT supported: {exc}"))
        watches = "/proc/sys/fs/inotify/max_user_watches"
        if os.path.exists(watches):
            try:
                with open(watches) as fh:
                    probes.append(("inotify", f"max_user_watches={fh.read().strip()}"))
            except OSError as exc:
                probes.append(("inotify", f"unreadable: {exc}"))
        else:
            probes.append(("inotify", "NO inotify support (no "
                                      "/proc/sys/fs/inotify)"))
        return probes

    def _target_build_dir(self, name):
        """Build directory that produced a target, from CMakeFiles/<name>.dir."""
        for dirpath, dirnames, _files in os.walk(self.build_folder):
            if name + ".dir" in dirnames and os.path.basename(dirpath) == "CMakeFiles":
                return os.path.dirname(dirpath)
        return None

    def _classify_unregistered(self, name):
        """(category, evidence) for a built programme ctest does not register.

        Nothing is waved through by name alone: the category is derived from
        where the build produced the target and from the target's own name, and
        either way the evidence is printed. A programme that fits no category
        is reported as UNCLASSIFIED and fails the verification -- an unavowed
        binary in the programme layer is exactly what this layer is for.
        """
        target_dir = self._target_build_dir(name)
        where = target_dir or "<target dir not found>"
        if "test_package" in (target_dir or ""):
            return "test_package consumer", where
        lowered = name.lower()
        if "benchmark" in lowered:
            return "upstream benchmark (not a registered test)", where
        if lowered.endswith("_helper") or "helper" in lowered:
            return "helper programme invoked by another test", where
        if target_dir and os.path.basename(target_dir).lower() != "autotests":
            return "build-time tool (not a test)", where
        return "UNCLASSIFIED", where

    def _run_upstream_tests(self):
        env = self._test_env()
        tests = self._ctest_listing()          # raises if the layer is unusable
        built = self._built_executables()
        registered = {name for name, _ in tests}
        unregistered = sorted(set(built) - registered)

        self.output.info("=" * 62)
        self.output.info("[upstream] L1 programme layer")
        self.output.info(f"[upstream]   ctest test files parsed    : "
                         f"{getattr(self, '_ctest_files_seen', 0)}")
        self.output.info(f"[upstream]   built executable files      : {len(built)}")
        self.output.info(f"[upstream]   ctest registrations         : {len(tests)}")
        self.output.info(
            f"[upstream]   built but not registered   : {len(unregistered)}"
        )
        unclassified = []
        for entry in unregistered:
            category, where = self._classify_unregistered(entry)
            if category == "UNCLASSIFIED":
                unclassified.append(entry)
            self.output.info(
                f"[upstream]     - {entry:<34} {category:<44} {where}"
            )
        listed = {os.path.basename(self._command_executable(cmd))
                  for _, cmd in tests if cmd}
        missing = sorted(listed - set(built))
        self.output.info(
            f"[upstream]   registered but not in bin : {len(missing)}"
        )
        for entry in missing:
            self.output.info(f"[upstream]     - {entry}")

        self.output.info("[upstream] L2 runtime case layer")
        counts = {"PASS": 0, "FAIL": 0, "SKIP": 0, "NOT_RUN": 0, "UNKNOWN_CASES": 0}
        totals = {"passed": 0, "failed": 0, "skipped": 0}
        budget = float(self._SUITE_BUDGET)
        ran = 0
        self._rows = {}
        for name, command in tests:
            started = time.monotonic()
            status, passed, failed, skipped, note, details = self._run_one(
                name, command, env, budget
            )
            budget -= time.monotonic() - started
            self._rows[name] = {
                "status": status, "passed": passed, "failed": failed,
                "skipped": skipped, "note": note, "details": details,
            }
            counts[status] += 1
            totals["passed"] += passed
            totals["failed"] += failed
            totals["skipped"] += skipped
            ran += 1
            cases = f"{passed}p/{failed}f/{skipped}s" if status != "NOT_RUN" else "-"
            self.output.info(
                f"[upstream]   {status:<13} {name:<38} {cases:<14} {note}"
            )
            for text in details:
                self.output.info(f"[upstream]       ! {text}")

        self.output.info("[upstream] ---- environment probes ----")
        for label, value in self._environment_probes(env):
            self.output.info(f"[upstream]   {label:<22} {value}")

        self.output.info("[upstream] ---- summary ----")
        self.output.info(
            "[upstream] L1 programmes: "
            + " ".join(f"{k}={v}" for k, v in sorted(counts.items()))
            + f" total={len(tests)}"
        )
        self.output.info(
            f"[upstream] L1 verdict sum {sum(counts.values())} == "
            f"registrations {len(tests)}; run queue {ran}"
        )
        self.output.info(
            "[upstream] L2 cases: "
            f"passed={totals['passed']} failed={totals['failed']} "
            f"skipped={totals['skipped']}"
        )
        unknown = counts["UNKNOWN_CASES"]
        if unknown:
            self.output.info(
                f"[upstream] {unknown} programme(s) produced no Totals line: "
                "their case counts are not known and are NOT counted as passes."
            )
        if self._TOTALS_DOCUMENTED:
            doc = self._TOTALS_DOCUMENTED
            self.output.info(
                "[upstream] L2 documented baseline: "
                f"passed={doc['passed']} failed={doc['failed']} "
                f"skipped={doc['skipped']} "
                f"(registrations={self._EXPECTED_REGISTRATIONS}, "
                f"min cases={self._MIN_TOTAL_CASES})"
            )
        self.output.info(
            "[upstream] test_package consumer is a separate link-level smoke "
            "check and is not part of the upstream N above."
        )
        self.output.info("=" * 62)

        self._upstream_verdict(tests, counts, totals, missing, unclassified)

    def _upstream_verdict(self, tests, counts, totals, missing, unclassified):
        """Fail the verification unless every anomaly is precisely excused.

        An empty or short programme layer, a registration with no executable,
        an unclassifiable binary, a programme that failed, never ran, or
        produced no Totals line -- each one fails the build unless its own
        allowlist entry exists AND that entry's environment probe is satisfied
        AND the programme's failing assertions are the recorded ones. There is
        no blanket "platform failures do not count" rule.
        """
        problems = []
        if not tests:
            problems.append("programme layer is empty")
        if sum(counts.values()) != len(tests):
            problems.append(
                f"verdicts {sum(counts.values())} != registrations {len(tests)}"
            )
        for name in missing:
            problems.append(f"registered test has no executable: {name}")
        for name in unclassified:
            problems.append(f"built programme fits no category: {name}")
        if self._MIN_TOTAL_CASES is not None:
            measured = totals["passed"] + totals["failed"] + totals["skipped"]
            if measured < self._MIN_TOTAL_CASES:
                problems.append(
                    f"runtime cases fell to {measured}, below the recorded "
                    f"baseline {self._MIN_TOTAL_CASES}"
                )

        # per-programme: anything not PASS/SKIP must be excused explicitly
        excused = []
        for name, row in sorted(getattr(self, "_rows", {}).items()):
            status = row["status"]
            if status in ("PASS", "SKIP"):
                continue
            entry = self._ENV_ALLOWLIST.get(name)
            if entry is None:
                problems.append(
                    f"{name}: {status} ({row['note']}) -- not excused by any "
                    "allowlist entry"
                )
                continue
            probe_ok, probe_note = self._allowlist_probe_satisfied(entry)
            if not probe_ok:
                problems.append(
                    f"{name}: excused only if {entry['why']}, but the probe "
                    f"does not support it ({probe_note})"
                )
                continue
            if status == "FAIL" and row["failed"] > entry.get("max_failed", 0):
                problems.append(
                    f"{name}: {row['failed']} failing cases exceed the recorded "
                    f"{entry.get('max_failed', 0)}"
                )
                continue
            # the assertion text must be the recorded one: a matching
            # programme name must not excuse a failure that has changed
            allowed = set(entry.get("assertions", []))
            unseen = [text for text in row["details"] if text not in allowed]
            if unseen:
                problems.append(
                    f"{name}: failure text not in the recorded evidence: "
                    + "; ".join(unseen[:3])
                )
                continue
            if status == "FAIL" and len(row["details"]) < row["failed"]:
                problems.append(
                    f"{name}: {row['failed']} failing cases but only "
                    f"{len(row['details'])} assertion line(s) captured"
                )
                continue
            excused.append(f"{name}={status} ({entry['why']})")

        for line in excused:
            self.output.info(f"[upstream] excused: {line}")
        if problems:
            raise ConanException(
                "[upstream] verification FAILED against the upstream suite:\n  - "
                + "\n  - ".join(problems)
            )
        self.output.info(
            "[upstream] all programme verdicts accounted for; no unexcused "
            "failure, non-run or unknown-case programme."
        )

    def _probe_running_uid_absent(self):
        """True when the running uid is not in the passwd database.

        Measured on this device: /etc/passwd holds 391 real entries and
        pwd.getpwnam('root') resolves, so "there is no user database" would be
        false. What is true is narrower -- the sandbox runs as uid 20020101,
        which the image deliberately leaves out, so getpwuid on the running uid
        fails and KUser(UseRealUserID) is invalid by construction.
        """
        uid = os.getuid()
        try:
            with open("/etc/passwd", encoding="utf-8", errors="replace") as fh:
                entries = fh.read()
        except OSError as exc:
            return False, f"/etc/passwd unreadable, cannot decide: {exc}"
        present = any(
            line.split(":")[2:3] == [str(uid)]
            for line in entries.splitlines() if line.count(":") >= 6
        )
        if present:
            return False, f"uid {uid} IS in /etc/passwd; the excuse does not hold"
        return True, (f"uid {uid} absent from /etc/passwd "
                      f"({len(entries.splitlines())} entries)")

    def _probe_hardlink_refused(self):
        """True when creating a hard link in the build tree is refused."""
        probe_dir = os.path.join(self.build_folder, "upstream-probe-link")
        try:
            os.makedirs(probe_dir, exist_ok=True)
            src = os.path.join(probe_dir, "a")
            dst = os.path.join(probe_dir, "b")
            with open(src, "w") as fh:
                fh.write("x")
            if os.path.exists(dst):
                os.unlink(dst)
            os.link(src, dst)
        except OSError as exc:
            return True, f"hard link refused: {exc}"
        return False, "hard link SUCCEEDED; the excuse does not hold"

    def _allowlist_probe_satisfied(self, entry):
        """Re-run the entry's probe and say whether the limitation is present."""
        probe = entry.get("probe")
        if not probe:
            return False, "entry carries no environment probe"
        # probes are named methods on this recipe, so an excuse is backed by
        # code that runs against the very machine being judged
        if isinstance(probe, str):
            func = getattr(self, probe, None)
            if func is None:
                return False, f"probe {probe} is not defined"
            try:
                ok, note = func()
            except Exception as exc:                  # noqa: BLE001
                return False, f"probe {probe} raised: {exc}"
            return bool(ok), f"{probe}: {note}"
        try:
            proc = subprocess.run(probe, capture_output=True, text=True,
                                  timeout=60)
        except (OSError, subprocess.SubprocessError) as exc:
            return False, f"probe could not run: {exc}"
        want = entry.get("probe_expect")
        if want == "missing":
            # absence means the probe FAILED, not that it succeeded quietly:
            # accepting rc=0 with empty output would let a probe that proves
            # nothing excuse a real failure
            ok = proc.returncode != 0
        elif want == "empty_output":
            ok = proc.returncode == 0 and not proc.stdout.strip()
        else:
            ok = proc.returncode == 0
        return ok, f"probe rc={proc.returncode} out={proc.stdout.strip()[:60]!r}"

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]
        self.cpp_info.libs = ["KF5CoreAddons"]
        # KF5CoreAddons depends on Qt5Core and is usually an additional dep of
        # other KF5 libs; let the installed KF5CoreAddonsConfig.cmake drive the
        # Qt5::Core find_dependency automatically.
        self.cpp_info.requires = []
