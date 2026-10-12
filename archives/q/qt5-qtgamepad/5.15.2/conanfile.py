#!/usr/bin/env python3
"""Conan recipe for qt5-qtgamepad 5.15.2 on OpenHarmony PC.

Qt5 Gamepad module (QtGamepad) built with qmake from the qt5-qtbase
package.  Follows the established qt5-qtsvg/qtwebsockets pattern: a
private writable Qt prefix mirrors qtbase (symlinks + rewritten
mkspecs), qmake builds from it, and `make install` stages into an
INSTALL_ROOT inside the build folder before relocation into the package.

Upstream auto tests: qtgamepad 5.15.2 ships NO QTest suites
(tests/auto/auto.pro has an empty SUBDIRS).  The single upstream-
registered test is tests/auto/cmake (ctest_testcase): it configures
with CMake, registers one `module_includes` build-and-test case and
asserts the installed Qt5 module cmake configurations resolve (Qt5Core /
Qt5Gui through the module dependency closure).  It is built and executed
inside build() via `make check`:
  * the upstream CMakeLists declares cmake_minimum_required(2.8) while
    the host CMake is 4.x, so CMAKE_POLICY_VERSION_MINIMUM=3.5 is
    exported for the whole check run;
  * ctest output must show "100% tests passed" with 1 registered test,
    otherwise the build fails loudly.

The evdev gamepad backend plugin is built (qtbase enables the evdev
feature for this device family) and packaged under plugins/gamepads/.
The sdl2 backend feature stays off: its configure.json probe requires
pkg-config sdl2, which is not part of the declared dependency set.
The QML import (src/imports) is skipped automatically because the
qtbase package does not provide the qml/quick modules.

Consumer-side verification (test_package) covers the gamepad API logic
that is reachable without a physical gamepad (OHOS PC has no
/dev/input/js* device): QGamepadManager instance/connectedGamepads
empty-list behaviour, QGamepad invalid-device behaviour, and the full
QGamepadKeyNavigation property matrix, plus a QPluginLoader load of the
packaged evdev plugin (dlopen + metadata "Keys" contains "evdev").
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


class Qt5QtgamepadConan(ConanFile):
    name = "qt5-qtgamepad"
    version = "5.15.2"
    description = "Qt5 Gamepad module (QtGamepad) for OpenHarmony"
    license = "LGPL-3.0"
    homepage = "https://www.qt.io/"
    url = ""

    settings = "os", "compiler", "build_type", "arch"
    package_type = "shared-library"

    # Upstream ctest-registered tests in tests/auto/cmake: exactly one
    # (module_includes, via the ctest_testcase machinery).
    _EXPECTED_CTEST_TESTS = 1

    # Stale build-dir references inside the cached qtbase mkspecs, e.g.
    # /home/.../.conan2/p/b/qt5f140ab856c797/b
    _BUILD_DIR_PATTERN = re.compile(
        r"(/[^\s\"]*/(?:\.cache/)?\.?conan2/p/b/qt[0-9a-zA-Z-]+/b)"
    )
    # Loose prefix form: matches the whole foreign build folder root
    # (/…/p/b/qt5-xxxx) regardless of what follows (/b/lib, /p/lib,
    # /b/include, …) — the .la libdir lines use the /p/lib suffix which
    # the strict _BUILD_DIR_PATTERN cannot reach.
    _PKG_DIR_PATTERN = re.compile(
        r"(/[^\s\"']*/(?:\.cache/)?\.?conan2/p/b/qt[0-9a-zA-Z-]+/p)(?=[/'\"]|$)"
    )

    _QMAKE_WRAPPER_TEMPLATE = r"""#!/usr/bin/env python3
import os, re, subprocess, sys

CUR = "__CUR__"
PKG = "__PKG__"
REAL = "__REAL__"

rc = subprocess.call([REAL] + sys.argv[1:])

PAT_B = re.compile(r"(/[^\s\"']*/(?:\.cache/)?\.?conan2/p/b/qt[0-9a-zA-Z-]+/b)")
PAT_P = re.compile(r"(/[^\s\"']*/(?:\.cache/)?\.?conan2/p/b/qt[0-9a-zA-Z-]+/p)(?=[/'\"]|$)")

def _sub(m):
    seg = m.group(1)
    root = seg[: seg.rfind("/")]
    if root == CUR:
        return seg
    return PKG

for name in os.listdir("."):
    if name != "Makefile" and not name.startswith("Makefile."):
        continue
    try:
        with open(name, "r", encoding="utf-8") as f:
            content = f.read()
    except OSError:
        continue
    fixed = PAT_P.sub(_sub, PAT_B.sub(_sub, content))
    if fixed != content:
        with open(name, "w", encoding="utf-8") as f:
            f.write(fixed)
sys.exit(rc)
"""

    def _current_build_prefix(self):
        """The /…/p/b/qt5-xxxx prefix of THIS build folder (whose qt-prefix
        mirror is live and must never be rewritten)."""
        bf = self.build_folder.rstrip(os.sep)
        m = re.search(r"^(.*(?:\.cache/)?\.?conan2/p/b/qt[0-9a-zA-Z-]+)", bf)
        return m.group(1) if m else bf

    def _rewrite_foreign_paths(self, content, qtbase_pkg):
        """Replace every foreign (dead) qt5 conan build-folder prefix with
        the qtbase package path, preserving this build's own references."""
        cur = self._current_build_prefix()

        def _sub(m):
            seg = m.group(1)
            root = seg[: seg.rfind("/")]
            if root == cur:
                return seg
            return qtbase_pkg

        content = self._BUILD_DIR_PATTERN.sub(_sub, content)
        return self._PKG_DIR_PATTERN.sub(_sub, content)
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
                fixed = self._rewrite_foreign_paths(content, qtbase_pkg)
                if fixed != content:
                    with open(pri_path, "w", encoding="utf-8") as f:
                        f.write(fixed)

        # NOTE: qtgamepad needs no private_tests / reduce_exports flipping —
        # upstream ships no private QTest suites for this module (the only
        # registered test is the ctest module_includes case, which links
        # nothing private).

        # 2) Prune foreign module .pri files: a locally cached qtbase package
        #    can be contaminated by sibling Qt5 module builds (qt_lib_qml*.pri,
        #    qt_lib_quick*.pri, ... pointing at other conan cache folders).
        #    They are not part of the declared dependency set and would make
        #    qtHaveModule(quick) true (pulling the QML import into the build
        #    with undeclared link lines).  On a pristine qtbase package this
        #    pass is a no-op.
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

    def _fix_lib_metadata_files(self, lib_dir, qtbase_pkg):
        """Rewrite stale conan build-dir references inside the mirrored
        lib/*.prl and lib/*.la files.  The qtbase package ships support
        library .prl files (libQt5DeviceDiscoverySupport.prl) whose
        QMAKE_PRL_LIBS points at the long-gone qtbase build folder
        (/…/p/b/qt5-*/b/lib/libQt5Core.so); qmake's link_prl machinery
        pulls those dead paths into the link line and the evdev plugin
        fails to link with 'no such file or directory'.  The shared
        cache package must not be mutated, so the mirror owns private
        copies of these small metadata files."""
        for name in os.listdir(lib_dir):
            path = os.path.join(lib_dir, name)
            if os.path.isdir(path):
                continue
            if name.endswith(".pc"):
                # .pc files are symlinks into the shared qtbase package
                # whose libdir/includedir lines still point at the
                # original build tree — materialize cleaned private
                # copies (recursive qmake runs read them when generating
                # sub-Makefiles, e.g. the evdev plugin link line).
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                except (UnicodeDecodeError, OSError):
                    continue
                fixed = self._rewrite_foreign_paths(content, qtbase_pkg)
                if fixed != content:
                    if os.path.islink(path):
                        os.remove(path)
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(fixed)
                    self.output.info(f"rewrote stale build paths in {name}")
                continue
            if not (name.endswith(".prl") or name.endswith(".la")):
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
            except (UnicodeDecodeError, OSError):
                continue
            fixed = self._rewrite_foreign_paths(content, qtbase_pkg)
            if fixed != content:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(fixed)
                self.output.info(f"rewrote stale build paths in {name}")

    def _sanitize_makefiles(self, root_dir, qtbase_pkg):
        """Rewrite stale qtbase build-dir paths inside qmake-generated
        Makefiles. CRITICAL: only rewrite paths that point at OTHER
        (dead) conan build folders — never the current build folder's
        own qt-prefix references (its bin/qmake symlink is live and
        used by the recursive sub-make QMAKE rules).
        """
        rewritten = 0
        for dirpath, _dirs, files in os.walk(root_dir):
            for name in files:
                if name != "Makefile" and not name.startswith("Makefile."):
                    continue
                path = os.path.join(dirpath, name)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                except (UnicodeDecodeError, OSError):
                    continue
                fixed = self._rewrite_foreign_paths(content, qtbase_pkg)
                if fixed != content:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(fixed)
                    rewritten += 1
        if rewritten:
            self.output.info(
                "sanitized %d qmake Makefile(s) under %s"
                % (rewritten, root_dir)
            )

    def _fix_qtbase_lib_metadata(self, qtbase_pkg):
        """Rewrite stale conan build-dir references inside the qtbase
        package's lib/*.prl and lib/*.la files (serialport/qtsvg
        precedent: the shared cache package carries build-machine paths
        that must be redirected to the package folder).

        The load-bearing case for qtgamepad is
        libQt5DeviceDiscoverySupport.prl: its QMAKE_PRL_LIBS names
        /…/p/b/qt5-*/b/lib/libQt5Core.so (the long-gone qtbase build
        folder).  qmake's link_prl machinery resolves .prl files next
        to the actual linked library (QT_MODULE_LIB_BASE → the package
        lib dir), reads that stale path into the link line and the
        evdev plugin fails with 'no such file or directory'.  A private
        mirror copy of the .prl is NOT consulted — the package-side
        file itself must be fixed.  The rewrite is idempotent: already
        rewritten paths (package dir) do not match the build-dir
        pattern.  qtserialport (which links no support library) is not
        affected by this class of stale paths; qtgamepad is, because it
        links Qt5DeviceDiscoverySupport.a."""
        lib_dir = os.path.join(qtbase_pkg, "lib")
        if not os.path.isdir(lib_dir):
            return
        fixed_files = 0
        for name in os.listdir(lib_dir):
            path = os.path.join(lib_dir, name)
            if os.path.isdir(path) or not (
                name.endswith(".prl") or name.endswith(".la")
            ):
                continue
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
            except (UnicodeDecodeError, OSError):
                continue
            fixed = self._BUILD_DIR_PATTERN.sub(qtbase_pkg, content)
            if fixed != content:
                try:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(fixed)
                except OSError as error:  # noqa: BLE001
                    # Read-only cache package (not observed on CI workers —
                    # the merged qt5-qtserialport recipe rewrites cache-side
                    # .pri files in place): degrade gracefully, the
                    # mirror-side four-pass sanitize remains the root cure.
                    self.output.warning(
                        "cannot rewrite %s inside the qtbase cache package "
                        "(%s) — relying on the mirror-side sanitize"
                        % (name, error)
                    )
                    continue
                fixed_files += 1
        if fixed_files:
            self.output.info(
                "rewrote stale build-dir paths in %d qtbase lib metadata "
                "files (.prl/.la)" % fixed_files
            )

    def _build_qt_tree(self, qtbase_pkg):
        qt_root = os.path.join(self.build_folder, "qt-prefix")
        if os.path.isdir(qt_root):
            shutil.rmtree(qt_root)
        os.makedirs(qt_root)
        for entry in os.listdir(qtbase_pkg):
            if entry in ("bin", "mkspecs", "lib"):
                continue
            os.symlink(os.path.join(qtbase_pkg, entry), os.path.join(qt_root, entry))
        bin_src = os.path.join(qtbase_pkg, "bin")
        bin_dst = os.path.join(qt_root, "bin")
        os.makedirs(bin_dst)
        for entry in os.listdir(bin_src):
            if entry == "qt.conf":
                continue
            if entry == "qmake":
                # Materialize qmake as qmake.real plus a sanitizing
                # wrapper. Materializing alone is NOT enough: the
                # cleaned module .pri files point library paths at the
                # qtbase package dir, so qmake's link_prl machinery
                # still reads the PACKAGE's own (uncleaned) .prl files
                # and re-injects stale build-dir paths into sub-Makefiles
                # generated during make's recursion — after the
                # in-recipe sanitize pass has already run. The wrapper
                # scrubs every Makefile at generation time, on every
                # qmake invocation (top-level and recursive).
                shutil.copy2(
                    os.path.join(bin_src, entry),
                    os.path.join(bin_dst, entry + ".real"),
                )
                cur_prefix = self._current_build_prefix()
                wrapper = os.path.join(bin_dst, "qmake")
                script = self._QMAKE_WRAPPER_TEMPLATE
                for token, value in (
                    ("__CUR__", cur_prefix),
                    ("__PKG__", qtbase_pkg),
                    ("__REAL__", os.path.join(bin_dst, "qmake.real")),
                ):
                    script = script.replace(token, value.replace("\\", "\\\\"))
                with open(wrapper, "w", encoding="utf-8") as f:
                    f.write(script)
                os.chmod(wrapper, 0o755)
                continue
            os.symlink(os.path.join(bin_src, entry), os.path.join(bin_dst, entry))
        # lib: symlink the payloads (big .so files stay in the cache
        # package) but materialize the small .prl/.la metadata files so
        # _fix_lib_metadata_files can rewrite them without touching the
        # shared cache package; cmake/pkgconfig trees are symlinked
        # wholesale (they carry no absolute build paths).
        lib_src = os.path.join(qtbase_pkg, "lib")
        lib_dst = os.path.join(qt_root, "lib")
        os.makedirs(lib_dst)
        for entry in os.listdir(lib_src):
            src_path = os.path.join(lib_src, entry)
            if entry.endswith(".prl") or entry.endswith(".la"):
                shutil.copy2(src_path, os.path.join(lib_dst, entry))
            elif entry == "cmake":
                # Materialize the cmake config tree (NOT a symlink): the
                # package's Qt5*ConfigExtrasMkspecDir.cmake files bake a
                # build-tree relative derivation
                # (${_qt5Core_install_prefix}/../b//mkspecs/...) that is
                # wrong for the mirror layout and must be rewritten — a
                # symlinked tree would point into the shared package.
                shutil.copytree(
                    src_path, os.path.join(lib_dst, entry), symlinks=False
                )
            else:
                os.symlink(src_path, os.path.join(lib_dst, entry))
        self._fix_lib_metadata_files(lib_dst, qtbase_pkg)
        self._fix_cmake_mkspec_dirs(lib_dst)
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
        # Redirect module .pri paths from the shared qtbase package into
        # the MIRROR: qmake's link_prl machinery resolves .prl files from
        # the libdir each .pri declares; pointing at the package dir makes
        # it read the PACKAGE's own (uncleaned, shared-cache) .prl files,
        # re-injecting stale build-dir paths into sub-Makefile link lines
        # during make's recursion. The mirror's lib/ holds cleaned .prl
        # copies for exactly this purpose.
        for modules_dir_name in ("modules", "modules-inst"):
            modules_dir = os.path.join(mkspecs_dst, modules_dir_name)
            if not os.path.isdir(modules_dir):
                continue
            for pri_file in os.listdir(modules_dir):
                if not pri_file.endswith(".pri"):
                    continue
                pri_path = os.path.join(modules_dir, pri_file)
                try:
                    with open(pri_path, "r", encoding="utf-8") as f:
                        content = f.read()
                except (UnicodeDecodeError, OSError):
                    continue
                fixed = content.replace(qtbase_pkg, qt_root)
                if fixed != content:
                    with open(pri_path, "w", encoding="utf-8") as f:
                        f.write(fixed)
        return qt_root

    def _fix_cmake_mkspec_dirs(self, lib_dst):
        """Rewrite the build-tree relative mkspecs derivation baked into
        the qtbase package's Qt5*ConfigExtrasMkspecDir.cmake files
        (${_qt5Core_install_prefix}/../b//mkspecs/linux-clang — valid
        only for the original qtbase build layout). In the mirror the
        mkspecs tree sits directly under the install prefix, so the
        derivation becomes ${_qt5Core_install_prefix}/mkspecs/...;
        consumer CMake projects (e.g. the upstream tests/auto/cmake
        ctest suite) resolve it through find_package(Qt5Core)."""
        cmake_root = os.path.join(lib_dst, "cmake")
        if not os.path.isdir(cmake_root):
            return
        for dirpath, _dirs, files in os.walk(cmake_root):
            for name in files:
                if not name.endswith(".cmake"):
                    continue
                path = os.path.join(dirpath, name)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                except (UnicodeDecodeError, OSError):
                    continue
                if "/../b//" not in content:
                    continue
                fixed = content.replace("/../b//", "/")
                with open(path, "w", encoding="utf-8") as f:
                    f.write(fixed)
                self.output.info(f"fixed mkspec dir derivation in {name}")

    def _qmake_env(self, qt_root, qtbase_pkg):
        build_env = Environment()
        build_env.define("QTDIR", qt_root)
        build_env.prepend_path("PATH", os.path.join(qt_root, "bin"))
        build_env.append("LD_LIBRARY_PATH", os.path.join(qtbase_pkg, "lib"))
        # Host CMake is 4.x while the upstream ctest project declares
        # cmake_minimum_required(2.8) — keep the whole `make check` run
        # (nested cmake configure + ctest build-and-test) on the
        # compatibility policy floor.
        build_env.define("CMAKE_POLICY_VERSION_MINIMUM", "3.5")
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

    def _sign_file(self, objcopy, signer, path):
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

    def _sign_tree_executables(self, root_dir):
        """Sign every regular executable ELF file under root_dir (upstream
        test binaries built in the build tree)."""
        objcopy, signer = self._sign_tools()
        if not signer:
            self.output.warning(
                "binary-sign-tool not found — upstream test binaries will "
                "run unsigned"
            )
            return
        for root, _dirs, files in os.walk(root_dir):
            for name in files:
                path = os.path.join(root, name)
                if os.path.islink(path) or not os.access(path, os.X_OK):
                    continue
                with open(path, "rb") as f:
                    if f.read(4) != b"\x7fELF":
                        continue
                self._sign_file(objcopy, signer, path)

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
        for root, _dirs, files in os.walk(os.path.join(self.package_folder, "lib")):
            for name in files:
                if not (name.endswith(".so") or ".so." in name):
                    continue
                path = os.path.join(root, name)
                if os.path.islink(path):
                    continue
                self._sign_file(objcopy, signer, path)
        plugdir = os.path.join(self.package_folder, "plugins")
        if os.path.isdir(plugdir):
            for root, _dirs, files in os.walk(plugdir):
                for name in files:
                    if not (name.endswith(".so") or ".so." in name):
                        continue
                    path = os.path.join(root, name)
                    if os.path.islink(path):
                        continue
                    self._sign_file(objcopy, signer, path)

    # ── upstream ctest log verification ────────────────────────────────

    def _verify_upstream_results(self, log_path):
        """Parse the make check log: exactly one ctest-registered test must
        run and pass, otherwise the build fails loudly."""
        with open(log_path, "r", errors="replace") as f:
            content = f.read()
        # ctest summary line: "100% tests passed, 0 tests failed out of 1"
        m = re.search(
            r"(\d+)% tests passed, (\d+) tests failed out of (\d+)", content
        )
        if not m:
            raise ConanException(
                "upstream ctest run produced no summary line (check log: %s)"
                % log_path
            )
        pct, failed, total = (int(g) for g in m.groups())
        self.output.info(
            "[upstream-tests] ctest: %d%% passed, %d failed, %d total"
            % (pct, failed, total)
        )
        if total != self._EXPECTED_CTEST_TESTS:
            raise ConanException(
                "upstream ctest run incomplete: expected %d registered test, "
                "got %d (check log: %s)"
                % (self._EXPECTED_CTEST_TESTS, total, log_path)
            )
        if failed != 0 or pct != 100:
            raise ConanException(
                "upstream ctest run failed: %d failed of %d (check log: %s)"
                % (failed, total, log_path)
            )

    # ── build / package ─────────────────────────────────────────────────

    def build(self):
        qtbase = self.dependencies["qt5-qtbase"]
        # Must run before qmake: link_prl resolves .prl files next to the
        # linked library inside the qtbase package itself (serialport
        # precedent of fixing the shared cache package in place).
        self._fix_qtbase_lib_metadata(qtbase.package_folder)
        qt_root = self._build_qt_tree(qtbase.package_folder)
        qmake = os.path.join(qt_root, "bin", "qmake")
        if not os.path.isfile(qmake):
            raise ConanException("qt5-qtbase does not provide bin/qmake")
        build_env = self._qmake_env(qt_root, qtbase.package_folder)
        jobs = self.conf.get("tools.build:jobs", default=2, check_type=int)
        with build_env.vars(self).apply():
            # qmake runs the configure.json machinery (config.tests/sdl
            # probe fails without pkg-config sdl2, so the sdl2 backend
            # feature stays off — expected and documented).
            self.run(
                f'cd "{self.source_folder}" && {shlex.quote(qmake)} '
                f'-spec linux-clang qtgamepad.pro'
            )
            # NOTE: no -r here — qtConfig(sdl2) in gamepads.pro is a
            # feature registered by the FIRST top-level qmake pass (from
            # configure.json), so recursive .pro reading in the same
            # invocation fails with "Could not find feature sdl2".
            # Sub-Makefiles are instead generated during make's own
            # recursion by the MATERIALIZED mirror qmake (real file, not
            # symlink), which resolves via /proc/self/exe into the mirror
            # and therefore reads the cleaned .prl/.qt.conf — no stale
            # build-dir paths can leak anymore.
            # Sanitize generated Makefiles: top-level Makefiles generated
            # pull stale qtbase build-dir paths (from .pc files / qmake's
            # baked-in prefixes) into LIBS lines even after the mirror's
            # .pri/.prl/.la rewrite pass. Rewrite every generated Makefile
            # in place right before make (qt5-qtserialport-style hard guard).
            self._sanitize_makefiles(self.source_folder, qtbase.package_folder)
            self.run(f'cd "{self.source_folder}" && make -j{jobs} QMAKE_STRIP=""')

            # ── upstream auto test: tests/auto/cmake (ctest_testcase) ──
            tests_dir = os.path.join(
                self.source_folder, "tests", "auto", "cmake"
            )
            self.run(
                f'cd "{tests_dir}" && {shlex.quote(qmake)} '
                f'-spec linux-clang cmake.pro'
            )
            self.run(f'cd "{tests_dir}" && make -j{jobs}')
            if not can_run(self):
                self.output.warning(
                    "Cross-building: upstream test binaries were built but "
                    "not executed on this host — run them on an OHOS host "
                    "(native build) before claiming target runtime results"
                )
                return
            # Sign every ELF executable produced under the cmake test build
            # tree (module_includes_exe and friends) before ctest runs them.
            self._sign_tree_executables(tests_dir)
            qtbase_lib = os.path.join(qtbase.package_folder, "lib")
            src_lib = os.path.join(self.source_folder, "lib")
            check_log = os.path.join(self.build_folder, "upstream-check.log")
            # `make check` drives ctest, which configures the generated
            # module_includes sub-project (find_package of the module
            # dependency closure: Qt5Core/Qt5Gui), builds it and runs it.
            # The rc is echoed as data; the log is cat'ed into the conan
            # output so the PASS evidence stays visible, and
            # _verify_upstream_results() enforces the 1/1 pass.
            self.run(
                f'cd "{tests_dir}" && '
                f'LD_LIBRARY_PATH={shlex.quote(src_lib)}:'
                f'{shlex.quote(qtbase_lib)}:$LD_LIBRARY_PATH '
                f'timeout 900 make check > {shlex.quote(check_log)} 2>&1; '
                f'rc=$?; cat {shlex.quote(check_log)}; '
                f'echo UPSTREAM_TESTS_RC=$rc'
            )
            self._verify_upstream_results(check_log)

    def package(self):
        qtbase_pkg = self.dependencies["qt5-qtbase"].package_folder
        # Idempotent re-run of the lib metadata fix (package() may run in a
        # fresh context where build()'s fix is not present).
        self._fix_qtbase_lib_metadata(qtbase_pkg)
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
        plugin_so = os.path.join(
            self.package_folder, "plugins", "gamepads", "libevdevgamepad.so"
        )
        if not os.path.isfile(plugin_so):
            self.output.warning(
                "evdev gamepad backend plugin missing from package "
                "(plugins/gamepads/libevdevgamepad.so)"
            )
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

        # Sign packaged ELF shared objects (lib + plugins)
        self._sign_shared_objects()

    def package_info(self):
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include", "include/QtGamepad"]
        self.cpp_info.libs = ["Qt5Gamepad"]
        self.cpp_info.requires = [
            "qt5-qtbase::Qt5Core",
            "qt5-qtbase::Qt5Gui",
        ]
        self.cpp_info.set_property("cmake_file_name", "Qt5Gamepad")
        self.cpp_info.set_property("cmake_target_name", "Qt5::Gamepad")
        self.cpp_info.set_property("pkg_config_name", "Qt5Gamepad")
