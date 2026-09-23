#!/usr/bin/env python3
"""Conan recipe for GNUstep GUI 0.32.0."""

import glob
import os
import shlex
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
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class GnustepGuiConan(ConanFile):
    name = "gnustep-gui"
    version = "0.32.0"
    description = "GNUstep AppKit/GUI library"
    license = "LGPL-2.1-or-later AND GPL-3.0-or-later"
    homepage = "https://gnustep.github.io/"
    url = "https://github.com/gnustep/libs-gui"
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
                f"gnustep-gui is prepared for Linux/OHOS targets, got {self.settings.os}"
            )
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("gnustep-base/1.31.1", transitive_headers=True, transitive_libs=True)
        self.requires("libtiff/4.7.2", transitive_headers=True, transitive_libs=True)
        self.requires("libjpeg/10", transitive_headers=True, transitive_libs=True)
        self.requires("libpng/1.6.58", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        self.tool_requires("gnustep-make/2.9.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"])

    def generate(self):
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            [
                "--without-x",
                "--disable-ungif",
                "--disable-icu",
                "--disable-aspell",
                "--disable-sound",
                "--disable-speech",
                "--disable-speech-recognizer",
                "--disable-cups",
            ]
        )
        tiff = self.dependencies["libtiff"]
        jpeg = self.dependencies["libjpeg"]
        tc.configure_args.extend(
            [
                f"--with-tiff-include={self._first_dir(tiff.cpp_info.includedirs, tiff.package_folder, 'include')}",
                f"--with-tiff-library={self._first_dir(tiff.cpp_info.libdirs, tiff.package_folder, 'lib')}",
                f"--with-jpeg-include={self._first_dir(jpeg.cpp_info.includedirs, jpeg.package_folder, 'include')}",
                f"--with-jpeg-library={self._first_dir(jpeg.cpp_info.libdirs, jpeg.package_folder, 'lib')}",
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

    @staticmethod
    def _runtime_dependency_names():
        return ("gnustep-base", "libtiff", "libjpeg", "libpng", "libobjc2", "libffi", "c" + "url")

    def _prepare_gnustep_install_dirs(self, root):
        headers_root = os.path.join(root, "Library", "Headers")
        libraries_root = os.path.join(root, "Library", "Libraries")
        resource_root = os.path.join(
            libraries_root,
            "gnustep-gui",
            "Versions",
            ".".join(self.version.split(".")[:2]),
            "Resources",
        )
        for path in (
            os.path.join(headers_root, "AppKit"),
            os.path.join(headers_root, "Cocoa"),
            os.path.join(headers_root, "GNUstepGUI"),
            os.path.join(libraries_root, "pkgconfig"),
            resource_root,
        ):
            os.makedirs(path, exist_ok=True)

    @staticmethod
    def _build_subprojects():
        return (
            "Source",
            "Images",
            "Sounds",
            "Model",
            "Tools",
            "Panels",
            "PrinterTypes",
            "TextConverters",
            "ColorPickers",
            "KeyBindings",
            "Resources",
            "Printing",
            "Themes",
        )

    def _gnustep_environment(self):
        make_folder = self._gnustep_make_folder()
        base = self.dependencies["gnustep-base"]
        root = self.package_folder
        package_libs = os.path.join(root, "Library", "Libraries")
        base_headers = self._first_dir(base.cpp_info.includedirs, base.package_folder, "Library/Headers")
        base_libs = self._first_dir(base.cpp_info.libdirs, base.package_folder, "Library/Libraries")

        environment = Environment()
        environment.prepend_path("PATH", os.path.join(make_folder, "bin"))
        environment.prepend_path("PATH", os.path.join(base.package_folder, "Tools"))
        environment.define_path(
            "GNUSTEP_MAKEFILES",
            os.path.join(make_folder, "share", "GNUstep", "Makefiles"),
        )
        environment.define_path("GNUSTEP_HEADERS", os.path.join(root, "Library", "Headers"))
        environment.define_path("GNUSTEP_LIBRARY", os.path.join(root, "Library"))
        environment.define_path("GNUSTEP_SYSTEM_LIBRARY", os.path.join(root, "Library"))
        environment.define_path("GNUSTEP_SYSTEM_ROOT", root)
        environment.define_path("GNUSTEP_SYSTEM_HEADERS", os.path.join(root, "Library", "Headers"))
        environment.define_path("GNUSTEP_SYSTEM_LIBRARIES", package_libs)
        environment.define_path(
            "GNUSTEP_CONFIG_FILE", os.path.join(root, "GNUstep.conf")
        )
        environment.define("GNUSTEP_INSTALLATION_DOMAIN", "SYSTEM")
        self._prepare_gnustep_install_dirs(root)
        environment.prepend_path("LD_LIBRARY_PATH", package_libs)
        environment.prepend_path("LD_LIBRARY_PATH", base_libs)
        environment.append("LDFLAGS", f"-L{package_libs}")
        environment.append("ADDITIONAL_LIB_DIRS", f"-L{package_libs}")
        environment.append("CPPFLAGS", f"-I{base_headers}")
        environment.append("ADDITIONAL_INCLUDE_DIRS", f"-I{base_headers}")
        environment.append("ADDITIONAL_LIB_DIRS", f"-L{base_libs}")
        self._append_dependency_tool_libs(environment, base, ("gnustep-base",))
        if "libobjc2" in self.dependencies:
            self._append_dependency_tool_libs(
                environment,
                self.dependencies["libobjc2"],
                ("objc",),
            )
        for dependency_name in self._runtime_dependency_names():
            if dependency_name in self.dependencies:
                dependency = self.dependencies[dependency_name]
                if dependency_name != "gnustep-base":
                    self._append_dependency_includedirs(environment, dependency)
                    self._append_dependency_libdirs(environment, dependency)
                self._prepend_dependency_libdirs(
                    environment,
                    dependency,
                )
        environment.append("LDFLAGS", f"-L{base_libs}")
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
        if not dependency.package_folder:
            return
        libdirs = dependency.cpp_info.libdirs or ["lib"]
        for libdir in libdirs:
            path = libdir if os.path.isabs(libdir) else os.path.join(dependency.package_folder, libdir)
            environment.prepend_path("LD_LIBRARY_PATH", path)

    def _append_dependency_includedirs(self, environment, dependency):
        if not dependency.package_folder:
            return
        includedirs = dependency.cpp_info.includedirs or ["include"]
        for includedir in includedirs:
            path = includedir if os.path.isabs(includedir) else os.path.join(dependency.package_folder, includedir)
            environment.append("CPPFLAGS", f"-I{path}")
            environment.append("ADDITIONAL_INCLUDE_DIRS", f"-I{path}")

    def _append_dependency_libdirs(self, environment, dependency):
        if not dependency.package_folder:
            return
        libdirs = dependency.cpp_info.libdirs or ["lib"]
        for libdir in libdirs:
            path = libdir if os.path.isabs(libdir) else os.path.join(dependency.package_folder, libdir)
            environment.append("LDFLAGS", f"-L{path}")
            environment.append("ADDITIONAL_LIB_DIRS", f"-L{path}")

    def _append_dependency_tool_libs(self, environment, dependency, fallback_libs):
        libs = dependency.cpp_info.libs or list(fallback_libs)
        for lib in libs:
            if lib.startswith(("-l", "-Wl,")) or os.path.isabs(lib):
                environment.append("ADDITIONAL_TOOL_LIBS", lib)
            else:
                environment.append("ADDITIONAL_TOOL_LIBS", f"-l{lib}")

    def _link_or_copy(self, target, link_name):
        if os.path.abspath(target) == os.path.abspath(link_name):
            return
        if os.path.lexists(link_name):
            return
        try:
            if os.path.dirname(os.path.abspath(target)) == os.path.dirname(os.path.abspath(link_name)):
                symlink_target = os.path.basename(target)
                os.symlink(symlink_target, link_name)
            else:
                shutil.copy2(target, link_name)
        except (AttributeError, NotImplementedError, OSError):
            shutil.copy2(target, link_name)

    def _ensure_gnustep_gui_shared_links(self, root, extra_link_dirs=None):
        if not os.path.isdir(root):
            return []
        targets = []
        for dirpath, _, filenames in os.walk(root):
            versioned_files = sorted(
                filename
                for filename in filenames
                if self._gnustep_gui_shared_link_names(filename)
            )
            if not versioned_files:
                continue
            target = os.path.join(dirpath, versioned_files[-1])
            targets.append(target)
            for link_name in self._gnustep_gui_shared_link_names(versioned_files[-1]):
                self._link_or_copy(target, os.path.join(dirpath, link_name))
        if not targets or not extra_link_dirs:
            return targets
        target = sorted(targets)[-1]
        link_names = self._gnustep_gui_shared_link_names(os.path.basename(target))
        for link_dir in extra_link_dirs:
            os.makedirs(link_dir, exist_ok=True)
            for link_name in link_names:
                self._link_or_copy(target, os.path.join(link_dir, link_name))
        return targets

    def _stage_gnustep_gui_shared_links(self):
        link_dirs = (
            os.path.join(self.source_folder, "Source", "obj"),
            os.path.join(self.build_folder, "Source", "obj"),
            os.path.join(self.package_folder, "Library", "Libraries"),
        )
        targets = []
        for root in dict.fromkeys((self.source_folder, self.build_folder, self.package_folder)):
            targets.extend(self._ensure_gnustep_gui_shared_links(root, link_dirs))
        if targets:
            self.output.info("GNUstep GUI shared library candidates staged for tool links:")
            for target in sorted(set(targets)):
                self.output.info(f"  {target}")
        else:
            debug_hits = []
            roots = dict.fromkeys((self.source_folder, self.build_folder, self.package_folder))
            for root in roots:
                if len(debug_hits) >= 5 or not os.path.isdir(root):
                    continue
                for dirpath, _, filenames in os.walk(root):
                    matches = sorted(
                        filename
                        for filename in filenames
                        if filename.startswith("libgnustep-gui")
                    )
                    if matches:
                        debug_hits.append(f"{dirpath}: {', '.join(matches[:6])}")
                    if len(debug_hits) >= 5:
                        break
            if debug_hits:
                self.output.warning(
                    "No libgnustep-gui shared library candidate found after Source build; nearby hits:"
                )
                for hit in debug_hits:
                    self.output.warning(f"  {hit}")
            else:
                self.output.warning("No libgnustep-gui shared library candidate found after Source build")

    def _preferred_gnustep_gui_tool_lib(self, targets):
        if not targets:
            return None
        normalized_targets = sorted({os.path.abspath(target) for target in targets})
        preferred_roots = (
            os.path.abspath(os.path.join(self.source_folder, "Source", "obj")),
            os.path.abspath(os.path.join(self.build_folder, "Source", "obj")),
            os.path.abspath(os.path.join(self.package_folder, "Library", "Libraries")),
        )
        for preferred_root in preferred_roots:
            for target in normalized_targets:
                if os.path.dirname(target) == preferred_root:
                    return target
        return normalized_targets[0]

    @staticmethod
    def _gnustep_gui_shared_link_names(filename):
        if filename in {"libgnustep-gui", "libgnustep-gui.so"}:
            return ["libgnustep-gui.so", "libgnustep-gui"]
        if not filename.startswith("libgnustep-gui."):
            return []
        if filename.startswith("libgnustep-gui.so."):
            version = filename[len("libgnustep-gui.so.") :]
            major = version.split(".", 1)[0]
            names = [
                "libgnustep-gui.so",
                f"libgnustep-gui.{version}.so",
                f"libgnustep-gui.{version}",
            ]
            if major:
                names.append(f"libgnustep-gui.so.{major}")
            return names
        if filename.startswith("libgnustep-gui.") and filename.endswith(".so"):
            version = filename[len("libgnustep-gui.") : -len(".so")]
            if not version:
                return []
            parts = version.split(".")
            names = [
                "libgnustep-gui.so",
                f"libgnustep-gui.so.{version}",
                f"libgnustep-gui.{version}",
            ]
            if parts[0]:
                names.append(f"libgnustep-gui.{parts[0]}.so")
            if len(parts) > 1:
                names.append(f"libgnustep-gui.{parts[0]}.{parts[1]}.so")
            return names
        version = filename[len("libgnustep-gui.") :]
        if not version or version == "so":
            return []
        if version.endswith(".so"):
            version = version[: -len(".so")]
        if not version:
            return []
        parts = version.split(".")
        names = [
            "libgnustep-gui.so",
            f"libgnustep-gui.so.{version}",
            f"libgnustep-gui.{version}.so",
            f"libgnustep-gui.{version}",
        ]
        if parts[0]:
            names.append(f"libgnustep-gui.so.{parts[0]}")
            names.append(f"libgnustep-gui.{parts[0]}.so")
        if len(parts) > 1:
            names.append(f"libgnustep-gui.so.{parts[0]}.{parts[1]}")
            names.append(f"libgnustep-gui.{parts[0]}.{parts[1]}.so")
        return names

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

    def _patch_tools_link_rules(self):
        tools_preamble = os.path.join(self.source_folder, "Tools", "GNUmakefile.preamble")
        replace_in_file(
            self,
            tools_preamble,
            """# Additional libraries when linking tools
gpbs_TOOL_LIBS += -lgnustep-gui $(SYSTEM_LIBS)
set_show_service_TOOL_LIBS += -lgnustep-gui $(SYSTEM_LIBS)
gopen_TOOL_LIBS += -lgnustep-gui $(SYSTEM_LIBS)
gcloseall_TOOL_LIBS += -lgnustep-gui $(SYSTEM_LIBS)
""",
            """# Additional libraries when linking tools
ifndef GNUSTEP_GUI_TOOL_LIBS
  GNUSTEP_GUI_TOOL_LIBS = $(firstword $(wildcard $(GNUSTEP_SYSTEM_LIBRARIES)/libgnustep-gui.so.* $(GNUSTEP_SYSTEM_LIBRARIES)/libgnustep-gui.*.so $(GNUSTEP_SYSTEM_LIBRARIES)/libgnustep-gui.[0-9]* $(GNUSTEP_SYSTEM_LIBRARIES)/libgnustep-gui.so $(GNUSTEP_SYSTEM_LIBRARIES)/libgnustep-gui ../Source/$(GNUSTEP_OBJ_DIR)/libgnustep-gui.so.* ../Source/$(GNUSTEP_OBJ_DIR)/libgnustep-gui.*.so ../Source/$(GNUSTEP_OBJ_DIR)/libgnustep-gui.[0-9]* ../Source/$(GNUSTEP_OBJ_DIR)/libgnustep-gui.so ../Source/$(GNUSTEP_OBJ_DIR)/libgnustep-gui ../Library/Libraries/libgnustep-gui.so.* ../Library/Libraries/libgnustep-gui.*.so ../Library/Libraries/libgnustep-gui.[0-9]* ../Library/Libraries/libgnustep-gui.so ../Library/Libraries/libgnustep-gui) -lgnustep-gui)
endif
GNUSTEP_GUI_TOOL_SYSTEM_LIBS = $(filter-out -lgnustep-gui,$(SYSTEM_LIBS))

gpbs_TOOL_LIBS += $(GNUSTEP_GUI_TOOL_LIBS) $(GNUSTEP_GUI_TOOL_SYSTEM_LIBS)
set_show_service_TOOL_LIBS += $(GNUSTEP_GUI_TOOL_LIBS) $(GNUSTEP_GUI_TOOL_SYSTEM_LIBS)
gopen_TOOL_LIBS += $(GNUSTEP_GUI_TOOL_LIBS) $(GNUSTEP_GUI_TOOL_SYSTEM_LIBS)
gcloseall_TOOL_LIBS += $(GNUSTEP_GUI_TOOL_LIBS) $(GNUSTEP_GUI_TOOL_SYSTEM_LIBS)
""",
            strict=False,
        )

    def _tool_gnustep_gui_lib_path(self):
        search_roots = (
            os.path.join(self.source_folder, "Source", "obj"),
            os.path.join(self.build_folder, "Source", "obj"),
            os.path.join(self.package_folder, "Library", "Libraries"),
        )
        patterns = (
            "libgnustep-gui.so",
            "libgnustep-gui",
            "libgnustep-gui.so.*",
            "libgnustep-gui.*.so",
            "libgnustep-gui.[0-9]*",
        )
        for root in search_roots:
            for pattern in patterns:
                matches = sorted(
                    path
                    for path in glob.glob(os.path.join(root, "**", pattern), recursive=True)
                    if os.path.isfile(path) or os.path.islink(path)
                )
                if matches:
                    return matches[0]
        return os.path.join(self.package_folder, "Library", "Libraries", "libgnustep-gui.so")

    def _configure_args(self, autotools):
        args = str(autotools._configure_args)
        if str(self.settings.os) != "OHOS":
            return args

        arch = str(self.settings.arch)
        cpu = {
            "armv8": "aarch64",
            "armv8.2": "aarch64",
            "armv8.3": "aarch64",
        }.get(arch, arch)
        explicit_triplets = [
            f"--build={cpu}-unknown-linux-gnu",
            f"--host={cpu}-unknown-linux-ohos",
            f"--target={cpu}-unknown-linux-ohos",
        ]
        filtered_args = [
            arg
            for arg in shlex.split(args)
            if not arg.startswith(("--build=", "--host=", "--target=", "ac_cv_prog_cc_works="))
        ]
        return " ".join(
            shlex.quote(arg)
            for arg in explicit_triplets + filtered_args + ["ac_cv_prog_cc_works=yes"]
        )

    def _configure_with_shell(self, autotools):
        configure_script = os.path.join(self.source_folder, "configure")
        self.run(f'"{self._script_shell()}" "{configure_script}" {self._configure_args(autotools)}')

    def _make_subproject(self, autotools, subproject, target=None, make_args=None):
        subproject_dir = os.path.join(self.source_folder, subproject)
        if not os.path.isdir(subproject_dir):
            return
        args = make_args or self._make_args()
        with chdir(self, subproject_dir):
            if target:
                autotools.make(target=target, args=args)
            else:
                autotools.make(args=args)

    def build(self):
        apply_conandata_patches(self)
        self._prepare_gnustep_make_scripts()
        self._patch_autoconf_tmp_umask()
        self._patch_tools_link_rules()
        self._prepare_configure_scripts()
        autotools = Autotools(self)
        tool_make_args = self._make_args()
        with self._gnustep_environment().vars(self).apply():
            with chdir(self, self.source_folder):
                self._configure_with_shell(autotools)
            for subproject in self._build_subprojects():
                if subproject == "Source":
                    self._make_subproject(autotools, subproject)
                    self._stage_gnustep_gui_shared_links()
                    self._make_subproject(autotools, subproject, target="install")
                    self._stage_gnustep_gui_shared_links()
                    tool_make_args = self._make_args() + [
                        f"GNUSTEP_GUI_TOOL_LIBS={self._tool_gnustep_gui_lib_path()}"
                    ]
                elif subproject == "Tools":
                    self._make_subproject(autotools, subproject, make_args=tool_make_args)
                else:
                    self._make_subproject(autotools, subproject)
            if can_run(self):
                self.output.info(
                    "Upstream GUI tests are discovered under Tests; execution is left to explicit test_package/shadow CI."
                )
            else:
                self.output.info(
                    "cross-building: upstream GNUstep GUI tests are not executed on the build host"
                )

    def package(self):
        self._prepare_gnustep_make_scripts()
        autotools = Autotools(self)
        with self._gnustep_environment().vars(self).apply():
            for subproject in self._build_subprojects():
                self._make_subproject(autotools, subproject, target="install")
                if subproject == "Source":
                    self._stage_gnustep_gui_shared_links()
        self._ensure_gnustep_gui_shared_links(
            os.path.join(self.package_folder, "Library", "Libraries")
        )
        for license_file in ("COPYING", "COPYING.LIB"):
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
        self.cpp_info.libs = ["gnustep-gui"]
        self.cpp_info.requires = [
            "gnustep-base::gnustep-base",
            "libtiff::libtiff",
            "libjpeg::libjpeg",
            "libpng::libpng",
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
        self.cpp_info.set_property("cmake_file_name", "gnustep-gui")
        self.cpp_info.set_property("cmake_target_name", "gnustep-gui::gnustep-gui")
        self.cpp_info.set_property("pkg_config_name", "gnustep-gui")

        root = self.package_folder
        self.buildenv_info.prepend_path("PATH", os.path.join(root, "Tools"))
        self.runenv_info.prepend_path("PATH", os.path.join(root, "Tools"))
        self.buildenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(root, "Library", "Libraries")
        )
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(root, "Library", "Libraries")
        )
        for dependency_name in self._runtime_dependency_names():
            if dependency_name in self.dependencies:
                dependency = self.dependencies[dependency_name]
                self._prepend_dependency_libdirs(self.buildenv_info, dependency)
                self._prepend_dependency_libdirs(self.runenv_info, dependency)
        self.buildenv_info.define_path("GNUSTEP_GUI_ROOT", root)
        self.runenv_info.define_path("GNUSTEP_GUI_ROOT", root)
