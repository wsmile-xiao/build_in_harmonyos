from conan import ConanFile
import os
import shlex
import shutil
import sys

from conan.tools.files import collect_libs, get
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class Libdav1dConan(ConanFile):
    name = "libdav1d"
    version = "1.5.4"
    description = "Small and fast AV1 decoder from the VideoLAN project"
    license = "BSD-2-Clause"
    homepage = "https://code.videolan.org/videolan/dav1d"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = MesonToolchain(self)
        tc.project_options["enable_asm"] = False
        tc.project_options["enable_tools"] = False
        tc.project_options["enable_examples"] = False
        tc.project_options["enable_tests"] = True
        tc.project_options["enable_docs"] = False
        tc.project_options["testdata_tests"] = False
        tc.generate()
        self._patch_meson_machine_files()

    def build(self):
        if self.settings.os == "Windows" and not os.environ.get("NINJA"):
            python_scripts_ninja = os.path.join(os.path.dirname(sys.executable), "ninja.exe")
            ninja = shutil.which("ninja.exe") or shutil.which("ninja")
            if not ninja and os.path.isfile(python_scripts_ninja):
                ninja = python_scripts_ninja
            if ninja:
                os.environ["NINJA"] = ninja
        meson = Meson(self)
        meson.configure()
        meson.build()
        meson.test()

    def package(self):
        Meson(self).install()
        self._copy_shared_library_aliases()
        if str(self.settings.os) == "OHOS":
            self._sign_ohos_package_elfs()

    def package_info(self):
        self.cpp_info.libs = collect_libs(self) or ["dav1d"]
        self.cpp_info.set_property("cmake_file_name", "dav1d")
        self.cpp_info.set_property("cmake_target_name", "dav1d::dav1d")
        self.cpp_info.set_property("pkg_config_name", "dav1d")
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread", "m"]

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

        for name in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            path = os.path.join(self.generators_folder, name)
            if not os.path.isfile(path):
                continue
            with open(path, "r", encoding="utf-8") as handle:
                content = handle.read()
            if "[binaries]" not in content:
                continue
            if str(self.settings.os) == "OHOS":
                for arg in ("-D_POSIX_C_SOURCE=200809L", "-Qunused-arguments"):
                    content = self._append_meson_builtin_array_option(content, "c_args", arg)
            if ar and "\nar =" not in content:
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

    @classmethod
    def _append_meson_builtin_array_option(cls, content, option, value):
        quoted = cls._meson_quote(value)
        trailing_newline = "\n" if content.endswith("\n") else ""
        lines = content.splitlines()
        section_start = None
        for index, line in enumerate(lines):
            if line.strip() == "[built-in options]":
                section_start = index
                break
        if section_start is None:
            prefix = "\n" if content and not content.endswith("\n") else ""
            return "{}{}[built-in options]\n{} = [{}]\n".format(
                content,
                prefix,
                option,
                quoted,
            )

        section_end = len(lines)
        for index in range(section_start + 1, len(lines)):
            stripped = lines[index].strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                section_end = index
                break

        for index in range(section_start + 1, section_end):
            line = lines[index]
            if not line.strip().startswith(f"{option} ="):
                continue
            if quoted in line:
                return "\n".join(lines) + trailing_newline
            before, separator, after = line.rpartition("]")
            if not separator:
                continue
            if before.rstrip().endswith("["):
                lines[index] = before + quoted + separator + after
            else:
                lines[index] = before + ", " + quoted + separator + after
            return "\n".join(lines) + trailing_newline

        lines.insert(section_end, "{} = [{}]".format(option, quoted))
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
        objcopy = self._resolve_tool("llvm-objcopy")
        signer = self._resolve_tool("binary-sign-tool")
        if not objcopy or not signer:
            return
        for root_dir in ("lib", "bin"):
            scan_root = os.path.join(self.package_folder, root_dir)
            if not os.path.isdir(scan_root):
                continue
            self._sign_ohos_elfs_in_directory(scan_root, objcopy, signer)

    def _sign_ohos_elfs_in_directory(self, scan_root, objcopy, signer):
        for root, _, filenames in os.walk(scan_root):
            for filename in sorted(filenames):
                path = os.path.join(root, filename)
                if os.path.islink(path) or not self._is_elf(path):
                    continue
                mode = os.stat(path).st_mode
                signed_path = path + ".signed"
                self.run("{} 2>/dev/null || true".format(
                    shlex.join([objcopy, "--remove-section", ".codesign", path])
                ))
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
