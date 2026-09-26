#!/usr/bin/env python3
"""Consumer test for rrdtool 1.9.0.

Two independent layers, both exercising real code (R34):

1. ``test_rrd_api.c`` is compiled against the *packaged* headers and linked
   against the *packaged* ``librrd.so``.  It drives create -> update -> info
   through the exported C API, which proves the library is consumable by a
   third party and not merely present on disk.
2. ``test_rrdtool.sh`` runs the installed multi-call binary through the full
   round-robin loop (create/update/fetch/last/first/info/tune/dump/restore/
   graph/graphv/xport) and additionally executes every other declared command
   (rrdupdate, rrdcached, rrdcgi).

The test is deliberately not guarded by ``can_run``: CI's destructive L1 gate
moves the package artifacts away and re-runs this test, which must then fail
because the binaries and library it invokes are gone.
"""
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.gnu import AutotoolsToolchain


class RrdtoolTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualBuildEnv", "VirtualRunEnv", "PkgConfigDeps"
    exports_sources = "test_rrd_api.c", "test_rrdtool.sh"
    test_type = "explicit"

    @property
    def _is_ohos(self):
        return str(self.settings.os) == "OHOS"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _pkg(self):
        return self.dependencies["rrdtool"]

    def build(self):
        # Emit CC/CFLAGS/LDFLAGS for this build folder from the same profile
        # the package was built with, so the consumer compiles identically.
        tc = AutotoolsToolchain(self)
        tc.generate()
        # Do NOT rely on "$CC" from the aggregated env scripts: the
        # conanbuild.sh aggregate can end up sourcing only the
        # VirtualBuildEnv part (which has no CC on this setup) and the
        # compile dies with "can't execute: Is a directory" (measured).
        # Resolve the compiler straight from the profile conf instead.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = (compilers or {}).get("c") or "clang"

        cpp = self._pkg().cpp_info.aggregated_components()
        includes = " ".join(f'-I"{p}"' for p in cpp.includedirs)
        libpaths = " ".join(f'-L"{p}"' for p in cpp.libdirs)
        libs = " ".join(f"-l{name}" for name in cpp.libs)
        system = " ".join(f"-l{name}" for name in cpp.system_libs)

        source = os.path.join(self.source_folder, "test_rrd_api.c")
        binary = os.path.join(self.build_folder, "test_rrd_api")
        command = (
            f'"{cc}" {includes} {libpaths} "{source}" -o "{binary}" '
            f'{libs} {system}'
        )
        self.run(command, env="conanbuild")
        if self._is_ohos:
            self._sign_elf(binary)

    def test(self):
        package_folder = self._pkg().package_folder
        bindir = os.path.join(package_folder, "bin")
        work = os.path.join(self.build_folder, "run")
        os.makedirs(work, exist_ok=True)

        api_binary = os.path.join(self.build_folder, "test_rrd_api")
        self.run(f'"{api_binary}" "{work}"', env="conanrun")

        harness = os.path.join(self.source_folder, "test_rrdtool.sh")
        shell = shutil.which("sh") or "/bin/sh"
        self.run(
            f'"{shell}" "{harness}" "{bindir}" "{work}"',
            env="conanrun",
        )

    @staticmethod
    def _sign_elf(path):
        signer = (
            shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        )
        if not os.path.isfile(signer):
            raise ConanException(f"missing OHOS signer: {signer}")
        output = path + ".signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", output, "-selfSign", "1"],
            check=True,
            timeout=180,
        )
        os.chmod(output, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(output, path)
