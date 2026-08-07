#!/usr/bin/env python3
"""Conan recipe for libxcb 1.16."""

import json
import os
import re
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.gnu.get_gnu_triplet import _get_gnu_triplet
from conan.tools.layout import basic_layout


EXTENSION_LIBS = (
    "composite",
    "damage",
    "dbe",
    "dpms",
    "dri2",
    "dri3",
    "glx",
    "present",
    "randr",
    "record",
    "render",
    "res",
    "screensaver",
    "shape",
    "shm",
    "sync",
    "xf86dri",
    "xfixes",
    "xinerama",
    "xinput",
    "xkb",
    "xtest",
    "xv",
    "xvmc",
)


class LibxcbConan(ConanFile):
    name = "libxcb"
    version = "1.16"
    description = "X protocol C-language binding library"
    license = "MIT"
    homepage = "https://xcb.freedesktop.org/"
    url = "https://gitlab.freedesktop.org/xorg/lib/libxcb"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libxcb supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        self.requires("xorgproto/2025.1", transitive_headers=True)
        self.requires("libxau/1.0.11")
        self.requires("libxdmcp/1.1.5")

    def build_requirements(self):
        self.tool_requires("xcb-proto/1.17.0")
        self.test_requires("check/0.15.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"][str(self.version)], strip_root=True)

    def generate(self):
        pkg_config = PkgConfigDeps(self)
        pkg_config.generate()
        VirtualBuildEnv(self).generate()

        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--disable-devel-docs")
        tc.configure_args.append("--with-doxygen=no")
        if str(self.settings.os) == "OHOS":
            # The project OHOS Conan profile maps to a linux-ohos GNU triplet.
            # Upstream's 2023 config.sub needs the companion patch in this
            # recipe to accept it.
            build_triplet = self._gnu_triplet(self.settings_build)
            host_triplet = self._gnu_triplet(self.settings)
            tc.configure_args.append(f"--build={build_triplet}")
            tc.configure_args.append(f"--host={host_triplet}")
        if self.options.shared:
            tc.configure_args.append("--enable-shared")
            tc.configure_args.append("--disable-static")
        else:
            tc.configure_args.append("--disable-shared")
            tc.configure_args.append("--enable-static")
        if str(self.settings.os) == "OHOS":
            tc.extra_cflags.append("-Qunused-arguments")
            tc.extra_cflags.append("-Wno-error=unused-command-line-argument")
            self._add_dependency_flags(tc)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        build_env = Environment()
        build_env.define("TMPDIR", tmpdir)
        build_env.define("TMP", tmpdir)
        build_env.define("TEMP", tmpdir)
        build_env.define("TMPPREFIX", os.path.join(tmpdir, "zsh"))
        if str(self.settings.os) == "OHOS":
            self._prepend_ohos_tool_paths()
            build_env.define("CK_FORK", "no")
            shell = self._resolve_shell()
            self._patch_conan_env_scripts(shell)
            build_env.define("CONFIG_SHELL", shell)
            build_env.define("SHELL", shell)
            for variable, tool in {
                "LD": "ld.lld",
                "AR": "llvm-ar",
                "RANLIB": "llvm-ranlib",
                "NM": "llvm-nm",
                "STRIP": "llvm-strip",
            }.items():
                build_env.define(variable, self._resolve_ohos_tool(tool))
            build_env.define("PKG_CONFIG", self._write_pkg_config_shim())
            self._add_runtime_library_paths(build_env)

        autotools = Autotools(self)
        with VirtualBuildEnv(self).vars().apply(), build_env.vars(self).apply():
            autotools.configure()
            autotools.make()
            if can_run(self):
                autotools.make(target="check")
            else:
                self.output.warning(
                    "Skipping upstream make check because the target cannot run on this host."
                )

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        self._patch_libtool_libdir()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libxcb")
        self.cpp_info.set_property("cmake_target_name", "libxcb::libxcb")
        self.cpp_info.set_property("pkg_config_name", "xcb")

        core = self.cpp_info.components["xcb"]
        core.libs = ["xcb"]
        core.requires = [
            "libxau::libxau",
            "libxdmcp::libxdmcp",
            "xorgproto::xorgproto",
        ]
        core.set_property("cmake_target_name", "libxcb::xcb")
        core.set_property("pkg_config_name", "xcb")
        if str(self.settings.os) in ("Linux", "OHOS"):
            core.system_libs = ["pthread"]

        for extension in EXTENSION_LIBS:
            component = self.cpp_info.components[extension]
            component.libs = [f"xcb-{extension}"]
            component.requires = ["xcb"]
            component.set_property("cmake_target_name", f"libxcb::{extension}")
            component.set_property("pkg_config_name", f"xcb-{extension}")

    def _patch_libtool_libdir(self):
        lib_dir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(lib_dir):
            return
        for entry in os.listdir(lib_dir):
            if not entry.endswith(".la"):
                continue
            la_path = os.path.join(lib_dir, entry)
            with open(la_path, "r", encoding="utf-8") as handle:
                content = handle.read()
            new_content = re.sub(
                r"^libdir='.*'$",
                f"libdir='{lib_dir}'",
                content,
                flags=re.MULTILINE,
            )
            if new_content != content:
                with open(la_path, "w", encoding="utf-8") as handle:
                    handle.write(new_content)

    def _resolve_ohos_tool(self, tool):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        for compiler in ("c", "cpp"):
            compiler_command = compilers.get(compiler)
            if not compiler_command:
                continue
            compiler_path = str(compiler_command).split()[0].strip("\"'")
            candidate = os.path.join(os.path.dirname(compiler_path), tool)
            if os.path.exists(candidate):
                return candidate
        return shutil.which(tool) or tool

    def _gnu_triplet(self, settings):
        compiler = settings.get_safe("compiler")
        triplet = _get_gnu_triplet(
            str(settings.os),
            str(settings.arch),
            str(compiler) if compiler else None,
        )
        if str(settings.os) == "OHOS":
            system = triplet["system"]
            if not system.startswith("linux-"):
                system = f"linux-{system}"
            return f"{triplet['machine']}-unknown-{system}"
        return triplet["triplet"]

    def _resolve_shell(self):
        for candidate in (
            os.environ.get("CONFIG_SHELL"),
            os.environ.get("SHELL"),
            shutil.which("bash"),
            shutil.which("sh"),
            "/bin/sh",
            "/system/bin/sh",
        ):
            if not candidate:
                continue
            if os.path.exists(candidate) and os.access(candidate, os.X_OK):
                return candidate
        return "sh"

    def _patch_conan_env_scripts(self, shell):
        generators_folder = self.generators_folder
        if not generators_folder or not os.path.isdir(generators_folder):
            return

        bootstrap_paths = self._ohos_tool_paths()
        if not bootstrap_paths:
            return
        bootstrap = ":".join(bootstrap_paths)
        marker = "# libxcb OHOS PATH bootstrap"
        for entry in os.listdir(generators_folder):
            if not entry.endswith(".sh") or entry.startswith("deactivate_"):
                continue
            script_path = os.path.join(generators_folder, entry)
            with open(script_path, "r", encoding="utf-8") as handle:
                content = handle.read()

            if marker not in content:
                content = f'{marker}\nexport PATH="{bootstrap}:${{PATH}}"\n' + content
            if shell:
                content = re.sub(
                    r'^export SHELL="[^"]*"$',
                    f'export SHELL="{shell}"',
                    content,
                    flags=re.MULTILINE,
                )
                content = re.sub(
                    r'^export CONFIG_SHELL="[^"]*"$',
                    f'export CONFIG_SHELL="{shell}"',
                    content,
                    flags=re.MULTILINE,
                )
            content = self._patch_missing_compiler_exports(content)

            with open(script_path, "w", encoding="utf-8") as handle:
                handle.write(content)

    def _patch_missing_compiler_exports(self, content):
        for variable, replacement in {
            "CC": self._fallback_compiler("c", "clang"),
            "CXX": self._fallback_compiler("cpp", "clang++"),
        }.items():
            if replacement:
                content = re.sub(
                    rf'^export {variable}="[^"]*"$',
                    f'export {variable}="{replacement}"',
                    content,
                    flags=re.MULTILINE,
                )
        return content

    def _fallback_compiler(self, compiler_key, fallback_name):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        configured = compilers.get(compiler_key)
        if configured:
            configured_path = str(configured).split()[0].strip("\"'")
            if os.path.exists(configured_path) and os.access(configured_path, os.X_OK):
                return None
        fallback = shutil.which(fallback_name)
        if fallback and os.path.exists(fallback) and os.access(fallback, os.X_OK):
            return fallback
        return None

    def _add_dependency_flags(self, toolchain):
        for name in ("xorgproto", "libxau", "libxdmcp", "check"):
            package_folder = self._dependency_folder(name)
            if not package_folder:
                continue
            include_dir = os.path.join(package_folder, "include")
            lib_dir = os.path.join(package_folder, "lib")
            if os.path.isdir(include_dir):
                toolchain.extra_cflags.append(f"-I{include_dir}")
            if os.path.isdir(lib_dir):
                toolchain.extra_ldflags.append(f"-L{lib_dir}")

    def _add_runtime_library_paths(self, build_env):
        for name in ("libxau", "libxdmcp", "check"):
            package_folder = self._dependency_folder(name)
            if not package_folder:
                continue
            lib_dir = os.path.join(package_folder, "lib")
            if os.path.isdir(lib_dir):
                build_env.prepend_path("LD_LIBRARY_PATH", lib_dir)

    def _prepend_ohos_tool_paths(self):
        tool_paths = self._ohos_tool_paths()
        existing = os.environ.get("PATH", "")
        for path in reversed(tool_paths):
            if os.path.isdir(path):
                if path not in existing.split(os.pathsep):
                    existing = path + (os.pathsep + existing if existing else "")
        os.environ["PATH"] = existing

    def _ohos_tool_paths(self):
        return [
            path
            for path in (
                "/data/service/hnp/bin",
                os.path.join(os.path.expanduser("~"), "usr", "local", "bin"),
                "/bin",
                "/usr/bin",
            )
            if os.path.isdir(path)
        ]

    def _write_pkg_config_shim(self):
        modules = self._pkg_config_modules()
        shim = os.path.join(self.build_folder, "pkg-config-libxcb.py")
        with open(shim, "w", encoding="utf-8") as handle:
            handle.write(
                "#!/usr/bin/env python3\n"
                "import re\n"
                "import sys\n"
                f"MODULES = {json.dumps(modules, sort_keys=True)}\n"
                "def requested_modules(args):\n"
                "    found = []\n"
                "    for arg in args:\n"
                "        if arg.startswith('-'):\n"
                "            continue\n"
                "        for token in re.split(r'\\s+|>=|<=|=|>|<', arg):\n"
                "            if token in MODULES and token not in found:\n"
                "                found.append(token)\n"
                "    return found\n"
                "def main():\n"
                "    args = sys.argv[1:]\n"
                "    if any(arg.startswith('--atleast-pkgconfig-version') for arg in args):\n"
                "        return 0\n"
                "    modules = requested_modules(args)\n"
                "    if not modules:\n"
                "        return 0\n"
                "    unknown = [module for module in modules if module not in MODULES]\n"
                "    if unknown:\n"
                "        return 1\n"
                "    if any(arg.startswith('--exists') for arg in args):\n"
                "        return 0\n"
                "    if any(arg.startswith('--atleast-version') for arg in args):\n"
                "        return 0\n"
                "    if '--modversion' in args:\n"
                "        print(MODULES[modules[0]]['version'])\n"
                "        return 0\n"
                "    for arg in args:\n"
                "        if arg.startswith('--variable='):\n"
                "            variable = arg.split('=', 1)[1]\n"
                "            print(MODULES[modules[0]].get('variables', {}).get(variable, ''))\n"
                "            return 0\n"
                "    output = []\n"
                "    if '--cflags' in args:\n"
                "        for module in modules:\n"
                "            output.extend(MODULES[module]['cflags'])\n"
                "    if '--libs' in args:\n"
                "        for module in modules:\n"
                "            output.extend(MODULES[module]['libs'])\n"
                "    print(' '.join(flag for flag in output if flag))\n"
                "    return 0\n"
                "sys.exit(main())\n"
            )
        return f"{sys.executable} {shim}"

    def _pkg_config_modules(self):
        xcb_proto = self._dependency_folder("xcb-proto")
        return {
            "check": self._module("check", "0.15.2", "check"),
            "xau": self._module("libxau", "1.0.11", "Xau"),
            "xdmcp": self._module("libxdmcp", "1.1.5", "Xdmcp"),
            "xcb-proto": {
                "version": "1.17.0",
                "cflags": [],
                "libs": [],
                "variables": {
                    "pythondir": os.path.join(
                        xcb_proto, "lib", "python3", "site-packages"
                    )
                    if xcb_proto
                    else "",
                    "xcbincludedir": os.path.join(xcb_proto, "share", "xcb")
                    if xcb_proto
                    else "",
                },
            },
        }

    def _module(self, dependency, version, library):
        package_folder = self._dependency_folder(dependency)
        cflags = []
        libs = []
        if package_folder:
            include_dir = os.path.join(package_folder, "include")
            lib_dir = os.path.join(package_folder, "lib")
            if os.path.isdir(include_dir):
                cflags.append(f"-I{include_dir}")
            if os.path.isdir(lib_dir):
                libs.append(f"-L{lib_dir}")
        libs.append(f"-l{library}")
        return {
            "version": version,
            "cflags": cflags,
            "libs": libs,
            "variables": {},
        }

    def _dependency_folder(self, name):
        for dependencies in (
            self.dependencies.host,
            self.dependencies.build,
            self.dependencies.test,
        ):
            try:
                dependency = dependencies[name]
            except KeyError:
                continue
            return dependency.package_folder
        return None
