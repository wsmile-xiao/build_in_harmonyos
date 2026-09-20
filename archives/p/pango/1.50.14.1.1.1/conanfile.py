#!/usr/bin/env python3
"""Conan recipe — pango 1.50.14.1.1.1 (meson)

Text layout library with pangocairo (needed by simple-tiles).
OHOS: disable xft/introspection; alias cairo-ft.pc for Meson.
R37: adaptation fix revision over archived 1.50.14 (incomplete Conan).
R37: 1.50.14.1.1.1 — cairo pin 对齐 gtk3 生态 cairo/1.18.4.1（xlib 版，
避免 gtk3 图内 override 后 pango package_id 变化导致 CI 重建）+ 修复
_ohos_meson_test 的 LD_LIBRARY_PATH（前置 glib 等依赖 libdirs，规避 CI
worker 环境 _ci_o.../lib/external 的 libintl.so.8 遮蔽 g_libintl_* 符号）。
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.env import Environment
from conan.tools.files import (
    apply_conandata_patches,
    collect_libs,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class PangoConan(ConanFile):
    name = "pango"
    version = "1.50.14.1.1.1"
    description = "Pango text layout and rendering library"
    license = "LGPL-2.1-or-later"
    homepage = "https://www.pango.org/"
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
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def requirements(self):
        # 2026-08-22 (R37 递增 1.50.14.1 -> 1.50.14.1.1): gtk/3.24.43 依赖链顶层
        # 强制 glib shared=True（制品仓 glib/2.84.0.1 仅有 shared=True binary），
        # pango 与 harfbuzz 同步改为共享 glib 才能在 gtk 图中直接复用 binary。
        self.requires("glib/2.84.0.1", options={"shared": True})
        # CI 制品仓为裸 ref（无 @user/channel）；勿写 @ohpcd/stable，否则 remote 解析失败
        # harfbuzz 同步递增到 14.2.0.1.1.1（依赖项 PR #6195，同样绑定 glib shared=True）
        self.requires("harfbuzz/14.2.0.1.1.1")
        self.requires("cairo/1.18.4.1")
        self.requires("fribidi/1.0.16")
        self.requires("freetype/2.14.3")
        # force=True：制品仓仍可能解析到旧 cairo recipe（钉 fontconfig/2.18.1），
        # 与本仓 cairo/main 的 2.18.1.1 冲突。pango 直接依赖 fontconfig（pangoft2），
        # 需 force 压过传递依赖（同 pinocchio→boost 模式）。2.18.1.1 为同上游清理重打包。
        self.requires("fontconfig/2.18.1.1", force=True)

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
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        ar = ce.get("ar")
        rl = ce.get("ranlib")
        if not ar:
            cc = ce.get("c") or ""
            bindir = os.path.dirname(cc) if os.path.sep in cc else ""
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

    def _alias_cairo_ft_pc(self):
        # Meson wants cairo-ft; Conan cairo may only emit cairo.pc.
        gens = self.generators_folder
        src = os.path.join(gens, "cairo.pc")
        dst = os.path.join(gens, "cairo-ft.pc")
        if os.path.isfile(src) and not os.path.isfile(dst):
            text = open(src).read()
            lines = []
            for line in text.splitlines(True):
                if line.startswith("Name:"):
                    lines.append("Name: cairo-ft\n")
                elif line.startswith("Description:"):
                    lines.append("Description: Cairo FreeType font backend\n")
                else:
                    lines.append(line)
            open(dst, "w").write("".join(lines))

    def _fix_fribidi_pc(self):
        # Upstream fribidi.pc uses -I${includedir}/fribidi; Conan PkgConfigDeps
        # often emits only -I${includedir}, so #include <fribidi.h> fails.
        pc = os.path.join(self.generators_folder, "fribidi.pc")
        if not os.path.isfile(pc):
            return
        text = open(pc).read()
        if "/fribidi" in text.split("Cflags:", 1)[-1]:
            return
        for old, new in (
            ('Cflags: -I"${includedir}"', 'Cflags: -I"${includedir}" -I"${includedir}/fribidi"'),
            ("Cflags: -I${includedir}", "Cflags: -I${includedir} -I${includedir}/fribidi"),
        ):
            if old in text:
                text = text.replace(old, new, 1)
                break
        open(pc, "w").write(text)

    def _fix_glib_pc(self):
        # Conan PkgConfigDeps 生成的 glib-2.0.pc 不带 glib_mkenums 变量。
        # pango/meson.build 用 pkgconfig.generate(glib_dep, 'glib_mkenums') 取工具路径，
        # 而 meson 1.10.2 不支持 default_value 参数 → "Could not get pkg-config variable
        # and no default provided for glib-2.0"。补丁：在 bindir= 行后追加 glib_mkenums。
        pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if not os.path.isfile(pc):
            return
        text = open(pc).read()
        if "glib_mkenums=" in text:
            return
        lines = text.splitlines(True)
        out = []
        injected = False
        for line in lines:
            out.append(line)
            if not injected and line.startswith("bindir="):
                out.append("glib_mkenums=${bindir}/glib-mkenums\n")
                injected = True
        if not injected:
            out.append("glib_mkenums=${prefix}/bin/glib-mkenums\n")
        open(pc, "w").write("".join(out))

    def generate(self):
        PkgConfigDeps(self).generate()
        self._alias_cairo_ft_pc()
        self._fix_fribidi_pc()
        self._fix_glib_pc()
        # pango/meson needs build-machine glib-mkenums (from glib package bin/).
        glib_bin = os.path.join(self.dependencies["glib"].package_folder, "bin")
        if os.path.isdir(glib_bin):
            env = Environment()
            env.prepend_path("PATH", glib_bin)
            env.vars(self, scope="build").save_script("conanbuildenv_glib_tools")
        tc = MesonToolchain(self)
        tc.project_options["wrap_mode"] = "nodownload"
        tc.project_options["cairo"] = "enabled"
        tc.project_options["freetype"] = "enabled"
        tc.project_options["fontconfig"] = "enabled"
        tc.project_options["xft"] = "disabled"
        tc.project_options["introspection"] = "disabled"
        tc.project_options["gtk_doc"] = "false"
        tc.project_options["libthai"] = "disabled"
        tc.project_options["sysprof"] = "disabled"
        tc.project_options["install-tests"] = "false"
        tc.generate()
        self._inject_meson_binaries()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        # Upstream suite (no -Dtests off switch in 1.50.14).
        # Cross: skip — OHOS binaries not runnable on Linux build host (同 glib)。
        # Native OHOS/HarmonyOS: --no-suite=failing 排除补丁标入 failing suite 的
        # 8 个 fontconfig 环境失败用例（无 fonts.conf）；其它失败向上传播。
        if cross_building(self):
            self.output.info(
                "cross-building: skip meson.test() (OHOS binaries not runnable on build host)"
            )
        else:
            if os.uname().sysname in ("OHOS", "HarmonyOS"):
                build_folder = self.build_folder

                def _ohos_meson_test():
                    # R37(1.50.14.1.1.1): 直接运行测试二进制（绕开 meson test 的
                    # python 进程）。原因：libglib-2.0.so 的 g_libintl_* 符号来自 glib
                    # 包自带 libintl.so.8（依赖 libdirs 内），而 meson test 的 python
                    # 进程需标准 libintl.so.8（python 发行版，导出 libintl_*）——两个
                    # 同名 libintl.so.8 符号集不同，同一 LD_LIBRARY_PATH 无法共存
                    # （CI worker 的 _ci_o.../lib/external 注入 LD_LIBRARY_PATH 会使
                    # 测试二进制 exit 127）。→ 直接运行测试二进制，无需 python 参与。
                    import json as _json
                    import subprocess as _sp
                    _ld = []
                    for _dep in self.dependencies.host.values():
                        _pf = getattr(_dep, "package_folder", None)
                        if not _pf:
                            continue
                        for _sub in ("lib", "lib64"):
                            _p = os.path.join(_pf, _sub)
                            if os.path.isdir(_p):
                                _ld.append(_p)
                    _prev_ld = os.environ.get("LD_LIBRARY_PATH", "").strip()
                    os.environ["LD_LIBRARY_PATH"] = ":".join(
                        _ld + ([_prev_ld] if _prev_ld else []))
                    _src = os.path.join(self.source_folder, "tests")
                    _bld = os.path.join(self.build_folder, "tests")
                    _prev_env = {}
                    for _k, _v in (("G_TEST_SRCDIR", _src), ("G_TEST_BUILDDIR", _bld)):
                        if os.path.isdir(_v):
                            _prev_env[_k] = os.environ.get(_k)
                            os.environ[_k] = _v
                    try:
                        _tests = []
                        _intro = os.path.join(self.build_folder,
                                              "meson-info", "intro-tests.json")
                        if os.path.isfile(_intro):
                            with open(_intro, encoding="utf-8") as _f:
                                for _t in _json.load(_f):
                                    _suites = _t.get("suite") or []
                                    if any("failing" in _s for _s in _suites):
                                        continue  # 等价 --no-suite=failing
                                    _cmd = _t.get("cmd") or []
                                    if _cmd and os.path.isfile(_cmd[0]):
                                        _tests.append(_cmd)
                        if not _tests:
                            # intro-tests.json 缺失：回退 meson test（本地无遮蔽时可用）
                            self.run(
                                'meson test -v -C "{}" --timeout-multiplier=16 '
                                "--no-rebuild --no-suite=failing".format(build_folder))
                            return
                        _fail = 0
                        _skip = 0
                        for _cmd in _tests:
                            _p = _sp.run(_cmd, env=os.environ.copy(),
                                         stdout=open(os.devnull, "w"), stderr=_sp.STDOUT)
                            if _p.returncode == 77:
                                _skip += 1
                            elif _p.returncode != 0:
                                _fail += 1
                        self.output.info(
                            "_ohos_meson_test: %d run, %d failed, %d skipped"
                            % (len(_tests), _fail, _skip))
                        if _fail:
                            raise Exception(
                                "pango upstream tests: %d failed (see build log)"
                                % _fail)
                    finally:
                        for _k, _v in _prev_env.items():
                            if _v is None:
                                os.environ.pop(_k, None)
                            else:
                                os.environ[_k] = _v
                        if _prev_ld:
                            os.environ["LD_LIBRARY_PATH"] = _prev_ld
                        else:
                            os.environ.pop("LD_LIBRARY_PATH", None)

                meson.test = _ohos_meson_test
            meson.test()

    def package(self):
        Meson(self).install()
        self._sign_shared_libs()

    def _sign_shared_libs(self):
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
        self.cpp_info.set_property("cmake_file_name", "Pango")
        self.cpp_info.set_property("pkg_config_name", "pango-unofficial")
        inc = ["include", "include/pango-1.0"]

        pango = self.cpp_info.components["pango"]
        pango.set_property("pkg_config_name", "pango")
        pango.set_property("cmake_target_name", "Pango::Pango")
        pango.libs = ["pango-1.0"]
        pango.includedirs = list(inc)
        pango.requires = [
            "glib::glib-2.0",
            "glib::gobject-2.0",
            "harfbuzz::harfbuzz",
            "fribidi::fribidi",
        ]
        if self.settings.os in ("Linux", "OHOS"):
            pango.system_libs = ["m"]

        pangoft2 = self.cpp_info.components["pangoft2"]
        pangoft2.set_property("pkg_config_name", "pangoft2")
        pangoft2.set_property("cmake_target_name", "Pango::PangoFT2")
        pangoft2.libs = ["pangoft2-1.0"]
        pangoft2.includedirs = list(inc)
        pangoft2.requires = [
            "pango",
            "freetype::freetype",
            "fontconfig::fontconfig",
            "harfbuzz::harfbuzz",
        ]

        pangocairo = self.cpp_info.components["pangocairo"]
        pangocairo.set_property("pkg_config_name", "pangocairo")
        pangocairo.set_property("cmake_target_name", "Pango::PangoCairo")
        pangocairo.libs = ["pangocairo-1.0"]
        pangocairo.includedirs = list(inc)
        pangocairo.requires = ["pango", "pangoft2", "cairo::cairo"]

        if not self.cpp_info.components["pango"].libs:
            self.cpp_info.libs = collect_libs(self)
