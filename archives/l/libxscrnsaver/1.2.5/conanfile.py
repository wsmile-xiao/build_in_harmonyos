#!/usr/bin/env python3
"""Conan recipe for libXScrnSaver 1.2.5.

The upstream Meson build consumes libX11, libXext, xextproto and
scrnsaverproto through pkg-config.  xorgproto/2025.1 provides the protocol
headers and .pc files; libx11/libxext are kept as normal Conan requirements so
this recipe stays self-contained once those dependency recipes are published.
"""

import glob
import os
import shutil
import site
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibXScrnSaverConan(ConanFile):
    name = "libxscrnsaver"
    version = "1.2.5"
    description = "X11 Screen Saver extension client library"
    license = "MIT"
    homepage = "https://gitlab.freedesktop.org/xorg/lib/libXScrnSaver"
    url = "https://gitlab.freedesktop.org/xorg/lib/libXScrnSaver"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "conandata.yml", "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libxscrnsaver supports Linux and OHOS, not {self.settings.os}"
            )
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        self.requires("libx11/6.4.0", transitive_headers=True, transitive_libs=True)
        self.requires("libxext/6.4.0", transitive_headers=True, transitive_libs=True)
        self.requires("xorgproto/2025.1", transitive_headers=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(
            self,
            **self.conan_data["sources"][str(self.version)],
            strip_root=True,
        )

    def generate(self):
        VirtualBuildEnv(self).generate()
        pkg_config = PkgConfigDeps(self)
        pkg_config.set_property("libx11", "pkg_config_name", "x11")
        pkg_config.set_property("libxext", "pkg_config_name", "xext")
        pkg_config.generate()
        self._copy_xorgproto_pc_files()
        toolchain = MesonToolchain(self)
        toolchain.project_options["default_library"] = (
            "shared" if self.options.shared else "static"
        )
        toolchain.project_options["wrap_mode"] = "nodownload"
        toolchain.generate()
        self._patch_meson_tool_paths()
        self._inject_meson_archiver()

    def build(self):
        self._ensure_meson()
        self._ensure_pkg_config()
        self._ensure_writable_tmpdir()
        self._patch_meson_pkg_config_binary()
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        Meson(self).install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        self._sign_shared_libs()

    def package_info(self):
        self.cpp_info.libs = ["Xss"]
        self.cpp_info.requires = [
            "libx11::libx11",
            "libxext::libxext",
            "xorgproto::xorgproto",
        ]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.set_property("cmake_file_name", "libxscrnsaver")
        self.cpp_info.set_property(
            "cmake_target_name", "libxscrnsaver::libxscrnsaver"
        )
        self.cpp_info.set_property("pkg_config_name", "xscrnsaver")

    def _ensure_meson(self):
        self._prepend_python_user_bin()
        if shutil.which("meson"):
            return
        self.run(f'"{sys.executable}" -m pip install --user meson')
        self._prepend_python_user_bin()

    def _ensure_pkg_config(self):
        self._prepend_python_user_bin()
        existing = shutil.which("pkg-config") or shutil.which("pkgconf")
        if existing:
            self._pkg_config_binary = existing
            return
        pkg_config = os.path.join(self.generators_folder, "pkg-config")
        with open(pkg_config, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(self._minimal_pkg_config_script())
        os.chmod(pkg_config, 0o755)
        os.environ["PATH"] = (
            self.generators_folder + os.pathsep + os.environ.get("PATH", "")
        )
        self._pkg_config_binary = pkg_config

    def _prepend_python_user_bin(self):
        user_bin = os.path.join(site.USER_BASE, "bin")
        path = os.environ.get("PATH", "")
        entries = path.split(os.pathsep) if path else []
        if os.path.isdir(user_bin) and user_bin not in entries:
            os.environ["PATH"] = user_bin + os.pathsep + path

    def _copy_xorgproto_pc_files(self):
        dependency = self.dependencies["xorgproto"]
        source_dir = os.path.join(dependency.package_folder, "share", "pkgconfig")
        for name in ("xextproto.pc", "scrnsaverproto.pc"):
            source = os.path.join(source_dir, name)
            if not os.path.isfile(source):
                continue
            with open(source, encoding="utf-8") as handle:
                content = handle.read()
            content = content.replace(
                "prefix=${pcfiledir}/../..",
                "prefix={}".format(dependency.package_folder.replace("\\", "/")),
            )
            with open(
                os.path.join(self.generators_folder, name),
                "w",
                encoding="utf-8",
                newline="\n",
            ) as handle:
                handle.write(content)

    def _ensure_writable_tmpdir(self):
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        for name in ("TMPDIR", "TMP", "TEMP"):
            os.environ[name] = tmpdir

    def _patch_meson_tool_paths(self):
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if str(self.settings.os) != "OHOS" or not os.path.isfile(native_file):
            return
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        replacements = {}
        for key, tool in (("c", "clang"), ("cpp", "clang++")):
            configured = executables.get(key)
            if configured and os.path.isfile(configured):
                continue
            fallback = shutil.which(tool)
            if fallback:
                replacements[key] = fallback.replace("\\", "/")
        if not replacements:
            return
        with open(native_file, encoding="utf-8") as handle:
            content = handle.read()
        for key, value in replacements.items():
            content = self._replace_meson_binary(content, key, f"'{value}'")
        with open(native_file, "w", encoding="utf-8") as handle:
            handle.write(content)

    def _patch_meson_pkg_config_binary(self):
        pkg_config = getattr(self, "_pkg_config_binary", None)
        pkg_config = pkg_config or shutil.which("pkg-config") or shutil.which("pkgconf")
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not (pkg_config and os.path.isfile(native_file)):
            return
        with open(native_file, encoding="utf-8") as handle:
            content = handle.read()
        value = "'{}'".format(pkg_config.replace("\\", "/"))
        if "\npkgconfig =" in content:
            content = self._replace_meson_binary(content, "pkgconfig", value)
        elif "[binaries]" in content:
            content = content.replace("[binaries]\n", f"[binaries]\npkgconfig = {value}\n", 1)
        with open(native_file, "w", encoding="utf-8") as handle:
            handle.write(content)

    @staticmethod
    def _minimal_pkg_config_script():
        return r'''#!/usr/bin/env python3
import os
import re
import sys


def split_paths(value):
    return [item for item in value.split(os.pathsep) if item]


def expand(value, variables):
    pattern = re.compile(r"\$\{([^}]+)\}")
    old = None
    while old != value:
        old = value
        value = pattern.sub(lambda match: variables.get(match.group(1), ""), value)
    return value


def load_pc(name, seen=None):
    seen = seen or set()
    if name in seen:
        return {"version": "", "cflags": [], "libs": [], "requires": []}
    seen.add(name)
    search_dirs = split_paths(os.environ.get("PKG_CONFIG_PATH", ""))
    search_dirs.extend(split_paths(os.environ.get("PKG_CONFIG_LIBDIR", "")))
    search_dirs.append(os.path.dirname(os.path.abspath(__file__)))
    pc_path = None
    for directory in search_dirs:
        candidate = os.path.join(directory, name + ".pc")
        if os.path.isfile(candidate):
            pc_path = candidate
            break
    if not pc_path:
        raise SystemExit("Package %s was not found in the pkg-config search path" % name)

    variables = {"pcfiledir": os.path.dirname(pc_path)}
    fields = {}
    with open(pc_path, encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                key, value = line.split(":", 1)
                fields[key.strip()] = expand(value.strip(), variables)
            elif "=" in line:
                key, value = line.split("=", 1)
                variables[key.strip()] = expand(value.strip(), variables)

    requires = []
    for key in ("Requires", "Requires.private"):
        for item in fields.get(key, "").replace(",", " ").split():
            if item in ("<", "<=", "=", ">=", ">"):
                continue
            if re.match(r"^[0-9][A-Za-z0-9_.+-]*$", item):
                continue
            requires.append(item)

    result = {
        "version": fields.get("Version", ""),
        "cflags": fields.get("Cflags", "").split(),
        "libs": fields.get("Libs", "").split(),
        "requires": requires,
    }
    for requirement in requires:
        dep = load_pc(requirement, seen)
        result["cflags"] = dep["cflags"] + result["cflags"]
        result["libs"] = dep["libs"] + result["libs"]
    return result


def dedupe(items):
    result = []
    seen = set()
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


args = sys.argv[1:]
if "--version" in args or any(arg.startswith("--atleast-pkgconfig-version") for arg in args):
    print("0.29.2")
    raise SystemExit(0)

packages = []
skip_next = False
for arg in args:
    if skip_next:
        skip_next = False
        continue
    if arg.startswith("-"):
        continue
    if arg in ("<", "<=", "=", ">=", ">"):
        skip_next = True
        continue
    if re.match(r"^[0-9][A-Za-z0-9_.+-]*$", arg):
        continue
    for part in arg.replace(",", " ").split():
        if part not in ("<", "<=", "=", ">=", ">") and not re.match(r"^[0-9]", part):
            packages.append(part)

try:
    loaded = [load_pc(package) for package in packages]
except SystemExit as error:
    if "--exists" in args or "--silence-errors" in args:
        raise SystemExit(1)
    print(error, file=sys.stderr)
    raise SystemExit(1)

if "--exists" in args:
    raise SystemExit(0)

output = []
if "--modversion" in args:
    output.extend(item["version"] for item in loaded if item["version"])
if "--cflags" in args:
    flags = []
    for item in loaded:
        flags.extend(item["cflags"])
    output.extend(dedupe(flags))
if "--libs" in args or "--libs-only-L" in args or "--libs-only-l" in args:
    libs = []
    for item in loaded:
        libs.extend(item["libs"])
    if "--libs-only-L" in args:
        libs = [item for item in libs if item.startswith("-L")]
    elif "--libs-only-l" in args:
        libs = [item for item in libs if item.startswith("-l")]
    output.extend(dedupe(libs))

if output:
    print(" ".join(output))
raise SystemExit(0)
'''

    def _inject_meson_archiver(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        ar = executables.get("ar")
        ranlib = executables.get("ranlib")
        if not ar:
            compiler = executables.get("c") or ""
            bindir = os.path.dirname(compiler) if os.path.sep in compiler else ""
            if bindir:
                candidate = os.path.join(bindir, "llvm-ar")
                if os.path.isfile(candidate):
                    ar = candidate
                    ranlib_candidate = os.path.join(bindir, "llvm-ranlib")
                    if os.path.isfile(ranlib_candidate):
                        ranlib = ranlib_candidate
        if not ar:
            ar = shutil.which("llvm-ar") or shutil.which("ar")
        if not ranlib:
            ranlib = shutil.which("llvm-ranlib") or shutil.which("ranlib")
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not (ar and os.path.isfile(native_file)):
            return
        with open(native_file, encoding="utf-8") as handle:
            content = handle.read()
        if "\nar =" in content or "[binaries]" not in content:
            return
        insert = "[binaries]\nar = '{}'\n".format(ar.replace("\\", "/"))
        if ranlib:
            insert += "ranlib = '{}'\n".format(ranlib.replace("\\", "/"))
        with open(native_file, "w", encoding="utf-8") as handle:
            handle.write(content.replace("[binaries]\n", insert, 1))

    def _sign_shared_libs(self):
        if str(self.settings.os) != "OHOS" or not self.options.shared:
            return
        objcopy = self._tool_path("llvm-objcopy", "/data/service/hnp/bin/llvm-objcopy")
        signer = self._tool_path(
            "binary-sign-tool", "/data/service/hnp/bin/binary-sign-tool"
        )
        libdir = os.path.join(self.package_folder, "lib")
        targets = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        targets += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        for target in targets:
            if os.path.islink(target):
                continue
            self.run(
                f'"{objcopy}" --remove-section .codesign "{target}" '
                "2>/dev/null || true"
            )
            self.run(
                f'"{signer}" sign -inFile "{target}" -outFile "{target}" '
                "-selfSign 1"
            )

    @staticmethod
    def _replace_meson_binary(content, key, value):
        lines = content.splitlines()
        for index, line in enumerate(lines):
            if line.startswith(f"{key} = "):
                lines[index] = f"{key} = {value}"
                break
        trailing_newline = "\n" if content.endswith("\n") else ""
        return "\n".join(lines) + trailing_newline

    @staticmethod
    def _tool_path(name, preferred):
        if os.path.isfile(preferred):
            return preferred
        return shutil.which(name) or preferred
