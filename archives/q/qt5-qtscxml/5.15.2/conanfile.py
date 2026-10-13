#!/usr/bin/env python3
"""Conan recipe for qt5-qtscxml 5.15.2 on OpenHarmony PC.

QtScxml provides the Qt SCXML state machine module (libQt5Scxml), the
qscxmlc compiler tool and the QtScxml QML plugin.  It is built with qmake
against the qt5-qtbase / qt5-qtdeclarative packages following the
established qt5 module pattern (qtmultimedia/qtgraphicaleffects):
a private writable Qt prefix mirrors qtbase (symlinks + rewritten
mkspecs), qtdeclarative's .pri module files are merged in so that
qtHaveModule(qml) holds, qmake builds from it, and `make install` stages
into an INSTALL_ROOT inside the build folder before relocation into the
package.

Upstream auto tests (tests/auto: parser/statemachine/statemachineinfo/
dynamicmetaobject/compiled) are compiled and executed in build() with
real results reported; the qscxmlc host tool and test binaries are ELF
signed with binary-sign-tool so they can run on the OHOS build host.
"""
import os
import re
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import get
from conan.tools.layout import basic_layout


class Qt5QtscxmlConan(ConanFile):
    name = "qt5-qtscxml"
    version = "5.15.2"
    description = "Qt5 SCXML state machine module (QtScxml, qscxmlc) for OpenHarmony"
    license = "LGPL-3.0"
    homepage = "https://www.qt.io/"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "shared-library"

    _BUILD_DIR_PATTERN = re.compile(
        r"(/[^\s]*/(?:\.cache/)?\.?conan2/p/b/qt5-q[0-9a-f]+/b)"
    )

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # qmake 工具与 Qt5 基础库（含 Qt5Test testlib）由 qt5-qtbase 提供
        self.requires("qt5-qtbase/5.15.2.2")
        # src/imports（QtScxml QML 插件）与上游测试依赖 Qt5Qml/QtQuick
        self.requires("qt5-qtdeclarative/5.15.2")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} only supports Linux and OHOS, got {self.settings.os}"
            )

    def source(self):
        source_data = self.conan_data["sources"][self.version]
        urls = source_data["url"]
        if isinstance(urls, str):
            urls = [urls]
        for url in urls:
            try:
                get(self, url=url, sha256=source_data.get("sha256", ""), strip_root=True)
                return
            except Exception as error:  # noqa: BLE001
                self.output.warning(f"Failed to download source from {url}: {error}")
        raise ConanInvalidConfiguration("Unable to download source from all mirrors")

    # ------------------------------------------------------------------
    # Writable Qt prefix (mirrors qtbase, merges qtdeclarative modules)
    # ------------------------------------------------------------------
    def _rewrite_module_files(self, mkspecs_dir, target_pkg_dir):
        build_dir_pattern = self._BUILD_DIR_PATTERN
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
                fixed = build_dir_pattern.sub(target_pkg_dir, content)
                if fixed != content:
                    with open(pri_path, "w", encoding="utf-8") as f:
                        f.write(fixed)

    def _build_qt_tree(self, qtbase_pkg, qtdecl_pkg):
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
        # qtdeclarative's .pri modules merged into the writable prefix so
        # that qtHaveModule(qml) / qtHaveModule(quick) resolve during qmake.
        for modules_dir_name in ("modules", "modules-inst"):
            src_dir = os.path.join(qtdecl_pkg, "mkspecs", modules_dir_name)
            if not os.path.isdir(src_dir):
                continue
            for pri_file in os.listdir(src_dir):
                if not pri_file.endswith(".pri"):
                    continue
                with open(os.path.join(src_dir, pri_file), "r", encoding="utf-8") as f:
                    content = f.read()
                content = self._BUILD_DIR_PATTERN.sub(qtdecl_pkg, content)
                dst_dir = os.path.join(mkspecs_dst, modules_dir_name)
                os.makedirs(dst_dir, exist_ok=True)
                with open(os.path.join(dst_dir, pri_file), "w", encoding="utf-8") as f:
                    f.write(content)
        self._rewrite_module_files(mkspecs_dst, qtbase_pkg)
        return qt_root

    def _qmake_env(self, qt_root, qtbase_pkg, qtdecl_pkg):
        build_env = Environment()
        build_env.define("QTDIR", qt_root)
        build_env.prepend_path("PATH", os.path.join(qt_root, "bin"))
        build_env.append("LD_LIBRARY_PATH", os.path.join(qtbase_pkg, "lib"))
        build_env.append("LD_LIBRARY_PATH", os.path.join(qtdecl_pkg, "lib"))
        return build_env

    # ------------------------------------------------------------------
    # OHOS ELF signing for host tools / test binaries (qscxmlc, tst_*)
    # ------------------------------------------------------------------
    def _sign_binary(self, path):
        if self.settings.os != "OHOS" or not os.path.isfile(path):
            return False
        signer = (
            os.environ.get("OHOS_SIGN_TOOL", "")
            or shutil.which("binary-sign-tool")
            or "/data/service/hnp/bin/binary-sign-tool"
        )
        if not os.path.isfile(signer):
            self.output.warning(
                "binary-sign-tool is unavailable; skipping OHOS ELF signing"
            )
            return False
        signed_path = f"{path}.signed"
        self.run(
            f'"{signer}" sign -inFile "{path}" '
            f'-outFile "{signed_path}" -selfSign 1',
            quiet=True,
        )
        if not os.path.isfile(signed_path):
            raise ConanException(f"binary-sign-tool produced no output for {path}")
        os.replace(signed_path, path)
        os.chmod(path, 0o755)
        return True

    # ------------------------------------------------------------------
    # Build + upstream tests
    # ------------------------------------------------------------------
    def build(self):
        qtbase = self.dependencies["qt5-qtbase"]
        qtdecl = self.dependencies["qt5-qtdeclarative"]
        qt_root = self._build_qt_tree(qtbase.package_folder, qtdecl.package_folder)
        qmake = os.path.join(qt_root, "bin", "qmake")
        if not os.path.isfile(qmake):
            raise ConanException("qt5-qtbase does not provide bin/qmake")
        build_env = self._qmake_env(
            qt_root, qtbase.package_folder, qtdecl.package_folder
        )
        jobs = self.conf.get("tools.build:jobs", default=4, check_type=int)

        with build_env.vars(self).apply():
            # Top-level in-tree build: src/ (libQt5Scxml) + tools/ (qscxmlc).
            # tests/examples are not part of the default target (qt_parts
            # marks them no_default_target) — they are driven separately
            # below from their own .pro files.
            self.run(
                f'cd "{self.source_folder}" && {shlex.quote(qmake)} -spec linux-clang '
                f'qtscxml.pro'
            )
            self.run(
                f'cd "{self.source_folder}" && make -j{jobs} QMAKE_STRIP=""'
            )

        # Sign the freshly built qscxmlc host tool so later qmake invocations
        # (which run qscxmlc to compile STATECHARTS for tst_compiled) work.
        # qt_tool.prf may place the binary in the source tree bin/, the
        # tools/qscxmlc build dir or the writable prefix bin/ — sign all.
        seen = set()
        for tool_root in (self.source_folder, self.build_folder):
            for root, dirs, files in os.walk(tool_root):
                dirs[:] = [d for d in dirs if d not in (".git", "__install_root")]
                for name in files:
                    if name != "qscxmlc":
                        continue
                    path = os.path.abspath(os.path.join(root, name))
                    if path in seen:
                        continue
                    seen.add(path)
                    self._sign_binary(path)
        self.output.info(f"signed qscxmlc candidates: {sorted(seen)}")

        # ------------------------------------------------------------------
        # Upstream auto tests: compile + run (real execution, rule4)
        # ------------------------------------------------------------------
        self._run_upstream_tests(qt_root, qtbase, qtdecl, jobs)

    def _run_upstream_tests(self, qt_root, qtbase, qtdecl, jobs):
        """Compile and execute the upstream tests/auto suites.

        Pure-logic suites (parser, statemachine, statemachineinfo,
        dynamicmetaobject, compiled) are qmake-built against the freshly
        built Qt5Scxml and executed with the offscreen QPA platform.
        QTest "Totals:" lines are echoed so the conan create log carries
        the real evidence.
        """
        import subprocess

        suites = ["parser", "statemachine", "statemachineinfo",
                  "dynamicmetaobject", "compiled"]
        # Deterministic loader paths for the qmake/make/test subprocesses:
        # the freshly built libQt5Scxml (in-tree lib/), the Qt dependency
        # packages and the toolchain's own lib dir.  The parent
        # LD_LIBRARY_PATH is deliberately NOT inherited: build hosts may
        # carry unrelated (and possibly incompatible) libc++ copies that
        # shadow the system one needed by the host tools (Qt qmake/moc).
        env_dict = dict(os.environ)
        lib_paths = [
            os.path.join(self.source_folder, "lib"),
            os.path.join(qtbase.package_folder, "lib"),
            os.path.join(qtdecl.package_folder, "lib"),
        ]
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compilers.get("cpp") or compilers.get("cxx")
        if compiler:
            toolchain_lib = os.path.normpath(os.path.join(
                os.path.dirname(os.path.realpath(compiler)), "..", "lib"
            ))
            if os.path.isdir(toolchain_lib) and toolchain_lib not in lib_paths:
                lib_paths.append(toolchain_lib)
        env_dict["LD_LIBRARY_PATH"] = os.pathsep.join(lib_paths)
        env_dict["PATH"] = (
            os.path.join(qt_root, "bin") + os.pathsep + env_dict.get("PATH", "")
        )
        env_dict["QT_QPA_PLATFORM"] = "offscreen"
        env_dict.setdefault("QT_QPA_FONTDIR", "/usr/share/fonts")
        qml_dir = os.path.join(qtdecl.package_folder, "qml")
        if os.path.isdir(qml_dir):
            env_dict["QML_IMPORT_PATH"] = qml_dir
            env_dict["QML2_IMPORT_PATH"] = qml_dir

        summary = []
        for suite in suites:
            # In-tree build: the suite .pro lives in the source tree and
            # qmake walks up to the top-level .qmake.cache (created by the
            # top-level qmake run) so "QT += scxml" resolves against the
            # freshly built module pri in the writable prefix.
            build_dir = os.path.join(self.source_folder, "tests", "auto", suite)
            if not os.path.isfile(os.path.join(build_dir, f"{suite}.pro")):
                self.output.warning(f"upstream test suite missing: {suite}")
                continue
            self.output.info(f"=== upstream test [{suite}]: qmake ===")
            qmake_cmd = [
                os.path.join(qt_root, "bin", "qmake"),
                "-spec", "linux-clang",
                f"{suite}.pro",
            ]
            proc = subprocess.run(
                qmake_cmd, cwd=build_dir, env=env_dict,
                capture_output=True, text=True, timeout=300,
            )
            self.output.info(proc.stdout)
            if proc.returncode != 0:
                self.output.warning(
                    f"qmake failed for upstream suite {suite}:\n{proc.stderr}"
                )
                summary.append((suite, None, "qmake failed"))
                continue
            self.output.info(f"=== upstream test [{suite}]: make ===")
            proc = subprocess.run(
                ["make", f"-j{jobs}", "QMAKE_STRIP="],
                cwd=build_dir, env=env_dict,
                capture_output=True, text=True, timeout=1800,
            )
            self.output.info(proc.stdout[-4000:] if proc.stdout else "")
            if proc.returncode != 0:
                self.output.warning(
                    f"make failed for upstream suite {suite}:\n"
                    f"{proc.stderr[-4000:]}"
                )
                summary.append((suite, None, "build failed"))
                continue
            # Sign and run the test binary
            candidates = [f for f in os.listdir(build_dir)
                          if f.startswith("tst_") and os.access(
                              os.path.join(build_dir, f), os.X_OK)]
            if not candidates:
                summary.append((suite, None, "no test binary"))
                continue
            test_bin = os.path.join(build_dir, candidates[0])
            self._sign_binary(test_bin)
            self.output.info(f"=== upstream test [{suite}]: run ===")
            proc = subprocess.run(
                [test_bin], cwd=build_dir, env=env_dict,
                capture_output=True, text=True, timeout=900,
            )
            out = (proc.stdout or "") + (proc.stderr or "")
            self.output.info(out[-8000:])
            totals = self._parse_qtest_totals(out)
            if totals is None:
                summary.append((suite, None, f"run rc={proc.returncode}"))
            else:
                summary.append((suite, totals, "ok" if proc.returncode == 0 else "failed"))

        self.output.info("=== upstream test summary (suite, totals, status) ===")
        for suite, totals, status in summary:
            self.output.info(f"  {suite}: totals={totals} status={status}")

    @staticmethod
    def _parse_qtest_totals(output):
        m = re.search(
            r"Totals:\s*(\d+)\s+passed,\s*(\d+)\s+failed,"
            r"(?:\s*(\d+)\s+skipped,)?",
            output,
        )
        if not m:
            return None
        passed, failed = int(m.group(1)), int(m.group(2))
        skipped = int(m.group(3)) if m.group(3) else 0
        return {"passed": passed, "failed": failed, "skipped": skipped}

    # ------------------------------------------------------------------
    # Package
    # ------------------------------------------------------------------
    def package(self):
        qtbase_pkg = self.dependencies["qt5-qtbase"].package_folder
        qtdecl_pkg = self.dependencies["qt5-qtdeclarative"].package_folder
        install_root = os.path.join(self.build_folder, "__install_root")
        if os.path.isdir(install_root):
            shutil.rmtree(install_root)
        os.makedirs(install_root)
        qt_root = os.path.join(self.build_folder, "qt-prefix")
        if not os.path.isdir(qt_root):
            qt_root = self._build_qt_tree(qtbase_pkg, qtdecl_pkg)
        build_env = self._qmake_env(qt_root, qtbase_pkg, qtdecl_pkg)
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
        for sub in ("lib", "include", "mkspecs", "bin", "qml", "plugins"):
            src_dir = os.path.join(staged, sub)
            if not os.path.isdir(src_dir):
                continue
            shutil.copytree(
                src_dir, os.path.join(self.package_folder, sub),
                symlinks=True, dirs_exist_ok=True,
            )
            moved.append(sub)
        if "lib" not in moved:
            raise ConanException(f"incomplete Qt prefix (got: {moved})")
        shutil.rmtree(install_root, ignore_errors=True)

        # Sign packaged host tools (bin/qscxmlc) for OHOS
        if self.settings.os == "OHOS":
            for root, _dirs, files in os.walk(os.path.join(self.package_folder, "bin")):
                for name in files:
                    path = os.path.join(root, name)
                    with open(path, "rb") as fh:
                        magic = fh.read(4)
                    if magic == b"\x7fELF":
                        self._sign_binary(path)

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
                    key=len, reverse=True,
                ):
                    content = content.replace(stale, self.package_folder)
                if content != original:
                    with open(path, "w", encoding="utf-8") as f:
                        f.write(content)

    def package_info(self):
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = ["include", "include/QtScxml"]
        self.cpp_info.libs = ["Qt5Scxml"]
        # src/imports QML plugin depends on Qt5Qml from qt5-qtdeclarative
        # (the qtdeclarative package defines no per-module components, so
        # the package-level default component is referenced — same as the
        # qt5-qtgraphicaleffects recipe).
        self.cpp_info.requires = [
            "qt5-qtbase::Qt5Core",
            "qt5-qtdeclarative::qt5-qtdeclarative",
        ]
        self.cpp_info.set_property("cmake_file_name", "Qt5Scxml")
        self.cpp_info.set_property("cmake_target_name", "Qt5::Scxml")
