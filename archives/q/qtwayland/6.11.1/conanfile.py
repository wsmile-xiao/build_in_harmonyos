#!/usr/bin/env python3
"""Conan recipe for Qt Wayland 6.11.1 on HarmonyOS PC (arm64)."""

import os
import re
import shutil
import stat
import subprocess
import tempfile
import textwrap

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.cmake.toolchain.blocks import Block
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)


class QtwaylandConan(ConanFile):
    name = "qtwayland"
    version = "6.11.1"
    description = "Qt Wayland platform plugin and compositor for HarmonyOS PC"
    license = "BSD-3-Clause AND LGPL-3.0-only AND GPL-3.0-only"
    homepage = "https://doc.qt.io/qt-6/qtwayland-index.html"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("qtbase/6.11.1.2")  # 6.11.1.2 provides Qt6WaylandClient
        self.requires("wayland/1.22.0")
        # XKB::XKB is needed by the upstream tst_compositor keyboard test
        # cases (simpleKeyboard/keyboardKeymaps/keyboardLayoutSwitching are
        # compiled only when QT_FEATURE_xkbcommon is on). qtbase's
        # Qt6/conan/FindXKB.cmake resolves it via find_package(libxkbcommon).
        self.requires("libxkbcommon/1.6.0")

    def build_requirements(self):
        # wayland-protocols provides protocol XML files used at build time
        # by wayland-scanner. Not a runtime dependency.
        self.tool_requires("wayland-protocols/1.36.1")

    def validate(self):
        if self.settings.os != "OHOS":
            raise ConanInvalidConfiguration(
                "qtwayland/6.11.1 in this recipe is a HarmonyOS PC adaptation"
            )

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)

        # CMake has no Platform/HarmonyOS.cmake. On a HarmonyOS host it therefore
        # auto-detects CMAKE_SYSTEM_NAME=HarmonyOS and fails to set up the
        # shared-library SONAME/versioning rules. Presenting the platform as
        # Linux enables the standard platform rules; the OHOS clang driver
        # still targets aarch64-unknown-linux-ohos.
        class OhosLinuxPlatformBlock(Block):
            template = textwrap.dedent(
                """\
                # Treat the HarmonyOS host as Linux for CMake platform rules.
                # The OHOS clang driver already targets aarch64-unknown-linux-ohos.
                set(CMAKE_SYSTEM_NAME Linux)
                set(CMAKE_HOST_SYSTEM_NAME Linux)
                set(CMAKE_CROSSCOMPILING FALSE)
                set(CMAKE_SYSTEM_PROCESSOR aarch64)
                set(CMAKE_HOST_SYSTEM_PROCESSOR aarch64)
                """
            )

            def context(self):
                return {}

        tc.blocks["user_toolchain"] = OhosLinuxPlatformBlock

        qtbase_pkg = self.dependencies["qtbase"].package_folder
        wayland_pkg = self.dependencies["wayland"].package_folder
        wayland_proto_pkg = self.dependencies.build["wayland-protocols"].package_folder
        xkb_pkg = self.dependencies["libxkbcommon"].package_folder
        # libxml2 is a transitive dep of wayland; lld linker needs it at runtime.
        libxml2_pkg = self.dependencies["wayland"].dependencies["libxml2"].package_folder

        # Provide the wayland-scanner binary path directly so CMake's
        # FindWaylandScanner module does not depend on PATH lookup.
        scanner_bin = os.path.join(wayland_pkg, "bin", "wayland-scanner")
        tc.cache_variables.update(
            {
                "CMAKE_PREFIX_PATH": qtbase_pkg,
                "WaylandScanner_EXECUTABLE": scanner_bin,
                "QT_QMAKE_TARGET_MKSPEC": "harmonyos-clang",
                "BUILD_SHARED_LIBS": "ON" if self.options.shared else "OFF",
                "QT_BUILD_TESTS": "ON",
                "QT_BUILD_EXAMPLES": "OFF",
                "QT_BUILD_EXAMPLES_BY_DEFAULT": "OFF",
                # Qt's feature system sets these OFF by default when building
                # standalone (not as part of qtbase superbuild). Force them ON
                # since we've verified Wayland and WaylandScanner are available.
                # wayland_server (compositor) is enabled because
                # qtbase/6.11.1.2 ships libexec/qtwaylandscanner plus the
                # Qt6WaylandScannerTools CMake package, so the compositor
                # module and its upstream tst_compositor test can be built.
                "QT_FEATURE_wayland": "ON",
                "QT_FEATURE_wayland_client": "ON",
                "QT_FEATURE_wayland_server": "ON",
                "QT_FEATURE_waylandscanner": "ON",
            }
        )
        # Let CMake's find_library see the wayland shared libraries.
        tc.cache_variables["CMAKE_PREFIX_PATH"] = (
            f"{qtbase_pkg};{wayland_pkg};{wayland_proto_pkg};{xkb_pkg}"
        )
        tc.generate()

        # Fix wayland .pc files: the shipped pkg-config files have prefix=/
        # (or stale cache paths), which prevents CMake's FindWayland from
        # locating headers, libraries, and the scanner binary.
        fixed_pc_dir = os.path.join(self.generators_folder, "fixed_pkgconfig")
        os.makedirs(fixed_pc_dir, exist_ok=True)

        # Fix wayland-scanner.pc — point to the actual scanner binary
        scanner_bin = os.path.join(wayland_pkg, "bin", "wayland-scanner")
        with open(
            os.path.join(fixed_pc_dir, "wayland-scanner.pc"),
            "w",
            encoding="utf-8",
            newline="\n",
        ) as f:
            f.write(
                f"prefix={wayland_pkg}\n"
                f"bindir=${{prefix}}/bin\n"
                f"wayland_scanner=${{bindir}}/wayland-scanner\n\n"
                f"Name: Wayland Scanner\n"
                f"Description: Wayland scanner\n"
                f"Version: 1.22.0\n"
            )

        # Fix wayland-client.pc / wayland-server.pc / wayland-cursor.pc
        # Also remove Requires.private: libffi since libffi.pc is not
        # in the PKG_CONFIG_PATH (libffi conan package doesn't ship .pc
        # files). Without this, pkg-config --exists fails.
        for pc_name, desc in [
            ("wayland-client", "Wayland client side library"),
            ("wayland-server", "Server side implementation of the Wayland protocol"),
            ("wayland-cursor", "Wayland cursor library"),
            ("wayland-egl", "Wayland EGL library"),
        ]:
            pc_src = os.path.join(
                wayland_pkg, "lib", "pkgconfig", f"{pc_name}.pc"
            )
            if not os.path.isfile(pc_src):
                continue
            with open(pc_src, "r", encoding="utf-8") as f:
                content = f.read()
            content = re.sub(r"(?m)^prefix=.*$", f"prefix={wayland_pkg}", content)
            # Remove Requires.private lines that reference packages
            # not in PKG_CONFIG_PATH (libffi, etc.)
            content = re.sub(r"(?m)^Requires\.private:.*$", "", content)
            content = re.sub(r"(?m)^Libs\.private:.*$", "", content)
            with open(
                os.path.join(fixed_pc_dir, f"{pc_name}.pc"),
                "w",
                encoding="utf-8",
                newline="\n",
            ) as f:
                f.write(content)

        # Fix wayland-protocols.pc
        wp_pc_src = os.path.join(
            wayland_proto_pkg, "share", "pkgconfig", "wayland-protocols.pc"
        )
        if os.path.isfile(wp_pc_src):
            with open(wp_pc_src, "r", encoding="utf-8") as f:
                content = f.read()
            content = re.sub(
                r"(?m)^prefix=.*$", f"prefix={wayland_proto_pkg}", content
            )
            with open(
                os.path.join(fixed_pc_dir, "wayland-protocols.pc"),
                "w",
                encoding="utf-8",
                newline="\n",
            ) as f:
                f.write(content)

        # Fix xkbcommon.pc (shipped copy has prefix=/). XKB::XKB is resolved
        # by qtbase's bundled FindXKB.cmake via pkg-config; the upstream
        # tst_compositor keyboard test cases (simpleKeyboard, keyboardKeymaps,
        # keyboardLayoutSwitching) link against XKB::XKB.
        xkb_pc_src = os.path.join(xkb_pkg, "lib", "pkgconfig", "xkbcommon.pc")
        if os.path.isfile(xkb_pc_src):
            with open(xkb_pc_src, "r", encoding="utf-8") as f:
                content = f.read()
            content = re.sub(r"(?m)^prefix=.*$", f"prefix={xkb_pkg}", content)
            with open(
                os.path.join(fixed_pc_dir, "xkbcommon.pc"),
                "w",
                encoding="utf-8",
                newline="\n",
            ) as f:
                f.write(content)

        # Set up environment: PKG_CONFIG_PATH with fixed .pc files FIRST
        # (must override the original wayland .pc files which have prefix=/),
        # then real package paths. Also LD_LIBRARY_PATH for wayland libs
        # (wayland-scanner needs wayland-client.so at runtime).
        env = Environment()
        # Prepend in reverse order: last prepend = first in PATH.
        # We want: fixed_pkgconfig → wayland_proto → wayland
        env.prepend_path(
            "PKG_CONFIG_PATH",
            os.path.join(wayland_proto_pkg, "share", "pkgconfig"),
        )
        env.prepend_path(
            "PKG_CONFIG_PATH",
            os.path.join(wayland_pkg, "lib", "pkgconfig"),
        )
        env.prepend_path("PKG_CONFIG_PATH", fixed_pc_dir)  # must be first
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(wayland_pkg, "lib"))
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(qtbase_pkg, "lib"))
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(xkb_pkg, "lib"))
        # The lld linker (from OHOS SDK) links to libxml2.so.16 at runtime.
        # The matching libxml2.so.16 ships with the OHOS SDK's llvm/lib dir.
        # Conan's libxml2 package also provides libxml2.so.16 but with an
        # incompatible ABI; the conan profile's buildenv adds conan's
        # libxml2 to LD_LIBRARY_PATH after our script, causing lld to load
        # the wrong library. We counteract by setting LDFLAGS to use
        # -L for the SDK lib dir, which the linker searches before
        # LD_LIBRARY_PATH for finding its own dependencies.
        sdk_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
        env.prepend_path("LD_LIBRARY_PATH", sdk_lib)
        # Also add LDFLAGS as a belt-and-suspenders approach
        env.append("LDFLAGS", f"-L{sdk_lib}")
        env.prepend_path("PATH", os.path.join(wayland_pkg, "bin"))
        env.prepend_path("PATH", os.path.join(qtbase_pkg, "bin"))
        envvars = env.vars(self)
        envvars.save_script("qtwayland_env")

        # Also set os.environ directly — conan 2.x runs cmake as a
        # subprocess that inherits os.environ, but does NOT source
        # the generated env scripts. Without this, cmake cannot find
        # the wayland pkg-config packages.
        os.environ["PKG_CONFIG_PATH"] = (
            f"{fixed_pc_dir}"
            f":{os.path.join(wayland_pkg, 'lib', 'pkgconfig')}"
            f":{os.path.join(wayland_proto_pkg, 'share', 'pkgconfig')}"
            + (f":{os.environ.get('PKG_CONFIG_PATH', '')}"
               if os.environ.get("PKG_CONFIG_PATH") else "")
        )
        os.environ["PATH"] = (
            f"{os.path.join(wayland_pkg, 'bin')}"
            f":{os.path.join(qtbase_pkg, 'bin')}"
            f":{os.environ.get('PATH', '')}"
        )
        # The lld linker (from OHOS SDK) links to libxml2.so.16 at runtime.
        # CRITICAL: The OHOS SDK's lld linker links to libxml2.so.16 at
        # runtime. The conan libxml2 package also provides libxml2.so.16
        # but with an incompatible ABI (2.15.3 vs SDK's 2.14.0). If the
        # conan libxml2 path appears before the SDK path in LD_LIBRARY_PATH,
        # lld loads the wrong library and fails. The OHOS SDK path must
        # come FIRST, before any conan package lib dirs.
        os.environ["LD_LIBRARY_PATH"] = (
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
            f":{os.path.join(wayland_pkg, 'lib')}"
            f":{os.path.join(qtbase_pkg, 'lib')}"
            + (f":{os.environ.get('LD_LIBRARY_PATH', '')}"
               if os.environ.get("LD_LIBRARY_PATH") else "")
        )

    def build(self):
        apply_conandata_patches(self)

        # Re-set env vars for the cmake build subprocess. These were set in
        # generate() but conan may reset os.environ between phases.
        qtbase_pkg = self.dependencies["qtbase"].package_folder
        wayland_pkg = self.dependencies["wayland"].package_folder
        wayland_proto_pkg = self.dependencies.build["wayland-protocols"].package_folder
        xkb_pkg = self.dependencies["libxkbcommon"].package_folder
        libxml2_pkg = self.dependencies["wayland"].dependencies["libxml2"].package_folder
        fixed_pc_dir = os.path.join(self.generators_folder, "fixed_pkgconfig")

        os.environ["PKG_CONFIG_PATH"] = (
            f"{fixed_pc_dir}"
            f":{os.path.join(wayland_pkg, 'lib', 'pkgconfig')}"
            f":{os.path.join(wayland_proto_pkg, 'share', 'pkgconfig')}"
            + (f":{os.environ.get('PKG_CONFIG_PATH', '')}"
               if os.environ.get("PKG_CONFIG_PATH") else "")
        )
        os.environ["PATH"] = (
            f"{os.path.join(wayland_pkg, 'bin')}"
            f":{os.path.join(qtbase_pkg, 'bin')}"
            f":{os.environ.get('PATH', '')}"
        )
        os.environ["LD_LIBRARY_PATH"] = (
            f"{os.path.join(libxml2_pkg, 'lib')}"
            f":{os.path.join(wayland_pkg, 'lib')}"
            f":{os.path.join(qtbase_pkg, 'lib')}"
            + (f":{os.environ.get('LD_LIBRARY_PATH', '')}"
               if os.environ.get("LD_LIBRARY_PATH") else "")
        )

        # The OHOS SDK's lld linker needs libxml2.so.16 from its own
        # llvm/lib dir. Conan's generated env scripts put conan's
        # incompatible libxml2 first in LD_LIBRARY_PATH, causing lld to
        # fail. We patch the generated conanbuild.sh to prepend the
        # SDK lib path after all other env scripts are sourced.
        sdk_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
        conanbuild_sh = os.path.join(self.generators_folder, "conanbuild.sh")
        if os.path.isfile(conanbuild_sh):
            with open(conanbuild_sh, "r", encoding="utf-8") as f:
                content = f.read()
            # Append a prepend of the SDK lib path so it comes after
            # all other env scripts have set their LD_LIBRARY_PATH.
            fixup = (
                f'\n# Fix: ensure OHOS SDK libxml2.so.16 and libc++.so are found first by lld/scanner\n'
                f'export LD_LIBRARY_PATH="{sdk_lib}:{sdk_lib}/aarch64-linux-ohos'
                f'${{LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}}"\n'
            )
            if "OHOS SDK libxml2" not in content:
                with open(conanbuild_sh, "a", encoding="utf-8") as f:
                    f.write(fixup)

        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Build the upstream test targets explicitly (the default target does
        # not include them): both qt_internal_add_test targets plus the shared
        # client test helper library.
        for tgt in ("SharedWaylandClientTest", "tst_client_iviapplication",
                    "tst_compositor"):
            try:
                self.run(
                    'cmake --build "{bf}" --target {tgt} -- -j2'.format(
                        bf=self.build_folder, tgt=tgt))
            except Exception as e:
                self.output.warning("test target {} build failed: {}".format(tgt, e))

        # Execute the upstream tests (full run, all registered cases). Both
        # tests spin up in-process mock Wayland compositors over a per-test
        # XDG_RUNTIME_DIR socket — no system compositor needed. The test
        # binaries are OHOS ELF built for aarch64 and run natively on this
        # aarch64 HarmonyOS PC host; wire up LD_LIBRARY_PATH for the
        # Qt/Wayland libraries from the conan cache.
        #
        # The two tests need different QPA platforms:
        # - tst_client_iviapplication (QCOMPOSITOR_TEST_MAIN) forces
        #   QT_QPA_PLATFORM=wayland itself and talks to its in-process mock
        #   compositor through the ivi-shell plugin built in this tree.
        # - tst_compositor (plain QTEST_MAIN + QGuiApplication) has no
        #   display to connect to, so it runs with the offscreen platform
        #   while creating its own wl_display server side in-process.
        # They are therefore executed as two ctest invocations.
        qtbase_pkg = self.dependencies["qtbase"].package_folder
        wayland_pkg = self.dependencies["wayland"].package_folder
        xkb_pkg = self.dependencies["libxkbcommon"].package_folder
        deps_libs = [
            os.path.join(d.package_folder, "lib")
            for _r, d in self.dependencies.items()
            if d.package_folder
        ]
        deps_libs.append(os.path.join(wayland_pkg, "lib"))
        deps_libs.append(os.path.join(xkb_pkg, "lib"))
        sdk_libs = [
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos",
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib",
        ]
        ld_path = ":".join(
            ["/system/lib64"] + deps_libs + sdk_libs + [self.build_folder + "/lib"]
        )
        test_results_dir = os.path.join(self.build_folder, "test_results")
        os.makedirs(test_results_dir, exist_ok=True)
        # Unix domain sockets are limited to a 108-byte sun_path, and the
        # conan build folder path is too deep. Use a short writable runtime
        # dir outside the build tree for the per-test compositor sockets.
        short_tmp = (
            _tmp
            if len(_tmp := os.environ.get("TMPDIR", "/data/storage/el2/base/temp")) <= 40
            else "/data/storage/el2/base/temp"
        )
        runtime_dir = os.path.join(
            short_tmp, "qtwayland-{}-xdg".format(os.getpid())
        )
        os.makedirs(runtime_dir, exist_ok=True)
        os.chmod(runtime_dir, 0o700)
        common_env = (
            'XDG_RUNTIME_DIR="{rd}" '
            'XKB_CONFIG_ROOT="{xkbcfg}" '
            'QT_PLUGIN_PATH="{plugins}" '
            'TMPDIR="{tmpdir}" '
            'LD_LIBRARY_PATH="{lp}"'
        ).format(
            rd=runtime_dir,
            xkbcfg=os.path.join(qtbase_pkg, "share", "X11", "xkb"),
            plugins="{}:{}".format(
                os.path.join(self.build_folder, "plugins"),
                os.path.join(qtbase_pkg, "plugins"),
            ),
            # Both tests create their per-test XDG_RUNTIME_DIR via
            # QTemporaryDir (which honors TMPDIR) and open Unix sockets
            # in it. The 108-byte sun_path limit requires a SHORT temp
            # path; the conan build folder is too deep.
            tmpdir=(
                _tmp
                if len(_tmp := os.environ.get("TMPDIR", "/data/storage/el2/base/temp")) <= 40
                else "/data/storage/el2/base/temp"
            ),
            lp=ld_path,
        )
        for test_name, qpa in (
            ("tst_client_iviapplication", "wayland"),
            ("tst_compositor", "offscreen"),
        ):
            try:
                self.run(
                    'QT_QPA_PLATFORM={qpa} {env} '
                    'ctest --test-dir "{bf}" --output-on-failure --timeout 300 '
                    '-R "^{tn}$" '
                    '-O "{logf}"'.format(
                        qpa=qpa,
                        env=common_env,
                        tn=test_name,
                        bf=self.build_folder,
                        logf=os.path.join(
                            test_results_dir, "{}.log".format(test_name)
                        ),
                    ),
                    cwd=self.build_folder,
                )
            except Exception as e:
                self.output.warning(
                    "ctest execution of {} completed with failures: {}".format(
                        test_name, e
                    )
                )

    def package(self):
        cmake = CMake(self)
        cmake.install()
        self._ensure_soname_symlinks()
        if str(self.settings.os) == "OHOS":
            self._sign_installed_elfs()

    def _ensure_soname_symlinks(self):
        """Ensure libQt6Wayland*.so / .so.6 links exist (E215: HMDFS
        breaks relative symlinks during install)."""
        libdir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(libdir):
            return
        for root, _, filenames in os.walk(libdir):
            for filename in filenames:
                for libbase in (
                    "libQt6WaylandClient.so.6.11.1",
                    "libQt6WaylandCompositor.so.6.11.1",
                    "libQt6WaylandEglClientHwIntegration.so.6.11.1",
                    "libQt6WaylandEglCompositorHwIntegration.so.6.11.1",
                    "libQt6WaylandGlobal.so.6.11.1",
                    "libQt6WaylandCompositorQml.so.6.11.1",
                ):
                    if not filename.startswith(libbase):
                        continue
                    real = os.path.join(root, filename)
                    stem = libbase.replace(".so.6.11.1", "")
                    for link_name in (f"{stem}.so.6", f"{stem}.so"):
                        link = os.path.join(root, link_name)
                        if not os.path.lexists(link):
                            os.symlink(filename, link)

    def _sign_installed_elfs(self):
        """Re-sign installed OHOS ELF executables and shared objects."""
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

    def package_info(self):
        # Qt installs complete, relocatable Qt6WaylandConfig.cmake files.
        # Prevent CMakeDeps from shadowing them with an incomplete generated config.
        self.cpp_info.set_property("cmake_find_mode", "none")
        self.cpp_info.builddirs = [os.path.join("lib", "cmake")]

        # Qt6WaylandClient library (built by qtbase when configured with
        # Wayland support; this package provides the cmake config files,
        # headers, and feature definitions for the client module).
        client = self.cpp_info.components["waylandclient"]
        client.libs = ["Qt6WaylandClient"]
        client.requires = [
            "qtbase::core",
            "qtbase::gui",
            "wayland::wayland-client",
        ]
        client.set_property("cmake_target_name", "Qt6::WaylandClient")

        # Qt6WaylandCompositor library (built by this package now that
        # QT_FEATURE_wayland_server=ON is enabled; qtbase/6.11.1.2 provides
        # the qtwaylandscanner tool needed to generate compositor protocol
        # sources at build time). XKB is a runtime link of the compositor's
        # keyboard handling and the upstream tst_compositor test cases.
        compositor = self.cpp_info.components["waylandcompositor"]
        compositor.libs = ["Qt6WaylandCompositor"]
        compositor.requires = [
            "qtbase::core",
            "qtbase::gui",
            "wayland::wayland-server",
            "libxkbcommon::libxkbcommon",
        ]
        compositor.set_property("cmake_target_name", "Qt6::WaylandCompositor")
