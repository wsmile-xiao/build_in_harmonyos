#!/usr/bin/env python3
"""Conan recipe — atkmm 2.36.4 (Meson)

Official C++ bindings for ATK, the accessibility toolkit (atkmm-2.36 ABI).
Native build on HarmonyOS PC (OHOS aarch64, clang 15, libc++). Meson drives
the build; the official tarball is a `meson dist` product that ships
generated bindings under untracked/, so mm-common / gmmproc are not required
(maintainer-mode=false).

Real upstream dependencies (atkmm-2.36.4/meson.build):
  - dependency('atk', version: '>= 2.33.3')
  - dependency('glibmm-2.68', version: '>= 2.68.0')  # glibmm 2.68 ABI line
pkg-config name: atkmm-2.36 (atkmm_api_version = '2.36').

NOTE: pangomm is NOT a dependency of atkmm (they are sibling mm bindings);
atkmm only requires atk + glibmm-2.68 (+ sigc++-3.0 transitively).

atkmm 2.36.4 ships no upstream tests in the meson build (no tests/ dir,
no test() registered — same as pangomm 2.50.1 tarball), so build() only
does configure+compile; consumer verification lives in test_package/.
"""
import glob
import os

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


class AtkmmConan(ConanFile):
    name = "atkmm"
    version = "2.36.4"
    description = "C++ bindings for ATK, the accessibility toolkit (atkmm-2.36)"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/atkmm"
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
        # atkmm 2.36.4 meson.build L117: glibmm-2.68 >= 2.68.0 (2.68 ABI line,
        # requires sigc++-3.0 transitively), atk >= 2.33.3.
        self.requires("glibmm/2.68.2", transitive_headers=True, transitive_libs=True)
        self.requires("atk/2.38.0.1", transitive_headers=True, transitive_libs=True)

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
        # 【skill: --pc-var 生成】atkmm 上游 meson.build L145 需要
        # glibmm_dep.get_variable('gmmprocdir')，PkgConfigDeps 只写标准变量，
        # 因此把缺失的变量写进生成的 glibmm-2.68.pc。
        _pc = os.path.join(self.generators_folder, "glibmm-2.68.pc")
        if os.path.isfile(_pc) and "gmmprocdir" not in open(_pc).read():
            with open(_pc, "a") as _f:
                _f.write("gmmprocdir=${libdir}/glibmm-2.68/proc\n")
        tc = MesonToolchain(self)
        # 产物为动态库：非系统同名库（libatkmm-2.36 不在 /lib、/lib64），
        # 由 Conan 管理依赖链（与 glibmm/pangomm 一致，默认 shared）。
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # Tarball 构建：generated bindings 已在 untracked/ 预生成，
        # 不需要 mm-common/gmmproc。
        tc.project_options["maintainer-mode"] = "false"
        # doxygen/dot/xsltproc 在 OHOS worker 上缺失；atkmm 2.36.4 的
        # meson_options.txt 无 build-tests 选项（tarball 无 tests/ 目录，
        # meson 下无注册测试）。
        tc.project_options["build-documentation"] = "false"
        # 禁止 meson 静默拉取 subprojects wrap（CI build 阶段无网络）。
        tc.project_options["wrap_mode"] = "nodownload"
        # 上游 meson.build 的 extra_defs_gen 用 cpp_compiler.find_library()
        # 查找 glibmm_generate_extra_defs-2.68，该库不在系统默认路径，
        # 需要把 glibmm libdir 加入链接器搜索路径（通过 conf 使 MesonToolchain
        # 写入 native 文件的 cpp_link_args / c_link_args）。（pangomm 同款技法）
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
        # atkmm 2.36.4 的 meson 未注册 test()（tarball 无 tests/ 目录），
        # 故无上游 meson 测试可执行；build() 只做 configure+compile。

    def package(self):
        Meson(self).install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        self._sign_shared_libs()

    def package_info(self):
        self.cpp_info.includedirs = [
            "include",
            "include/atkmm-2.36",
            "lib/atkmm-2.36/include",
        ]
        self.cpp_info.libs = ["atkmm-2.36"]
        self.cpp_info.set_property("pkg_config_name", "atkmm-2.36")

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
