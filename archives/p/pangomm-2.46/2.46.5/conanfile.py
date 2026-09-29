#!/usr/bin/env python3
"""Conan recipe — pangomm-2.46 2.46.5 (Meson)

C++ bindings for Pango (pangomm-1.4, legacy mm ABI line). Native build on
HarmonyOS PC (OHOS aarch64, clang 15, libc++). Meson drives the build; the
tarball ships generated bindings under untracked/, so mm-common / gmmproc
are not required (maintainer-mode=false).

pangomm 2.46.x is the last release of the legacy mm ABI line (parallel to
the new pangomm-2.48/2.50 lines). Real upstream dependencies
(pangomm-2.46.5/meson.build):
  - dependency('pangocairo', version: '>= 1.45.1')      # provided by pango
  - dependency('cairomm-1.0', version: '>= 1.2.2')      # cairomm 1.14.x ABI
  - dependency('glibmm-2.4', version: '>= 2.48.0')      # glibmm 2.66.x ABI
  - python3 >= 3.5, meson >= 0.60.0
pkg-config name: pangomm-1.4 (pangomm_api_version = '1.4').

glibmm 2.66.x builds the legacy ABI (configure.ac:
MM_INIT_MODULE([glibmm-2.4])), so the repo's glibmm/2.66.9 emits
glibmm-2.4.pc and satisfies the requirement directly; likewise cairomm
1.14.x emits cairomm-1.0.pc.
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
    name = "pangomm-2.46"
    version = "2.46.5"
    description = "C++ bindings for Pango (pangomm-1.4, legacy ABI line)"
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
        # pangomm 2.46.5 meson.build: glibmm-2.4 >= 2.48.0, cairomm-1.0 >= 1.2.2,
        # pangocairo >= 1.45.1 (via pango).
        # glibmm 2.66.x 即旧 ABI 线（configure.ac MM_INIT_MODULE([glibmm-2.4])），
        # 其包名与 pc 名均为 glibmm-2.4；cairomm 1.14.x 同理生成 cairomm-1.0。
        # 本包不含 giomm 依赖（pangomm 2.46 无 gio 绑定）。
        self.requires("glibmm/2.66.9")
        self.requires("cairomm/1.14.5.1")
        self.requires("pango/1.56.4")
        # 版本冲突对齐：glibmm/2.66.9 钉 libsigc/2.10.8，cairomm/1.14.5.1 钉
        # libsigc/2.12.1。sigc++-2.0 在 2.x 内 ABI 稳定（SONAME libsigc-2.0.so.0），
        # 强制统一为较新的 2.12.1。
        self.requires("libsigc/2.12.1", override=True)
        # 版本冲突对齐：pango/1.56.4 依赖链中 fontconfig/2.18.1 与 cache 中的
        # 2.18.1.1 冲突，强制统一为 2.18.1.1（与已发布依赖一致）。
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
        # 但 pangomm 上游 meson.build 用 dependency('pangocairo') 和
        # dependency('pango') 分别查找。PkgConfigDeps 不感知 components，
        # 需要手动创建转发型 .pc，且必须携带 Name/Description/Version 三字段
        # （pkg-config 0.29.2 校验；meson 还需 version >= 1.45.1）。
        # 版本从 pango.pc 中读取。
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
        # meson.build L123 需要 glibmm_dep.get_variable('gmmprocdir')，
        # 因此把缺失的变量写进生成的 glibmm-2.4.pc（上游 glibmm 2.66.9 的
        # glibmm.pc.in 同款取值：gmmprocdir=${libdir}/glibmm-2.4/proc）。
        for _pv in ['glibmm-2.4:gmmprocdir=${libdir}/glibmm-2.4/proc']:
            _pc, _kv = _pv.split(":", 1)
            _path2 = _os.path.join(self.generators_folder, _pc + ".pc")
            if _os.path.isfile(_path2) and "gmmprocdir" not in open(_path2).read():
                with open(_path2, "a") as _f:
                    _f.write("%s\n" % _kv)
        tc = MesonToolchain(self)
        # 产物为动态库：非系统同名库（libpangomm-1.4 不在 /lib、/lib64），
        # 由 Conan 管理依赖链（与 glibmm/libsigc 一致，默认 shared）。
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # Tarball 构建：generated bindings 已在 untracked/ 预生成，
        # 不需要 mm-common/gmmproc。
        tc.project_options["maintainer-mode"] = "false"
        # doxygen/dot/xsltproc 在 OHOS worker 上缺失；pangomm 2.46.5 的
        # meson_options.txt 无 build-tests 选项（tests/ 仅有 autotools Makefile.am，
        # meson 下无注册测试）。
        tc.project_options["build-documentation"] = "false"
        # 禁止 meson 静默拉取 subprojects wrap（CI build 阶段无网络）。
        tc.project_options["wrap_mode"] = "nodownload"
        # 上游 meson.build 的 extra_defs_gen 用 cpp_compiler.find_library()
        # 查找 glibmm_generate_extra_defs-2.4，该库不在系统默认路径，
        # 需要把 glibmm libdir 加入链接器搜索路径（通过 conf 使 MesonToolchain
        # 写入 native 文件的 cpp_link_args / c_link_args）。
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
        # pangomm 2.46.5 的 meson 未注册 test()（tests/ 无 meson.build 入口），
        # 故无上游 meson 测试可执行；build() 只做 configure+compile。

    def package(self):
        Meson(self).install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        self._materialize_sonames()
        self._sign_shared_libs()

    def _materialize_sonames(self):
        # 【skill: --soname 物化】/storage 等 OHOS 挂载点禁 symlink（EPERM），
        # meson install 的 libfoo.so / libfoo.so.N 符号链接静默缺失，加载器按
        # DT_NEEDED 的 SONAME 查找落空（"Error relocating"/"Error loading
        # shared library"，kea-hook 同款实坑）。包内物化：对每个
        # lib*.so.N.M.K 实文件 copyfile 出 lib*.so.N 与 lib*.so（幂等跳过已
        # 存在；Linux CI 的真符号链接同样跳过，不改 CI 行为）。
        import shutil as _shutil
        import re as _re
        for _so in glob.glob(
                os.path.join(self.package_folder, "lib", "**", "*.so*"),
                recursive=True):
            _m = _re.match(r"^(.*\.so)\.(\d+)\.(\d+)\.(\d+)$", _so)
            if not _m:
                continue
            _base, _major = _m.group(1), _m.group(2)
            for _target in (_base + "." + _major, _base):
                if not os.path.lexists(_target):
                    _shutil.copyfile(_so, _target)

    def package_info(self):
        self.cpp_info.includedirs = [
            "include",
            "include/pangomm-1.4",
            "lib/pangomm-1.4/include",
        ]
        self.cpp_info.libs = ["pangomm-1.4"]
        self.cpp_info.set_property("pkg_config_name", "pangomm-1.4")

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
