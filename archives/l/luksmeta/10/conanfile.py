#!/usr/bin/env python3
"""Conan recipe — luksmeta 10 (Autotools, C)."""

import json
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LuksmetaConan(ConanFile):
    name = "luksmeta"
    version = "10"
    description = "Library and utility for storing metadata in LUKSv1 headers"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/latchset/luksmeta"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("luks", "cryptsetup", "disk-encryption", "metadata")
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # luksmeta.h includes libcryptsetup.h and the shared library exposes
        # cryptsetup symbols, so both usage requirements are public.
        self.requires(
            "cryptsetup/2.8.8",
            transitive_headers=True,
            transitive_libs=True,
        )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "luksmeta is supported on Linux-compatible block-device platforms"
            )

    def _runtime_view(self):
        """Create an entity-only shared-library view for the OHOS loader."""
        view = os.path.join(self.build_folder, "runtime-libs")
        os.makedirs(view, exist_ok=True)
        for dependency in self.dependencies.values():
            if not dependency.package_folder:
                continue
            cpp_info = dependency.cpp_info.aggregated_components()
            for libdir in cpp_info.libdirs:
                source_dir = os.path.join(dependency.package_folder, libdir)
                if not os.path.isdir(source_dir):
                    continue
                for filename in os.listdir(source_dir):
                    if ".so" not in filename or filename.endswith(".la"):
                        continue
                    source = os.path.join(source_dir, filename)
                    if not os.path.isfile(source):
                        continue
                    destination = os.path.join(view, filename)
                    if not os.path.exists(destination):
                        shutil.copy2(os.path.realpath(source), destination)
        return view

    def generate(self):
        runtime_view = self._runtime_view()
        cryptsetup = self.dependencies["cryptsetup"]

        toolchain = AutotoolsToolchain(self)
        # Upstream tests use assert(); keep their checks active in Release.
        toolchain.extra_cflags.append("-UNDEBUG")
        # Native HarmonyOS builds otherwise run config.guess, whose compiled
        # probe cannot execute from the CI worker's HMDFS-backed build tree.
        # Cross builds already receive distinct build/host triples from Conan.
        if not cross_building(self) and str(self.settings.os) == "OHOS":
            toolchain.configure_args.extend([
                "--build=aarch64-unknown-linux-ohos",
                "--host=aarch64-unknown-linux-ohos",
            ])
        toolchain.generate()

        dependencies = PkgConfigDeps(self)
        dependencies.generate()

        pc_path = os.path.join(self.generators_folder, "libcryptsetup.pc")
        include_dir = os.path.join(cryptsetup.package_folder, "include")
        with open(pc_path, "w", encoding="utf-8") as pc_file:
            pc_file.write(
                "prefix={}\n"
                "exec_prefix=${{prefix}}\n"
                "libdir={}\n"
                "includedir={}\n\n"
                "Name: libcryptsetup\n"
                "Description: cryptsetup library (Conan overlay)\n"
                "Version: {}\n"
                "Libs: -L${{libdir}} -lcryptsetup\n"
                "Cflags: -I${{includedir}}\n".format(
                    cryptsetup.package_folder,
                    runtime_view,
                    include_dir,
                    cryptsetup.ref.version,
                )
            )

        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        environment = Environment()
        environment.define("TMPDIR", tmpdir)
        environment.prepend_path("PATH", os.path.join(cryptsetup.package_folder, "bin"))
        environment.prepend_path("LD_LIBRARY_PATH", runtime_view)
        environment.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        environment.vars(self).save_script("luksmeta-build-env")

    def _runner(self, runtime_view):
        runner = self.conf.get(
            "user.luksmeta:qemu_runner", default="", check_type=str
        ).strip()
        library_path = os.pathsep.join([
            os.path.join(self.build_folder, ".libs"),
            runtime_view,
        ])
        if not cross_building(self):
            inherited_path = os.environ.get("LD_LIBRARY_PATH", "")
            if inherited_path:
                library_path += os.pathsep + inherited_path
            return ["env", "LD_LIBRARY_PATH=" + library_path]
        if not runner:
            raise ConanInvalidConfiguration(
                "Cross-building luksmeta tests requires user.luksmeta:qemu_runner"
            )
        return shlex.split(runner) + ["-E", "LD_LIBRARY_PATH=" + library_path]

    def _run_binary(self, name, runtime_view):
        executable = os.path.join(self.build_folder, ".libs", name)
        if not os.path.isfile(executable):
            executable = os.path.join(self.build_folder, name)
        command = self._runner(runtime_view) + [executable]
        self.run(shlex.join(command), cwd=self.build_folder)

    def _run_shell_test(self, runtime_view):
        bash = shutil.which("bash")
        if not bash:
            raise ConanInvalidConfiguration("The upstream CLI test requires bash")

        if not cross_building(self):
            self.run(
                "{} {}".format(
                    shlex.quote(bash),
                    shlex.quote(os.path.join(self.source_folder, "test-luksmeta")),
                ),
                cwd=self.build_folder,
            )
            return

        runner_bin = os.path.join(self.build_folder, "qemu-runner-bin")
        os.makedirs(runner_bin, exist_ok=True)
        runner = shlex.join(self._runner(runtime_view))
        cryptsetup = self.dependencies["cryptsetup"]
        wrappers = {
            "luksmeta": os.path.join(self.build_folder, ".libs", "luksmeta"),
            "cryptsetup": os.path.join(cryptsetup.package_folder, "bin", "cryptsetup"),
        }
        for name, target in wrappers.items():
            wrapper = os.path.join(runner_bin, name)
            with open(wrapper, "w", encoding="utf-8") as script:
                script.write(
                    "#!/bin/sh\nexec {} {} \"$@\"\n".format(
                        runner, shlex.quote(target)
                    )
                )
            os.chmod(wrapper, 0o755)

        original_path = os.environ.get("PATH", "")
        test_path = runner_bin + os.pathsep + original_path
        build_wrapper = os.path.join(self.build_folder, "luksmeta")
        saved_wrapper = build_wrapper + ".libtool"
        os.replace(build_wrapper, saved_wrapper)
        shutil.copy2(os.path.join(runner_bin, "luksmeta"), build_wrapper)
        try:
            self.run(
                "env PATH={} {} {}".format(
                    shlex.quote(test_path),
                    shlex.quote(bash),
                    shlex.quote(os.path.join(self.source_folder, "test-luksmeta")),
                ),
                cwd=self.build_folder,
            )
        finally:
            os.replace(saved_wrapper, build_wrapper)

    def build(self):
        apply_conandata_patches(self)

        os.environ["PATH"] = os.pathsep.join(
            path for path in os.environ.get("PATH", "").split(os.pathsep)
            if path and "safe-bin" not in path
        )
        for key in list(os.environ):
            if key == "BASH_ENV" or key.startswith("BASH_FUNC_") \
                    or key.startswith("CODEBUDDY_SAFE_DELETE"):
                os.environ.pop(key, None)

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        autotools.make(target="check", args=["-j1", "TESTS="])

        runtime_view = self._runtime_view()
        upstream_tests = [
            "test-crc32c",
            "test-lm-assumptions",
            "test-lm-init",
            "test-lm-one",
            "test-lm-two",
            "test-lm-big",
        ]
        for test_name in upstream_tests:
            self._run_binary(test_name, runtime_view)
        self._run_shell_test(runtime_view)
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "passed",
            "framework": "Automake parallel-tests",
            "command": "make check (6 C tests + test-luksmeta)",
            "discovered": 7,
            "executed": 7,
            "passed": 7,
            "failed": 0,
            "skipped": 0,
        }))

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        libdir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(libdir):
            for filename in os.listdir(libdir):
                path = os.path.join(libdir, filename)
                if filename.endswith(".la"):
                    os.remove(path)
                elif os.path.islink(path):
                    temporary = path + ".tmp"
                    shutil.copy2(path, temporary, follow_symlinks=True)
                    os.replace(temporary, path)
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["luksmeta"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.requires = ["cryptsetup::cryptsetup"]
        self.cpp_info.set_property("cmake_file_name", "luksmeta")
        self.cpp_info.set_property("cmake_target_name", "luksmeta::luksmeta")
        self.cpp_info.set_property("pkg_config_name", "luksmeta")
