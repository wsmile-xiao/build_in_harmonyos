#!/usr/bin/env python3
"""Conan recipe for Redis 6.2 (upstream Redis 6.2.0)."""

import os
import shlex
import shutil
import tempfile

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class RedisConan(ConanFile):
    name = "redis"
    version = "6.2"
    description = "High-performance in-memory key-value data store"
    license = "BSD-3-Clause"
    homepage = "https://redis.io/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build_requirements(self):
        # Redis' official integration suite is Tcl-based. This dependency must
        # expose tclsh8.6 in PATH before the target binaries can be tested.
        self.tool_requires("tcl/8.6.16")

    def generate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"redis supports Linux/OHOS in this recipe, got {self.settings.os}"
            )
        VirtualBuildEnv(self).generate()

        tcl_root = self.dependencies.build["tcl"].package_folder
        if not tcl_root:
            raise ConanInvalidConfiguration("tcl/8.6.16 has no package folder")

        tcl_bin = os.path.join(tcl_root, "bin")
        tcl_lib = os.path.join(tcl_root, "lib")
        tcl_library = os.path.join(tcl_lib, "tcl8.6")
        required_runtime = (
            os.path.join(tcl_bin, "tclsh8.6"),
            os.path.join(tcl_library, "init.tcl"),
            os.path.join(tcl_lib, "tcl8", "8.5", "msgcat-1.6.1.tm"),
        )
        missing = [path for path in required_runtime if not os.path.isfile(path)]
        if missing:
            raise ConanInvalidConfiguration(
                "tcl/8.6.16 is missing Redis test runtime files: "
                + ", ".join(missing)
            )

        # Bind the tool requirement directly. Older cached Tcl recipe revisions
        # may not export their runtime paths through buildenv_info.
        tcl_env = Environment()
        tcl_env.prepend_path("PATH", tcl_bin)
        tcl_env.define_path("TCL_ROOT", tcl_root)
        tcl_env.define_path("TCL_LIBRARY", tcl_library)
        if self.settings.os in ("Linux", "OHOS"):
            tcl_env.prepend_path("LD_LIBRARY_PATH", tcl_lib)
        tcl_env.vars(self).save_script("redis_tcl_env")

    def _make_tool_args(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = executables.get("c", "clang")
        cxx = executables.get("cpp", "clang++")
        ar = executables.get("ar", "llvm-ar")
        ranlib = executables.get("ranlib", "llvm-ranlib")
        args = [
            f"CC={shlex.quote(cc)}",
            f"CXX={shlex.quote(cxx)}",
            f"LD={shlex.quote(cc)}",
            f"AR={shlex.quote(ar)}",
            f"RANLIB={shlex.quote(ranlib)}",
            "MALLOC=libc",
            "USE_SYSTEMD=no",
            "BUILD_TLS=no",
        ]
        if str(self.settings.os) == "OHOS":
            args.append("NO_LIBATOMIC=yes")
            args.append("INSTALL=/system/bin/install")
        return args

    def build(self):
        apply_conandata_patches(self)
        args = " ".join(self._make_tool_args())
        self.run(
            f"make -j1 {args}",
            cwd=self.source_folder,
            env="conanbuild",
        )

        # Redis' Tcl suite executes the just-built target binaries. Sign them
        # first on OHOS, then retain the complete upstream integration suite.
        is_ohos = str(self.settings.os) == "OHOS"
        if is_ohos:
            self._sign_ohos_binaries(os.path.join(self.source_folder, "src"))

        test_tmp = None
        test_env = ""
        if is_ohos:
            test_storage = "/data/storage/el2/base/cache"
            if not os.path.isdir(test_storage):
                raise ConanInvalidConfiguration(
                    f"OHOS user cache directory does not exist: {test_storage}"
                )
            test_tmp = tempfile.mkdtemp(prefix="redis-test-", dir=test_storage)
            test_env = f"REDIS_TEST_TMPDIR={shlex.quote(test_tmp)} "

        try:
            self.run(
                f"{test_env}make -j1 test {args}",
                cwd=self.source_folder,
                env="conanbuild",
            )
        finally:
            if test_tmp:
                shutil.rmtree(test_tmp, ignore_errors=True)

    def package(self):
        is_ohos = str(self.settings.os) == "OHOS"
        if is_ohos:
            source_bin = os.path.join(self.source_folder, "src")
            package_bin = os.path.join(self.package_folder, "bin")
            for binary in (
                "redis-server",
                "redis-sentinel",
                "redis-cli",
                "redis-benchmark",
                "redis-check-rdb",
                "redis-check-aof",
            ):
                copy(self, binary, src=source_bin, dst=package_bin)
        else:
            args = " ".join(self._make_tool_args())
            prefix = shlex.quote(f"PREFIX={self.package_folder}")
            self.run(
                f"make install {prefix} {args}",
                cwd=self.source_folder,
                env="conanbuild",
            )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def _sign_ohos_binaries(self, bindir):
        signer = self._find_tool(
            "binary-sign-tool",
            [
                "/data/service/hnp/bin/binary-sign-tool",
                "/storage/Users/currentUser/usr/local/bin/binary-sign-tool",
            ],
        )
        objcopy = self._find_tool(
            "llvm-objcopy",
            [
                "/data/service/hnp/bin/llvm-objcopy",
                "/storage/Users/currentUser/usr/local/bin/llvm-objcopy",
            ],
        )
        commands = {
            "redis-server",
            "redis-sentinel",
            "redis-cli",
            "redis-benchmark",
            "redis-check-rdb",
            "redis-check-aof",
        }
        for entry in os.scandir(bindir):
            if entry.name not in commands or not entry.is_file(follow_symlinks=False):
                continue
            binary = entry.path
            signed = binary + ".signed"
            self.run(
                f"{shlex.quote(objcopy)} --remove-section .codesign "
                f"{shlex.quote(binary)}",
                quiet=True,
            )
            self.run(
                f"{shlex.quote(signer)} sign -inFile {shlex.quote(binary)} "
                f"-outFile {shlex.quote(signed)} -selfSign 1",
                quiet=True,
            )
            os.replace(signed, binary)
            os.chmod(binary, 0o755)

    @staticmethod
    def _find_tool(name, fallbacks):
        found = shutil.which(name)
        if found:
            return found
        for candidate in fallbacks:
            if os.path.isfile(candidate):
                return candidate
        raise ConanInvalidConfiguration(f"{name} is required to build Redis on OHOS")

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
