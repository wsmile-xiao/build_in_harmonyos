#!/usr/bin/env python3
"""Conan recipe for awf-gtk 4.2.0 on OpenHarmony PC.

awf-extended ("A widget factory") is a cross GTK/Qt theme preview application.
This recipe builds its GTK4 frontend (`awf-gtk4`) as an application package
(bin/awf-gtk4 + share/ desktop/man/icons/locale/bash-completion).

The upstream release archive ships only configure.ac + build.sh (no generated
configure), so build() runs `autoreconf -fi` first. The GTK4 stack is consumed
from the installed OpenHarmony system prefix (same model as gtkdatabox), while
cairo/graphene/libnotify headers and libs come from conan packages (the system
prefix does not ship their .pc files / headers).

Key adaptations:
- E114: the autoconf-generated configure's config.status temp directory is
  moved off HMDFS (mktemp on HMDFS creates drwx--S--- dirs that cannot be
  written).
- E252 boundary: `--version`/`--list` print and `_exit(0)` (fflush first),
  skipping GTK teardown that crashes headless (Signal 5/Signal 11). Full GUI
  rendering still requires an OpenHarmony PC display session.
- The system gtk4.pc Requires `cairo-gobject` which does not exist on OHOS;
  a generated pkg-config overlay drops that requirement and supplies
  cairo/graphene-gobject/libnotify/libpng .pc entries pointing at the conan
  dependency package folders and the system prefix.
"""
import glob
import io
import os
import re
import shlex
import shutil
import ssl
import subprocess
import tarfile
import urllib.request

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import Environment
from conan.tools.files import get, load, save, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class AwfgtkConan(ConanFile):
    name = "awf-gtk"
    version = "4.2.0"
    description = "GTK4 主题预览工具：预览当前桌面主题下各 GUI 控件外观（A widget factory GTK4 前端）"
    license = "GPL-3.0-or-later"
    homepage = "https://github.com/luigifab/awf-extended"
    url = ""  # CI fills this

    package_type = "application"

    # L0p 门禁要求 settings 含 os/compiler/build_type/arch 四项（对齐 CI profile）
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # cairo/graphene/libnotify: headers + libs (system prefix lacks these)
        self.requires("cairo/1.18.4")
        self.requires("graphene/1.10.8")
        self.requires("libnotify/0.8.3")
        # 依赖图中 glib2/2.88.0 声明 zlib/1.3.1（--static 无 -fPIC 旧版，E005），
        # 而 cairo/graphene/libpng 等拉 zlib/1.3.1.1（-fPIC 版，见 E234）。
        # override 到 1.3.1.1 消除版本冲突，并保证共享链接使用 PIC libz.a。
        self.requires("zlib/1.3.1.1", override=True)
        # dbus/1.14.10（libnotify 传递依赖）声明 expat/2.8.2，若解析到 conancenter
        # 上游配方其 tool_require cmake 在 OHOS 构建报 KeyError；其余依赖拉
        # expat/2.8.2.1（ohpcd 已发布适配配方）。override 到 2.8.2.1（同 avahi）。
        self.requires("expat/2.8.2.1", override=True)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        if str(self.settings.os) == "OHOS":
            self._ensure_system_deps()
            self._sign_libnotify_external()
        overlay = self._create_pkgconfig_overlay()
        envvars = self._system_env(overlay).vars(self)
        with envvars.apply():
            # Upstream release ships no generated configure. autoreconf needs
            # ACLOCAL_PATH (pkg.m4 for PKG_PROG_PKG_CONFIG) from _system_env.
            self.run("autoreconf -fi", cwd=self.source_folder)
            if str(self.settings.os) == "OHOS":
                self._patch_config_status_tmpdir()
            prefix = "/"
            configure_args = [
                "--prefix={}".format(prefix),
                "--enable-only-gtk4",
            ]
            # configure 失败时输出 config.log 尾部（本地无法复现 CI #30162
            # "C compiler cannot create executables"，需 CI 日志给出真实错误）
            self.run(
                "./configure {args} ; rc=$?; if [ $rc -ne 0 ]; then "
                "echo '=== configure FAILED, config.log error context ==='; "
                "grep -nE 'conftest|error:|cannot|undefined|ld:|collect2|No such' config.log 2>/dev/null | tail -40; "
                "echo '=== manual compile test ==='; "
                "printf 'int main(void){{return 0;}}\\n' > _cc_test.c; "
                "$CC -o _cc_test _cc_test.c 2>&1 | tail -20; "
                "echo \"manual compile exit: $?\"; "
                "echo '=== loader path file ==='; "
                "cat /etc/ld-musl-aarch64.path 2>/dev/null; "
                "echo '=== SDK libxml2 forced test ==='; "
                "env -u LD_LIBRARY_PATH $CC -o _cc_sdk _cc_test.c 2>&1 | tail -6; "
                "echo \"sdk test exit: $?\"; "
                "echo '=== lld binding (readelf) ==='; "
                "readelf -d /data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/bin/lld 2>/dev/null | grep -E 'NEEDED|RUNPATH|RPATH'; "
                "echo '=== xml2 load trace via ldd ==='; "
                "ldd /data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/bin/lld 2>&1 | grep -iE 'xml2|not found' | head -5; "
                "echo '=== env diagnostic ==='; "
                "echo \"HOME=$HOME\"; "
                "echo \"LD_LIBRARY_PATH=$LD_LIBRARY_PATH\"; "
                "echo '--- libxml2 candidates ---'; "
                "ls -la $HOME/usr/local/lib/libxml2* 2>/dev/null; "
                "ls -la $HOME/usr/local/lib/external/libxml2* 2>/dev/null; "
                "ls -la /data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib/libxml2* 2>/dev/null; "
                "echo '--- lld RUNPATH/NEEDED ---'; "
                "readelf -d /data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/bin/lld 2>/dev/null | grep -E 'NEEDED|RUNPATH|RPATH'; "
                "exit $rc; fi".format(
                    args=" ".join(configure_args)
                ),
                cwd=self.source_folder,
            )
            self.run("make -j1", cwd=self.source_folder)

    def package(self):
        envvars = self._system_env(None).vars(self)
        with envvars.apply():
            self.run("make install DESTDIR={}".format(shlex.quote(str(self.package_folder))),
                     cwd=self.source_folder)

    def package_info(self):
        # Application package: no libs/headers. bin/awf-gtk4 only.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.bindirs = ["bin"]

    # ── E114: config.status temp dir off HMDFS ──

    def _patch_config_status_tmpdir(self):
        """Move config.status temp files to a writable dir (E114, HMDFS mktemp issue).

        The autoconf-generated configure/config.status create their awk temp
        directory with `mktemp -d ./confXXXXXX`; on HMDFS the resulting dir has
        drwx--S--- (setgid) permissions so even its owner cannot write into it.
        We replace the whole block with a fixed pre-created tmpdir.
        """
        fixed_tmp = os.path.join(self.source_folder, "..", ".awf-gtk-config-tmp")
        fixed_tmp = os.path.abspath(fixed_tmp)
        os.makedirs(fixed_tmp, exist_ok=True)
        os.chmod(fixed_tmp, 0o700)

        old_block = (
            "{\n"
            "  tmp=`(umask 077 && mktemp -d \"./confXXXXXX\") 2>/dev/null` &&\n"
            "  test -d \"$tmp\"\n"
            "}  ||\n"
            "{\n"
            "  tmp=./conf$$-$RANDOM\n"
            "  (umask 077 && mkdir \"$tmp\")\n"
            "} || as_fn_error $? \"cannot create a temporary directory in .\" \"$LINENO\" 5\n"
            "ac_tmp=$tmp\n"
        )
        new_block = (
            "tmp={}\n"
            "mkdir -p \"$tmp\" 2>/dev/null || true\n"
            "ac_tmp=$tmp\n"
        ).format(fixed_tmp)

        for script_name in ("configure", "config.status"):
            script_path = os.path.join(self.source_folder, script_name)
            if not os.path.isfile(script_path):
                continue
            content = load(self, script_path)
            if old_block in content:
                content = content.replace(old_block, new_block)
            elif "ac_tmp=$tmp" in content:
                # Fallback: some autoconf versions inline the tmp assignment differently.
                content = content.replace("ac_tmp=$tmp", "ac_tmp={}".format(fixed_tmp))
            else:
                self.output.info("E114: {} has no ac_tmp pattern, skipping".format(script_name))
                continue
            save(self, script_path, content)
            os.chmod(script_path, 0o755)
            self.output.info("E114: {} config.status tmpdir -> {}".format(script_name, fixed_tmp))

    # ── GTK4 system prefix discovery ──

    def _system_prefix(self):
        return self._find_gtk_prefix()

    def _find_gtk_prefix(self):
        candidates = []
        for env_name in ("GTK_PREFIX", "DEFAULT_PREFIX"):
            value = os.environ.get(env_name)
            if value:
                candidates.append(os.path.normpath(value))
        candidates.append("/storage/Users/currentUser/usr/local")
        for pattern in (
            "/data/service/hnp/*/*/lib/pkgconfig",
            "/data/service/hnp/*/*/share/pkgconfig",
        ):
            for pc_dir in sorted(glob.glob(pattern)):
                candidates.append(os.path.dirname(os.path.dirname(pc_dir)))
        for pc_file in sorted(glob.glob("/data/service/hnp/**/gtk4.pc", recursive=True)):
            candidates.append(os.path.dirname(os.path.dirname(pc_file)))

        seen = set()
        for prefix in candidates:
            if prefix in seen:
                continue
            seen.add(prefix)
            if self._gtk_pc_exists(prefix):
                self.output.info("Using GTK4 prefix {}".format(prefix))
                return prefix
        return candidates[0] if candidates else "/storage/Users/currentUser/usr/local"

    def _gtk_pc_exists(self, prefix):
        return (
            os.path.isfile(os.path.join(prefix, "lib", "pkgconfig", "gtk4.pc"))
            or os.path.isfile(os.path.join(prefix, "share", "pkgconfig", "gtk4.pc"))
        )

    # ── GTK4 system deps auto-install (cmd-pkgs) ──

    def _ensure_system_deps(self):
        """Install the OpenHarmony GTK4 stack from cmd-pkgs when missing.

        CI workers are clean: no system GTK4 is preinstalled, so gtk4.pc (and
        its pango/gdk-pixbuf/cairo/fontconfig/freetype/harfbuzz/... stack) must
        be provisioned from the prebuilt cmd-pkgs packages (same model as
        gtkdatabox). Conan deps (cairo/graphene/libnotify) stay as declared in
        requirements(); cmd-pkgs only supplies the system GTK4 prefix pieces
        that have no conan recipe on ohpcd (gtk4 itself).
        """
        prefix = os.path.expanduser("~/usr/local")
        pc_dir = os.path.join(prefix, "lib", "pkgconfig")
        share_pc_dir = os.path.join(prefix, "share", "pkgconfig")

        def _pc_present(name):
            return (
                os.path.isfile(os.path.join(pc_dir, name))
                or os.path.isfile(os.path.join(share_pc_dir, name))
            )

        # CI worker 是全新环境：autoreconf -fi 需要 aclocal/automake/m4/libtool
        # （本机有 ~/usr/local/bin 的 automake，但 CI 无）。cmd-pkgs 提供
        # autotools 工具链，缺失时一并安装（参照 gtkdatabox 系统依赖模型）。
        # 注意：cmd-pkgs automake-1.16.5 包内 aclocal 的 @INC 指向
        # share/automake-1.17（与包内 automake-1.16 目录不匹配，会报
        # Can't locate Automake/Config.pm），故用 1.17（@INC 自洽）。
        # aclocal/automake 是 perl 脚本，shebang 指向 ~/usr/local/bin/perl，
        # 因此还需先装 perl。
        # 工具链【总是安装】（_install_cmd_pkg 内部会先清理已存在目标再解压，
        # 幂等覆盖）：同一 CI worker 可能残留上一轮构建的旧版本 automake
        # （如 1.16.5，其 aclocal @INC 指向 automake-1.17 但 share 目录是
        # automake-1.16），若按 bin 存在跳过安装会导致残留版本继续报
        # Can't locate Automake/Config.pm（CI #30156）。
        toolchain = [
            ("perl", "5.42.2", "perl"),
            ("automake", "1.17", "aclocal"),
            ("m4", "1.4.19", "m4"),
            ("libtool", "2.4.7", "libtool"),
            ("autoconf", "2.72", "autoconf"),
        ]
        for name, version, bin_name in toolchain:
            self._install_cmd_pkg(name, version, prefix)

        # clang 的链接器 lld（ohos-sdk llvm）动态依赖 libxml2.so.16，SDK
        # llvm/lib 自带该库（lld RUNPATH=$ORIGIN/../lib）。CI #30715 证实：
        # 卸载 LD_LIBRARY_PATH 后 clang 链接成功（lld 经 RUNPATH 加载 SDK
        # libxml2），而 cmd-pkgs libxml2 装入 ~/usr/local/lib 后遮蔽 SDK 版
        # 导致 lld 加载失败（Error loading shared library libxml2.so.16）。
        # 因此【不安装 cmd-pkgs libxml2】，并在 _system_env 中把 SDK
        # llvm/lib 前置到 LD_LIBRARY_PATH 首位，确保 lld 始终用 SDK 自带库。
        # 同时清理 CI worker 复用残留的 cmd-pkgs libxml2（_install_cmd_pkg
        # 未跟踪的旧文件）。
        import glob as _glob
        for stale in _glob.glob(os.path.join(prefix, "lib", "libxml2.so*")):
            try:
                os.remove(stale)
            except OSError:
                pass

        # gtk4.pc Requires: pango/pangocairo/gdk-pixbuf-2.0/cairo/graphene-
        # gobject/gio-2.0; cairo-gobject is dropped by the pkg-config overlay
        # (no such .pc on OHOS). Install the full system GTK4 stack.
        # gdk-pixbuf 的 loader 需要 libtiff/libjpeg/libwebp/zstd（运行时符号
        # TIFF* 等，CI #30152 因缺失报 Error relocating）。
        deps = [
            ("glib", "2.88.0", "glib-2.0.pc", "libglib-2.0.so", "external"),
            ("gdk-pixbuf", "2.42.12", "gdk-pixbuf-2.0.pc", "libgdk_pixbuf-2.0.so.0", "external"),
            ("pango", "1.50.14", "pango.pc", "libpango-1.0.so.0", "external"),
            ("cairo", "1.18.2", "cairo.pc", "libcairo.so.2", "external"),
            ("fontconfig", "2.16.0", "fontconfig.pc", "libfontconfig.so.1", "external"),
            ("freetype", "2.14.3", "freetype2.pc", "libfreetype.so.6", "external"),
            ("harfbuzz", "14.2.0", "harfbuzz.pc", "libharfbuzz.so.0", "external"),
            ("libpng", "1.6.43", "libpng.pc", "libpng16.so.16", "external"),
            ("pixman", "0.46.4", "pixman-1.pc", "libpixman-1.so.0", "external"),
            ("atk", "2.38.0", "atk.pc", "libatk-1.0.so.0", "lib"),
            ("fribidi", "1.0.13", "fribidi.pc", "libfribidi.so.0", "external"),
            ("libepoxy", "1.5.10", "epoxy.pc", "libepoxy.so.0", "external"),
            ("zlib", "1.3.1", "zlib.pc", "libz.so", "external"),
            ("libtiff", "4.6.0", "libtiff-4.pc", "libtiff.so.5", "external"),
            ("libjpeg-turbo", "2.1.5.1", "libjpeg.pc", "libjpeg.so.62", "external"),
            ("libwebp", "1.3.2", "libwebp.pc", "libwebp.so.7", "external"),
            ("zstd", "1.5.6", "libzstd.pc", "libzstd.so.1", "lib"),
            ("gtk", "4.22.4", "gtk4.pc", "libgtk-4.so.1", "lib"),
        ]
        # 条件安装：仅当 .pc 缺失或【规范位置】的运行库文件缺失时才安装。
        # CI worker 的 ~/usr/local 跨构建持久化（G27）：lib 顶层可能残留
        # 上一轮构建的损坏 .so（libglib-2.0.so/libz.so/libpng16.so 等），
        # 若只按 lib 顶层文件存在判断会误判为已安装、跳过 external 签名
        # 依赖集刷新，test() 运行时从 lib 顶层加载残留坏库报 Error loading
        # shared library（CI #30719/30745）。因此按每个包的规范位置校验：
        # GTK 栈主体（glib/pango/cairo/...）在 lib/external，gtk/atk/zstd
        # 在 lib 顶层。
        def _lib_present(name, location):
            base = os.path.join(prefix, "lib", "external") if location == "external" else os.path.join(prefix, "lib")
            path = os.path.join(base, name)
            # 文件存在且非空（>0 字节）才认为有效：CI worker 的 ~/usr/local
            # 跨构建持久化，可能残留 0 字节/截断的损坏 .so（libglib-2.0.so、
            # libz.so、libpng16.so 等），若只按 isfile 判断会误判已安装、
            # 跳过 external 依赖集刷新，test() 运行时加载残留坏库报 Error
            # loading shared library（CI #30719/30745/30755）。
            return os.path.isfile(path) and os.path.getsize(path) > 0

        missing = [
            (name, version, pc_name)
            for name, version, pc_name, lib_name, location in deps
            if not (_pc_present(pc_name) and _lib_present(lib_name, location))
        ]
        if not missing:
            self.output.info("GTK4 system dependencies already present at {}".format(prefix))
        else:
            for name, version, pc_name in missing:
                self._install_cmd_pkg(name, version, prefix)
            if not self._gtk_pc_exists(prefix):
                raise ConanException("GTK4 auto-install from cmd-pkgs did not produce gtk4.pc")
            self.output.info("GTK4 system dependencies installed at {}".format(prefix))

        # cmd-pkgs 库的 DT_NEEDED 是【绝对路径】（libgtk-4.so.1 NEEDED
        # /storage/Users/currentUser/usr/local/lib/libglib-2.0.so、libtiff.so、
        # libjpeg.so；libcairo.so.2 NEEDED libz.so/libpng16.so 等），musl
        # loader 对绝对路径 NEEDED 直接加载该路径、不走 LD_LIBRARY_PATH
        # 搜索（CI #30803/#30829 失败根因：报错路径均为 ~/usr/local/lib/*.so
        # 而非 external）。本机 test 通过是因为本机 lib 顶层有这些库
        # （软链到 external 签名库）。因此在 lib 顶层为 external 的签名库
        # 建立软链，确保绝对路径 NEEDED 命中签名库；lib 顶层残留旧文件
        # （GTK3 时代 libcairo.so.2/libgdk_pixbuf-2.0.so.0 等）一并替换。
        external_dir = os.path.join(prefix, "lib", "external")
        if os.path.isdir(external_dir):
            for ext_name in sorted(os.listdir(external_dir)):
                if not ext_name.startswith("lib") or ".so" not in ext_name:
                    continue
                ext_src = os.path.join(external_dir, ext_name)
                if not os.path.isfile(ext_src):
                    continue
                link_name = ext_name
                if ext_name == "libpng16.so.16":
                    # 绝对路径 NEEDED 用的是无版本名 libpng16.so
                    link_name = "libpng16.so"
                top = os.path.join(prefix, "lib", link_name)
                rel = os.path.join("external", ext_name)
                if os.path.islink(top):
                    if os.readlink(top) == rel:
                        continue
                    try:
                        os.remove(top)
                    except OSError:
                        continue
                elif os.path.exists(top):
                    try:
                        os.remove(top)
                    except OSError:
                        continue
                try:
                    os.symlink(rel, top)
                except OSError:
                    pass
            # libgdk_pixbuf（旧版）NEEDED 绝对路径 libpng.so；external 只有
            # libpng16.so.16，补一条 libpng.so 软链（本机探索期同款）。
            top_png = os.path.join(prefix, "lib", "libpng.so")
            if not os.path.exists(top_png) and os.path.isfile(
                os.path.join(external_dir, "libpng16.so.16")
            ):
                try:
                    os.symlink("external/libpng16.so.16", top_png)
                except OSError:
                    pass

    # ── libnotify 签名放入 external ──
    # OHOS 动态链接器要求共享库必须用 binary-sign-tool 签名才能加载
    # （SKILL: ELF 签名，未签名加载报 Error loading shared library）。
    # libnotify 是 conan 依赖（libnotify/0.8.3），其 .so 在 conan 缓存里，
    # 未签名 → awf-gtk4 运行时重定位报 notify_* symbol not found（CI
    # #30719/30745/30755/30760）。这里把 conan 缓存的 libnotify.so.4
    # 复制到 external 目录并 selfSign 签名，使 test() 阶段 LD_LIBRARY_PATH
    # 命中签名版（本机探索期方案：libnotify.so.4 + .signed 放 external）。
    def _sign_libnotify_external(self):
        prefix = self._system_prefix()
        external_dir = os.path.join(prefix, "lib", "external")
        target = os.path.join(external_dir, "libnotify.so.4")
        if not os.path.isdir(external_dir):
            self.output.warning("external dir missing, skip libnotify signing: {}".format(external_dir))
            return
        if self._has_ohos_signature(target):
            self.output.info("libnotify.so.4 already signed at {}".format(target))
            return
        dep = self.dependencies.get("libnotify")
        if not dep or not getattr(dep, "package_folder", None):
            self.output.warning("libnotify conan dep unavailable, skip signing")
            return
        src = None
        for libdir in dep.cpp_info.libdirs or ["lib"]:
            full = libdir if os.path.isabs(libdir) else os.path.join(dep.package_folder, libdir)
            cand = os.path.join(full, "libnotify.so.4")
            if os.path.isfile(cand):
                src = cand
                break
        if not src:
            self.output.warning("libnotify.so.4 not found in conan package, skip signing")
            return
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            raise ConanException("binary-sign-tool is required to sign libnotify for OHOS loader")
        objcopy = shutil.which("llvm-objcopy") or "/data/service/hnp/bin/llvm-objcopy"
        tmp_dir = os.path.join(prefix, ".sign-tmp")
        try:
            os.makedirs(tmp_dir, exist_ok=True)
            tmp_in = os.path.join(tmp_dir, "libnotify.so.4")
            tmp_out = tmp_in + ".signed"
            shutil.copy2(src, tmp_in)
            # 移除已有 .codesign 段（若 conan 包已带签名，重复签名会失败）
            subprocess.run(
                [objcopy, "--remove-section", ".codesign", tmp_in],
                capture_output=True,
                timeout=30,
            )
            subprocess.check_call(
                [
                    signer, "sign",
                    "-selfSign", "1",
                    "-inFile", tmp_in,
                    "-outFile", tmp_out,
                    "-signAlg", "SHA256withECDSA",
                ],
                timeout=120,
            )
            shutil.move(tmp_out, target)
            os.chmod(target, 0o755)
            self.output.info("libnotify.so.4 signed into external: {}".format(target))
        finally:
            for stale in (tmp_in, tmp_in + ".signed"):
                if os.path.isfile(stale):
                    try:
                        os.unlink(stale)
                    except OSError:
                        pass

    @staticmethod
    def _has_ohos_signature(path):
        try:
            with open(path, "rb") as binary:
                data = binary.read()
        except OSError:
            return False
        return b".codesign" in data or b".note.ohos" in data

    def _install_cmd_pkg(self, name, version, prefix):
        """Download and extract one cmd-pkgs OHOS aarch64 package."""
        url = (
            "https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/"
            "download/pkgs/{}-{}-ohos-aarch64.tar.gz".format(name, version)
        )
        self.output.info("Installing {} {} from cmd-pkgs into {}".format(name, version, prefix))
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        try:
            with urllib.request.urlopen(url, context=ctx, timeout=300) as response:
                data = response.read()
            with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tf:
                # HMDFS 上 extractall 覆盖已存在的同名文件会报 Operation not
                # permitted（E046 平台限制：rm -f && ln -s 不能直接覆盖）。
                # 先移除目标路径中已存在的文件/软链，再整体解压。
                for member in tf.getmembers():
                    target = os.path.join(prefix, member.name)
                    if os.path.lexists(target) and not os.path.isdir(target):
                        try:
                            os.remove(target)
                        except OSError:
                            pass
                tf.extractall(prefix)
            self.output.info("  Installed {} {} from cmd-pkgs".format(name, version))
        except Exception as exc:
            raise ConanException("Failed to install {} {} from cmd-pkgs: {}".format(name, version, exc))
        if name == "libpng":
            src = os.path.join(prefix, "lib", "pkgconfig", "libpng16.pc")
            dst = os.path.join(prefix, "lib", "pkgconfig", "libpng.pc")
            if os.path.isfile(src) and not os.path.isfile(dst):
                import shutil
                shutil.copy2(src, dst)
                self.output.info("  Created libpng.pc alias for pkg-config")

    # ── pkg-config overlay (sanitized gtk4.pc + dep .pc) ──

    def _create_pkgconfig_overlay(self):
        """Generate a pkg-config overlay dir in the build folder.

        The deployed system gtk4.pc Requires `cairo-gobject`, but no
        cairo-gobject.pc exists anywhere on OHOS. We copy the system gtk4.pc
        dropping that requirement, and provide cairo/graphene-gobject/libnotify
        /libpng .pc entries pointing at the conan dependency package folders and
        the system prefix. The overlay is prepended to PKG_CONFIG_PATH.
        """
        prefix = self._system_prefix()
        overlay = os.path.join(self.build_folder, "pkgconfig-overlay")
        os.makedirs(overlay, exist_ok=True)

        # 1) gtk4.pc — system copy without cairo-gobject requirement
        system_gtk4 = None
        for cand in (
            os.path.join(prefix, "lib", "pkgconfig", "gtk4.pc"),
            os.path.join(prefix, "share", "pkgconfig", "gtk4.pc"),
        ):
            if os.path.isfile(cand):
                system_gtk4 = cand
                break
        if system_gtk4:
            content = load(self, system_gtk4)
            # The system gtk4.pc Requires cairo-gobject (absent on OHOS) and
            # pins pango >= 1.56 while the deployed pango is 1.50.14. Mirror the
            # validated exploration overlay: drop cairo-gobject, relax pango.
            content = re.sub(r"cairo-gobject\s*>=\s*[\d.]+\s*", " ", content)
            content = re.sub(r"cairo-gobject\s*", " ", content)
            content = re.sub(r"pango\s*>=\s*1\.5[0-9]", "pango >=  1.50", content)
            content = re.sub(r"pangocairo\s*>=\s*1\.5[0-9]", "pangocairo >=  1.50", content)
            content = re.sub(r",\s*,", ",", content)
            # 只折叠行内连续空格，保留换行（.pc 字段以换行分隔，压平会导致
            # 例如 `libdir=${prefix}/lib targets=broadway` 挤在一行解析失败）
            content = re.sub(r"[ \t]{2,}", " ", content)
            save(self, os.path.join(overlay, "gtk4.pc"), content)
            self.output.info("overlay gtk4.pc (cairo-gobject dropped, pango relaxed)")
        else:
            raise ConanException("gtk4.pc not found under system prefix {}".format(prefix))

        # 2) cairo.pc — include from conan cairo, libdir from system prefix (signed)
        cairo = self.dependencies["cairo"]
        cairo_inc = os.path.join(cairo.package_folder, "include")
        cairo_pc = """prefix={inc}
includedir=${{prefix}}
libdir={lib}

Name: cairo
Description: Multi-platform 2D graphics library
Version: 1.18.4
Requires.private: zlib, libpng >=  1.4.0, fontconfig >=  2.13.0, freetype2 >=  23.0.17, pixman-1 >=  0.40.0
Libs: -L${{libdir}} -lcairo
Cflags: -I${{includedir}}/cairo
""".format(inc=cairo_inc, lib=os.path.join(prefix, "lib"))
        save(self, os.path.join(overlay, "cairo.pc"), cairo_pc)

        # 3) graphene pcs — from conan graphene package
        graphene = self.dependencies["graphene"]
        g_prefix = graphene.package_folder
        graphene_1 = """prefix={pfx}
includedir=${{prefix}}/include
libdir=${{prefix}}/lib

graphene_has_sse2=0
graphene_has_gcc=0
graphene_has_neon=1
graphene_has_scalar=1

Name: Graphene
Description: Math classes for graphic libraries
Version: 1.10.8
Requires: gobject-2.0 >=  2.30.0
Libs: -L${{libdir}} -lgraphene-1.0 -lm -pthread
Cflags: -I${{includedir}}/graphene-1.0 -pthread -I${{libdir}}/graphene-1.0/include
""".format(pfx=g_prefix)
        save(self, os.path.join(overlay, "graphene-1.0.pc"), graphene_1)
        graphene_gobject = """prefix={pfx}
includedir=${{prefix}}/include

graphene_has_sse2=0
graphene_has_gcc=0
graphene_has_neon=1
graphene_has_scalar=1

Name: Graphene-GObject
Description: GObject types for Graphene
Version: 1.10.8
Requires: graphene-1.0, gobject-2.0
Cflags: -I${{includedir}}/graphene-1.0
""".format(pfx=g_prefix)
        save(self, os.path.join(overlay, "graphene-gobject-1.0.pc"), graphene_gobject)

        # 4) libnotify.pc — from conan libnotify package
        libnotify = self.dependencies["libnotify"]
        ln_pc = """prefix={pfx}
includedir=${{prefix}}/include
libdir=${{prefix}}/lib

Name: libnotify
Description: Notifications Library
Version: 0.8.3
Requires: gdk-pixbuf-2.0, gio-2.0 >=  2.62.0, glib-2.0 >=  2.62.0
Libs: -L${{libdir}} -lnotify
Cflags: -I${{includedir}}
""".format(pfx=libnotify.package_folder)
        save(self, os.path.join(overlay, "libnotify.pc"), ln_pc)

        # 5) libpng.pc — system libpng16 alias
        libpng_pc = """prefix={pfx}
includedir=${{prefix}}/include/libpng16
libdir=${{prefix}}/lib

Name: libpng
Description: Loads and saves PNG files
Version: 1.6.43
Requires.private: zlib
Libs: -L${{libdir}} -lpng16
Cflags: -I${{includedir}}
""".format(pfx=prefix)
        save(self, os.path.join(overlay, "libpng.pc"), libpng_pc)

        self.output.info("pkg-config overlay generated at {}".format(overlay))
        return overlay

    # ── Build/runtime environment ──

    def _system_env(self, overlay):
        prefix = self._system_prefix()
        env = Environment()

        # OHOS /tmp 只读：clang 等编译工具需要可写临时目录。CI 干净环境
        # 无 TMPDIR，configure 的 C 编译器测试报 "C compiler cannot create
        # executables"（clang: unable to make temporary file: Read-only file
        # system，CI #30159）。本机 shell 有 TMPDIR=/storage/.../tmp 故本机
        # 通过。显式定义 TMPDIR/TMP/TEMP 指向可写目录。
        tmpdir = os.path.expanduser("~/tmp")
        try:
            os.makedirs(tmpdir, exist_ok=True)
        except OSError:
            pass
        env.define("TMPDIR", tmpdir)
        env.define("TMP", tmpdir)
        env.define("TEMP", tmpdir)

        # Compiler executables from the Conan profile conf (R33: no bare shell
        # env vars — must come from the toolchain/conf).
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        if compilers.get("c"):
            env.define("CC", compilers["c"])
        if compilers.get("cpp"):
            env.define("CXX", compilers["cpp"])
        if compilers.get("ar"):
            env.define("AR", compilers["ar"])
        if compilers.get("ranlib"):
            env.define("RANLIB", compilers["ranlib"])

        # conan dependency include/lib dirs
        for dep_name in ("cairo", "graphene", "libnotify"):
            dep = self.dependencies.get(dep_name)
            if not dep or not getattr(dep, "package_folder", None):
                continue
            for inc in dep.cpp_info.includedirs or ["include"]:
                full_inc = inc if os.path.isabs(inc) else os.path.join(dep.package_folder, inc)
                if os.path.isdir(full_inc):
                    env.append("CPPFLAGS", "-I{}".format(full_inc))
            for lib in dep.cpp_info.libdirs or ["lib"]:
                full_lib = lib if os.path.isabs(lib) else os.path.join(dep.package_folder, lib)
                if os.path.isdir(full_lib):
                    env.append("LDFLAGS", "-L{}".format(full_lib))
                    env.prepend_path("LD_LIBRARY_PATH", full_lib)

        # system GTK prefix
        env.prepend_path("PKG_CONFIG_PATH", os.path.join(prefix, "lib", "pkgconfig"))
        env.prepend_path("PKG_CONFIG_PATH", os.path.join(prefix, "share", "pkgconfig"))
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(prefix, "lib", "external"))
        env.append("LDFLAGS", "-L{}".format(os.path.join(prefix, "lib", "external")))
        env.prepend_path("PATH", os.path.join(prefix, "bin"))
        # pkg.m4 (PKG_PROG_PKG_CONFIG) lives under the pkg-config installation.
        # HMDFS 目录形如 /data/service/hnp/pkg-config.org/pkg-config_0.29.2/
        pkg_m4_dirs = sorted(
            glob.glob("/data/service/hnp/pkg-config*/*/share/aclocal")
        ) or sorted(glob.glob("/data/service/hnp/**/share/aclocal", recursive=True))
        for pkg_m4_dir in pkg_m4_dirs:
            if os.path.isfile(os.path.join(pkg_m4_dir, "pkg.m4")):
                env.prepend_path("ACLOCAL_PATH", pkg_m4_dir)
        if str(self.settings.os) == "OHOS":
            hnp_pkgconfigs = sorted(
                glob.glob("/data/service/hnp/*/*/lib/pkgconfig"),
                key=lambda p: (p.count("/"), p),
            )
            for pkgconfig_dir in hnp_pkgconfigs:
                env.prepend_path("PKG_CONFIG_PATH", pkgconfig_dir)
            hnp_runtime_libs = []
            for pattern in ("libpcre2-8.so*", "libffi.so*", "libexpat.so*", "libintl.so*"):
                for match in glob.glob("/data/service/hnp/*/*/lib/{}".format(pattern)):
                    hnp_runtime_libs.append(os.path.dirname(match))
            for libdir in sorted(set(hnp_runtime_libs)):
                env.append_path("LD_LIBRARY_PATH", libdir)
        env.append("CPPFLAGS", "-I{}".format(os.path.join(prefix, "include")))
        env.append("LDFLAGS", "-L{}".format(os.path.join(prefix, "lib")))
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(prefix, "lib"))

        # clang 的链接器 lld 动态依赖 libxml2.so.16（ohos-sdk llvm）。
        # musl 搜索顺序 LD_LIBRARY_PATH 优先于 lld 的 RUNPATH
        # ($ORIGIN/../lib)，因此必须把 SDK 自带 libxml2 所在目录放到
        # LD_LIBRARY_PATH 最前，否则 ~/usr/local/lib 下任何 libxml2.so.16
        # 都会遮蔽 SDK 版导致 lld 加载失败（CI #30715：Error loading
        # shared library libxml2.so.16 / xmlFreeDoc symbol not found）。
        sdk_llvm_libs = sorted(
            glob.glob("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib")
        )
        for sdk_libdir in sdk_llvm_libs:
            env.prepend_path("LD_LIBRARY_PATH", sdk_libdir)

        if overlay:
            env.prepend_path("PKG_CONFIG_PATH", overlay)

        return env
