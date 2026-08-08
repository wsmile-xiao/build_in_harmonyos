#!/usr/bin/env python3
"""Conan recipe for COIN-OR Osi 0.108.12 - OpenHarmony aarch64 port."""

import glob
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name
from conan.tools.build import cross_building, load_toolchain_args
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rename,
    replace_in_file,
    rm,
    rmdir,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.microsoft import check_min_vs, is_msvc, msvc_runtime_flag


required_conan_version = ">=2.28"


class CoinOsiConan(ConanFile):
    name = "coin-osi"
    version = "0.108.12"
    description = "COIN-OR Open Solver Interface, a uniform API for LP/MIP solvers"
    topics = ("coin-or", "osi", "lp", "solver", "interface")
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/coin-or/Osi"
    license = "EPL-2.0"
    package_type = "library"

    settings = "os", "arch", "build_type", "compiler"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    @property
    def _settings_build(self):
        return getattr(self, "settings_build", self.settings)

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        # Provided by PR #3882.
        self.requires("coin-utils/2.11.13", transitive_headers=True)

    def validate(self):
        if self.settings.os == "Windows" and self.options.shared:
            raise ConanInvalidConfiguration(
                "coin-osi does not support shared builds on Windows"
            )
        if hasattr(self, "settings_build") and cross_building(self) and self.options.shared:
            raise ConanInvalidConfiguration(
                "coin-osi shared not supported yet when cross-building"
            )

    def build_requirements(self):
        if self._settings_build.os == "Windows":
            self.win_bash = True
            if not self.conf.get("tools.microsoft.bash:path", check_type=str):
                self.tool_requires("msys2/cci.latest")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        os.makedirs(self._sample_data_folder(), exist_ok=True)
        get(
            self,
            **self.conan_data["test_sources"]["data_sample"],
            strip_root=True,
            destination=self._sample_data_folder(),
        )
        apply_conandata_patches(self)

    def generate(self):
        env = VirtualBuildEnv(self)
        env.generate()

        tc = AutotoolsToolchain(self)
        tc.configure_args.extend([
            "--without-blas",
            "--without-lapack",
            "--without-cplex",
            "--without-gurobi",
            "--without-mosek",
            "--without-xpress",
            "--without-soplex",
            "--without-glpk",
        ])
        if is_msvc(self):
            tc.extra_cxxflags.append("-EHsc")
            tc.configure_args.append(f"--enable-msvc={msvc_runtime_flag(self)}")
            if check_min_vs(self, "180", raise_invalid=False):
                tc.extra_cflags.append("-FS")
                tc.extra_cxxflags.append("-FS")
        env = tc.environment()
        if is_msvc(self):
            env.define("CC", "cl -nologo")
            env.define("CXX", "cl -nologo")
            env.define("LD", "link -nologo")
            env.define("AR", "lib -nologo")
        if self._settings_build.os == "Windows":
            env.define("PKG_CONFIG_PATH", self.generators_folder)
        tc.generate(env)

        deps = PkgConfigDeps(self)
        deps.generate()

    def build(self):
        autotools = Autotools(self)
        if str(self.settings.os) == "OHOS":
            work_folder = self._ohos_work_folder()
            previous_umask = os.umask(0o002)
            try:
                os.makedirs(work_folder, mode=0o775, exist_ok=True)
            finally:
                os.umask(previous_umask)

            configure_scripts = (
                "configure",
                os.path.join("Osi", "configure"),
            )
            for relative_path in configure_scripts:
                configure = os.path.join(self.source_folder, relative_path)
                replace_in_file(
                    self,
                    configure,
                    "(umask 077 && mkdir $tmp)",
                    "(umask 002 && mkdir $tmp)",
                )
                replace_in_file(
                    self,
                    configure,
                    "umask 077 && mktemp -d",
                    "umask 002 && mktemp -d",
                )
            replace_in_file(
                self,
                os.path.join(
                    self.source_folder, "Osi", "src", "Osi", "Makefile.in"
                ),
                "\t$(install_sh_DATA) config_osi.h",
                "\t$(SHELL) $(install_sh_DATA) config_osi.h",
            )
            configure_args = load_toolchain_args(self.generators_folder).get(
                "configure_args", ""
            )
            configure = os.path.join(self.source_folder, "configure")
            config_shell = self._build_shell()
            command = shlex.join([config_shell, configure])
            command = f"CONFIG_SHELL={shlex.quote(config_shell)} {command}"
            if configure_args:
                command = f"{command} {configure_args}"
            self.run(command, cwd=work_folder)
            self.run("make -j1", cwd=work_folder)
            if str(self._settings_build.os) == "OHOS":
                self._run_ohos_upstream_tests(work_folder)
            else:
                self.output.info(
                    "Skipping upstream unitTest execution while cross-building; "
                    "the target executable cannot run on this build machine."
                )
        else:
            autotools.configure()
            autotools.make()
            if cross_building(self):
                self.output.info(
                    "Skipping upstream unitTest execution while cross-building; "
                    "the target executable cannot run on this build machine."
                )
            else:
                autotools.make(target="test")

    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        if str(self.settings.os) == "OHOS":
            destination = shlex.quote(self.package_folder)
            self.run(
                f"make install DESTDIR={destination} -j1",
                cwd=self._ohos_work_folder(),
            )
        else:
            autotools = Autotools(self)
            autotools.install(args=["-j1"])
        rm(self, "*.la", os.path.join(self.package_folder, "lib"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        fix_apple_shared_install_name(self)
        if is_msvc(self):
            for libname in ("Osi", "OsiCommonTests"):
                rename(self,
                       os.path.join(self.package_folder, "lib", f"lib{libname}.lib"),
                       os.path.join(self.package_folder, "lib", f"{libname}.lib"))
        self._sign_shared_libraries()

    def _ohos_work_folder(self):
        return os.path.join(self.build_folder, "ohos-work")

    def _sample_data_folder(self):
        return os.path.join(self.source_folder, "_test_data", "Sample")

    def _build_shell(self):
        if str(self._settings_build.os) == "OHOS":
            return "/system/bin/sh"
        shell = shutil.which("sh")
        if not shell:
            raise ConanInvalidConfiguration(
                "coin-osi requires sh on the build machine"
            )
        return shell

    def _sign_shared_libraries(self):
        if str(self.settings.os) != "OHOS" or not self.options.get_safe("shared"):
            return

        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanInvalidConfiguration(
                "OHOS shared libraries require llvm-objcopy and binary-sign-tool"
            )

        libraries = glob.glob(
            os.path.join(self.package_folder, "lib", "**", "*.so*"), recursive=True
        )
        for library in libraries:
            if os.path.islink(library):
                continue
            self._sign_elf_atomically(library, objcopy, signer)

    def _run_ohos_upstream_tests(self, work_folder):
        test_dir = os.path.join(work_folder, "Osi", "test")
        self.run("make unitTest -j1", cwd=test_dir)
        unit_test = os.path.join(test_dir, "unitTest")
        self._sign_ohos_executable(unit_test)
        unittestflags = f"unittestflags=-mpsDir={self._sample_data_folder()}"
        self.run(f"make test -j1 {shlex.quote(unittestflags)}", cwd=test_dir)

    def _sign_ohos_executable(self, path):
        if str(self.settings.os) != "OHOS":
            return
        if not os.path.isfile(path):
            raise ConanInvalidConfiguration(f"OHOS test executable not found: {path}")

        objcopy = self._find_ohos_tool("llvm-objcopy")
        signer = self._find_ohos_tool("binary-sign-tool")
        if not objcopy or not signer:
            raise ConanInvalidConfiguration(
                "OHOS upstream tests require llvm-objcopy and binary-sign-tool"
            )
        self._sign_elf_atomically(path, objcopy, signer)

    def _sign_elf_atomically(self, path, objcopy, signer):
        original_mode = os.stat(path).st_mode
        temporary = f"{path}.signing"
        try:
            shutil.copy2(path, temporary)
            self.run(f'"{objcopy}" --remove-section .codesign "{temporary}"')
            self.run(
                f'"{signer}" sign -inFile "{temporary}" '
                f'-outFile "{temporary}" -selfSign 1'
            )
            os.chmod(temporary, original_mode)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.remove(temporary)

    def _find_ohos_tool(self, name):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler_dir = os.path.dirname(compilers.get("cpp", ""))
        candidates = [
            os.path.join(compiler_dir, name) if compiler_dir else "",
            os.path.join("/data/service/hnp/bin", name),
            shutil.which(name) or "",
        ]
        return next((path for path in candidates if os.path.isfile(path)), "")

    def package_info(self):
        self.cpp_info.components["libosi"].set_property("pkg_config_name", "osi")
        self.cpp_info.components["libosi"].libs = ["Osi"]
        self.cpp_info.components["libosi"].includedirs = [
            os.path.join("include", "coin")
        ]
        self.cpp_info.components["libosi"].requires = ["coin-utils::coin-utils"]

        self.cpp_info.components["osi-unittests"].set_property(
            "pkg_config_name", "osi-unittests"
        )
        self.cpp_info.components["osi-unittests"].libs = ["OsiCommonTests"]
        self.cpp_info.components["osi-unittests"].requires = ["libosi"]
