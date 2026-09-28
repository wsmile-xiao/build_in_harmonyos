#!/usr/bin/env python3
"""Conan recipe — libtypec 0.6.0 (Meson, OHOS).

libtypec 是用户态访问 Linux USB Type-C / USB Power Delivery 子系统的 C 库，
通过 sysfs (/sys/class/typec) 与 debugfs 暴露连接器能力、PDO、连接器状态等。

依赖：
- eudev/3.2.14 提供 libudev。上游 meson.build 里 `dependency('libudev',
  required: true)`，仅 libtypec_sysfs_ops.c 使用 udev monitor 跟踪 typec 事件。

构建系统说明：
- 上游 0.6.0 同时提供 meson.build 与 CMakeLists.txt。本配方选用 Meson：
  顶层 meson.build 只构建共享库 `typec`（libtypec.so），不引入 utils/
  （CMake 会额外构建 lstypec/typecstatus/ucsicontrol，且 usbcview 需要 gtk3）。
- 因此本包是纯库，无 bin/ 可执行文件，不需要 commands.json。

OHOS 适配要点（详见 notes.md）：
- 仅交叉编译出 .so；运行期需要 /sys/class/typec 与真实 Type-C 控制器，
  OHOS 设备上无该 sysfs 类，故 test_package 不依赖硬件，只验证库能被加载、
  符号可解析、libtypec_init 能填充版本串。
- 内核 UAPI 头（<linux/usbdevice_fs.h>、<linux/usb/ch9.h>、<linux/magic.h>）
  若 OHOS NDK 缺失，需要在真机/CI 阶段补 patch（本轮本机前置尚未触发）。
"""
import os
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps


class LibtypecConan(ConanFile):
    name = "libtypec"
    version = "0.6.0"
    description = "C library to interface with USB Type-C and USB Power Delivery class devices"
    license = "MIT"
    homepage = "https://github.com/Rajaram-Regupathy/libtypec"
    url = "https://github.com/Rajaram-Regupathy/libtypec"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
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
        if str(self.settings.os) == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # Hard dependency: upstream meson.build uses dependency('libudev',
        # required: true). eudev ships libudev.so + headers + libudev.pc.
        self.requires("eudev/3.2.14")

    def build_requirements(self):
        # Meson's dependency('libudev') reads libudev.pc via a pkg-config
        # binary. The OHOS device has no system pkg-config; pkgconf/3.0.5
        # (already in the local cache) provides it as a build tool.
        self.tool_requires("pkgconf/3.0.5")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libtypec targets the Linux Type-C/PD sysfs ABI; only Linux/OHOS are supported"
            )

    def source(self):
        sources = dict(self.conan_data["sources"])
        mirror_urls = sources.pop("mirror_urls", [])
        mirror_sha256 = sources.pop("mirror_sha256", None)
        try:
            get(self, **sources, strip_root=True)
        except Exception as error:
            if not mirror_urls or not mirror_sha256:
                raise
            self.output.warning(f"Primary source failed ({error}); trying verified mirrors")
            for mirror_url in mirror_urls:
                try:
                    get(self, url=mirror_url, sha256=mirror_sha256, strip_root=True)
                    return
                except Exception as mirror_error:
                    self.output.warning(f"Mirror source failed ({mirror_error}): {mirror_url}")
            raise

    def generate(self):
        # eudev exposes libudev only as a pkg-config dependency; upstream probes
        # it with dependency('libudev'), so generate libudev.pc into the env.
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.generate()
        # The pkgconf tool package ships a binary named `pkgconf`, not
        # `pkg-config`; meson looks up `pkg-config` by default. Point it at the
        # tool-provided `pkgconf` on PATH.
        os.environ["PKG_CONFIG"] = "pkgconf"
        self._patch_meson_machine_files()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()

        # Meson installs libtypec.so.0.6.0 with soversion 0; materialise the
        # linker alias libtypec.so and the SONAME alias libtypec.so.0.
        self._copy_shared_library_aliases()

        if str(self.settings.os) == "OHOS":
            self._sign_ohos_package_elfs()

        license_src = os.path.join(self.source_folder, "LICENSES")
        if os.path.isdir(license_src):
            copy(self, "MIT", src=license_src,
                 dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["typec"]
        self.cpp_info.set_property("cmake_file_name", "libtypec")
        self.cpp_info.set_property("cmake_target_name", "libtypec::libtypec")
        self.cpp_info.set_property("pkg_config_name", "libtypec")
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "dl", "pthread"]

    # ------------------------------------------------------------------ #
    # OHOS meson cross-file helpers (proven on libdvbv5)
    # ------------------------------------------------------------------ #
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
            if "\nar = " not in content:
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
            source_path = os.path.join(lib_dir, name)
            if not os.path.isfile(source_path):
                continue
            prefix, version = name.split(".so.", 1)
            version_parts = version.split(".")
            aliases = ["{}.so".format(prefix),
                       "{}.so.{}".format(prefix, version_parts[0])]
            for alias in aliases:
                target = os.path.join(lib_dir, alias)
                if not os.path.exists(target):
                    shutil.copy2(source_path, target)

    # ------------------------------------------------------------------ #
    # OHOS ELF codesigning (shared lib must be signed to be loadable)
    # ------------------------------------------------------------------ #
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
            signer, "sign", "-inFile", path, "-outFile", signed_path,
            "-selfSign", "1",
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
