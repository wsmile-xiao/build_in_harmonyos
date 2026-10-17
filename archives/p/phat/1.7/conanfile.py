#!/usr/bin/env python3
"""Conan recipe — PHAT 1.7 (C++11 header library and CLI)."""

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


class PhatConan(ConanFile):
    name = "phat"
    version = "1.7"
    description = "Persistent Homology Algorithm Toolbox"
    license = "LGPL-3.0-or-later"
    homepage = "https://bitbucket.org/phat-code/phat"
    url = "https://bitbucket.org/phat-code/phat"
    topics = ("persistent-homology", "topological-data-analysis", "header-only")
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if self.settings.compiler.cppstd:
            check_min_cppstd(self, "11")
        if self.options.shared:
            raise ConanInvalidConfiguration("PHAT 1.7 only provides a header library")

    def build(self):
        apply_conandata_patches(self)
        os.makedirs(self._output_directory(), exist_ok=True)
        self._compile("src/phat.cpp", self._cli_path())
        upstream_test = os.path.join(self._output_directory(), "phat-upstream-self-test")
        self._compile("src/self_test.cpp", upstream_test)
        self._run_upstream_test(upstream_test)

    def _compiler(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}
        )
        return executables.get("cpp") or "clang++"

    def _compile(self, relative_source, output):
        source = os.path.join(self.source_folder, relative_source)
        include = os.path.join(self.source_folder, "include")
        pic = "-fPIC " if self.options.get_safe("fPIC") else ""
        command = (
            f"{shlex.quote(self._compiler())} -std=c++11 -O2 -DNDEBUG -pthread {pic}"
            f"-I{shlex.quote(include)} {shlex.quote(source)} -o {shlex.quote(output)}"
        )
        self.run(command, env="conanbuild")

    def _run_upstream_test(self, executable):
        runner = self.conf.get(
            "user.phat:qemu_runner", default="", check_type=str
        ).strip()
        if str(self.settings.os) == "OHOS" and not runner:
            self._sign(executable)
        test_data = os.path.join(self.source_folder, "examples", "torus.bin")
        command = "{} {} {}".format(
            runner, shlex.quote(executable), shlex.quote(test_data)
        ).strip()
        self.run(command, env="conanrun")
        result = {
            "status": "passed",
            "framework": "standalone",
            "command": "./phat-upstream-self-test examples/torus.bin",
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

    def _output_directory(self):
        return os.path.join(self.build_folder, "phat-build")

    def _cli_path(self):
        return os.path.join(self._output_directory(), "phat")

    def package(self):
        copy(
            self,
            "*.h",
            src=os.path.join(self.source_folder, "include"),
            dst=os.path.join(self.package_folder, "include"),
        )
        copy(
            self,
            "COPYING*",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        copy(
            self,
            "phat",
            src=self._output_directory(),
            dst=os.path.join(self.package_folder, "bin"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "phat")
        self.cpp_info.set_property("cmake_target_name", "phat::phat")
