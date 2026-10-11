#!/usr/bin/env python3
"""Conan test_package for pcc-libs (L1 consumer test).

pcc-libs does not use a conventional include/lib layout: upstream installs the
runtime under <prefix>/lib/pcc/<triplet>/<version>/{lib,include}, addressed by
the compiler through that triplet path rather than through -I/-L flags.  The
package therefore exports PCC_LIBS_ROOT instead of a normal cpp_info library,
and this test compiles its consumer against that root.

The consumer is linked statically so the same binary can be executed here
(under qemu-user via WSL) and on a HarmonyOS device: a dynamically linked OHOS
program needs /lib/ld-musl-aarch64.so.1, which exists only on the device.
"""
import os
import re
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class PccLibsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    #: Mirrors the recipe's install layout; the environment variable exported
    #: by the recipe is cross-checked against it in _runtime_root().
    _RUNTIME_SUBDIR = os.path.join(
        "lib", "pcc", "aarch64-unknown-linux-ohos", "1.2.0.DEVEL"
    )

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self, src_folder=".")

    def _runtime_root(self):
        """Locate the installed runtime and verify the recipe's advertised path."""
        dependency = self.dependencies[self.tested_reference_str]
        root = os.path.join(dependency.package_folder, self._RUNTIME_SUBDIR)
        if not os.path.isdir(root):
            raise ConanException(
                "pcc-libs runtime directory is missing: {}".format(root)
            )

        advertised = dependency.runenv_info.vars(self).get("PCC_LIBS_ROOT")
        if not advertised:
            raise ConanException(
                "pcc-libs did not export PCC_LIBS_ROOT; consumers would have "
                "no supported way to locate the runtime"
            )
        if os.path.normpath(advertised) != os.path.normpath(root):
            raise ConanException(
                "PCC_LIBS_ROOT ({}) does not match the installed runtime "
                "directory ({})".format(advertised, root)
            )
        return root

    def _compiler(self):
        toolchain = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        return toolchain.get("c", "cc")

    @staticmethod
    def _to_wsl_path(host_path):
        path = os.path.abspath(host_path).replace("\\", "/")
        match = re.match(r"^([A-Za-z]):/(.*)$", path)
        if not match:
            raise ConanException(
                "Expected a drive-letter path, got: {}".format(host_path)
            )
        return "/mnt/{}/{}".format(match.group(1).lower(), match.group(2))

    def build(self):
        runtime = self._runtime_root()
        source = os.path.join(self.source_folder, "consumer.c")
        binary = os.path.join(self.build_folder, "consumer")
        command = [
            self._compiler(),
            "-O1",
            "-std=c99",
            "-static",
            "-I" + os.path.join(runtime, "include"),
            source,
            os.path.join(runtime, "lib", "libpcc.a"),
            os.path.join(runtime, "lib", "libpccsoftfloat.a"),
            "-o",
            binary,
        ]
        self.output.info("compiling consumer: {}".format(" ".join(command)))
        self.run(" ".join('"{}"'.format(part) for part in command))

    def test(self):
        binary = os.path.join(self.build_folder, "consumer")
        if not os.path.exists(binary):
            raise ConanException("consumer binary was not built: {}".format(binary))

        if can_run(self):
            # Native run (device or an OHOS-capable runner).
            self.run(binary, env="conanrun")
            return

        if os.name != "nt":
            # Already inside the POSIX host: binfmt_misc routes the aarch64
            # ELF to qemu-user, so the static binary can be executed directly.
            os.chmod(binary, os.stat(binary).st_mode | 0o755)
            self.run("'{}'".format(binary))
            return

        # Cross-built artifact: execute the static binary through WSL's
        # qemu-user, which is how this port is verified on the build host.
        distro = os.environ.get("OHOS_WSL_DISTRO", "Ubuntu-24.04")
        wsl_binary = self._to_wsl_path(binary)
        shell = (
            "cp '{src}' /tmp/pcc-libs-consumer && chmod +x /tmp/pcc-libs-consumer "
            "&& /tmp/pcc-libs-consumer"
        ).format(src=wsl_binary)
        result = subprocess.run(
            ["wsl", "-d", distro, "--", "bash", "-lc", shell],
            capture_output=True,
            text=True,
        )
        for line in ((result.stdout or "") + (result.stderr or "")).splitlines():
            self.output.info("  " + line)
        if result.returncode != 0:
            raise ConanException(
                "pcc-libs consumer test failed (exit {}) under WSL/{}. "
                "Is qemu-user-static installed and the binary static?".format(
                    result.returncode, distro
                )
            )