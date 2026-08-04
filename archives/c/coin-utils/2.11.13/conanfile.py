#!/usr/bin/env python3
"""Conan recipe for COIN-OR CoinUtils 2.11.13 — OpenHarmony aarch64 native port."""

import os
import shutil
import glob
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.apple import fix_apple_shared_install_name, is_apple_os
from conan.tools.build import cross_building, load_toolchain_args
from conan.tools.env import Environment, VirtualRunEnv
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
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout
from conan.tools.microsoft import check_min_vs, is_msvc, unix_path


required_conan_version = ">=2"


class CoinUtilsConan(ConanFile):
    name = "coin-utils"
    version = "2.11.13"
    description = (
        "CoinUtils is an open-source collection of classes and helper "
        "functions that are generally useful to multiple COIN-OR projects."
    )
    topics = ("coin", "sparse", "matrix", "helper", "parsing", "representation")
    url = "https://github.com/conan-io/conan-center-index"
    homepage = "https://github.com/coin-or/CoinUtils"
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

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if str(self.settings.os) == "Windows":
            del self.options.fPIC
            del self.options.shared
            self.package_type = "static-library"

    def configure(self):
        if self.options.get_safe("shared"):
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self, src_folder="src")

    def requirements(self):
        # 鸿蒙 aarch64 上 bzip2 与 zlib 均有现成预编译包，直接引用
        self.requires("bzip2/1.0.8")
        self.requires("zlib/[>=1.2.11 <2]")
        # BLAS/LAPACK/Glpk/ASL 为可选，configure 阶段 --without 关闭

    def validate(self):
        # 上游已知问题：交叉编译 + shared 暂不支持（autotools 老式 libtool 限制）
        if cross_building(self) and self.options.get_safe("shared"):
            raise ConanInvalidConfiguration(
                "coin-utils shared not supported yet when cross-building"
            )

    def build_requirements(self):
        if is_msvc(self):
            self.tool_requires("automake/1.16.5")
        if self.settings_build.os == "Windows":
            self.win_bash = True
            if not self.conf.get("tools.microsoft.bash:path", check_type=str):
                self.tool_requires("msys2/cci.latest")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        if not cross_building(self):
            env = VirtualRunEnv(self)
            env.generate(scope="build")

        tc = AutotoolsToolchain(self)
        # 鸿蒙适配关键：禁用 BLAS/LAPACK/Glpk/ASL
        tc.configure_args.append("--without-blas")
        tc.configure_args.append("--without-lapack")
        tc.configure_args.append("--without-glpk")
        tc.configure_args.append("--without-asl")
        if is_msvc(self):
            tc.configure_args.append(f"--enable-msvc={self.settings.compiler.runtime}")
            tc.extra_cxxflags.append("-EHsc")
            if check_min_vs(self, "180", raise_invalid=False):
                tc.extra_cflags.append("-FS")
                tc.extra_cxxflags.append("-FS")
        env = tc.environment()
        if is_msvc(self):
            compile_wrapper = unix_path(self, self.conf.get("user.automake:compile-wrapper", check_type=str))
            ar_wrapper = unix_path(self, self.conf.get("user.automake:lib-wrapper", check_type=str))
            env.define("CC", f"{compile_wrapper} cl -nologo")
            env.define("CXX", f"{compile_wrapper} cl -nologo")
            env.define("LD", "link -nologo")
            env.define("AR", f"{ar_wrapper} \"lib -nologo\"")
            env.define("NM", "dumpbin -symbols")
            env.define("OBJDUMP", ":")
            env.define("RANLIB", ":")
            env.define("STRIP", ":")
        tc.generate(env)

        if is_msvc(self):
            # Custom AutotoolsDeps for cl like compilers
            # workaround for https://github.com/conan-io/conan/issues/12784
            includedirs = []
            defines = []
            libs = []
            libdirs = []
            linkflags = []
            cxxflags = []
            cflags = []
            for dependency in self.dependencies.values():
                deps_cpp_info = dependency.cpp_info.aggregated_components()
                includedirs.extend(deps_cpp_info.includedirs)
                defines.extend(deps_cpp_info.defines)
                libs.extend(deps_cpp_info.libs + deps_cpp_info.system_libs)
                libdirs.extend(deps_cpp_info.libdirs)
                linkflags.extend(deps_cpp_info.sharedlinkflags + deps_cpp_info.exelinkflags)
                cxxflags.extend(deps_cpp_info.cxxflags)
                cflags.extend(deps_cpp_info.cflags)

            env = Environment()
            env.append("CPPFLAGS", [f"-I{unix_path(self, p)}" for p in includedirs] + [f"-D{d}" for d in defines])
            env.append("_LINK_", [lib if lib.endswith(".lib") else f"{lib}.lib" for lib in libs])
            env.append("LDFLAGS", [f"-L{unix_path(self, p)}" for p in libdirs] + linkflags)
            env.append("CXXFLAGS", cxxflags)
            env.append("CFLAGS", cflags)
            env.vars(self).save_script("conanautotoolsdeps_cl_workaround")
        else:
            deps = AutotoolsDeps(self)
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
                os.path.join("CoinUtils", "configure"),
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
                os.path.join(self.source_folder, "CoinUtils", "src", "Makefile.in"),
                "\t$(install_sh_DATA) config_coinutils.h",
                "\t$(SHELL) $(install_sh_DATA) config_coinutils.h",
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
        else:
            autotools.configure()
            autotools.make()

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
            rename(self,
                   os.path.join(self.package_folder, "lib", "libCoinUtils.a"),
                   os.path.join(self.package_folder, "lib", "CoinUtils.lib"))
        self._sign_shared_libraries()

    def _ohos_work_folder(self):
        return os.path.join(self.build_folder, "ohos-work")

    def _build_shell(self):
        if str(self.settings_build.os) == "OHOS":
            return "/system/bin/sh"
        shell = shutil.which("sh")
        if not shell:
            raise ConanInvalidConfiguration(
                "coin-utils requires sh on the build machine"
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
        self.cpp_info.set_property("pkg_config_name", "coinutils")
        self.cpp_info.libs = ["CoinUtils"]
        self.cpp_info.includedirs = ["include", os.path.join("include", "coin")]
        if not self.options.get_safe("shared"):
            if str(self.settings.os) in ("FreeBSD", "Linux", "OHOS"):
                self.cpp_info.system_libs = ["m"]
            if is_apple_os(self):
                self.cpp_info.frameworks.append("Accelerate")
