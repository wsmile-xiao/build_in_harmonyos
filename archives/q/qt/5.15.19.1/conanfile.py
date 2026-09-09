#!/usr/bin/env python3
"""Conan recipe for a headless Qt 5.15.19 foundation on HarmonyOS PC."""

import os
import shlex
import shutil
import stat
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class QtConan(ConanFile):
    name = "qt"
    version = "5.15.19.1"
    description = "Qt 5 Core, Network, Gui, Widgets, Xml and DBus for HarmonyOS PC"
    license = "LGPL-3.0-only OR GPL-3.0-only"
    homepage = "https://doc.qt.io/qt-5/"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    no_copy_source = True
    _skipped_modules = (
        "qt3d",
        "qtactiveqt",
        "qtandroidextras",
        "qtcanvas3d",
        "qtcharts",
        "qtconnectivity",
        "qtdatavis3d",
        "qtdeclarative",
        "qtdoc",
        "qtgamepad",
        "qtgraphicaleffects",
        "qtimageformats",
        "qtlocation",
        "qtlottie",
        "qtmacextras",
        "qtmultimedia",
        "qtnetworkauth",
        "qtpurchasing",
        "qtquick3d",
        "qtquickcontrols",
        "qtquickcontrols2",
        "qtquicktimeline",
        "qtremoteobjects",
        "qtscript",
        "qtscxml",
        "qtsensors",
        "qtserialbus",
        "qtserialport",
        "qtspeech",
        "qtsvg",
        "qttools",
        "qttranslations",
        "qtvirtualkeyboard",
        "qtwayland",
        "qtwebchannel",
        "qtwebengine",
        "qtwebglplugin",
        "qtwebsockets",
        "qtwebview",
        "qtwinextras",
        "qtx11extras",
        "qtxmlpatterns",
    )

    _upstream_tests = (
        (
            "tst_qstring",
            "qtbase/tests/auto/corelib/text/qstring",
            "tst_qstring",
        ),
        (
            "tst_qhostaddress",
            "qtbase/tests/auto/network/kernel/qhostaddress",
            "tst_qhostaddress",
        ),
        (
            "tst_qimage",
            "qtbase/tests/auto/gui/image/qimage",
            "tst_qimage",
        ),
        (
            "tst_qsizepolicy",
            "qtbase/tests/auto/widgets/kernel/qsizepolicy",
            "tst_qsizepolicy",
        ),
        (
            "tst_qdom",
            "qtbase/tests/auto/xml/dom/qdom",
            "tst_qdom",
        ),
    )

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        os_name = str(self.settings.os)
        if os_name not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "qt/5.15.19 expects a Linux-compatible POSIX target"
            )
        if os_name != "OHOS":
            raise ConanInvalidConfiguration(
                "qt/5.15.19 in this archive is a HarmonyOS PC adaptation"
            )

    def layout(self):
        self.folders.source = "src"
        self.folders.build = "build"
        self.folders.generators = os.path.join(self.folders.build, "generators")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)
        self._ensure_source_adaptations()

    def generate(self):
        VirtualBuildEnv(self).generate()

    def build(self):
        self._ensure_source_adaptations()
        self._make_configure_scripts_executable()
        os.makedirs(self.build_folder, exist_ok=True)
        os.makedirs(self._qtbase_build_folder(), exist_ok=True)
        qt_build_folder = self._qt_build_folder()
        build_env = self._build_environment()
        with build_env.vars(self).apply():
            self._configure()
            self._make(cwd=qt_build_folder)
            self._build_selected_upstream_tests()

    def package(self):
        qt_build_folder = self._qt_build_folder()
        build_env = self._build_environment()
        with build_env.vars(self).apply():
            self._make(
                cwd=qt_build_folder,
                extra_args=[f"INSTALL_ROOT={self.package_folder}"],
                target="install",
            )
        self._ensure_installed_shlib_alias_copies()
        if str(self.settings.os) == "OHOS":
            self._sign_installed_elfs()

    def package_info(self):
        # Qt installs complete, relocatable Qt5Config.cmake files. Prevent
        # CMakeDeps from generating an incomplete replacement config.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]

        bindir = os.path.join(self.package_folder, "bin")
        libdir = os.path.join(self.package_folder, "lib")
        plugindir = os.path.join(self.package_folder, "plugins")
        self.buildenv_info.prepend_path("PATH", bindir)
        self.runenv_info.prepend_path("PATH", bindir)
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", libdir)
        self.runenv_info.define_path("QT_PLUGIN_PATH", plugindir)

        core = self.cpp_info.components["core"]
        core.libs = ["Qt5Core"]
        core.set_property("cmake_target_name", "Qt5::Core")

        network = self.cpp_info.components["network"]
        network.libs = ["Qt5Network"]
        network.requires = ["core"]
        network.set_property("cmake_target_name", "Qt5::Network")

        gui = self.cpp_info.components["gui"]
        gui.libs = ["Qt5Gui"]
        gui.requires = ["core"]
        gui.set_property("cmake_target_name", "Qt5::Gui")

        widgets = self.cpp_info.components["widgets"]
        widgets.libs = ["Qt5Widgets"]
        widgets.requires = ["core", "gui"]
        widgets.set_property("cmake_target_name", "Qt5::Widgets")

        xml = self.cpp_info.components["xml"]
        xml.libs = ["Qt5Xml"]
        xml.requires = ["core"]
        xml.set_property("cmake_target_name", "Qt5::Xml")

        # 5.15.19.1: QtDBus enabled (removed -no-dbus); needed by
        # libqtdbustest / Qt D-Bus consumers.
        dbus = self.cpp_info.components["dbus"]
        dbus.libs = ["Qt5DBus"]
        dbus.requires = ["core"]
        dbus.set_property("cmake_target_name", "Qt5::DBus")

    def _ensure_source_adaptations(self):
        self._ensure_harmonyos_mkspec()
        self._ensure_harmonyos_shlib_alias_copy()
        self._ensure_harmonyos_test_env_host_os()
        self._ensure_pthread_cancel_guard()
        self._ensure_configure_target_spec()

    def _ensure_harmonyos_mkspec(self):
        mkspec_dir = os.path.join(self.source_folder, "qtbase", "mkspecs", "harmonyos-clang")
        os.makedirs(mkspec_dir, exist_ok=True)
        files = {
            "qmake.conf": (
                "# qmake configuration for native HarmonyOS clang builds.\n"
                "\n"
                "MAKEFILE_GENERATOR = UNIX\n"
                "CONFIG += incremental\n"
                "\n"
                "QMAKE_INCREMENTAL_STYLE = sublib\n"
                "QMAKE_LN_SHLIB = cp -f\n"
                "\n"
                "include(../common/linux.conf)\n"
                "include(../common/gcc-base-unix.conf)\n"
                "include(../common/clang.conf)\n"
                "\n"
                "QMAKE_PLATFORM += harmonyos ohos\n"
                "DEFINES += QT_NO_PTHREAD_CANCEL QT_NO_ARM_AES_INTRINSICS\n"
                "\n"
                "QMAKE_LFLAGS += -ccc-gcc-name g++\n"
                "\n"
                "load(qt_config)\n"
            ),
            "qplatformdefs.h": (
                "#ifndef QHARMONYOS_PLATFORMDEFS_H\n"
                "#define QHARMONYOS_PLATFORMDEFS_H\n"
                "\n"
                "#include \"../linux-g++/qplatformdefs.h\"\n"
                "\n"
                "#endif // QHARMONYOS_PLATFORMDEFS_H\n"
            ),
        }
        for name, contents in files.items():
            path = os.path.join(mkspec_dir, name)
            if os.path.isfile(path):
                with open(path, encoding="utf-8") as existing:
                    if existing.read() == contents:
                        continue
            with open(path, "w", encoding="utf-8", newline="\n") as created:
                created.write(contents)

    def _ensure_harmonyos_shlib_alias_copy(self):
        spec_post = os.path.join(
            self.source_folder,
            "qtbase",
            "mkspecs",
            "features",
            "spec_post.prf",
        )
        if not os.path.isfile(spec_post):
            raise ConanInvalidConfiguration("Qt spec_post.prf is missing")

        with open(spec_post, encoding="utf-8") as feature:
            contents = feature.read()

        override = (
            "\n"
            "# HarmonyOS package cache does not allow symbolic links.\n"
            "contains(QMAKE_PLATFORM, harmonyos): QMAKE_LN_SHLIB = cp -f\n"
        )
        if "contains(QMAKE_PLATFORM, harmonyos): QMAKE_LN_SHLIB = cp -f" in contents:
            return

        with open(spec_post, "w", encoding="utf-8", newline="\n") as feature:
            feature.write(contents.rstrip() + override)

    def _ensure_harmonyos_test_env_host_os(self):
        qt_functions = os.path.join(
            self.source_folder,
            "qtbase",
            "mkspecs",
            "features",
            "qt_functions.prf",
        )
        if not os.path.isfile(qt_functions):
            raise ConanInvalidConfiguration("Qt qt_functions.prf is missing")

        with open(qt_functions, encoding="utf-8") as feature:
            contents = feature.read()

        original = "Linux|FreeBSD|OpenBSD|NetBSD|DragonFly|SunOS|HP-UX|QNX|GNU"
        replacement = "Linux|FreeBSD|OpenBSD|NetBSD|DragonFly|SunOS|HP-UX|QNX|GNU|HarmonyOS"
        if replacement in contents:
            return
        if original not in contents:
            raise ConanInvalidConfiguration("Qt qt_functions.prf host OS context was not found")

        contents = contents.replace(original, replacement, 1)
        with open(qt_functions, "w", encoding="utf-8", newline="\n") as feature:
            feature.write(contents)

    def _ensure_pthread_cancel_guard(self):
        qthread = os.path.join(
            self.source_folder,
            "qtbase",
            "src",
            "corelib",
            "thread",
            "qthread_unix.cpp",
        )
        if not os.path.isfile(qthread):
            raise ConanInvalidConfiguration("Qt qthread_unix.cpp is missing")

        with open(qthread, encoding="utf-8") as source:
            contents = source.read()

        replacements = (
            (
                "#if !defined(Q_OS_ANDROID)\n"
                "    pthread_setcancelstate(PTHREAD_CANCEL_DISABLE, nullptr);",
                "#if !defined(Q_OS_ANDROID) && !defined(QT_NO_PTHREAD_CANCEL)\n"
                "    pthread_setcancelstate(PTHREAD_CANCEL_DISABLE, nullptr);",
            ),
            (
                "#if !defined(Q_OS_ANDROID)\n"
                "        pthread_setcancelstate(PTHREAD_CANCEL_ENABLE, nullptr);",
                "#if !defined(Q_OS_ANDROID) && !defined(QT_NO_PTHREAD_CANCEL)\n"
                "        pthread_setcancelstate(PTHREAD_CANCEL_ENABLE, nullptr);",
            ),
            (
                "#if !defined(Q_OS_ANDROID)\n"
                "    Q_D(QThread);",
                "#if !defined(Q_OS_ANDROID) && !defined(QT_NO_PTHREAD_CANCEL)\n"
                "    Q_D(QThread);",
            ),
            (
                "#if defined(Q_OS_ANDROID)\n"
                "    Q_UNUSED(enabled);",
                "#if defined(Q_OS_ANDROID) || defined(QT_NO_PTHREAD_CANCEL)\n"
                "    Q_UNUSED(enabled);",
            ),
        )
        changed = False
        for original, replacement in replacements:
            if replacement in contents:
                continue
            if original not in contents:
                raise ConanInvalidConfiguration(
                    "Qt qthread_unix.cpp pthread_cancel guard context was not found"
                )
            contents = contents.replace(original, replacement, 1)
            changed = True

        if changed:
            with open(qthread, "w", encoding="utf-8", newline="\n") as source:
                source.write(contents)

    def _ensure_configure_target_spec(self):
        configure = os.path.join(self.source_folder, "qtbase", "configure")
        if not os.path.isfile(configure):
            raise ConanInvalidConfiguration("Qt configure script is missing")

        with open(configure, encoding="utf-8") as source:
            contents = source.read()

        patched = "TargetSpec=$PLATFORM\nHostSpec=$PLATFORM"
        if patched in contents:
            return

        original = "TargetSpec=dummy\nHostSpec=$PLATFORM"
        if original not in contents:
            raise ConanInvalidConfiguration(
                "Qt configure target spec bootstrap context was not found"
            )

        with open(configure, "w", encoding="utf-8", newline="\n") as source:
            source.write(contents.replace(original, patched, 1))

    def _make_configure_scripts_executable(self):
        executable_bits = stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
        for relative_path in ("configure", os.path.join("qtbase", "configure")):
            configure = os.path.join(self.source_folder, relative_path)
            if os.path.isfile(configure):
                os.chmod(configure, os.stat(configure).st_mode | executable_bits)

    def _configure(self):
        configure = os.path.join(self.source_folder, "qtbase", "configure")
        if not os.path.isfile(configure):
            raise ConanInvalidConfiguration("Qt configure script is missing")

        args = [
            "sh",
            configure,
            "-top-level",
            "-opensource",
            "-confirm-license",
            "-prefix",
            "/",
            "-platform",
            "harmonyos-clang",
            "-xplatform",
            "harmonyos-clang",
            "-release" if str(self.settings.build_type) == "Release" else "-debug",
            "-shared" if self.options.shared else "-static",
            "-nomake",
            "examples",
            "-nomake",
            "tests",
            "-no-opengl",
            "-no-eglfs",
            "-no-linuxfb",
            "-no-kms",
            "-no-gbm",
            "-no-xcb",
            "-no-xkbcommon",
            "-no-libinput",
            "-no-evdev",
            "-no-mtdev",
            "-no-tslib",
            "-no-gtk",
            "-no-glib",
            "-no-cups",
            "-no-icu",
            "-no-fontconfig",
            "-no-ssl",
            "-no-sql-sqlite",
            "-qt-zlib",
            "-qt-pcre",
            "-qt-libpng",
            "-qt-libjpeg",
            "-qt-freetype",
            "-qt-harfbuzz",
            "-no-pch",
        ]
        for module in self._skipped_modules:
            args.extend(["-skip", module])
        args.extend(self._qmake_assignments())
        self._run(args, cwd=self._qtbase_build_folder())

    def _build_selected_upstream_tests(self):
        qmake = self._qmake_executable()

        tests_root = os.path.join(self._qt_build_folder(), "selected-upstream-tests")
        os.makedirs(tests_root, exist_ok=True)
        built_tests = []
        for name, relative_dir, executable in self._upstream_tests:
            project = os.path.join(self.source_folder, relative_dir)
            if not os.path.isdir(project):
                raise ConanInvalidConfiguration(
                    f"Upstream test directory is missing: {relative_dir}"
                )
            build_dir = os.path.join(tests_root, name)
            os.makedirs(build_dir, exist_ok=True)
            self._run([qmake, project], cwd=build_dir)
            self._make(cwd=build_dir)
            built_tests.append(os.path.join(build_dir, executable))

        if not can_run(self):
            self.output.info("Cross-run disabled; upstream Qt tests were built only")
            return

        tests_tmp = os.path.join(tests_root, "tmp")
        os.makedirs(tests_tmp, exist_ok=True)

        test_env = Environment()
        test_env.prepend_path("LD_LIBRARY_PATH", os.path.join(self._qtbase_build_folder(), "lib"))
        test_env.define("QT_QPA_PLATFORM", "offscreen")
        test_env.define("QT_LOGGING_RULES", "qt.qpa.*=false")
        test_env.define("TMPDIR", tests_tmp)
        test_env.define("TMPPREFIX", os.path.join(tests_tmp, "zsh"))
        with test_env.vars(self).apply():
            for executable in built_tests:
                self._run([executable], cwd=os.path.dirname(executable))

    def _qt_build_folder(self):
        return os.path.dirname(self.build_folder)

    def _qtbase_build_folder(self):
        return os.path.join(self._qt_build_folder(), "qtbase")

    def _qmake_executable(self):
        qt_build_folder = self._qt_build_folder()
        candidates = [
            os.path.join(qt_build_folder, "qtbase", "bin", "qmake"),
            os.path.join(self.build_folder, "bin", "qmake"),
            os.path.join(self.build_folder, "qtbase", "bin", "qmake"),
        ]
        for candidate in candidates:
            if os.path.isfile(candidate):
                return candidate
        raise ConanInvalidConfiguration("Qt qmake was not built")

    def _build_environment(self):
        env = Environment()
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        if compilers.get("c"):
            env.define("CC", compilers["c"])
        if compilers.get("cpp"):
            env.define("CXX", compilers["cpp"])
        shell = shutil.which("sh") or "sh"
        env.define("CONFIG_SHELL", shell)
        env.define("SHELL", shell)
        return env

    def _qmake_assignments(self):
        assignments = []
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        if compilers.get("c"):
            assignments.append(f"QMAKE_CC={compilers['c']}")
        if compilers.get("cpp"):
            assignments.append(f"QMAKE_CXX={compilers['cpp']}")
            assignments.append(f"QMAKE_LINK={compilers['cpp']}")
            assignments.append(f"QMAKE_LINK_SHLIB={compilers['cpp']}")
        return assignments

    def _has_pthread_cancel(self):
        if str(self.settings.os) == "OHOS":
            return False
        test_code = (
            "#include <pthread.h>\n"
            "int main(void) {\n"
            "    int old_state;\n"
            "    return pthread_setcancelstate(PTHREAD_CANCEL_DISABLE, "
            "&old_state);\n"
            "}\n"
        )
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        configured_compiler = (
            compilers.get("cpp")
            or os.environ.get("CXX")
            or shutil.which("clang++")
            or shutil.which("c++")
        )
        if not configured_compiler:
            return False
        try:
            compiler_command = shlex.split(configured_compiler)
        except ValueError:
            return False
        compiler_flags = self.conf.get(
            "tools.build:cxxflags", default=[], check_type=list
        ) or []
        with tempfile.TemporaryDirectory(prefix="qt5-pthread-check-") as temp_dir:
            source_path = os.path.join(temp_dir, "check.cpp")
            executable = os.path.join(temp_dir, "check")
            with open(source_path, "w", encoding="utf-8") as source_file:
                source_file.write(test_code)
            try:
                for link_flags in ([], ["-lpthread"]):
                    result = subprocess.run(
                        compiler_command
                        + compiler_flags
                        + [source_path]
                        + link_flags
                        + ["-o", executable],
                        capture_output=True,
                        timeout=30,
                    )
                    if result.returncode == 0:
                        return True
                return False
            except (OSError, subprocess.SubprocessError):
                return False

    def _make(self, cwd, target=None, extra_args=None):
        args = [self._make_program()]
        jobs = self.conf.get("tools.build:jobs", default=None)
        if jobs:
            args.append(f"-j{jobs}")
        if target:
            args.append(target)
        if extra_args:
            args.extend(extra_args)
        self._run(args, cwd=cwd)

    def _make_program(self):
        return os.environ.get("MAKE") or shutil.which("make") or "make"

    def _ensure_installed_shlib_alias_copies(self):
        if str(self.settings.os) != "OHOS":
            return

        libdir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(libdir):
            return

        version_suffix = f".so.{self.version}"
        major, minor, _ = str(self.version).split(".", 2)
        alias_suffixes = (".so", f".so.{major}", f".so.{major}.{minor}")
        for filename in sorted(os.listdir(libdir)):
            if not filename.startswith("libQt5") or not filename.endswith(version_suffix):
                continue
            source = os.path.join(libdir, filename)
            if not os.path.isfile(source) or os.path.islink(source):
                continue
            basename = filename[: -len(version_suffix)]
            for suffix in alias_suffixes:
                alias = os.path.join(libdir, basename + suffix)
                if os.path.islink(alias) or not os.path.exists(alias):
                    if os.path.lexists(alias):
                        os.unlink(alias)
                    shutil.copy2(source, alias)

    def _sign_installed_elfs(self):
        binaries = []
        for root, _, filenames in os.walk(self.package_folder):
            for filename in filenames:
                candidate = os.path.join(root, filename)
                if os.path.islink(candidate):
                    continue
                if self._elf_type(candidate) in (2, 3):  # ET_EXEC, ET_DYN
                    binaries.append(candidate)
        if not binaries:
            return
        objcopy = self._resolve_tool("OBJCOPY", "llvm-objcopy")
        objdump = self._resolve_tool("OBJDUMP", "llvm-objdump")
        signer = self._resolve_tool("BINARY_SIGN_TOOL", "binary-sign-tool")
        for binary in sorted(binaries):
            original_mode = stat.S_IMODE(os.stat(binary).st_mode)
            with tempfile.TemporaryDirectory(
                prefix=".conan-sign-", dir=os.path.dirname(binary)
            ) as temp_dir:
                unsigned = os.path.join(temp_dir, "unsigned")
                signed = os.path.join(temp_dir, "signed")
                shutil.copy2(binary, unsigned)
                if self._has_codesign_section(objdump, unsigned):
                    self._run_tool(
                        [objcopy, "--remove-section", ".codesign", unsigned],
                        f"remove the old code signature from {binary}",
                    )
                self._run_tool(
                    [
                        signer,
                        "sign",
                        "-inFile",
                        unsigned,
                        "-outFile",
                        signed,
                        "-selfSign",
                        "1",
                    ],
                    f"sign {binary}",
                )
                if not os.path.isfile(signed) or self._elf_type(signed) not in (2, 3):
                    raise ConanInvalidConfiguration(
                        f"Signing did not produce a runnable ELF file for {binary}"
                    )
                if not self._has_codesign_section(objdump, signed):
                    raise ConanInvalidConfiguration(
                        f"Signing did not add a .codesign section to {binary}"
                    )
                os.replace(signed, binary)
                os.chmod(binary, original_mode)

    def _has_codesign_section(self, objdump, path):
        section_table = self._run_tool(
            [objdump, "-h", path], f"inspect ELF sections in {path}"
        )
        return any(
            ".codesign" in line.split()
            for line in section_table.splitlines()
        )

    def _run(self, args, cwd=None):
        self.run(" ".join(shlex.quote(str(arg)) for arg in args), cwd=cwd)

    @staticmethod
    def _run_tool(command, action):
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=60,
            )
        except (OSError, subprocess.SubprocessError) as error:
            raise ConanInvalidConfiguration(f"Unable to {action}: {error}") from error
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip()
            raise ConanInvalidConfiguration(
                f"Unable to {action}: {detail or 'tool exited unsuccessfully'}"
            )
        return result.stdout

    @staticmethod
    def _elf_type(path):
        try:
            with open(path, "rb") as binary:
                header = binary.read(18)
        except OSError as error:
            raise ConanInvalidConfiguration(
                f"Unable to inspect installed file {path}: {error}"
            ) from error
        if len(header) < 18 or header[:4] != b"\x7fELF":
            return None
        byte_order = {1: "little", 2: "big"}.get(header[5])
        if byte_order is None:
            raise ConanInvalidConfiguration(
                f"Unsupported ELF byte order in installed file {path}"
            )
        return int.from_bytes(header[16:18], byte_order)

    @staticmethod
    def _resolve_tool(environment_variable, executable):
        configured = os.environ.get(environment_variable)
        candidate = configured or executable
        resolved = shutil.which(candidate)
        if (
            not resolved
            and os.path.isfile(candidate)
            and os.access(candidate, os.X_OK)
        ):
            resolved = os.path.abspath(candidate)
        if (
            not resolved
            or not os.path.isfile(resolved)
            or not os.access(resolved, os.X_OK)
        ):
            raise ConanInvalidConfiguration(
                f"Required tool {executable} was not found; set "
                f"{environment_variable} or add it to PATH"
            )
        return os.path.abspath(resolved)
