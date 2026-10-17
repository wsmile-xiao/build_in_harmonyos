#!/usr/bin/env python3
"""Consumer test package for libkylin-chkname 1.0.10."""
import json
import os
import platform
import re
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.env import Environment


class LibkylinChknameTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def _command(self, executable):
        qemu = shutil.which("qemu-aarch64")
        if (
            str(self.settings.arch) == "armv8"
            and platform.machine().lower() not in ("aarch64", "arm64")
            and qemu
            and os.environ.get("QEMU_LD_PREFIX")
        ):
            return [qemu, executable]
        if can_run(self):
            return [executable]
        return None

    def _runtime_environment(self):
        dependency = self.dependencies["libkylin-chkname"]
        package_folder = dependency.package_folder
        reserved = os.path.join(
            package_folder, "share", "kylin-chkname", "reserved-names"
        )
        locale = os.path.join(package_folder, "share", "locale")
        library_paths = []
        for item in self.dependencies.values():
            folder = getattr(item, "package_folder", None)
            if not folder:
                continue
            for libdir in item.cpp_info.libdirs:
                path = os.path.join(folder, libdir)
                if os.path.isdir(path) and path not in library_paths:
                    library_paths.append(path)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compilers.get("cpp") or compilers.get("c")
        if compiler:
            cxx_runtime = os.path.normpath(
                os.path.join(os.path.dirname(compiler), "..", "lib", "aarch64-linux-ohos")
            )
            if os.path.isdir(cxx_runtime) and cxx_runtime not in library_paths:
                library_paths.append(cxx_runtime)
        ndk_home = os.environ.get("OHOS_NDK_HOME")
        if ndk_home:
            local_cxx_runtime = os.path.join(
                ndk_home, "llvm", "lib", "aarch64-linux-ohos"
            )
            if (
                os.path.isdir(local_cxx_runtime)
                and local_cxx_runtime not in library_paths
            ):
                library_paths.append(local_cxx_runtime)
        existing_ld = os.environ.get("LD_LIBRARY_PATH")
        if existing_ld:
            library_paths.append(existing_ld)
        ld_path = os.pathsep.join(library_paths)

        values = {
            "KYLIN_CHKNAME_RESERVED_NAMES": reserved,
            "KYLIN_CHKNAME_LOCALEDIR": locale,
            "LD_LIBRARY_PATH": ld_path,
        }
        # QEMU_SET_ENV controls the guest variables.  Preserve the local
        # compatibility shim while replacing stale package paths.
        if os.environ.get("QEMU_LD_PREFIX"):
            qemu_items = [
                value
                for value in os.environ.get("QEMU_SET_ENV", "").split(",")
                if value
                and not value.startswith("LD_LIBRARY_PATH=")
                and not value.startswith("KYLIN_CHKNAME_RESERVED_NAMES=")
                and not value.startswith("KYLIN_CHKNAME_LOCALEDIR=")
            ]
            qemu_items.extend(
                [
                    "LD_LIBRARY_PATH=" + ld_path,
                    "KYLIN_CHKNAME_RESERVED_NAMES=" + reserved,
                    "KYLIN_CHKNAME_LOCALEDIR=" + locale,
                ]
            )
            values["QEMU_SET_ENV"] = ",".join(qemu_items)
        return values

    def test(self):
        executable = os.path.join(self.cpp.build.bindirs[0], "test_libkylin_chkname")
        command = self._command(executable)
        if command is None:
            raise ConanException(
                "target execution is required; no native runner or QEMU runtime found"
            )

        runtime_values = self._runtime_environment()
        env = dict(os.environ)
        env.update(runtime_values)
        # self.run below is the authoritative consumer execution.  The first
        # run captures machine-readable counts required by the test gate.
        proc = subprocess.run(
            command,
            cwd=self.build_folder,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        self.output.info("test output:\n" + output)
        passed = len(set(re.findall(r"PASS\[(\d+)/20\]", output)))
        result = {
            "executed": True,
            "passed": proc.returncode == 0 and passed == 20,
            "command": " ".join(command),
            "discovered": 20,
            "passedCount": passed,
        }
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(result, ensure_ascii=False)
        )
        upstream = {
            "status": "no_tests",
            "framework": "autotools",
            "command": "none (upstream defines no test/check target)",
            "discovered": 0,
            "executed": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "reason": "release archive has no test directories, sources, macros, or test targets",
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
        )
        if not result["passed"]:
            raise ConanException(
                "libkylin-chkname tests failed: {}/20 cases, rc={}".format(
                    passed, proc.returncode
                )
            )

        quoted = " ".join(shlex.quote(part) for part in command)
        runtime = Environment()
        for key, value in runtime_values.items():
            runtime.define(key, value)
        with runtime.vars(self).apply():
            self.run(quoted, env="conanrun")
