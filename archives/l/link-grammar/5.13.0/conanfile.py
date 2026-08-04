#!/usr/bin/env python3
"""Conan recipe for Link Grammar 5.13.0."""

import glob
import hashlib
import json
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building, load_toolchain_args
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    check_sha256,
    copy,
    export_conandata_patches,
    get,
    load,
    save,
    unzip,
)
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class LinkGrammarConan(ConanFile):
    name = "link-grammar"
    version = "5.13.0"
    description = "Natural-language parser based on link grammar theory"
    license = "BSD-3-Clause"
    homepage = "https://opencog.github.io/link-grammar-website/"
    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"
    win_bash = True

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        source = self.conan_data["sources"]
        staged = os.path.expanduser(
            "~/Download/link-grammar-link-grammar-5.13.0.tar.gz"
        )
        if os.path.isfile(staged):
            check_sha256(self, staged, source["sha256"])
            unzip(self, staged, strip_root=True)
        else:
            get(self, **source, strip_root=True)

        archive = self.conan_data["autoconf_archive"]
        archive_staged = os.path.expanduser(
            "~/Download/autoconf-archive-2024.10.16.tar.xz"
        )
        archive_root = os.path.join(
            self.source_folder, ".build-aux", "autoconf-archive"
        )
        os.makedirs(archive_root, exist_ok=True)
        if os.path.isfile(archive_staged):
            check_sha256(self, archive_staged, archive["sha256"])
            unzip(self, archive_staged, archive_root, strip_root=True)
        else:
            get(self, **archive, destination=archive_root, strip_root=True)

    def requirements(self):
        self.requires("pcre2/10.45")
        self.requires("sqlite3/3.49.1")

    def build_requirements(self):
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def generate(self):
        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.extend(
            [
                "--disable-java-bindings",
                "--disable-python-bindings",
                "--disable-perl-bindings",
                "--disable-sat-solver",
                "--disable-hunspell",
                "--disable-aspell",
                "--disable-editline",
                "--with-regexlib=pcre2",
                "--enable-static",
                "--disable-shared",
            ]
        )
        toolchain.generate()

        if str(self.settings.os) == "OHOS":
            work_folder = self._work_build_folder()
            if os.path.isdir(work_folder):
                shutil.rmtree(work_folder)
            os.makedirs(work_folder)
            self._stage_build_tools()
            self._stage_dependency_archives()

    def build(self):
        apply_conandata_patches(self)
        with self._dependency_environment().vars(self).apply():
            if not os.path.isfile(os.path.join(self.source_folder, "configure")):
                self.output.info("Bootstrapping the Git tag archive with autoreconf")
                self.run(
                    "autoreconf -fiv",
                    cwd=self.source_folder,
                    env=self._build_environment_files(),
                )
            self._patch_generated_config_guess()
            self._make_generated_configure_hmdfs_safe()
            self._run_configure()
            self._sanitize_generated_feature_paths()
            self.run(
                "make -j1",
                cwd=self._work_build_folder(),
                env=self._build_environment_files(),
            )
            if cross_building(self):
                self.output.info(
                    "Cross build: compiling all four upstream test programs"
                )
                self.run(
                    "make -C tests -j1 dict-reopen multi-dict multi-thread mem-leak",
                    cwd=self._work_build_folder(),
                    env=self._build_environment_files(),
                )
            else:
                self.run(
                    "make -j1 check",
                    cwd=self._work_build_folder(),
                    env=self._build_environment_files(),
                )

    def package(self):
        with self._dependency_environment().vars(self).apply():
            self.run(
                "make -j1 install DESTDIR=%s" % shlex.quote(self.package_folder),
                cwd=self._work_build_folder(),
                env=self._build_environment_files(),
            )
        for metadata in glob.glob(
            os.path.join(self.package_folder, "lib", "*.la")
        ):
            os.remove(metadata)
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.libs = ["link-grammar"]
        self.cpp_info.system_libs = ["m", "pthread"]
        self.cpp_info.resdirs = [os.path.join("share", "link-grammar")]
        self.cpp_info.set_property("cmake_file_name", "link-grammar")
        self.cpp_info.set_property(
            "cmake_target_name", "link-grammar::link-grammar"
        )
        self.cpp_info.set_property("pkg_config_name", "link-grammar")

    def _dependency_environment(self):
        env = Environment()
        self._define_static_dependency(
            env, "pcre2", "PCRE2", ["pcre2-8"]
        )
        self._define_static_dependency(
            env, "sqlite3", "SQLITE3", ["sqlite3"]
        )
        return env

    def _stage_dependency_archives(self):
        destination = self._dependency_archive_folder()
        if os.path.isdir(destination):
            shutil.rmtree(destination)
        os.makedirs(destination)
        requirements = {
            "pcre2": ["pcre2-8"],
            "sqlite3": ["sqlite3"],
        }
        for dependency, libraries in requirements.items():
            cpp_info = self.dependencies[dependency].cpp_info
            for library in libraries:
                candidates = [
                    os.path.join(directory, "lib%s.a" % library)
                    for directory in cpp_info.libdirs
                ]
                archive = next(
                    (path for path in candidates if os.path.isfile(path)), None
                )
                if archive is None:
                    raise ConanException(
                        "Static archive for %s is missing: %s"
                        % (dependency, ", ".join(candidates))
                    )
                shutil.copy2(archive, destination)

    def _dependency_archive_folder(self):
        return os.path.join(self._work_build_folder(), ".dependency-archives")

    def _run_configure(self):
        args = load_toolchain_args(self.generators_folder).get("configure_args", "")
        configure = shlex.quote(os.path.join(self.source_folder, "configure"))
        if str(self.settings.os) == "OHOS":
            shell = self._find_hnp_interpreter(
                "bash", "/data/service/hnp/bash.org/bash_*/bin/bash"
            )
            configure = "%s %s" % (shlex.quote(shell), configure)
        command = "%s %s" % (configure, args)
        self.run(
            command.strip(),
            cwd=self._work_build_folder(),
            env=self._build_environment_files(),
        )

    def _build_environment_files(self):
        env = ["conanbuild"]
        if str(self.settings.os) == "OHOS":
            env.append("link_grammar_tools")
        return env

    def _stage_build_tools(self):
        tools_root = os.path.join(self._work_build_folder(), ".build-tools")
        if os.path.isdir(tools_root):
            shutil.rmtree(tools_root)
        os.makedirs(tools_root)
        tmpdir = os.path.join(self._work_build_folder(), ".tmp")
        os.makedirs(tmpdir, exist_ok=True)

        staged = {}
        env = Environment()
        for name in ("automake", "libtool"):
            package_folder = self.dependencies.build[name].package_folder
            if not package_folder or not os.path.isdir(package_folder):
                raise ConanException("Missing build-tool package folder for %s" % name)
            destination = os.path.join(tools_root, name)
            shutil.copytree(package_folder, destination, symlinks=False)
            staged[name] = destination

        automake_bin = os.path.join(staged["automake"], "bin")
        libtool_bin = os.path.join(staged["libtool"], "bin")
        self._materialize_libtoolize_layout(staged["libtool"])
        launchers = os.path.join(tools_root, "launchers")
        os.makedirs(launchers)
        perl = self._find_hnp_interpreter(
            "perl", "/data/service/hnp/perl.org/perl_*/bin/perl"
        )
        shell = self._find_hnp_interpreter(
            "bash", "/data/service/hnp/bash.org/bash_*/bin/bash"
        )

        self._compile_script_launcher(
            os.path.join(launchers, "aclocal"),
            perl,
            os.path.join(automake_bin, ".aclocal-real"),
            [
                "--automake-acdir="
                + os.path.join(staged["automake"], "share", "aclocal-1.18"),
                "--system-acdir="
                + os.path.join(staged["automake"], "share", "aclocal"),
            ],
        )
        self._compile_script_launcher(
            os.path.join(launchers, "aclocal-1.18"),
            perl,
            os.path.join(automake_bin, ".aclocal-1.18-real"),
            [
                "--automake-acdir="
                + os.path.join(staged["automake"], "share", "aclocal-1.18"),
                "--system-acdir="
                + os.path.join(staged["automake"], "share", "aclocal"),
            ],
        )
        for name in ("automake", "automake-1.18"):
            self._compile_script_launcher(
                os.path.join(launchers, name),
                perl,
                os.path.join(automake_bin, ".%s-real" % name),
                [
                    "--libdir="
                    + os.path.join(staged["automake"], "share", "automake-1.18")
                ],
            )
        self._compile_script_launcher(
            os.path.join(launchers, "libtoolize"),
            shell,
            os.path.join(libtool_bin, "libtoolize"),
            [],
        )

        env.prepend_path("PATH", launchers)
        env.define_path("TMPDIR", tmpdir)
        env.define_path("PWD", self._work_build_folder())
        target_tools = self._target_tool_paths()
        for variable in ("LD", "AR", "NM", "OBJDUMP"):
            env.define_path(variable, target_tools[variable])
        env.define("RANLIB", "%s s" % shlex.quote(target_tools["AR"]))
        required_tools = {
            "ACLOCAL": os.path.join(launchers, "aclocal"),
            "AUTOMAKE": os.path.join(launchers, "automake"),
            "LIBTOOLIZE": os.path.join(launchers, "libtoolize"),
        }
        for variable, executable in required_tools.items():
            if not os.path.isfile(executable) or not os.access(executable, os.X_OK):
                raise ConanException(
                    "Staged %s is not executable: %s" % (variable, executable)
                )
            env.define_path(variable, executable)

        env.prepend_path(
            "PERL5LIB", os.path.join(staged["automake"], "share", "automake-1.18")
        )
        for directory in (
            os.path.join(
                self.source_folder,
                ".build-aux",
                "autoconf-archive",
                "m4",
            ),
            os.path.join(staged["automake"], "share", "aclocal-1.18"),
            os.path.join(staged["automake"], "share", "aclocal"),
            os.path.join(staged["libtool"], "share", "aclocal"),
        ):
            if not os.path.isdir(directory):
                raise ConanException(
                    "Autoconf macro directory is missing: %s" % directory
                )
            env.prepend_path("ACLOCAL_PATH", directory)
        env.define_path(
            "_lt_pkgdatadir",
            os.path.join(staged["libtool"], "share", "libtool-conan"),
        )
        env.vars(self).save_script("link_grammar_tools")

    def _target_tool_paths(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compilers.get("c")
        if not compiler or not os.path.isfile(compiler):
            raise ConanException("C compiler is unavailable for target tools")

        tool_dir = os.path.dirname(compiler)
        names = {
            "LD": "ld.lld",
            "AR": "llvm-ar",
            "NM": "llvm-nm",
            "OBJDUMP": "llvm-objdump",
        }
        tools = {
            variable: os.path.join(tool_dir, name)
            for variable, name in names.items()
        }
        missing = [path for path in tools.values() if not os.path.isfile(path)]
        if missing:
            raise ConanException(
                "Required target tools are missing: %s" % ", ".join(missing)
            )
        return tools

    def _work_build_folder(self):
        if str(self.settings.os) != "OHOS":
            return self.build_folder
        digest = hashlib.sha256(self.build_folder.encode("utf-8")).hexdigest()[:12]
        return os.path.join(
            "/data/storage/el2/base/cache",
            "conan-link-grammar-%s-%s" % (self.version, digest),
        )

    @staticmethod
    def _materialize_libtoolize_layout(libtool_root):
        share = os.path.join(libtool_root, "share")
        layout = os.path.join(share, "libtool-conan")
        os.makedirs(layout, exist_ok=True)
        sources = {
            "build-aux": os.path.join(share, "libtool", "build-aux"),
            "libltdl": os.path.join(share, "libtool", "libltdl"),
            "m4": os.path.join(share, "aclocal"),
        }
        for name, source in sources.items():
            if not os.path.isdir(source):
                raise ConanException("Libtool data directory is missing: %s" % source)
            destination = os.path.join(layout, name)
            if os.path.isdir(destination):
                shutil.rmtree(destination)
            shutil.copytree(source, destination, symlinks=False)

    @staticmethod
    def _find_hnp_interpreter(name, pattern):
        candidates = sorted(glob.glob(pattern), reverse=True)
        executable = candidates[0] if candidates else shutil.which(name)
        if not executable or not os.path.isfile(executable):
            raise ConanException("Required interpreter is missing: %s" % name)
        return executable

    def _compile_script_launcher(self, output, interpreter, script, fixed_args):
        if not os.path.isfile(script):
            raise ConanException("Launcher script is missing: %s" % script)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = compilers.get("c")
        if not compiler or not os.path.isfile(compiler):
            raise ConanException("C compiler is unavailable for tool launchers")

        fixed = [interpreter, script] + list(fixed_args)
        source = output + ".c"
        values = ",\n        ".join(json.dumps(value) for value in fixed)
        save(
            self,
            source,
            """#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(int argc, char **argv)
{
    static const char *fixed[] = {
        %s
    };
    const size_t fixed_count = sizeof(fixed) / sizeof(fixed[0]);
    char **args = (char **)calloc(fixed_count + (size_t)argc, sizeof(char *));
    if (args == NULL) {
        return 126;
    }
    for (size_t i = 0; i < fixed_count; ++i) {
        args[i] = (char *)fixed[i];
    }
    for (int i = 1; i < argc; ++i) {
        args[fixed_count + (size_t)i - 1] = argv[i];
    }
    args[fixed_count + (size_t)argc - 1] = NULL;
    execv(fixed[0], args);
    perror("execv");
    return 127;
}
"""
            % values,
        )
        tmpdir = os.path.join(self._work_build_folder(), ".tmp")
        os.makedirs(tmpdir, exist_ok=True)
        old_tmpdir = os.environ.get("TMPDIR")
        os.environ["TMPDIR"] = tmpdir
        try:
            self.run(
                "%s -O2 %s -o %s"
                % (
                    shlex.quote(compiler),
                    shlex.quote(source),
                    shlex.quote(output),
                ),
                env=None,
            )
        finally:
            if old_tmpdir is None:
                os.environ.pop("TMPDIR", None)
            else:
                os.environ["TMPDIR"] = old_tmpdir
        os.chmod(output, 0o755)

    def _patch_generated_config_guess(self):
        config_guess = os.path.join(self.source_folder, "config.guess")
        contents = load(self, config_guess)
        if "HarmonyOS)" not in contents:
            anchor = "case $UNAME_SYSTEM in\nLinux|GNU|GNU/*)"
            if contents.count(anchor) != 1:
                raise ConanException("Unexpected config.guess system-case layout")
            replacement = (
                "case $UNAME_SYSTEM in\n"
                "HarmonyOS)\n"
                "\techo ${UNAME_MACHINE}-unknown-linux-ohos\n"
                "\texit ;;\n"
                "Linux|GNU|GNU/*)"
            )
            save(self, config_guess, contents.replace(anchor, replacement, 1))
        if "HarmonyOS)" not in load(self, config_guess):
            raise ConanException("Failed to add HarmonyOS to config.guess")

    def _define_static_dependency(self, env, dependency, variable, libraries):
        cpp_info = self.dependencies[dependency].cpp_info
        cflags = " ".join(
            "-I" + shlex.quote(path) for path in cpp_info.includedirs
        )
        libdirs = list(cpp_info.libdirs)
        if str(self.settings.os) == "OHOS":
            libdirs = [self._dependency_archive_folder()]
        libs = ["-L" + shlex.quote(path) for path in libdirs]
        for library in libraries:
            candidates = [
                os.path.join(directory, "lib%s.a" % library)
                for directory in libdirs
            ]
            archive = next((path for path in candidates if os.path.isfile(path)), None)
            if archive is None:
                raise ConanException(
                    "Static archive for %s is missing: %s"
                    % (dependency, ", ".join(candidates))
                )
            libs.append("-l" + library)
        libs.extend("-l" + lib for lib in cpp_info.system_libs)
        env.define(variable + "_CFLAGS", cflags)
        env.define(variable + "_LIBS", " ".join(libs))

    def _make_generated_configure_hmdfs_safe(self):
        configure = os.path.join(self.source_folder, "configure")
        contents = load(self, configure)
        if "umask 077" in contents:
            contents = contents.replace("umask 077", "umask 022")
            save(self, configure, contents)
        if "umask 077" in load(self, configure):
            raise RuntimeError("Failed to remove restrictive configure umask")

    def _sanitize_generated_feature_paths(self):
        feature_header = os.path.join(
            self._work_build_folder(), "link-grammar", "link-features.h"
        )
        contents = load(self, feature_header)
        dependency_paths = []
        for dependency in ("pcre2", "sqlite3"):
            dependency_paths.extend(
                self.dependencies[dependency].cpp_info.includedirs
            )
        for path in dependency_paths:
            contents = contents.replace(" -I%s" % path, "")
        save(self, feature_header, contents)
        remaining = [path for path in dependency_paths if path in contents]
        if remaining:
            raise ConanException(
                "Generated feature metadata retains dependency paths: %s"
                % ", ".join(remaining)
            )
