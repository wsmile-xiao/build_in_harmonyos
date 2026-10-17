#!/usr/bin/env python3
"""Conan recipe for qt5-qtwebsockets 5.15.2 on OpenHarmony PC.

Qt5 WebSockets module (QtWebSockets, RFC 6455) built with qmake from the
qt5-qtbase package.  Follows the established qt5-qtcharts/qtmultimedia
pattern: a private writable Qt prefix mirrors qtbase (symlinks + rewritten
mkspecs), qmake builds from it, and `make install` stages into an
INSTALL_ROOT inside the build folder before relocation into the package.

Upstream auto tests (tests/auto/websockets — 9 QTest suites / 67 test
functions / 7322 data cases) are built and executed inside build() over the
127.0.0.1 loopback on the OHOS host:
  * the mirror mkspecs flips `private_tests` on so the 6 private test
    directories (websocketprotocol / dataprocessor / websocketframe /
    handshakerequest / handshakeresponse / qdefaultmaskgenerator) are
    entered by websockets.pro;
  * `reduce_exports` is MOVED to disabled_features in the mirror (Qt
    developer-build equivalent) so private classes (QWebSocketFrame,
    QWebSocketHandshakeRequest/Response, QDefaultMaskGenerator,
    QWebSocketProtocol helpers) are exported and the private tests link
    against the single library build;
  * module .pri files not owned by qtbase (contamination left in a locally
    cached qtbase package by sibling Qt5 module builds) are pruned so the
    build stays closed on the declared dependency set;
  * tst_* executables are signed with binary-sign-tool before execution;
  * `make check -k` runs all suites; the run log is parsed and every failed
    case must belong to the documented environment-limited allowlist
    (tst_QWebSocket::tst_errorString — the build environment's DNS answers
    arbitrary hostnames with a fake IP, so the expected HostNotFoundError
    never occurs).  Any other failure, or a missing suite summary, fails
    the build — no silent tolerance.
"""
import os
import re
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.files import get
from conan.tools.layout import basic_layout


class Qt5QtwebsocketsConan(ConanFile):
    name = "qt5-qtwebsockets"
    version = "5.15.2"
    description = "Qt5 WebSockets module (QtWebSockets) for OpenHarmony"
    license = "LGPL-3.0"
    homepage = "https://www.qt.io/"
    url = ""

    settings = "os", "compiler", "build_type", "arch"
    package_type = "shared-library"

    # Upstream suites expected in the check log (websockets.pro SUBDIRS with
    # private_tests enabled): 9 QTest binaries.
    _EXPECTED_SUITES = 9
    # Environment-limited failures, documented in notes.md.  Keyed as
    # (suite_class, test_function).
    _ALLOWED_FAILURES = {("tst_QWebSocket", "tst_errorString")}

    # Stale build-dir references inside the cached qtbase mkspecs, e.g.
    # /home/.../.conan2/p/b/qt5f140ab856c797/b or
    # /home/.../.cache/conan2/p/b/qt552e5077fd769e/b
    _BUILD_DIR_PATTERN = re.compile(
        r"(/[^\s\"]*/(?:\.cache/)?\.?conan2/p/b/qt[0-9a-zA-Z-]+/b)"
    )
    # Any conan2 cache path (used to detect foreign .pri files)
    _CONAN_PATH_PATTERN = re.compile(r"(/[^\s\"]*/(?:\.cache/)?\.?conan2/p/[^\s\"]+)")

    def layout(self):
        basic_layout(self)

    def requirements(self):
        self.requires("qt5-qtbase/5.15.2.2")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} only supports Linux and OHOS, got {self.settings.os}"
            )

    def source(self):
        # R39: conandata ships the single official URL.  The CI pre-download
        # step may rewrite it into a mirror list, so accept both shapes.
        source_data = self.conan_data["sources"][self.version]
        urls = source_data["url"]
        if isinstance(urls, str):
            urls = [urls]
        for url in urls:
            try:
                get(self, url=url, sha256=source_data.get("sha256", ""), strip_root=True)
                return
            except ConanException as error:  # noqa: BLE001
                self.output.warning(f"Failed to download source from {url}: {error}")
        raise ConanInvalidConfiguration("Unable to download source from all mirrors")

    # ── private writable Qt prefix mirroring qtbase ────────────────────

    def _prepare_mkspecs(self, mkspecs_dir, qtbase_pkg):
        # 1) Redirect stale build-dir references to the qtbase package folder
        for modules_dir_name in ("modules", "modules-inst"):
            modules_dir = os.path.join(mkspecs_dir, modules_dir_name)
            if not os.path.isdir(modules_dir):
                continue
            for pri_file in os.listdir(modules_dir):
                if not pri_file.endswith(".pri"):
                    continue
                pri_path = os.path.join(modules_dir, pri_file)
                with open(pri_path, "r", encoding="utf-8") as f:
                    content = f.read()
                fixed = self._BUILD_DIR_PATTERN.sub(qtbase_pkg, content)
                if fixed != content:
                    with open(pri_path, "w", encoding="utf-8") as f:
                        f.write(fixed)

        # 2) Flip private_tests on / reduce_exports off (developer-build
        #    style) so the upstream private test suites are entered and can
        #    link the private classes.  Features must be MOVED between the
        #    enabled/disabled lists — deleting a name makes qtConfig() abort
        #    with "Could not find feature <name>".
        qmodule = os.path.join(mkspecs_dir, "qmodule.pri")
        if os.path.isfile(qmodule):
            with open(qmodule, "r", encoding="utf-8") as f:
                content = f.read()
            enabled = re.search(
                r"QT\.global_private\.enabled_features = ([^\n]*)", content
            )
            disabled = re.search(
                r"QT\.global_private\.disabled_features = ([^\n]*)", content
            )
            if enabled and disabled:
                en = [w for w in enabled.group(1).split() if w != "reduce_exports"]
                dis = [w for w in disabled.group(1).split() if w != "private_tests"]
                if "private_tests" not in en:
                    en.insert(0, "private_tests")
                if "reduce_exports" not in dis:
                    dis.insert(0, "reduce_exports")
                content = (
                    content[: enabled.start(1)]
                    + " ".join(en)
                    + content[enabled.end(1):]
                )
                disabled = re.search(
                    r"QT\.global_private\.disabled_features = ([^\n]*)", content
                )
                content = (
                    content[: disabled.start(1)]
                    + " ".join(dis)
                    + content[disabled.end(1):]
                )
                with open(qmodule, "w", encoding="utf-8") as f:
                    f.write(content)

        # 3) Prune foreign module .pri files: a locally cached qtbase package
        #    can be contaminated by sibling Qt5 module builds (qt_lib_qml*.pri,
        #    qt_lib_quick*.pri, ... pointing at other conan cache folders).
        #    They are not part of the declared dependency set and would make
        #    qtHaveModule(quick) true (pulling undeclared link lines) or break
        #    the build on paths that do not exist.  On a pristine qtbase
        #    package (fresh CI download) this pass is a no-op.
        pruned = []
        for modules_dir_name in ("modules", "modules-inst"):
            modules_dir = os.path.join(mkspecs_dir, modules_dir_name)
            if not os.path.isdir(modules_dir):
                continue
            for pri_file in sorted(os.listdir(modules_dir)):
                if not pri_file.endswith(".pri"):
                    continue
                pri_path = os.path.join(modules_dir, pri_file)
                with open(pri_path, "r", encoding="utf-8") as f:
                    content = f.read()
                foreign = any(
                    not match.group(1).startswith(qtbase_pkg)
                    for match in self._CONAN_PATH_PATTERN.finditer(content)
                )
                if foreign:
                    os.remove(pri_path)
                    pruned.append(f"{modules_dir_name}/{pri_file}")
        if pruned:
            self.output.info(
                "pruned %d foreign module pri files (not owned by qt5-qtbase): %s"
                % (len(pruned), ", ".join(pruned))
            )

    def _build_qt_tree(self, qtbase_pkg):
        qt_root = os.path.join(self.build_folder, "qt-prefix")
        if os.path.isdir(qt_root):
            shutil.rmtree(qt_root)
        os.makedirs(qt_root)
        for entry in os.listdir(qtbase_pkg):
            if entry in ("bin", "mkspecs"):
                continue
            os.symlink(os.path.join(qtbase_pkg, entry), os.path.join(qt_root, entry))
        bin_src = os.path.join(qtbase_pkg, "bin")
        bin_dst = os.path.join(qt_root, "bin")
        os.makedirs(bin_dst)
        for entry in os.listdir(bin_src):
            if entry == "qt.conf":
                continue
            os.symlink(os.path.join(bin_src, entry), os.path.join(bin_dst, entry))
        with open(os.path.join(bin_dst, "qt.conf"), "w", encoding="utf-8") as f:
            f.write(
                "[EffectivePaths]\n"
                "Prefix=..\n"
                "[DevicePaths]\n"
                f"Prefix={qt_root}\n"
                "[Paths]\n"
                f"Prefix={qt_root}\n"
                f"HostPrefix={qt_root}\n"
                "Sysroot=\n"
                "SysrootifyPrefix=false\n"
                "TargetSpec=linux-clang\n"
                "HostSpec=linux-clang\n"
            )
        mkspecs_dst = os.path.join(qt_root, "mkspecs")
        shutil.copytree(
            os.path.join(qtbase_pkg, "mkspecs"), mkspecs_dst, symlinks=True
        )
        self._prepare_mkspecs(mkspecs_dst, qtbase_pkg)
        return qt_root

    def _qmake_env(self, qt_root, qtbase_pkg):
        build_env = Environment()
        build_env.define("QTDIR", qt_root)
        build_env.prepend_path("PATH", os.path.join(qt_root, "bin"))
        build_env.append("LD_LIBRARY_PATH", os.path.join(qtbase_pkg, "lib"))
        return build_env

    # ── OHOS ELF signing ────────────────────────────────────────────────

    def _sign_tools(self):
        objcopy = os.environ.get(
            "OHOS_LLVM_OBJCOPY", "/data/service/hnp/bin/llvm-objcopy"
        )
        signer = os.environ.get(
            "OHOS_BINARY_SIGN_TOOL", "/data/service/hnp/bin/binary-sign-tool"
        )
        if os.path.isfile(objcopy) and os.path.isfile(signer):
            return objcopy, signer
        return None, None

    def _sign_test_binaries(self, tests_dir):
        """Sign the built tst_* executables before running them (coinutils
        precedent: unsigned OHOS ELFs may be rejected by the target runtime)."""
        objcopy, signer = self._sign_tools()
        if not signer:
            self.output.warning(
                "binary-sign-tool not found — upstream tests will run unsigned"
            )
            return
        for root, _dirs, files in os.walk(tests_dir):
            for name in files:
                if not name.startswith("tst_"):
                    continue
                path = os.path.join(root, name)
                if os.path.islink(path) or not os.access(path, os.X_OK):
                    continue
                self.run(
                    '{0} --remove-section .codesign "{1}" 2>/dev/null || true'.format(
                        objcopy, path
                    )
                )
                self.run(
                    '{0} sign -inFile "{1}" -outFile "{1}" -selfSign 1'.format(
                        signer, path
                    )
                )

    def _sign_shared_objects(self):
        """Sign packaged OHOS ELF shared objects with the target's native
        signer (qrencode pattern)."""
        objcopy, signer = self._sign_tools()
        if not signer:
            self.output.warning(
                "binary-sign-tool not found — packaged libraries left unsigned"
            )
            return
        libdir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(libdir):
            return
        for root, _dirs, files in os.walk(libdir):
            for name in files:
                if not (name.endswith(".so") or ".so." in name):
                    continue
                path = os.path.join(root, name)
                if os.path.islink(path):
                    continue
                self.run(
                    '{0} --remove-section .codesign "{1}" 2>/dev/null || true'.format(
                        objcopy, path
                    )
                )
                self.run(
                    '{0} sign -inFile "{1}" -outFile "{1}" -selfSign 1'.format(
                        signer, path
                    )
                )

    # ── upstream test log verification ──────────────────────────────────

    def _verify_upstream_results(self, log_path):
        """Parse the make check log: every failure must be on the documented
        environment-limited allowlist and all 9 suite summaries must be
        present, otherwise the build fails loudly."""
        with open(log_path, "r", errors="replace") as f:
            content = f.read()
        totals = re.findall(
            r"Totals: (\d+) passed, (\d+) failed, (\d+) skipped, (\d+) blacklisted",
            content,
        )
        failures = re.findall(r"FAIL!\s*:\s*(\w+)::(\w+)\(\)", content)
        passed = sum(int(t[0]) for t in totals)
        failed = sum(int(t[1]) for t in totals)
        skipped = sum(int(t[2]) for t in totals)
        self.output.info(
            "[upstream-tests] suites=%d passed=%d failed=%d skipped=%d"
            % (len(totals), passed, failed, skipped)
        )
        if len(totals) != self._EXPECTED_SUITES:
            raise ConanException(
                "upstream test run incomplete: expected %d suite summaries, "
                "got %d (check log: %s)" % (self._EXPECTED_SUITES, len(totals), log_path)
            )
        failure_set = {(cls, func) for cls, func in failures}
        if len(failures) != failed:
            raise ConanException(
                "upstream test log inconsistent: %d FAIL! lines vs %d failed in "
                "Totals" % (len(failures), failed)
            )
        unexpected = failure_set - self._ALLOWED_FAILURES
        if unexpected:
            raise ConanException(
                "unexpected upstream test failures (not on the environment-"
                "limited allowlist): %s" % ", ".join(
                    "%s::%s()" % f for f in sorted(unexpected)
                )
            )
        if failed:
            self.output.warning(
                "[upstream-tests] %d failed case(s) tolerated as environment-"
                "limited (documented in notes.md): %s"
                % (failed, ", ".join("%s::%s()" % f for f in sorted(failure_set)))
            )

    # ── build / package ─────────────────────────────────────────────────

    def build(self):
        qtbase = self.dependencies["qt5-qtbase"]
        qt_root = self._build_qt_tree(qtbase.package_folder)
        qmake = os.path.join(qt_root, "bin", "qmake")
        if not os.path.isfile(qmake):
            raise ConanException("qt5-qtbase does not provide bin/qmake")
        build_env = self._qmake_env(qt_root, qtbase.package_folder)
        jobs = self.conf.get("tools.build:jobs", default=4, check_type=int)
        with build_env.vars(self).apply():
            self.run(
                f'cd "{self.source_folder}" && {shlex.quote(qmake)} '
                f'-spec linux-clang qtwebsockets.pro'
            )
            self.run(f'cd "{self.source_folder}" && make -j{jobs} QMAKE_STRIP=""')

            # ── upstream auto tests: build + execute (tests/auto/websockets)
            tests_dir = os.path.join(
                self.source_folder, "tests", "auto", "websockets"
            )
            self.run(
                f'cd "{tests_dir}" && {shlex.quote(qmake)} '
                f'-spec linux-clang websockets.pro'
            )
            self.run(f'cd "{tests_dir}" && make -j{jobs}')
            if not can_run(self):
                self.output.warning(
                    "Cross-building: upstream test binaries were built but not "
                    "executed on this host — run them on an OHOS host "
                    "(native build) before claiming target runtime results"
                )
                return
            self._sign_test_binaries(tests_dir)
            src_lib = os.path.join(self.source_folder, "lib")
            qtbase_lib = os.path.join(qtbase.package_folder, "lib")
            check_log = os.path.join(self.build_folder, "upstream-check.log")
            # `make check -k` executes all 9 QTest suites on the 127.0.0.1
            # loopback.  The rc is echoed as data (rc=2 is expected when the
            # documented env-limited failure occurs); the log is cat'ed into
            # the conan output so the PASS/FAIL evidence stays visible, and
            # _verify_upstream_results() enforces the allowlist.
            self.run(
                f'cd "{tests_dir}" && '
                f'LD_LIBRARY_PATH={shlex.quote(src_lib)}:'
                f'{shlex.quote(qtbase_lib)}:$LD_LIBRARY_PATH '
                f'timeout 1500 make check -k > {shlex.quote(check_log)} 2>&1; '
                f'rc=$?; cat {shlex.quote(check_log)}; '
                f'echo UPSTREAM_TESTS_RC=$rc'
            )
            self._verify_upstream_results(check_log)

    def package(self):
        qtbase_pkg = self.dependencies["qt5-qtbase"].package_folder
        install_root = os.path.join(self.build_folder, "__install_root")
        if os.path.isdir(install_root):
            shutil.rmtree(install_root)
        os.makedirs(install_root)
        qt_root = os.path.join(self.build_folder, "qt-prefix")
        if not os.path.isdir(qt_root):
            qt_root = self._build_qt_tree(qtbase_pkg)
        build_env = self._qmake_env(qt_root, qtbase_pkg)
        with build_env.vars(self).apply():
            self.run(
                f'cd "{self.source_folder}" && make install '
                f'INSTALL_ROOT={shlex.quote(install_root)} STRIP=true'
            )
        staged = os.path.join(install_root, qt_root.lstrip(os.sep))
        if not os.path.isdir(staged):
            raise ConanException(
                f"make install did not stage anything under {staged}"
            )
        moved = []
        for sub in ("lib", "include", "mkspecs", "plugins", "bin", "qml"):
            src_dir = os.path.join(staged, sub)
            if not os.path.isdir(src_dir):
                continue
            shutil.copytree(
                src_dir,
                os.path.join(self.package_folder, sub),
                symlinks=True,
                dirs_exist_ok=True,
            )
            moved.append(sub)
        if "lib" not in moved:
            raise ConanException(f"incomplete Qt prefix (got: {moved})")
        shutil.rmtree(install_root, ignore_errors=True)

        # Rewrite stale build-dir references in the packaged .prl/.la/.pc
        qt_prefix_dir = os.path.join(self.build_folder, "qt-prefix")
        own_build_dir = self.build_folder.rstrip(os.sep)
        build_root = os.path.dirname(own_build_dir)
        source_dir = self.source_folder.rstrip(os.sep)
        for root, _dirs, files in os.walk(self.package_folder):
            for name in files:
                path = os.path.join(root, name)
                if not name.endswith((".prl", ".la", ".pc")):
                    continue
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                except (UnicodeDecodeError, OSError):
                    continue
                original = content
                for stale in sorted(
                    {qt_prefix_dir, own_build_dir, source_dir, build_root},
                    key=len,
                    reverse=True,
                ):
                    content = content.replace(stale, self.package_folder)
                if content != original:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(content)

        # Sign packaged ELF shared objects (binary-sign-tool)
        self._sign_shared_objects()

    def package_info(self):
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include", "include/QtWebSockets"]
        self.cpp_info.libs = ["Qt5WebSockets"]
        self.cpp_info.requires = [
            "qt5-qtbase::Qt5Core",
            "qt5-qtbase::Qt5Network",
        ]
        self.cpp_info.set_property("cmake_file_name", "Qt5WebSockets")
        self.cpp_info.set_property("cmake_target_name", "Qt5::WebSockets")
        self.cpp_info.set_property("pkg_config_name", "Qt5WebSockets")
