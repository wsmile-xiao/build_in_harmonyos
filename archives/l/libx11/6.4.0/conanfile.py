#!/usr/bin/env python3
"""Conan recipe for the libx11/6.4.0 compatibility package.

The Conan version follows the historical cmd-pkgs/SONAME identifier used by
downstream packages. The source archive is upstream libX11 1.8.10, whose
libtool version emits libX11.so.6.4.0.
"""

import json
import os
import re
import shutil
import sys
from pathlib import Path

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    rm,
)
from conan.tools.gnu import (
    Autotools,
    AutotoolsDeps,
    AutotoolsToolchain,
    PkgConfigDeps,
)
from conan.tools.gnu.get_gnu_triplet import _get_gnu_triplet
from conan.tools.layout import basic_layout


XORGPROTO_PC_MODULES = (
    "inputproto",
    "kbproto",
    "xextproto",
    "xf86bigfontproto",
    "xproto",
)


class Libx11Conan(ConanFile):
    name = "libx11"
    version = "6.4.0"
    description = "X.Org X11 client-side library"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/lib/libx11"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
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

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libx11 supports Linux and OHOS, not {self.settings.os}"
            )
        if str(self.settings.os) == "OHOS" and str(self.settings.arch) != "armv8":
            raise ConanInvalidConfiguration("libx11 OHOS validation targets armv8")

    def requirements(self):
        self.requires("xorgproto/2025.1", transitive_headers=True)
        self.requires("xtrans/1.6.0", transitive_headers=True)
        # libX11 1.8.10 hard-requires xcb >= 1.11.1 in configure.ac.
        # libxcb is intentionally modeled instead of being hidden as a system
        # library, so this package remains blocked until libxcb is published.
        self.requires("libxcb/1.16", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        if str(self.settings_build.os) in ("Linux", "OHOS"):
            self.tool_requires("perl/5.42.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        if str(self.settings.os) != "OHOS":
            AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()

        toolchain = AutotoolsToolchain(self)
        if str(self.settings.os) == "OHOS":
            # Match the current libxcb recipe: keep the OHOS identity in the
            # GNU triplet while letting libtool treat it as a Linux-family OS.
            toolchain.configure_args.append(
                f"--build={self._gnu_triplet(self.settings_build)}"
            )
            toolchain.configure_args.append(f"--host={self._gnu_triplet(self.settings)}")
        toolchain.configure_args.extend(
            [
                "--disable-dependency-tracking",
                "--disable-specs",
                "--with-xmlto=no",
                "--with-fop=no",
                "--with-xsltproc=no",
            ]
        )
        if self.options.shared:
            toolchain.configure_args.append("--enable-shared")
            toolchain.configure_args.append("--disable-static")
        else:
            toolchain.configure_args.append("--disable-shared")
            toolchain.configure_args.append("--enable-static")
        if str(self.settings.os) == "OHOS":
            toolchain.extra_cflags.append("-Qunused-arguments")
            toolchain.extra_cflags.append("-Wno-error=unused-command-line-argument")
            self._add_dependency_flags(toolchain)
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)

        environment = self._autotools_environment()
        autotools = Autotools(self)
        with VirtualBuildEnv(self).vars().apply(), environment.vars(self).apply():
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
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        lib_dir = os.path.join(self.package_folder, "lib")
        rm(self, "*.la", lib_dir, recursive=False)

    def package_info(self):
        self.cpp_info.libs = ["X11"]
        self.cpp_info.requires = [
            "xorgproto::xorgproto",
            "xtrans::xtrans",
            "libxcb::xcb",
        ]
        self.cpp_info.set_property("cmake_file_name", "libx11")
        self.cpp_info.set_property("cmake_target_name", "libx11::libx11")
        self.cpp_info.set_property("pkg_config_name", "x11")

        x11 = self.cpp_info.components["x11"]
        x11.libs = ["X11"]
        x11.requires = [
            "xorgproto::xorgproto",
            "xtrans::xtrans",
            "libxcb::xcb",
        ]
        x11.set_property("cmake_target_name", "libx11::x11")
        x11.set_property("pkg_config_name", "x11")

        x11_xcb = self.cpp_info.components["x11-xcb"]
        x11_xcb.libs = ["X11-xcb"]
        x11_xcb.requires = ["x11", "libxcb::xcb"]
        x11_xcb.set_property("cmake_target_name", "libx11::x11-xcb")
        x11_xcb.set_property("pkg_config_name", "x11-xcb")

        pc_dir = os.path.join(self.package_folder, "lib", "pkgconfig")
        self.buildenv_info.append_path("PKG_CONFIG_PATH", pc_dir)
        self.runenv_info.append_path("PKG_CONFIG_PATH", pc_dir)

    def _autotools_environment(self):
        tmp_dir = Path(self.build_folder) / "tmp"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        environment = Environment()
        environment.define_path("TMPDIR", str(tmp_dir))
        environment.define_path("TMP", str(tmp_dir))
        environment.define_path("TEMP", str(tmp_dir))
        environment.define_path("TMPPREFIX", str(tmp_dir / "zsh"))
        if str(self.settings.os) == "OHOS":
            self._prepend_ohos_tool_paths()
            shell = self._resolve_shell()
            self._patch_conan_env_scripts(shell)
            environment.define("CONFIG_SHELL", shell)
            environment.define("SHELL", shell)
            for variable, tool in {
                "LD": "ld.lld",
                "AR": "llvm-ar",
                "RANLIB": "llvm-ranlib",
                "NM": "llvm-nm",
                "STRIP": "llvm-strip",
            }.items():
                environment.define(variable, self._resolve_ohos_tool(tool))
            environment.define("PKG_CONFIG", self._write_pkg_config_shim())
            self._add_runtime_library_paths(environment)
        return environment

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
        if not self.generators_folder or not os.path.isdir(self.generators_folder):
            return

        bootstrap_paths = self._ohos_tool_paths()
        if not bootstrap_paths:
            return
        bootstrap = ":".join(bootstrap_paths)
        marker = "# libx11 OHOS PATH bootstrap"
        for entry in os.listdir(self.generators_folder):
            if not entry.endswith(".sh") or entry.startswith("deactivate_"):
                continue
            script_path = os.path.join(self.generators_folder, entry)
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

    def _add_dependency_flags(self, toolchain):
        for name in ("xorgproto", "xtrans", "libxcb", "libxau", "libxdmcp"):
            package_folder = self._dependency_folder(name)
            if not package_folder:
                continue
            include_dir = os.path.join(package_folder, "include")
            lib_dir = self._dependency_lib_dir(name, package_folder)
            if os.path.isdir(include_dir):
                toolchain.extra_cflags.append(f"-I{include_dir}")
            if lib_dir and os.path.isdir(lib_dir):
                toolchain.extra_ldflags.append(f"-L{lib_dir}")

    def _add_runtime_library_paths(self, environment):
        for name in ("libxcb", "libxau", "libxdmcp"):
            package_folder = self._dependency_folder(name)
            if not package_folder:
                continue
            lib_dir = os.path.join(package_folder, "lib")
            if os.path.isdir(lib_dir):
                environment.prepend_path("LD_LIBRARY_PATH", lib_dir)

    def _prepend_ohos_tool_paths(self):
        tool_paths = self._ohos_tool_paths()
        existing = os.environ.get("PATH", "")
        existing_parts = existing.split(os.pathsep) if existing else []
        for path in reversed(tool_paths):
            if os.path.isdir(path) and path not in existing_parts:
                existing = path + (os.pathsep + existing if existing else "")
                existing_parts.insert(0, path)
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
        shim = os.path.join(self.build_folder, "pkg-config-libx11.py")
        with open(shim, "w", encoding="utf-8") as handle:
            handle.write(
                "#!/usr/bin/env python3\n"
                "import json\n"
                "import re\n"
                "import sys\n"
                f"MODULES = {json.dumps(modules, sort_keys=True)}\n"
                "VERSION_RE = re.compile(r'^[0-9][0-9A-Za-z_.+-]*$')\n"
                "def requested_modules(args):\n"
                "    found = []\n"
                "    unknown = []\n"
                "    for arg in args:\n"
                "        if arg.startswith('-'):\n"
                "            continue\n"
                "        for token in re.split(r'\\s+|>=|<=|=|>|<', arg):\n"
                "            token = token.strip()\n"
                "            if not token or VERSION_RE.match(token):\n"
                "                continue\n"
                "            if token in MODULES:\n"
                "                if token not in found:\n"
                "                    found.append(token)\n"
                "            elif re.search(r'[A-Za-z]', token) and token not in unknown:\n"
                "                unknown.append(token)\n"
                "    return found, unknown\n"
                "def main():\n"
                "    args = sys.argv[1:]\n"
                "    if any(arg.startswith('--atleast-pkgconfig-version') for arg in args):\n"
                "        return 0\n"
                "    modules, unknown = requested_modules(args)\n"
                "    if unknown:\n"
                "        return 1\n"
                "    if not modules:\n"
                "        return 0\n"
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
        modules = {}
        xorgproto = self._dependency_folder("xorgproto")
        xorg_cflags = self._include_flags(xorgproto)
        xorg_variables = {
            "includedir": os.path.join(xorgproto, "include") if xorgproto else "",
        }
        for module in XORGPROTO_PC_MODULES:
            modules[module] = {
                "version": "2025.1",
                "cflags": xorg_cflags,
                "libs": [],
                "variables": xorg_variables,
            }

        xtrans = self._dependency_folder("xtrans")
        modules["xtrans"] = {
            "version": "1.6.0",
            "cflags": self._include_flags(xtrans) + self._dependency_defines("xtrans"),
            "libs": [],
            "variables": {
                "includedir": os.path.join(xtrans, "include") if xtrans else "",
            },
        }

        libxcb = self._dependency_folder("libxcb")
        modules["xcb"] = {
            "version": "1.16",
            "cflags": self._include_flags(libxcb),
            "libs": self._library_flags("libxcb", libxcb, "xcb"),
            "variables": {
                "includedir": os.path.join(libxcb, "include") if libxcb else "",
            },
        }
        return modules

    @staticmethod
    def _include_flags(package_folder):
        if not package_folder:
            return []
        include_dir = os.path.join(package_folder, "include")
        if os.path.isdir(include_dir):
            return [f"-I{include_dir}"]
        return []

    def _library_flags(self, name, package_folder, library):
        flags = []
        lib_dir = self._dependency_lib_dir(name, package_folder)
        if lib_dir and os.path.isdir(lib_dir):
            flags.append(f"-L{lib_dir}")
        flags.append(f"-l{library}")
        return flags

    def _dependency_lib_dir(self, name, package_folder):
        if not package_folder:
            return None
        lib_dir = os.path.join(package_folder, "lib")
        if str(self.settings.os) == "OHOS" and name in (
            "libxcb",
            "libxau",
            "libxdmcp",
        ):
            return self._stage_shared_libraries(name, lib_dir)
        return lib_dir

    def _stage_shared_libraries(self, name, lib_dir):
        if not os.path.isdir(lib_dir):
            return None

        stage_dir = Path(self.build_folder) / "libx11-deps-no-la" / name
        stage_dir.mkdir(parents=True, exist_ok=True)
        for library_path in Path(lib_dir).glob("*.so*"):
            target = stage_dir / library_path.name
            if target.exists() or target.is_symlink():
                target.unlink()
            shutil.copy2(library_path, target)
        return str(stage_dir)

    def _dependency_defines(self, name):
        defines = []
        try:
            dependency = self.dependencies.host[name]
        except KeyError:
            return defines
        for define in dependency.cpp_info.defines or []:
            defines.append(f"-D{define}")
        return defines

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
