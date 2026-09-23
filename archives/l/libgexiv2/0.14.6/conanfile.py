#!/usr/bin/env python3
"""Conan recipe — libgexiv2 0.14.6 (Meson).

libgexiv2（上游项目名 gexiv2）是 Exiv2 的 GObject 封装：C++ 实现（gexiv2/ 下 10 个 .cpp），对外提供
C ABI + GObject 绑定。上游 meson.build 的直接依赖只有两项：

  exiv2       >= 0.26     dependency('exiv2')，经 pkg-config 解析
  gobject-2.0 >= 2.46.0   ┐ 同一个 glib 包的两个 pkg-config 模块
  gio-2.0     >= 2.46.0   ┘

meson_options.txt 的可选特性（上游默认值）：
  introspection=true, vapi=true, python3=true, tools=true,
  tests=false, gtk_doc=false

HarmonyOS PC 适配策略（判据见 notes.md）：
  * introspection/vapi/python3/tools 一律关闭。这四个特性都由上游
    `find_program('g-ir-scanner')` 驱动；提供 g-ir-scanner 的唯一包是
    gobject-introspection/1.78.1.1，而它的强制版本闭包（glib/2.84.0.1、
    python/3.12.9 在 `force=True` 的 zlib/1.3.1.1.1.1 + libffi/3.5.2 下）
    在 ohpcd 制品仓没有已发布二进制 —— 属于 R36 依赖阻塞，不允许用
    `--build=missing` 或本地缓存绕过。同仓先例：gupnp-av/0.14.5、
    gdk-pixbuf/2.44.6 同样关闭 introspection。
  * gtk_doc 上游默认 false（且制品仓无 gtk-doc），保持关闭。
  * tests 强制打开：上游 test/ 目录产出 gexiv2-regression（C 回归套件），
    build() 内实际执行 `meson test`，作为适配后的上游测试证据。
"""
import glob
import os
import re
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run, cross_building
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class Gexiv2Conan(ConanFile):
    name = "libgexiv2"
    version = "0.14.6"
    description = "GObject-based wrapper around the Exiv2 library"
    license = "GPL-2.0-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/gexiv2"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    generators = "VirtualBuildEnv", "VirtualRunEnv"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        # R32: OHOS 归入 Linux 家族，不能用 == "Linux"
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"gexiv2 is only supported on Linux/OHOS, not {self.settings.os}"
            )

    def requirements(self):
        # 上游 meson.build:20 exiv2 >= 0.26；ohpcd 仅有 0.28.7，满足约束。
        self.requires("exiv2/0.28.7", transitive_headers=True, transitive_libs=True)
        # 上游 meson.build:28-29 gobject-2.0/gio-2.0 >= 2.46.0 —— 同一 glib 包。
        # glib/2.84.0.1 与 exiv2 共享 zlib/1.3.1.1（glib/2.88.x 会要求
        # zlib/1.3.2/1.3.1，与 exiv2 钉死的 zlib/1.3.1.1 冲突，见 notes.md）。
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)

    def build_requirements(self):
        # 上游 meson.build:6 meson_version >= 0.56；仓库 meson 惯例版本。
        self.tool_requires("meson/1.11.0")
        self.tool_requires("ninja/1.12.1")
        self.tool_requires("pkgconf/3.0.5")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        toolchain = MesonToolchain(self)
        toolchain.project_options.update(
            {
                "wrap_mode": "nodownload",
                "default_library": "shared" if self.options.shared else "static",
                # 见文件头注释：g-ir-scanner 依赖闭包不完整（R36），
                # 上游 introspection/vapi/python3 三个开关必须同时关闭。
                "introspection": "false",
                "vapi": "false",
                "python3": "false",
                "tools": "false",
                "gtk_doc": "false",
                # 上游默认 false；这里打开以便 build() 里实际跑上游测试。
                "tests": "true",
            }
        )
        toolchain.generate()
        self._inject_meson_binaries()
        self._append_dependency_pkg_config_paths()
        self._augment_glib_pkg_config()
        sdk_llvm_lib = self._sdk_llvm_libdir()
        if sdk_llvm_lib:
            # OHOS SDK 的 lld 动态依赖 llvm/lib/libxml2.so.16；构建机
            # （AppSpawn 沙箱）默认搜索路径里没有该目录，链接/探测子进程会
            # 报 "Error loading shared library libxml2.so.16"（E120 变体）。
            self.buildenv_info.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)

    def build(self):
        apply_conandata_patches(self)
        with self._build_environment().vars(self).apply():
            meson = Meson(self)
            meson.configure()
            meson.build()
            if not cross_building(self) and can_run(self):
                meson.test()

    def package(self):
        with self._build_environment().vars(self).apply():
            Meson(self).install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        for la in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(la)
        if self.settings.os == "OHOS":
            self._create_shared_lib_aliases(
                os.path.join(self.package_folder, "lib"))
            self._sign_installed_elfs()

    def package_info(self):
        self.cpp_info.libs = ["gexiv2"]
        # 上游 install_headers(..., subdir: 'gexiv2')；库内头文件相互包含用
        # 相对路径，故 include 根目录即 `${prefix}/include`。
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        self.cpp_info.requires = ["exiv2::exiv2", "glib::glib-2.0", "glib::gobject-2.0", "glib::gio-2.0"]
        self.cpp_info.set_property("cmake_file_name", "gexiv2")
        self.cpp_info.set_property("cmake_target_name", "gexiv2::gexiv2")
        self.cpp_info.set_property("pkg_config_name", "gexiv2")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "dl", "pthread"]

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _sdk_llvm_libdir(self):
        import glob as _glob
        for d in reversed(sorted(_glob.glob(
                "/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib"))):
            if os.path.isdir(d):
                return d
        return None

    def _build_environment(self):
        environment = Environment()
        tmpdir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmpdir, exist_ok=True)
        environment.define_path("TMPDIR", tmpdir)
        environment.define_path("TMP", tmpdir)
        environment.define_path("TEMP", tmpdir)
        # meson 用裸名 `ninja` 探测后端；OHOS 上 subprocess 裸名解析不可靠，
        # 显式给绝对路径（meson tooldetect 优先读 NINJA 环境变量）。
        ninja = os.environ.get("NINJA") or shutil.which("ninja")
        if ninja and os.path.isfile(ninja):
            environment.define_path("NINJA", ninja)
        if os.environ.get("LD_LIBRARY_PATH"):
            environment.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        else:
            environment.define_path("LD_LIBRARY_PATH", "/system/lib64")
        for dependency in self.dependencies.host.values():
            bin_dir = os.path.join(dependency.package_folder, "bin")
            if os.path.isdir(bin_dir):
                environment.prepend_path("PATH", bin_dir)
            for libdir in dependency.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dependency.package_folder, libdir)
                if os.path.isdir(libdir):
                    environment.prepend_path("LD_LIBRARY_PATH", libdir)
        # 上游 C 回归测试通过 link_with/共享库运行，需要能 dlopen 刚构建的
        # libgexiv2.so（meson 的 LD_LIBRARY_PATH 只覆盖 build 目录）。
        environment.prepend_path("LD_LIBRARY_PATH", os.path.join(self.build_folder, "gexiv2"))
        return environment

    @staticmethod
    def _create_shared_lib_aliases(libdir):
        """OHOS: 把 soname 符号链接换成真实文件。

        HMDFS 上 symlink 的 soname 解析不稳定；gdk-pixbuf/2.44.6 同款处理
        （用 copyfile 生成 libgexiv2.so.2 / libgexiv2.so 实体）。
        """
        versioned = sorted(
            path for path in glob.glob(os.path.join(libdir, "libgexiv2.so.*.*.*"))
            if os.path.isfile(path) and not os.path.islink(path))
        if not versioned:
            raise FileNotFoundError(
                f"Versioned gexiv2 shared library missing in {libdir}")
        source = versioned[-1]
        for name in ("libgexiv2.so.2", "libgexiv2.so"):
            alias = os.path.join(libdir, name)
            if os.path.lexists(alias):
                os.unlink(alias)
            shutil.copyfile(source, alias)

    def _sign_installed_elfs(self):
        """OHOS: 安装后的 .so 必须签名，否则动态加载器直接拒载。

        实测（本机 OHOS aarch64）：meson install 落地后未签名的
        libgexiv2.so.2.14.6 被 `ctypes.CDLL()` 拒绝：
          OSError: Error loading shared library libgexiv2.so.2.14.6:
                   Permission denied
        用 `binary-sign-tool sign -selfSign 1` 原地签名后即可正常加载。
        同款先例：archives/g/gdk-pixbuf/2.44.6 package() → _sign_installed_elfs。
        """
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            raise FileNotFoundError(
                f"HarmonyOS binary signer is missing: {signer}")
        targets = []
        for directory in ("lib", "bin"):
            root = os.path.join(self.package_folder, directory)
            if not os.path.isdir(root):
                continue
            for name in sorted(os.listdir(root)):
                path = os.path.join(root, name)
                if not os.path.isfile(path) or os.path.islink(path):
                    continue
                with open(path, "rb") as handle:
                    if handle.read(4) != b"\x7fELF":
                        continue
                targets.append(path)
        for path in targets:
            self.run(shlex.join([signer, "sign", "-inFile", path,
                                 "-outFile", path, "-selfSign", "1"]))
        self.output.info(f"libgexiv2: signed {len(targets)} ELF file(s) for OHOS")

    def _augment_glib_pkg_config(self):
        """把 glib 的 pkg-config 自定义变量补进 Conan 生成的 glib-2.0.pc。

        gexiv2/meson.build:36 的 `gnome.mkenums()` 会向 glib-2.0 依赖索取
        `glib_mkenums` 变量来定位 glib-mkenums 程序。PkgConfigDeps 生成的
        glib-2.0.pc 只有标准字段（prefix/libdir/includedir*/bindir），
        meson 直接报：
          ERROR: Could not get pkg-config variable and no default provided
                 for <PkgConfigDependency glib-2.0>
        glib 包自带的 lib/pkgconfig/glib-2.0.pc 里这两个变量是
        ${bindir}/glib-{mkenums,genmarshal}；这里按包内绝对路径补回
        （同 archives/g/gupnp-av/0.14.5、archives/a/atk/2.38.0.1.1 的先例）。
        """
        pc_file = os.path.join(self.generators_folder, "glib-2.0.pc")
        if not os.path.isfile(pc_file):
            self.output.warning("glib-2.0.pc not found in generators folder")
            return
        entries = []
        for tool in ("glib-mkenums", "glib-genmarshal"):
            for dependency in self.dependencies.host.values():
                candidate = os.path.join(dependency.package_folder, "bin", tool)
                if os.path.isfile(candidate):
                    entries.append("{}={}".format(
                        tool.replace("-", "_"), candidate.replace("\\", "/")))
                    break
        if not entries:
            return
        with open(pc_file, encoding="utf-8") as handle:
            content = handle.read()
        missing = [e for e in entries
                   if e.split("=", 1)[0] + "=" not in content]
        if not missing:
            return
        addition = "\n" + "\n".join(missing)
        index = content.find("\nName:")
        if index >= 0:
            content = content[:index] + addition + content[index:]
        else:
            content = addition + "\n" + content
        with open(pc_file, "w", encoding="utf-8") as handle:
            handle.write(content)
        self.output.info("glib-2.0.pc augmented with: %s" % ", ".join(missing))

    def _append_dependency_pkg_config_paths(self):
        # MesonToolchain 的 native file 只把 generators 目录写进
        # pkg_config_path；依赖包自带的 .pc（如 exiv2 由 PkgConfigDeps 生成，
        # 但 glib 的 gio-2.0.pc 等在包内 lib/pkgconfig）需显式追加。
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not os.path.isfile(native_file):
            return
        paths = [self.generators_folder]
        for dependency in self.dependencies.host.values():
            for relative in (("lib", "pkgconfig"), ("share", "pkgconfig")):
                candidate = os.path.join(dependency.package_folder, *relative)
                if os.path.isdir(candidate):
                    paths.append(candidate)
        unique = []
        for path in paths:
            normalized = path.replace("\\", "/")
            if normalized not in unique:
                unique.append(normalized)
        with open(native_file, encoding="utf-8") as handle:
            lines = handle.read().splitlines()
        replacement = "pkg_config_path = [" + ", ".join(
            "'{}'".format(p) for p in unique) + "]"
        for index, line in enumerate(lines):
            if line.startswith("pkg_config_path = "):
                lines[index] = replacement
                break
        else:
            lines.append(replacement)
        with open(native_file, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")

    def _inject_meson_binaries(self):
        # MesonToolchain 不写 ar/ranlib/pkg-config；OHOS 工具链在
        # /data/service/hnp/bin，PATH 上无裸名 llvm-ar 时 meson configure 失败。
        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            machine_file = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(machine_file):
                continue
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict) or {}
            cc = compilers.get("c") or ""
            bindir = os.path.dirname(cc) if cc and os.path.sep in cc else ""
            ar = compilers.get("ar")
            ranlib = compilers.get("ranlib")
            for directory in (bindir, "/data/service/hnp/bin"):
                if not directory:
                    continue
                if not ar:
                    candidate = os.path.join(directory, "llvm-ar")
                    if os.path.isfile(candidate):
                        ar = candidate
                if not ranlib:
                    candidate = os.path.join(directory, "llvm-ranlib")
                    if os.path.isfile(candidate):
                        ranlib = candidate
            pkg_config = self.conf.get("tools.gnu:pkg_config", default=None)
            if not pkg_config or not os.path.isfile(str(pkg_config)):
                pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")
            with open(machine_file, encoding="utf-8") as handle:
                content = handle.read()
            if "[binaries]" not in content:
                continue
            insert = []
            if ar and not re.search(r"^ar\s*=", content, flags=re.M):
                insert.append(f"ar = '{ar}'")
            if ranlib and not re.search(r"^ranlib\s*=", content, flags=re.M):
                insert.append(f"ranlib = '{ranlib}'")
            if pkg_config and not re.search(r"^pkg-?config\s*=", content, flags=re.M):
                insert.append(f"pkg-config = '{pkg_config}'")
            if insert:
                content = content.replace(
                    "[binaries]\n", "[binaries]\n" + "\n".join(insert) + "\n", 1)
                with open(machine_file, "w", encoding="utf-8") as handle:
                    handle.write(content)
