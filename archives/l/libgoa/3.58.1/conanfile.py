#!/usr/bin/env python3
"""Conan recipe — libgoa 3.58.1 (Meson)。

GNOME Online Accounts (gnome-online-accounts) 的客户端库 libgoa-1.0：
通过 D-Bus 连接 goa-daemon，枚举与管理在线账户（Google / Microsoft 365 /
WebDAV / ownCloud / IMAP-SMTP 等）以及 OAuth2 / 密码 / Ticket 类凭据。

OHOS 适配要点：
  1. Meson 构建。worker 未预装 meson，recipe 通过 tool_requires 引入制品仓中
     已发布的 meson/1.11.0（本仓 libtsm/4.6.0、kea-shell 同款做法）；
     ninja / pkg-config / clang / msgfmt / gdbus-codegen / glib-mkenums 由
     worker 自带（CI profile 的 PATH 已包含 /data/service/hnp/bin 与
     /storage/Users/currentUser/usr/local/bin）。
  2. 关闭 goabackend。上游后端需要 json-glib / libsecret / libsoup-3.0 /
     libxml2 / rest-1.0 / gtk4 / libadwaita-1，这些尚未发布到 ohpcd 制品仓，
     因此 -Dgoabackend=false，并同步关闭全部 provider 与
     introspection / vapi / documentation / man。
     后端关闭后 libgoa-1.0 只链接 glib/gio：dbus-1 只服务于 goa-daemon 的
     D-Bus service 安装路径（data/meson.build 的 goabackend 分支），补丁 0001
     后构建图里不再出现。因此 requires 里不放 dbus——conan 2.29 会拒绝
     "声明了却未出现在 cpp_info.requires 的直接依赖"
     (The direct dependency 'dbus' is not used by any cpp_info.requires)。
     开启后端时需一并加回 dbus/json-glib/libsecret/libsoup-3.0/libxml2/
     rest-1.0（均未发布到 ohpcd）。
  3. patches/0001 修复 pkg-config 缺口。conan 的 glib / dbus 包没有 meson
     需要的 gio-unix-2.0.pc 与 dbus-1.pc（glib 包内 .pc 以 prefix=/ 安装，
     路径不可用；dbus 包不安装任何 .pc；PkgConfigDeps 生成的 dbus.pc 也没有
     上游 get_variable 索要的 session_bus_services_dir，而该调用没有
     default_value）。补丁让 gio-unix 缺失时回退到 gio_dep，并让 dbus-1 的
     查找只在 goabackend 打开时求值——上游 dbus_service_dir 确实只被
     data/meson.build 的 goabackend 分支引用，关闭后端时该依赖不进入
     构建图。src/goa/ 下没有任何 gio-unix 符号引用，该回退不改变导出 ABI。
  4. data/ 与 po/ 子目录在任何配置下都会执行（i18n.gettext 需要 msgfmt），
     worker 自带 msgfmt，无需额外 tool_requires。
  5. conan 2.29.1 的 Meson 助手编译入口是 Meson.build()，仓库模板
     templates/conanfile-meson.py.tmpl 与 docs/ADAPTATION_GUIDE.md §4.4 里的
     meson.compile() 在本版 conan 不存在（AttributeError），同 meson_layout。
  6. E012 + gnome 模块工具注入。MesonToolchain 不往 conan_meson_native.ini 写
     [binaries]，有两处会断：(a) ar/ranlib 缺失 → 链接期 "Unable to detect
     linker"；(b) gnome.gdbus_codegen / gnome.mkenums_simple 先查 pkg-config
     变量（conan 生成的 gio-2.0.pc / glib-2.0.pc 没有 gdbus_codegen /
     glib_mkenums，meson 直接抛 "Could not get pkg-config variable"），而
     worker 的 /data/service/hnp/bin/gdbus-codegen 是 glib 2.38 的软链、
     shebang 指向不存在的 /usr/bin/python3，不可执行。因此 generate() 把
     ar/ranlib 与 glib 制品自带的 gdbus-codegen / glib-mkenums（与本包同为
     2.88.3）绝对路径写进 [binaries]（dconf / glib 同款处理）。
"""
import filecmp
import os
import shutil
import stat
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibgoaConan(ConanFile):
    name = "libgoa"
    version = "3.58.1"
    description = "GNOME Online Accounts client library (libgoa-1.0) over D-Bus"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/gnome-online-accounts"
    url = "https://gitlab.gnome.org/GNOME/gnome-online-accounts"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    # libgoa-1.0 不是 OHOS 系统同名库，允许动态库；上游 src/goa/meson.build
    # 固定使用 shared_library()，因此产物必然是共享库
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # goa-1.0.pc 的 Requires 是 gio-2.0 / glib-2.0，公开头文件包含 gio/gio.h
        self.requires("glib/2.88.3", transitive_headers=True, transitive_libs=True)
        # 不声明 dbus：goabackend=false 时构建图与链接都不用它（见文件头 2.）

    def build_requirements(self):
        # 制品仓已发布 meson/1.11.0；1.11.0.1 只在索引里可见，实际下载返回
        # "system acceleration policy not enabled"（R36/PF4 判定为未发布）
        self.tool_requires("meson/1.11.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _probe_tool(self, names, first_dir=""):
        """在已知目录 + PATH 上找工具，返回绝对路径或 None。"""
        dirs = []
        for d in (first_dir, "/data/service/hnp/bin",
                  os.path.expanduser("~/usr/local/bin")):
            if d and d not in dirs:
                dirs.append(d)
        for d in dirs:
            for name in names:
                cand = os.path.join(d, name)
                if os.path.isfile(cand):
                    return cand
        for name in names:
            cand = shutil.which(name)
            if cand:
                return cand
        return None

    def _inject_meson_binaries(self):
        """把构建工具的绝对路径注入 conan_meson_native.ini 的 [binaries]。

        (a) E012：MesonToolchain 不写 ar/ranlib，真机 hnp 工具链下 meson 报
            "Unable to detect linker"；
        (b) gnome.gdbus_codegen / gnome.mkenums_simple 会先查 pkg-config 变量
            gdbus_codegen / glib_mkenums，conan 生成的 .pc 里没有这两个变量，
            meson 抛 "Could not get pkg-config variable and no default"；
        (c) worker 自带 /data/service/hnp/bin/gdbus-codegen 是 glib 2.38 软链、
            shebang 指向不存在的 /usr/bin/python3，不可执行。
        故优先用与本包同版本的 glib 制品自带 bin/，失败再退回目录/PATH 探测。
        """
        ce = self.conf.get("tools.build:compiler_executables", default={},
                           check_type=dict) or {}
        cc = ce.get("c") or os.environ.get("CC") or ""
        cbindir = os.path.dirname(cc) if ("/" in cc or os.sep in cc) else ""

        binaries = {}
        ar = ce.get("ar") or self._probe_tool(("llvm-ar", "ar"), cbindir)
        rl = ce.get("ranlib") or self._probe_tool(("llvm-ranlib", "ranlib"), cbindir)
        if ar:
            binaries["ar"] = ar
        if rl:
            binaries["ranlib"] = rl

        try:
            glib_bin = os.path.join(self.dependencies["glib"].package_folder, "bin")
        except Exception:
            glib_bin = ""
        for tool in ("gdbus-codegen", "glib-mkenums"):
            cand = os.path.join(glib_bin, tool) if glib_bin else ""
            if cand and os.path.isfile(cand):
                binaries[tool] = cand
            else:
                found = self._probe_tool((tool,))
                if found:
                    binaries[tool] = found

        nf = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not (binaries and os.path.isfile(nf)):
            return
        with open(nf, encoding="utf-8") as f:
            content = f.read()
        if "[binaries]" not in content:
            return
        ins = ""
        for name, path in binaries.items():
            if "\n%s =" % name in content:
                continue
            ins += "%s = '%s'\n" % (name, path)
        if not ins:
            return
        with open(nf, "w", encoding="utf-8") as f:
            f.write(content.replace("[binaries]\n", "[binaries]\n" + ins, 1))
        self.output.info("libgoa: meson [binaries] injected: %s"
                         % ", ".join(sorted(binaries)))

    def generate(self):
        PkgConfigDeps(self).generate()

        tc = MesonToolchain(self)
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # 后端及其依赖未发布到制品仓，整体关闭
        tc.project_options["goabackend"] = "false"
        tc.project_options["exchange"] = "false"
        tc.project_options["fedora"] = "false"
        tc.project_options["google"] = "false"
        tc.project_options["imap_smtp"] = "false"
        tc.project_options["kerberos"] = "false"
        tc.project_options["owncloud"] = "false"
        tc.project_options["webdav"] = "false"
        tc.project_options["ms_graph"] = "false"
        # 文档/内省/Vala 需要 gi-docgen / gobject-introspection / valac，OHOS 不可用
        tc.project_options["documentation"] = "false"
        tc.project_options["introspection"] = "false"
        tc.project_options["vapi"] = "false"
        tc.project_options["man"] = "false"
        tc.generate()
        self._inject_meson_binaries()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    # ── OHOS ELF 重新签名 (E077 / E212) ──────────────────────────────────
    # 鸿蒙加载器只加载 .codesign 段有效的 ELF。meson 安装期会调用
    # mesonbuild/scripts/depfixer.py 就地改写 .dynstr（把 build rpath 清成
    # 'X'），使链接期写入的签名失效；此后任何 dlopen 都返回
    # "Permission denied"（test_package 里表现为
    # `Error loading shared library libgoa-1.0.so.0`）。
    # 因此安装后按「移除旧签名 → 重新签名 → 恢复权限」四步重签一次；
    # 与制品仓 glib/2.88.3 配方的 _sign_final_ohos_package 同法。
    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as stream:
                return stream.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _resolve_ohos_signing_tools(self):
        """在配置的 clang 同目录下解析 llvm-readelf/llvm-objcopy/binary-sign-tool。"""
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get("c") or ""
        compiler_dir = os.path.dirname(compiler) if "/" in str(compiler) else ""
        names = {
            "readelf": "llvm-readelf",
            "objcopy": "llvm-objcopy",
            "signer": "binary-sign-tool",
        }
        tools = {key: os.path.join(compiler_dir, name) if compiler_dir else ""
                 for key, name in names.items()}
        missing = [key for key, path in tools.items()
                   if not path or not os.path.isfile(path) or not os.access(path, os.X_OK)]
        if missing:
            if not can_run(self):
                self.output.info(
                    "PACKAGE_CODESIGN=NOT_RUN reason=cross_building; missing_tools=%s"
                    % ",".join(missing)
                )
                return None
            raise ConanInvalidConfiguration(
                "native OHOS package signing tools are missing: " + ", ".join(missing)
            )
        return tools

    @staticmethod
    def _run_signing_tool(arguments, label):
        completed = subprocess.run(
            arguments, stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
        if completed.returncode != 0:
            raise ConanInvalidConfiguration(
                "%s failed with exit code %s" % (label, completed.returncode)
            )
        return completed.stdout

    def _sign_ohos_elf(self, path, tools):
        if not os.path.isfile(path) or os.path.islink(path) or not self._is_elf(path):
            raise ConanInvalidConfiguration(
                "required final OHOS ELF is missing, linked, or invalid: %r" % path
            )
        original_mode = stat.S_IMODE(os.stat(path, follow_symlinks=False).st_mode)
        temporary = "%s.signing-%s" % (path, os.getpid())
        signed = "%s.signed-%s" % (path, os.getpid())
        if os.path.lexists(temporary) or os.path.lexists(signed):
            raise ConanInvalidConfiguration(
                "OHOS ELF signing temporary already exists for %r" % path
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
                [tools["signer"], "sign", "-inFile", temporary,
                 "-outFile", signed, "-selfSign", "1"],
                "OHOS ELF signer",
            )
            if not os.path.isfile(signed) or os.path.islink(signed):
                raise ConanInvalidConfiguration(
                    "OHOS ELF signer did not create a regular output: %r" % path
                )
            signed_sections = self._run_signing_tool(
                [tools["readelf"], "-S", signed], "post-sign readelf"
            ).decode("utf-8", errors="strict")
            if signed_sections.count(".codesign") != 1:
                raise ConanInvalidConfiguration(
                    "signed OHOS ELF must contain exactly one .codesign: %r" % path
                )
            if filecmp.cmp(temporary, signed, shallow=False):
                raise ConanInvalidConfiguration(
                    "OHOS ELF signer did not change the unsigned input: %r" % path
                )
            os.chmod(signed, original_mode | 0o755)
            os.replace(signed, path)
        finally:
            for candidate in (temporary, signed):
                if os.path.lexists(candidate):
                    os.unlink(candidate)

    def _sign_ohos_package(self):
        """对包内所有常规 ELF 重新签名（安装期 rpath 改写会使签名失效）。"""
        if str(self.settings.os) != "OHOS":
            return
        tools = self._resolve_ohos_signing_tools()
        if tools is None:
            return
        signed = []
        for directory, subdirectories, filenames in os.walk(self.package_folder):
            subdirectories.sort()
            for filename in sorted(filenames):
                path = os.path.join(directory, filename)
                if os.path.islink(path) or not self._is_elf(path):
                    continue
                self._sign_ohos_elf(path, tools)
                signed.append(path)
        self.output.info("PACKAGE_CODESIGN=PASS signed_elfs=%s" % len(signed))

    def package(self):
        meson = Meson(self)
        meson.install()
        # meson 安装期 depfixer 改写会让链接期 .codesign 失效，重签后才能加载
        self._sign_ohos_package()

    def package_info(self):
        # src/goa/meson.build: shared_library(goa_api_name, version: '0.0.0')
        #   -> lib/libgoa-1.0.so.0.0.0 (SONAME libgoa-1.0.so.0)
        # 共享库：把本包 lib/ 前置进 runenv 的 LD_LIBRARY_PATH，消费者
        # （test_package 的 conanrun）才能加载 libgoa-1.0.so.0。
        # 与制品仓内 glib / libayatana-common 等共享库配方同法。
        if self.options.shared and str(self.settings.os) in ("Linux", "OHOS"):
            self.runenv_info.prepend_path(
                "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
            )

        self.cpp_info.libs = ["goa-1.0"]
        # 上游 pkg.generate(subdirs: 'goa-1.0', extra_cflags:
        # '-I${libdir}/goa-1.0/include') 的等价物：公开头文件在
        # include/goa-1.0/goa/，生成的 goaconfig.h 在 lib/goa-1.0/include/，
        # 两者都要给，否则消费者 #include <goa/goa.h> 找不到头。
        self.cpp_info.includedirs = ["include/goa-1.0", "lib/goa-1.0/include"]
        # 上游 pkg.generate(filebase: 'goa-1.0') -> goa-1.0.pc
        self.cpp_info.set_property("pkg_config_name", "goa-1.0")
        # 公开头文件包含 gio/gio.h；与 goa-1.0.pc 的 Requires 保持一致。
        # glib 制品的 cpp_info 组件名是 glib / gobject / gio（pkg_config_name
        # 才是 glib-2.0 / gio-2.0），按组件名引用，否则 CMakeDeps 报
        # "Component 'glib::glib-2.0' not found in 'glib' package requirement"。
        self.cpp_info.requires = ["glib::glib", "glib::gio"]
