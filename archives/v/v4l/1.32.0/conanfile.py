#!/usr/bin/env python3
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    collect_libs,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
)
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class V4lConan(ConanFile):
    name = "v4l"
    version = "1.32.0"
    description = "Video4Linux userspace libraries and utilities"
    license = "LGPL-2.1-or-later"
    homepage = "https://linuxtv.org/wiki/index.php/V4l-utils"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_utils": [True, False],
        "with_plugins": [True, False],
        "with_wrappers": [True, False],
    }
    default_options = {
        "shared": True,
        "fPIC": True,
        "with_utils": False,
        "with_plugins": False,
        "with_wrappers": False,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if str(self.settings.os) == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "v4l requires Linux/OHOS V4L2/media headers and ioctl support"
            )

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.project_options["bpf"] = "disabled"
        tc.project_options["gconv"] = "disabled"
        tc.project_options["jpeg"] = "disabled"
        tc.project_options["libdvbv5"] = "disabled"
        tc.project_options["qv4l2"] = "disabled"
        tc.project_options["qvidcap"] = "disabled"
        tc.project_options["v4l2-tracer"] = "disabled"
        tc.project_options["v4l-plugins"] = bool(self.options.with_plugins)
        tc.project_options["v4l-utils"] = bool(self.options.with_utils)
        tc.project_options["v4l-wrappers"] = bool(self.options.with_wrappers)
        tc.project_options["v4l2-compliance-libv4l"] = False
        tc.project_options["v4l2-ctl-libv4l"] = False
        tc.project_options["v4l2-ctl-stream-to"] = False
        tc.project_options["doxygen-doc"] = "disabled"
        tc.project_options["doxygen-html"] = False
        tc.project_options["doxygen-man"] = False
        tc.generate()
        self._patch_meson_machine_files()

    def build(self):
        apply_conandata_patches(self)
        if str(self.settings.os) == "OHOS":
            replace_in_file(
                self,
                os.path.join(self.source_folder, "meson.build"),
                "prog_perl = find_program('perl')",
                "prog_perl = find_program('perl', required : false)",
            )
            replace_in_file(
                self,
                os.path.join(self.source_folder, "meson.build"),
                "    dep_argp = cc.find_library('argp')",
                "    dep_argp = dependency('', required : false)",
            )
            replace_in_file(
                self,
                os.path.join(self.source_folder, "meson.build"),
                "dep_intl = dependency('intl')",
                "dep_intl = dependency('intl', required : false)",
            )
            replace_in_file(
                self,
                os.path.join(self.source_folder, "meson.build"),
                "v4l2_utils_incdir_arr = [\n    'lib' / 'include',\n]",
                "v4l2_utils_incdir_arr = [\n    'lib' / 'include',\n    'include',\n]",
            )
            replace_in_file(
                self,
                os.path.join(self.source_folder, "lib", "libv4lconvert", "libv4lconvert.c"),
                '#include "libv4lsyscall-priv.h"\n',
                '#include "libv4lsyscall-priv.h"\n\n'
                "#ifndef V4L2_PIX_FMT_NV12_16L16\n"
                "#define V4L2_PIX_FMT_NV12_16L16 v4l2_fourcc('H', 'M', '1', '2')\n"
                "#endif\n",
            )
            utils_meson = os.path.join(self.source_folder, "utils", "meson.build")
            for subdir in ("libcecutil", "cec-ctl", "cec-follower", "cec-compliance"):
                replace_in_file(
                    self,
                    utils_meson,
                    "subdir('{}')".format(subdir),
                    "if prog_perl.found()\n    subdir('{}')\nendif".format(subdir),
                )
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()
        self._copy_shared_library_aliases()
        if str(self.settings.os) == "OHOS":
            self._sign_ohos_package_elfs()
        for license_file in ("COPYING", "COPYING.libv4l", "COPYING.libdvbv5"):
            copy(self, license_file, src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        detected_libs = collect_libs(self)
        preferred = ["v4l2", "v4l1", "v4lconvert", "v4l2rds"]
        self.cpp_info.libs = [lib for lib in preferred if lib in detected_libs] or detected_libs or preferred
        self.cpp_info.set_property("cmake_file_name", "v4l")
        self.cpp_info.set_property("cmake_target_name", "v4l::v4l")
        self.cpp_info.set_property("pkg_config_name", "libv4l2")
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "dl", "pthread", "rt"]

    def _patch_meson_machine_files(self):
        compiler_exes = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        shell = os.environ.get("CONFIG_SHELL") or os.environ.get("SHELL") or "/bin/sh"
        wrapper_binaries = {}
        if str(self.settings.os) == "OHOS":
            for key in ("c", "cpp"):
                compiler = compiler_exes.get(key)
                if compiler and self._is_shell_script(compiler):
                    wrapper_binaries[key] = "[{}, {}]".format(
                        self._meson_quote(shell),
                        self._meson_quote(compiler),
                    )

        ar = compiler_exes.get("ar")
        ranlib = compiler_exes.get("ranlib")
        if not ar:
            cc = compiler_exes.get("c") or ""
            bindir = os.path.dirname(cc) if os.path.sep in cc else ""
            if bindir:
                candidate = os.path.join(bindir, "llvm-ar")
                if os.path.isfile(candidate):
                    ar = candidate
                    ranlib_candidate = os.path.join(bindir, "llvm-ranlib")
                    if os.path.isfile(ranlib_candidate):
                        ranlib = ranlib_candidate
        if not ar:
            return

        for name in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            path = os.path.join(self.generators_folder, name)
            if not os.path.isfile(path):
                continue
            with open(path, "r", encoding="utf-8") as handle:
                content = handle.read()
            if "[binaries]" not in content:
                continue
            if "\nar =" not in content:
                insertion = "[binaries]\nar = '{}'\n".format(ar.replace("\\", "/"))
                if ranlib:
                    insertion += "ranlib = '{}'\n".format(ranlib.replace("\\", "/"))
                content = content.replace("[binaries]\n", insertion, 1)
            for key, value in wrapper_binaries.items():
                content = self._replace_meson_binary(content, key, value)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(content)

    @staticmethod
    def _is_shell_script(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(32).startswith(b"#!")
        except OSError:
            return False

    @staticmethod
    def _meson_quote(value):
        return "'{}'".format(value.replace("\\", "/").replace("'", "\\'"))

    @staticmethod
    def _replace_meson_binary(content, key, value):
        lines = content.splitlines()
        for index, line in enumerate(lines):
            if line.startswith(f"{key} = "):
                lines[index] = f"{key} = {value}"
                break
        trailing_newline = "\n" if content.endswith("\n") else ""
        return "\n".join(lines) + trailing_newline

    def _copy_shared_library_aliases(self):
        lib_dir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(lib_dir):
            return
        for name in os.listdir(lib_dir):
            if ".so." not in name:
                continue
            source = os.path.join(lib_dir, name)
            if not os.path.isfile(source):
                continue
            prefix, version = name.split(".so.", 1)
            aliases = ["{}.so".format(prefix)]
            version_parts = version.split(".")
            aliases.extend(
                "{}.so.{}".format(prefix, ".".join(version_parts[:index]))
                for index in range(1, len(version_parts))
            )
            for alias in aliases:
                target = os.path.join(lib_dir, alias)
                if not os.path.exists(target):
                    shutil.copy2(source, target)

    def _sign_ohos_package_elfs(self):
        elf_paths = []
        for root_dir in ("lib", "bin"):
            scan_root = os.path.join(self.package_folder, root_dir)
            if os.path.isdir(scan_root):
                elf_paths.extend(self._collect_ohos_elfs(scan_root))
        if not elf_paths:
            return

        objcopy = self._resolve_tool("llvm-objcopy")
        signer = self._resolve_tool("binary-sign-tool")
        missing = []
        if not objcopy:
            missing.append("llvm-objcopy")
        if not signer:
            missing.append("binary-sign-tool")
        if missing:
            raise ConanInvalidConfiguration(
                "OHOS ELF signing requires {}".format(", ".join(missing))
            )

        for path in elf_paths:
            self._sign_ohos_elf(path, objcopy, signer)

    def _collect_ohos_elfs(self, scan_root):
        elf_paths = []
        for root, _, filenames in os.walk(scan_root):
            for filename in sorted(filenames):
                path = os.path.join(root, filename)
                if os.path.islink(path) or not self._is_elf(path):
                    continue
                elf_paths.append(path)
        return elf_paths

    def _sign_ohos_elf(self, path, objcopy, signer):
        mode = os.stat(path).st_mode
        signed_path = path + ".signed"
        if os.path.exists(signed_path):
            os.remove(signed_path)
        self.run(shlex.join([objcopy, "--remove-section", ".codesign", path]))
        self.run(shlex.join([
            signer,
            "sign",
            "-inFile",
            path,
            "-outFile",
            signed_path,
            "-selfSign",
            "1",
        ]))
        os.replace(signed_path, path)
        os.chmod(path, mode)

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _resolve_tool(self, name):
        compiler_exes = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        compiler = compiler_exes.get("c") or ""
        compiler_path = shutil.which(compiler) or compiler
        compiler_dir = os.path.dirname(compiler_path) if compiler_path else ""
        candidates = [
            os.environ.get(name.upper().replace("-", "_")),
            shutil.which(name),
            os.path.join(compiler_dir, name) if compiler_dir else None,
            os.path.join(os.path.expanduser("~"), "usr", "local", "bin", name),
            os.path.join("/data/service/hnp/bin", name),
        ]
        for candidate in candidates:
            if candidate and os.path.isfile(candidate):
                return candidate
        return ""
