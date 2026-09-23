#!/usr/bin/env python3
"""Conan recipe — glib-networking 2.90.0 (Meson).

GLib official TLS backend implementation (GIO TLS modules). Bridges the GLib
TLS API to OpenSSL so g_tls_backend_get_default() returns a real backend
(gioopenssl) instead of GLib's GDummyTlsBackend on HarmonyOS. This is the
dependency baseline for libsoup3 http2 tests (TLS availability).
"""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import cross_building
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches
from conan.tools.meson import Meson, MesonToolchain


class GlibNetworkingConan(ConanFile):
    name = "glib-networking"
    version = "2.90.0"
    description = "GLib TLS backend modules bridging to OpenSSL/GnuTLS"
    license = "LGPL-2.1+"
    homepage = "https://gitlab.gnome.org/GNOME/glib-networking"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}
    generators = "PkgConfigDeps"
    # glib-networking installs GIO modules (*.so) not consumable as a normal
    # library; the test_package validates the TLS backend actually activates.
    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # glib 2.88.3 is published on ohpcd as a SHARED build (glib2/2.88.0 is
        # static-only there). A shared glib is required: the gioopenssl.so GIO
        # module is dlopen()ed into the same process as the consumer's copy of
        # glib, so both must resolve the same type system (static glib2 would
        # double-register GObject types -> "cannot register existing type").
        # glib/2.88.3's .so only needs libc.so and loads cleanly on OHOS.
        self.requires("glib/2.88.3")
        # TLS backend: OpenSSL (3.5.8.1 published on ohpcd). GnuTLS is also
        # possible but OpenSSL is the more mature OHOS target (see manifest).
        self.requires("openssl/3.5.8.1")
        # glib's gi18n-lib.h includes <libintl.h> unconditionally; the shared
        # glib .so embeds proxy-libintl but does not ship the header. Declare it
        # explicitly so its include dir is resolvable in generate() (as a
        # transitive dep its package_folder is None there). Same 0.5 instance
        # glib uses, so no version conflict.
        self.requires("proxy-libintl/0.5")

    def layout(self):
        # meson_layout was removed in conan 2.29.x; replicate its folders here
        self.folders.build = "builddir"
        self.folders.generators = "builddir/generators"

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # The CI worker exports AR/AS/STRIP/NM/RANLIB as llvm-* names (llvm-ar,
        # ...) that are NOT on its PATH — only the GNU binutils and ld.lld exist.
        # meson probes these and aborts at configure; pin the real tools by
        # ABSOLUTE PATH (resolved from PATH) and drop the broken env values.
        # (same fix as glib2/2.88.0 and libsoup3 recipes)
        for _var in ("AR", "AS", "STRIP", "NM", "RANLIB"):
            os.environ.pop(_var, None)
        tools = {name: shutil.which(name) for name in ("ar", "as", "strip", "nm", "ranlib")}
        missing = [name for name, path in tools.items() if path is None]
        if missing:
            raise ConanInvalidConfiguration(f"Required build tools not found in PATH: {', '.join(missing)}")
        tc = MesonToolchain(self)
        tc.ar = tools["ar"]
        tc.as_ = tools["as"]
        # ⚠️ 绝不可 strip 共享模块：OHOS loader 校验 .codesign 段内嵌哈希，
        # strip 改写 .so 内容导致哈希失配，dlopen 报 Permission denied
        # （libsoup3 铁证同源）。GIO 模块必须被 dlopen 加载，禁用 strip。
        tc.strip = None
        tc.binaries["nm"] = tools["nm"]
        tc.binaries["ranlib"] = tools["ranlib"]
        tc.project_options["default_library"] = "shared" if self.options.shared else "static"
        # TLS backend: OpenSSL enabled, GnuTLS disabled (single backend choice).
        tc.project_options["openssl"] = "enabled"
        tc.project_options["gnutls"] = "disabled"
        # Proxy backends: libproxy / gnome_proxy / env_proxy not required on OHOS.
        tc.project_options["libproxy"] = "disabled"
        tc.project_options["gnome_proxy"] = "disabled"
        tc.project_options["environment_proxy"] = "disabled"
        # Run upstream tests (tls/tests) on the target.
        tc.project_options["tests"] = "true"
        tc.project_options["installed_tests"] = "false"
        # glib's real .pc files (gio-2.0 with giomoduledir, gobject,
        # gmodule-no-export) come from the glib package; PkgConfigDeps also
        # generates its own gio-2.0.pc but WITHOUT the giomoduledir variable
        # (meson.build asserts on it). Prepend the fixed copies so pkg-config
        # resolves the full variable set (prefix corrected from "/").
        extra_pc = []
        if self.dependencies.get("glib"):
            glib_pkg = self.dependencies["glib"].package_folder
            pc_fix_dir = os.path.join(self.build_folder, "glib-pc-fix")
            os.makedirs(pc_fix_dir, exist_ok=True)
            for pc in os.listdir(os.path.join(glib_pkg, "lib", "pkgconfig")):
                if not pc.endswith(".pc"):
                    continue
                src = os.path.join(glib_pkg, "lib", "pkgconfig", pc)
                dst = os.path.join(pc_fix_dir, pc)
                with open(src, "r", encoding="utf-8") as fh:
                    text = fh.read()
                text = re.sub(r"^prefix=.*$", f"prefix={glib_pkg}", text, count=1, flags=re.M)
                # The shared glib rebuild embeds proxy-libintl, zlib and pcre2
                # statically (its .so only NEEDs libc.so), yet the installed PC
                # still lists them under Requires/Requires.private; pkg-config
                # then demands their .pc files which PkgConfigDeps does not emit
                # for transitive deps. Strip those spurious requires so the
                # glib/gio/gobject chains resolve (same class of fix as the
                # zlib private-requires issue seen with glib2).
                text = re.sub(
                    r"^(Requires(?:\.private)?):\s*([^\n]*)$",
                    lambda m: m.group(1) + ": "
                    + re.sub(
                        r"\b(?:proxy-libintl|zlib|libpcre2-8)\b(?:\s*>=\s*[0-9.]+)?(?:\s*,\s*|\s*$)",
                        "",
                        m.group(2),
                    ).strip().rstrip(",")
                    if any(t in m.group(2) for t in ("proxy-libintl", "zlib", "libpcre2-8"))
                    else m.group(0),
                    text,
                    flags=re.M,
                )
                # Requirements.private describe static-link internals; with a
                # shared glib they are already embedded in the .so (libffi
                # etc.), and their .pc files are not emitted by PkgConfigDeps.
                # Clear them so pkg-config resolves glib-2.0/gio-2.0 chains.
                text = re.sub(
                    r"^Requires\.private:.*$",
                    "Requires.private:",
                    text,
                    flags=re.M,
                )
                with open(dst, "w", encoding="utf-8") as fh:
                    fh.write(text)
            extra_pc.insert(0, pc_fix_dir)
            # glib2 package bin holds the meson gnome module tools
            # (glib-mkenums, gdbus-codegen, glib-compile-resources, ...) as
            # python3 scripts; pin them so gnome.*() resolves them.
            glib_bin = os.path.join(glib_pkg, "bin")
            if os.path.isdir(glib_bin):
                self.buildenv_info.prepend_path("PATH", glib_bin)
                for tool in ("glib-mkenums", "glib-genmarshal", "gdbus-codegen",
                             "glib-compile-resources", "glib-compile-schemas",
                             "gio-querymodules"):
                    tool_path = os.path.join(glib_bin, tool)
                    if os.path.isfile(tool_path):
                        tc.binaries[tool] = tool_path
        extra_pc.append("/storage/Users/currentUser/usr/local/lib/pkgconfig")
        # pc-fix must win over the PkgConfigDeps-generated .pc (which lacks
        # giomoduledir), so put extra_pc BEFORE tc.pkg_config_path.
        tc.pkg_config_path = os.pathsep.join(extra_pc + [tc.pkg_config_path])
        # glib's gi18n-lib.h includes <libintl.h> unconditionally; the shared
        # glib .so already embeds proxy-libintl but does not ship the header.
        # Add the proxy-libintl package include dir so gettext/bindtextdomain
        # declarations resolve (musl has no libc gettext).
        if self.dependencies.get("proxy-libintl"):
            intl_pkg = self.dependencies["proxy-libintl"].package_folder
            intl_inc = os.path.join(intl_pkg, "include")
            if os.path.isdir(intl_inc):
                tc.c_args.append(f"-I{intl_inc}")
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        meson = Meson(self)
        meson.configure()
        meson.build()
        if cross_building(self):
            self.output.info(
                "cross-building: skip meson.test() (OHOS binaries are not runnable on the build host)"
            )
        else:
            if hasattr(os, "uname") and os.uname().sysname in ("OHOS", "HarmonyOS"):
                build_folder = self.build_folder
                # The shared glib exposes libglib/libgio/... as shared libraries;
                # meson test runs the OHOS test binaries directly and needs
                # LD_LIBRARY_PATH to resolve them (glib package_info does not
                # inject runenv). Cover the shared glib's own lib dir; its .so
                # only NEEDs libc.so so no transitive lib dirs are required.
                run_lib_dirs = []
                for dep_name in ("glib",):
                    dep = self.dependencies.get(dep_name)
                    if dep and dep.package_folder:
                        run_lib_dirs.append(os.path.join(dep.package_folder, "lib"))
                ld_path = os.environ.get("LD_LIBRARY_PATH", "")
                extra = ":".join(d for d in run_lib_dirs if d)
                if ld_path:
                    ld_path = extra + ":" + ld_path if extra else ld_path
                else:
                    ld_path = extra

                def _ohos_meson_test():
                    self.run(
                        'LD_LIBRARY_PATH="{}" meson test -v -C "{}" '
                        "--timeout-multiplier=16".format(ld_path, build_folder)
                    )

                meson.test = _ohos_meson_test

            meson.test()

    def package(self):
        meson = Meson(self)
        meson.install()
        # ⚠️ meson install 会清理 DT_RUNPATH：把 .dynstr 中的 rpath 路径字符串
        # 用 'X' 覆盖并删除 DT_RUNPATH 条目。这改写了 .so 内容，使链接时写入的
        # .codesign 哈希失配，OHOS loader 校验失败 → dlopen 报 Permission denied
        # （libsoup3 铁证同源）。用 build 目录的原始链接产物覆盖被修改的 .so。
        _module_build = os.path.join(
            self.build_folder, "tls", "openssl", "libgioopenssl.so"
        )
        _module_pkg = os.path.join(
            self.package_folder, "lib", "gio", "modules", "libgioopenssl.so"
        )
        if os.path.exists(_module_build):
            shutil.copy2(_module_build, _module_pkg)

    def package_info(self):
        # GIO modules are dlopened by libgio at runtime; expose the module dir so
        # consumers can point GIO_EXTRA_MODULES / GIO_MODULE_DIR at it.
        module_dir = os.path.join(self.package_folder, "lib", "gio", "modules")
        if os.path.isdir(module_dir):
            self.runenv_info.prepend_path("GIO_EXTRA_MODULES", module_dir)
            self.runenv_info.prepend_path("GIO_MODULE_DIR", module_dir)
        # No linkable public library: consumers use GLib's TLS API only.
        self.cpp_info.includedirs = ["include"]