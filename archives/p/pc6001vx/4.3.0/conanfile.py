#!/usr/bin/env python3
"""Conan recipe — pc6001vx 4.3.0 (Qt6 + qmake, HarmonyOS PC aarch64).

PC-6001 / PC-6001mkII / PC-6601 emulator: the cross-platform edition of
eighttails' PC6001V. Upstream builds the application with qmake and needs
Qt 6.4 or newer (Qt Core/Gui/Widgets/Network plus Qt Multimedia for sound
output); SDL2 is used for joystick input only (PC6001VX.pro: `PKGCONFIG +=
sdl2` unless NOJOYSTICK is defined). The adaptation brief described the
project as an "SDL2 emulator"; the 4.3.0 source tree is Qt6/qmake based, so
this recipe adapts the real upstream build — the deviation is recorded in
notes.md.

HarmonyOS PC adaptation (full rationale in notes.md):
- qtbase/6.11.1 from the OHOS 制品仓 is built without OpenGL and installs only
  the `minimal`/`offscreen` QPA plugins, so NO_HWACCEL is defined and the
  X11/xcb backend is switched off (patch 0001).
- Qt Multimedia ships as its own Conan package: the qmake module files under
  the qtbase prefix cannot resolve `QT += multimedia` in a split-prefix
  install, so the recipe passes the real include/library directories on the
  qmake command line (patch 0001).
- SysV semaphores (semget) are not usable on OHOS PC, which breaks Qt's
  QSharedMemory and therefore the bundled SingleApplication single-instance
  helper; NOSINGLEAPP is the upstream-supported configuration for such
  targets (used by the Android build as well).
- musl has no <libintl.h>: NOLIBINTL, as upstream does for Android.
- lrelease comes from the qttools package (Qt Linguist tools are not part of
  qtbase); the translated .qm files stay embedded in the binary.
"""
import os
import shlex
import shutil
import stat
import subprocess
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import build_jobs
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class Pc6001vxConan(ConanFile):
    name = "pc6001vx"
    version = "4.3.0"
    description = "PC-6001 emulator (cross-platform Qt6 edition, SDL2 joystick input)"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/eighttails/PC6001VX"
    url = ""  # CI fills this

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # W0 verified against the ohpcd 制品仓 (conan download --only-recipe):
        # qtbase/6.11.1, qtmultimedia/6.11.1, qttools/6.11.1, sdl2/2.30.10.
        self.requires("qtbase/6.11.1", transitive_headers=True, transitive_libs=True)
        self.requires("qtmultimedia/6.11.1", transitive_headers=True, transitive_libs=True)
        # Joystick input only; the 制品仓 package is static (libSDL2.a), so the
        # emulator ends up with no SDL2 runtime dependency.
        self.requires("sdl2/2.30.10")

    def build_requirements(self):
        # lrelease: `CONFIG += lrelease embed_translations` in PC6001VX.pro is
        # executed by Qt Linguist tools, which live in qttools, not in qtbase.
        self.tool_requires("qttools/6.11.1")

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "pc6001vx targets Linux-compatible UNIX platforms"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        # CI worker network jitter hardening: explicit Conan-level retries.
        get(self, **self.conan_data["sources"], strip_root=True,
            retry=5, retry_wait=10)

    def generate(self):
        VirtualBuildEnv(self).generate()

        qtbase = self.dependencies["qtbase"].package_folder
        qtmultimedia = self.dependencies["qtmultimedia"].package_folder
        qttools = self.dependencies.build["qttools"].package_folder

        # PC6001VX.pro asks pkg-config for `sdl2` (packagesExist/PKGCONFIG).
        # The .pc file shipped inside the static sdl2 package is not
        # relocatable (prefix=/), so consume Conan's rewritten pkg-config
        # files instead of the packaged one.
        PkgConfigDeps(self).generate()

        env = Environment()
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        # qmake runs moc/uic/rcc (RPATH $ORIGIN/../lib, self-contained) and
        # lrelease from qttools. The Linguist tools are installed without an
        # RPATH, so they need the Qt libraries on the loader path while
        # `make` runs the translation step.
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(qtbase, "lib"))
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(qttools, "lib"))
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(qtmultimedia, "lib"))
        env.vars(self).save_script("pc6001vx_build_env")

    def build(self):
        apply_conandata_patches(self)

        qtbase = self.dependencies["qtbase"].package_folder
        qtmultimedia = self.dependencies["qtmultimedia"].package_folder
        qttools = self.dependencies.build["qttools"].package_folder

        qmake = os.path.join(qtbase, "bin", "qmake6")
        if not os.path.isfile(qmake):
            qmake = os.path.join(qtbase, "bin", "qmake")

        # Platform defines. All of them are upstream switches; none of them
        # modifies emulator behaviour beyond what the platform cannot provide.
        defines = (
            # No OpenGL in the OHOS qtbase package (no Qt6OpenGLWidgets module).
            "NO_HWACCEL",
            # musl has no <libintl.h>; upstream uses the same switch on Android.
            "NOLIBINTL",
            # No X server and no Qt xcb platform plugin on OHOS PC.
            "P6VX_NO_X11",
            # SysV semaphores (semget) are unusable, so QSharedMemory based
            # single-instance detection cannot start; upstream switch, also
            # used by the Android build.
            "NOSINGLEAPP",
        )

        qmake_args = [qmake, os.path.join(self.source_folder, "PC6001VX.pro")]
        qmake_args += ["DEFINES+=" + define for define in defines]
        qmake_args += [
            # Split-prefix Qt: hand the Qt Multimedia directories to the qmake
            # project instead of relying on `QT += multimedia` module files.
            "P6VX_QTMULTIMEDIA_INCDIR=" + os.path.join(qtmultimedia, "include"),
            "P6VX_QTMULTIMEDIA_LIBDIR=" + os.path.join(qtmultimedia, "lib"),
            # `CONFIG += lrelease` resolves lrelease through QT_TOOL; point it
            # at the qttools package.
            "QT_TOOL.lrelease.binary=" + os.path.join(qttools, "bin", "lrelease"),
        ]

        # Shadow build: the upstream source tree stays pristine, qmake writes
        # the Makefile into the Conan build folder.
        self.run(
            " ".join(shlex.quote(arg) for arg in qmake_args),
            cwd=self.build_folder,
            env=["conanbuild", "pc6001vx_build_env"],
        )
        # Parallel make: the jobs are plain compiler invocations (no recursive
        # make), build_jobs() honours tools.build:jobs and defaults to the
        # builder's CPU count — a -j1 full build needs ~47 minutes.
        self.run(
            f"make -j{build_jobs(self)}",
            cwd=self.build_folder,
            env=["conanbuild", "pc6001vx_build_env"],
        )

    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

        built_binary = os.path.join(self.build_folder, "PC6001VX")
        if not os.path.isfile(built_binary):
            raise ConanInvalidConfiguration(
                f"build artifact missing: {built_binary}"
            )
        bin_dir = os.path.join(self.package_folder, "bin")
        os.makedirs(bin_dir, exist_ok=True)
        packaged_binary = os.path.join(bin_dir, "PC6001VX")
        shutil.copy2(built_binary, packaged_binary)
        os.chmod(packaged_binary, 0o755)

        if str(self.settings.os) == "OHOS":
            self._sign_installed_elfs()

    def _sign_installed_elfs(self):
        """Re-sign installed OHOS ELF binaries (HarmonyOS refuses to start
        binaries whose code signature does not match)."""
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
                    [signer, "sign", "-inFile", unsigned, "-outFile", signed,
                     "-selfSign", "1"],
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
            result = subprocess.run(command, capture_output=True, text=True,
                                    timeout=60)
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
        if not resolved and os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            resolved = os.path.abspath(candidate)
        if not resolved or not os.path.isfile(resolved) or not os.access(resolved, os.X_OK):
            raise ConanInvalidConfiguration(
                f"Required tool {executable} was not found; set "
                f"{environment_variable} or add it to PATH"
            )
        return os.path.abspath(resolved)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
        # Qt GUI consumers need the QPA plugins. The OHOS qtbase package ships
        # `minimal` and `offscreen`; the emulator window itself needs a desktop
        # QPA plugin that the platform package does not provide yet.
        self.runenv_info.prepend_path(
            "QT_PLUGIN_PATH",
            os.path.join(self.dependencies["qtbase"].package_folder, "plugins"),
        )
