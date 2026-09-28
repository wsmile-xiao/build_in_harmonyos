#!/usr/bin/env python3
"""Conan recipe — paryfor 0.1 (header-only C++14 library)."""

import json
import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class ParyforConan(ConanFile):
    name = "paryfor"
    version = "0.1"
    description = "Header-only parallel_for implementation based on atomic queues"
    license = "MIT"
    homepage = "https://github.com/ekg/paryfor"
    url = "https://github.com/ekg/paryfor"
    topics = ("parallel-for", "atomic-queue", "concurrency", "header-only")
    package_type = "header-library"

    settings = "os", "compiler", "build_type", "arch"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if self.settings.compiler.cppstd:
            check_min_cppstd(self, "14")

    def build(self):
        apply_conandata_patches(self)
        self._build_upstream_test()

    def _build_upstream_test(self):
        """Compile and, on native workers, run the official test.cpp."""
        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}
        )
        cxx = compiler_executables.get("cpp") or "clang++"
        executable = os.path.join(self.build_folder, "paryfor-upstream-test")
        source = os.path.join(self.source_folder, "test.cpp")
        command = (
            f"{shlex.quote(cxx)} -std=c++14 -O2 -pthread "
            f"-I{shlex.quote(self.source_folder)} {shlex.quote(source)} "
            f"-o {shlex.quote(executable)}"
        )
        self.run(command, env="conanbuild")

        runner = self.conf.get(
            "user.paryfor:qemu_runner", default="", check_type=str
        ).strip()
        if str(self.settings.os) == "OHOS" and not runner:
            self._sign(executable)
        run_command = "{} {} 1024 4 16".format(
            runner, shlex.quote(executable)
        ).strip()
        self.run(
            run_command,
            env="conanrun",
        )
        result = {
            "status": "passed",
            "framework": "standalone",
            "command": "./paryfor-upstream-test 1024 4 16",
            "discovered": 1,
            "executed": 1,
            "passed": 1,
            "failed": 0,
            "skipped": 0,
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT="
            + json.dumps(result, ensure_ascii=False, separators=(",", ":"))
        )

    @staticmethod
    def _sign(executable):
        """Sign an OHOS executable before running it on a native worker."""
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            raise ConanInvalidConfiguration(
                "binary-sign-tool is required to execute upstream tests on OHOS"
            )
        directory = os.path.dirname(executable)
        unsigned_name = os.path.basename(executable)
        signed_name = unsigned_name + ".signed"
        signed = os.path.join(directory, signed_name)
        subprocess.run(
            [signer, "sign", "-inFile", unsigned_name, "-outFile", signed_name,
             "-selfSign", "1"],
            check=True,
            cwd=directory,
        )
        shutil.move(signed, executable)
        os.chmod(executable, 0o755)

    def package(self):
        copy(
            self,
            "paryfor.hpp",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "LICENSE*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = ["include"]
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
        self.cpp_info.set_property("cmake_file_name", "paryfor")
        self.cpp_info.set_property("cmake_target_name", "paryfor::paryfor")
