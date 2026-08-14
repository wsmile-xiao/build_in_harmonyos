#!/usr/bin/env python3
"""Conan recipe for the p11-kit server commands from p11-kit 0.26.2."""

import glob
import os
import shlex
import shutil
import socket
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class P11KitServerConan(ConanFile):
    name = "p11-kit-server"
    version = "0.26.2"
    description = "Server and remote commands for forwarding PKCS#11 modules"
    license = "BSD-3-Clause"
    homepage = "https://github.com/p11-glue/p11-kit"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # The server executables link to libp11-kit.so.0. Keep the source and
        # runtime versions aligned because 0.26.2 contains an RPC security fix.
        self.requires("p11-kit/0.26.2", run=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = MesonToolchain(self)
        toolchain.project_options.update(
            {
                "wrap_mode": "nodownload",
                "libexecdir": "libexec",
                "hash_impl": "internal",
                "env_override_paths": "enabled",
                "libffi": "disabled",
                "closures": 64,
                "trust_module": "disabled",
                "systemd": "disabled",
                "bash_completion": "disabled",
                "zsh_completion": "disabled",
                "gtk_doc": False,
                "man": False,
                "nls": False,
                "test": True,
                "post_install_test": False,
            }
        )
        toolchain.generate()
        self._inject_archiver_tools()

    def build(self):
        apply_conandata_patches(self)
        self._prepare_build_environment()

        meson = Meson(self)
        meson.configure()
        meson.build()

        if can_run(self):
            self._run_upstream_server_tests()
        else:
            self.output.info(
                "upstream server tests skipped: target executables cannot run on the build host"
            )

    def package(self):
        Meson(self).install()

        installed_commands = os.path.join(self.package_folder, "libexec", "p11-kit")
        package_bin = os.path.join(self.package_folder, "bin")
        copy(
            self,
            "p11-kit-server",
            src=installed_commands,
            dst=package_bin,
            keep_path=False,
        )
        copy(
            self,
            "p11-kit-remote",
            src=installed_commands,
            dst=package_bin,
            keep_path=False,
        )

        missing = [
            name
            for name in ("p11-kit-server", "p11-kit-remote")
            if not os.path.isfile(os.path.join(package_bin, name))
        ]
        if missing:
            raise ConanException(
                "Meson installation did not produce: {}".format(", ".join(missing))
            )

        # Meson installs the complete p11-kit source package. This Conan package
        # owns only the server subpackage, so discard all other installed output.
        for entry in os.listdir(self.package_folder):
            if entry == "bin":
                continue
            path = os.path.join(self.package_folder, entry)
            if os.path.isdir(path) and not os.path.islink(path):
                shutil.rmtree(path)
            else:
                os.remove(path)

        retained_commands = {"p11-kit-server", "p11-kit-remote"}
        for entry in os.listdir(package_bin):
            if entry in retained_commands:
                continue
            path = os.path.join(package_bin, entry)
            if os.path.isdir(path) and not os.path.islink(path):
                shutil.rmtree(path)
            else:
                os.remove(path)

        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        self._sign_elf()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.runenv_info.define_path(
            "P11_KIT_PRIVATEDIR", os.path.join(self.package_folder, "bin")
        )

    def _prepare_build_environment(self):
        if self.settings.os != "OHOS":
            return

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compilers.get("c")
        if not compiler:
            raise ConanException(
                "tools.build:compiler_executables must define the C compiler"
            )
        llvm_lib_candidates = []
        try:
            resource_dir = subprocess.check_output(
                [compiler, "--print-resource-dir"],
                stderr=subprocess.STDOUT,
                universal_newlines=True,
            ).strip()
            if resource_dir:
                llvm_lib_candidates.append(
                    os.path.dirname(os.path.dirname(resource_dir))
                )
        except (OSError, subprocess.CalledProcessError):
            pass

        resolved_compiler = os.path.realpath(compiler)
        llvm_lib_candidates.append(
            os.path.join(os.path.dirname(os.path.dirname(resolved_compiler)), "lib")
        )
        llvm_lib = next(
            (
                path
                for path in dict.fromkeys(llvm_lib_candidates)
                if os.path.isfile(os.path.join(path, "libxml2.so.16"))
            ),
            None,
        )
        if llvm_lib is None:
            raise ConanException(
                "OHOS SDK libxml2.so.16 not found; checked: {}".format(
                    ", ".join(dict.fromkeys(llvm_lib_candidates))
                )
            )

        # Keep worker-local libraries from shadowing the libxml2 used by the
        # SDK lld. The dependency recipe applies the same ordering.
        current_ld_path = os.environ.get("LD_LIBRARY_PATH", "")
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
            path for path in (llvm_lib, current_ld_path) if path
        )

        tmpdir = self._select_socket_tmpdir()
        os.environ["TMPDIR"] = tmpdir
        os.environ["TMP"] = tmpdir
        os.environ["TEMP"] = tmpdir

    def _run_upstream_server_tests(self):
        test_binary = os.path.join(self.build_folder, "p11-kit", "test-server")
        test_names = (
            "/server/initialize",
            "/server/initialize-no-address",
            "/server/initialize-address-from-config",
            "/server/open-session",
            "/server/open-session-write-protected",
            "/server/all/initialize",
            "/server/all/initialize-no-address",
            "/server/all/open-session",
        )

        # OHOS retains dynamically loaded module state when all cases share
        # one process. The upstream test runner accepts a case name, so keep
        # every original assertion while isolating each case in its own process.
        for test_name in test_names:
            self.run(
                "{} {}".format(
                    shlex.quote(test_binary), shlex.quote(test_name)
                ),
                env="conanbuild",
            )

        self.run(
            "meson test -C {} --verbose --print-errorlogs test-server.sh".format(
                shlex.quote(self.build_folder)
            ),
            env="conanbuild",
        )
        self.output.info("upstream server tests passed: 9/9")

    def _select_socket_tmpdir(self):
        candidates = [
            os.environ.get("TMPDIR"),
            "/data/storage/el2/base/cache",
            os.path.join(self.build_folder, "tmp"),
        ]
        failures = []
        seen = set()
        for candidate in candidates:
            if not candidate:
                continue
            candidate = os.path.abspath(candidate)
            if candidate in seen:
                continue
            seen.add(candidate)
            probe_name = os.path.join(
                candidate, ".p11-kit-server-bind-{}".format(os.getpid())
            )
            listener = None
            try:
                os.makedirs(candidate, exist_ok=True)
                if os.path.lexists(probe_name):
                    os.unlink(probe_name)
                listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                listener.bind(probe_name)
            except OSError as error:
                failures.append(
                    "{}: errno {} ({})".format(
                        candidate, error.errno, error.strerror or str(error)
                    )
                )
                continue
            finally:
                if listener is not None:
                    listener.close()
                if os.path.lexists(probe_name):
                    os.unlink(probe_name)
            self.output.info(
                "using AF_UNIX-capable temporary directory: {}".format(candidate)
            )
            return candidate

        raise ConanException(
            "no AF_UNIX-capable temporary directory is available; "
            "server tests require a filesystem socket: {}".format(
                "; ".join(failures)
            )
        )

    def _sign_elf(self):
        if self.settings.os != "OHOS":
            return
        hnp_bin = "/data/service/hnp/bin"
        objcopy = os.path.join(hnp_bin, "llvm-objcopy")
        signer = os.path.join(hnp_bin, "binary-sign-tool")
        if not os.path.isfile(objcopy) or not os.path.isfile(signer):
            self.output.warning(
                "binary-sign-tool/llvm-objcopy unavailable; skipping ELF re-signing"
            )
            return

        for path in sorted(glob.glob(os.path.join(self.package_folder, "bin", "*"))):
            if not os.path.isfile(path):
                continue
            try:
                with open(path, "rb") as handle:
                    if handle.read(4) != b"\x7fELF":
                        continue
            except OSError:
                continue
            self.run(
                '{objcopy} --remove-section .codesign "{path}" 2>/dev/null || true'.format(
                    objcopy=objcopy, path=path
                )
            )
            self.run(
                '{signer} sign -inFile "{path}" -outFile "{path}.signed" -selfSign 1'.format(
                    signer=signer, path=path
                )
            )
            if os.path.isfile(path + ".signed"):
                os.replace(path + ".signed", path)
                os.chmod(path, 0o755)

    def _inject_archiver_tools(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        ar = compilers.get("ar")
        ranlib = compilers.get("ranlib")
        cc = compilers.get("c") or ""
        compiler_dir = os.path.dirname(cc) if os.path.sep in cc else ""

        if not ar and compiler_dir:
            candidate = os.path.join(compiler_dir, "llvm-ar")
            if os.path.isfile(candidate):
                ar = candidate
        if not ranlib and compiler_dir:
            candidate = os.path.join(compiler_dir, "llvm-ranlib")
            if os.path.isfile(candidate):
                ranlib = candidate

        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            toolchain_file = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(toolchain_file):
                continue
            with open(toolchain_file, encoding="utf-8") as handle:
                content = handle.read()
            if "[binaries]" not in content:
                continue

            entries = []
            if ar and "\nar =" not in content:
                entries.append("ar = '{}'".format(ar))
            if ranlib and "\nranlib =" not in content:
                entries.append("ranlib = '{}'".format(ranlib))
            if entries:
                insertion = "[binaries]\n" + "\n".join(entries) + "\n"
                with open(toolchain_file, "w", encoding="utf-8") as handle:
                    handle.write(content.replace("[binaries]\n", insertion, 1))
