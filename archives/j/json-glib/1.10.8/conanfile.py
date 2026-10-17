#!/usr/bin/env python3
"""Conan recipe for json-glib 1.10.8."""

import configparser
import filecmp
import os
import re
import shutil
import stat
import sys
from contextlib import contextmanager

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.meson import Meson, MesonToolchain


class JsonGlibConan(ConanFile):
    name = "json-glib"
    version = "1.10.8"
    description = "JSON parser and generator library integrated with GLib"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/json-glib"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_upstream_tests": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "with_upstream_tests": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def requirements(self):
        self.requires(
            "glib/2.88.3", transitive_headers=True, transitive_libs=True
        )
        self.requires(
            "proxy-libintl/0.5",
            transitive_headers=True,
            transitive_libs=True,
        )

    def layout(self):
        self.folders.source = "."
        self.folders.build = "build"
        self.folders.generators = "build"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        self._ensure_tmpdir()
        PkgConfigDeps(self).generate()
        self._add_glib_tool_variables()

        tc = MesonToolchain(self)
        tc.project_options["default_library"] = (
            "shared" if self.options.shared else "static"
        )
        tc.project_options["wrap_mode"] = "nodownload"
        tc.project_options["introspection"] = "disabled"
        tc.project_options["documentation"] = "disabled"
        tc.project_options["man"] = False
        tc.project_options["nls"] = "disabled"
        tc.project_options["tests"] = bool(self.options.with_upstream_tests)
        tc.project_options["conformance"] = bool(self.options.with_upstream_tests)
        tc.project_options["installed_tests"] = False
        tc.generate()
        self._inject_archive_tools()

    def build(self):
        self._ensure_tmpdir()
        if not shutil.which("meson"):
            raise ConanInvalidConfiguration(
                "Meson is a required build tool and must be prepared by the worker"
            )
        apply_conandata_patches(self)
        meson = Meson(self)
        with self._host_tool_environment():
            self._configure_meson(meson)
            if self._windows_ohos_host():
                jobs = self.conf.get(
                    "tools.build:jobs", default=1, check_type=int
                )
                self._run_meson(
                    f'meson compile -C "{self._meson_path(self.build_folder)}" '
                    f"-j{jobs}"
                )
            else:
                meson.build()
            if self.options.with_upstream_tests and can_run(self):
                if self._windows_ohos_host():
                    self._run_meson(
                        f'meson test -v -C "{self._meson_path(self.build_folder)}"'
                    )
                else:
                    meson.test()

    def package(self):
        if self._windows_ohos_host():
            self._run_meson(
                f'meson install -C "{self._meson_path(self.build_folder)}" '
                f'--destdir "{self._meson_path(self.package_folder)}"'
            )
        else:
            Meson(self).install()
        if str(self.settings.os) == "OHOS" and self.options.shared:
            self._materialize_shared_library_aliases()

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "json-glib")
        self.cpp_info.set_property("pkg_config_name", "json-glib-1.0")
        self.cpp_info.bindirs = ["bin"]

        component = self.cpp_info.components["json-glib-1.0"]
        component.set_property("cmake_target_name", "json-glib::json-glib")
        component.set_property("pkg_config_name", "json-glib-1.0")
        component.libs = ["json-glib-1.0"]
        component.includedirs = ["include/json-glib-1.0"]
        component.libdirs = ["lib"]
        component.requires = [
            "glib::glib",
            "glib::gobject",
            "glib::gio",
            "proxy-libintl::proxy-libintl",
        ]
        if str(self.settings.os) in ("Linux", "OHOS") and self.options.shared:
            self.runenv_info.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
            )

    def _add_glib_tool_variables(self):
        bindir = self._glib_bindir()
        variables = {
            "glib_genmarshal": self._host_tool_path(
                os.path.join(bindir, "glib-genmarshal")
            ),
            "gobject_query": self._host_tool_path(
                os.path.join(bindir, "gobject-query")
            ),
            "glib_mkenums": self._host_tool_path(
                os.path.join(bindir, "glib-mkenums")
            ),
        }
        for pc_name in (
            "glib-2.0.pc",
            "gobject-2.0.pc",
            "gmodule-2.0.pc",
            "gthread-2.0.pc",
            "gio-2.0.pc",
        ):
            pc_path = os.path.join(self.generators_folder, pc_name)
            if not os.path.isfile(pc_path):
                continue
            with open(pc_path, encoding="utf-8") as source:
                pc_content = source.read()
            missing = [
                f"{key}={value}"
                for key, value in variables.items()
                if f"{key}=" not in pc_content
            ]
            if missing:
                pc_content = "\n".join(missing) + "\n" + pc_content
            if pc_name == "glib-2.0.pc":
                pc_content = self._add_pkg_config_requirement(pc_content, "intl")
            with open(pc_path, "w", encoding="utf-8", newline="\n") as target:
                target.write(pc_content)

    def _inject_archive_tools(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get("c", "")
        bindir = os.path.dirname(compiler) if os.path.sep in compiler else ""
        ar = executables.get("ar") or os.path.join(bindir, "llvm-ar")
        ranlib = executables.get("ranlib") or os.path.join(bindir, "llvm-ranlib")
        pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")
        if not pkg_config:
            raise ConanInvalidConfiguration(
                "pkg-config or pkgconf is required to resolve generated dependency modules"
            )

        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            machine_file = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(machine_file):
                continue
            parser = configparser.ConfigParser(interpolation=None)
            parser.optionxform = str
            parser.read(machine_file, encoding="utf-8")
            if not parser.has_section("binaries"):
                continue
            if ar and not parser.has_option("binaries", "ar"):
                parser.set("binaries", "ar", self._meson_string(ar))
            if ranlib and not parser.has_option("binaries", "ranlib"):
                parser.set("binaries", "ranlib", self._meson_string(ranlib))
            if not parser.has_option("binaries", "pkg-config"):
                parser.set(
                    "binaries", "pkg-config", self._meson_string(pkg_config)
                )
            with open(machine_file, "w", encoding="utf-8", newline="\n") as output:
                parser.write(output, space_around_delimiters=True)

    def _ensure_tmpdir(self):
        tmpdir = os.path.join(self.build_folder, ".tmp")
        os.makedirs(tmpdir, exist_ok=True)
        os.environ["TMPDIR"] = tmpdir

    def _windows_ohos_host(self):
        return os.name == "nt" and str(self.settings.os) == "OHOS"

    def _run_meson(self, command):
        self.run(command, env=None if self._windows_ohos_host() else "")

    def _host_tool_path(self, source):
        source = os.path.abspath(source)
        if not self._windows_ohos_host() or not os.path.isfile(source):
            return self._meson_path(source)
        with open(source, "rb") as script:
            if script.read(2) != b"#!":
                return self._meson_path(source)

        wrapper_dir = os.path.join(self.build_folder, ".host-tools")
        os.makedirs(wrapper_dir, exist_ok=True)
        wrapper = os.path.join(wrapper_dir, os.path.basename(source) + ".cmd")
        python = sys.executable.replace('"', '""')
        source_arg = source.replace('"', '""')
        with open(wrapper, "w", encoding="utf-8", newline="") as output:
            output.write(
                f'@"{python}" "{source_arg}" %*\r\n'
            )
        return self._meson_path(wrapper)

    def _materialize_shared_library_aliases(self):
        library_dir = os.path.join(self.package_folder, "lib")
        stem = "libjson-glib-1.0"
        pattern = re.compile(
            rf"^{re.escape(stem)}[.]so[.](?P<version>[0-9]+(?:[.][0-9]+)+)$"
        )
        sources = []
        if os.path.isdir(library_dir):
            for name in os.listdir(library_dir):
                path = os.path.join(library_dir, name)
                if (
                    pattern.fullmatch(name)
                    and os.path.isfile(path)
                    and not os.path.islink(path)
                ):
                    sources.append(path)
        if len(sources) != 1:
            raise ConanInvalidConfiguration(
                f"expected one versioned shared object for {stem!r}, "
                f"found {len(sources)}"
            )

        source = sources[0]
        source_mode = stat.S_IMODE(
            os.stat(source, follow_symlinks=False).st_mode
        )
        if os.name == "posix" and not source_mode & stat.S_IXUSR:
            raise ConanInvalidConfiguration(
                f"versioned shared object is not owner-executable: {source!r}"
            )
        version = pattern.fullmatch(os.path.basename(source)).group("version")
        aliases = (f"{stem}.so.{version.split('.', 1)[0]}", f"{stem}.so")

        alias_states = []
        for alias_name in aliases:
            alias = os.path.join(library_dir, alias_name)
            if not os.path.lexists(alias):
                alias_states.append((alias_name, alias, "missing"))
                continue
            if os.path.islink(alias):
                try:
                    same_source = os.path.samefile(alias, source)
                except OSError:
                    same_source = False
                if not same_source:
                    raise ConanInvalidConfiguration(
                        f"shared-library alias {alias!r} does not match {source!r}"
                    )
                alias_states.append((alias_name, alias, "link"))
                continue
            if (
                os.path.isfile(alias)
                and filecmp.cmp(alias, source, shallow=False)
                and stat.S_IMODE(
                    os.stat(alias, follow_symlinks=False).st_mode
                )
                == source_mode
            ):
                alias_states.append((alias_name, alias, "regular"))
                continue
            raise ConanInvalidConfiguration(
                f"shared-library alias {alias!r} does not match {source!r}"
            )

        for alias_name, alias, state in alias_states:
            if state == "regular":
                try:
                    if os.path.samefile(alias, source):
                        self.output.info(
                            f"preserved existing shared-library alias {alias_name}"
                        )
                        continue
                except OSError:
                    pass
                raise ConanInvalidConfiguration(
                    f"regular shared-library alias is not a hardlink: {alias!r}"
                )

            if state == "link":
                self.output.info(
                    f"preserved loader-preserving shared-library symlink {alias_name}"
                )
                continue

            # A missing alias is unexpected after Meson install.  Create a
            # relative symlink only after the complete alias inventory above
            # established that no conflicting path exists.
            try:
                target = os.path.relpath(source, os.path.dirname(alias))
                os.symlink(target, alias)
            except OSError as exc:
                raise ConanInvalidConfiguration(
                    f"cannot materialize missing shared-library alias {alias!r}"
                ) from exc
            self.output.info(
                f"materialized loader-preserving shared-library symlink {alias_name}"
            )
    def _configure_meson(self, meson):
        if not self._windows_ohos_host():
            meson.configure()
            return

        cross_file = os.path.join(
            self.generators_folder, MesonToolchain.cross_filename
        )
        if not os.path.isfile(cross_file):
            raise ConanInvalidConfiguration("Meson cross file was not generated")

        machine_args = [
            '--cross-file "{}"'.format(self._meson_path(cross_file))
        ]
        native_file = os.path.join(
            self.generators_folder, MesonToolchain.native_filename
        )
        if os.path.isfile(native_file):
            machine_args.append(
                '--native-file "{}"'.format(self._meson_path(native_file))
            )

        command = 'meson setup {} "{}" "{}" --prefix=/'.format(
            " ".join(machine_args),
            self._meson_path(self.build_folder),
            self._meson_path(self.source_folder),
        )
        self.output.info(f"Meson configure cmd: {command}")
        self._run_meson(command)

    def _glib_bindir(self):
        glib_pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if not os.path.isfile(glib_pc):
            raise ConanInvalidConfiguration(
                "PkgConfigDeps did not generate glib-2.0.pc"
            )

        with open(glib_pc, encoding="utf-8") as source:
            content = source.read()
        for line in content.splitlines():
            if line.startswith("prefix="):
                prefix = line.split("=", 1)[1].strip().strip("\"'")
                if prefix:
                    return os.path.join(prefix, "bin")
        raise ConanInvalidConfiguration("glib-2.0.pc has no prefix")

    @contextmanager
    def _host_tool_environment(self):
        if str(self.settings.os) != "OHOS":
            yield
            return
        ld_library_path = os.environ.pop("LD_LIBRARY_PATH", None)
        path = os.environ.get("PATH")
        os.environ["PATH"] = os.pathsep.join(
            value for value in (self._glib_bindir(), path) if value
        )
        try:
            yield
        finally:
            if path is None:
                os.environ.pop("PATH", None)
            else:
                os.environ["PATH"] = path
            if ld_library_path is not None:
                os.environ["LD_LIBRARY_PATH"] = ld_library_path

    @staticmethod
    def _meson_string(value):
        return "'{}'".format(str(value).replace("\\", "/").replace("'", "\\'"))

    @staticmethod
    def _meson_path(value):
        return str(value).replace("\\", "/").replace('"', '\\"')

    @staticmethod
    def _add_pkg_config_requirement(content, requirement):
        lines = content.splitlines()
        for index, line in enumerate(lines):
            if not line.startswith("Requires:"):
                continue
            requirements = line.split(":", 1)[1].split()
            if requirement not in requirements:
                requirements.append(requirement)
                lines[index] = "Requires: " + " ".join(requirements)
            return "\n".join(lines) + "\n"
        lines.append(f"Requires: {requirement}")
        return "\n".join(lines) + "\n"
