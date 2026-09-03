#!/usr/bin/env python3
"""Conan recipe — gssdp 1.6.6 (Meson).

GSSDP — a GObject-based SSDP (Simple Service Discovery Protocol) library,
part of the GUPnP stack. Adapted to HarmonyOS PC (aarch64, musl, clang).
See notes.md for the platform adaptations and the shared cross-compile
handling inherited from libsoup3 3.6.5-r1 (same GLib meson stack).
"""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain


class GssdpConan(ConanFile):
    name = "gssdp"
    version = "1.6.6"
    description = "GSSDP — GObject-based SSDP (Simple Service Discovery Protocol) library"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/gssdp"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}
    generators = "PkgConfigDeps"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # gssdp meson.build deps: glib-2.0, gobject-2.0, gio-2.0 (all from the
        # glib2 package) and libsoup-3.0 (libsoup3). No libxml2 — gssdp itself
        # does not link libxml2 (that is a gupnp dependency, not gssdp).
        # ⚠️ libsoup3 (shared) links glib2 (static), whose libgio-2.0.a references
        # zlib. The published zlib/1.3.1 libz.a is NOT -fPIC and fails when linked
        # into a shared .so (R_AARCH64 relocation). Force the PIC variant
        # zlib/1.3.1.1 here at the ROOT level — a bare override inside libsoup3's
        # own requirements() is defeated by glib2's zlib/1.3.1 when libsoup3 is a
        # transitive dependency (conan 2.29 override resolution is order-sensitive
        # across the graph). Root-level override reliably pins zlib to 1.3.1.1.
        self.requires("zlib/1.3.1.1", override=True)
        self.requires("glib2/2.88.0")
        self.requires("libsoup3/3.6.5-r1")

    def build_requirements(self):
        # meson probes `ninja --version` during configure. The build profile
        # already prepends /storage/Users/currentUser/usr/local/bin (see
        # profiles/ohos-aarch64) where a static ninja lives on this host; the
        # registry ninja/1.12.1 binary needs libc++_shared.so at load time and
        # fails the probe in a clean env, so we deliberately do NOT
        # tool_requires it. CI workers ship their own system ninja.
        pass

    def layout(self):
        # meson_layout was removed in conan 2.29.x; replicate its folders here
        self.folders.build = "builddir"
        self.folders.generators = "builddir/generators"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # The CI worker exports AR/AS/STRIP/NM/RANLIB as llvm-* names (llvm-ar,
        # llvm-as, ...) that are NOT on its PATH — only the GNU binutils and
        # ld.lld exist. meson probes these and aborts at configure; pin the real
        # tools by ABSOLUTE PATH (resolved from PATH) and drop the broken env
        # values. (same fix as glib2/2.88.0 and libsoup3/3.6.5-r1 recipes)
        for _var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(_var, None)
        tools = {name: shutil.which(name) for name in ("ar", "as", "strip", "nm", "ranlib")}
        missing = [name for name, path in tools.items() if path is None]
        if missing:
            raise ConanInvalidConfiguration(
                f"Required build tools not in PATH: {', '.join(missing)}"
            )
        tc = MesonToolchain(self)
        tc.ar = tools["ar"]
        tc.as_ = tools["as"]
        # ⚠️ 绝不可 strip 共享库：OHOS loader 校验 .codesign 段内嵌哈希与文件内容
        # 是否一致，strip 会改写 .so 内容导致哈希失配，dlopen 报 Permission
        # denied（libsoup3 本地实验铁证，gssdp 同为 shared 库必须同样禁用）。
        tc.strip = None
        tc.binaries["nm"] = tools["nm"]
        tc.binaries["ranlib"] = tools["ranlib"]
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # gssdp meson options — all boolean: sniffer depends on gtk4 (disable),
        # introspection/vapi are gobject-introspection (cross-compile disable),
        # gtk_doc depends on gi-docgen (disable), manpages depends on pandoc
        # (not in toolchain — disable), examples are not needed for a lib.
        for opt in ("gtk_doc", "sniffer", "introspection", "vapi", "examples", "manpages"):
            tc.project_options[opt] = "false"

        # R8-compliant netlink suppression: the patch keys off this recipe-injected
        # feature macro (NOT a platform macro) so the recipe controls the cut.
        # Rationale: the OHOS sysroot's linux/socket.h and sys/socket.h both define
        # sockaddr_storage, so linux/netlink.h cannot even be included (compile-time
        # redefinition error — not detectable via meson feature detection because
        # the breakage is in the header include itself); HarmonyOS does not expose
        # netlink sockets. With the macro defined the code takes the same fallback
        # path as the upstream darwin/win branches (mac lookup returns the IP
        # string). Documented in notes.md.
        tc.c_args = ["-DGSSDP_NO_NETLINK"]
        tc.cpp_args = ["-DGSSDP_NO_NETLINK"]

        # meson needs the real .pc files (gobject-2.0/gio-2.0/gmodule-*.pc/...) from
        # the glib2 package — PkgConfigDeps only generates a single glib-2.0.pc
        # (glib2's pkg_config_name), and gssdp's meson.build requests
        # gobject-2.0/gio-2.0 as separate modules. Same approach as libsoup3.
        extra_pc = []
        glib2 = self.dependencies.get("glib2")
        if glib2 and glib2.package_folder:
            glib_pkg = glib2.package_folder
            extra_pc.append(os.path.join(glib_pkg, "lib", "pkgconfig"))
            # The glib2 package .pc files were installed with --prefix=/ so their
            # Cflags/Libs resolve to /include, /lib (broken). Copy them and fix
            # prefix to the real package folder; prepend so meson prefers these.
            pc_fix_dir = os.path.join(self.build_folder, "glib2-pc-fix")
            os.makedirs(pc_fix_dir, exist_ok=True)
            for pc in os.listdir(os.path.join(glib_pkg, "lib", "pkgconfig")):
                if not pc.endswith(".pc"):
                    continue
                src = os.path.join(glib_pkg, "lib", "pkgconfig", pc)
                dst = os.path.join(pc_fix_dir, pc)
                with open(src, "r", encoding="utf-8") as fh:
                    text = fh.read()
                text = re.sub(r"^prefix=.*$", f"prefix={glib_pkg}", text, count=1, flags=re.M)
                # ⚠️ GObject 单副本（R40 级平台适配）：ohpcd 只发布了 static glib2。
                # 如果按原样保留 .pc 的 Libs: -lglib-2.0 ...，meson 会把静态 glib
                # 链进 libgssdp.so、测试可执行文件也再链一份，加上 libsoup-3.0.so
                # 自带的副本，进程内出现 3 份 GObject → GType 注册撕裂
                # (g_type_register_static: assertion failed: static_quark_type_flags
                # / G_TYPE_IS_INITABLE false SIGABRT，本地铁证)。
                # 修法：把 GLib 系 .pc 的 Libs 行去掉（只留 Cflags），让 gssdp 与
                # 测试产物全部以 UND 引用 g_* 符号，运行时统一解析到已发布的
                # libsoup-3.0.so 导出的唯一 gobject 副本（其内部调用也走 PLT，
                # 可被自身导出符号解析）——全进程单 GObject 域，上游测试可跑通。
                # meson 链接时未解析符号由 libsoup-3.0.so 的导出表满足。
                if pc in ("glib-2.0.pc", "gobject-2.0.pc", "gio-2.0.pc",
                          "gmodule-2.0.pc", "gmodule-no-export-2.0.pc",
                          "gmodule-export-2.0.pc", "gthread-2.0.pc"):
                    text = re.sub(r"^Libs:.*$", "Libs: ", text, flags=re.M)
                    text = re.sub(r"^Libs\.private:.*$", "Libs.private: ", text, flags=re.M)
                with open(dst, "w", encoding="utf-8") as fh:
                    fh.write(text)
            extra_pc.insert(0, pc_fix_dir)
            # glib2 package bin holds the meson gnome module tools
            # (glib-mkenums — gssdp's libgssdp/meson.build uses gnome.mkenums()).
            # Pin them in the meson native file [binaries] section.
            glib_bin = os.path.join(glib_pkg, "bin")
            if os.path.isdir(glib_bin):
                self.buildenv_info.prepend_path("PATH", glib_bin)
                for tool in ("glib-mkenums", "glib-genmarshal", "gdbus-codegen",
                             "glib-compile-resources", "glib-compile-schemas"):
                    tool_path = os.path.join(glib_bin, tool)
                    if os.path.isfile(tool_path):
                        tc.binaries[tool] = tool_path
        tc.pkg_config_path = os.pathsep.join([tc.pkg_config_path] + extra_pc)
        tc.generate()
        # ⚠️ PkgConfigDeps 会在 generators/ 下生成一个 glib-2.0.pc（glib2 的
        # pkg_config_name），其 Libs 带全量静态 glib 链接列表，且 generators
        # 目录排在 pkg_config_path 最前——libsoup-3.0.pc 的 Requires: glib-2.0
        # 展开时会命中它，把静态 glib 再次链进测试可执行文件（GObject 多副本
        # 问题的最后一个入口）。generate() 之后改写它的 Libs 为空，与上面的
        # glib2-pc-fix 一致：g_* 一律 UND，运行时统一解析到 libsoup-3.0.so。
        gen_glib_pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if os.path.isfile(gen_glib_pc):
            with open(gen_glib_pc, "r", encoding="utf-8") as fh:
                text = fh.read()
            text = re.sub(r"^Libs:.*$", "Libs: ", text, flags=re.M)
            with open(gen_glib_pc, "w", encoding="utf-8") as fh:
                fh.write(text)

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        if cross_building(self):
            self.output.info(
                "cross-building: skip meson.test() (OHOS binaries are not runnable on the build host)"
            )
        else:
            if hasattr(os, "uname") and os.uname().sysname in ("OHOS", "HarmonyOS"):
                build_folder = self.build_folder

                def _ohos_meson_test():
                    # gssdp's two upstream tests do SSDP/UPnP on localhost; run
                    # them natively on the OHOS device with a generous timeout.
                    self.run(
                        'meson test -v -C "{}" --timeout-multiplier=16 '
                        "--no-rebuild".format(build_folder)
                    )

                meson.test = _ohos_meson_test

            meson.test()

    def package(self):
        meson = Meson(self)
        meson.install()
        # ⚠️ meson install 会清理 DT_RUNPATH：把 .dynstr 中的 rpath 路径字符串
        # 用 'X' 覆盖并删除 DT_RUNPATH 条目，改写 .so 内容使链接时写入的
        # .codesign 哈希失配（libsoup3 本地铁证）。用 build 目录的原始链接产物
        # 覆盖被修改的 .so，保证 dlopen 不报 Permission denied。
        if self.options.shared:
            for _lib in ("libgssdp-1.6.so.0.106.6",):
                _src = os.path.join(self.build_folder, "libgssdp", _lib)
                _dst = os.path.join(self.package_folder, "lib", _lib)
                if os.path.exists(_src):
                    shutil.copy2(_src, _dst)

    def package_info(self):
        self.cpp_info.libs = ["gssdp-1.6"]
        # gssdp headers are installed to include/gssdp-1.6/libgssdp/ (meson
        # install_headers subdir: gssdp-1.6/libgssdp); consumers use
        #   #include <libgssdp/gssdp.h>
        # so the include dir is include/gssdp-1.6.
        self.cpp_info.includedirs = ["include/gssdp-1.6"]
        self.cpp_info.system_libs = ["m", "pthread", "dl"]
        # gssdp public headers include glib/gio/gobject and libsoup headers;
        # CMakeDeps generates empty data for TRANSITIVE glib2/libsoup3 deps
        # (conan 2.29), so expose their include dirs + libs here to let consumers
        # compile/link (same approach as libsoup3).
        for depname in ("glib2", "libsoup3"):
            dep = self.dependencies.get(depname)
            if dep and dep.package_folder:
                self.cpp_info.includedirs.append(os.path.join(dep.package_folder, "include"))
                self.runenv_info.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib")
                )
                if depname == "glib2":
                    # glib-2.0 headers live in a nested include dir (+ the
                    # arch-specific glibconfig.h under lib/); only the glib2
                    # package has these. libsoup3's headers are flat under
                    # include/ and need no extra entries.
                    self.cpp_info.includedirs.append(
                        os.path.join(dep.package_folder, "include", "glib-2.0")
                    )
                    self.cpp_info.includedirs.append(
                        os.path.join(dep.package_folder, "lib", "glib-2.0", "include")
                    )
                self.cpp_info.libdirs.append(os.path.join(dep.package_folder, "lib"))
        # ⚠️ cpp_info.libs 只声明 gssdp-1.6 本体：glib/gobject/gio/soup 符号由
        # libgssdp-1.6.so 的 NEEDED libsoup-3.0.so 提供（该 .so 导出完整 glib
        # 符号表）。若把静态 glib 也写进 libs，CMakeDeps 会给消费者生成
        # -lglib-2.0 链接，静态 glib 被链进消费者可执行文件 → 与 libsoup-3.0.so
        # 内嵌的 gobject 形成双副本，GObject 类型系统撕裂（GType 注册
        # SIGABRT，本地铁证）——即 test_package 空壳崩根因。
        for _lib in ("gssdp-1.6",):
            if _lib not in self.cpp_info.libs:
                self.cpp_info.libs.append(_lib)
        self.runenv_info.prepend_path("LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib"))
        # PkgConfigDeps picks up pkg_config_name; CMakeDeps (test_package) needs
        # cmake_file_name + cmake_target_name set explicitly.
        self.cpp_info.set_property("pkg_config_name", "gssdp-1.6")
        self.cpp_info.set_property("cmake_file_name", "gssdp-1.6")
        self.cpp_info.set_property("cmake_target_name", "gssdp-1.6::gssdp-1.6")
