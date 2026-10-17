#!/usr/bin/env python3
"""Conan recipe — libportal-gtk3 0.10.0 (Meson, GTK3 backend only).

libportal 的 GTK3 后端模块（XDG desktop portal 的 GTK3 集成）。
上游 https://github.com/flatpak/libportal（同仓多后端，meson 选项
backend-gtk3 控制产出）。

OHOS 适配要点：
  - 构建系统: meson (upstream meson.build >= 0.62)
  - 只构建 GTK3 后端：backend-gtk4/qt5/qt6 全 disabled
  - 主库 libportal 在同一源码树内一起编译（meson declare_dependency
    内部 target 依赖，不需要外部 libportal 包参与构建期链接）；
    运行时 libportal-gtk3.so NEEDED libportal.so.1，由
    libportal/0.10.0 requires 提供同源同版本主件（跨账号同链分工，
    本包 package() 阶段剔除主件产物只交付 gtk3 后端）
  - gtk 用 ohpcd 已发布的 broadway 后端 gtk/3.24.43：
    gdkconfig.h 里 GDK_WINDOWING_X11/WAYLAND 均 #undef，上游
    portal-gtk3.c 的 X11/Wayland 分支被条件编译剔除，剩余代码
    （xdp_parent_new_gtk 纯 GObject 逻辑 + g_warning 兜底）无需
    平台补丁即天然兼容 OHOS
  - glib/2.84.0.1 配方未声明 gio-unix 组件 → PkgConfigDeps 不产出
    gio-unix-2.0.pc；上游 meson dependency('gio-unix-2.0') 需要它。
    generate() 从 glib 包内真实 pc 复制并改写 prefix（cpdb-libs 模式）
  - gnome.mkenums 需要 glib-mkenums/glib-genmarshal（glib 包 bin/
    下 python3 脚本，PATH 注入直接可用）；gdbus_codegen 变量经
    wrapper 写入 gio-2.0.pc（accountsservice 模式）
  - introspection/vapi/docs/tests/portal-tests 全关（CI 无
    g-ir-scanner/gi-docgen/pytest-dbusmock 环境）
  - 上游测试：tests/pyportaltest 81 个 pytest 用例需要
    D-Bus session bus + python-dbus + dbusmock + PyGObject，
    CI 离线环境与 OHOS 目标机均无 D-Bus daemon，逐项豁免
    （技术原因+报错原文+本地补跑尝试证据见 PR 正文）
"""
import os
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get, load, save
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibportalGtk3Conan(ConanFile):
    name = "libportal-gtk3"
    version = "0.10.0"
    description = "GTK3 backend of libportal — XDG desktop portal integration for GTK3 applications"
    license = "LGPL-3.0-only"
    homepage = "https://github.com/flatpak/libportal"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # 对齐已发布 ohpcd gtk/3.24.43 binary 树（依赖项 PR #6117 起全
        # shared 链）；顶层声明覆盖避免图中出现 static binary 缺失。
        try:
            self.options["gtk"].shared = True
            self.options["libportal"].shared = True
        except Exception:
            pass

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def requirements(self):
        # gtk3 后端构建期依赖 gtk+-3.0（broadway 后端）与 gio-unix-2.0；
        # 运行期 NEEDED libportal.so.1（主件同版本）。
        self.requires("gtk/3.24.43", transitive_headers=True, transitive_libs=True)
        self.requires("libportal/0.10.0", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        self._create_gio_unix_pc()
        self._augment_glib_pkg_config_tools()
        tc = MesonToolchain(self)
        tc.project_options.update({
            "wrap_mode": "nodownload",
            "default_library": "shared" if self.options.shared else "static",
            "backend-gtk3": "enabled",
            "backend-gtk4": "disabled",
            "backend-qt5": "disabled",
            "backend-qt6": "disabled",
            "introspection": "false",
            "vapi": "false",
            "docs": "false",
            "tests": "false",
            "portal-tests": "false",
        })
        tc.generate()
        self._inject_meson_tools()

    def build(self):
        apply_conandata_patches(self)
        with self._build_environment().vars(self).apply():
            meson = Meson(self)
            meson.configure()
            meson.build()

    def package(self):
        with self._build_environment().vars(self).apply():
            Meson(self).install()
        self._prune_non_gtk3_outputs()
        if self.settings.os == "OHOS":
            if self.options.shared:
                self._create_shared_lib_aliases(os.path.join(self.package_folder, "lib"))
            self._sign_installed_elfs()

    def package_info(self):
        self.cpp_info.libs = ["portal-gtk3"]
        # 上游头文件布局 include/libportal-gtk3/portal-gtk3.h，消费者
        # #include <libportal-gtk3/portal-gtk3.h> → includedirs 为 include
        # 根（与包内 pc 的 Cflags: -I${includedir} 口径一致）。
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("pkg_config_name", "libportal-gtk3")
        self.cpp_info.set_property("cmake_file_name", "libportal-gtk3")
        self.cpp_info.set_property("cmake_target_name", "libportal-gtk3::libportal-gtk3")

    # ── helpers ─────────────────────────────────────────────────────

    def _glib_package_folder(self):
        for dep in self.dependencies.host.values():
            if dep.ref.name == "glib":
                return dep.package_folder
        # gtk 直接依赖树内没有独立 glib 节点时，从 gtk 的依赖里递归找
        return None

    def _create_gio_unix_pc(self):
        """glib 配方未声明 gio-unix 组件，PkgConfigDeps 不产出该 pc。

        从 glib 包内真实 pc 复制并把 prefix=/ 改写为包路径
        （cpdb-libs 已验证模式）。
        """
        glib_package = self._glib_package_folder()
        if not glib_package:
            self.output.warning("glib package not found in graph; skipping gio-unix pc")
            return
        gio_unix_pc = os.path.join(glib_package, "lib", "pkgconfig", "gio-unix-2.0.pc")
        if not os.path.isfile(gio_unix_pc):
            self.output.warning(f"glib package does not provide gio-unix-2.0.pc ({gio_unix_pc})")
            return
        metadata = load(self, gio_unix_pc)
        metadata = metadata.replace("prefix=/\n", "prefix={}\n".format(glib_package), 1)
        save(self, os.path.join(self.generators_folder, "gio-unix-2.0.pc"), metadata)

    def _augment_glib_pkg_config_tools(self):
        """为 glib 系 pc 补齐 meson gnome 模块需要的工具变量。

        gnome.mkenums 通过 glib-2.0.pc 的 glib_mkenums/glib_genmarshal
        变量定位工具；gdbus-codegen 通过 gio-2.0.pc 的 gdbus_codegen。
        工具本体是 glib 包 bin/ 下的 python3 脚本，直接用绝对路径
        wrapper 写入 pc（accountsservice 已验证模式）。
        """
        glib_package = self._glib_package_folder()
        if not glib_package:
            return
        glib_bin = os.path.join(glib_package, "bin")
        needed = ("glib-mkenums", "glib-genmarshal", "gdbus-codegen")
        have = all(os.path.isfile(os.path.join(glib_bin, t)) for t in needed)
        if not have:
            self.output.warning(f"glib build tools missing under {glib_bin}")
            return
        variables = {
            "glib-2.0": [
                f"glib_mkenums={os.path.join(glib_bin, 'glib-mkenums')}",
                f"glib_genmarshal={os.path.join(glib_bin, 'glib-genmarshal')}",
                "gobject_query=${bindir}/gobject-query",
            ],
            "gio-2.0": [
                f"gdbus_codegen={os.path.join(glib_bin, 'gdbus-codegen')}",
            ],
        }
        for pc_name, entries in variables.items():
            pc_file = os.path.join(self.generators_folder, f"{pc_name}.pc")
            if not os.path.isfile(pc_file):
                self.output.warning(f"Could not augment missing {pc_name}.pc")
                continue
            with open(pc_file, encoding="utf-8") as handle:
                content = handle.read()
            inserted = []
            for entry in entries:
                key = entry.split("=", 1)[0] + "="
                if key not in content:
                    inserted.append(entry)
            if inserted:
                addition = "\n" + "\n".join(inserted)
                name_index = content.find("\nName:")
                if name_index >= 0:
                    content = content[:name_index] + addition + content[name_index:]
                else:
                    content = "\n".join(inserted) + "\n" + content
                with open(pc_file, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write(content)

    def _inject_meson_tools(self):
        """补全 meson machine file 的 ar/ranlib/pkg-config 条目。

        OHOS SDK 的 lld 工具链路径在 profile conf 里只声明了 c/cpp，
        meson 交叉机器文件缺 ar/ranlib 时 mkenums 之外的静态归档会
        用错误的 host ar（accountsservice 已验证模式）。
        """
        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            machine_file = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(machine_file):
                continue
            compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
            cc = compilers.get("c") or ""
            bindir = os.path.dirname(cc) if cc and os.path.sep in cc else ""
            ar = compilers.get("ar")
            ranlib = compilers.get("ranlib")
            for directory in (bindir, "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/bin"):
                if not ar:
                    candidate = os.path.join(directory, "llvm-ar")
                    if os.path.isfile(candidate):
                        ar = candidate
                if not ranlib:
                    candidate = os.path.join(directory, "llvm-ranlib")
                    if os.path.isfile(candidate):
                        ranlib = candidate
            with open(machine_file, encoding="utf-8") as handle:
                content = handle.read()
            if "[binaries]" not in content:
                continue
            insert = []
            if ar and "\nar =" not in content:
                insert.append(f"ar = '{ar}'")
            if ranlib and "\nranlib =" not in content:
                insert.append(f"ranlib = '{ranlib}'")
            if insert:
                lines = content.splitlines(keepends=True)
                for index, line in enumerate(lines):
                    if line.strip() == "[binaries]":
                        lines[index] = line + "\n".join(insert) + "\n"
                        break
                with open(machine_file, "w", encoding="utf-8", newline="\n") as handle:
                    handle.write("".join(lines))

    def _build_environment(self):
        """为主机端 meson 构建注入 glib 构建工具与运行库搜索路径。"""
        env = Environment()
        tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp, exist_ok=True)
        env.define_path("TMPDIR", tmp)
        env.define_path("TMP", tmp)
        env.define_path("TEMP", tmp)
        glib_package = self._glib_package_folder()
        if glib_package:
            env.prepend_path("PATH", os.path.join(glib_package, "bin"))
        for dep in self.dependencies.host.values():
            for libdir in dep.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dep.package_folder, libdir)
                if os.path.isdir(libdir):
                    env.prepend_path("LD_LIBRARY_PATH", libdir)
        user_bin = os.path.join(os.path.expanduser("~"), ".local", "bin")
        if os.path.isdir(user_bin):
            env.prepend_path("PATH", user_bin)
        return env

    def _prune_non_gtk3_outputs(self):
        """本件只交付 gtk3 后端：剔除 meson 同时安装出的主件产物。

        源码树内一起构建的主库 libportal.so 与公共头由 libportal/0.10.0
        主件包交付（跨账号同链分工），本包 lib/ 下出现的 libportal.so*、
        libportal.pc 与 include/libportal/（主件公共头）一律剔除，
        避免与主件包冲突（R26 同名库隔离口径）。
        """
        lib = os.path.join(self.package_folder, "lib")
        pkg = os.path.join(lib, "pkgconfig")
        inc = os.path.join(self.package_folder, "include")
        if os.path.isdir(lib):
            for name in os.listdir(lib):
                if name.startswith("libportal.so") or name == "libportal.a":
                    os.remove(os.path.join(lib, name))
                    self.output.info(f"pruned main-library artifact: {name}")
        if os.path.isdir(pkg):
            for name in os.listdir(pkg):
                if name == "libportal.pc":
                    os.remove(os.path.join(pkg, name))
                    self.output.info("pruned main-library pc file")
        main_inc = os.path.join(inc, "libportal")
        if os.path.isdir(main_inc):
            shutil.rmtree(main_inc)
            self.output.info("pruned main-library headers include/libportal/")

    def _create_shared_lib_aliases(self, libdir):
        """dev so 别名用真拷贝（gtk 配方同款，比 symlink 更稳，规避 HMDFS 限制）。"""
        base = "libportal-gtk3.so"
        real = os.path.join(libdir, f"{base}.1.0.0")
        if not os.path.isfile(real):
            return
        for name in (f"{base}.1", base):
            alias = os.path.join(libdir, name)
            if os.path.lexists(alias):
                os.unlink(alias)
            shutil.copyfile(real, alias)

    def _sign_installed_elfs(self):
        """OHOS 要求产物 ELF 签名后才可执行/加载（gtk 配方同款口径）。"""
        import glob as _glob
        import shlex
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool not found; skip signing")
            return
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = ce.get("c") or ""
        candidates = [shutil.which("llvm-objcopy")]
        if cc and os.path.sep in cc:
            candidates.insert(0, os.path.join(os.path.dirname(cc), "llvm-objcopy"))
        objcopy = next((p for p in candidates if p and os.path.isfile(p)), None)
        patterns = [
            os.path.join(self.package_folder, "bin", "*"),
            os.path.join(self.package_folder, "lib", "**", "*.so"),
            os.path.join(self.package_folder, "lib", "**", "*.so.*"),
        ]
        cands = []
        for pat in patterns:
            cands.extend(_glob.glob(pat, recursive=True))
        for binary in sorted(set(cands)):
            if not os.path.isfile(binary) or os.path.islink(binary):
                continue
            if objcopy:
                self.run(f"{shlex.quote(objcopy)} --remove-section .codesign {shlex.quote(binary)} 2>/dev/null || true")
            self.run(shlex.join([signer, "sign", "-inFile", binary, "-outFile", binary, "-selfSign", "1"]))
