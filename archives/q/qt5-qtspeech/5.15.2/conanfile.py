#!/usr/bin/env python3
"""Conan recipe for qt5-qtspeech 5.15.2 on OpenHarmony PC.

QtSpeech provides the Qt TextToSpeech module (libQt5TextToSpeech) plus
platform TTS engine plugins.  It is built with qmake against the
qt5-qtbase package following the established qt5 addon module pattern
(qtmultimedia/qtscxml): a private writable Qt prefix mirrors qtbase
(symlinks + rewritten mkspecs), qmake builds from it, and ``make install``
stages into an INSTALL_ROOT inside the build folder before relocation
into the package.

Platform note (TTS engine backends): the upstream plugin set is
speechdispatcher (unix + libspeechd), flite (unix + flite + multimedia),
sapi/winrt (windows), osx/ios (apple) and android.  OpenHarmony PC has
no speech-dispatcher daemon and no flite TTS synthesizer service, so
qmake feature detection (src/tts/configure.json) disables speechd/flite
and src/plugins/tts compiles no plugin.  libQt5TextToSpeech itself is
complete; its documented no-engine behaviours (state()==BackendError,
-guarded say/stop/pause/resume, 0.0 rate/pitch/volume defaults,
empty availableVoices/availableLocales) are asserted from the consumer
side in test_package.

Upstream auto tests (tests/auto) are compiled and executed in build()
with real results reported (rule4):
- texttospeech: qmake+make+run of tst_qtexttospeech (QTest).  The five
  engine-dependent test functions cannot pass without a TTS engine
  (upstream runs them against speechd/flite); the recipe tolerates
  exactly the documented no-engine failure signature and fails the
  build on any other failure.  speech_rate/set_voice are BLACKLISTed by
  upstream on all platforms.
- cmake: the upstream module_includes ctest is driven directly with
  three environment adaptations: CMAKE_POLICY_VERSION_MINIMUM=3.5
  (CMake >= 4 removed compatibility with cmake_minimum_required(2.8)),
  a mkspecs symlink repairing qt5-qtbase's packaged
  Qt5CoreConfigExtrasMkspecDir.cmake stale build path, and the
  CMAKE_SYSTEM_NAME=Linux override (mirrored in test_package — the
  "double override") so the Qt5 config files resolve on HarmonyOS.
"""
import os
import re
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import get
from conan.tools.layout import basic_layout


class Qt5QtspeechConan(ConanFile):
    name = "qt5-qtspeech"
    version = "5.15.2"
    description = "Qt5 TextToSpeech module (QtTextToSpeech) for OpenHarmony"
    license = "LGPL-3.0"
    homepage = "https://www.qt.io/"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "shared-library"

    _BUILD_DIR_PATTERN = re.compile(
        r"(/[^\s]*/(?:\.cache/)?\.?conan2/p/b/qt5-q[0-9a-f]+/b)"
    )

    # QTest functions that require a live TTS engine plugin (none ships on
    # OHOS: no speech-dispatcher daemon, no flite synthesizer service).
    _ENGINE_DEPENDENT_TESTS = {
        "say_hello", "speech_rate", "pitch", "set_voice", "volume",
    }

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # qmake 工具与 Qt5 基础库（libQt5TextToSpeech 仅 NEEDED libQt5Core）
        # 由 qt5-qtbase 提供
        self.requires("qt5-qtbase/5.15.2.2")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"{self.name} only supports Linux and OHOS, got {self.settings.os}"
            )

    def source(self):
        # conandata 只写官方单条 URL（R39 纪律：CI 统一镜像治理）
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
    # Writable Qt prefix (mirrors qtbase)
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
        self._rewrite_module_files(mkspecs_dst, qtbase_pkg)
        return qt_root

    def _qmake_env(self, qt_root, qtbase_pkg):
        build_env = Environment()
        build_env.define("QTDIR", qt_root)
        build_env.prepend_path("PATH", os.path.join(qt_root, "bin"))
        build_env.append("LD_LIBRARY_PATH", os.path.join(qtbase_pkg, "lib"))
        return build_env

    def _fix_mkspecs_dir_link(self, qtbase_pkg):
        """Repair qt5-qtbase's packaged Qt5CoreConfigExtrasMkspecDir.cmake.

        The packaged file keeps the conan build-time mkspecs path
        ("<install_prefix>/../b//mkspecs/linux-clang").  The writable Qt
        prefix sits at <build>/qt-prefix, so "../b" resolves to <build>/b
        — provide the linux-clang mkspecs dir there so
        _qt5_Core_check_file_exists passes when the upstream cmake test
        suite consumes Qt5Core via CMAKE_PREFIX_PATH (local prototype
        verified: without this link find_package(Qt5Core) FATAL_ERRORs).
        """
        link_root = os.path.join(self.build_folder, "b", "mkspecs")
        os.makedirs(link_root, exist_ok=True)
        link_path = os.path.join(link_root, "linux-clang")
        if not os.path.exists(link_path):
            os.symlink(
                os.path.join(qtbase_pkg, "mkspecs", "linux-clang"), link_path
            )

    # ------------------------------------------------------------------
    # OHOS ELF signing for test binaries (binary-sign-tool)
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
    # Build + upstream tests (real run, rule4)
    # ------------------------------------------------------------------
    def build(self):
        qtbase = self.dependencies["qt5-qtbase"]
        qt_root = self._build_qt_tree(qtbase.package_folder)
        qmake = os.path.join(qt_root, "bin", "qmake")
        if not os.path.isfile(qmake):
            raise ConanException("qt5-qtbase does not provide bin/qmake")
        # mkspecs link must exist before the upstream cmake suite runs
        self._fix_mkspecs_dir_link(qtbase.package_folder)
        build_env = self._qmake_env(qt_root, qtbase.package_folder)
        jobs = self.conf.get("tools.build:jobs", default=4, check_type=int)

        with build_env.vars(self).apply():
            # Top-level in-tree build: src/tts (libQt5TextToSpeech) and
            # src/plugins/tts (empty on OHOS — speechd/flite features are
            # disabled by configure.json feature detection).  tests/examples
            # are no_default_target under qt_parts and are driven separately
            # below from their own .pro files.
            self.run(
                f'cd "{self.source_folder}" && {shlex.quote(qmake)} -spec linux-clang '
                f'qtspeech.pro'
            )
            self.run(
                f'cd "{self.source_folder}" && make -j{jobs} QMAKE_STRIP=""'
            )

        self._run_upstream_tests(qt_root, qtbase, jobs)

    def _test_env(self, qt_root, qtbase):
        """Deterministic loader/PATH environment for test subprocesses.

        The parent LD_LIBRARY_PATH is deliberately NOT inherited: build
        hosts may carry unrelated (and possibly incompatible) libc++
        copies that shadow the system one needed by the host tools
        (same rationale as the qt5-qtscxml recipe).
        """
        qtbase_pkg = qtbase.package_folder
        env_dict = dict(os.environ)
        lib_paths = [
            os.path.join(self.source_folder, "lib"),
            os.path.join(qtbase_pkg, "lib"),
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
        if os.path.isdir("/system/lib64"):
            lib_paths.append("/system/lib64")
        env_dict["LD_LIBRARY_PATH"] = os.pathsep.join(lib_paths)
        env_dict["PATH"] = (
            os.path.join(qt_root, "bin") + os.pathsep + env_dict.get("PATH", "")
        )
        env_dict["QT_QPA_PLATFORM"] = "offscreen"
        env_dict.setdefault("QT_QPA_FONTDIR", "/usr/share/fonts")
        return env_dict, compilers

    def _run_upstream_tests(self, qt_root, qtbase, jobs):
        """Compile and execute the upstream tests/auto suites (rule4)."""
        env_dict, compilers = self._test_env(qt_root, qtbase)
        summary = []

        # ---------------- suite 1: texttospeech (QTest) ----------------
        suite = "texttospeech"
        suite_dir = os.path.join(self.source_folder, "tests", "auto", suite)
        if not os.path.isfile(os.path.join(suite_dir, f"{suite}.pro")):
            raise ConanException(f"upstream test suite missing: {suite}")

        self.output.info(f"=== upstream test [{suite}]: qmake ===")
        proc = subprocess.run(
            [os.path.join(qt_root, "bin", "qmake"), "-spec", "linux-clang",
             f"{suite}.pro"],
            cwd=suite_dir, env=env_dict,
            capture_output=True, text=True, timeout=300,
        )
        self.output.info(proc.stdout)
        if proc.returncode != 0:
            raise ConanException(
                f"qmake failed for upstream suite {suite}:\n{proc.stderr}"
            )

        self.output.info(f"=== upstream test [{suite}]: make ===")
        proc = subprocess.run(
            ["make", f"-j{jobs}", "QMAKE_STRIP="],
            cwd=suite_dir, env=env_dict,
            capture_output=True, text=True, timeout=1800,
        )
        self.output.info(proc.stdout[-4000:] if proc.stdout else "")
        if proc.returncode != 0:
            raise ConanException(
                f"make failed for upstream suite {suite}:\n{proc.stderr[-4000:]}"
            )

        candidates = [f for f in os.listdir(suite_dir)
                      if f.startswith("tst_") and os.access(
                          os.path.join(suite_dir, f), os.X_OK)]
        if not candidates:
            raise ConanException(f"no test binary produced for suite {suite}")
        test_bin = os.path.join(suite_dir, candidates[0])
        self._sign_binary(test_bin)

        self.output.info(f"=== upstream test [{suite}]: run ===")
        proc = subprocess.run(
            [test_bin], cwd=suite_dir, env=env_dict,
            capture_output=True, text=True, timeout=300,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        self.output.info(out[-8000:])
        totals = self._parse_qtest_totals(out)
        if totals is None:
            raise ConanException(
                f"upstream suite {suite} produced no QTest Totals line "
                f"(rc={proc.returncode})"
            )
        self._validate_engine_absence(suite, out, totals)
        summary.append((suite, totals, proc.returncode))

        # ---------------- suite 2: cmake (ctest module_includes) --------
        suite = "cmake"
        cmake_src = os.path.join(self.source_folder, "tests", "auto", suite)
        cmake_build = os.path.join(cmake_src, "build")
        if not os.path.isfile(os.path.join(cmake_src, "CMakeLists.txt")):
            raise ConanException(f"upstream test suite missing: {suite}")
        os.makedirs(cmake_build, exist_ok=True)

        # Environment adaptations (local prototype verified):
        # 1. CMake >= 4 removed compatibility with the upstream template's
        #    cmake_minimum_required(2.8) — CMAKE_POLICY_VERSION_MINIMUM=3.5.
        # 2. CMAKE_SYSTEM_NAME=Linux override ("double override" together
        #    with test_package) so the Qt5 config files resolve on HarmonyOS.
        env_dict["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        cc = compilers.get("c") or "clang"
        cxx = compilers.get("cpp") or compilers.get("cxx") or "clang++"
        processor = (
            "aarch64" if str(self.settings.arch) in ("armv8", "armv8.3")
            else str(self.settings.arch)
        )
        prefix_path = self.source_folder + ";" + qt_root
        self.output.info(f"=== upstream test [{suite}]: cmake configure ===")
        proc = subprocess.run(
            ["cmake", cmake_src,
             f"-DCMAKE_C_COMPILER={cc}",
             f"-DCMAKE_CXX_COMPILER={cxx}",
             "-DCMAKE_BUILD_TYPE=Release",
             "-DCMAKE_SYSTEM_NAME=Linux",
             f"-DCMAKE_SYSTEM_PROCESSOR={processor}",
             f"-DCMAKE_PREFIX_PATH={prefix_path}",
             "-DQt5_MODULE_TEST_DEPENDS=Core",
             "-DCMAKE_TextToSpeech_MODULE_MAJOR_VERSION=5",
             "-DCMAKE_TextToSpeech_MODULE_MINOR_VERSION=15",
             "-DCMAKE_TextToSpeech_MODULE_PATCH_VERSION=2",
             "-DCMAKE_MODULES_UNDER_TEST=TextToSpeech"],
            cwd=cmake_build, env=env_dict,
            capture_output=True, text=True, timeout=600,
        )
        self.output.info(proc.stdout[-4000:] if proc.stdout else "")
        if proc.returncode != 0:
            raise ConanException(
                f"cmake configure failed for upstream suite {suite}:\n"
                f"{(proc.stderr or '')[-4000:]}"
            )

        self.output.info(f"=== upstream test [{suite}]: ctest ===")
        proc = subprocess.run(
            ["ctest", "--output-on-failure"],
            cwd=cmake_build, env=env_dict,
            capture_output=True, text=True, timeout=900,
        )
        self.output.info(proc.stdout[-8000:] if proc.stdout else "")
        if proc.returncode != 0 or "100% tests passed" not in (proc.stdout or ""):
            raise ConanException(
                f"upstream cmake suite failed (rc={proc.returncode}):\n"
                f"{(proc.stdout or '')[-4000:]}"
            )
        summary.append((suite, {"passed": 1, "failed": 0, "skipped": 0}, 0))

        self.output.info("=== upstream test summary (suite, totals, rc) ===")
        for suite, totals, rc in summary:
            self.output.info(
                f"  {suite}: passed={totals['passed']} failed={totals['failed']} "
                f"skipped={totals['skipped']} rc={rc}"
            )

    def _validate_engine_absence(self, suite, out, totals):
        """Tolerate exactly the documented no-engine failure signature.

        Every failing function must be an engine-dependent test AND the
        run must carry the "No text-to-speech plug-ins were found."
        signature (OHOS has no speech-dispatcher/flite backend).  Any
        other failure is a real defect and fails the build.
        """
        if totals["failed"] == 0:
            return
        failed_funcs = re.findall(
            r"^(?:FAIL!|BFAIL|XPASS)\s*:\s*tst_QTextToSpeech::(\w+)\(\)",
            out, re.M,
        )
        unexpected = [f for f in failed_funcs
                      if f not in self._ENGINE_DEPENDENT_TESTS]
        if unexpected:
            raise ConanException(
                f"upstream suite {suite} failed outside the engine-dependent "
                f"test set {sorted(self._ENGINE_DEPENDENT_TESTS)}: "
                f"{sorted(set(unexpected))} — real defect, not the documented "
                f"no-engine behaviour"
            )
        if "No text-to-speech plug-ins were found." not in out:
            raise ConanException(
                f"upstream suite {suite} failed without the documented "
                f"'No text-to-speech plug-ins were found.' signature — "
                f"real defect (totals={totals})"
            )
        if not re.search(r"PASS\s+:\s*tst_QTextToSpeech::initTestCase\(\)", out):
            raise ConanException(
                f"upstream suite {suite}: initTestCase did not pass — "
                f"environment/bootstrap defect (totals={totals})"
            )
        self.output.warning(
            f"upstream suite {suite}: {totals['failed']} failed test(s) match "
            f"the documented no-engine behaviour on OHOS (no speech-dispatcher/"
            f"flite TTS backend) — environment limitation, see "
            f"test_package/MANIFEST.yml exemption"
        )

    @staticmethod
    def _parse_qtest_totals(output):
        m = re.search(
            r"Totals:\s*(\d+)\s+passed,\s*(\d+)\s+failed,"
            r"(?:\s*(\d+)\s+skipped,)?(?:\s*(\d+)\s+blacklisted,)?",
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

        # Sign packaged host tools for OHOS (defensive: qtspeech ships no
        # bin/ tools, only libQt5TextToSpeech which keeps its toolchain
        # .codesign section because QMAKE_STRIP is empty)
        if self.settings.os == "OHOS":
            bin_dir = os.path.join(self.package_folder, "bin")
            if os.path.isdir(bin_dir):
                for root, _dirs, files in os.walk(bin_dir):
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
        self.cpp_info.includedirs = ["include", "include/QtTextToSpeech"]
        # readelf -d: libQt5TextToSpeech.so NEEDED libQt5Core.so.5 only
        # (plus libc++_shared.so / libc.so from the platform)
        self.cpp_info.libs = ["Qt5TextToSpeech"]
        self.cpp_info.requires = ["qt5-qtbase::Qt5Core"]
        self.cpp_info.set_property("cmake_file_name", "Qt5TextToSpeech")
        self.cpp_info.set_property("cmake_target_name", "Qt5::TextToSpeech")
