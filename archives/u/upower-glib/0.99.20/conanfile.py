#!/usr/bin/env python3
"""Conan recipe for upower-glib 0.99.20 (Meson)."""

import filecmp
import os
import posixpath
import re
import shlex
import shutil
import stat
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import (
    apply_conandata_patches,
    check_sha256,
    copy,
    export_conandata_patches,
    get,
    unzip,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class UpowerGlibConan(ConanFile):
    name = "upower-glib"
    version = "0.99.20"
    description = (
        "UPower is a system daemon for managing power devices; "
        "upower-glib is its client library"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://gitlab.freedesktop.org/upower/upower"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("glib/2.88.3")

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        if self.settings.os == "OHOS" and self.settings.arch != "armv8":
            raise ConanInvalidConfiguration(
                "upower-glib's target adaptation is validated only for AArch64"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        source = self.conan_data["sources"]
        configured_archive = self.conf.get(
            "user.upower-glib:source_archive", default=None
        )
        if not configured_archive:
            get(self, **source, strip_root=True)
            return

        configured_archive = os.path.abspath(os.fspath(configured_archive))
        if not os.path.isfile(configured_archive):
            raise ConanInvalidConfiguration(
                "user.upower-glib:source_archive does not name a regular file"
            )
        check_sha256(self, configured_archive, source["sha256"])
        local_archive = os.path.join(
            self.source_folder, "upower-v0.99.20.tar.bz2"
        )
        if os.path.normcase(configured_archive) != os.path.normcase(
            local_archive
        ):
            shutil.copy2(configured_archive, local_archive)
        check_sha256(self, local_archive, source["sha256"])
        unzip(self, local_archive, destination=self.source_folder, strip_root=True)

    @staticmethod
    def _require_absolute_tool(value, label):
        if not isinstance(value, str) or not value:
            raise ConanInvalidConfiguration(
                f"tools.build:compiler_executables[{label!r}] is not set"
            )
        if not os.path.isabs(value):
            raise ConanInvalidConfiguration(
                f"tools.build:compiler_executables[{label!r}] must be absolute"
            )
        if not os.path.isfile(value) or not os.access(value, os.X_OK):
            raise ConanInvalidConfiguration(
                f"tools.build:compiler_executables[{label!r}] is not executable"
            )
        return os.path.normpath(value)

    @classmethod
    def _resolve_llvm_tools(cls, executables):
        if not isinstance(executables, dict):
            raise ConanInvalidConfiguration(
                "tools.build:compiler_executables must be a dictionary"
            )
        compiler = cls._require_absolute_tool(
            executables.get("c"), "c"
        )
        compiler_dir = os.path.dirname(compiler)
        resolved = {}
        for name in ("ar", "ranlib", "nm", "objcopy", "strip"):
            configured = executables.get(name)
            if configured:
                resolved[name] = cls._require_absolute_tool(configured, name)
                continue
            candidates = (
                os.path.join(compiler_dir, f"llvm-{name}"),
                os.path.join(compiler_dir, name),
            )
            found = None
            for candidate in dict.fromkeys(candidates):
                if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                    found = os.path.normpath(candidate)
                    break
            if found is None:
                raise ConanInvalidConfiguration(
                    f"cannot resolve llvm-{name} beside the configured C compiler"
                )
            resolved[name] = found
        return resolved

    def generate(self):
        PkgConfigDeps(self).generate()

        toolchain = MesonToolchain(self)
        if str(self.settings.os) in ("Linux", "OHOS"):
            executables = self.conf.get(
                "tools.build:compiler_executables",
                default={},
                check_type=dict,
            ) or {}
            tools = self._resolve_llvm_tools(executables)
            toolchain.ar = tools["ar"]
            toolchain.strip = tools["strip"]
            toolchain.binaries["ranlib"] = tools["ranlib"]
            toolchain.binaries["nm"] = tools["nm"]
            toolchain.binaries["objcopy"] = tools["objcopy"]
        toolchain.project_options["default_library"] = (
            "shared" if self.options.shared else "static"
        )
        toolchain.project_options["wrap_mode"] = "nofallback"
        toolchain.project_options["man"] = "false"
        toolchain.project_options["gtk-doc"] = "false"
        toolchain.project_options["introspection"] = "disabled"
        toolchain.project_options["idevice"] = "disabled"
        # OHOS has no udev/systemd; disable those integration points.
        toolchain.project_options["udevrulesdir"] = "no"
        toolchain.project_options["udevhwdbdir"] = "no"
        toolchain.project_options["systemdsystemunitdir"] = "no"
        # PkgConfigDeps does not emit gio-unix-2.0.pc (it is shipped inside
        # the glib package's lib/pkgconfig), and glib's installed .pc files
        # carry spurious Requires for proxy-libintl/zlib/libpcre2-8 whose .pc
        # files PkgConfigDeps does not emit for transitive deps.  Copy the
        # glib .pc files into a fix dir: rewrite prefix, strip those private
        # requires, and prepend it so gio-unix-2.0 and the glib chain resolve
        # (glib-networking 2.90.0 pattern).
        glib_dep = self.dependencies.get("glib")
        extra_pc = []
        if glib_dep and glib_dep.package_folder:
            glib_pkg = glib_dep.package_folder
            glib_pc = os.path.join(glib_pkg, "lib", "pkgconfig")
            if os.path.isdir(glib_pc):
                pc_fix_dir = os.path.join(self.build_folder, "glib-pc-fix")
                os.makedirs(pc_fix_dir, exist_ok=True)
                for pc in os.listdir(glib_pc):
                    if not pc.endswith(".pc"):
                        continue
                    src = os.path.join(glib_pc, pc)
                    dst = os.path.join(pc_fix_dir, pc)
                    with open(src, "r", encoding="utf-8") as fh:
                        text = fh.read()
                    text = re.sub(
                        r"^prefix=.*$", f"prefix={glib_pkg}", text,
                        count=1, flags=re.M,
                    )
                    text = re.sub(
                        r"^(Requires(?:\.private)?):\s*([^\n]*)$",
                        lambda m: m.group(1) + ": "
                        + re.sub(
                            r"\b(?:proxy-libintl|zlib|libpcre2-8)\b"
                            r"(?:\s*>=\s*[0-9.]+)?(?:\s*,\s*|\s*$)",
                            "",
                            m.group(2),
                        ).strip().rstrip(",")
                        if any(
                            t in m.group(2)
                            for t in ("proxy-libintl", "zlib", "libpcre2-8")
                        )
                        else m.group(0),
                        text,
                        flags=re.M,
                    )
                    text = re.sub(
                        r"^Requires\.private:.*$",
                        "Requires.private:",
                        text,
                        flags=re.M,
                    )
                    if pc == "gio-2.0.pc":
                        # gnome.gdbus_codegen() (dbus/meson.build) falls back to
                        # the gdbus_codegen variable of gio-2.0.pc.
                        gdbus_codegen = os.path.join(glib_pkg, "bin", "gdbus-codegen")
                        if os.path.isfile(gdbus_codegen):
                            if re.search(r"^gdbus_codegen=", text, flags=re.M):
                                text = re.sub(
                                    r"^gdbus_codegen=.*$",
                                    f"gdbus_codegen={gdbus_codegen}",
                                    text, flags=re.M,
                                )
                            else:
                                text += f"\ngdbus_codegen={gdbus_codegen}\n"
                    with open(dst, "w", encoding="utf-8") as fh:
                        fh.write(text)
                extra_pc.insert(0, pc_fix_dir)
            glib_bin = os.path.join(glib_pkg, "bin")
            if os.path.isdir(glib_bin):
                self.buildenv_info.prepend_path("PATH", glib_bin)
        # pc-fix must win over the PkgConfigDeps-generated .pc.
        toolchain.pkg_config_path = os.pathsep.join(
            extra_pc + [toolchain.pkg_config_path]
        )
        toolchain.generate()

    def _runtime_directories(self):
        directories = [os.path.join(self.build_folder, "libupower-glib")]
        for dependency in self.dependencies.host.values():
            if not dependency.package_folder:
                continue
            for libdir in dependency.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dependency.package_folder, libdir)
                if os.path.isdir(libdir):
                    directories.append(libdir)
        return directories

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        runtime_path = ":".join(self._runtime_directories())
        self.run(
            f"LD_LIBRARY_PATH={shlex.quote(runtime_path)}"
            "${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH} "
            "meson compile -C . -j1",
            env="conanbuild",
        )

    def package(self):
        meson = Meson(self)
        meson.install()
        self._sign_final_ohos_package()

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as stream:
                return stream.read(4) == b"\x7fELF"
        except OSError:
            return False

    @staticmethod
    def _require_absolute_ohos_tool(value, label):
        if not isinstance(value, str) or not value:
            raise ConanInvalidConfiguration(
                f"tools.build:compiler_executables[{label!r}] is not set"
            )
        if not posixpath.isabs(value):
            raise ConanInvalidConfiguration(
                f"tools.build:compiler_executables[{label!r}] must be absolute"
            )
        if not os.path.isfile(value) or not os.access(value, os.X_OK):
            raise ConanInvalidConfiguration(
                f"tools.build:compiler_executables[{label!r}] is not executable"
            )
        return os.path.normpath(value)

    def _resolve_ohos_signing_tools(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = self._require_absolute_ohos_tool(
            executables.get("c"), "c"
        )
        compiler_dir = posixpath.dirname(compiler)
        tools = {
            "readelf": posixpath.join(compiler_dir, "llvm-readelf"),
            "objcopy": posixpath.join(compiler_dir, "llvm-objcopy"),
            "signer": posixpath.join(compiler_dir, "binary-sign-tool"),
        }
        missing = [
            name
            for name, path in tools.items()
            if not os.path.isfile(path) or not os.access(path, os.X_OK)
        ]
        if missing:
            if not can_run(self):
                self.output.info(
                    "PACKAGE_CODESIGN=NOT_RUN reason=cross_building; "
                    f"missing_tools={','.join(missing)}"
                )
                return None
            raise ConanInvalidConfiguration(
                "native OHOS package signing tools are missing: "
                + ", ".join(missing)
            )
        return tools

    @staticmethod
    def _run_signing_tool(arguments, label):
        completed = subprocess.run(
            arguments,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if completed.returncode != 0:
            raise ConanInvalidConfiguration(
                f"{label} failed with exit code {completed.returncode}"
            )
        return completed.stdout

    def _sign_final_ohos_elf(self, path, tools):
        if not os.path.isfile(path) or os.path.islink(path) or not self._is_elf(path):
            raise ConanInvalidConfiguration(
                f"required final OHOS ELF is missing, linked, or invalid: {path!r}"
            )
        original_mode = stat.S_IMODE(os.stat(path, follow_symlinks=False).st_mode)
        temporary = f"{path}.signing-{os.getpid()}"
        signed = f"{path}.signed-{os.getpid()}"
        if os.path.lexists(temporary) or os.path.lexists(signed):
            raise ConanInvalidConfiguration(
                f"OHOS ELF signing temporary already exists for {path!r}"
            )
        try:
            shutil.copy2(path, temporary)
            sections = self._run_signing_tool(
                [tools["readelf"], "-S", temporary], "pre-sign readelf"
            ).decode("utf-8", errors="strict")
            if ".codesign" in sections:
                self._run_signing_tool(
                    [tools["objcopy"], "--remove-section", ".codesign", temporary],
                    "codesign removal",
                )
            self._run_signing_tool(
                [
                    tools["signer"],
                    "sign",
                    "-inFile",
                    temporary,
                    "-outFile",
                    signed,
                    "-selfSign",
                    "1",
                ],
                "OHOS ELF signer",
            )
            if not os.path.isfile(signed) or os.path.islink(signed):
                raise ConanInvalidConfiguration(
                    f"OHOS ELF signer did not create a regular output: {path!r}"
                )
            signed_sections = self._run_signing_tool(
                [tools["readelf"], "-S", signed], "post-sign readelf"
            ).decode("utf-8", errors="strict")
            if signed_sections.count(".codesign") != 1:
                raise ConanInvalidConfiguration(
                    f"signed OHOS ELF must contain exactly one .codesign: {path!r}"
                )
            if filecmp.cmp(temporary, signed, shallow=False):
                raise ConanInvalidConfiguration(
                    f"OHOS ELF signer did not change the unsigned input: {path!r}"
                )
            os.chmod(signed, original_mode | 0o755)
            os.replace(signed, path)
        finally:
            for candidate in (temporary, signed):
                if os.path.lexists(candidate):
                    os.unlink(candidate)

    def _sign_final_ohos_package(self):
        if str(self.settings.os) != "OHOS":
            return
        tools = self._resolve_ohos_signing_tools()
        if tools is None:
            return

        signed_paths = []
        for directory, subdirectories, filenames in os.walk(self.package_folder):
            subdirectories.sort()
            for filename in sorted(filenames):
                path = os.path.join(directory, filename)
                if os.path.islink(path) or not self._is_elf(path):
                    continue
                self._sign_final_ohos_elf(path, tools)
                signed_paths.append(path)

        # The link-time aliases libupower-glib.so / .so.3 are symlinks
        # installed by meson; the runtime SONAME itself is the versioned
        # regular file libupower-glib.so.3.1.0 that must carry the signature.
        library_dir = os.path.join(self.package_folder, "lib")
        pattern = re.compile(r"^libupower-glib[.]so[.][0-9]+([.][0-9]+)*$")
        sonames = [
            os.path.join(library_dir, name)
            for name in os.listdir(library_dir)
            if pattern.fullmatch(name)
            and os.path.isfile(os.path.join(library_dir, name))
            and not os.path.islink(os.path.join(library_dir, name))
        ]
        if len(sonames) != 1:
            raise ConanInvalidConfiguration(
                f"expected one runtime SONAME for libupower-glib, "
                f"found {len(sonames)}"
            )
        soname = sonames[0]
        if soname not in signed_paths:
            raise ConanInvalidConfiguration(
                f"runtime SONAME was not signed: {soname!r}"
            )
        alias = os.path.join(library_dir, "libupower-glib.so")
        if os.path.islink(alias):
            if os.path.realpath(alias) != os.path.realpath(soname):
                raise ConanInvalidConfiguration(
                    f"link-time alias {alias!r} does not resolve to {soname!r}"
                )
        elif os.path.isfile(alias):
            shutil.copyfile(soname, alias)
            shutil.copymode(soname, alias, follow_symlinks=False)
            if not filecmp.cmp(alias, soname, shallow=False):
                raise ConanInvalidConfiguration(
                    f"signed link-time alias validation failed: {alias!r}"
                )
        else:
            raise ConanInvalidConfiguration(
                f"link-time alias is missing: {alias!r}"
            )
        self.output.info(f"PACKAGE_CODESIGN=PASS signed_elfs={len(signed_paths)}")

    def package_info(self):
        self.cpp_info.set_property("pkg_config_name", "upower-glib")
        self.cpp_info.libs = ["upower-glib"]
        # meson install_headers(..., subdir: 'libupower-glib') puts headers at
        # include/libupower-glib/*.h; consumers include <libupower-glib/upower.h>.
        self.cpp_info.includedirs = ["include"]
        # The package also installs the upower / upowerd CLI tools (R38:
        # commands.json declares them; keep bindirs aligned for consumers).
        self.cpp_info.bindirs = ["bin"]
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs.append("m")
