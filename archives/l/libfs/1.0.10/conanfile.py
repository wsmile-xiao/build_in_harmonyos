#!/usr/bin/env python3
"""Conan recipe for X.Org libFS 1.0.10."""

import os
import re
import shlex
import socket
import struct
import threading
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import (
    Autotools,
    AutotoolsDeps,
    AutotoolsToolchain,
    PkgConfigDeps,
)
from conan.tools.layout import basic_layout


class LibfsConan(ConanFile):
    name = "libfs"
    version = "1.0.10"
    description = "X.Org library interface to the X Font Server protocol"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/lib/libfs"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("xorgproto/2025.1", transitive_headers=True)
        self.requires("xtrans/1.6.0", visible=False)

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libfs supports Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        self._autotools_toolchain().generate()

    def build(self):
        environment = self._build_environment()
        with environment.vars(self).apply():
            if str(self.settings.os) == "OHOS":
                self._prepare_ohos_configure()
                self._configure_ohos()
                self._run_ohos("make -j1")
                self._run_ohos("make -j1 check")
                self._run_upstream_check_ohos()
            else:
                autotools = Autotools(self)
                autotools.configure()
                autotools.make(args=["-j1"])
                autotools.make(target="check", args=["-j1"])

    def package(self):
        environment = self._build_environment()
        with environment.vars(self).apply():
            if str(self.settings.os) == "OHOS":
                destination = shlex.quote(self.package_folder)
                self._run_ohos(f"make -j1 install DESTDIR={destination}")
            else:
                Autotools(self).install(args=["-j1"])
        self._relocate_metadata()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["FS"]
        self.cpp_info.requires = ["xorgproto::xorgproto"]
        self.cpp_info.set_property("cmake_file_name", "libfs")
        self.cpp_info.set_property("cmake_target_name", "libfs::libfs")
        self.cpp_info.set_property("pkg_config_name", "libfs")
        pc_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        self.buildenv_info.append_path("PKG_CONFIG_PATH", pc_dir)
        self.runenv_info.append_path("PKG_CONFIG_PATH", pc_dir)

    def _build_environment(self):
        temporary = Path(self.build_folder, ".tmp")
        temporary.mkdir(parents=True, exist_ok=True)
        environment = Environment()
        environment.define_path("TMPDIR", str(temporary))
        if str(self.settings.os) == "OHOS":
            environment.define("MKDIR_P", "/system/bin/mkdir -p")
        return environment

    def _autotools_toolchain(self):
        return AutotoolsToolchain(self)

    def _configure_ohos(self):
        shell = "/system/bin/sh"
        if not os.path.isfile(shell):
            raise ConanInvalidConfiguration(f"OHOS configure shell is missing: {shell}")
        configure = self._ohos_configure_path()
        toolchain = self._autotools_toolchain()
        # XORG_CHECK_MALLOC_ZERO's default "auto" branch RUNS a conftest
        # binary to probe malloc(0); under cross-compiling that aborts with
        # "cannot run test program while cross compiling".  OHOS bionic's
        # malloc(0) returns a valid pointer, so pin the option to "no"
        # (empty MALLOC_ZERO_CFLAGS) and skip the runtime probe.
        toolchain.configure_args.append("--disable-malloc0returnsnull")
        arguments = " ".join(
            shlex.quote(argument)
            for argument in toolchain.configure_args
        )
        self._run_ohos(f'"{shell}" "{configure}" {arguments}')

    def _prepare_ohos_configure(self):
        configure = self._ohos_configure_path()
        content = configure.read_text(encoding="utf-8")
        needle = "umask 077"
        if content.count(needle) != 2:
            raise ConanException("configure umask contract changed")
        configure.write_text(
            content.replace(needle, "umask 022"),
            encoding="utf-8",
            newline="\n",
        )

    def _ohos_configure_path(self):
        configure = Path(self.source_folder, "configure")
        if not configure.is_file():
            raise ConanException(f"configure script is missing: {configure}")
        return configure

    def _run_ohos(self, command):
        shell = "/system/bin/sh"
        prefix = f"export SHELL={shell} CONFIG_SHELL={shell}; "
        self.run(prefix + command, cwd=self.build_folder, env="conanbuild")

    def _run_upstream_check_ohos(self):
        """Run the upstream test program that ``make check`` only builds.

        test/Makefile.am declares FSGetErrorText under noinst_PROGRAMS
        with no TESTS entries, so the Automake check target builds the
        binary but executes nothing.  The recipe runs it for real here.
        OHOS ships no xfs font server, so an in-process peer speaking
        the minimal FS protocol lets FSOpenServer() complete: it answers
        the handshake (fsConnClientPrefix -> fsConnSetup ->
        fsConnSetupAccept with a 32-bit aligned "mock" vendor string)
        and then drains the connection.  FSGetErrorText only reads
        ext_procs from the server handle and resolves the error strings
        locally, so no further server replies are needed.  The upstream
        test sources are used unmodified.
        """
        test_program = Path(self.build_folder, "test", "FSGetErrorText")
        if not test_program.is_file():
            raise ConanException(
                f"upstream test program was not built: {test_program}"
            )
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        server = threading.Thread(
            target=self._serve_fs_handshake, args=(listener,), daemon=True
        )
        server.start()
        try:
            fontserver = f"FONTSERVER=127.0.0.1:{listener.getsockname()[1]}"
            self._run_ohos(f"{fontserver} ./test/FSGetErrorText")
        finally:
            try:
                listener.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            listener.close()
            server.join(timeout=5)

    @staticmethod
    def _serve_fs_handshake(listener):
        """Serve FS protocol handshakes until the listener is shut down."""
        while True:
            try:
                conn, _ = listener.accept()
            except OSError:
                return
            try:
                prefix = LibfsConan._read_exactly(conn, 8)
                if prefix is None or prefix[0] not in (ord("l"), ord("B")):
                    continue
                endian = "<" if prefix[0] == ord("l") else ">"
                # fsConnSetup: status=AuthSuccess(0), major=2, minor=0,
                # num_alternates=0, auth_index=0, alternate_len=0 -- no
                # alternate or auth blobs follow.
                setup = bytearray(12)
                setup[2] = 2  # major_version
                conn.sendall(setup)
                # fsConnSetupAccept: length=0, max_request_len=65535,
                # vendor_len=4, release_number=1, vendor "mock" (already
                # 32-bit aligned, so _FSReadPad reads no extra bytes).
                conn.sendall(
                    struct.pack(endian + "IHHI", 0, 0xFFFF, 4, 1) + b"mock"
                )
                while conn.recv(4096):
                    pass
            except OSError:
                pass
            finally:
                conn.close()

    @staticmethod
    def _read_exactly(conn, size):
        data = bytearray()
        while len(data) < size:
            chunk = conn.recv(size - len(data))
            if not chunk:
                return None
            data.extend(chunk)
        return bytes(data)

    def _relocate_metadata(self):
        pc_path = Path(self.package_folder, "lib", "pkgconfig", "libfs.pc")
        if not pc_path.is_file():
            raise ConanException("installed libfs.pc is missing")
        pc_content = pc_path.read_text(encoding="utf-8")
        pc_content, count = re.subn(
            r"^prefix=.*$",
            "prefix=${pcfiledir}/../..",
            pc_content,
            count=1,
            flags=re.MULTILINE,
        )
        if count != 1:
            raise ConanException("libfs.pc has no unique prefix field")
        pc_path.write_text(pc_content, encoding="utf-8")

        la_path = Path(self.package_folder, "lib", "libFS.la")
        if la_path.is_file():
            la_path.unlink()
