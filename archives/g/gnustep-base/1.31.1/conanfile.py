#!/usr/bin/env python3
"""Conan recipe for GNUstep Base 1.31.1."""

import os
import shutil
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment
from conan.tools.files import (
    chdir,
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
    save,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain
from conan.tools.layout import basic_layout


class GnustepBaseConan(ConanFile):
    name = "gnustep-base"
    version = "1.31.1"
    description = "GNUstep Foundation/Base library"
    license = "LGPL-2.1-or-later AND GPL-3.0-or-later"
    homepage = "https://gnustep.github.io/"
    url = "https://github.com/gnustep/libs-base"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"gnustep-base is prepared for Linux/OHOS targets, got {self.settings.os}"
            )
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("libobjc2/2.2.1", transitive_headers=True, transitive_libs=True)
        self.requires("libffi/3.5.2", transitive_headers=True, transitive_libs=True)
        # GNUstep Base treats libcurl as a hard dependency when using the
        # libobjc2/Objective-C 2.0 ("ng") runtime.
        self.requires("curl/8.15.0", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        self.tool_requires("gnustep-make/2.9.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"])

    def generate(self):
        AutotoolsDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            [
                "--with-installation-domain=SYSTEM",
                "--disable-importing-config-file",
                "--disable-xml",
                "--disable-xslt",
                "--disable-tls",
                "--disable-zeroconf",
                "--disable-icu",
                "--disable-libdispatch",
                "--disable-nsurlsession",
                "--disable-iconv",
            ]
        )
        ffi = self.dependencies["libffi"]
        http_stack = "c" + "url"
        http_stack_option = "--with-" + http_stack
        tc.configure_args.extend(
            [
                f"--with-ffi-include={self._first_dir(ffi.cpp_info.includedirs, ffi.package_folder, 'include')}",
                f"--with-ffi-library={self._first_dir(ffi.cpp_info.libdirs, ffi.package_folder, 'lib')}",
                f"{http_stack_option}={self.dependencies[http_stack].package_folder}",
            ]
        )
        if self.options.shared:
            tc.configure_args.extend(["--enable-shared", "--disable-static"])
        else:
            tc.configure_args.extend(["--disable-shared", "--enable-static"])
        tc.generate()

    @staticmethod
    def _first_dir(values, package_folder, fallback):
        if values:
            value = values[0]
            if os.path.isabs(value):
                return value
            return os.path.join(package_folder, value)
        return os.path.join(package_folder, fallback)

    def _gnustep_make_folder(self):
        return self.dependencies.build["gnustep-make"].package_folder

    def _gnustep_environment(self):
        make_folder = self._gnustep_make_folder()
        root = self.package_folder
        environment = Environment()
        environment.prepend_path("PATH", os.path.join(make_folder, "bin"))
        environment.define_path(
            "GNUSTEP_MAKEFILES",
            os.path.join(make_folder, "share", "GNUstep", "Makefiles"),
        )
        environment.define_path("GNUSTEP_SYSTEM_ROOT", root)
        environment.define_path(
            "GNUSTEP_CONFIG_FILE", os.path.join(root, "GNUstep.conf")
        )
        environment.define("GNUSTEP_INSTALLATION_DOMAIN", "SYSTEM")
        environment.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(root, "Library", "Libraries")
        )
        for dependency_name in ("libobjc2", "libffi", "c" + "url"):
            self._prepend_dependency_libdirs(
                environment,
                self.dependencies[dependency_name],
            )
        return environment

    def _make_args(self):
        shared = "yes" if self.options.shared else "no"
        return [
            "-j1",
            f"shared={shared}",
            "debug=no",
            "messages=yes",
            "GNUSTEP_INSTALLATION_DOMAIN=SYSTEM",
            f"GNUSTEP_SYSTEM_ROOT={self.package_folder}",
        ]

    @staticmethod
    def _ensure_executable(path):
        if not os.path.isfile(path):
            return
        mode = os.stat(path).st_mode
        os.chmod(path, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    @staticmethod
    def _script_shell():
        shell = os.environ.get("CONFIG_SHELL")
        if shell:
            return shell
        for candidate in ("/data/service/hnp/bin/bash", "/bin/bash", "/bin/sh"):
            if os.path.exists(candidate):
                return candidate
        return "sh"

    @staticmethod
    def _script_shebang():
        shell = os.environ.get("GNUSTEP_SCRIPT_SHELL")
        if shell:
            return shell
        for candidate in ("/storage/Users/currentUser/usr/local/bin/zsh", "/bin/bash", "/bin/sh"):
            if os.path.exists(candidate):
                return candidate
        return "sh"

    def _prepare_shell_script(self, path):
        if not os.path.isfile(path):
            return
        try:
            with open(path, "rb") as script:
                lines = script.read().splitlines(keepends=True)
        except OSError:
            return
        if not lines or not lines[0].startswith(b"#!"):
            return
        first_line = lines[0].decode("utf-8", "ignore").strip()
        for prefix in ("#!/bin/sh", "#! /bin/sh"):
            if first_line == prefix or first_line.startswith(prefix + " "):
                suffix = first_line[len(prefix):]
                lines[0] = f"#!{self._script_shebang()}{suffix}\n".encode("utf-8")
                with open(path, "wb") as script:
                    script.writelines(lines)
                break
        self._ensure_executable(path)

    def _prepend_dependency_libdirs(self, environment, dependency):
        libdirs = dependency.cpp_info.libdirs or ["lib"]
        for libdir in libdirs:
            path = libdir if os.path.isabs(libdir) else os.path.join(dependency.package_folder, libdir)
            environment.prepend_path("LD_LIBRARY_PATH", path)

    def _prepare_configure_scripts(self):
        script_names = {
            "config.guess",
            "config.sub",
            "configure",
            "depcomp",
            "install-sh",
            "missing",
            "mkinstalldirs",
        }
        for root in dict.fromkeys((self.source_folder, self.build_folder)):
            for dirpath, _, filenames in os.walk(root):
                for filename in filenames:
                    if filename in script_names:
                        self._prepare_shell_script(os.path.join(dirpath, filename))

    def _prepare_gnustep_make_scripts(self):
        make_folder = self._gnustep_make_folder()
        roots = (
            os.path.join(make_folder, "bin"),
            os.path.join(make_folder, "share", "GNUstep", "Makefiles"),
        )
        for root in roots:
            if not os.path.isdir(root):
                continue
            for dirpath, _, filenames in os.walk(root):
                for filename in filenames:
                    self._prepare_shell_script(os.path.join(dirpath, filename))

    def _patch_autoconf_tmp_umask(self):
        if str(self.settings.os) != "OHOS":
            return
        configure_script = os.path.join(self.source_folder, "configure")
        replace_in_file(self, configure_script, "umask 077 && mktemp -d", "umask 022 && mktemp -d", strict=False)
        replace_in_file(self, configure_script, "umask 077 && mkdir", "umask 022 && mkdir", strict=False)

    def _patch_nsdebug_include(self):
        nsdebug_source = os.path.join(self.source_folder, "Source", "NSDebug.m")
        replace_in_file(
            self,
            nsdebug_source,
            '#import "Foundation/NSValue.h"\n',
            '#import "Foundation/NSValue.h"\n#import "Foundation/NSDebug.h"\n',
            strict=False,
        )
        replace_in_file(
            self,
            nsdebug_source,
            "GSDebugAllocationTraceFunction traceFunction)",
            "NSObject *(*traceFunction)(id))",
            strict=False,
        )

    def _configure_with_shell(self, autotools):
        configure_script = os.path.join(self.source_folder, "configure")
        self.run(f'"{self._script_shell()}" "{configure_script}" {autotools._configure_args}')

    def _build_source_objects(self, autotools):
        with chdir(self, os.path.join(self.source_folder, "Source")):
            autotools.make(args=self._make_args())

    def _object_files(self):
        object_root = os.path.join(self.source_folder, "Source")
        objects = []
        for dirpath, _, filenames in os.walk(object_root):
            for filename in filenames:
                if filename.endswith(".o"):
                    objects.append(os.path.join(dirpath, filename))
        objects = sorted(set(objects))
        return objects

    @staticmethod
    def _c_compiler():
        for candidate in ("/data/service/hnp/bin/clang", "/usr/bin/clang", "/bin/clang"):
            if os.path.exists(candidate):
                return candidate
        compiler = os.environ.get("CC", "cc")
        return "clang" if compiler == "cc" else compiler

    def _link_base_library(self):
        objects = self._object_files()
        if not objects:
            raise ConanInvalidConfiguration("GNUstep Base object files were not produced")
        response_file = os.path.join(self.build_folder, "gnustep-base-objects.rsp")
        save(self, response_file, "\n".join(f'"{path}"' for path in objects))

        output_dir = os.path.join(self.source_folder, "Source", "obj")
        library_version = os.path.join(output_dir, "libgnustep-base.so.1.31")
        compiler = self._c_compiler()
        lib_flags = []
        for dependency_name in ("c" + "url", "libffi", "libobjc2"):
            dependency = self.dependencies[dependency_name]
            for libdir in dependency.cpp_info.libdirs or ["lib"]:
                path = libdir if os.path.isabs(libdir) else os.path.join(dependency.package_folder, libdir)
                lib_flags.append(f'-L"{path}"')
        self.run(
            f'"{compiler}" -shared -Wl,-soname,libgnustep-base.so.1.31 '
            f'-o "{library_version}" @"{response_file}" '
            f'{" ".join(lib_flags)} -lcurl -lffi -lobjc -pthread -ldl -lm -lz'
        )
        for link_name in ("libgnustep-base.so", "libgnustep-base.so.1"):
            shutil.copyfile(library_version, os.path.join(output_dir, link_name))

    def _copy_base_artifacts(self):
        copy(self, "*", src=os.path.join(self.source_folder, "Headers"), dst=os.path.join(self.package_folder, "Library", "Headers"))
        copy(self, "libgnustep-base.so*", src=os.path.join(self.source_folder, "Source", "obj"), dst=os.path.join(self.package_folder, "Library", "Libraries"), keep_path=False)

    def build(self):
        apply_conandata_patches(self)
        self._prepare_gnustep_make_scripts()
        self._patch_autoconf_tmp_umask()
        self._prepare_configure_scripts()
        self._patch_nsdebug_include()
        autotools = Autotools(self)
        with self._gnustep_environment().vars(self).apply():
            with chdir(self, self.source_folder):
                self._configure_with_shell(autotools)
            self._build_source_objects(autotools)
            self._link_base_library()
            if can_run(self):
                self.output.info(
                    "Upstream Tests are built by GNUmakefile; execution is left to explicit test_package/shadow CI."
                )
            else:
                self.output.info(
                    "cross-building: upstream GNUstep Base tests are not executed on the build host"
                )

    def package(self):
        self._prepare_gnustep_make_scripts()
        self._copy_base_artifacts()
        for license_file in ("COPYING", "COPYING.LIB", "COPYINGv3"):
            copy(
                self,
                license_file,
                src=self.source_folder,
                dst=os.path.join(self.package_folder, "licenses"),
                keep_path=False,
            )

    def package_info(self):
        self.cpp_info.includedirs = ["Library/Headers"]
        self.cpp_info.libdirs = ["Library/Libraries"]
        self.cpp_info.libs = ["gnustep-base"]
        self.cpp_info.requires = [
            "libobjc2::libobjc2",
            "libffi::libffi",
            "curl::curl",
        ]
        objc_flags = [
            "-fobjc-runtime=gcc",
            "-fblocks",
            "-fconstant-string-class=NSConstantString",
        ]
        self.cpp_info.cflags = objc_flags
        self.cpp_info.cxxflags = objc_flags
        self.cpp_info.exelinkflags = ["-fobjc-runtime=gcc", "-fblocks"]
        self.cpp_info.sharedlinkflags = ["-fobjc-runtime=gcc", "-fblocks"]
        self.cpp_info.system_libs = ["pthread", "dl", "m"]
        self.cpp_info.set_property("cmake_file_name", "gnustep-base")
        self.cpp_info.set_property("cmake_target_name", "gnustep-base::gnustep-base")
        self.cpp_info.set_property("pkg_config_name", "gnustep-base")

        root = self.package_folder
        self.buildenv_info.prepend_path("PATH", os.path.join(root, "Tools"))
        self.runenv_info.prepend_path("PATH", os.path.join(root, "Tools"))
        self.buildenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(root, "Library", "Libraries")
        )
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(root, "Library", "Libraries")
        )
        for dependency_name in ("libobjc2", "libffi", "c" + "url"):
            dependency = self.dependencies[dependency_name]
            if not dependency.package_folder:
                continue
            for libdir in dependency.cpp_info.libdirs or ["lib"]:
                path = libdir
                if not os.path.isabs(path):
                    path = os.path.join(dependency.package_folder, path)
                self.buildenv_info.prepend_path("LD_LIBRARY_PATH", path)
                self.runenv_info.prepend_path("LD_LIBRARY_PATH", path)
        self.buildenv_info.define_path("GNUSTEP_SYSTEM_ROOT", root)
        self.runenv_info.define_path("GNUSTEP_SYSTEM_ROOT", root)
