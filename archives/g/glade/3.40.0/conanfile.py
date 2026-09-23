#!/usr/bin/env python3
"""Conan recipe — glade 3.40.0 (GNOME user interface designer, Meson).

OHOS 适配要点（全部经本地实测验证，详见 notes.md）：
  - 构建系统: meson（上游 meson.build），禁用 OHOS 不可用特性：
    introspection / man（xsltproc docbook 网络）/ help（itstool 缺失）/
    gjs / python（pygobject）/ webkit2gtk
  - 依赖均来自 ohpcd 制品仓：gtk/3.24.43（broadway 后端）、libxml2/2.15.3
  - glib 构建工具（glib-mkenums 等 python 脚本 + OHOS ELF 工具）按
    gdk-pixbuf/gtk 模式处理：wrapper 注入 + ELF 重签名（HMFS 执行限制）
  - PkgConfigDeps 生成的 pc 缺 glib_mkenums 等工具变量与 gmodule-export，
    按 gtk 配方同款方式在 generate() 中修补
  - glib-2.0.pc 补 -lintl（glib 2.84 的 g_libintl_* 符号在 libintl.so）
  - XDG_DATA_DIRS 注入含 hicolor index.theme + glib schemas 的目录，
    规避 GTK 3.24.43 conan 包在无 hicolor theme 时 lookup_icon 走 brk
    断言的问题（实测最小复现与规避验证）
  - 上游测试：broadwayd 虚拟显示（TCP :tcpN 模式）下 4/5 套件通过
    (add-child 1228 + create-widgets 154 + refcount 1 + toplevel-order 7)
  - OHOS 下对 bin/ 与 lib/ ELF 签名
"""
import glob
import json
import os
import shlex
import shutil
import sys

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain

HNP_BIN = "/data/service/hnp/bin"
SDK_LLVM_LIB = ("/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/"
                "ohos/native/llvm/lib/aarch64-linux-ohos")
SDK_LLVM_BIN = ("/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/"
                "ohos/native/llvm/bin")
HNP_PATCHelf = "/data/service/hnp/bin/patchelf"
SIGN_TOOL = os.path.join(HNP_BIN, "binary-sign-tool")
OBJCOPY = os.path.join(HNP_BIN, "llvm-objcopy")
PYTHON3 = os.path.realpath(sys.executable)


class GladeConan(ConanFile):
    name = "glade"
    version = "3.40.0"
    description = ("GNOME user interface designer (Glade) with the "
                   "libgladeui designer library, GTK+ catalog and "
                   "glade-previewer")
    license = "GPL-2.0-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/glade"
    url = "https://gitlab.gnome.org/GNOME/glade"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"
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
        # 与 gtk/3.24.43 已发布 binary 的依赖选项对齐（同 gtk 配方）
        try:
            self.options["glib"].shared = True
            self.options["gtk"].shared = True
            self.options["pango"].shared = True
            self.options["gdk-pixbuf"].shared = True
        except Exception:
            pass

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"Unsupported OS: {self.settings.os}")

    def requirements(self):
        # 传递头与库：test_package 需 include <gladeui/glade.h> 时
        # gtk/glib 头文件与 so 均可传递解析（同 avahi-ui-tools 模式）
        self.requires("gtk/3.24.43",
                      transitive_headers=True, transitive_libs=True)
        self.requires("glib/2.84.0.1",
                      transitive_headers=True, transitive_libs=True)
        self.requires("libxml2/2.15.3", transitive_headers=True,
                      transitive_libs=True)

    def build_requirements(self):
        # meson 从 ohpcd 工具包取（libavtp 同款），避免依赖 worker 全局
        self.tool_requires("meson/1.11.0")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        sources = dict(self.conan_data["sources"])
        mirror_url = sources.pop("mirror_url", None)
        staged = os.path.expanduser("~/tmp/builds/glade-3.40.0.tar.xz")
        if os.path.isfile(staged):
            from conan.tools.files import check_sha256, unzip
            check_sha256(self, staged, sources["sha256"])
            unzip(self, staged, strip_root=True)
            return
        try:
            get(self, **sources, strip_root=True)
        except Exception as e:
            if not mirror_url:
                raise
            self.output.warning(f"Primary source failed ({e}), trying mirror")
            get(self, url=mirror_url, sha256=sources["sha256"], strip_root=True)

    # ──────────────────────────────────────────────────────────────
    # generate(): pc 修补 + glib 工具 staging + meson toolchain
    # ──────────────────────────────────────────────────────────────
    def generate(self):
        PkgConfigDeps(self).generate()
        tools_folder = self._prepare_glib_build_tools()
        self._augment_glib_pkg_config(tools_folder)
        self._create_gmodule_export_pc()
        self._create_gdk_pc()
        self._patch_libintl()
        self._write_test_runtime_data()
        # staged lld：CI worker SDK lib 目录缺 libxml2.so.16 时系统 lld
        # 起不来的根治方案（详见 _stage_lld 注释）。generate 阶段就绪，
        # machine file c_ld 与 CFLAGS/LDFLAGS 双通道注入——meson 的
        # guess_nix_linker 探测读取 LDFLAGS 与 language+'_ld' 条目
        # （mesonbuild/linkers/detect.py）。
        staged_ld = self._stage_lld()
        tc = MesonToolchain(self)
        tc.project_options.update({
            "wrap_mode": "nodownload",
            "default_library": "shared" if self.options.shared else "static",
            "introspection": False,
            "man": False,
            "gjs": "disabled",
            "python": "disabled",
            "webkit2gtk": "disabled",
            "gladeui": False,
            "mac_bundle": False,
        })
        # machine file [properties] link_args（探测与链接都吃）
        tc.c_link_args.append(f"--ld-path={staged_ld}")
        tc.cpp_link_args.append(f"--ld-path={staged_ld}")
        tc.generate()
        self._inject_meson_tools(tools_folder)
        self._inject_ld_in_machine_files(staged_ld)

    def _inject_ld_in_machine_files(self, staged_ld):
        """把 c_ld/cpp_ld 写进 conan 生成的 machine files（[binaries] 段）。

        meson guess_nix_linker 对 language+'_ld' 条目：
        lookup_binary_entry → use_linker_args → 追加到探测命令与全部
        链接命令（clang mixin 对绝对路径走 shutil.which 命中 →
        '-fuse-ld=<路径>'，clang 15 支持）。与 --ld-path 双保险。"""
        for filename in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            mf = os.path.join(self.generators_folder, filename)
            if not os.path.isfile(mf):
                continue
            content = open(mf, encoding="utf-8").read()
            if "[binaries]" not in content or "\nc_ld = " in content:
                continue
            additions = (f"c_ld = '{staged_ld}'\n"
                         f"cpp_ld = '{staged_ld}'\n")
            content = content.replace(
                "[binaries]\n", "[binaries]\n" + additions, 1)
            open(mf, "w", encoding="utf-8", newline="\n").write(content)

    def build(self):
        apply_conandata_patches(self)
        env = self._build_environment()
        with env.vars(self).apply():
            meson = Meson(self)
            meson.configure()
            meson.build()
            self._run_upstream_tests()

    def package(self):
        with self._build_environment().vars(self).apply():
            Meson(self).install()
        # meson_post_install.py 调 gtk-update-icon-cache：DESTDIR 模式下
        # meson install 会跳过（无 DESTDIR 时工具也不可用）。目录里的
        # 图标缓存为运行时可选资源，缺失不阻塞。
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)
        if self.settings.os == "OHOS":
            self._sign_installed_elfs()

    def package_info(self):
        # 应用包：glade / glade-previewer 可执行 + libgladeui 设计时库。
        # 下游 IDE 集成方按 pkg-config gladeui-2.0 链接 libgladeui。
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = ["gladeui-2"]
        self.cpp_info.includedirs = ["include/libgladeui-2.0", "include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.set_property("cmake_file_name", "glade")
        self.cpp_info.set_property("cmake_target_name", "glade::glade")
        self.cpp_info.set_property("pkg_config_name", "gladeui-2")
        # gtk/glib 包均为无组件平铺包（gtk 配方不声明 cpp_info.requires，
        # 链接顺序由 graph 与各包 .pc 的 Libs 承载，同 gtk 配方做法），
        # 这里不声明组件 requires 以免 CMakeDeps/PkgConfigDeps 拒绝。
        if str(self.settings.os) in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]

    # ──────────────────────────────────────────────────────────────
    # 构建环境：LD_LIBRARY_PATH（含 SDK libc++ 与 conan 依赖）+ TMPDIR
    # ──────────────────────────────────────────────────────────────
    def _stage_lld(self):
        """Stage 一个 RUNPATH 自包含且保留 --code-sign 行为的 lld。

        背景（全部实测）：
        1. 部分 CI worker 的 SDK lib 目录缺 libxml2.so.16，系统 lld
           （RUNPATH 只含 $ORIGIN/../lib）无法启动，meson 的 linker
           探测（clang -Wl,--version）第一步就崩（CI builds 37741/
           37751/37760/37793 均为此）。
        2. OHOS musl loader 对带签名 ELF 忽略 LD_LIBRARY_PATH——
           LD_LIBRARY_PATH 注入方案（gtk 配方 ld-fallback）无效。
        3. SDK 的 bin/ld.lld 是 sh wrapper：exec lld --code-sign "$@"——
           链接产物自动带签名；HMFS 上未签名 ELF 无法执行（meson
           sanity check 的 exe 会 EPERM）。staged 链接器必须保留该
           行为（实测：staged 裸 lld 链接的 sanity exe 无 .codesign
           段，执行 EPERM；系统 lld 链接的有签名可执行）。

        方案：lld ELF 拷贝 + patchelf RUNPATH=$ORIGIN（同目录放
        conan libxml2 包的 libxml2.so.16）+ 重签（HMFS 执行要求），
        再用 SDK 同款 wrapper 脚本补 --code-sign。返回 wrapper 路径。
        幂等。"""
        lld_dir = os.path.join(self.build_folder, "lld-stage")
        os.makedirs(lld_dir, exist_ok=True)
        staged_ld = os.path.join(lld_dir, "ld.lld")
        staged_elf = os.path.join(lld_dir, "lld.elf")
        if os.path.isfile(staged_ld) and os.access(staged_ld, os.X_OK):
            return staged_ld
        sdk_lld = os.path.join(SDK_LLVM_BIN, "lld")
        if not os.path.isfile(sdk_lld):
            raise ConanException(f"SDK lld missing: {sdk_lld}")
        shutil.copyfile(sdk_lld, staged_elf)
        os.chmod(staged_elf, 0o755)
        # 同目录放 libxml2.so.16（conan libxml2 包，制品仓必带；拷实体）
        import glob as _glob
        libxml2_lib = None
        try:
            libxml2 = self.dependencies["libxml2"]
            hits = _glob.glob(os.path.join(
                libxml2.package_folder, "lib", "libxml2.so.16"))
            if hits:
                libxml2_lib = hits[0]
        except KeyError:
            pass
        if libxml2_lib is None:
            hits = _glob.glob(os.path.join(
                os.path.expanduser("~"), "usr", "local", "lib",
                "libxml2.so.16"))
            if hits:
                libxml2_lib = hits[0]
        if libxml2_lib is None:
            raise ConanException(
                "libxml2.so.16 not found in conan package or user lib")
        shutil.copyfile(libxml2_lib, os.path.join(lld_dir, "libxml2.so.16"))
        # RUNPATH=$ORIGIN → staged lld 从本目录解析 libxml2.so.16
        if os.path.isfile(HNP_PATCHelf):
            self.run(f"{shlex.quote(HNP_PATCHelf)} --set-rpath "
                     f"'$ORIGIN' {shlex.quote(staged_elf)}")
        # HMFS 执行限制：拷出的 ELF 需重签
        if os.path.isfile(OBJCOPY):
            self.run(f"{shlex.quote(OBJCOPY)} --remove-section .codesign "
                     f"{shlex.quote(staged_elf)} 2>/dev/null || true")
        if os.path.isfile(SIGN_TOOL):
            self.run(shlex.join([SIGN_TOOL, "sign", "-inFile", staged_elf,
                                 "-outFile", staged_elf, "-selfSign", "1"]))
        # SDK 同款 wrapper：保留 --code-sign（链接产物签名，HMFS 可执行）
        with open(staged_ld, "w", encoding="utf-8", newline="\n") as h:
            h.write("#!/bin/sh\n"
                    f"exec -a \"$0\" {shlex.quote(staged_elf)} "
                    "--code-sign \"$@\"\n")
        os.chmod(staged_ld, 0o755)
        return staged_ld

    def _build_environment(self):
        env = Environment()
        tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp, exist_ok=True)
        env.define_path("TMPDIR", tmp)
        env.define_path("TMP", tmp)
        env.define_path("TEMP", tmp)
        env.prepend_path("LD_LIBRARY_PATH", SDK_LLVM_LIB)
        env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        env.prepend_path("PATH", self._glib_tools_folder())
        # 部分 CI worker 的 SDK lld 依赖 libxml2.so.16 但其 RUNPATH 只含
        # $ORIGIN/../lib（SDK lib 目录无该库时 lld 无法启动），且 OHOS
        # musl loader 对带签名 ELF 忽略 LD_LIBRARY_PATH（实测：设
        # LD_LIBRARY_PATH 指向含 libxml2.so.16 的目录，lld 仍报
        # "Error loading shared library libxml2.so.16"）——LD_LIBRARY_PATH
        # 注入方案（gtk 配方 ld-fallback）对该场景无效。
        # 有效方案（实测验证）：把 lld ELF staging 到构建目录，patchelf
        # 设 RUNPATH=$ORIGIN + selfSign 重签，libxml2.so.16 放同目录，
        # 通过 CFLAGS/CXXFLAGS 注入 --ld-path 让 clang 全链路使用 staged
        # 链接器（meson 的 linker 探测 `clang -Wl,--version` 同样吃
        # CFLAGS，实测返回 LLD 15.0.4）。SDK 自带 libxml2.so.16 的
        # worker 上 staged 副本同样可用（RUNPATH 自包含）。
        staged_ld = self._stage_lld()
        env.define("CFLAGS", f"--ld-path={staged_ld}")
        env.define("CXXFLAGS", f"--ld-path={staged_ld}")
        # meson guess_nix_linker 探测命令读 external_link_args（含
        # LDFLAGS env），与 machine file c_ld 双保险
        env.define("LDFLAGS", f"--ld-path={staged_ld}")
        # msgfmt ITS 规则 + hicolor theme + glib schemas 的数据目录
        # （hnp gettext 0.26 的 ITS 在其安装 share 下；msgfmt 只搜
        # $XDG_DATA_DIRS/gettext/its，需 staging 软链或拷贝）
        self._stage_msgfmt_its()
        env.prepend_path("XDG_DATA_DIRS",
                         os.path.join(self.build_folder, "test-data",
                                      "share"))
        for dep in self.dependencies.host.values():
            bindir = os.path.join(dep.package_folder, "bin")
            if os.path.isdir(bindir):
                env.prepend_path("PATH", bindir)
            for libdir in dep.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dep.package_folder, libdir)
                if os.path.isdir(libdir):
                    env.prepend_path("LD_LIBRARY_PATH", libdir)
        return env

    def _stage_msgfmt_its(self):
        """把 hnp gettext 0.26 的 ITS 规则放到 XDG_DATA_DIRS 搜索路径。

        msgfmt --xml/--desktop 需要 ITS 定位规则；gettext 0.26 安装在
        /data/service/hnp/gettext.org/gettext_0.26/share/gettext-0.26/its，
        但运行时只搜 $XDG_DATA_DIRS/gettext/its。实测拷贝后 i18n.merge_file
        正常。"""
        src = ("/data/service/hnp/gettext.org/gettext_0.26/share/"
               "gettext-0.26/its")
        dst = os.path.join(self.build_folder, "test-data", "share",
                           "gettext", "its")
        if os.path.isdir(dst) and os.listdir(dst):
            return
        if not os.path.isdir(src):
            self.output.warning(f"gettext ITS rules not found: {src}")
            return
        os.makedirs(dst, exist_ok=True)
        for name in os.listdir(src):
            shutil.copyfile(os.path.join(src, name), os.path.join(dst, name))

    def _glib_tools_folder(self):
        return os.path.join(self.build_folder, "conan-native-tools")

    def _prepare_glib_build_tools(self):
        """glib 构建工具 staging（gtk 配方同款思路 + 适配差异）。

        差异点（本机实测）：
        1. glib 包内 OHOS ELF 工具（glib-compile-resources 等）在 HMFS
           上直接执行报 EPERM —— 拷贝到 build 目录重签名后可执行；
           它们链接 conan glib 的 so，通过 wrapper 注入 LD_LIBRARY_PATH。
        2. python 脚本工具（glib-mkenums/glib-genmarshal）无 shebang
           执行权（HMFS 拒绝跨 UID 脚本），用 sh wrapper 显式指定
           python 解释器。
        3. meson 的 ninja 探测走 subprocess（PATH 查找在部分 worker 上
           对裸名一律 ENOENT），NINJA 环境变量显式指定绝对路径。
        """
        glib_bin = os.path.join(
            self.dependencies["glib"].package_folder, "bin")
        tools_folder = self._glib_tools_folder()
        os.makedirs(tools_folder, exist_ok=True)

        python_tools = ("glib-mkenums", "glib-genmarshal")
        for tool in python_tools:
            src = os.path.join(glib_bin, tool)
            if not os.path.isfile(src):
                raise ConanException(f"GLib build tool missing: {src}")
            wrapper = os.path.join(tools_folder, tool)
            q = lambda s: "'" + str(s).replace("'", "'\\''") + "'"
            with open(wrapper, "w", encoding="utf-8", newline="\n") as h:
                h.write(f"#!/bin/sh\nexec {q(PYTHON3)} {q(src)} \"$@\"\n")
            os.chmod(wrapper, 0o755)

        elf_tools = ("glib-compile-resources", "glib-compile-schemas")
        glib_libdir = os.path.join(
            self.dependencies["glib"].package_folder, "lib")
        for tool in elf_tools:
            src = os.path.join(glib_bin, tool)
            if not os.path.isfile(src):
                raise ConanException(f"GLib build tool missing: {src}")
            staged = os.path.join(tools_folder, tool)
            shutil.copyfile(src, staged)
            os.chmod(staged, 0o755)
            if self.settings.os == "OHOS":
                self._resign_elf(staged)
            wrapper = os.path.join(tools_folder, tool)
            # 重签后的 ELF + LD_LIBRARY_PATH 指向 conan glib 库
            q = lambda s: "'" + str(s).replace("'", "'\\''") + "'"
            with open(wrapper + ".sh", "w", encoding="utf-8",
                      newline="\n") as h:
                h.write("#!/bin/sh\n"
                        f"export LD_LIBRARY_PATH={q(glib_libdir)}"
                        ":$LD_LIBRARY_PATH\n"
                        f"exec {q(staged)} \"$@\"\n")
            os.chmod(wrapper + ".sh", 0o755)
        return tools_folder

    def _resign_elf(self, binary):
        """HMFS 执行限制规避：移除 .codesign 段后 selfSign 重签（实测）。"""
        if os.path.isfile(OBJCOPY):
            self.run(f"{shlex.quote(OBJCOPY)} --remove-section .codesign "
                     f"{shlex.quote(binary)} 2>/dev/null || true")
        if os.path.isfile(SIGN_TOOL):
            self.run(shlex.join([SIGN_TOOL, "sign", "-inFile", binary,
                                 "-outFile", binary, "-selfSign", "1"]))

    def _augment_glib_pkg_config(self, tools_folder):
        """PkgConfigDeps 生成的 glib/gio pc 缺 meson gnome 模块查询的
        工具变量（glib_mkenums/glib_compile_resources 等），按 gtk 配方
        同款方式注入 wrapper 路径。glib-2.0.pc 同时补 -lintl。"""
        tools = {
            "glib-2.0": {
                "glib_genmarshal": os.path.join(tools_folder, "glib-genmarshal"),
                "gobject_query": os.path.join(tools_folder, "gobject-query.sh"),
                "glib_mkenums": os.path.join(tools_folder, "glib-mkenums"),
            },
            "gio-2.0": {
                "glib_compile_schemas": os.path.join(tools_folder, "glib-compile-schemas.sh"),
                "glib_compile_resources": os.path.join(tools_folder, "glib-compile-resources.sh"),
            },
        }
        for pc_name, variables in tools.items():
            pc = os.path.join(self.generators_folder, f"{pc_name}.pc")
            if not os.path.isfile(pc):
                self.output.warning(f"PkgConfigDeps missing: {pc_name}.pc")
                continue
            content = open(pc, encoding="utf-8").read()
            block = "".join(
                f"{k}={v.replace(os.sep, '/')}\n"
                for k, v in variables.items() if f"{k}=" not in content)
            marker = "\nName:"
            if block and marker in content:
                content = content.replace(marker, f"\n{block}{marker}", 1)
                open(pc, "w", encoding="utf-8", newline="\n").write(content)

    def _create_gmodule_export_pc(self):
        """glade 顶层 meson.build 依赖 gmodule-export-2.0；glib 包内自带
        该 pc 但 PkgConfigDeps 只生成组件 pc。手工生成指向 glib 包。"""
        glib = self.dependencies["glib"]
        prefix = glib.package_folder.replace(os.sep, "/")
        pc = os.path.join(self.generators_folder, "gmodule-export-2.0.pc")
        with open(pc, "w", encoding="utf-8", newline="\n") as h:
            h.write(f"prefix={prefix}\n")
            h.write("libdir=${prefix}/lib\n")
            h.write("includedir=${prefix}/include\n\n")
            h.write("gmodule_supported=true\n\n")
            h.write("Name: gmodule-export-2.0\n")
            h.write("Description: Dynamic module loader for GLib (export)\n")
            h.write(f"Version: {glib.ref.version}\n")
            h.write("Libs: -L${libdir} -lgmodule-2.0 -ldl -Wl,--export-dynamic\n")
            h.write("Cflags: -I${includedir}/glib-2.0 "
                    "-I${libdir}/glib-2.0/include\n")
            h.write("Requires: glib-2.0\n")

    def _create_gdk_pc(self):
        """glade 用 dependency('gdk-3.0').get_pkgconfig_variable('targets')
        检查 quartz；gtk 包内有 gdk-3.0.pc 但 PkgConfigDeps 不生成它
        （gtk 配方 cpp_info 未单独声明 gdk 组件），手工补一个。"""
        gtk = self.dependencies["gtk"]
        prefix = gtk.package_folder.replace(os.sep, "/")
        pc = os.path.join(self.generators_folder, "gdk-3.0.pc")
        with open(pc, "w", encoding="utf-8", newline="\n") as h:
            h.write(f"prefix={prefix}\n")
            h.write("libdir=${prefix}/lib\n")
            h.write("includedir=${prefix}/include\n\n")
            h.write("targets=broadway\n\n")
            h.write("Name: GDK\n")
            h.write("Description: GTK+ Drawing Kit\n")
            h.write(f"Version: {gtk.ref.version}\n")
            h.write("Requires: gtk+-3.0\n")
            h.write("Libs: -L${libdir} -lgdk-3\n")
            h.write("Cflags: -I${includedir}/gtk-3.0\n")

    def _patch_libintl(self):
        """glib 2.84 的 g_libintl_* 符号在 libintl.so（glib 包内）；
        PkgConfigDeps 生成的 glib-2.0.pc Libs 缺 -lintl，链接
        libgladeui 时 undefined symbol（实测）。补进 pc。"""
        pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if not os.path.isfile(pc):
            return
        content = open(pc, encoding="utf-8").read()
        if "-lintl" in content:
            return
        lines = []
        for line in content.splitlines(keepends=True):
            if line.startswith("Libs:") and "-lintl" not in line.split():
                line = line.rstrip("\r\n") + " -lintl\n"
            lines.append(line)
        open(pc, "w", encoding="utf-8", newline="\n").write("".join(lines))

    def _write_test_runtime_data(self):
        """上游测试运行时数据：hicolor icon theme + GTK glib schemas。

        实测根因：GTK 3.24.43 conan 包在 icon theme 无 hicolor 时，
        gtk_icon_theme_lookup_icon 在打印 warning 后走到 brk 断言
        （musl 无消息直接 SIGTRAP），glade_init→register_icon_names
        必然触发。提供最小合法 index.theme 后 lookup 正常返回 NULL。
        FileChooserButton 用例还需要 org.gtk.Settings.FileChooser schema。
        """
        data_root = os.path.join(self.build_folder, "test-data")
        share = os.path.join(data_root, "share")
        hicolor = os.path.join(share, "icons", "hicolor")
        for sub in ("24x24/actions", "24x24/apps", "24x24/status",
                    "48x48/status", "scalable/actions"):
            os.makedirs(os.path.join(hicolor, sub), exist_ok=True)
        with open(os.path.join(hicolor, "index.theme"), "w",
                  encoding="utf-8", newline="\n") as h:
            h.write("[Icon Theme]\n"
                    "Name=Hicolor\n"
                    "Comment=Fallback icon theme\n"
                    "Hidden=true\n"
                    "Directories=24x24/actions,24x24/apps,24x24/status,"
                    "48x48/status,scalable/actions\n"
                    "\n[24x24/actions]\nSize=24\nContext=Actions\n"
                    "Type=Threshold\n"
                    "\n[24x24/apps]\nSize=24\nContext=Applications\n"
                    "Type=Threshold\n"
                    "\n[24x24/status]\nSize=24\nContext=Status\n"
                    "Type=Threshold\n"
                    "\n[48x48/status]\nSize=48\nContext=Status\n"
                    "Type=Threshold\n"
                    "\n[scalable/actions]\nSize=48\nContext=Actions\n"
                    "Type=Scalable\nMinSize=8\nMaxSize=512\n")
        # refcount/toplevel-order 套件渲染 widget 树时会请求
        # 'image-missing'（GTK 缺图标 fallback），Adwaita/hicolor 均无时
        # gtkiconhelper assert。glade 源码 data/icons/placeholder.png
        # 作为合法 PNG 提供该图标名。
        for size_dir in ("24x24", "48x48"):
            src = os.path.join(self.source_folder, "data", "icons",
                               "placeholder.png")
            dst = os.path.join(hicolor, size_dir, "status",
                               "image-missing.png")
            if os.path.isfile(src):
                shutil.copyfile(src, dst)
        # GTK 包自带 schemas；编译到测试数据目录供 GSettings 找到
        schemas_dir = os.path.join(share, "glib-2.0", "schemas")
        os.makedirs(schemas_dir, exist_ok=True)
        gtk_share = os.path.join(
            self.dependencies["gtk"].package_folder, "share",
            "glib-2.0", "schemas")
        compiled = False
        if os.path.isdir(gtk_share):
            for name in os.listdir(gtk_share):
                if name.endswith(".gschema.xml"):
                    shutil.copyfile(os.path.join(gtk_share, name),
                                    os.path.join(schemas_dir, name))
            gcs = os.path.join(self._glib_tools_folder(),
                               "glib-compile-schemas.sh")
            if os.path.isfile(gcs):
                self.run(f"{shlex.quote(gcs)} "
                         f"{shlex.quote(schemas_dir)}", env="conanbuild")
                compiled = os.path.isfile(os.path.join(
                    schemas_dir, "gschemas.compiled"))
        if not compiled:
            self.output.warning("glib schemas not compiled for tests")

    # ──────────────────────────────────────────────────────────────
    # 上游测试：broadwayd 虚拟显示 + 4 个可运行套件
    # ──────────────────────────────────────────────────────────────
    def _run_upstream_tests(self):
        if str(self.settings.os) != "OHOS":
            # 非 OHOS（Linux 原生）也可跑，路径一致
            pass
        env = self._build_environment()
        # broadwayd：gtk 包内 OHOS ELF，staging + 重签名后可执行
        gtk_bin = os.path.join(
            self.dependencies["gtk"].package_folder, "bin")
        broadwayd = os.path.join(self.build_folder, "conan-native-tools",
                                 "broadwayd")
        src = os.path.join(gtk_bin, "broadwayd")
        if not os.path.isfile(src):
            raise ConanException(f"broadwayd missing in gtk package: {src}")
        shutil.copyfile(src, broadwayd)
        os.chmod(broadwayd, 0o755)
        if self.settings.os == "OHOS":
            self._resign_elf(broadwayd)

        port = 9095  # display :tcp5 → 127.0.0.1:9095
        test_env = env
        test_env.define("BROADWAY_DISPLAY", ":tcp5")
        test_env.define("GDK_BACKEND", "broadway")
        test_env.define("XDG_DATA_DIRS",
                        os.path.join(self.build_folder, "test-data", "share"))
        test_env.define("GLADE_TESTING", "1")
        test_env.define("GLADE_CATALOG_SEARCH_PATH",
                        os.path.join(self.source_folder, "plugins", "gtk+"))
        test_env.define("GLADE_MODULE_SEARCH_PATH",
                        os.path.join(self.build_folder, "plugins", "gtk+"))
        test_env.define("GLADE_PIXMAP_DIR",
                        os.path.join(self.source_folder, "data", "icons"))
        test_env.define("GLADE_ICON_THEME_PATH",
                        os.path.join(self.source_folder, "plugins", "gtk+",
                                     "icons", "22x22"))

        with test_env.vars(self).apply():
            # 启动 broadwayd（setsid 脱离进程组，防止 conan build 退出杀掉）
            self.run(f"setsid {shlex.quote(broadwayd)} :tcp5 "
                     f">{shlex.quote(os.path.join(self.build_folder, 'broadwayd.log'))} "
                     "2>&1 < /dev/null &", env="conanbuild")
            import time
            time.sleep(3)
            suites = (
                # (name, 可运行性说明)
                ("add-child", None),
                ("create-widgets", None),
                ("refcount", None),
                ("toplevel-order", None),
                ("modules", "requires python/gjs plugins (disabled on OHOS)"),
            )
            log = os.path.join(self.build_folder, "upstream-tests.log")
            entries = []
            with open(log, "w", encoding="utf-8", newline="\n") as h:
                for name, skip_reason in suites:
                    binary = os.path.join(self.build_folder, "tests", name)
                    if skip_reason:
                        h.write(f"# {name}: SKIPPED ({skip_reason})\n")
                        entries.append((name, "SKIP"))
                        continue
                    h.write(f"# {name}\n")
                    try:
                        self.run(f"{shlex.quote(binary)}",
                                 cwd=self.build_folder, env="conanbuild",
                                 stdout=h, stderr=h)
                        entries.append((name, "PASS"))
                    except ConanException:
                        entries.append((name, "FAIL"))
            # 关闭 broadwayd（pkill -f 会匹配到自身命令行导致误杀 shell，
            # 用 [b]roadwayd 正则技巧规避；0=杀到 1=无匹配均视为成功）
            self.run(f"pkill -f '[b]roadwayd :tcp5' || [ $? -eq 1 ]",
                     env="conanbuild")

        with open(log, "r", encoding="utf-8", errors="replace") as h:
            text = h.read()
        passed = sum(1 for _, s in entries if s == "PASS")
        failed = sum(1 for _, s in entries if s == "FAIL")
        total_cases = 0
        total_ok = 0
        for line in text.splitlines():
            if line.startswith("ok "):
                total_ok += 1
                total_cases += 1
            elif line.startswith("not ok"):
                total_cases += 1
        upstream = {
            "status": "passed" if failed == 0 else "failed",
            "framework": "meson test (gtk_test_init TAP suites)",
            "command": "broadwayd :tcp5 & tests/{add-child,create-widgets,"
                       "refcount,toplevel-order}",
            "discovered": len(entries),
            "executed": passed + failed,
            "passed": passed,
            "failed": failed,
            "test_cases_total": total_cases,
            "test_cases_passed": total_ok,
        }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT="
                         + json.dumps(upstream, ensure_ascii=False))
        if failed > 0:
            raise ConanException(
                f"upstream tests failed: {passed} passed, {failed} failed"
                f"\n{text[-4000:]}")

    # ──────────────────────────────────────────────────────────────
    # meson machine files 注入 ar/ranlib/pkg-config/NINJA（裸名 subprocess
    # 在部分 worker 上 ENOENT 的规避）
    # ──────────────────────────────────────────────────────────────
    def _inject_meson_tools(self, tools_folder):
        ce = self.conf.get("tools.build:compiler_executables",
                           default={}, check_type=dict) or {}
        cc = ce.get("c") or ""
        cdir = os.path.dirname(cc) if cc and os.path.sep in cc else ""
        ar = ce.get("ar")
        ranlib = ce.get("ranlib")
        if cdir:
            if not ar:
                cand = os.path.join(cdir, "llvm-ar")
                if os.path.isfile(cand):
                    ar = cand
            if not ranlib:
                cand = os.path.join(cdir, "llvm-ranlib")
                if os.path.isfile(cand):
                    ranlib = cand
        pkg_config = self.conf.get("tools.gnu:pkg_config", default=None)
        if not pkg_config or not os.path.isfile(str(pkg_config)):
            pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")
            if not pkg_config and cdir:
                cand = os.path.join(cdir, "pkg-config")
                if os.path.isfile(cand):
                    pkg_config = cand
        ninja = shutil.which("ninja")
        for fn in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            nf = os.path.join(self.generators_folder, fn)
            if not os.path.isfile(nf):
                continue
            content = open(nf, encoding="utf-8").read()
            if "[binaries]" not in content:
                continue
            binaries = []
            if ar and "\nar =" not in content:
                binaries.append(f"ar = '{ar}'")
            if ranlib and "\nranlib =" not in content:
                binaries.append(f"ranlib = '{ranlib}'")
            if pkg_config and ("\npkg-config =" not in content
                               and "\npkgconfig =" not in content):
                binaries.append(f"pkg-config = '{pkg_config}'")
            if ninja and "\nninja = " not in content:
                binaries.append(f"ninja = '{ninja}'")
            if not binaries:
                continue
            content = content.replace(
                "[binaries]\n", "[binaries]\n" + "\n".join(binaries) + "\n", 1)
            open(nf, "w", encoding="utf-8", newline="\n").write(content)

    def _sign_installed_elfs(self):
        """OHOS 签名（ci/artifacts/sign.sh 同款自签逻辑）。

        实测：HMFS 上对刚由 meson install 产出的文件做单次 selfSign，
        部分 .so（如 lib/glade/modules/libgladegtk.so）签名结果无效
        （dlopen Permission denied）；同一文件二次重签后有效。故对每个
        ELF 执行 remove-section + selfSign 两轮，规避首签失效。"""
        if not os.path.isfile(SIGN_TOOL):
            self.output.warning("binary-sign-tool not found; skip signing")
            return
        targets = []
        for pattern in (os.path.join(self.package_folder, "bin", "*"),
                        os.path.join(self.package_folder, "lib", "**",
                                     "*.so"),
                        os.path.join(self.package_folder, "lib", "**",
                                     "*.so.*")):
            targets.extend(glob.glob(pattern, recursive=True))
        for binary in sorted(set(targets)):
            if not os.path.isfile(binary) or os.path.islink(binary):
                continue
            for _round in (1, 2):
                if os.path.isfile(OBJCOPY):
                    self.run(
                        f"{shlex.quote(OBJCOPY)} --remove-section "
                        f".codesign {shlex.quote(binary)} 2>/dev/null || true")
                self.run(shlex.join(
                    [SIGN_TOOL, "sign", "-inFile", binary,
                     "-outFile", binary, "-selfSign", "1"]))
