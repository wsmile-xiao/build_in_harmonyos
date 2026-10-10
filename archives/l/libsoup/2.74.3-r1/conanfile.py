#!/usr/bin/env python3
"""Conan recipe — libsoup 2.74.3-r1 (Meson).

libsoup 2.74.3-r1 = shared-glib release form fix（与 libsoup3/3.6.5-r3 同类）。
已发布的 libsoup/2.74.3 依赖 glib2/2.88.0（该包 shared=False，仅发布静态库），
把 glib/gobject 静态链入 libsoup-2.4.so.1 —— 产物 DT_NEEDED 无
libglib-2.0.so.0 / libgobject-2.0.so.0，本体导出 4113 个 g_* 定义符号。
当依赖图里同时存在共享 glib/2.84.0.1.1（librest/json-glib 链，NEEDED
libgobject-2.0.so.0）时，两份 GObject 类型系统在同一进程竞争注册 →
g_param_spec_pool_lookup: assertion 'pool != NULL' failed → SIGABRT
（librest 0.10.2.1 soup2 变体 7/10 上游测试全崩，实测）。

本版本改为依赖共享 glib/2.84.0.1.1，使 libsoup-2.4.so.1 链接共享
libgobject-2.0.so.0，全依赖图只保留一份共享 glib（单 GObject 副本）。

因 cnb.cool 制品仓不允许同一 name/version 并存两个 recipe revision（规则 R37），
已发布的 libsoup/2.74.3 不能原地改，故以独立版本号 2.74.3-r1 重发（与平台
libsoup3/3.6.5-r1..r3 的版本命名法一致）。
"""
import os
import re
import shlex
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain

# OHOS HMFS refuses to exec an ELF straight out of the read-only conan package
# cache (EPERM, which ninja surfaces as exit code 126); the fix is to stage a
# copy into the build folder, drop the stale .codesign section and self-sign it.
HNP_BIN = "/data/service/hnp/bin"
SIGN_TOOL = os.path.join(HNP_BIN, "binary-sign-tool")
OBJCOPY = os.path.join(HNP_BIN, "llvm-objcopy")


class LibsoupConan(ConanFile):
    name = "libsoup"
    version = "2.74.3-r1"
    description = ("libsoup is an HTTP client/server library for GNOME, based on "
                   "GLib (shared-glib release form fix)")
    license = "LGPL-2.0-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/libsoup"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}
    generators = "PkgConfigDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # ⚠️ 必须共享 glib：见文件头。用 glib/2.84.0.1.1（shared）替代 glib2/2.88.0
        # （静态），使 libsoup-2.4.so.1 链接共享 libgobject-2.0.so.0，与
        # librest/json-glib 链共用同一份共享 glib（单 GObject 副本）。
        self.requires("glib/2.84.0.1.1", options={"shared": True},
                      transitive_headers=True, transitive_libs=True)
        self.requires("libpsl/0.21.5.1")
        self.requires("libxml2/2.15.3")
        self.requires("sqlite3/3.49.1")
        self.requires("brotli/1.2.0")
        self.requires("libnghttp2/1.70.0")
        # glib/2.84.0.1.1 自身已 pin zlib/1.3.1.1（-fPIC），无需再 override。
        # （原 2.74.3 配方为 glib2/*:shared 触发的 zlib 非 PIC 问题而 override，
        # 改用共享 glib 后该问题不再出现——同 libsoup3/3.6.5-r3。）

    def layout(self):
        self.folders.build = "builddir"
        self.folders.generators = "builddir/generators"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # The CI worker exports AR/AS/STRIP/NM/RANLIB as llvm-* names (llvm-ar,
        # ...) that are NOT on its PATH — only the GNU binutils and ld.lld exist.
        # meson probes these and aborts at configure; pin the real tools by
        # ABSOLUTE PATH (resolved from PATH) and drop the broken env values.
        for _var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(_var, None)
        tools = {name: shutil.which(name) for name in ("ar", "as", "strip", "nm", "ranlib")}
        missing = [name for name, path in tools.items() if path is None]
        if missing:
            raise ConanInvalidConfiguration(f"Required build tools not in PATH: {', '.join(missing)}")
        # lld (LLVM linker) depends on libxml2.so.16; the shared lib lives in
        # the OHOS SDK's llvm/lib dir but lld has no RPATH to find it. Locate
        # the SDK llvm/lib dir from clang's real path and add to LD_LIBRARY_PATH
        # so meson linker detection succeeds. 必须用 buildenv_info.prepend_path
        # 持久化到 conan 构建环境（conanbuild.sh），Meson 运行时才会带上。
        clang_path = shutil.which("clang")
        if clang_path:
            clang_real = os.path.realpath(clang_path)
            llvm_lib = os.path.join(os.path.dirname(os.path.dirname(clang_real)), "lib")
            if os.path.isdir(llvm_lib):
                self.buildenv_info.prepend_path("LD_LIBRARY_PATH", llvm_lib)
                os.environ["LD_LIBRARY_PATH"] = (
                    llvm_lib + os.pathsep + os.environ.get("LD_LIBRARY_PATH", "")
                )
        # ninja（meson 后端）与 lld 同为 HNP 工具链二进制，NEEDED libc++_shared.so；
        # conan 构建环境把 LD_LIBRARY_PATH 覆盖为依赖包 lib 目录后 ninja 加载
        # libc++ 失败 → meson 检测不到 Ninja。加回 /system/lib64。
        self.buildenv_info.prepend_path("LD_LIBRARY_PATH", "/system/lib64")
        os.environ["LD_LIBRARY_PATH"] = (
            "/system/lib64" + os.pathsep + os.environ.get("LD_LIBRARY_PATH", "")
        )
        tc = MesonToolchain(self)
        tc.ar = tools["ar"]
        tc.as_ = tools["as"]
        # OHOS loader validates .codesign hash against file content; strip
        # rewrites .so content → hash mismatch → dlopen Permission denied.
        tc.strip = None
        tc.binaries["nm"] = tools["nm"]
        tc.binaries["ranlib"] = tools["ranlib"]
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # 构建上游测试二进制（规则5 要求真实运行上游测试并提供证据）
        tc.project_options["tests"] = "true"
        tc.project_options["installed_tests"] = "false"
        # glib-networking (TLS backend) is not packaged on OHOS; libsoup meson
        # asserts at configure when tls_check is enabled — disable the check.
        tc.project_options["tls_check"] = "false"
        tc.project_options["gnome"] = "false"
        # feature options -> "disabled" (not available on OHOS)
        for opt in ("vapi", "introspection", "gssapi", "ntlm", "sysprof"):
            tc.project_options[opt] = "disabled"
        tc.project_options["gtk_doc"] = "false"

        extra_pc = []
        # glib 包提供 meson 探测需要的真实 .pc（gio/gmodule-no-export-2.0/
        # gio-unix-2.0 等）；PkgConfigDeps 只生成 glib-2.0/gobject-2.0/gio-2.0/
        # gmodule-2.0/gthread-2.0。把 glib 包 lib/pkgconfig 下全部 .pc 复制并
        # 修正 prefix（包安装时用了 --prefix=/，Cflags/Libs 会解析到 /include、
        # /lib，损坏）。
        glib = self.dependencies.get("glib")
        if glib and glib.package_folder:
            glib_pkg = glib.package_folder
            glib_pc_dir = os.path.join(glib_pkg, "lib", "pkgconfig")
            pc_fix_dir = os.path.join(self.build_folder, "glib-pc-fix")
            os.makedirs(pc_fix_dir, exist_ok=True)
            if os.path.isdir(glib_pc_dir):
                for pc in os.listdir(glib_pc_dir):
                    if not pc.endswith(".pc"):
                        continue
                    with open(os.path.join(glib_pc_dir, pc), "r", encoding="utf-8") as fh:
                        text = fh.read()
                    text = re.sub(r"^prefix=.*$", f"prefix={glib_pkg}", text, count=1, flags=re.M)
                    with open(os.path.join(pc_fix_dir, pc), "w", encoding="utf-8") as fh:
                        fh.write(text)
            extra_pc.append(glib_pc_dir)
            extra_pc.insert(0, pc_fix_dir)
            # 用官方 glib-2.0.pc（修正 prefix、去 Requires.private）覆盖
            # PkgConfigDeps 生成的简化版：后者 Libs 缺 -lintl，而 libsoup 的
            # soup-init.c 经 glib i18n 宏直接引用 g_libintl_bindtextdomain /
            # g_libintl_gettext，-Wl,--no-undefined 下 ld.lld 报 undefined
            # symbol（gtk4 / libsoup3 配方同机制）。Requires.private 引用的
            # libpcre2-8 等 .pc 不在本图 PkgConfigDeps 输出里，须删除该行。
            _official = os.path.join(glib_pc_dir, "glib-2.0.pc")
            if os.path.isfile(_official):
                with open(_official, "r", encoding="utf-8") as _fh:
                    _text = _fh.read()
                _text = re.sub(r"^prefix=.*$", f"prefix={glib_pkg}", _text, count=1, flags=re.M)
                _text = re.sub(r"^Requires\.private:.*$", "", _text, count=1, flags=re.M)
                with open(os.path.join(self.generators_folder, "glib-2.0.pc"), "w", encoding="utf-8") as _fh:
                    _fh.write(_text)
                self.output.info("glib-2.0.pc: overridden with official package .pc (adds -lintl)")
            # glib 包 bin/ 内的 meson gnome 模块工具。glib-mkenums /
            # glib-genmarshal / gdbus-codegen 是 python3 脚本，可以从只读包
            # 缓存直接 exec，pin 到 native [binaries] 即可。但
            # glib-compile-resources 是 OHOS **ELF**：HMFS 拒绝从只读包缓存
            # 直接执行（EPERM，ninja 报 exit 126 —— 2.74.3 用 glib2/2.88.0
            # 时该工具是 python 脚本故无此问题，改依赖共享 glib/2.84.0.1.1 后
            # 才暴露）。须 stage 到 build 目录、去 .codesign 段后重签，并用 sh
            # wrapper 注入 LD_LIBRARY_PATH（该 ELF NEEDED 共享
            # libglib/gio/gobject 且无 RPATH）。同一处理见平台
            # libgmobile/0.7.2、glade、gnumeric。
            glib_bin = os.path.join(glib_pkg, "bin")
            if os.path.isdir(glib_bin):
                self.buildenv_info.prepend_path("PATH", glib_bin)
                for tool in ("glib-mkenums", "glib-genmarshal", "gdbus-codegen"):
                    tool_path = os.path.join(glib_bin, tool)
                    if os.path.isfile(tool_path):
                        tc.binaries[tool] = tool_path
                staged = self._stage_glib_elf_tools()
                for tool, wrapper in staged.items():
                    tc.binaries[tool] = wrapper
                self._augment_gio_pkg_config(staged)

        # 其余依赖（libpsl/libxml2/sqlite3/brotli/libnghttp2 等）的 .pc 复制并
        # 重写 prefix，避免指向已失效的构建路径（与 2.74.3 一致，推广到全部依赖）；
        # 禁止回退系统 /usr/local pkg-config（DT_NEEDED 含绝对路径、产物不可移植）。
        pc_fix_dir = os.path.join(self.build_folder, "deps-pc-fix")
        os.makedirs(pc_fix_dir, exist_ok=True)
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            _pc_dir = os.path.join(dep.package_folder, "lib", "pkgconfig")
            if not os.path.isdir(_pc_dir):
                continue
            for pc in os.listdir(_pc_dir):
                if not pc.endswith(".pc"):
                    continue
                with open(os.path.join(_pc_dir, pc), "r", encoding="utf-8") as fh:
                    text = fh.read()
                text = re.sub(r"^prefix=.*$", f"prefix={dep.package_folder}",
                              text, count=1, flags=re.M)
                with open(os.path.join(pc_fix_dir, pc), "w", encoding="utf-8") as fh:
                    fh.write(text)
        # generators 目录（含被覆盖的官方 glib-2.0.pc）排在最前，优先于复制目录。
        extra_pc.insert(0, pc_fix_dir)
        tc.pkg_config_path = os.pathsep.join([tc.pkg_config_path] + extra_pc)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()

    def package(self):
        meson = Meson(self)
        meson.install()
        # meson install may strip DT_RUNPATH from .so files, causing OHOS
        # loader .codesign hash mismatch. Copy original build artifacts.
        for _lib in ("libsoup-2.4.so.1.11.2",):
            _src = os.path.join(self.build_folder, "libsoup", _lib)
            _dst = os.path.join(self.package_folder, "lib", _lib)
            if os.path.exists(_src):
                shutil.copy2(_src, _dst)

    def package_info(self):
        self.cpp_info.libs = ["soup-2.4"]
        self.cpp_info.includedirs = ["include/libsoup-2.4"]
        self.cpp_info.system_libs = ["m", "pthread", "dl"]
        # libsoup public headers include glib/gio/gobject headers; CMakeDeps
        # generates empty data for the TRANSITIVE glib dep (conan 2.29), so
        # expose glib's include dirs + libs here to let consumers compile/link.
        glib = self.dependencies.get("glib")
        if glib and glib.package_folder:
            self.cpp_info.includedirs.append(os.path.join(glib.package_folder, "include"))
            self.cpp_info.includedirs.append(os.path.join(glib.package_folder, "include", "glib-2.0"))
            self.cpp_info.includedirs.append(os.path.join(glib.package_folder, "lib", "glib-2.0", "include"))
            self.cpp_info.libdirs.append(os.path.join(glib.package_folder, "lib"))
            for _lib in ("glib-2.0", "gobject-2.0", "gio-2.0", "gmodule-2.0", "gthread-2.0"):
                if _lib not in self.cpp_info.libs:
                    self.cpp_info.libs.append(_lib)
            self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(glib.package_folder, "lib"))
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
        self.cpp_info.set_property("pkg_config_name", "libsoup-2.4")
        self.cpp_info.set_property("cmake_file_name", "libsoup-2.4")
        self.cpp_info.set_property("cmake_target_name", "libsoup-2.4::libsoup-2.4")

    # ─────────────────── glib ELF build-tool staging ───────────────────
    # 与平台 libgmobile/0.7.2 完全同机制（glade / gnumeric / at-spi2-core 亦同）。
    def _glib_tools_folder(self):
        return os.path.join(self.build_folder, "glib-native-tools")

    def _find_host_tool(self, tool_name):
        for dependency in self.dependencies.host.values():
            candidate = os.path.join(dependency.package_folder, "bin", tool_name)
            if os.path.isfile(candidate):
                return candidate
        return shutil.which(tool_name)

    def _dependency_libdirs(self):
        """Existing ``lib`` directories of every host dependency, deduplicated."""
        libdirs = []
        for dependency in self.dependencies.host.values():
            for libdir in dependency.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dependency.package_folder, libdir)
                if os.path.isdir(libdir) and libdir not in libdirs:
                    libdirs.append(libdir)
        return libdirs

    def _resign_build_tool(self, binary):
        """Drop the stale .codesign section and self-sign (HMFS exec rule)."""
        if not os.path.isfile(OBJCOPY) or not os.path.isfile(SIGN_TOOL):
            raise ConanInvalidConfiguration(
                f"OHOS signing tools missing: {OBJCOPY} / {SIGN_TOOL}")
        self.run(f"{shlex.quote(OBJCOPY)} --remove-section .codesign "
                 f"{shlex.quote(binary)}")
        self.run(shlex.join([SIGN_TOOL, "sign", "-inFile", binary,
                             "-outFile", binary, "-selfSign", "1"]))

    def _stage_glib_elf_tools(self):
        """Make glib's ELF build tools runnable from the build folder.

        ``glib-compile-resources`` (libsoup/meson.build 与 tests/meson.build 的
        ``gnome.compile_resources`` 在 build 期调用它）是 OHOS ELF，HMFS 拒绝
        直接从只读包缓存执行（EPERM / exit 126）。复制到 build 目录并重签即可
        执行；该 ELF NEEDED 共享 libglib/gio/gobject 且无 RPATH，故用 ``sh``
        wrapper 注入 LD_LIBRARY_PATH（导出**全部**依赖 lib 目录，工具后续
        spawn 的子进程继承环境也能解析 conan 库）。
        """
        tools_folder = self._glib_tools_folder()
        os.makedirs(tools_folder, exist_ok=True)
        libdirs = self._dependency_libdirs()
        staged = {}
        for tool in ("glib-compile-resources",):
            source = self._find_host_tool(tool)
            if not source:
                raise ConanInvalidConfiguration(
                    f"build tool not found in any dependency bin/ dir: {tool}")
            target = os.path.join(tools_folder, tool)
            shutil.copyfile(source, target)
            os.chmod(target, 0o755)
            if self.settings.os == "OHOS":
                self._resign_build_tool(target)
            wrapper = target + ".sh"
            own = os.path.join(os.path.dirname(os.path.dirname(source)), "lib")
            search = [own] + [d for d in libdirs if d != own]
            quote = lambda value: "'" + str(value).replace("'", "'\\''") + "'"
            with open(wrapper, "w", encoding="utf-8", newline="\n") as handle:
                handle.write("#!/bin/sh\n"
                             f"export LD_LIBRARY_PATH={quote(os.pathsep.join(search))}"
                             ":$LD_LIBRARY_PATH\n"
                             f"exec {quote(target)} \"$@\"\n")
            os.chmod(wrapper, 0o755)
            staged[tool] = wrapper
        self.output.info(f"staged + re-signed glib ELF tools: {staged}")
        return staged

    def _augment_gio_pkg_config(self, staged_tools):
        """Point gio-2.0.pc's glib_compile_resources at the staged wrapper.

        meson 的 gnome 模块经
        ``find_tool('glib-compile-resources', 'gio-2.0', 'glib_compile_resources')``
        解析资源编译器：先问 dependency('gio-2.0').get_variable(pkgconfig: ...)。
        PkgConfigDeps 生成的简化版 gio-2.0.pc 无该变量，须补上；否则 meson 会
        回退到包缓存里的 ELF（EPERM）。generators_folder 在 PKG_CONFIG_PATH
        最前，故此处的变量优先于 glib 包自带的官方 gio-2.0.pc。
        """
        pc_file = os.path.join(self.generators_folder, "gio-2.0.pc")
        if not os.path.isfile(pc_file):
            raise ConanInvalidConfiguration(
                f"generated {pc_file} not found (needed for glib_compile_resources)")
        with open(pc_file, encoding="utf-8") as handle:
            content = handle.read()
        if "glib_compile_resources=" in content:
            return
        wrapper = staged_tools["glib-compile-resources"].replace(os.sep, "/")
        content = content.rstrip("\n") + f"\nglib_compile_resources={wrapper}\n"
        with open(pc_file, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        self.output.info("gio-2.0.pc: glib_compile_resources -> staged wrapper")
