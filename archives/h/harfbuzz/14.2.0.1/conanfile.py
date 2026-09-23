#!/usr/bin/env python3
"""Conan recipe — harfbuzz 14.2.0.1 (meson)

Text shaping library. Requires glib + freetype (cairo optional; disabled to
avoid extra cycles — pango links cairo separately).
R37: adaptation fix revision over archived 14.2.0 (cmd-pkgs / incomplete Conan).
"""
import glob
import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.files import (
    apply_conandata_patches,
    collect_libs,
    export_conandata_patches,
    get,
)
from conan.tools.env import Environment
from conan.tools.gnu import PkgConfigDeps
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class HarfbuzzConan(ConanFile):
    name = "harfbuzz"
    version = "14.2.0.1"
    description = "HarfBuzz text shaping library"
    license = "MIT"
    homepage = "https://harfbuzz.github.io/"
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
        # ADAPTATION_GUIDE §3.2: HarmonyOS namespace.default.lib.paths only
        # allows libc.so / libc++_shared.so — dlopen of /storage/.../*.so
        # always fails with EPERM.  Request static glib on OHOS so test
        # executables' ELF NEEDED list contains no libglib-2.0.so /
        # libintl.so.  Other platforms retain the shared variant.
        if self.settings.os == "OHOS":
            self.requires("glib/2.84.0.1", options={"shared": False})
        else:
            self.requires("glib/2.84.0.1")
        self.requires("freetype/2.14.3")
        self.requires("zlib/1.3.1.1")

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
        # MesonToolchain omits ar/ranlib; cross builds also omit pkg-config.
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

    def _inject_static_glib_intl(self):
        # E107 / E123: OHOS requests glib with shared=False so tests avoid
        # dlopen(libglib/libintl).  Static libglib-2.0.a still references
        # g_libintl_* from proxy-libintl (libintl.a), but published
        # glib/2.84.0.1 package_info() only exports -lglib-2.0.  Without
        # -lintl, linking libharfbuzz.so fails with undefined g_libintl_*.
        # Inject the absolute archive into Conan's generated glib-2.0.pc
        # (absolute path avoids picking a system libintl.so that lacks the
        # g_libintl_* renames).  R37: do not revise published glib in-place.
        if self.settings.os != "OHOS":
            return
        try:
            glib_dep = self.dependencies["glib"]
        except KeyError:
            return
        if glib_dep.options.get_safe("shared", True):
            return
        intl_a = os.path.join(glib_dep.package_folder, "lib", "libintl.a")
        if not os.path.isfile(intl_a):
            self.output.warning(
                "static glib requested but libintl.a missing under {}; "
                "libharfbuzz.so link may fail with undefined g_libintl_*".format(
                    os.path.join(glib_dep.package_folder, "lib")
                )
            )
            return
        pc = os.path.join(self.generators_folder, "glib-2.0.pc")
        if not os.path.isfile(pc):
            return
        with open(pc) as f:
            text = f.read()
        if "libintl.a" in text or "-lintl" in text:
            return
        lines = []
        patched = False
        for line in text.splitlines(True):
            if line.startswith("Libs:") and not patched:
                lines.append(line.rstrip("\n") + " " + intl_a + "\n")
                patched = True
            else:
                lines.append(line)
        if patched:
            with open(pc, "w") as f:
                f.write("".join(lines))
            self.output.info("injected {} into glib-2.0.pc Libs for static glib".format(intl_a))

    def generate(self):
        PkgConfigDeps(self).generate()
        self._inject_static_glib_intl()
        env = Environment()
        # gobject=enabled needs build-machine glib-mkenums (Python script from glib package).
        glib_bin = os.path.join(self.dependencies["glib"].package_folder, "bin")
        if os.path.isdir(glib_bin):
            env.prepend_path("PATH", glib_bin)
        # check-static-inits.py / check-symbols.py call `shutil.which("objdump"|"nm")`,
        # which fails when `/data/service/hnp/bin` isn't in PATH.  Point both at
        # the absolute path of the llvm tools so meson test() finds them.
        cc = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict).get("c", "")
        if cc:
            bindir = os.path.dirname(cc)
            for tool, envname in (("llvm-objdump", "OBJDUMP"), ("llvm-nm", "NM")):
                full = os.path.join(bindir, tool)
                if os.path.isfile(full):
                    env.define(envname, full)
        env.vars(self, scope="build").save_script("conanbuildenv_glib_tools")
        tc = MesonToolchain(self)
        tc.project_options["wrap_mode"] = "nodownload"
        tc.project_options["glib"] = "enabled"
        # OHOS: disable gobject.  Conan's PkgConfigDeps does not emit the
        # `glib_mkenums` variable in glib-2.0.pc, so `gnome.mkenums(...)` in
        # src/meson.build fails with "Could not get pkg-config variable".
        # hb-gobject is unused on OHOS (no test references it), and `hb-info`
        # still builds against null_dep -- it just won't print GObject types.
        # Other platforms keep gobject=enabled so cairo/pango consumers work.
        tc.project_options["gobject"] = "disabled" if self.settings.get_safe("os") == "OHOS" else "enabled"
        tc.project_options["freetype"] = "enabled"
        tc.project_options["zlib"] = "enabled"
        tc.project_options["cairo"] = "disabled"
        tc.project_options["graphite2"] = "disabled"
        tc.project_options["icu"] = "disabled"
        tc.project_options["introspection"] = "disabled"
        # ADAPTATION_GUIDE: enable upstream meson test suite in build().
        tc.project_options["tests"] = "enabled"
        tc.project_options["docs"] = "disabled"
        # utilities=enabled：上游 test/meson.build 用它门控 test/subset、test/shape、
        # test/vector；关闭则无法注册 236 用例中的 shape/subset/repack 套件。
        # cairo 仍 disabled → hb-view 不构建；hb-shape / hb-subset / hb-info 仍可用。
        tc.project_options["utilities"] = "enabled"
        tc.project_options["chafa"] = "disabled"
        tc.project_options["benchmark"] = "disabled"
        tc.project_options["png"] = "disabled"
        tc.project_options["gpu_demo"] = "disabled"
        tc.generate()
        self._inject_meson_binaries()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        # Upstream official suite (ADAPTATION_GUIDE / TEST_QUALITY_SPEC).
        meson.test()

    def package(self):
        Meson(self).install()
        self._sign_shared_libs()

    def _resolve_ohos_tool(self, env_keys, tool_name):
        # Priority: env → user.ohos:* conf → sibling of Conan clang → PATH →
        # last-resort CI Worker path (never first). Absolute paths only.
        for key in env_keys:
            val = os.environ.get(key) or ""
            if val and os.path.isfile(val):
                return val
        conf_val = self.conf.get("user.ohos:%s" % tool_name.replace("-", "_"), default=None)
        if conf_val and os.path.isfile(str(conf_val)):
            return str(conf_val)
        ce = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cc = ce.get("c") or ce.get("cpp") or ""
        if cc and os.path.sep in cc:
            sibling = os.path.join(os.path.dirname(cc), tool_name)
            if os.path.isfile(sibling):
                return sibling
        which = shutil.which(tool_name)
        if which and os.path.isfile(which):
            return which
        fallback = "/data/service/hnp/bin/%s" % tool_name
        if os.path.isfile(fallback):
            return fallback
        return None

    def _sign_shared_libs(self):
        # Native OHOS worker: re-sign after meson install rewrites rpath.
        # Cross Docker SDK may lack binary-sign-tool — skip with warning.
        libdir = os.path.join(self.package_folder, "lib")
        sos = glob.glob(os.path.join(libdir, "**", "*.so"), recursive=True)
        sos += glob.glob(os.path.join(libdir, "**", "*.so.*"), recursive=True)
        if not sos:
            return
        objcopy = self._resolve_ohos_tool(("LLVM_OBJCOPY", "OBJCOPY"), "llvm-objcopy")
        signer = self._resolve_ohos_tool(("BINARY_SIGN_TOOL",), "binary-sign-tool")
        if not signer:
            self.output.warning(
                "binary-sign-tool not found (set BINARY_SIGN_TOOL or user.ohos:binary_sign_tool); "
                "skip OHOS codesign (cross/SDK env)"
            )
            return
        for so in sos:
            qso = shlex.quote(so)
            if objcopy:
                self.run(
                    "{oc} --remove-section .codesign {f} 2>/dev/null || true".format(
                        oc=shlex.quote(objcopy), f=qso
                    )
                )
            self.run(
                "{sg} sign -inFile {f} -outFile {f} -selfSign 1".format(
                    sg=shlex.quote(signer), f=qso
                )
            )

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "harfbuzz")
        self.cpp_info.set_property("pkg_config_name", "harfbuzz-unofficial")
        # utilities=enabled 安装 hb-shape / hb-subset / hb-info（R38 / L0k）
        if os.path.isdir(os.path.join(self.package_folder, "bin")):
            self.cpp_info.bindirs = ["bin"]

        hb = self.cpp_info.components["harfbuzz"]
        hb.set_property("pkg_config_name", "harfbuzz")
        hb.set_property("cmake_target_name", "harfbuzz::harfbuzz")
        hb.libs = ["harfbuzz"]
        hb.includedirs = ["include/harfbuzz", "include"]
        hb.requires = ["glib::glib-2.0", "freetype::freetype", "zlib::zlib"]
        if self.settings.os in ("Linux", "OHOS"):
            hb.system_libs = ["m", "pthread"]

        # Optional subset library when present.
        subset_so = os.path.join(self.package_folder, "lib", "libharfbuzz-subset.so")
        if os.path.isfile(subset_so) or glob.glob(
            os.path.join(self.package_folder, "lib", "libharfbuzz-subset.so*")
        ):
            subset = self.cpp_info.components["harfbuzz-subset"]
            subset.set_property("pkg_config_name", "harfbuzz-subset")
            subset.set_property("cmake_target_name", "harfbuzz::harfbuzz-subset")
            subset.libs = ["harfbuzz-subset"]
            subset.includedirs = ["include/harfbuzz", "include"]
            subset.requires = ["harfbuzz"]

        if not any(c.libs for c in self.cpp_info.components.values()):
            self.cpp_info.libs = collect_libs(self)
