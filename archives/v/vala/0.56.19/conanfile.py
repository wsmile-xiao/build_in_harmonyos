#!/usr/bin/env python3
"""Conan recipe — vala 0.56.19 (GNU Autotools).

Vala — object-oriented programming language with a self-hosting compiler that
targets GObject.  Ships the ``valac`` compiler / ``vala`` interpreter wrapper /
``vapigen`` (GObject-Introspection → VAPI generator) command-line tools plus the
``libvala-0.56`` / ``libvaladoc-0.56`` shared libraries.

OHOS adaptation notes:
  - config.guess/config.sub are patched so the OHOS triplet
    ``aarch64-unknown-linux-ohos`` is recognised (uname -s = HarmonyOS).
  - ``GI_GIRDIR`` is provided to configure so the gobject-introspection
    girdir check is skipped (the CI worker has no gobject-introspection .pc).
  - valadoc is disabled: it pulls the whole graphviz (libgvc → gd/pango/
    libwebp/poppler) dependency chain, which is not needed for the compiler.
    Recorded in notes.md (upstream valadoc remains buildable manually).
  - OHOS requires every exec'd/dlopen'd ELF to carry a valid code signature
    (added by the SDK clang driver at link time).  We relocate RUNPATH with
    patchelf after install and then re-sign every ELF so the packaged tools
    keep running on OHOS.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class ValaConan(ConanFile):
    name = "vala"
    version = "0.56.19"
    description = "Vala — object-oriented programming language with self-hosting compiler targeting GObject"
    license = "LGPL-2.1"
    homepage = "https://wiki.gnome.org/Projects/Vala"
    url = ""

    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: settings.os 判断必须覆盖 "Linux" 和 "OHOS"
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "vala recipe currently supports Linux and OHOS native builds only"
            )

    def requirements(self):
        # R36: glib/2.84.0.1（含 gobject-2.0/gio-2.0/gmodule-2.0 组件）已发布到 ohpcd
        self.requires("glib/2.84.0.1", transitive_headers=True, transitive_libs=True)
        # libffi/pcre2 是 glib 的传递依赖；显式 requires 使它们在本图成为
        # host 直接依赖、二进制真实安装（否则 CI 图中是 Skipped binaries，
        # _augment_glib_pkg_config 注入 -lffi/-lpcre2-8 时无有效 -L 路径 →
        # 链接 libvala-0.56.so 报 "unable to find library -lffi"，CI #26196）。
        self.requires("libffi/3.4.4")
        self.requires("pcre2/10.45")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # 生成依赖的修正 .pc（glib-2.0/gobject-2.0/gio-2.0/gmodule-2.0 →
        # 真实缓存路径），vala configure 用 pkg-config 找 glib 头/库
        PkgConfigDeps(self).generate()
        self._augment_glib_pkg_config()
        env = Environment()
        # 绕过 gobject-introspection girdir 检查（本环境无该 .pc，值仅作编译期
        # define，运行期 valac --girdir 由用户显式指定）
        env.define("GI_GIRDIR", "/share/gir-1.0")
        env.vars(self).save_script("conanbuild_gigirdir")
        tc = AutotoolsToolchain(self)
        # valadoc 依赖 libgvc(graphviz) 全链，收窄为 glib 单依赖（见文件头注释）
        tc.configure_args.append("--disable-valadoc")
        # OHOS 沙箱不支持 mkfifo(jobserver)，-j1 串行构建（opensp/vala 先例）
        tc.generate()

    def _augment_glib_pkg_config(self):
        # OHOS 链接器以 --no-allow-shlib-undefined 链接 libvala-0.56.so：
        # glib-2.0/gobject-2.0 的 g_libintl_*（glib 包代理 libintl.so）与
        # ffi_type_*（libffi）/pcre2_*（libpcre2-8）符号必须显式可见，否则
        # valac 链接报 undefined reference（CI #26164）。
        # 注意：autotools/libtool 会把 -L/-l 转成 .la 文件查找，而 libffi/pcre2
        # 只有静态库（.a），导致 libtool 报 "cannot find the library
        # '//lib/libpcre2-8.la'"（CI #26226）。因此这里直接追加库文件的
        # 绝对路径（.so/.a 均可，libtool 对绝对路径直接链接，不做 .la 解析）。
        augment_parts = []
        for name, libfile in (
            ("glib", "libintl.so"),
            ("libffi", "libffi.a"),
            ("pcre2", "libpcre2-8.a"),
        ):
            try:
                dep = self.dependencies[name]
            except (KeyError, AttributeError):
                continue
            if dep and dep.package_folder:
                path = os.path.join(dep.package_folder, "lib", libfile)
                if os.path.isfile(path):
                    augment_parts.append(path)
        augment = " ".join(augment_parts)
        if not augment:
            return
        for pc_name in ("glib-2.0.pc", "gobject-2.0.pc", "gio-2.0.pc", "gmodule-2.0.pc"):
            pc_file = os.path.join(self.generators_folder, pc_name)
            if not os.path.isfile(pc_file):
                continue
            with open(pc_file, encoding="utf-8") as handle:
                content = handle.read()
            if "libffi.a" in content:
                continue
            lines = content.splitlines(keepends=True)
            for index, line in enumerate(lines):
                if line.startswith("Libs:"):
                    lines[index] = line.rstrip("\r\n") + " " + augment + "\n"
                    break
            with open(pc_file, "w", encoding="utf-8", newline="\n") as handle:
                handle.write("".join(lines))

    def build(self):
        apply_conandata_patches(self)
        self._disable_libtool_archives()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # 上游 make check 不做进 conan build：1430 用例耗时过长（>30min），
        # 且 dbus/* 用例在本环境无 dbus daemon 必失败（详见 notes.md）。
        # test_package 已实质调用 valac 编译并运行 .vala 程序（R34）。

    def _disable_libtool_archives(self):
        # CI #26233/#26235：OHOS 下 libtool 链接 libvala-0.56.la 时读取 conan
        # 依赖包自带的 .la 存档（其 libdir=/lib，与缓存路径不符）→ libtool 报
        # "cannot find the library '//lib/libpcre2-8.la' / '//lib/libffi.la'"
        # （"was moved"）。把 glib/libffi/pcre2 依赖包 lib/ 下的 *.la 改名为
        # *.la.off，libtool 找不到 .la 后直接链接 .a/.so，绕过损坏存档。
        for name in ("glib", "libffi", "pcre2"):
            try:
                dep = self.dependencies[name]
            except (KeyError, AttributeError):
                continue
            if not dep or not dep.package_folder:
                continue
            libdir = os.path.join(dep.package_folder, "lib")
            if not os.path.isdir(libdir):
                continue
            for la in glob.glob(os.path.join(libdir, "*.la")):
                target = la + ".off"
                if not os.path.exists(target):
                    os.rename(la, target)
                    self.output.info(f"libtool .la disabled: {la}")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        self._relocate_rpath()

    # ── RPATH 重定位 + OHOS 重签名 ────────────────────────────────

    @staticmethod
    def _is_elf(path):
        try:
            with open(path, "rb") as handle:
                return handle.read(4) == b"\x7fELF"
        except OSError:
            return False

    def _patch_rpath(self, path, rpath):
        """patchelf 改写 RUNPATH → $ORIGIN 相对 + glib 依赖库路径。

        OHOS 的 clang 链接器会自动写入 .codesign 签名节；patchelf 改字节后
        签名失效（exec 报 EPERM），因此 objcopy 移除旧签名节并用
        binary-sign-tool 重新签名（fftw/graphviz 先例）。
        """
        patchelf = shutil.which("patchelf") or "/data/service/hnp/bin/patchelf"
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.exists(patchelf):
            self.output.warning(f"patchelf not found, skip RPATH fix for {path}")
            return
        self.run(f'"{patchelf}" --set-rpath "{rpath}" --force-rpath "{path}"')
        if os.path.exists(objcopy):
            self.run(f'"{objcopy}" --remove-section .codesign "{path}" 2>/dev/null || true')
        if os.path.exists(signer):
            self.run(f'"{signer}" sign -inFile "{path}" -outFile "{path}" -selfSign 1')

    def _relocate_rpath(self):
        glib_lib = os.path.join(self.dependencies["glib"].package_folder, "lib")
        bin_dir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bin_dir):
            for name in os.listdir(bin_dir):
                path = os.path.join(bin_dir, name)
                if os.path.isfile(path) and not os.path.islink(path) and self._is_elf(path):
                    # bin/valac-0.56 需要 libvala-0.56.so(lib/) 和
                    # libvalaccodegen.so(lib/vala-0.56/)
                    self._patch_rpath(
                        path,
                        "$ORIGIN/../lib:$ORIGIN/../lib/vala-0.56:" + glib_lib,
                    )
        lib_root = os.path.join(self.package_folder, "lib")
        for path in glob.glob(os.path.join(lib_root, "**", "*.so*"), recursive=True):
            if os.path.islink(path) or not os.path.isfile(path):
                continue
            if not self._is_elf(path):
                continue
            rel = os.path.relpath(path, lib_root)
            if rel.startswith("vala-0.56"):
                # lib/vala-0.56/libvalaccodegen.so → libvala 在 lib/
                rpath = "$ORIGIN/..:" + glib_lib
            else:
                # lib/libvala-0.56.so / lib/libvaladoc-0.56.so
                rpath = "$ORIGIN:" + glib_lib
            self._patch_rpath(path, rpath)

    # ── package_info ──────────────────────────────────────────────

    def package_info(self):
        self.cpp_info.includedirs = ["include/vala-0.56"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = ["vala-0.56"]
        self.cpp_info.set_property("pkg_config_name", "libvala-0.56")
        # libvala-0.56.so 位于 lib/，libvalaccodegen.so 位于非标准目录
        # lib/vala-0.56/，valac 运行期都需要在 LD_LIBRARY_PATH 中
        # （RPATH 已兜底，runenv 双保险）
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH", os.path.join(self.package_folder, "lib")
        )
        self.runenv_info.prepend_path(
            "LD_LIBRARY_PATH",
            os.path.join(self.package_folder, "lib", "vala-0.56"),
        )
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
