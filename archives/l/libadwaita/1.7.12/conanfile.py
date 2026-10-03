#!/usr/bin/env python3
"""Conan recipe — libadwaita 1.7.12 (Meson).

libadwaita is the GNOME Adwaita theme widget library built on GTK4.
On HarmonyOS PC (aarch64) it is a pure library (no binaries), built
against the published ohpcd gtk4/4.22.4 (Broadway backend) + glib
chain. Meson build; introspection/vapi/gtk_doc/examples are disabled
for the OHOS cross build; upstream tests are compiled with -Dtests=true.

Compared to the previously adapted 1.2.0:
- glib_min_version raised to >= 2.80.0 (satisfied by glib/2.84.0.1.1)
- gtk_min_version raised to >= 4.17.5 (satisfied by gtk4/4.22.4)
- new hard dependency on appstream (AdwAboutDialog from AppStream
  metadata, src/adw-about-dialog.c includes <appstream.h>) →
  appstream/1.2.0 from ohpcd.
"""
import os
import shutil
import time

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibadwaitaConan(ConanFile):
    name = "libadwaita"
    version = "1.7.12"
    description = "libadwaita — GNOME Adwaita theme widgets for GTK4 (OHOS adaptation)"
    license = "LGPL-2.1-or-later"
    homepage = "https://gitlab.gnome.org/GNOME/libadwaita"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # libadwaita's src/stylesheet/meson.build needs sassc to compile
        # base.scss → base.css (only when base.css is absent from the source
        # tree, which is the case for git-archive tarballs). On OHOS there is
        # no git subproject clone (meson would try `git clone
        # github.com/lazka/sassc.git` and fail), so provide the published
        # ohpcd sassc/3.6.2 as a build-time tool → meson find_program('sassc')
        # succeeds and the subproject branch is skipped.
        if self._conanfile_requires_sassc():
            self.tool_requires("sassc/3.6.2")

    def _conanfile_requires_sassc(self):
        return True

    def requirements(self):
        # libadwaita 1.7.12 meson dependency() names → conan packages:
        #   gtk4 (>= 4.17.5) → gtk4/4.22.4 (transitive headers/libs so the
        #       consumer-facing headers' gtk4 includes resolve)
        #   glib-2.0/gio-2.0 → glib/2.84.0.1.1 shared=True — the SAME graph
        #       constraint gtk4/4.22.4 uses (override=True unifies the
        #       pango/harfbuzz/cairo-gobject/graphene glib pins; .1.1's
        #       bin tools are codesigned so glib-compile-resources etc. run
        #       on OHOS — the plain 2.84.0.1 package ships a broken
        #       (unsigned) tool binary: "Operation not permitted").
        #   fribidi           → fribidi/1.0.16 (transitive)
        #   appstream         → appstream/1.2.0 (new in 1.7.12; AdwAboutDialog
        #       reads AppStream metadata; fallback would subproject-clone and
        #       fail on OHOS, so the published ohpcd package is required).
        self.requires("gtk4/4.22.4", transitive_headers=True, transitive_libs=True)
        self.requires("glib/2.84.0.1.1", options={"shared": True}, override=True)
        # gtk4 recipe pins the whole graph onto one zlib/fontconfig revision;
        # propagate the same pins so this graph resolves identically.
        self.requires("zlib/1.3.1.1", override=True)
        self.requires("fontconfig/2.18.1.1", override=True)
        self.requires("fribidi/1.0.16", transitive_headers=True, transitive_libs=True)
        self.requires("appstream/1.2.0")
        # gtk4/4.22.4 requires pango >= 1.56 (meson), but appstream/1.2.0
        # directly requires pango/1.50.14 (no force) → graph conflict.
        # Align the whole graph onto gtk4's pango/1.56.4 (same override the
        # gtk4 recipe applies); 1.50.14 predates gtk4's requirement.
        self.requires("pango/1.56.4", transitive_headers=True, transitive_libs=True, override=True)
        # appstream/1.2.0 requires zstd/1.5.7.1 while its other deps
        # (vips/libxmlb chain) pull zstd/1.5.7 → graph conflict. Pin the
        # published 1.5.7.1 so the whole graph resolves to one zstd.
        self.requires("zstd/1.5.7.1", override=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # MesonToolchain doesn't write ar/ranlib into the native file from
        # tools.build:compiler_executables; meson then probes bare llvm-ar
        # (not on PATH on OHOS — clang toolchain is in /data/service/hnp/bin).
        # Pin the real tools by ABSOLUTE PATH and drop broken env values.
        for _var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(_var, None)
        tools = {name: shutil.which(name) for name in ("ar", "as", "strip", "nm", "ranlib")}
        missing = [name for name, path in tools.items() if path is None]
        if missing:
            raise ConanInvalidConfiguration(
                f"Required build tools not found in PATH: {', '.join(missing)}"
            )
        # appstream 链 libxmlb 配方组件 requires 引用 glib::glib/gobject/gio/gmodule
        # （无 -2.0 后缀，针对 glib/2.88.3 组件键编写），而本图 glib/2.84.0.1.1
        # 组件键为 glib-2.0/gobject-2.0/gio-2.0/gmodule-2.0 → 为 glib 依赖 cpp_info
        # 补无后缀别名键（指向同一组件对象），使 PkgConfigDeps 解析 libxmlb 引用时
        # 不报 "Component 'glib::gobject' not found"（appstream 配方同款注入先例）。
        _gd = (getattr(self, "dependencies", None) or {}).get("glib")
        if _gd is not None:
            for _suffix, _plain in (
                ("glib-2.0", "glib"),
                ("gobject-2.0", "gobject"),
                ("gio-2.0", "gio"),
                ("gmodule-2.0", "gmodule"),
            ):
                if _suffix in _gd.cpp_info.components and _plain not in _gd.cpp_info.components:
                    _gd.cpp_info.components[_plain] = _gd.cpp_info.components[_suffix]
        PkgConfigDeps(self).generate()
        self._fix_glib_pc_intl()
        tc = MesonToolchain(self)
        # OHOS: disable introspection/vapi/gtk_doc/examples (no GI/Vala/display
        # on the cross target); keep tests enabled for the upstream suite.
        tc.project_options["introspection"] = "disabled"
        tc.project_options["vapi"] = "false"
        tc.project_options["gtk_doc"] = "false"
        tc.project_options["examples"] = "false"
        tc.project_options["tests"] = "true"
        tc.generate()
        self._inject_meson_archiver()
        self._patch_pc_datadir()
        self._prepend_glib_bin_to_path()
        self._fix_fribidi_pc()

    def _fix_glib_pc_intl(self):
        # glib 包内真实 glib-2.0.pc 的 Libs 为 `-lglib-2.0 -lintl`（glib 包自带
        # libintl.so.8，导出 g_libintl_* 前缀符号；E142 proxy-libintl 机制）。
        # conan PkgConfigDeps 生成的 glib-2.0.pc 只带 `-lglib-2.0 -lm -lpthread
        # -ldl`，缺 `-lintl` → 链接 libadwaita-1.so 时 g_libintl_gettext 等符号
        # 未定义（ld.lld undefined symbol: g_libintl_*）。追加 -lintl（指向
        # ${libdir} 即 glib 包 lib 目录，链接器按 -L 找到 libintl.so.8）。
        _pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if not os.path.isfile(_pc):
            self.output.warning("fix glib-2.0.pc -lintl: file not generated, skip")
            return
        with open(_pc, encoding="utf-8") as _f:
            _txt = _f.read()
        if "-lintl" in _txt:
            return
        if "Libs:" not in _txt:
            return
        _txt = _txt.replace("Libs:", "Libs: -lintl", 1)
        with open(_pc, "w", encoding="utf-8") as _f:
            _f.write(_txt)
        self.output.info("glib-2.0.pc: appended -lintl to Libs")

    def _fix_fribidi_pc(self):
        # fribidi.h lives in include/fribidi/ (meson dependency('fribidi')
        # compiles adw-bidi.c with `#include <fribidi.h>`); the PkgConfigDeps
        # generated fribidi.pc only carries -I${includedir} — same issue gtk4
        # fixed. Append the subdir include to Cflags.
        _pc = os.path.join(self.generators_folder, "fribidi.pc")
        if not os.path.isfile(_pc):
            return
        with open(_pc, encoding="utf-8") as _f:
            _txt = _f.read()
        if "-I${includedir}/fribidi" in _txt:
            return
        if "Cflags:" in _txt:
            _txt = _txt.replace("Cflags:", "Cflags: -I${includedir}/fribidi", 1)
        else:
            _txt += "Cflags: -I${includedir}/fribidi\n"
        with open(_pc, "w", encoding="utf-8") as _f:
            _f.write(_txt)
        self.output.info("fribidi.pc: appended -I${includedir}/fribidi to Cflags")

    def _prepend_glib_bin_to_path(self):
        # glib/2.84.0.1.1 shared: the glib package's bin tools
        # (glib-compile-resources / glib-compile-schemas / glib-mkenums / …)
        # are OHOS aarch64 ELF executables whose linker-time .codesign is
        # stale — OHOS XPM exec rejects them with "Operation not permitted"
        # (ninja FAILED [code=126]). Re-sign them in-place (same ML-0043
        # pattern as gtk4) so gnome.compile_resources can run. They also have
        # no RPATH, so glib's own shared libs must be on LD_LIBRARY_PATH at
        # exec time ("Error loading shared library libgio-2.0.so.0").
        import os as _os
        _g = (getattr(self, "dependencies", None) or {}).get("glib")
        if not _g or not getattr(_g, "package_folder", None):
            return
        _gbin = _os.path.join(_g.package_folder, "bin")
        _glib = _os.path.join(_g.package_folder, "lib")
        if _os.path.isdir(_gbin):
            _os.environ["PATH"] = _gbin + _os.pathsep + _os.environ.get("PATH", "")
            self.output.info("PATH prepended with glib bin: %s" % _gbin)
        _os.environ["LD_LIBRARY_PATH"] = _glib + _os.pathsep + _os.environ.get("LD_LIBRARY_PATH", "")
        self.output.info("LD_LIBRARY_PATH prepended with glib lib: %s" % _glib)
        _objcopy = "/data/service/hnp/bin/llvm-objcopy"
        _signer = "/data/service/hnp/bin/binary-sign-tool"
        if not (_os.path.isdir(_gbin) and _os.path.isfile(_signer)):
            return
        for _tool in _os.listdir(_gbin):
            _tp = _os.path.join(_gbin, _tool)
            if not _os.path.isfile(_tp):
                continue
            with open(_tp, "rb") as _f:
                _magic = _f.read(4)
            if _magic[:4] != b"\x7fELF":
                continue  # shebang scripts (gdbus-codegen etc.) — leave alone
            try:
                self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=_objcopy, f=_tp))
                self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=_signer, f=_tp))
                self.output.info("re-signed glib bin tool: %s" % _tp)
            except Exception as _e:  # pragma: no cover — non-blocking
                self.output.warning("re-sign %s failed: %s" % (_tp, _e))

    def _patch_pc_datadir(self):
        # gnome.compile_resources() resolves its helper tools via the
        # gio-2.0.pc pkg-config variables glib_compile_resources /
        # glib_compile_schemas / gio_querymodules / gdbus_codegen (meson
        # find_tool with no default) — the PkgConfigDeps generated .pc lacks
        # them → meson aborts "Could not get pkg-config variable and no
        # default provided for <PkgConfigDependency gio-2.0>". Append the
        # tool variables (and datadir for resource install dirs) to the
        # generated .pc files.
        _tool_vars = {
            "gio-2.0.pc": [
                "glib_compile_resources=${prefix}/bin/glib-compile-resources",
                "glib_compile_schemas=${prefix}/bin/glib-compile-schemas",
                "gio_querymodules=${prefix}/bin/gio-querymodules",
                "gdbus_codegen=${prefix}/bin/gdbus-codegen",
            ],
            "glib-2.0.pc": [
                "glib_genmarshal=${prefix}/bin/glib-genmarshal",
                "glib_mkenums=${prefix}/bin/glib-mkenums",
            ],
        }
        for _pc, _vars in _tool_vars.items():
            _f = os.path.join(self.generators_folder, _pc)
            if not os.path.isfile(_f):
                continue
            with open(_f, encoding="utf-8") as _fh:
                _txt = _fh.read()
            _extra = []
            if "datadir=" not in _txt:
                _extra.append("datadir=${prefix}/share")
            for _v in _vars:
                _vn = _v.split("=", 1)[0]
                if _vn not in _txt:
                    _extra.append(_v)
            if not _extra:
                continue
            # insert variables right after the prefix/libdir line block
            _lines = _txt.splitlines(keepends=True)
            _ins = []
            for _ln in _lines:
                _ins.append(_ln)
                if _ln.startswith(("prefix=", "libdir=", "bindir=")) and _extra:
                    for _v in list(_extra):
                        _ins.append(_v + "\n")
                    _extra = []
            _txt = "".join(_ins)
            with open(_f, "w", encoding="utf-8") as _fh:
                _fh.write(_txt)
            self.output.info("%s: appended tool/datadir vars" % _pc)

    def _inject_meson_archiver(self):
        # MesonToolchain doesn't write ar/ranlib into the native file from
        # tools.build:compiler_executables; meson then probes bare llvm-ar /
        # ar / gar (not on PATH on OHOS — clang toolchain is in
        # /data/service/hnp/bin) → configure aborts with "No such file or
        # directory: 'llvm-ar'". Pin the real archiver by ABSOLUTE PATH.
        _ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        _ar, _rl = _ce.get("ar"), _ce.get("ranlib")
        if not _ar:
            _cc = _ce.get("c") or ""
            _bindir = os.path.dirname(_cc) if os.path.sep in _cc else ""
            if _bindir:
                _cand = os.path.join(_bindir, "llvm-ar")
                if os.path.isfile(_cand):
                    _ar = _cand
                    _rlc = os.path.join(_bindir, "llvm-ranlib")
                    if os.path.isfile(_rlc):
                        _rl = _rlc
        _nf = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not (_ar and os.path.isfile(_nf)):
            return
        with open(_nf, encoding="utf-8") as _f:
            _c = _f.read()
        if "\nar =" in _c or "[binaries]" not in _c:
            return
        _ins = "[binaries]\nar = '%s'\n" % _ar
        if _rl:
            _ins += "ranlib = '%s'\n" % _rl
        with open(_nf, "w", encoding="utf-8") as _f:
            _f.write(_c.replace("[binaries]\n", _ins, 1))
        self.output.info("injected ar/ranlib into conan_meson_native.ini")

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        self._run_upstream_tests(meson)

    def _run_upstream_tests(self, meson):
        # OHOS headless 无 X 显示：GTK 交互式上游测试需显示服务器。gtk4/4.22.4
        # 启用 broadway backend（HTML5 渲染，无需 X），通过 gtk4-broadwayd +
        # GDK_BACKEND=broadway 在 headless 下运行 62 项上游测试（本机已实证
        # 62/62 通过）。依赖环境：GSETTINGS_SCHEMA_DIR（gtk4 schemas 需先编译
        # gschemas.compiled）、FONTCONFIG_FILE、DBUS_MACHINE_ID、XDG_RUNTIME_DIR。
        if self.settings.os != "OHOS":
            return
        _gd = (getattr(self, "dependencies", None) or {}).get("gtk4")
        _gl = (getattr(self, "dependencies", None) or {}).get("glib")
        _fc = (getattr(self, "dependencies", None) or {}).get("fontconfig")
        if not (_gd and _gl):
            return
        import subprocess as _sp
        import uuid as _uuid
        _objcopy = "/data/service/hnp/bin/llvm-objcopy"
        _signer = "/data/service/hnp/bin/binary-sign-tool"
        _bw = os.path.join(_gd.package_folder, "bin", "gtk4-broadwayd")
        if not os.path.isfile(_bw):
            self.output.warning("上游测试跳过：gtk4-broadwayd 不存在")
            return
        # 1) re-sign gtk4-broadwayd（OHOS XPM 签名，与 glib 工具同款 ML-0043）
        self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=_objcopy, f=_bw))
        self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=_signer, f=_bw))
        # 2) 编译 gtk4 GSettings schema（生成 gschemas.compiled）到构建目录
        _schemas_src = os.path.join(_gd.package_folder, "share", "glib-2.0", "schemas")
        _schemas_tmp = os.path.join(self.build_folder, "test-schemas")
        if os.path.isdir(_schemas_src) and not os.path.isdir(os.path.join(_schemas_tmp, "gschemas.compiled")):
            if not os.path.isdir(_schemas_tmp):
                shutil.copytree(_schemas_src, _schemas_tmp)
            _gcs = os.path.join(_gl.package_folder, "bin", "glib-compile-schemas")
            if os.path.isfile(_gcs):
                self.run('{g} "{d}"'.format(g=_gcs, d=_schemas_tmp))
        # 3) 启动 gtk4-broadwayd + 设置测试环境
        # 注意：OHOS 上构建目录（el2/base/files 下）创建 unix socket 会报
        # "Operation not permitted"（实测 gtk4-broadwayd bind 失败）；缓存目录
        # /data/storage/el2/base/cache 可正常创建，broadway1.socket 必须落在
        # 客户端可访问路径。XDG_RUNTIME_DIR 用 cache 目录（本机验证实证）。
        _xdg = os.environ.get("XDG_CACHE_HOME") or "/data/storage/el2/base/cache"
        os.makedirs(_xdg, exist_ok=True)
        # conan 构建环境 LD_LIBRARY_PATH 仅含 llvm+glib（自研环境）；broadwayd 与
        # 上游测试需完整依赖库（gtk4/cairo/pango 等）才能加载。显式收集全部依赖
        # package lib 目录并前置到 LD_LIBRARY_PATH，避免 "Error loading shared
        # library" / socket 未建立 → 测试全部 Failed to open display。
        _libdirs = []
        for _dep in (getattr(self, "dependencies", None) or {}).values():
            _pf = getattr(_dep, "package_folder", None)
            if _pf and os.path.isdir(os.path.join(_pf, "lib")):
                _libdirs.append(os.path.join(_pf, "lib"))
        _ld = os.environ.get("LD_LIBRARY_PATH", "")
        _env = {
            "GDK_BACKEND": "broadway",
            # 注意：不设置 BROADWAY_DISPLAY——GTK4 broadway 客户端将其作为
            # display type 校验，空串/数字（如 "1"）会报 "Broadway display
            # type not supported"，未设置时走默认 "Broadway" 分支（实测成功）。
            "XDG_RUNTIME_DIR": _xdg,
            "GSETTINGS_SCHEMA_DIR": _schemas_tmp if os.path.isdir(_schemas_tmp) else _schemas_src,
            "DBUS_MACHINE_ID": _uuid.uuid4().hex,
            "LD_LIBRARY_PATH": ":".join(_libdirs + ([_ld] if _ld else [])),
        }
        if _fc and os.path.isfile(os.path.join(_fc.package_folder, "etc", "fonts", "fonts.conf")):
            _env["FONTCONFIG_FILE"] = os.path.join(_fc.package_folder, "etc", "fonts", "fonts.conf")
        _proc = None
        try:
            _proc = _sp.Popen([_bw], env=dict(os.environ, **_env),
                              stdout=_sp.DEVNULL, stderr=_sp.DEVNULL)
            _t0 = time.time()
            _sock = os.path.join(_xdg, "broadway1.socket")
            while not os.path.exists(_sock) and time.time() - _t0 < 20:
                time.sleep(0.5)
            os.environ.update(_env)
            self.output.info("运行上游测试（broadway headless，62 项）...")
            meson.test()
            self.output.info("✅ 上游测试全部通过")
        finally:
            os.environ.pop("GDK_BACKEND", None)
            os.environ.pop("XDG_RUNTIME_DIR", None)
            os.environ.pop("GSETTINGS_SCHEMA_DIR", None)
            os.environ.pop("DBUS_MACHINE_ID", None)
            os.environ.pop("FONTCONFIG_FILE", None)
            if _proc is not None:
                try:
                    _proc.terminate()
                except Exception:
                    pass

    def package(self):
        meson = Meson(self)
        meson.install()
        self._sign_shared_libs()

    def _sign_shared_libs(self):
        # meson install rewrites rpath and mutates .so post-link → the linker
        # self-sign breaks; OHOS XPM dlopen then reports Permission denied.
        # Strip old .codesign + binary-sign-tool -selfSign 1 re-sign (ML-0043).
        import glob as _glob
        libdir = os.path.join(self.package_folder, "lib")
        sos = _glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += _glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        objcopy = "/data/service/hnp/bin/llvm-objcopy"
        signer = "/data/service/hnp/bin/binary-sign-tool"
        for so in sos:
            self.run('{oc} --remove-section .codesign "{f}" 2>/dev/null || true'.format(oc=objcopy, f=so))
            self.run('{sg} sign -inFile "{f}" -outFile "{f}" -selfSign 1'.format(sg=signer, f=so))

    def package_info(self):
        # libadwaita public headers live under include/libadwaita-1
        # (meson package_api_name = libadwaita-1); library is libadwaita-1.so.
        self.cpp_info.includedirs = ["include/libadwaita-1"]
        self.cpp_info.libs = ["adwaita-1"]
        self.cpp_info.set_property("cmake_file_name", "libadwaita")
        self.cpp_info.set_property("cmake_target_name", "libadwaita::libadwaita")
        self.cpp_info.set_property("pkg_config_name", "libadwaita-1")
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread", "dl"]
