#!/usr/bin/env python3
"""Conan recipe — pangomm 2.46.5 (Meson)

C++ bindings for Pango，旧 mm ABI 线（pkg-config `pangomm-1.4`）。
HarmonyOS PC 原生构建（OHOS aarch64, clang 15, libc++）。

上游真实依赖（pangomm-2.46.5/meson.build）：
  - dependency('pangocairo', version: '>= 1.45.1')   # 由 pango 提供
  - dependency('cairomm-1.0', version: '>= 1.2.2')   # cairomm 1.14.x ABI
  - dependency('glibmm-2.4',  version: '>= 2.48.0')  # glibmm 2.66.x ABI
  - python3, meson >= 0.60.0, c++11
发布物为 `meson dist` tarball，生成的绑定代码已在 untracked/ 预置，
因此不需要 mm-common / gmmproc（maintainer-mode=false）。

平台适配要点（均在 generate()/package() 内补齐，不改上游源码）：
  1. PkgConfigDeps 只写标准 pc 变量，上游 meson 需要
     glibmm_dep.get_variable('gmmprocdir') → 追加进 glibmm-2.4.pc；
  2. 上游用 dependency('pangocairo') 查找，补齐转发型 pangocairo.pc；
  3. 上游 extra_defs_gen 用 find_library('glibmm_generate_extra_defs-2.4')
     查库，把 glibmm libdir 注入链接搜索路径；
  4. OHOS 挂载点禁 symlink，meson install 的 .so/.so.N 链可能缺失 →
     package() 内物化（copyfile 幂等）；
  5. 原生 OHOS 上 meson install 改写 rpath，.so 需重新 codesign（E135）。
"""
import glob
import os
import re
import shutil

from conan import ConanFile
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
    version = "2.46.5"
    description = "C++ bindings for Pango (pangomm-1.4)"
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
        # pangocairo >= 1.45.1（经 pango）。这是 pangomm-1.4 旧 API 线：
        # glibmm/2.66.9 生成 glibmm-2.4.pc（旧 ABI 线），cairomm/1.14.5.1
        # 生成 cairomm-1.0.pc，pango/1.50.14.1.1 提供 pangocairo 组件，
        # 三者同处 sigc++-2.0 ABI。
        self.requires("glibmm/2.66.9")
        self.requires("cairomm/1.14.5.1")
        self.requires("pango/1.50.14.1.1")
        # 版本冲突对齐：glibmm/2.66.9 钉 libsigc/2.10.8，cairomm/1.14.5.1 钉
        # libsigc/2.12.1，Conan 2 无法自动归一化。sigc++-2.0 在 2.x 内 ABI 稳定
        # （SONAME libsigc-2.0.so.0），统一到 2.12.1（对齐制品仓 cairomm 已
        # 发布 binary）。package_id 变化使 glibmm 由 --build=missing 重建。
        self.requires("libsigc/2.12.1", override=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        sources = dict(self.conan_data["sources"])
        get(self, **sources, strip_root=True)

    def _inject_meson_binaries(self):
        """把 ar/ranlib 与 pkg-config 的完整路径写进 meson native 文件。

        MesonToolchain 只映射 tools.build:compiler_executables 的 c/cpp 项，
        meson 对 ar/ranlib 按裸名探测（llvm-ar），pkg-config 走 PATH。
        clang 工具链位于 /data/service/hnp/bin（某些 worker 上不在 PATH），
        且 meson 需要可用的 pkg-config 才能读到 PkgConfigDeps 生成的 .pc。
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
        # 上游 meson.build 用 dependency('pangocairo') 查找；PkgConfigDeps 为
        # pango 的组件生成 pangocairo.pc，为防旧行为只生成 pango.pc，这里幂等
        # 补转发 .pc（文件已存在则跳过）。pkg-config 0.29.2 要求
        # Name/Description/Version 三字段齐全，meson 还要求 version >= 1.45.1。
        _pango_pc = os.path.join(self.generators_folder, "pango.pc")
        _pango_ver = "1.50.14.1.1"
        if os.path.isfile(_pango_pc):
            for _line in open(_pango_pc):
                if _line.startswith("Version:"):
                    _pango_ver = _line.split(":", 1)[1].strip()
                    break
        for _al in ['pangocairo=pango', 'pangoft2=pango']:
            _pc, _req = _al.split("=", 1)
            _path = os.path.join(self.generators_folder, _pc + ".pc")
            if not os.path.isfile(_path):
                with open(_path, "w") as _f:
                    _f.write("Name: %s\nDescription: Conan package: %s\n"
                             "Requires: %s\nVersion: %s\n" % (_pc, _pc, _req, _pango_ver))
        # 上游 meson.build 需要 glibmm_dep.get_variable('gmmprocdir')，而
        # PkgConfigDeps 只写标准变量，需追加（取值同上游 glibmm.pc.in）。
        for _pv in ['glibmm-2.4:gmmprocdir=${libdir}/glibmm-2.4/proc']:
            _pc, _kv = _pv.split(":", 1)
            _path2 = os.path.join(self.generators_folder, _pc + ".pc")
            if os.path.isfile(_path2) and "gmmprocdir" not in open(_path2).read():
                with open(_path2, "a") as _f:
                    _f.write("%s\n" % _kv)
        tc = MesonToolchain(self)
        # 产物为动态库：非系统同名库（libpangomm-1.4 不在 /lib、/lib64），
        # 由 Conan 管理依赖链（与 glibmm/libsigc 一致，默认 shared）。
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # Tarball 构建：生成的绑定代码已在 untracked/ 预置，无需 mm-common。
        tc.project_options["maintainer-mode"] = "false"
        # doxygen/dot/xsltproc 在 OHOS worker 上缺失；pangomm 2.46.5 的
        # meson_options.txt 无 build-tests 选项。
        tc.project_options["build-documentation"] = "false"
        # 禁止 meson 静默拉取 subprojects wrap（CI build 阶段无网络）。
        tc.project_options["wrap_mode"] = "nodownload"
        # 上游 tools/extra_defs_gen/meson.build 用 cpp_compiler.find_library()
        # 查找 glibmm_generate_extra_defs-2.4，该库不在系统默认路径，需要把
        # glibmm libdir 加入链接器搜索路径（MesonToolchain 写入 native 文件）。
        dep_glibmm = self.dependencies.get("glibmm")
        if dep_glibmm:
            for _ld in dep_glibmm.cpp_info.libdirs:
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
        # pangomm 2.46.5 的 meson 未注册 test()：全部 meson.build grep test(
        # 零命中，meson_options.txt 无 build-tests 选项，tests/ 仅含 autotools
        # Makefile.am 且 SUBDIRS 为空 → 上游无 meson 测试可执行。
        # 消费者验证由 test_package/ 承担（L1 + 鸿蒙特有测试）。

    def package(self):
        Meson(self).install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        self._materialize_sonames()
        self._sign_shared_libs()

    def _materialize_sonames(self):
        # OHOS 挂载点（/storage 等）禁 symlink（EPERM），meson install 生成的
        # libfoo.so / libfoo.so.N 符号链接可能静默缺失，加载器按 DT_NEEDED 的
        # SONAME 查找落空（"Error loading shared library"）。在包内物化：
        # 对每个 lib*.so.N.M.K 实文件 copyfile 出 lib*.so.N 与 lib*.so
        # （已存在则跳过；Linux CI 真符号链接同样跳过，不改 CI 行为）。
        for _so in glob.glob(
                os.path.join(self.package_folder, "lib", "**", "*.so*"),
                recursive=True):
            _m = re.match(r"^(.*\.so)\.(\d+)\.(\d+)\.(\d+)$", _so)
            if not _m:
                continue
            _base, _major = _m.group(1), _m.group(2)
            for _target in (_base + "." + _major, _base):
                if not os.path.lexists(_target):
                    shutil.copyfile(_so, _target)

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
            # （先移除 .codesign 段再签，与 abbtr/acme-client 既有做法一致）。
            if os.path.isfile(objcopy):
                self.run('"{}" --remove-section .codesign "{}" 2>/dev/null || true'.format(objcopy, so))
            self.run('"{}" sign -selfSign 1 -inFile "{}" -outFile "{}"'.format(sign_tool, so, tmp_signed))
            if os.path.isfile(tmp_signed):
                os.replace(tmp_signed, so)


def shutil_which_pkg_config():
    return shutil.which("pkg-config") or shutil.which("pkgconf")
