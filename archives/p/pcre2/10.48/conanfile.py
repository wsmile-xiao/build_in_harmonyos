#!/usr/bin/env python3
"""Conan recipe for PCRE2 10.48 (Autotools, static PIC libraries).

Reuses the proven 10.47 OHOS adaptation (config.guess/config.sub/configure
patches, capability-tested shell probe, CONFIG_SHELL reassertion, LOG_COMPILER
dispatch, relocatable pkg-config metadata). Version bumped 10.47 -> 10.48.
"""

import os
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    load,
    rm,
    save,
)
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


_CONFIGURE_ARGS = (
    "--enable-static",
    "--disable-shared",
    "--enable-jit",
    "--enable-pcre2-16",
    "--enable-pcre2-32",
    "--disable-pcre2grep-libz",
    "--disable-pcre2grep-libbz2",
)

_INSTALL_DIR_ARGS = (
    "--prefix=/",
    "--bindir=${prefix}/bin",
    "--sbindir=${prefix}/bin",
    "--libdir=${prefix}/lib",
    "--includedir=${prefix}/include",
    "--oldincludedir=${prefix}/include",
)

_BUILD_ENVIRONMENT = ["conanbuild", "pcre2_shell"]

_RELOCATABLE_CONFIG_PREFIX = """case \"$0\" in
  */*) pcre2_config=$0 ;;
  *) pcre2_config=`command -v \"$0\"` || exit 1 ;;
esac
pcre2_config_dir=${pcre2_config%/*}
prefix=`CDPATH= cd -P \"$pcre2_config_dir/..\" 2>/dev/null && pwd` || exit 1
"""


class Pcre2Conan(ConanFile):
    name = "pcre2"
    version = "10.48"
    description = "Perl-compatible regular expression library and tools"
    license = "BSD-3-Clause"
    homepage = "https://www.pcre.org/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        if self.options.get_safe("fPIC"):
            toolchain.extra_cflags.append("-fPIC")
        toolchain.configure_args.extend(_CONFIGURE_ARGS)
        toolchain.generate()

    def _config_shell(self):
        candidates = []
        configured_shell = os.environ.get("CONFIG_SHELL")
        if configured_shell:
            candidates.append(configured_shell)

        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        c_compiler = compilers.get("c") if compilers else None
        if c_compiler:
            compiler_path = shlex.split(c_compiler)[0]
            candidates.append(os.path.join(os.path.dirname(compiler_path), "bash"))

        candidates.extend(
            ["/system/bin/sh", shutil.which("bash"), shutil.which("sh"), "/bin/sh"]
        )
        seen = set()
        for candidate in candidates:
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            if not os.path.isfile(candidate) or not os.access(candidate, os.X_OK):
                continue
            try:
                probe = subprocess.run(
                    [candidate, "-c", "pwd >/dev/null"],
                    cwd=self.build_folder,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=5,
                    check=False,
                )
            except (OSError, subprocess.TimeoutExpired):
                continue
            if probe.returncode == 0 and not probe.stdout and not probe.stderr:
                return candidate

        raise ConanInvalidConfiguration(
            "No executable POSIX shell can preserve the build working directory"
        )

    def _save_shell_environment(self, config_shell):
        shell_environment = Environment()
        shell_environment.define("CONFIG_SHELL", config_shell)
        shell_environment.define("SHELL", config_shell)
        if str(self.settings.os) == "OHOS":
            shell_environment.define("MKDIR_P", "/system/bin/mkdir -p")
        shell_environment.vars(self).save_script("pcre2_shell")

    def _run_make(self, *args):
        make_program = self.conf.get("tools.gnu:make_program", default="make")
        command = " ".join([shlex.quote(make_program), *args])
        self.run(
            command,
            cwd=self.build_folder,
            env=_BUILD_ENVIRONMENT,
        )

    @staticmethod
    def _test_log_compiler(config_shell):
        dispatcher = (
            'case "$$0" in '
            "RunTest|*/RunTest|RunGrepTest|*/RunGrepTest) "
            f'exec {shlex.quote(config_shell)} "$$0" "$$@";; '
            '*) exec "$$0" "$$@";; '
            "esac"
        )
        command = "{} -c {}".format(shlex.quote(config_shell), shlex.quote(dispatcher))
        return shlex.quote(f"LOG_COMPILER={command}")

    def build(self):
        apply_conandata_patches(self)
        configure = os.path.join(self.source_folder, "configure")
        config_shell = self._config_shell()
        self._save_shell_environment(config_shell)
        configure_args = _INSTALL_DIR_ARGS + _CONFIGURE_ARGS
        self.run(
            "{} {} {}".format(
                shlex.quote(config_shell),
                shlex.quote(configure),
                shlex.join(configure_args),
            ),
            cwd=self.build_folder,
            env=_BUILD_ENVIRONMENT,
        )
        self._run_make("-j1")
        self._run_make("-j1", "check", self._test_log_compiler(config_shell))

    def package(self):
        self._save_shell_environment(self._config_shell())
        self._run_make(
            "-j1",
            "install",
            "DESTDIR={}".format(shlex.quote(self.package_folder)),
            "dist_doc_DATA=",
            "dist_html_DATA=",
            "dist_man_MANS=",
        )
        self._relocate_discovery_metadata()

    def _relocate_discovery_metadata(self):
        pkgconfig_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        pc_names = (
            "libpcre2-8.pc",
            "libpcre2-16.pc",
            "libpcre2-32.pc",
            "libpcre2-posix.pc",
        )
        for pc_name in pc_names:
            pc_path = os.path.join(pkgconfig_dir, pc_name)
            content = load(self, pc_path)
            if content.count("prefix=/\n") != 1:
                raise ConanInvalidConfiguration(
                    f"Unexpected installed pkg-config prefix in {pc_name}"
                )
            save(
                self,
                pc_path,
                content.replace("prefix=/\n", "prefix=${pcfiledir}/../..\n", 1),
            )

        config_path = os.path.join(self.package_folder, "bin", "pcre2-config")
        config_content = load(self, config_path)
        if config_content.count("prefix=/\n") != 1:
            raise ConanInvalidConfiguration(
                "Unexpected installed prefix in pcre2-config"
            )
        save(
            self,
            config_path,
            config_content.replace("prefix=/\n", _RELOCATABLE_CONFIG_PREFIX, 1),
        )

        # Libtool archives embed the build-time /lib path. Conan component and
        # pkg-config metadata provide the supported static-link contract.
        rm(
            self,
            "*.la",
            os.path.join(self.package_folder, "lib"),
            recursive=True,
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "pcre2")

        for width in ("8", "16", "32"):
            component = self.cpp_info.components[f"pcre2-{width}"]
            component.libs = [f"pcre2-{width}"]
            component.defines = ["PCRE2_STATIC"]
            component.set_property("pkg_config_name", f"libpcre2-{width}")
            component.set_property("cmake_target_name", f"pcre2::{width}BIT")

        posix = self.cpp_info.components["pcre2-posix"]
        posix.libs = ["pcre2-posix"]
        posix.defines = ["PCRE2_STATIC"]
        posix.requires = ["pcre2-8"]
        posix.set_property("pkg_config_name", "libpcre2-posix")
        posix.set_property("cmake_target_name", "pcre2::POSIX")
