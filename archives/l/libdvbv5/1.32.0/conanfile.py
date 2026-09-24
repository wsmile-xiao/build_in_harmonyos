#!/usr/bin/env python3
"""Conan recipe — libdvbv5 1.32.0 (Meson, OHOS).

libdvbv5 是 v4l-utils 源码树里的 DVBv5 用户态库（DVB 前端/解复用/表解析/
频道文件读写）。上游只以 v4l-utils 整体发布，没有独立 tarball，因此本配方
下载官方 v4l-utils 发布包，用 Meson 选项只启用 libdvbv5 目标。

依赖：
- eudev/3.2.14 提供 libudev。上游 `lib/libdvbv5/meson.build` 在
  `dep_libudev` 未找到时直接 `subdir_done()`，因此 libudev 是硬依赖。

OHOS 适配要点（详见 patches/ 与 notes.md）：
- musl 无 argp / 无可用的 libintl，上游顶层 meson.build 的探测是
  `cc.find_library('argp')`（硬性）与 `dependency('intl')`（硬性），会让
  整个 configure 失败；改为可选，并由 gettext.h 的 NLS-disabled 分支兜底。
- 顶层 include/ 只在 `host_machine.system() == 'linux'` 时加入搜索路径，
  OHOS 下 `gettext.h` 找不到；把 `harmonyos` 纳入同一分支。
- OHOS UAPI 头缺少 `V4L2_PIX_FMT_NV12_16L16`（libv4lconvert 用到）。
- musl 无 `pthread_cancel`：两处线程清理改为协作停止 + `pthread_join`。
- OHOS 共享库必须签名后才能被加载器加载（package() 内用 binary-sign-tool）。
"""
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
)
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain
from conan.tools.gnu import PkgConfigDeps


class Libdvbv5Conan(ConanFile):
    name = "libdvbv5"
    version = "1.32.0"
    description = "DVBv5 userspace library (libdvbv5 from v4l-utils)"
    license = "LGPL-2.1-or-later"
    homepage = "https://linuxtv.org/wiki/index.php/V4l-utils"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
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
        # Hard requirement: upstream skips the whole library when libudev is
        # missing. eudev ships libudev.so/.h and libudev.pc.
        self.requires("eudev/3.2.14")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libdvbv5 requires Linux/OHOS DVB UAPI headers and ioctl support"
            )

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # eudev ships libudev only as a pkg-config dependency; upstream probes
        # it with dependency('libudev'), so its .pc file must be generated and
        # PKG_CONFIG_PATH injected.
        PkgConfigDeps(self).generate()
        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        tc.project_options["libdvbv5"] = "enabled"
        # Everything below is outside this package's surface; disable it so the
        # build stays minimal and does not pull Qt/BPF/JPEG/DVB utilities.
        tc.project_options["bpf"] = "disabled"
        tc.project_options["gconv"] = "disabled"
        tc.project_options["jpeg"] = "disabled"
        tc.project_options["qv4l2"] = "disabled"
        tc.project_options["qvidcap"] = "disabled"
        tc.project_options["v4l2-tracer"] = "disabled"
        tc.project_options["doxygen-doc"] = "disabled"
        tc.project_options["doxygen-html"] = False
        tc.project_options["doxygen-man"] = False
        tc.project_options["v4l-utils"] = False
        tc.project_options["v4l-plugins"] = False
        tc.project_options["v4l-wrappers"] = False
        tc.generate()
        self._patch_meson_machine_files()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()
        # Upstream's lib/meson.build always descends into libv4lconvert,
        # libv4l2, libv4l1 and libv4l2rds; there is no option to build
        # libdvbv5 alone. Those four libraries belong to the `v4l` package,
        # so drop them here and keep this package's surface to libdvbv5.
        self._prune_non_libdvbv5()
        self._copy_shared_library_aliases()
        if str(self.settings.os) == "OHOS":
            self._sign_ohos_package_elfs()
        for license_file in ("COPYING", "COPYING.libdvbv5"):
            copy(self, license_file, src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        detected_libs = collect_libs(self)
        self.cpp_info.libs = ["dvbv5"] if "dvbv5" in detected_libs else detected_libs or ["dvbv5"]
        self.cpp_info.set_property("cmake_file_name", "libdvbv5")
        self.cpp_info.set_property("cmake_target_name", "libdvbv5::libdvbv5")
        self.cpp_info.set_property("pkg_config_name", "libdvbv5")
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

    def _prune_non_libdvbv5(self):
        """Remove artefacts installed by the libv4l* subprojects.

        Upstream always builds libv4lconvert/libv4l2/libv4l1/libv4l2rds
        alongside libdvbv5. They are shipped by the `v4l` package, so this
        package keeps only files whose name starts with `libdvbv5` plus the
        `libdvbv5/` header directory.
        """
        keep_prefix = "libdvbv5"
        v4l_prefix = "libv4l"
        for rel_dir in ("lib", "include", "bin", "sbin", "share"):
            base = os.path.join(self.package_folder, rel_dir)
            if not os.path.isdir(base):
                continue
            # Walk the whole subtree so nested locations such as
            # lib/pkgconfig/libv4l2.pc are covered too.
            for root, dirs, files in os.walk(base):
                for name in list(dirs):
                    if name.startswith(v4l_prefix) and not name.startswith(keep_prefix):
                        shutil.rmtree(os.path.join(root, name))
                        dirs.remove(name)
                for name in files:
                    if name.startswith(keep_prefix):
                        continue
                    if not name.startswith(v4l_prefix):
                        continue
                    os.remove(os.path.join(root, name))

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
            version_parts = version.split(".")
            # Meson installs libdvbv5.so.0.0.0, so materialise the SONAME
            # alias libdvbv5.so.0 and the linker alias libdvbv5.so. The
            # intermediate libdvbv5.so.0.0 adds nothing and is skipped.
            aliases = ["{}.so".format(prefix), "{}.so.{}".format(prefix, version_parts[0])]
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
