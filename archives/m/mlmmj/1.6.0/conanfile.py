#!/usr/bin/env python3
"""Conan recipe — mlmmj 1.6.0 (Autotools) — mailing list manager suite."""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class MlmmjConan(ConanFile):
    name = "mlmmj"
    version = "1.6.0"
    description = ("Mailing list manager suite: receive/subscribe/unsubscribe, "
                   "bounce handling, digest, moderation and maintenance tools")
    license = "MIT"
    homepage = "http://mlmmj.org/"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration("mlmmj is adapted for Linux and OHOS only")

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Native build: no --build/--host/--target triplets. build-aux/config.guess
        # and config.sub are patched (0001/0002) to recognize HarmonyOS, so the
        # configure-time build/host detection succeeds on its own and the
        # AC_RUN_IFELSE probes execute natively on the device.
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(self._recipe_configure_args())
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        autotools = Autotools(self)
        if str(self.settings.os) == "OHOS":
            self._ohos_restore_script_modes()
            with self._runtime_env().vars(self).apply():
                self._ohos_configure()
                autotools.make(args=["-j1"])
        else:
            autotools.configure()
            autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        if str(self.settings.os) == "OHOS":
            with self._runtime_env().vars(self).apply():
                autotools.install()
        else:
            autotools.install()

    def package_info(self):
        bindir = os.path.join(self.package_folder, "bin")
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.libs = []
        self.buildenv_info.append_path("PATH", bindir)
        self.runenv_info.append_path("PATH", bindir)

    def _ohos_restore_script_modes(self):
        # E490: scripts from the tarball may lose their exec bits on HMDFS.
        # Restore them (belt for CI); the actual OHOS dispatch fix is below.
        for rel in ("configure", "config.guess", "config.sub",
                    "install-sh", "missing", "compile", "depcomp",
                    "build-aux/config.guess", "build-aux/config.sub",
                    "build-aux/install-sh", "build-aux/missing",
                    "build-aux/compile", "build-aux/depcomp",
                    "src/mkinstalldirs"):
            path = os.path.join(self.source_folder, rel)
            if os.path.exists(path):
                os.chmod(path, os.stat(path).st_mode | 0o111)

    def _ohos_configure(self):
        # OHOS has no binfmt_script: executing a script path directly fails
        # with EACCES (Error 126) even with the exec bits set. Run configure
        # explicitly through the shell, with the same arguments that
        # AutotoolsToolchain/Autotools.configure() would use (native build:
        # no --build/--host triplets).
        configure = os.path.join(self.source_folder, "configure")
        args = [
            "--prefix=/",
            "--bindir=${prefix}/bin",
            "--sbindir=${prefix}/bin",
            "--libdir=${prefix}/lib",
            "--includedir=${prefix}/include",
            "--oldincludedir=${prefix}/include",
        ] + self._recipe_configure_args()
        self.run(f"sh {shlex.quote(configure)} {shlex.join(args)}",
                 cwd=self.build_folder, env="conanautotoolstoolchain")

    def _runtime_env(self):
        # /tmp is read-only on OHOS devices: point configure/make temp files
        # at a writable directory under the build folder.
        env = Environment()
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        env.define_path("TMPDIR", tmpdir)
        env.define_path("TMP", tmpdir)
        env.define_path("TEMP", tmpdir)
        return env

    @staticmethod
    def _recipe_configure_args():
        # --disable-tests: the ATF test suite is enabled by default and needs
        # ATF at configure time; the package build does not. The upstream
        # suite is executed out-of-band on the device (see notes.md).
        return [
            "--disable-tests",
            "--disable-dependency-tracking",
            "--disable-silent-rules",
        ]
