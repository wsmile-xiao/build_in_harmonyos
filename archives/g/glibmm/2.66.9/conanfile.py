#!/usr/bin/env python3
"""Conan recipe — glibmm 2.66.9 (Meson)

C++ bindings for GLib (glibmm-2.4 / giomm-2.4). Native build on HarmonyOS
PC (OHOS aarch64, clang 15, libc++). Meson drives the build; the tarball is a
`meson dist` product that ships the generated bindings under untracked/
directories, so mm-common / gmmproc are not required (maintainer-mode=false).

⚠️ 版本裁决（修正 ADAPTATION.md 的错误前提）：libxml++ 2.42.3（旧 2.6 API 线，
   pc 名 libxml++-2.6）的 meson.build 探测 dependency('glibmm-2.4',
   version: '>= 2.32.0')，需要 glibmm-2.4.pc（2.4 ABI）。glibmm 2.66.x 是最后
   提供 glibmm-2.4.pc / libglibmm-2.4.so 的 2.4 ABI 线；glibmm 2.68+（含
   2.84.0）改为 glibmm-2.68 ABI（sigc++-3.0），不满足 libxml++ 2.x。
   故本配方固定 glibmm **2.66.9**。

Dependencies: glib/2.84.0.1 (components glib-2.0 / gobject-2.0 / gio-2.0) and
libsigc/2.10.8 (sigc++-2.0) — both already published to ohpcd (W0/R36 verified).
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.files import (
    apply_conandata_patches,
    collect_libs,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class GlibmmConan(ConanFile):
    name = "glibmm"
    version = "2.66.9"
    description = "C++ bindings for GLib (glibmm-2.4 / giomm-2.4)"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/glibmm"
    url = ""
    package_type = "library"

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

    def requirements(self):
        # glibmm 2.66.9 requires glib >= 2.61.2 and sigc++-2.0 >= 2.9.1.
        self.requires("glib/2.84.0.1")
        self.requires("libsigc/2.10.8")

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        sources = dict(self.conan_data["sources"])
        mirror_url = sources.pop("mirror_url", None)
        try:
            get(self, **sources, strip_root=True)
        except Exception as e:
            if not mirror_url:
                raise
            self.output.warning(f"Primary source failed ({e}), trying mirror")
            get(self, url=mirror_url, sha256=sources["sha256"], strip_root=True)

    def _inject_meson_binaries(self):
        """Write ar/ranlib + pkg-config full paths into the meson native file.

        MesonToolchain only maps the c/cpp entries of tools.build:compiler_executables,
        so meson probes ar/ranlib by bare name (llvm-ar) and pkg-config by PATH. The
        clang toolchain lives in /data/service/hnp/bin (not on PATH during conan
        create on some workers), and meson cannot see the PkgConfigDeps .pc files
        without a usable pkg-config.
        """
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        ar = ce.get("ar")
        rl = ce.get("ranlib")
        if not ar:
            compiler = ce.get("cpp") or ce.get("c") or ""
            bindir = os.path.dirname(compiler) if os.path.sep in compiler else ""
            if bindir:
                for name in ("llvm-ar", "ar"):
                    cand = os.path.join(bindir, name)
                    if os.path.isfile(cand):
                        ar = cand
                        break
                for name in ("llvm-ranlib", "ranlib"):
                    rlc = os.path.join(bindir, name)
                    if os.path.isfile(rlc):
                        rl = rlc
                        break
        pkg_config = self.conf.get("tools.gnu:pkg_config", default=None)
        if not pkg_config or not os.path.isfile(str(pkg_config)):
            pkg_config = shutil.which("pkg-config") or shutil.which("pkgconf")
        for nf_name in ("conan_meson_native.ini", "conan_meson_cross.ini"):
            nf = os.path.join(self.generators_folder, nf_name)
            if not os.path.isfile(nf):
                continue
            with open(nf) as f:
                content = f.read()
            if "[binaries]" not in content:
                continue
            extras = []
            if ar and "\nar =" not in content:
                extras.append("ar = '%s'" % ar)
                if rl:
                    extras.append("ranlib = '%s'" % rl)
            if pkg_config and "\npkg-config =" not in content and "\npkgconfig =" not in content:
                extras.append("pkg-config = '%s'" % pkg_config)
            if not extras:
                continue
            content = content.replace("[binaries]\n", "[binaries]\n" + "\n".join(extras) + "\n", 1)
            with open(nf, "w") as f:
                f.write(content)

    def _copy_gio_unix_pc(self):
        """giomm needs dependency('gio-unix-2.0'); glib pkg ships gio-unix-2.0.pc.

        Copy it into generators folder and rewrite prefix to the glib package root.
        """
        try:
            glib_dep = self.dependencies["glib"]
        except KeyError:
            return
        glib_pkg = glib_dep.package_folder
        if not glib_pkg:
            return
        src = os.path.join(glib_pkg, "lib", "pkgconfig", "gio-unix-2.0.pc")
        if not os.path.isfile(src):
            return
        with open(src, encoding="utf-8") as f:
            content = f.read()
        content = content.replace("prefix=/\n", "prefix={}\n".format(glib_pkg))
        content = content.replace("includedir=${prefix}/include\n",
                                  "includedir=${prefix}/include\n"
                                  "libdir=${prefix}/lib\n")
        dst = os.path.join(self.generators_folder, "gio-unix-2.0.pc")
        with open(dst, "w", encoding="utf-8") as f:
            f.write(content)
        self.output.info(
            "gio-unix-2.0.pc copied from glib pkg -> generators (prefix={})".format(glib_pkg)
        )

    def generate(self):
        PkgConfigDeps(self).generate()
        self._copy_gio_unix_pc()
        tc = MesonToolchain(self)
        # 产物为动态库：非系统同名库（libglibmm-2.4 / libgiomm-2.4 不在 /lib、/lib64），
        # R26 不适用，由 Conan 管理依赖链（与 glib/libsigc 一致，默认 shared）。
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # Tarball 构建：generated bindings 已在 untracked/ 预生成，
        # 不需要 mm-common/gmmproc。
        tc.project_options["maintainer-mode"] = "false"
        # doxygen/dot/xsltproc 在 OHOS worker 上缺失。
        tc.project_options["build-documentation"] = "false"
        # examples 与测试工具不在包内。
        tc.project_options["build-examples"] = "false"
        # 2.66.9 的 meson_options.txt 无 build-tests 选项（tests/ 无条件构建，
        # subdir('tests') 直接编译自包含 C++ 测试程序）。不得设置未知选项。
        # 禁止 meson 静默拉取 subprojects wrap（CI build 阶段无网络）。
        tc.project_options["wrap_mode"] = "nodownload"
        tc.generate()
        self._inject_meson_binaries()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        # ── 上游官方测试 ──
        # build() 保留 meson.test() 供 CI 静态门禁识别。交叉构建（build=Linux /
        # host=OHOS）时构建机不能 exec aarch64 二进制 → 跳过；原生 OHOS/HarmonyOS
        # 包装后附 --timeout-multiplier=16 --no-rebuild --no-suite=failing。
        if cross_building(self):
            self.output.info(
                "cross-building: skip meson.test() (OHOS binaries not runnable on build host)"
            )
        else:
            if os.uname().sysname in ("OHOS", "HarmonyOS"):
                build_folder = self.build_folder

                def _ohos_meson_test():
                    self.run(
                        'meson test -v -C "{}" --timeout-multiplier=16 '
                        "--no-rebuild --no-suite=failing".format(build_folder)
                    )

                meson.test = _ohos_meson_test
            meson.test()

    def package(self):
        Meson(self).install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        # 原生 OHOS worker：meson install 改写了 rpath，.so 需要重新 codesign
        # 才能 dlopen/执行（E135）。交叉 Docker SDK 无 binary-sign-tool → 跳过。
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        candidates_objcopy = [
            "/data/service/hnp/bin/llvm-objcopy",
            shutil.which("llvm-objcopy") or "",
        ]
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = ce.get("c") or ""
        if cc:
            candidates_objcopy.insert(0, os.path.join(os.path.dirname(cc), "llvm-objcopy"))
        objcopy = next((p for p in candidates_objcopy if p and os.path.isfile(p)), None)
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning("binary-sign-tool not found; skip OHOS codesign (cross/SDK env)")
            return
        for so in sos:
            if objcopy:
                self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=so))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=so))

    def package_info(self):
        # 头文件布局：include/glibmm-2.4 + include/giomm-2.4（公共头）+
        # lib/glibmm-2.4/include（构建期生成的 glibmmconfig.h，同 libsigc 模式）。
        self.cpp_info.set_property("cmake_file_name", "glibmm")
        glibmm_inc = ["include/glibmm-2.4", "lib/glibmm-2.4/include"]
        giomm_inc = ["include/giomm-2.4", "lib/giomm-2.4/include"]

        # glibmm-2.4：pkg-config 名与上游 .pc 一致（下游 meson dependency('glibmm-2.4')）。
        glibmm = self.cpp_info.components["glibmm-2.4"]
        glibmm.set_property("pkg_config_name", "glibmm-2.4")
        glibmm.set_property("cmake_target_name", "glibmm::glibmm-2.4")
        glibmm.libs = ["glibmm-2.4"]
        glibmm.includedirs = list(glibmm_inc)
        glibmm.requires = ["glib::glib-2.0", "glib::gobject-2.0", "libsigc::libsigc"]

        # giomm-2.4：GIO 的 C++ 绑定，单独 .pc（上游 giomm-2.4.pc Requires: glibmm-2.4）。
        giomm = self.cpp_info.components["giomm-2.4"]
        giomm.set_property("pkg_config_name", "giomm-2.4")
        giomm.set_property("cmake_target_name", "glibmm::giomm-2.4")
        giomm.libs = ["giomm-2.4"]
        giomm.includedirs = list(giomm_inc)
        giomm.requires = ["glibmm-2.4", "glib::glib-2.0", "glib::gobject-2.0",
                          "glib::gio-2.0", "libsigc::libsigc"]

        # 兜底：若未来布局变化导致组件 libs 为空，退回 collect_libs。
        if not any(c.libs for c in self.cpp_info.components.values()):
            self.cpp_info.libs = collect_libs(self)
