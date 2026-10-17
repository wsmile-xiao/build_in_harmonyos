#!/usr/bin/env python3
"""Conan recipe for YUView 2.14 on HarmonyOS PC.

YUView is a Qt qmake desktop application. The recipe builds the bundled
YUViewLib static library and the YUView executable with the qmake6 provided by
the Qt Base package, runs the upstream QtTest suites shipped in YUViewUnitTest,
and packages the executable together with its Qt runtime environment.

Only registry-published Qt modules are used: the patches make the qmake project
tolerate Qt configurations without OpenGL and without SSL, both of which are
absent from the HarmonyOS PC Qt Base build.
"""

import os
import shlex
import shutil
import stat
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout

# The upstream unit test executables contained in YUViewUnitTest. Each one is a
# standalone QtTest binary that runs without a window system.
_UPSTREAM_TESTS = (
    "YUViewUnitTest/filesource/filesource/FilesourceTest",
    "YUViewUnitTest/filesource/filesourceAnnexB/FilesourceAnnexBTest",
    "YUViewUnitTest/statistics/statisticsData/StatisticsDataTest",
    "YUViewUnitTest/statistics/statisticsFileCSV/StatisticsFileCSVTest",
    "YUViewUnitTest/statistics/statisticsFileVTMBMS/StatisticsFileVTMBMSTest",
    "YUViewUnitTest/video/rgb/ConversionRGBTest/ConversionRGBTest",
    "YUViewUnitTest/video/rgb/Issue511RGBConversionInvalidMemoryAccess/"
    "Issue511RGBConversionInvalidMemoryAccess",
    "YUViewUnitTest/video/rgb/PixelFormatRGBGuessTest/PixelFormatRGBGuessTest",
    "YUViewUnitTest/video/rgb/PixelFormatRGBTest/PixelFormatRGBTest",
    "YUViewUnitTest/video/yuv/PixelFormatYUVGuessTest/PixelFormatYUVGuessTest",
    "YUViewUnitTest/video/yuv/PixelFormatYUVTest/PixelFormatYUVTest",
)


class YUViewConan(ConanFile):
    name = "yuview"
    version = "2.14"
    description = "YUV player with an advanced analytic toolset for HarmonyOS PC"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/IENT/YUView"
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1.3")

    def validate(self):
        if self.settings.os != "OHOS":
            raise ConanInvalidConfiguration(
                "yuview/2.14 in this archive is a HarmonyOS PC adaptation"
            )

    def layout(self):
        basic_layout(self)
        self.folders.build = "build"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        self._qt_environment().vars(self).save_script("conanbuild_yuview_qt")
        self._lld_environment().vars(self).save_script("conanbuild_yuview_lld")

    def build(self):
        apply_conandata_patches(self)
        os.makedirs(self.build_folder, exist_ok=True)
        # Compiling and linking needs the OHOS SDK linker libraries on the
        # loader path (see _lld_environment). The upstream test binaries are run
        # outside this block so those libraries cannot leak into the tests.
        with self._lld_environment().vars(self).apply():
            self._run(self._qmake_args(), cwd=self.build_folder)
            # Build the library, the application and the upstream unit tests in
            # one pass. CONFIG+=UNITTESTS adds YUViewUnitTest to the subdirs.
            self._run(["make", "-j{}".format(self._jobs())], cwd=self.build_folder)
        with self._qt_environment().vars(self).apply():
            self._run_upstream_tests()

    def package(self):
        binary = os.path.join(self.build_folder, "YUViewApp", "YUView")
        if not os.path.isfile(binary):
            raise ConanInvalidConfiguration("The qmake build did not produce YUView")
        bindir = os.path.join(self.package_folder, "bin")
        os.makedirs(bindir, exist_ok=True)
        target = os.path.join(bindir, "YUView")
        shutil.copy2(binary, target)
        os.chmod(target, stat.S_IMODE(os.stat(target).st_mode) | 0o755)
        self._sign_elfs([target])
        copy(self, "LICENSE.GPL3", self.source_folder,
             os.path.join(self.package_folder, "licenses"))

        # Upstream does not install a library, but it does build one. Ship the
        # static library together with its public headers so downstream
        # consumers of the YUView analytics code have something to link
        # against, and so the package can be verified through a real consumer.
        sdk_dir = os.path.join(self.package_folder, "sdk", "YUViewLib")
        # qmake mirrors the project layout inside the build folder.
        archive = os.path.join(self.build_folder, "YUViewLib", "libYUViewLib.a")
        if not os.path.isfile(archive):
            raise ConanInvalidConfiguration("The qmake build did not produce libYUViewLib.a")
        os.makedirs(sdk_dir, exist_ok=True)
        shutil.copy2(archive, os.path.join(sdk_dir, "libYUViewLib.a"))
        copy(self, "*.h", os.path.join(self.source_folder, "YUViewLib", "src"),
             os.path.join(sdk_dir, "src"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
        qtbase = self.dependencies["qtbase"].package_folder
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(qtbase, "lib"))
        self.runenv_info.prepend_path("QT_PLUGIN_PATH", os.path.join(qtbase, "plugins"))
        self.runenv_info.define_path("QT_QPA_PLATFORM", "offscreen")

    # ── qmake helpers ──────────────────────────────────────────────────────

    def _qmake_args(self):
        # The project file has to be addressed by absolute path: qmake is run
        # from the build folder to keep the upstream sources untouched.
        project = os.path.join(self.source_folder, "YUView.pro")
        args = [self._qmake_executable(), "-spec", "harmonyos-clang",
                "CONFIG+=UNITTESTS", "CONFIG+=release", "CONFIG-=debug",
                "VERSION={}".format(self.version),
                # The upstream test projects enable CONFIG+=testcase, and
                # testcase.prf asks qt_functions.prf for the library search
                # path variable. That test only accepts a fixed list of host
                # operating systems and aborts with "Operating system not
                # supported." on the HarmonyOS host name. HarmonyOS PC is
                # Linux-like, so declare the host accordingly; the result is
                # the same branch the Linux host would take.
                "QMAKE_HOST.os=Linux",
                project]
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        # R33: the compiler paths come from the Conan configuration, they are
        # never taken from the shell environment.
        if compilers.get("c"):
            args.insert(-1, "QMAKE_CC={}".format(compilers["c"]))
        if compilers.get("cpp"):
            args.insert(-1, "QMAKE_CXX={}".format(compilers["cpp"]))
        return args

    def _qmake_executable(self):
        qtbase = self.dependencies["qtbase"].package_folder
        for name in ("qmake6", "qmake"):
            candidate = os.path.join(qtbase, "bin", name)
            if os.path.isfile(candidate):
                return candidate
        raise ConanInvalidConfiguration(
            "qtbase/6.11.1.3 does not provide bin/qmake6 or bin/qmake"
        )

    def _qt_environment(self):
        env = Environment()
        qtbase = self.dependencies["qtbase"].package_folder
        env.prepend_path("PATH", os.path.join(qtbase, "bin"))
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(qtbase, "lib"))
        env.prepend_path("QT_PLUGIN_PATH", os.path.join(qtbase, "plugins"))
        env.prepend_path("QMAKEPATH", qtbase)
        # The upstream unit tests and the application are GUI-less here, so the
        # offscreen platform plugin is the one that always loads.
        env.define("QT_QPA_PLATFORM", "offscreen")
        return env

    def _lld_environment(self):
        """Build/link environment carrying the Qt and OHOS SDK runtime paths.

        The OHOS SDK ships `llvm/bin/lld` as a dynamically linked ELF that
        NEEDs `libxml2.so.16` from its sibling `llvm/lib` directory (E120/E132/
        E266). Clang loads the linker as an in-process library/driver, so a
        worker whose loader path lacks that directory fails at link time with
        `Error loading shared library libxml2.so.16` followed by a cascade of
        `xml...: symbol not found` relocations — while the compile steps still
        succeed, which is what makes this look like a source error.

        Only the compile/link block runs with this environment: the upstream
        test binaries are executed under _qt_environment() so the SDK libraries
        cannot leak into the test processes.
        """
        env = self._qt_environment()
        libdir = self._ohos_sdk_llvm_libdir()
        if libdir:
            env.prepend_path("LD_LIBRARY_PATH", libdir)
        return env

    @staticmethod
    def _jobs():
        try:
            return max(1, len(os.sched_getaffinity(0)))
        except AttributeError:
            return max(1, os.cpu_count() or 1)

    # ── upstream tests ─────────────────────────────────────────────────────

    def _run_upstream_tests(self):
        """Run every upstream QtTest binary produced by the build."""
        missing = []
        failed = []
        for relative in _UPSTREAM_TESTS:
            executable = os.path.join(self.build_folder, relative)
            if not os.path.isfile(executable):
                missing.append(relative)
                continue
            # QtTest binaries report their own pass/fail through the exit code.
            result = subprocess.run([executable], cwd=os.path.dirname(executable))
            if result.returncode != 0:
                failed.append(relative)
        if missing:
            raise ConanInvalidConfiguration(
                "Upstream test binaries were not built: {}".format(", ".join(missing))
            )
        if failed:
            raise ConanInvalidConfiguration(
                "Upstream tests failed: {}".format(", ".join(failed))
            )
        self.output.info(
            "Upstream YUView 2.14 unit tests: {}/{} passed".format(
                len(_UPSTREAM_TESTS), len(_UPSTREAM_TESTS)
            )
        )

    # ── OHOS ELF signing ───────────────────────────────────────────────────

    def _sign_elfs(self, binaries):
        """Re-sign the packaged executables so the OHOS loader accepts them."""
        environment = Environment()
        sdk_libdir = self._ohos_sdk_llvm_libdir()
        if sdk_libdir:
            environment.append("LD_LIBRARY_PATH", sdk_libdir)
        with environment.vars(self).apply():
            objcopy = self._resolve_sdk_tool("OBJCOPY", "llvm-objcopy")
            objdump = self._resolve_sdk_tool("OBJDUMP", "llvm-objdump")
            signer = self._resolve_sdk_tool(
                "BINARY_SIGN_TOOL", "binary-sign-tool", ("toolchains/lib",)
            )
            for binary in binaries:
                original_mode = stat.S_IMODE(os.stat(binary).st_mode)
                unsigned = binary + ".unsigned"
                signed = binary + ".signed"
                shutil.copy2(binary, unsigned)
                if self._has_codesign_section(objdump, unsigned):
                    self._run_tool(
                        [objcopy, "--remove-section", ".codesign", unsigned],
                        "remove the old code signature from {}".format(binary),
                    )
                self._run_tool(
                    [signer, "sign", "-inFile", unsigned, "-outFile", signed,
                     "-selfSign", "1"],
                    "sign {}".format(binary),
                )
                if not os.path.isfile(signed) or not self._has_codesign_section(
                    objdump, signed
                ):
                    raise ConanInvalidConfiguration(
                        "Signing did not produce a signed ELF file for {}".format(binary)
                    )
                os.replace(signed, binary)
                # The signed file is a fresh output of the signing tool, so the
                # executable bit of the original has to be restored explicitly.
                os.chmod(binary, original_mode | 0o755)
                os.unlink(unsigned)

    def _ohos_sdk_llvm_libdir(self):
        """Locate the OHOS SDK llvm/lib directory that ships libxml2.so.16."""
        candidates = []
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        clang = compilers.get("c") or shutil.which("clang") or ""
        if clang:
            # <sdk>/native/llvm/bin/clang -> <sdk>/native/llvm/lib
            candidates.append(
                os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(clang))), "lib")
            )
        for candidate in candidates:
            if os.path.isfile(os.path.join(candidate, "libxml2.so.16")):
                return candidate
        return ""

    @staticmethod
    def _has_codesign_section(objdump, path):
        section_table = YUViewConan._run_tool(
            [objdump, "-h", path], "inspect ELF sections in {}".format(path)
        )
        return any(".codesign" in line.split() for line in section_table.splitlines())

    def _ohos_sdk_tool_dirs(self):
        """Directories of the OHOS SDK toolchain, derived from the compiler.

        CI workers expose the SDK through a curated PATH that does not include
        `llvm/bin`, so tools such as `llvm-objdump` resolve to a bare name and
        fail when invoked. Deriving the directories from the active compiler
        keeps the lookup independent of PATH.
        """
        dirs = []
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        clang = compilers.get("c") or shutil.which("clang") or ""
        if clang:
            # <sdk>/native/llvm/bin/clang -> <sdk>/native/llvm
            llvm_root = os.path.dirname(os.path.dirname(os.path.realpath(clang)))
            dirs.append(os.path.join(llvm_root, "bin"))
            # <sdk>/native/llvm -> <sdk>/toolchains, which holds binary-sign-tool
            sdk_root = os.path.dirname(os.path.dirname(llvm_root))
            dirs.append(os.path.join(sdk_root, "toolchains", "bin"))
        return dirs

    def _resolve_sdk_tool(self, env_name, default_name, extra_subdirs=()):
        """Resolve a toolchain tool, preferring PATH but falling back to the SDK.

        `_resolve_tool` returns the bare name when the lookup fails, which
        defers the error to execution time with a confusing message. This
        variant additionally searches the SDK directories derived from the
        compiler, so the tools are found on workers with a minimal PATH.
        """
        explicit = os.environ.get(env_name)
        candidates = [explicit] if explicit else []
        candidates.append(default_name)
        for directory in self._ohos_sdk_tool_dirs():
            candidates.append(os.path.join(directory, default_name))
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        clang = compilers.get("c") or shutil.which("clang") or ""
        if clang:
            llvm_root = os.path.dirname(os.path.dirname(os.path.realpath(clang)))
            sdk_root = os.path.dirname(os.path.dirname(llvm_root))
            for subdir in extra_subdirs:
                candidates.append(os.path.join(sdk_root, subdir, default_name))
        for candidate in candidates:
            if not candidate:
                continue
            resolved = shutil.which(candidate) if os.sep not in candidate else (
                candidate if os.path.isfile(candidate) else None
            )
            if resolved and os.path.isfile(resolved) and os.access(resolved, os.X_OK):
                return os.path.abspath(resolved)
        raise ConanInvalidConfiguration(
            "Required tool {} was not found; set {} or add it to PATH "
            "or the OHOS SDK".format(default_name, env_name)
        )

    @staticmethod
    def _run_tool(command, action):
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=120)
        except (OSError, subprocess.SubprocessError) as error:
            raise ConanInvalidConfiguration(
                "Unable to {}: {}".format(action, error)
            ) from error
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            raise ConanInvalidConfiguration(
                "Unable to {}: {}".format(action, detail or "tool exited unsuccessfully")
            )
        return result.stdout

    @staticmethod
    def _run(command, cwd):
        printable = " ".join(shlex.quote(part) for part in command)
        result = subprocess.run(command, cwd=cwd)
        if result.returncode != 0:
            raise ConanInvalidConfiguration(
                "Command failed with exit code {}: {}".format(result.returncode, printable)
            )
