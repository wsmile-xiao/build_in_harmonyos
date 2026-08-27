#!/usr/bin/env python3
"""Conan recipe for libunwind 1.6.2 on OHOS."""

import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
    rmdir,
    replace_in_file,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibunwindConan(ConanFile):
    name = "libunwind"
    version = "1.6.2"
    description = "Portable stack unwinding library"
    license = "MIT"
    homepage = "https://www.nongnu.org/libunwind/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def validate(self):
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                "libunwind OHOS adaptation is prepared for armv8/AArch64"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.extend(
            [
                "--disable-shared",
                "--enable-static",
                "--disable-coredump",
                "--disable-ptrace",
                "--disable-setjmp",
                "--disable-documentation",
                "--disable-minidebuginfo",
                "--disable-zlibdebuginfo",
                "--disable-dependency-tracking",
            ]
        )
        if self.settings.os == "OHOS":
            triplet = "aarch64-linux-ohos"
            toolchain.configure_args.extend(
                [
                    f"--build={triplet}",
                    f"--host={triplet}",
                    f"--target={triplet}",
                ]
            )
        toolchain.generate()

        if self.settings.os == "OHOS":
            wrapper_dir = os.path.join(self.build_folder, "ohos-configure-tools")
            os.makedirs(wrapper_dir, exist_ok=True)
            mktemp = os.path.join(wrapper_dir, "mktemp")
            with open(mktemp, "w", encoding="utf-8", newline="\n") as handle:
                handle.write("#!/bin/sh\nexit 1\n")
            os.chmod(mktemp, 0o755)

            tools = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            )
            compiler = tools.get("c", "")
            tool_dir = os.path.dirname(compiler)
            if not tool_dir and os.path.isdir("/data/service/hnp/bin"):
                tool_dir = "/data/service/hnp/bin"

            if tool_dir:
                env = Environment()
                env.prepend_path("PATH", tool_dir)
                env.prepend_path("PATH", wrapper_dir)
                for variable, executable in {
                    "AR": "llvm-ar",
                    "NM": "llvm-nm",
                    "RANLIB": "llvm-ranlib",
                    "STRIP": "llvm-strip",
                }.items():
                    path = os.path.join(tool_dir, executable)
                    if os.path.exists(path):
                        env.define_path(variable, path)
                env.vars(self).save_script("libunwind_ohos_tools")

        self._configure_args = list(toolchain.configure_args)

    @staticmethod
    def _quote_args(args):
        return " ".join(shlex.quote(str(arg)) for arg in args)

    def _ohos_configure_tmpdir(self):
        if os.path.isdir("/data/storage/el2/base"):
            return "/data/storage/el2/base/libunwind-configure-tmp"
        return os.path.join(self.build_folder, "ohos-configure-tmp").replace("\\", "/")

    def _ohos_configure_env(self):
        wrapper_dir = os.path.join(
            self.build_folder, "ohos-configure-tools"
        ).replace("\\", "/")
        tmp_dir = self._ohos_configure_tmpdir()
        os.makedirs(tmp_dir, exist_ok=True)
        path_entries = [wrapper_dir]

        tools = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        compiler = tools.get("c", "")
        tool_dir = os.path.dirname(compiler)
        if not tool_dir and os.path.isdir("/data/service/hnp/bin"):
            tool_dir = "/data/service/hnp/bin"
        tool_dir = tool_dir.replace("\\", "/")
        if tool_dir:
            path_entries.append(tool_dir)

        assignments = [
            f"TMPDIR={shlex.quote(tmp_dir)}",
            "PATH={}:$PATH".format(
                ":".join(shlex.quote(entry) for entry in path_entries)
            )
        ]
        if tool_dir:
            for variable, executable in {
                "AR": "llvm-ar",
                "NM": "llvm-nm",
                "RANLIB": "llvm-ranlib",
                "STRIP": "llvm-strip",
            }.items():
                path = os.path.join(tool_dir, executable).replace("\\", "/")
                if os.path.exists(path):
                    assignments.append(f"{variable}={shlex.quote(path)}")
        return " ".join(assignments)

    def _patch_ohos_config_status_tmpdir(self):
        if self.settings.os != "OHOS":
            return

        configure = os.path.join(self.source_folder, "configure")
        search = """# Create a (secure) tmp directory for tmp files.

{
  tmp=`(umask 077 && mktemp -d "./confXXXXXX") 2>/dev/null` &&
  test -d "$tmp"
}  ||
{
  tmp=./conf$$-$RANDOM
  (umask 077 && mkdir "$tmp")
} || as_fn_error $? "cannot create a temporary directory in ." "$LINENO" 5
ac_tmp=$tmp"""
        replace = """# Create a (secure) tmp directory for tmp files.
: ${TMPDIR:=.}
{
  tmp=`(umask 077 && mktemp -d "$TMPDIR/confXXXXXX") 2>/dev/null` &&
  test -d "$tmp"
}  ||
{
  tmp=$TMPDIR/conf$$-$RANDOM
  (umask 077 && mkdir "$tmp")
} || as_fn_error $? "cannot create a temporary directory in $TMPDIR" "$LINENO" 5
ac_tmp=$tmp"""
        replace_in_file(self, configure, search, replace, strict=True)

    def _configure(self):
        autotools = Autotools(self)
        if self.settings.os != "OHOS":
            autotools.configure()
            return

        os.makedirs(self.build_folder, exist_ok=True)
        configure = os.path.join(self.source_folder, "configure").replace("\\", "/")
        command = "{} sh {} {}".format(
            self._ohos_configure_env(),
            shlex.quote(configure),
            self._quote_args(self._configure_args),
        )
        self.run(command, cwd=self.build_folder, env="conanbuild")

    def _run_ohos_upstream_subset(self):
        tests = [
            "test-proc-info",
            "test-static-link",
            "test-strerror",
            "Gtest-bt",
            "Ltest-bt",
            "Gtest-exc",
            "Ltest-exc",
            "Gtest-init",
            "Ltest-init",
            "Gtest-concurrent",
            "Ltest-concurrent",
            "Gtest-trace",
            "Ltest-trace",
            "test-async-sig",
            "test-flush-cache",
            "test-init-remote",
            "test-mem",
            "Ltest-varargs",
            "Ltest-nomalloc",
            "Lrs-race",
        ]
        excluded = [
            "Gtest-resume-sig",
            "Ltest-resume-sig",
            "Gtest-resume-sig-rt",
            "Ltest-resume-sig-rt",
            "Ltest-init-local-signal",
            "Ltest-mem-validate",
            "test-reg-state",
            "Ltest-nocalloc",
            "run-check-namespace",
        ]
        self.output.info(
            "RUN LIBUNWIND_UPSTREAM=20/29 scope=ohos-stable-subset "
            "excluded={}".format(",".join(excluded))
        )

        tests_dir = os.path.join(self.build_folder, "tests")
        self.run(
            "make -j1 -C tests {}".format(self._quote_args(tests)),
            cwd=self.build_folder,
            env="conanbuild",
        )
        for test in tests:
            self.run("./{}".format(shlex.quote(test)), cwd=tests_dir, env="conanbuild")

        self.output.info(
            "PASS LIBUNWIND_UPSTREAM=20/29 scope=ohos-stable-subset "
            "excluded={}".format(",".join(excluded))
        )

    def build(self):
        apply_conandata_patches(self)
        self._patch_ohos_config_status_tmpdir()
        self._configure()
        autotools = Autotools(self)
        autotools.make(args=["-j1"])

        run_upstream_tests = self.conf.get(
            "user.libunwind:run_upstream_tests",
            default=False,
            check_type=bool,
        )
        if run_upstream_tests and can_run(self) and self.settings.os == "OHOS":
            self._run_ohos_upstream_subset()
        elif run_upstream_tests and can_run(self):
            autotools.make(target="check", args=["-j1"])
        else:
            reason = "cross_building" if not can_run(self) else "disabled_by_default"
            self.output.info(
                "NOT_RUN LIBUNWIND_UPSTREAM=0/29 "
                f"reason={reason}; enable with "
                "-c user.libunwind:run_upstream_tests=True"
            )

    def package(self):
        Autotools(self).install(args=["-j1"])
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["unwind"]
        self.cpp_info.set_property("cmake_file_name", "libunwind")
        self.cpp_info.set_property("cmake_target_name", "libunwind::libunwind")
        self.cpp_info.set_property("pkg_config_name", "libunwind")
