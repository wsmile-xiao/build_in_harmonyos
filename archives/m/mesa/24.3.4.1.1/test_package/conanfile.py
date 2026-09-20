#!/usr/bin/env python3
"""Conan test_package — mesa 24.3.4.1.1 L1 消费者验证."""
import glob
import os
import shlex

from conan import ConanFile
from conan.tools.layout import basic_layout


class MesaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        mesa = self.dependencies.host["mesa"]
        include_dir = os.path.join(mesa.package_folder, "include")
        lib_dir = os.path.join(mesa.package_folder, "lib")
        output = os.path.join(self.build_folder, "test_mesa")
        compiler = (
            (self.conf.get("tools.build:compiler_executables",
                           default={}, check_type=dict) or {}).get("c")
            or os.environ.get("CC")
            or "clang"
        )
        command = " ".join(
            [
                shlex.quote(compiler),
                "-std=c11",
                f"-I{shlex.quote(include_dir)}",
                shlex.quote(os.path.join(self.source_folder, "test.c")),
                f"-L{shlex.quote(lib_dir)}",
                "-lOSMesa",
                "-lglapi",
                *[
                    f"-Wl,-rpath,{shlex.quote(path)}"
                    for path in [lib_dir] + self._sdk_runtime_dirs()
                ],
                f"-o {shlex.quote(output)}",
            ]
        )
        self.run(command, env="conanbuild")

    def _sdk_runtime_dirs(self):
        if str(self.settings.os) != "OHOS":
            return []
        sdk_roots = [
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18"
        ]
        sdk_roots.extend(
            sorted(glob.glob("/data/service/hnp/ohos-sdk.org/*"))
        )
        result = []
        for sdk_root in sdk_roots:
            native = os.path.join(sdk_root, "ohos", "native")
            candidates = [
                os.path.join(
                    native, "llvm", "lib", "aarch64-linux-ohos", "c++"
                ),
                os.path.join(native, "llvm", "lib", "aarch64-linux-ohos"),
                os.path.join(
                    native,
                    "sysroot",
                    "usr",
                    "lib",
                    "aarch64-linux-ohos",
                ),
            ]
            for candidate in candidates:
                if not os.path.isdir(candidate):
                    continue
                if (
                    os.path.isfile(os.path.join(candidate, "libc++_shared.so"))
                    or os.path.isfile(os.path.join(candidate, "libz.so"))
                ):
                    result.append(candidate)
            if result:
                break
        return list(dict.fromkeys(result))

    def test(self):
        mesa = self.dependencies.host["mesa"]
        lib_dir = os.path.join(mesa.package_folder, "lib")
        binary = os.path.join(self.build_folder, "test_mesa")
        # Keep the package libdir and OHOS SDK runtime dirs explicit. The
        # worker's default conanrun environment does not reliably expose
        # cache-local shared libraries to the device loader.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        runtime_dirs = [lib_dir] + self._sdk_runtime_dirs()
        ldpath = ":".join(runtime_dirs)
        script = (
            f'export LD_LIBRARY_PATH="{ldpath}'
            '${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"; '
            f"exec {shlex.quote(binary)}"
        )
        self.run(
            f"{shlex.quote(bash)} -c {shlex.quote(script)}",
            env="conanrun",
        )
