#!/usr/bin/env python3
"""Conan recipe — libnma-gtk4 1.10.6 (Meson, GTK4 variant of libnma).

libnma 的 GTK4 变体拆分包（NetworkManager UI utilities，gtk4 版）。
上游 https://gitcode.com/GNOME/libnma 官方 release tarball 同源构建，
meson 选项 libnma_gtk4=true 控制产出 libnma-gtk4.so。

OHOS 适配要点：
  - 构建系统: meson (upstream meson_version >= 0.46)
  - 源码用 GNOME 官方 release tarball（非 GitHub tag archive）：
    dist tarball 自带 src/libnma-gtk4/ 下 17 个预转换的 Gtk4 .ui 文件
    （上游 Makefile.am EXTRA_DIST 清单），meson 检测到该目录后走
    "dist 已含 gtk4 数据" 分支，构建期无需运行 gtk4-builder-tool
    （GitHub tag archive 缺该目录，会改走 generator 在线 3to4 转换，
    依赖构建机 PATH 上有可执行的 gtk4-builder-tool——OHOS 需签名才
    能执行，官方 dist tarball 从根上绕开此问题）
  - 本件是 gtk4 变体拆分包（libportal-gtk3/gtk4 同款拆分模式：姊妹件
    libnma 1.10.6 本体在途 #8298，本件只交付 gtk4 变体）。上游 meson
    无条件探测 gtk+-3.0 并构建 gtk3 主库——补丁 0001 新增 libnma_gtk3
    选项，false 时跳过 gtk+-3.0 探测与主库构建，共享基础设施
    （utils-libnm/gir_sources/tests）改用 gtk4 头编译（源码
    GTK_CHECK_VERSION(4,0,0) 双兼容分支），图上只留 gtk4 单链
  - libnm 硬依赖切换到 libnm/1.58.0（NetworkManager 客户端库）。
    制品仓实况：libnm/1.58.0 归档为【知识库扩展】件（main 09-21 合入）
    不发布制品，registry 仅有 libnm/1.58.0（#14301 networkmanager-qt
    同款依赖）——本件直接 requires libnm/1.58.0
  - gtk4 用 ohpcd 已发布的 broadway 后端 gtk4/4.22.4：上游
    libnma-gtk4 代码对 X11/Wayland 无直接依赖（ gdkconfig.h 里
    GDK_WINDOWING_X11/WAYLAND 均 #undef 时相关分支自然剔除），
    nma-wifi-dialog.c/nma-cert-chooser.c 等带 GTK_CHECK_VERSION(4,0,0)
    条件分支，gtk4 头下走 gtk4 专用代码路径，无需平台补丁
  - gcr=false：ohpcd 未发布 gcr-4/gck-2（gcr-base/3.41.2 只有 gcr-base-3
    /gck-1 pc 名），pkcs11_sources（nma-pkcs11-cert-chooser-dialog.c 等
    硬依赖 gck/gcr 头）在 enable_gcr=false 时整个不参与编译，
    nma-cert-chooser.c 的 #ifdef GCK stub 分支天然兼容
  - iso_codes=false / mobile_broadband_provider_info=false：两者仅影响
    config.h 里的数据目录宏（fallback 到 prefix 内相对路径），不影响
    编译产物
  - glib 系 pc 的工具变量（glib_mkenums/glib_genmarshal/gdbus_codegen）
    由 glib 包 bin/ 下的脚本以绝对路径注入 pc（accountsservice 模式）
  - gtk4/4.22.4 recipe 以 override 统一 glib 到 2.84.0.1.1；libnm/1.58.0
    requires glib/2.84.0.1——本件顶层用 override 统一声明
    glib/2.84.0.1.1（与 gtk4 recipe 的 override 同款），图上两链统一到
    gtk4 链（libnm.so 的 soname 兼容性不受 glib 小版本影响）
  - introspection/vapi/gtk_doc 全关（CI 无 g-ir-scanner/gtk-doc 环境）；
    gettext 部分（subdir po）由 gettext/0.22.5.1 tool_requires 提供
    msgfmt/msgmerge
  - 上游测试：meson 注册 test() 共 1 例（src/utils 的 test-utils，
    纯数据函数单测，链接 utils-libnm 静态库）；src/tests 下 8 个示例
    可执行（bar-code/cert-chooser/mobile-wizard/run-vpn/
    vpn-password-dialog/wifi-dialog/wifi-dialog-secrets/ws）只是
    executable() 不注册 test()，gtk4 启用后再各生成 8 个 -gtk4 示例
    可执行（同样不注册）。test-utils 真跑（R51 口径），示例可执行
    构建通过即编译级验证
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, load, save
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibnmaGtk4Conan(ConanFile):
    name = "libnma-gtk4"
    version = "1.10.6"
    description = "GTK4 variant of libnma — NetworkManager UI utilities (wifi dialogs, EAP/WS editors, mobile wizard) for GTK4 applications"
    license = "GPL-2.0-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/libnma"
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
        # 对齐已发布 ohpcd gtk4/4.22.4 binary 树（glib/2.84.0.1.1
        # shared 全链）；顶层声明覆盖避免图中出现 static binary 缺失。
        try:
            self.options["gtk4"].shared = True
            self.options["libnm"].shared = True
        except Exception:
            pass

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def build_requirements(self):
        # meson 上游主构建系统；pkgconf 提供 meson 用的 pkg-config。
        self.tool_requires("meson/1.11.0")
        self.tool_requires("pkgconf/3.0.5")
        # subdir('po') → i18n.gettext 需要 msgfmt/msgmerge（OHOS 系统
        # 只有 /data/service/hnp/bin/msgfmt 无 msgmerge，gettext 工具包
        # 双全，avahi-glib/ayatana-indicator-notifications 同款）。
        self.tool_requires("gettext/0.22.5.1")

    def requirements(self):
        # 上游 meson.build:178 无条件 dependency('libnm', version: '>= 1.7')
        # ——gtk4 变体也链接 libnm（NMConnection/NMSetting* API）。已发布的
        # libnm/1.58.0（NetworkManager 客户端库）提供，glib 2.84.0.1 链。
        #
        # 依赖图两链统一（gtk4 件特有，libportal-gtk4 同款问题）：
        #   libnm/1.58.0 requires glib/2.84.0.1 + libudev-zero/uuid/gnutls；
        #   gtk4/4.22.4 requires glib/2.84.0.1.1（override 链统一到 shared）。
        #   两链在 conan 图上 glib 版本冲突。统一方向：gtk4 链胜出（顶层
        #   override 声明 glib/2.84.0.1.1，gtk4 recipe 同款写法）。libnm.so
        #   与 glib 小版本（2.84.0.1 vs 2.84.0.1.1）二进制兼容——同 2.84 ABI，
        #   .1.1 是适配修复后缀（R37 版本号策略），soname 不变
        #   （libglib-2.0.so.0），libnm.so 的 NEEDED 在制品仓发布后由
        #   conan 图解析统一。
        # glib 全图统一：libnm 链 glib/2.84.0.1、gtk4 链 glib/2.84.0.1.1
        # （override）——统一到 2.84.0.1.1（同 2.84 ABI，.1.1 是适配修复
        # 后缀，soname libglib-2.0.so.0 不变，两链 binary 均兼容）。
        self.requires("glib/2.84.0.1.1", options={"shared": True}, override=True)
        # zlib/fontconfig 图级冲突统一（gtk4 recipe 同款）。
        self.requires("zlib/1.3.1.1", override=True)
        self.requires("fontconfig/2.18.1.1", override=True)
        # 注意：pango/cairo-gobject/harfbuzz/gdk-pixbuf 不做 override——
        # 图上只有 gtk4 一条 UI 链（libnma_gtk3=false 补丁跳过 gtk3 探测），
        # 各依赖直接沿用 gtk4 recipe 的版本 pin，binary 均从缓存/制品仓取。
        self.requires("gtk4/4.22.4", transitive_headers=True, transitive_libs=True)
        self.requires("libnm/1.58.0", transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # 桥接必须先于 PkgConfigDeps：组件引用是 generate() 内延迟解析的。
        self._bridge_glib_component_names()
        PkgConfigDeps(self).generate()
        self._create_gio_unix_pc()
        self._create_gmodule_export_pc()
        self._augment_glib_pkg_config_tools()
        self._alias_libnm_pc()
        tc = MesonToolchain(self)
        tc.project_options.update({
            "wrap_mode": "nodownload",
            "default_library": "shared" if self.options.shared else "static",
            # ── 只产出 gtk4 变体需要的面 ──
            # libnma_gtk3=false（补丁新增选项）：跳过 gtk+-3.0 探测与主库
            # 构建，共享基础设施（utils-libnm/gir_sources/tests）改用 gtk4
            # 头编译（源码 GTK_CHECK_VERSION(4,0,0) 双兼容分支）。图上只留
            # gtk4 链（pango 1.56 系），不拖入 gtk3 链（pango 1.50 系）——
            # conan 图同名包版本冲突与 gtk3 binary 失配问题从根上消除。
            "libnma_gtk3": "false",
            "libnma_gtk4": "true",
            "gcr": "false",
            "iso_codes": "false",
            "mobile_broadband_provider_info": "false",
            "ld_gc": "false",
            "gtk_doc": "false",
            "introspection": "false",
            "vapi": "false",
        })
        tc.generate()
        self._inject_meson_tools()
        self._append_dependency_pkg_config_paths()

    def _dependency_pkg_config_dirs(self):
        """收集所有 host 依赖包内的真实 pkgconfig 目录（glib 包内带
        gio-unix-2.0.pc/gmodule-export-2.0.pc/gmodule-no-export-2.0.pc
        等 PkgConfigDeps 不产出的 pc——glib recipe 未声明这些组件）。"""
        paths = []
        for dependency in self.dependencies.host.values():
            for relative in (("lib", "pkgconfig"), ("share", "pkgconfig")):
                candidate = os.path.join(dependency.package_folder, *relative)
                if os.path.isdir(candidate):
                    paths.append(candidate.replace("\\", "/"))
        return paths

    def _append_dependency_pkg_config_paths(self):
        """把依赖包内真实 pc 目录追加进 meson native file 的
        pkg_config_path（libnm 1.58.0 已验证模式——meson.build:176
        硬依赖 gmodule-export-2.0，其 Requires 链 gmodule-no-export-2.0
        只有 glib 包内 pc 提供）。"""
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not os.path.isfile(native_file):
            return
        paths = [self.generators_folder.replace("\\", "/")]
        paths.extend(self._dependency_pkg_config_dirs())
        unique_paths = []
        for path in paths:
            if path not in unique_paths:
                unique_paths.append(path)
        replacement = "pkg_config_path = [" + ", ".join("'{}'".format(p) for p in unique_paths) + "]"
        with open(native_file, encoding="utf-8") as handle:
            content = handle.read()
        lines = content.splitlines()
        for index, line in enumerate(lines):
            if line.startswith("pkg_config_path = "):
                lines[index] = replacement
                break
        else:
            lines.append(replacement)
        with open(native_file, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")

    def build(self):
        apply_conandata_patches(self)
        with self._build_environment().vars(self).apply():
            meson = Meson(self)
            meson.configure()
            meson.build()
            self._run_upstream_tests()

    def package(self):
        with self._build_environment().vars(self).apply():
            Meson(self).install()
        self._prune_non_gtk4_outputs()
        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        if self.settings.os == "OHOS":
            if self.options.shared:
                self._create_shared_lib_aliases(os.path.join(self.package_folder, "lib"))
            self._sign_installed_elfs()

    def package_info(self):
        self.cpp_info.libs = ["nma-gtk4"]
        # 上游头文件布局 include/libnma/nma-wifi-dialog.h；上游 pc 的
        # Cflags: -I${includedir}/libnma（无前缀拼法），conan 侧声明
        # includedirs=["include"]（消费者 #include <libnma/nma-wifi-dialog.h>
        # 带前缀拼法，与本体包 libnma/1.10.6（在途 #8298，同布局）形成
        # 显式二选一——变体拆分包语义）。CMake 消费者通过 CMakeDeps 的
        # target_include_directories 自动获得 include 根。
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("pkg_config_name", "libnma-gtk4")
        self.cpp_info.set_property("cmake_file_name", "libnma-gtk4")
        self.cpp_info.set_property("cmake_target_name", "libnma-gtk4::libnma-gtk4")
        # 不声明 cpp_info.requires：libnma-gtk4.so 的运行期依赖链全部由
        # libnm/1.58.0 的 pc（Requires: gio-2.0）与 gtk4 传递给消费者；
        # 上游 libnma-gtk4.pc 也只 requires: 'libnm'。conan 的组件校验
        # （check_component_requires）要求 cpp_info.requires 覆盖全部
        # 直接依赖且 override 依赖不能进组件表——glib 是 override 统一
        # 声明（非直接依赖），gtk4 的组件由 PkgConfigDeps 从 pc 链自动
        # 生成，无需在此重复（libportal-gtk4 同款口径）。

    # ── helpers ─────────────────────────────────────────────────────

    def _glib_package_folder(self):
        for dep in self.dependencies.host.values():
            if dep.ref.name == "glib":
                return dep.package_folder
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

    def _create_gmodule_export_pc(self):
        """上游 meson.build:176 无条件 dependency('gmodule-export-2.0')。

        glib 配方未声明 gmodule-export 组件，PkgConfigDeps 不产出该 pc。
        从 glib 包内真实 pc 复制并把 prefix=/ 改写为包路径（gio-unix 同款
        模式；Requires: gmodule-no-export-2.0, glib-2.0 在同一目录内由
        PkgConfigDeps 产出的 glib-2.0.pc/gmodule-no-export-2.0.pc 接管，
        pkg-config 按搜索路径解析）。
        """
        glib_package = self._glib_package_folder()
        if not glib_package:
            self.output.warning("glib package not found in graph; skipping gmodule-export pc")
            return
        src_pc = os.path.join(glib_package, "lib", "pkgconfig", "gmodule-export-2.0.pc")
        if not os.path.isfile(src_pc):
            self.output.warning(f"glib package does not provide gmodule-export-2.0.pc ({src_pc})")
            return
        metadata = load(self, src_pc)
        metadata = metadata.replace("prefix=/\n", "prefix={}\n".format(glib_package), 1)
        # Requires 里指向的同目录 pc 由 PkgConfigDeps 已生成（glib-2.0.pc
        # 等），保留依赖声明即可；改写后 includedir/libdir 落在包内。
        save(self, os.path.join(self.generators_folder, "gmodule-export-2.0.pc"), metadata)

    def _augment_glib_pkg_config_tools(self):
        """为 glib 系 pc 补齐 meson gnome 模块需要的工具变量。

        gnome.mkenums 通过 glib-2.0.pc 的 glib_mkenums/glib_genmarshal
        变量定位工具；gdbus-codegen 通过 gio-2.0.pc 的 gdbus_codegen；
        gnome.compile_resources 通过 gio-2.0.pc 的 glib_compile_resources。

        glib 包 bin/ 下的 ELF 工具无 RPATH，ninja custom command 环境
        下直接执行报 "Error loading shared library libgio-2.0.so.0"——
        工具变量一律指向 shell wrapper（wrapper 注入 glib 包 lib/ 的
        LD_LIBRARY_PATH，libnm 配方 _create_python_tool_wrapper 同款
        模式；gdbus-codegen 是 python 脚本本体，wrapper 同样适用）。
        """
        glib_package = self._glib_package_folder()
        if not glib_package:
            return
        glib_bin = os.path.join(glib_package, "bin")
        glib_lib = os.path.join(glib_package, "lib")
        tools = ("glib-mkenums", "glib-genmarshal", "gdbus-codegen",
                 "glib-compile-resources")
        have = all(os.path.isfile(os.path.join(glib_bin, t)) for t in tools)
        if not have:
            self.output.warning(f"glib build tools missing under {glib_bin}")
            return

        def _wrapper(tool):
            import shlex
            path = os.path.join(glib_bin, tool)
            target = path
            # OHOS: unsigned host ELF cannot exec (EPERM -> ninja code=126).
            # glib-compile-resources is an ELF; glib-mkenums/glib-genmarshal/
            # gdbus-codegen are python scripts run via interpreter (no sign).
            # Copy ELF into build tree, self-sign, exec the signed copy
            # (gap 4.16.0 same approach).
            with open(path, "rb") as probe:
                is_elf = probe.read(4) == b"\x7fELF"
            if is_elf:
                signer = "/data/service/hnp/bin/binary-sign-tool"
                objcopy = shutil.which("llvm-objcopy")
                if not objcopy or not os.path.isfile(objcopy):
                    objcopy = "/data/service/hnp/bin/llvm-objcopy"
                if os.path.isfile(signer):
                    signed_dir = os.path.join(self.generators_folder, "signed-host-tools")
                    os.makedirs(signed_dir, exist_ok=True)
                    target = os.path.join(signed_dir, tool)
                    shutil.copyfile(path, target)
                    os.chmod(target, 0o755)
                    if os.path.isfile(objcopy):
                        self.run(f"{shlex.quote(objcopy)} --remove-section .codesign {shlex.quote(target)} 2>/dev/null || true")
                    self.run(shlex.join([signer, "sign", "-inFile", target, "-outFile", target, "-selfSign", "1"]))
            wrapper = os.path.join(self.generators_folder, f"{tool}-wrap")
            with open(wrapper, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(
                    "#!/data/service/hnp/bin/bash\n"
                    f'export LD_LIBRARY_PATH="{glib_lib}:$LD_LIBRARY_PATH"\n'
                    f'exec "{target}" "$@"\n'
                )
            os.chmod(wrapper, 0o755)
            return wrapper

        wrapped = {t: _wrapper(t) for t in tools}
        variables = {
            "glib-2.0": [
                f"glib_mkenums={wrapped['glib-mkenums']}",
                f"glib_genmarshal={wrapped['glib-genmarshal']}",
                "gobject_query=${bindir}/gobject-query",
            ],
            "gio-2.0": [
                f"gdbus_codegen={wrapped['gdbus-codegen']}",
                f"glib_compile_resources={wrapped['glib-compile-resources']}",
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

    def _alias_libnm_pc(self):
        """libnm/1.58.0 配方 pkg_config_name=libnm（PkgConfigDeps 直接
        产出 libnm.pc），本方法核对存在性——上游 meson 硬要求
        dependency('libnm')，缺失则显式告警（libnm 已发布无需改写）。"""
        pc_file = os.path.join(self.generators_folder, "libnm.pc")
        if not os.path.isfile(pc_file):
            self.output.warning("libnm.pc not generated by PkgConfigDeps")
        else:
            self.output.info("libnm.pc present (from libnm/1.58.0 package)")

    def _bridge_glib_component_names(self):
        """glib 组件名代际桥接（gtk4×libnm 混链图特有）。

        libnm/1.58.0 的 cpp_info.requires 按 glib/2.88.3+ 的新组件名引用
        （glib::glib/gobject/gio/gmodule）；本图 override 钉住
        glib/2.84.0.1.1（gtk4/4.22.4 recipe 同款 pin，旧组件名带 -2.0
        后缀）——PkgConfigDeps 延迟解析组件引用时报
        "Component 'glib::gobject' not found in 'glib' package
        requirement"。桥接：把 libnm 依赖 requires 里的 glib:: 新名
        改写为旧名组件（同一包同一二进制，pkg_config_name 即 pc 名，
        产出的 libnm.pc Requires 与上游官方一致）。
        """
        mapping = {
            "glib": "glib-2.0",
            "gobject": "gobject-2.0",
            "gio": "gio-2.0",
            "gmodule": "gmodule-2.0",
        }
        for dep in self.dependencies.host.values():
            if dep.ref.name != "libnm":
                continue
            original = list(dep.cpp_info.requires or [])
            patched = []
            for req in original:
                if req.startswith("glib::"):
                    comp = req.split("::", 1)[1]
                    req = "glib::" + mapping.get(comp, comp)
                patched.append(req)
            if patched != original:
                dep.cpp_info.requires = patched
                self.output.info(
                    "bridged libnm glib component requires: %s" % patched
                )

    def _inject_meson_tools(self):
        """补全 meson machine file 的 ar/ranlib/pkg-config 条目。

        OHOS SDK 的 lld 工具链路径在 profile conf 里只声明了 c/cpp，
        meson 交叉机器文件缺 ar/ranlib 时静态归档会用错误的 host ar
        （accountsservice 已验证模式）。
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

    def _prune_non_gtk4_outputs(self):
        """本件只交付 gtk4 变体：剔除 meson 同时安装出的主件产物。

        上游 meson 无条件构建 gtk3 主库 libnma.so 与 gschema/gtk-doc，
        libnma_gtk4=true 额外构建 libnma-gtk4.so。本包剔除：
          - lib/libnma.so*（gtk3 主件库，姊妹件 libnma/1.10.6 本体在途
            #8298 交付，跨账号同链分工，libportal-gtk3/gtk4 拆分同款）
          - lib/pkgconfig/libnma.pc（主件 pc）
          - share/glib-2.0/schemas/*.gschema.xml（gschema 属 nm-applet
            域，org.gnome.nm-applet.*；gtk4 变体的运行时 gsettings key
            相同，由本体包/系统侧统一部署）
          - share/gtk-doc（gtk_doc=false 时不产出，防御性剔除）
        include/libnma 头文件保留（gtk4 变体与 gtk3 本体的公共头同名
        同路径，nma-version.h 等；变体包声明自己的 includedirs）。
        """
        lib = os.path.join(self.package_folder, "lib")
        pkg = os.path.join(lib, "pkgconfig")
        if os.path.isdir(lib):
            for name in os.listdir(lib):
                if name.startswith("libnma.so") or name == "libnma.a":
                    os.remove(os.path.join(lib, name))
                    self.output.info(f"pruned main-library artifact: {name}")
        if os.path.isdir(pkg):
            for name in os.listdir(pkg):
                if name == "libnma.pc":
                    os.remove(os.path.join(pkg, name))
                    self.output.info("pruned main-library pc file")
        for share_sub in ("gtk-doc",):
            d = os.path.join(self.package_folder, "share", share_sub)
            if os.path.isdir(d):
                shutil.rmtree(d)
                self.output.info(f"pruned share/{share_sub}")
        schemas = os.path.join(self.package_folder, "share", "glib-2.0", "schemas")
        if os.path.isdir(schemas):
            for name in os.listdir(schemas):
                if name.endswith(".gschema.xml"):
                    os.remove(os.path.join(schemas, name))
                    self.output.info(f"pruned gschema: {name}")

    def _create_shared_lib_aliases(self, libdir):
        """dev so 别名用真拷贝（gtk 配方同款，规避 HMDFS symlink 限制）。"""
        base = "libnma-gtk4.so"
        real = os.path.join(libdir, f"{base}.0.0.0")
        if not os.path.isfile(real):
            return
        for name in (f"{base}.0", base):
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

    # ── 上游测试（R51 口径：真跑 + 解析 testlog + 环境受限逐项豁免）──

    def _run_upstream_tests(self):
        import json
        runtime_dir = ""
        if str(self.settings.os) == "OHOS":
            runtime_dir = self._materialize_test_runtime_libs()
        # 构造纯净测试环境：
        # 1) self.run 默认走 conanbuildenv 包装（LD_LIBRARY_PATH 里
        #    VirtualBuildEnv 注入的 gettext 工具包 lib 目录排在前）——
        #    gettext 的 libintl.so.8 只导出 libintl_*（无 g_ 前缀），先
        #    加载会遮蔽 glib vendor 的 libintl（g_libintl_*），libgtk-4/
        #    libgio 一整链加载期 "Error relocating ... g_libintl_*:
        #    symbol not found"（实测二分定位）。改用 subprocess 直跑 +
        #    env=None 语义（self.run 的 meson 路径在 PATH 上，工具链库
        #    由 meson 自己的 wrapper 处理）。
        # 2) runtime_dir（物化了 glib vendor libintl + 全部 symlink .so
        #    的真拷贝）排 LD_LIBRARY_PATH 最前，纯净依赖 libdir 在后。
        import subprocess
        if runtime_dir:
            paths = [runtime_dir]
            for dependency in self.dependencies.host.values():
                for libdir in dependency.cpp_info.libdirs:
                    if not os.path.isabs(libdir):
                        libdir = os.path.join(dependency.package_folder, libdir)
                    if os.path.isdir(libdir) and libdir not in paths:
                        paths.append(libdir)
            current = os.environ.get("LD_LIBRARY_PATH", "")
            if current:
                paths.extend(p for p in current.split(":") if p and p not in paths)
            os.environ["LD_LIBRARY_PATH"] = ":".join(paths)
        # subprocess 不走 conan 的 conanbuildenv 包装（正是要绕开的），
        # meson 从 PATH 解析；meson python 启动器自身需要的库路径已由
        # 上面拼好的 LD_LIBRARY_PATH 覆盖。
        meson_bin = shutil.which("meson")
        if not meson_bin:
            self.output.warning("meson not on PATH; skipping upstream test run")
            self._parse_and_report_tests()
            return
        try:
            proc = subprocess.run(
                [meson_bin, "test", "-v", "--no-rebuild", "-C", self.build_folder],
                check=False, timeout=1800,
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            )
            self.output.info(f"meson test exit code: {proc.returncode}")
            if proc.stdout:
                tail = proc.stdout.decode("utf-8", "replace")[-2000:]
                self.output.info("meson test output tail:\n" + tail)
        except Exception as exc:
            self.output.info(f"meson test invocation issue: {exc}")
        self._parse_and_report_tests()

    def _materialize_test_runtime_libs(self):
        """OHOS 加载器不解析 symlink 形态的 DT_NEEDED——把符号链接 .so
        物化为真拷贝（libnm 配方同款）。

        额外把 glib 包 lib/ 下的 libintl 全家真拷贝进来：VirtualBuildEnv
        把 gettext 工具包的 lib 目录也放进了 LD_LIBRARY_PATH（排在
        conan 依赖目录前），gettext 的 libintl.so.8 只导出 libintl_*
        符号（无 g_ 前缀），先加载会遮蔽 glib vendor 的 libintl
        （g_libintl_* 版本），libgtk-4/libgio 等一整链加载期报
        "Error relocating ... g_libintl_*: symbol not found"。本目录
        排在全部 conan 依赖目录之前，同名的 glib 版 libintl.so.8 在此
        优先命中（实测验证的遮蔽修复）。
        """
        runtime_dir = os.path.join(self.build_folder, "test-runtime-lib")
        os.makedirs(runtime_dir, exist_ok=True)
        # 1) glib vendor libintl 全家（同名遮蔽 gettext 工具包版本）
        glib_package = self._glib_package_folder()
        if glib_package:
            glib_lib = os.path.join(glib_package, "lib")
            for name in os.listdir(glib_lib):
                if name.startswith("libintl.so"):
                    src = os.path.join(glib_lib, name)
                    dst = os.path.join(runtime_dir, name)
                    if os.path.isfile(src) and not os.path.exists(dst):
                        shutil.copy2(src, dst)
        # 2) 依赖目录里的 symlink .so 物化
        candidates = []
        for dependency in self.dependencies.host.values():
            for libdir in dependency.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dependency.package_folder, libdir)
                if os.path.isdir(libdir):
                    candidates.extend(os.path.join(libdir, n) for n in os.listdir(libdir))
        for dirpath, dirnames, filenames in os.walk(self.build_folder):
            if os.path.abspath(dirpath).startswith(runtime_dir):
                dirnames[:] = []
                continue
            dirnames[:] = [d for d in dirnames if d not in (".git", "test-runtime-lib")]
            candidates.extend(os.path.join(dirpath, n) for n in filenames)
        materialized = []
        for candidate in candidates:
            name = os.path.basename(candidate)
            if ".so" not in name or not os.path.islink(candidate):
                continue
            real = os.path.realpath(candidate)
            if not os.path.isfile(real):
                continue
            destination = os.path.join(runtime_dir, name)
            if os.path.exists(destination):
                continue
            shutil.copy2(real, destination)
            materialized.append(name)
        if materialized:
            self.output.info(
                "test runtime: materialised %d symlinked .so file(s) into %s: %s"
                % (len(materialized), runtime_dir, ", ".join(sorted(materialized)))
            )
        return runtime_dir

    def _parse_and_report_tests(self):
        import json
        import re
        log_path = os.path.join(self.build_folder, "meson-logs", "testlog.txt")
        results = []
        if os.path.isfile(log_path):
            with open(log_path, encoding="utf-8", errors="replace") as handle:
                content = handle.read()
            for block in re.split(r"^=+ \d+/\d+ =+$", content, flags=re.M):
                name = re.search(r"^test:\s+(\S+)\s*$", block, flags=re.M)
                result = re.search(r"^result:\s+(.*?)\s*$", block, flags=re.M)
                if not name or not result:
                    continue
                short = name.group(1).split(":", 1)[-1]
                if result.group(1).startswith("exit status 0"):
                    status = "OK"
                elif result.group(1).startswith("SKIP"):
                    status = "SKIP"
                else:
                    status = "FAIL"
                results.append((short, status))
        passed = [n for n, s in results if s == "OK"]
        failed = [n for n, s in results if s == "FAIL"]
        skipped = [n for n, s in results if s == "SKIP"]
        marker = {
            "status": "passed" if not failed else "failed",
            "framework": "meson",
            "command": "meson test -C <build_folder>",
            "discovered": len(results),
            "executed": len(results),
            "passed": len(passed),
            "failed": len(failed),
            "skipped": len(skipped),
            "failed_environment": [],
            "failed_unexpected": failed,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(marker, ensure_ascii=False))
        for name, status in results:
            self.output.info(f"  upstream test {name}: {status}")
        if failed:
            raise Exception(
                "upstream libnma test suite failed: %s" % ", ".join(failed)
            )
        if not results:
            raise Exception("meson test produced no parsable results; see meson-logs/testlog.txt")
