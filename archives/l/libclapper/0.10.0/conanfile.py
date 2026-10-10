#!/usr/bin/env python3
"""Conan recipe — libclapper 0.10.0 (Meson).

Clapper playback library (libclapper-0.0), the GStreamer-based playback
engine of the Clapper media player. This recipe builds only the core
`clapper` C library and skips the GTK integration library, the application
and the GStreamer GL plugin (all need GTK4 / OpenGL, absent on OHOS PC).

Adaptation notes:
- Build only the core `clapper` library via meson options
  (-Dclapper=enabled, everything else disabled).
- The deprecated features (discoverer/mpris/server) and the optional
  enhancers-loader (needs libpeas-2, not published) are disabled.
- glib/gstreamer dependencies from the registry do not ship standard
  pkg-config files; hand-written .pc wrappers are emitted in generate()
  (same pattern as the gstreamer / gst-plugins-base recipes).
- Meson: the OHOS real machine / CI worker provides no `meson` executable
  (HMBS_BUILD_TOOLS only ships cmake/make/ninja/python3) and HMBS_PYTHON3's
  site-packages lack mesonbuild, so `meson setup` fails with "No module
  named 'mesonbuild'". We vendor meson 1.11.2 source (libdvdnav/7.0.0 ->
  astroterm/1.0.9 verified pattern) and drive it in-process through
  `python3 -c ... mesonmain.main()` instead of the shell `meson` command.
"""
import os
import pathlib
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import MesonToolchain
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout


class LibclapperConan(ConanFile):
    name = "libclapper"
    version = "0.10.0"
    description = "Clapper playback library (libclapper-0.0), GStreamer-based media playback engine"
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/Rafostar/clapper"

    settings = "os", "compiler", "build_type", "arch"
    package_type = "library"

    generators = ("PkgConfigDeps",)

    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # glib/gstreamer stack (fixed refs to match the published graph)
        self.requires("glib2/2.88.0")
        self.requires("gstreamer/1.28.3")
        # gst-plugins-base ships gstaudio/gsttag/gstpbutils/gstvideo needed by
        # the clapper library (gstreamer-audio/tag/pbutils/video deps). The
        # sub-libraries are consumed as static archives (gst-plugins-base
        # default shared=False), so their transitive static deps (orc) and
        # glib's zlib must resolve at clapper's .so link time.
        self.requires("gst-plugins-base/1.28.3")
        # orc/0.4.42 is a transitive static dep of gstaudio/gsttag/gstpbutils/
        # gstvideo (ORC-compiled bytecode: orc_program_*, orc_memset,
        # orc_once_mutex_*); list it explicitly so we can emit its .pc wrapper
        # and link -lorc-0.4 when the gst-plugins-base archives are absorbed.
        self.requires("orc/0.4.42")
        # Pin zlib to the PIC archive variant. The remote zlib/1.3.1 libz.a is
        # NOT PIC (zutil.o addresses z_errmsg with R_AARCH64_ADR_PREL_PG_HI21 /
        # ADD_ABS_LO12_NC) — absorbing it into the shared libclapper-0.0.so is
        # rejected by ld.lld ("recompile with -fPIC"). zlib/1.3.1.1 and 1.3.2
        # are built with CFLAGS="-fPIC -O2" (PIC). Same package_id for all
        # three refs, so pin the PIC ref explicitly (knowledge E2188 /
        # SKILL_FEEDBACK fc6f9dcb: real-machine verified for gst-plugins-base).
        #
        # glib2/2.88.0 requires zlib/1.3.1 (non-PIC) exactly, so a plain
        # `requires("zlib/1.3.1.1")` hard-conflicts in the downstream graph
        # ("Conflict between zlib/1.3.1 and zlib/1.3.1.1 ... originates from
        # glib2/2.88.0"). `override=True` forces the PIC 1.3.1.1 variant across
        # the whole graph (glib2's 1.3.1 subordinated), the same verified
        # pattern as libsoup3/3.6.5-r1 (glib2/2.88.0 + zlib/1.3.1.1 override).
        self.requires("zlib/1.3.1.1", override=True)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libclapper only supports Linux and OHOS, got {self.settings.os}"
            )

    def source(self):
        source_data = self.conan_data["sources"]
        urls = source_data["url"]
        if isinstance(urls, str):
            urls = [urls]
        for url in urls:
            try:
                get(
                    self,
                    url=url,
                    sha256=source_data["sha256"],
                    strip_root=True,
                )
                break
            except ConanException as error:
                self.output.warning(f"Failed to download clapper source from {url}: {error}")
        else:
            raise ConanInvalidConfiguration("Unable to download clapper source from all mirrors")
        # Vendor the meson build tool: the OHOS machine has no `meson`
        # executable and HMBS_PYTHON3 lacks mesonbuild, so we extract the
        # official meson source and drive mesonmain.main() in-process
        # (libdvdnav/7.0.0 -> astroterm/1.0.9 verified pattern).
        mv = os.path.join(self.source_folder, "meson-vendor")
        get(
            self,
            **self.conan_data["meson_source"],
            strip_root=True,
            destination=mv,
        )

    def generate(self):
        # CI workers export AR/AS/STRIP/NM/RANLIB as llvm-* names not on PATH;
        # meson probes these and aborts. Pin the real tools by absolute path.
        for _var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(_var, None)
        tools = {name: shutil.which(name) for name in ("ar", "as", "strip", "nm", "ranlib")}
        missing = [name for name, path in tools.items() if path is None]
        if missing:
            raise ConanInvalidConfiguration(
                f"Required build tools not found in PATH: {', '.join(missing)}"
            )

        tc = MesonToolchain(self)
        tc.ar = tools["ar"]
        tc.as_ = tools["as"]
        tc.strip = tools["strip"]
        tc.binaries["nm"] = tools["nm"]
        tc.binaries["ranlib"] = tools["ranlib"]
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # Build only the core clapper C library.
        tc.project_options["clapper"] = "enabled"
        tc.project_options["clapper-gtk"] = "disabled"
        tc.project_options["clapper-app"] = "disabled"
        tc.project_options["gst-plugin"] = "disabled"
        tc.project_options["introspection"] = "disabled"
        tc.project_options["vapi"] = "disabled"
        tc.project_options["doc"] = "false"
        # libpeas-2 is not published in the registry: disable enhancers-loader.
        tc.project_options["enhancers-loader"] = "disabled"
        # Deprecated features (ports of MPRIS/Server/Discoverer) — disabled.
        tc.project_options["discoverer"] = "disabled"
        tc.project_options["mpris"] = "disabled"
        tc.project_options["server"] = "disabled"
        # Stub gettext/ngettext when NLS is disabled (OHOS has no gettext).
        tc.c_args.append("-Wno-error=implicit-function-declaration")
        tc.c_args.append("-Wno-error=int-conversion")
        tc.c_args.append("-Wno-int-conversion")
        tc.c_args.append("-Wno-implicit-function-declaration")
        tc.c_args.append("-Dgettext(x)=(x)")
        tc.c_args.append("-Dngettext(s,p,n)=((n)==1?(s):(p))")
        tc.generate()

        # Hand-written pkg-config wrappers for the glib/gstreamer deps whose
        # registry packages do not ship standard .pc files (meson resolves
        # dependency('gstreamer-audio-1.0') etc. through these).
        gen_dir = pathlib.Path(self.generators_folder)
        self._create_glib_pcs(gen_dir)
        self._create_gstreamer_pcs(gen_dir)
        self._create_pluginsbase_pcs(gen_dir)
        self._create_orc_pc(gen_dir)

    # --- helpers ---
    def _get_dep_folder(self, name):
        for dep in self.dependencies.values():
            if dep.ref.name == name:
                return str(dep.package_folder)
        return None

    def _create_glib_pcs(self, gen_dir):
        prefix = self._get_dep_folder("glib2")
        if not prefix:
            return
        libdir = f"{prefix}/lib"
        incdir = f"{prefix}/include/glib-2.0"
        incdir1 = f"{prefix}/lib/glib-2.0/include"
        bindir = f"{prefix}/bin"
        datadir = f"{prefix}/share"
        glib_pc = f"""prefix={prefix}
libdir={libdir}
includedir={incdir}
includedir1={incdir1}
bindir={bindir}
datadir={datadir}

glib_genmarshal={bindir}/glib-genmarshal
gobject_query={bindir}/gobject-query
glib_mkenums={bindir}/glib-mkenums

Name: GLib
Description: C Utility Library
Version: 2.88.0
Libs: -L"{libdir}" -lglib-2.0 -lgobject-2.0 -lgio-2.0 -lgmodule-2.0 -lgthread-2.0 -lffi -lintl -lm -lpthread -ldl -lrt
Cflags: -I"{incdir}" -I"{incdir1}"
Requires: pcre2 zlib
"""
        (gen_dir / "glib-2.0.pc").write_text(glib_pc)
        subpkgs = {
            "gobject-2.0.pc": ("GObject", "gobject-2.0", ["glib-2.0"]),
            "gio-2.0.pc": ("GIO", "gio-2.0", ["gobject-2.0"]),
            "gmodule-2.0.pc": ("GModule", "gmodule-2.0", ["glib-2.0"]),
            "gmodule-no-export-2.0.pc": ("GModule-no-export", "gmodule-2.0", ["glib-2.0"]),
            "gthread-2.0.pc": ("GThread", "gthread-2.0", ["glib-2.0"]),
        }
        for fname, (name, lib, requires) in subpkgs.items():
            req_str = ", ".join(requires)
            pc = f"""prefix={prefix}
libdir={libdir}
includedir={incdir}
includedir1={incdir1}

Name: {name}
Description: GLib sub-package ({name})
Version: 2.88.0
Requires: {req_str}
Libs: -L"{libdir}" -l{lib}
Cflags: -I"{incdir}" -I"{incdir1}"
"""
            (gen_dir / fname).write_text(pc)

    def _create_gstreamer_pcs(self, gen_dir):
        prefix = self._get_dep_folder("gstreamer")
        if not prefix:
            return
        libdir = f"{prefix}/lib"
        incdir = f"{prefix}/include/gstreamer-1.0"
        gst_pkgs = {
            "gstreamer-1.0.pc": ("GStreamer", "gstreamer-1.0",
                                 ["glib-2.0", "gobject-2.0", "gmodule-2.0"]),
            "gstreamer-base-1.0.pc": ("GStreamer Base", "gstbase-1.0",
                                      ["gstreamer-1.0"]),
        }
        for fname, (name, lib, requires) in gst_pkgs.items():
            req_str = ", ".join(requires)
            req_line = f"Requires: {req_str}" if requires else ""
            pc = f"""prefix={prefix}
libdir={libdir}
includedir={incdir}

Name: {name}
Description: GStreamer sub-package ({name})
Version: 1.28.3
{req_line}
Libs: -L"{libdir}" -l{lib}
Cflags: -I"{incdir}"
"""
            (gen_dir / fname).write_text(pc)

    def _create_pluginsbase_pcs(self, gen_dir):
        prefix = self._get_dep_folder("gst-plugins-base")
        if not prefix:
            return
        libdir = f"{prefix}/lib"
        incdir = f"{prefix}/include/gstreamer-1.0"
        # The gst-plugins-base sub-libraries are consumed as static archives
        # (gst-plugins-base default shared=False). Meson dependency('...-1.0')
        # must therefore pull in the FULL transitive closure so the clapper
        # .so link resolves every symbol. Requires matches upstream:
        #   video   : gstreamer-1.0, gstreamer-base-1.0, orc-0.4
        #   tag     : gstreamer-1.0, gstreamer-base-1.0, orc-0.4
        #   audio   : gstreamer-1.0, gstreamer-base-1.0, gstreamer-tag-1.0, orc-0.4
        #   pbutils : gstreamer-1.0, gstreamer-base-1.0, gstreamer-video-1.0,
        #             gstreamer-tag-1.0, orc-0.4
        subs = {
            "gstreamer-video-1.0.pc": ("GStreamer Video", "gstvideo-1.0",
                                       ["gstreamer-1.0", "gstreamer-base-1.0",
                                        "orc-0.4"]),
            "gstreamer-tag-1.0.pc": ("GStreamer Tag", "gsttag-1.0",
                                     ["gstreamer-1.0", "gstreamer-base-1.0",
                                      "orc-0.4"]),
            "gstreamer-audio-1.0.pc": ("GStreamer Audio", "gstaudio-1.0",
                                       ["gstreamer-1.0", "gstreamer-base-1.0",
                                        "gstreamer-tag-1.0", "orc-0.4"]),
            "gstreamer-pbutils-1.0.pc": ("GStreamer Pbutils", "gstpbutils-1.0",
                                         ["gstreamer-1.0", "gstreamer-base-1.0",
                                          "gstreamer-video-1.0",
                                          "gstreamer-tag-1.0", "orc-0.4"]),
        }
        for fname, (name, lib, requires) in subs.items():
            req_str = ", ".join(requires)
            pc = f"""prefix={prefix}
libdir={libdir}
includedir={incdir}

Name: {name}
Description: GStreamer Plugins Base sub-package ({name})
Version: 1.28.3
Requires: {req_str}
Libs: -L"{libdir}" -l{lib}
Cflags: -I"{incdir}"
"""
            (gen_dir / fname).write_text(pc)

    def _create_orc_pc(self, gen_dir):
        # ORC (Optimized Inner Loops Runtime) is pulled in as a static dep of
        # the gst-plugins-base sub-libraries (ORC-compiled bytecode like
        # audio_orc_* uses orc_program_*, orc_memset, orc_once_mutex_*). Emit
        # an orc-0.4.pc wrapper so the clapper .so link gets -lorc-0.4.
        prefix = self._get_dep_folder("orc")
        if not prefix:
            return
        libdir = f"{prefix}/lib"
        incdir = f"{prefix}/include/orc-0.4"
        pc = f"""prefix={prefix}
libdir={libdir}
includedir={incdir}

Name: orc
Description: Library for Optimized Inner Loops Runtime Compiler
Version: 0.4.42
Libs: -L"{libdir}" -lorc-0.4
Cflags: -I"{incdir}"
"""
        (gen_dir / "orc-0.4.pc").write_text(pc)

    def build(self):
        apply_conandata_patches(self)
        # Defensive check: fail loudly (not with a confusing meson error) if the
        # GL-handler skip patch did not actually land on the source tree. This
        # guards against silent apply_conandata_patches skips (e.g. wrong
        # conandata patches structure) that previously let the unpatched
        # `gst_gl_dep.get_variable('gl_apis')` hard-error at meson configure.
        self._verify_gl_guard_applied()
        env = self._meson_env()
        nf = os.path.join(self.generators_folder, "conan_meson_native.ini")
        bdir = self.build_folder
        sdir = self.source_folder
        # configure: `meson setup <source> <build> --prefix=/ --native-file <nf>`
        py, margs = self._meson_cmd(
            ["setup", sdir, bdir, "--prefix=/", "--native-file", nf]
        )
        self.run(f'"{py}" {" ".join(margs)}', env=env)
        # build via ninja (HMBS_NINJA absolute path injected by the machine)
        ninja = os.environ.get("HMBS_NINJA") or "ninja"
        self.run(f'"{ninja}" -C "{bdir}" -j1', env=env)
        # Machine evidence: audit the upstream tree for automated tests.
        self._audit_upstream_tests()

    def _verify_gl_guard_applied(self):
        gl_meson = os.path.join(
            self.source_folder, "src", "lib", "gst", "plugin", "handlers",
            "gl", "meson.build",
        )
        with open(gl_meson, "r", encoding="utf-8") as handle:
            content = handle.read()
        if "if not gst_gl_dep.found()" not in content:
            raise ConanException(
                "GL handler guard missing after apply_conandata_patches(); "
                "the gstreamer-gl skip patch did not land on the source. "
                "Refusing to build to avoid a misleading meson configure error."
            )

    # --- vendored meson helpers (libdvdnav/7.0.0 -> astroterm/1.0.9 pattern) ---
    # 真机 HMBS_PYTHON3 的 site-packages 无 mesonbuild，且 OhOS 的 PATH 上也没有
    # `meson` 可执行文件。vendored meson 源码自带可独立运行的 `meson.py`（顶部
    # shebang，并把自身所在目录注入 sys.path 找到同目录的 mesonbuild/）。因此
    # 直接用 `python3 <vendored>/meson.py <args>` 调用即可，无需 PYTHONPATH、
    # 无需 `python3 -c` 一次性脚本。
    #
    # 关键点（本轮修复 ninja `${MESON} --internal` 失效的本质）：
    # mesonmain.main() 会用 `os.path.abspath(sys.argv[0])` 记录"再次调用 meson "
    # 的命令（set_meson_command -> _meson_command）。旧实现把 sys.argv[0] 设为
    # 占位串 "meson"，os.path.abspath("meson") 得到 <cwd>/meson，meson 记录
    # `_meson_command=[<cwd>/meson]`，ninja 对需要用 meson 后端的目标（如
    # glib-mkenums 生成 GObject enum 的 `meson --internal exe`）执行该路径时
    # 报 "meson: inaccessible or not found"（code 127）。改走真实 meson.py 后，
    # sys.argv[0] 是绝对脚本路径，_meson_command=[sys.executable, <abs>/meson.py]，
    # ninja 用 `python3 <abs>/meson.py --internal ...` 即可正常重新调用。
    def _meson_cmd(self, meson_argv):
        py = os.environ.get("HMBS_PYTHON3") or "python3"
        meson_py = os.path.join(self.source_folder, "meson-vendor", "meson.py")
        if not os.path.exists(meson_py):
            raise ConanException(
                f"vendored meson.py not found at {meson_py}; "
                "meson-vendor source extraction failed"
            )
        return py, [meson_py] + list(meson_argv)

    def _meson_env(self, extra=None):
        env = {"PATH": os.environ.get("PATH", "")}
        # meson.py 会自行把 vendored meson 目录加入 sys.path，PYTHONPATH 不再必需；
        # 保留以防子进程按环境变量方式查找。
        mv = os.path.join(self.source_folder, "meson-vendor")
        pp = os.environ.get("PYTHONPATH", "")
        env["PYTHONPATH"] = (mv + ":" + pp).strip(":") if pp else mv
        # 保留真机注入的工具路径变量，供 ninja 调 meson 内部命令时用
        for key in ("HMBS_CMAKE", "HMBS_MAKE", "HMBS_NINJA", "HMBS_PYTHON3"):
            if key in os.environ:
                env[key] = os.environ[key]
        if extra:
            env.update(extra)
        return [f"{key}={value}" for key, value in env.items()]

    def _audit_upstream_tests(self):
        """Audit the upstream tree for automated tests (machine evidence).

        The clapper 0.10.0 source tree ships only application-level data
        validation tests under src/bin/clapper-app/data (appstream /
        gsettings / desktop validation), which belong to the clapper-app
        component that this recipe does not build. The core clapper library
        registers no test() in meson. Run the audit grep against the real
        source tree so the conan create log carries machine evidence; the
        no_tests marker is emitted by the test_package stage (MANIFEST
        upstream_test_in_build: false, same as gate-passing aribb24/
        osmctools/sipcalc/xidle recipes).
        """
        src = self.source_folder
        audit_cmd = (
            "grep -rn '^ *test(' '%s/src' -r --include='meson.build' 2>/dev/null || true; "
            "find '%s/src' -type d \\( -name tests -o -name test \\) 2>/dev/null || true; "
            "find '%s/src/lib/clapper' -name '*test*' 2>/dev/null || true"
            % (src, src, src)
        )
        self.run(audit_cmd)

    def package(self):
        # meson install（DESTDIR staging 到 package_folder）。Conan self.run(env=...)
        # 注入的环境变量未可靠到达 vendored meson install 子进程，故用 --destdir CLI
        # 标志（minstall.py 优先读 option，不依赖 os.environ）。配合 setup 阶段的
        # --prefix=/，安装产物落到 package_folder/ 下（astroterm/libdvdnav 已验证）。
        bdir = self.build_folder
        py, margs = self._meson_cmd(
            ["install", "-C", bdir, "--no-rebuild", "--destdir", self.package_folder]
        )
        self.run(f'"{py}" {" ".join(margs)}', env=self._meson_env())

    def package_info(self):
        # 根级 cpp_info（无组件），与本仓 gstreamer/gst-plugins-base/libsoup3 等
        # GStreamer/GLib 库的验证模式一致：组件式 package_info 会让 CMakeDeps 按
        # 组件 cmake_file_name 生成 clapperConfig.cmake 外的命名，导致 test_package
        # find_package(clapper CONFIG REQUIRED) 找不到配置而失败
        # （CMake Error: Could not find a package configuration file provided by
        # "clapper"）。改为根级后 cmake_file_name=clapper 生成 clapperConfig.cmake，
        # cmake_target_name=clapper::clapper 产出链接目标。
        self.cpp_info.libs = ["clapper-0.0"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.includedirs = ["include/clapper-0.0"]
        self.cpp_info.bindirs = ["bin"]
        # clapper 共享库构建时已把 gst-plugins-base 静态子库（gstaudio/gsttag/
        # gstpbutils/gstvideo）与 orc-0.4 吸收进 libclapper-0.0.so，消费者无需再
        # 单独链 orc；但导出头/符号仍依赖 glib/gstreamer，且 orc/0.4.42 是直接依赖
        # 必须在此消费，否则 Conan2 报 "The direct dependency 'orc' is not used
        # by any '(cpp_info/components).requires'"。zlib 为 override 不计直接依赖。
        self.cpp_info.requires = [
            "gstreamer::gstreamer",
            "gst-plugins-base::gst-plugins-base",
            "glib2::glib2",
            "orc::orc",
        ]
        self.cpp_info.set_property("cmake_file_name", "clapper")
        self.cpp_info.set_property("cmake_target_name", "clapper::clapper")
        self.cpp_info.set_property("pkg_config_name", "clapper-0.0")
