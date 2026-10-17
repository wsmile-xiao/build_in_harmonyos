#!/usr/bin/env python3
"""Conan recipe for zenlisp 2013.11.22."""
import glob
import os
import re
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class ZenlispConan(ConanFile):
    name = "zenlisp"
    version = "2013.11.22"
    description = "A small interpreter for a purely symbolic, lexically scoped Lisp dialect"
    license = "BSD-2-Clause"
    homepage = "https://github.com/barak/zenlisp"
    url = "https://github.com/barak/zenlisp"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    _source_url = (
        "https://github.com/barak/zenlisp/archive/"
        "9ae13c8b5ecd5e4d1167cf446532208ab2ee97b0.tar.gz"
    )
    _source_sha256 = (
        "5285107e98516da16a9fe457a22ecacb9eb758d47b12057916eea0a2cdea49db"
    )

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "zenlisp is supported only on Linux and HarmonyOS"
            )

    def export_sources(self):
        copy(
            self,
            "patches/*.patch",
            src=self.recipe_folder,
            dst=self.export_sources_folder,
        )

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(
            self,
            url=self._source_url,
            sha256=self._source_sha256,
            strip_root=True,
        )

    def _compiler(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        return compilers.get("c") or "clang"

    def _shell(self):
        return (
            os.environ.get("CONFIG_SHELL")
            or shutil.which("bash")
            or shutil.which("sh")
            or "/system/bin/sh"
        )

    def _run_shell(self, command):
        self.run(
            '"{}" -c {}'.format(self._shell(), shlex.quote(command)),
            cwd=self.source_folder,
        )

    def _apply_source_patch(self):
        patch_file = os.path.join(
            self.export_sources_folder,
            "patches",
            "0001-relocatable-default-image.patch",
        )
        self._run_shell(
            "patch -p1 -i {}".format(shlex.quote(patch_file))
        )

    def _sign_binary(self, path):
        if self.settings.os != "OHOS":
            return
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning(
                "binary-sign-tool is unavailable; native OHOS execution may require "
                "post-build signing"
            )
            return
        signed = path + ".signed"
        self.run(
            '"{}" sign -inFile "{}" -outFile "{}" '
            "-selfSign 1 -signAlg SHA256withECDSA".format(signer, path, signed)
        )
        if not os.path.isfile(signed):
            raise ConanException("binary-sign-tool did not create {}".format(signed))
        os.replace(signed, path)
        os.chmod(path, 0o755)

    def _run_upstream_tests(self, zl_path):
        output_path = os.path.join(self.build_folder, "zenlisp-upstream-test.out")
        command = '"{}" -i < "{}" > "{}"'.format(
            zl_path,
            os.path.join(self.source_folder, "test.l"),
            output_path,
        )
        self._run_shell(command)

        with open(output_path, encoding="utf-8", errors="replace") as actual_file:
            actual = actual_file.read()
        with open(
            os.path.join(self.source_folder, "test.OK"),
            encoding="utf-8",
            errors="replace",
        ) as expected_file:
            expected = expected_file.read()

        actual = re.sub(r"^\* [0-9]+: ", "* ", actual, flags=re.MULTILINE)
        if actual != expected:
            raise ConanException(
                "zenlisp upstream test output differs from test.OK"
            )
        try:
            os.remove(output_path)
        except OSError:
            pass

    def build(self):
        self._apply_source_patch()

        if not can_run(self):
            raise ConanInvalidConfiguration(
                "zenlisp must run its target interpreter during the build to "
                "generate the default image and execute the upstream test suite"
            )

        cc = self._compiler()
        zl_path = os.path.join(self.source_folder, "zl")
        macro = '-DDEFAULT_IMAGE="share/zenlisp/zenlisp"'
        compile_command = '"{}" -std=c89 -O2 -D_GNU_SOURCE {} -o "{}" "{}"'.format(
            cc,
            shlex.quote(macro),
            zl_path,
            os.path.join(self.source_folder, "zl.c"),
        )
        self.run(compile_command, cwd=self.source_folder)
        self._sign_binary(zl_path)

        image_command = (
            'printf \'%s\\n\' "(load base) (dump-image zenlisp)" | '
            '"{}" -bi -n 12K'
        ).format(zl_path)
        self._run_shell(image_command)
        if not os.path.isfile(os.path.join(self.source_folder, "zenlisp")):
            raise ConanException("zenlisp default image was not generated")

        self._run_upstream_tests(zl_path)

    def package(self):
        runtime_dir = os.path.join(self.package_folder, "share", "zenlisp")
        copy(self, "zl", src=self.source_folder, dst=os.path.join(self.package_folder, "bin"))
        copy(self, "zenlisp", src=self.source_folder, dst=runtime_dir)
        for path in glob.glob(os.path.join(self.source_folder, "*.l")):
            copy(self, os.path.basename(path), src=self.source_folder, dst=runtime_dir)
        for path in glob.glob(os.path.join(self.source_folder, "src", "*", "*.l")):
            copy(
                self,
                os.path.basename(path),
                src=os.path.dirname(path),
                dst=runtime_dir,
            )
        copy(
            self,
            "zl.1",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "man", "man1"),
        )
        copy(
            self,
            "zenlisp.txt",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "share", "doc", "zenlisp"),
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        runtime_dir = os.path.join(self.package_folder, "share", "zenlisp")
        self.runenv_info.define("ZENLISP_IMAGE", os.path.join(runtime_dir, "zenlisp"))
        self.runenv_info.define("ZENSRC", runtime_dir)
