#!/usr/bin/env python3
"""Conan recipe for the QtBase 6.0.0 HarmonyOS PC feature subset."""

import os
import re
import shutil
import stat
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.cmake.toolchain.blocks import Block
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


UPSTREAM_TEST_TARGETS = (
    "tst_qabstractnetworkcache",
    "tst_qabstractsocket",
    "tst_qdnslookup",
    "tst_qdnslookup_appless",
    "tst_qhostaddress",
    "tst_qlocalsocket",
    "tst_qnetworkaccessmanager",
    "tst_qnetworkaddressentry",
    "tst_qnetworkcachemetadata",
    "tst_qnetworkcookie",
    "tst_qnetworkcookiejar",
    "tst_qnetworkdatagram",
    "tst_qnetworkdiskcache",
    "tst_qnetworkinterface",
    "tst_qnetworkreply",
    "tst_qnetworkrequest",
    "tst_qpassworddigestor",
    "tst_qsslcipher",
    "tst_qsslellipticcurve",
    "tst_qsslerror",
    "tst_qsslkey",
    "tst_qtcpserver",
    "tst_qudpsocket",
    "tst_qeventloop",
    "tst_qthread",
    "tst_qimage",
    "tst_qpainter",
    "tst_qwidget",
    "tst_qdom",
)
UPSTREAM_CTEST_TARGETS = UPSTREAM_TEST_TARGETS
UPSTREAM_TEST_HELPER_TARGETS = ("socketprocess",)


class Qt6Conan(ConanFile):
    name = "qt6"
    version = "6.0"
    description = (
        "QtBase Core, Concurrent, Network, raster Gui, offscreen Widgets, "
        "PrintSupport, Test and Xml for HarmonyOS PC"
    )
    license = "BSD-3-Clause AND LGPL-3.0-only AND GPL-3.0-only"
    homepage = "https://doc.qt.io/qt-6/qtbase-index.html"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True]}
    default_options = {"shared": True}

    def requirements(self):
        # Qt 6.0 only registers the OpenSSL-backed qsslkey target when
        # its OpenSSL development files are present at configure time.
        self.requires("openssl/3.5.6.1.2")

    def configure(self):
        # Qt loads OpenSSL at runtime; ship a matching shared OpenSSL 3
        # dependency so clean CI and Conan consumers have that runtime.
        self.options["openssl"].shared = True

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        if self.settings.os != "OHOS" or self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                "qt6/6.0 supports HarmonyOS PC AArch64 only"
            )

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        openssl_root = self.dependencies["openssl"].package_folder
        self.output.info(f"Using Conan OpenSSL 3 runtime package at {openssl_root}")
        # CMake does not load Qt's source-tree Platform/HarmonyOS.cmake while
        # selecting system modules. Reuse Linux platform rules, as QtBase 6.11
        # does, while Conan continues to provide the OHOS compiler and SDK.
        class OhosLinuxPlatformBlock(Block):
            template = """\
set(CMAKE_SYSTEM_NAME Linux)
set(CMAKE_HOST_SYSTEM_NAME Linux)
set(CMAKE_CROSSCOMPILING FALSE)
set(CMAKE_SYSTEM_PROCESSOR aarch64)
set(CMAKE_HOST_SYSTEM_PROCESSOR aarch64)
"""

            def context(self):
                return {}

        tc.blocks["user_toolchain"] = OhosLinuxPlatformBlock
        tc.cache_variables.update(
            {
                "OPENSSL_ROOT_DIR": openssl_root,
                "INPUT_openssl": "runtime",
                "QT_QMAKE_TARGET_MKSPEC": "harmonyos-clang",
                "BUILD_SHARED_LIBS": "ON",
                "QT_BUILD_TESTS": "ON",
                "QT_BUILD_TESTS_BY_DEFAULT": "OFF",
                "QT_BUILD_EXAMPLES": "OFF",
                "QT_BUILD_EXAMPLES_BY_DEFAULT": "OFF",
                "FEATURE_gui": "ON",
                "FEATURE_network": "ON",
                "FEATURE_widgets": "ON",
                "FEATURE_xml": "ON",
                # Qt 6.0 emits QTuioTouchPlugin and qtuiotouchplugin make
                # targets whose generated directories differ only by case.
                # HarmonyOS storage aliases those paths; this hardware-input
                # plugin is outside the package's offscreen feature scope.
                "FEATURE_tuiotouch": "OFF",
                "FEATURE_sql": "OFF",
                "FEATURE_testlib": "ON",
                "FEATURE_dbus": "OFF",
                "FEATURE_glib": "OFF",
                "FEATURE_opengl": "OFF",
                "FEATURE_opengles2": "OFF",
                "FEATURE_egl": "OFF",
                "FEATURE_eglfs": "OFF",
                "FEATURE_vulkan": "OFF",
                "FEATURE_xcb": "OFF",
                "FEATURE_xlib": "OFF",
                "FEATURE_linuxfb": "OFF",
                "FEATURE_vnc": "OFF",
                "FEATURE_evdev": "OFF",
                "FEATURE_libinput": "OFF",
                "FEATURE_mtdev": "OFF",
                "FEATURE_tslib": "OFF",
                "FEATURE_fontconfig": "OFF",
                "FEATURE_cups": "OFF",
                "FEATURE_icu": "OFF",
                "FEATURE_pkg_config": "OFF",
                "FEATURE_system_zlib": "OFF",
                "FEATURE_system_pcre2": "OFF",
                "FEATURE_system_freetype": "OFF",
                "FEATURE_system_harfbuzz": "OFF",
                "FEATURE_system_png": "OFF",
                "FEATURE_system_jpeg": "OFF",
                "INPUT_opengl": "no",
            }
        )
        # HarmonyOS exposes PTHREAD_CANCEL_* constants but omits the
        # pthread cancellation functions. Keep Qt's Android-style no-op
        # termination path instead of compiling calls the SDK cannot satisfy.
        tc.extra_cxxflags.append("-DQT_NO_PTHREAD_CANCEL")
        # Restrict the abstract local-socket behavior to this HarmonyOS QtBase
        # build; the private macro is not exported to package consumers.
        tc.extra_cxxflags.append("-DQT_BUILD_HARMONYOS_LOCAL_SOCKETS")
        # SO_PEERCRED and struct ucred are exposed by the HarmonyOS socket
        # headers when GNU socket extensions are enabled.
        tc.extra_cxxflags.append("-D_GNU_SOURCE")
        self.output.info(
            "pthread cancellation APIs unavailable; defining QT_NO_PTHREAD_CANCEL"
        )
        self.output.info(
            "HarmonyOS abstract local sockets enabled for this QtBase build"
        )
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        for target in UPSTREAM_TEST_HELPER_TARGETS:
            self.output.info(f"Building upstream Qt test helper {target}")
            cmake.build(target=target)
        for target in UPSTREAM_TEST_TARGETS:
            self.output.info(f"Building upstream Qt test target {target}")
            cmake.build(target=target)
        if can_run(self):
            test_env = Environment()
            test_env.define("QT_QPA_PLATFORM", "offscreen")
            test_env.define("QT_LOGGING_RULES", "qt.qpa.*=false")
            openssl_library_candidates = []
            openssl_dependency = self.dependencies["openssl"]
            for libdir in openssl_dependency.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(openssl_dependency.package_folder, libdir)
                openssl_library_candidates.append(libdir)
            if os.environ.get("OPENSSL_LIBDIR"):
                openssl_library_candidates.append(os.environ["OPENSSL_LIBDIR"])
            if os.environ.get("OPENSSL_ROOT_DIR"):
                openssl_root = os.environ["OPENSSL_ROOT_DIR"]
                openssl_library_candidates.extend(
                    [os.path.join(openssl_root, "lib"),
                     os.path.join(openssl_root, "lib64")]
                )
            configured_modules = os.environ.get("OPENSSL_MODULES")
            if configured_modules:
                openssl_library_candidates.append(
                    os.path.dirname(configured_modules)
                )
            openssl_library_candidates.append(
                os.path.join(os.path.expanduser("~"), ".harmonybrew", "lib")
            )
            openssl_runtime_candidates = []
            for candidate in dict.fromkeys(openssl_library_candidates):
                if not os.path.isfile(os.path.join(candidate, "libcrypto.so.3")):
                    continue
                modules_in_candidate = (
                    configured_modules
                    if configured_modules
                    and os.path.realpath(os.path.dirname(configured_modules))
                    == os.path.realpath(candidate)
                    else os.path.join(candidate, "ossl-modules")
                )
                legacy_in_candidate = os.path.join(modules_in_candidate, "legacy.so")
                openssl_runtime_candidates.append(
                    (candidate, modules_in_candidate, os.path.isfile(legacy_in_candidate))
                )

            # Prefer an OpenSSL 3 installation that contains its own legacy
            # provider. If explicit library and module paths disagree, derive
            # the modules directory from the selected library installation.
            openssl_runtime = next(
                (runtime for runtime in openssl_runtime_candidates if runtime[2]),
                openssl_runtime_candidates[0] if openssl_runtime_candidates else None,
            )
            if openssl_runtime and not openssl_runtime[2]:
                raise ConanInvalidConfiguration(
                    "OpenSSL 3 was found for Qt CTest, but its matching legacy "
                    "provider was not found; set OPENSSL_LIBDIR or "
                    "OPENSSL_ROOT_DIR to an OpenSSL 3 installation with "
                    "ossl-modules/legacy.so"
                )

            if openssl_runtime:
                openssl_libdir, openssl_modules, _ = openssl_runtime
                legacy_provider = os.path.join(openssl_modules, "legacy.so")
                # Qt's OpenSSL tests include legacy DES/RC2/RC4 key fixtures.
                # Use the same OpenSSL installation for Qt and its provider,
                # and activate it only for this CTest process. The HarmonyOS
                # system OpenSSL may have a different SONAME-compatible build
                # and no matching legacy provider module.
                test_env.prepend_path("LD_LIBRARY_PATH", openssl_libdir)
                openssl_config = os.path.join(
                    self.build_folder, "qt6-ctest-openssl3-legacy.cnf"
                )
                with open(openssl_config, "w", encoding="utf-8") as config_file:
                    config_file.write(
                        "openssl_conf = openssl_init\n"
                        "[openssl_init]\n"
                        "providers = provider_sect\n"
                        "[provider_sect]\n"
                        "default = default_sect\n"
                        "legacy = legacy_sect\n"
                        "[default_sect]\n"
                        "activate = 1\n"
                        "[legacy_sect]\n"
                        "activate = 1\n"
                    )
                test_env.define("OPENSSL_CONF", openssl_config)
                test_env.define("OPENSSL_MODULES", openssl_modules)
                self.output.info(
                    "OpenSSL CTest runtime and legacy provider matched at "
                    + openssl_libdir
                )
            pattern = "^({})$".format("|".join(UPSTREAM_CTEST_TARGETS))
            with test_env.vars(self).apply():
                self.run(
                    f'ctest --timeout 600 --output-on-failure -R "{pattern}"',
                    cwd=self.build_folder,
                )

    def package(self):
        cmake = CMake(self)
        cmake.install()
        if str(self.settings.os) == "OHOS":
            self._stamp_plugin_sonames()
            self._sign_installed_elfs()

    def _stamp_plugin_sonames(self):
        """Give Qt MODULE plugins a SONAME and align their exported targets."""
        plugin_root = os.path.join(self.package_folder, "plugins")
        if not os.path.isdir(plugin_root):
            return

        plugins = []
        for root, _, filenames in os.walk(plugin_root):
            for filename in sorted(filenames):
                if filename.endswith(".so") or ".so." in filename:
                    path = os.path.join(root, filename)
                    if os.path.isfile(path) and not os.path.islink(path):
                        plugins.append((path, filename))
        if not plugins:
            return

        patchelf = self._resolve_tool("PATCHELF", "patchelf")
        sonames = {}
        for path, filename in plugins:
            try:
                current = self._run_tool(
                    [patchelf, "--print-soname", path],
                    f"read the SONAME of Qt plugin {filename}",
                ).strip()
            except ConanInvalidConfiguration:
                current = ""
            if not current:
                self._run_tool(
                    [patchelf, "--set-soname", filename, path],
                    f"set the SONAME of Qt plugin {filename}",
                )
                current = filename
            relative_path = os.path.relpath(path, self.package_folder).replace(
                os.sep, "/"
            )
            sonames[relative_path] = current

        cmake_root = os.path.join(self.package_folder, "lib", "cmake")
        for root, _, filenames in os.walk(cmake_root):
            for filename in filenames:
                if not filename.endswith(".cmake"):
                    continue
                cmake_file = os.path.join(root, filename)
                with open(cmake_file, "r", encoding="utf-8") as stream:
                    contents = stream.read()
                if "IMPORTED_NO_SONAME" not in contents:
                    continue

                location = re.search(
                    r'IMPORTED_LOCATION(?:_\w+)?\s+"\$\{_IMPORT_PREFIX\}/([^\"]+)"',
                    contents,
                )
                relative_path = (
                    os.path.normpath(location.group(1)).replace("\\", "/")
                    if location
                    else None
                )
                plugin_soname = sonames.get(relative_path) if relative_path else None
                if not plugin_soname:
                    continue

                def replace_no_soname(match):
                    suffix = match.group(1) or ""
                    return f'IMPORTED_SONAME{suffix} "{plugin_soname}"'

                updated, count = re.subn(
                    r'IMPORTED_NO_SONAME(_\w+)?\s+"TRUE"',
                    replace_no_soname,
                    contents,
                )
                if count:
                    with open(cmake_file, "w", encoding="utf-8") as stream:
                        stream.write(updated)

    def _sign_installed_elfs(self):
        """Re-sign installed OHOS ELF executables and shared objects."""
        binaries = []
        for root, _, filenames in os.walk(self.package_folder):
            for filename in filenames:
                candidate = os.path.join(root, filename)
                if os.path.islink(candidate):
                    continue
                if self._elf_type(candidate) in (2, 3):
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
        return any(".codesign" in line.split() for line in section_table.splitlines())

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
        """Return the ELF e_type value, or None for a non-ELF file."""
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
        if not resolved and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
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

    def package_info(self):
        # Qt installs complete relocatable Qt6Config.cmake files; do not have
        # CMakeDeps shadow them with generated partial package metadata.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]

        core = self.cpp_info.components["core"]
        core.libs = ["Qt6Core"]
        core.set_property("cmake_target_name", "Qt6::Core")

        network = self.cpp_info.components["network"]
        network.libs = ["Qt6Network"]
        network.requires = ["core"]
        network.set_property("cmake_target_name", "Qt6::Network")

        gui = self.cpp_info.components["gui"]
        gui.libs = ["Qt6Gui"]
        gui.requires = ["core"]
        gui.set_property("cmake_target_name", "Qt6::Gui")

        widgets = self.cpp_info.components["widgets"]
        widgets.libs = ["Qt6Widgets"]
        widgets.requires = ["core", "gui"]
        widgets.set_property("cmake_target_name", "Qt6::Widgets")

        xml = self.cpp_info.components["xml"]
        xml.libs = ["Qt6Xml"]
        xml.requires = ["core"]
        xml.set_property("cmake_target_name", "Qt6::Xml")

        concurrent = self.cpp_info.components["concurrent"]
        concurrent.libs = ["Qt6Concurrent"]
        concurrent.requires = ["core"]
        concurrent.set_property("cmake_target_name", "Qt6::Concurrent")

        printsupport = self.cpp_info.components["printsupport"]
        printsupport.libs = ["Qt6PrintSupport"]
        printsupport.requires = ["core", "gui", "widgets"]
        printsupport.set_property("cmake_target_name", "Qt6::PrintSupport")

        test = self.cpp_info.components["test"]
        test.libs = ["Qt6Test"]
        test.requires = ["core"]
        test.set_property("cmake_target_name", "Qt6::Test")
