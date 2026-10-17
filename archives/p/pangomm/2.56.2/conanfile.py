#!/usr/bin/env python3
"""Conan recipe — pangomm 2.56.2 (Meson)

C++ bindings for Pango (pangomm-2.48). Native build on HarmonyOS PC
(OHOS aarch64, clang 15, libc++). Meson drives the build; the tarball is a
`meson dist` product that ships generated bindings under untracked/, so
mm-common / gmmproc are not required (maintainer-mode=false).

Real upstream dependencies (pangomm-2.56.2/meson.build):
  - dependency('pangocairo', version: '>= 1.56.0')     # provided by pango
  - dependency('cairomm-1.16', version: '>= 1.15.1')   # cairomm (1.16 ABI)
  - dependency('glibmm-2.68', version: '>= 2.68.0')    # glibmm 2.68 ABI line
  - dependency('giomm-2.68', version: '>= 2.68.0')     # glibmm 2.68 ABI line
  - python3 (meson >= 0.62.0; 2.56.x 门槛从 2.50.x 的 0.55.0 提高)
pkg-config name: pangomm-2.48 (pangomm_api_version = '2.48').

与 2.50.1 配方的差异（其余结构完全复用，见 2.50.1/notes 与本报告）：
  - pangocairo 下限 1.49.4 → 1.56.0（pango/1.56.4 提供 1.56.4，满足）；
  - meson 最低版本 0.62.0（本机/CI worker meson 1.11.x 满足）；
  - 测试体系不变：全部 meson.build 无 test() 注册，tests/ 仅空 autotools
    Makefile.am（SUBDIRS 为空），meson_options.txt 无 build-tests 选项。
"""
import glob
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class PangommConan(ConanFile):
    name = "pangomm"
    version = "2.56.2"
    description = "C++ bindings for Pango (pangomm-2.48)"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/pangomm"
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
        # pangomm 2.56.2 meson.build: glibmm-2.68 >= 2.68.0, giomm-2.68 >= 2.68.0,
        # cairomm-1.16 >= 1.15.1, pangocairo >= 1.56.0 (via pango).
        # glibmm 2.68 ABI line requires sigc++-3.0 / libsigc 3.x transitively
        # (由 glibmm/cairomm 配方声明，此处不重复)。
        # 全部为真实依赖，不依赖宿主机偶然存在的头文件/库。
        self.requires("glibmm/2.68.2")
        self.requires("cairomm/1.18.0")
        self.requires("pango/1.56.4")
        # 版本冲突对齐：pango/1.56.4 声明 fontconfig/2.18.1，而远端 cache 中
        # 2.18.1 二进制损坏（DT_NEEDED 烤死构建机绝对路径，见 cairomm/1.18.0
        # 与 2.50.1 配方注释），强制统一为已修复的 2.18.1.1。
        self.requires("fontconfig/2.18.1.1", override=True)

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
            pkg_config = shutil_which_pkg_config()
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

    def generate(self):
        PkgConfigDeps(self).generate()
        # 【skill: --alias-pc 生成】pango 的 PkgConfigDeps 只生成一个 pango.pc，
        # 但 pangomm 上游 meson.build 用 dependency('pangocairo') 查找。
        # PkgConfigDeps 不感知 components，需要手动创建转发型 .pc，且必须携带
        # Name/Description/Version 三字段（pkg-config 0.29.2 校验；meson 还需
        # version >= 1.56.0，2.56.2 提高的下限）。版本从 pango.pc 中读取。
        import os as _os
        _pango_pc = _os.path.join(self.generators_folder, "pango.pc")
        _pango_ver = "1.56.4"
        if _os.path.isfile(_pango_pc):
            for _line in open(_pango_pc):
                if _line.startswith("Version:"):
                    _pango_ver = _line.split(":", 1)[1].strip()
                    break
        for _al in ['pangocairo=pango', 'pangoft2=pango']:
            _pc, _req = _al.split("=", 1)
            _path = _os.path.join(self.generators_folder, _pc + ".pc")
            if not _os.path.isfile(_path):
                with open(_path, "w") as _f:
                    _f.write("Name: %s\nDescription: Conan package: %s\n"
                             "Requires: %s\nVersion: %s\n" % (_pc, _pc, _req, _pango_ver))
        # 【skill: --pc-var 生成】PkgConfigDeps 只写标准变量，pangomm 上游
        # meson.build 需要 glibmm_dep.get_variable('gmmprocdir')，
        # 因此把缺失的变量写进生成的 glibmm-2.68.pc。
        for _pv in ['glibmm-2.68:gmmprocdir=${libdir}/glibmm-2.68/proc']:
            _pc, _kv = _pv.split(":", 1)
            _path2 = _os.path.join(self.generators_folder, _pc + ".pc")
            if _os.path.isfile(_path2) and "gmmprocdir" not in open(_path2).read():
                with open(_path2, "a") as _f:
                    _f.write("%s\n" % _kv)
        tc = MesonToolchain(self)
        # 产物为动态库：非系统同名库（libpangomm-2.48 不在 /lib、/lib64），
        # 由 Conan 管理依赖链（与 glibmm/libsigc 一致，默认 shared）。
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # Tarball 构建：generated bindings 已在 untracked/ 预生成，
        # 不需要 mm-common/gmmproc。
        tc.project_options["maintainer-mode"] = "false"
        # doxygen/dot/xsltproc 在 OHOS worker 上缺失；pangomm 2.56.2 的
        # meson_options.txt 无 build-tests 选项（tests/ 仅有空 autotools
        # Makefile.am，meson 下无注册测试）。
        tc.project_options["build-documentation"] = "false"
        # 禁止 meson 静默拉取 subprojects wrap（CI build 阶段无网络）。
        tc.project_options["wrap_mode"] = "nodownload"
        # 上游 tools/extra_defs_gen/meson.build 的 extra_defs_gen 用
        # cpp_compiler.find_library() 查找 glibmm_generate_extra_defs-2.68，
        # 该库不在系统默认路径，需要把 glibmm libdir 加入链接器搜索路径
        # （通过 conf 使 MesonToolchain 写入 native 文件的 cpp_link_args /
        # c_link_args）。
        dep_glibmm = self.dependencies.get("glibmm")
        if dep_glibmm:
            _libdirs = dep_glibmm.cpp_info.libdirs
            for _ld in _libdirs:
                self.conf.define("tools.build:sharedlinkflags",
                                 self.conf.get("tools.build:sharedlinkflags", default=[]) + ["-L" + _ld])
                self.conf.define("tools.build:exelinkflags",
                                 self.conf.get("tools.build:exelinkflags", default=[]) + ["-L" + _ld])
        tc.generate()
        self._inject_meson_binaries()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        # pangomm 2.56.2 的 meson 未注册 test()（全部 meson.build grep test(
        # 零命中；tests/ 无 meson.build 入口，Makefile.am 的 SUBDIRS 为空），
        # 故无上游 meson 测试可执行；build() 只做 configure+compile，
        # 原因记录于 test_package/MANIFEST.yml 与 reports/。

    def package(self):
        Meson(self).install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        self._sign_shared_libs()

    def package_info(self):
        self.cpp_info.includedirs = [
            "include",
            "include/pangomm-2.48",
            "lib/pangomm-2.48/include",
        ]
        self.cpp_info.libs = ["pangomm-2.48"]
        self.cpp_info.set_property("pkg_config_name", "pangomm-2.48")

    def _sign_shared_libs(self):
        # 原生 OHOS worker：meson install 改写了 rpath，.so 需要重新 codesign
        # 才能 dlopen/执行（E135）。交叉 Docker SDK 无 binary-sign-tool → 跳过。
        if self.settings.os != "OHOS":
            return
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        sign_tool = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(sign_tool):
            self.output.warning("binary-sign-tool 不存在，跳过 .so 签名")
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        for so in sos:
            tmp_signed = so + ".signed"
            # 正确签名语法：sign -selfSign 1 -inFile X -outFile Y
            # （对 .so 先移除 .codesign 段再签名，与 abbtr/acme-client 既有做法一致）。
            if os.path.isfile(objcopy):
                self.run('"{}" --remove-section .codesign "{}" 2>/dev/null || true'.format(objcopy, so))
            self.run('"{}" sign -selfSign 1 -inFile "{}" -outFile "{}"'.format(sign_tool, so, tmp_signed))
            if os.path.isfile(tmp_signed):
                os.replace(tmp_signed, so)


def shutil_which_pkg_config():
    import shutil
    return shutil.which("pkg-config") or shutil.which("pkgconf")
