#!/usr/bin/env python3
"""Conan recipe for libcryptui 3.12.2 (HarmonyOS PC / OHOS).

libcryptui — Seahorse（GNOME 密码与密钥）的密钥选择/加密 UI 库（GTK3）。
构建系统：autotools（configure + make）。
产物：lib/libcryptui.so（SONAME libcryptui.so.0）、lib/pkgconfig/cryptui-0.0.pc、
include/libcryptui/*.h、share/glib-2.0/schemas/org.gnome.seahorse.recipients.gschema.xml。

OHOS 适配要点：
- config.guess/config.sub 补丁：识别 *:HarmonyOS:* → ${MACHINE}-unknown-linux-ohos（E007/E160）。
- configure 补丁：豁免 intltool（Perl XML::Parser，HMDFS 上不可加载）与 gettext
  外部工具硬闸；ac_pwd 回退（`pwd` 在 HMDFS 上可能失败）；SM/ICE 由硬依赖降级。
- Makefile.am/Makefile.in 子目录裁剪：SUBDIRS 只保留 libcryptui（库本体）与
  data（gsettings schema）。daemon/（需 gnome-keyring + gpgme + MIME 数据库）、
  libegg/（需 libSM/libICE）、reference/（gtk-doc）、po/（intltool）、pixmaps/ 不参与构建。
- 库本体只依赖 gtk+-3.0 与 dbus-glib-1（cryptui.pc.in 的 Requires），
  gnome-keyring/gpgme 仅 daemon/ 使用，已随子目录裁剪移除。
- 公共头 cryptui.h 强制消费者定义 LIBCRYPTUI_API_SUBJECT_TO_CHANGE（否则 #error），
  已在 package_info 的 cpp_info.defines 中提供给下游。
"""
import glob
import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import (apply_conandata_patches, copy,
                               export_conandata_patches, get)
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LibcryptuiConan(ConanFile):
    name = "libcryptui"
    version = "3.12.2"
    description = "Seahorse key selection and encryption UI library for GTK3"
    license = "LGPL-2.1-or-later"
    homepage = "https://wiki.gnome.org/Apps/Seahorse"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    # GTK3 栈（gtk/3.24.43、dbus-glib/0.114.1）只发布 shared 二进制；公共头
    # cryptui-key-store.h 直接暴露 GtkTreeModelSort，静态库会把整条 GTK3
    # 依赖透传给消费者，故默认 shared（gtkspell3/gtksourceview3 同款决策）。
    default_options = {"shared": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # 依赖链版本冲突（本地 graph 实测）：gtk/3.24.43 精确 pin glib/2.84.0.1，
        # 而 dbus-glib/0.114 要求 glib/2.88.0 →
        # "ERROR: Version conflict: Conflict between glib/2.88.0 and glib/2.84.0.1"。
        # 同源还有 expat（dbus/1.14.10 侧 2.8.2 vs GTK3 链 2.8.2.1）与
        # zlib（dbus-glib 侧 1.3.1 vs GTK3 链 1.3.1.1）。
        #
        # 三处分叉改由依赖侧对齐解决：dbus-glib/0.114.1 自身 pin
        # glib/2.84.0.1、以 override 声明 expat/2.8.2.1、不再显式 require zlib。
        # 消费者侧不再写 override —— 那会把 dbus-glib 的 package_id 从已发布
        # 值改掉，而 CI 只构建包本体（--build="${pkg_name}/*"）不重建依赖，
        # 结果就是「依赖二进制缺失」红灯（dbus-glib/0.114.1 一并交付）。
        # expat 分叉：dbus/1.14.10（dbus-glib 的传递依赖）精确 pin expat/2.8.2，
        # 而 GTK3 链用 expat/2.8.2.1 →
        # "ERROR: Version conflict: Conflict between expat/2.8.2 and expat/2.8.2.1"。
        # 依赖侧 dbus-glib/0.114.1 的已发布二进制不可回改，故在消费侧以
        # override 统一到 2.8.2.1（actiona/3.11.1 同款做法）。两版本
        # major.minor.patch 相同（2.8.2，差别仅为适配后缀），Conan 默认
        # requires 的 package_id 模式为 semver_mode，故不改变 dbus-glib/dbus
        # 的 package_id，制品仓已发布二进制仍可复用。
        self.requires("expat/2.8.2.1", override=True)
        # 统一依赖图为 dbus/1.14.10.1（带 dbus-run-session/dbus-daemon 工具；
        # 1.14.10 配方跳过 tools 构建）。1.14.10.1 仅依赖 expat/2.8.2.1（无 glib），
        # ohpcd 已发布 OHOS aarch64 二进制（requires expat/2.8.Z，与本图匹配，
        # 无需重编）；上游用例（cryptui-test keyset 模式）运行期需要 session bus。
        self.requires("dbus/1.14.10.1", override=True)
        self.requires("gtk/3.24.43", transitive_headers=True, transitive_libs=True)
        self.requires("dbus-glib/0.114.1",
                      transitive_headers=True, transitive_libs=True)

    def layout(self):
        basic_layout(self)

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libcryptui requires Linux or OHOS, got {self.settings.os}")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        PkgConfigDeps(self).generate()
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(self._configure_args())
        # cmd-pkgs 的 gtk/cairo-gobject 等 .so 含未解析的传递依赖符号
        # （g_libintl_*/ffi_type_*/pcre2_*），链接期需允许（gtkspell3 同款）。
        tc.extra_ldflags.append("-Wl,--allow-shlib-undefined")
        tc.generate()
        # 交叉编译分支的 GLIB_GSETTINGS 宏用 AC_PATH_PROG 在 PATH 里找
        # glib-compile-schemas，找不到即 as_fn_error 硬失败
        # （实测 `configure: error: glib-compile-schemas not found.`）；
        # 依赖包 bin/ 不在该 PATH 上，故先把工具拷+签到构建目录再前置 PATH。
        self._stage_build_tools()
        self._pin_build_env()

    def build(self):
        apply_conandata_patches(self)
        self._pin_generated_marshallers()
        self._fix_dependency_la_metadata()
        env = self._build_environment()
        with env.vars(self).apply():
            autotools = Autotools(self)
            autotools.configure()
            # E074: HMDFS 上 jobserver fifo 不可用 → -j1
            autotools.make(args=["-j1"])

    def package(self):
        env = self._build_environment()
        with env.vars(self).apply():
            autotools = Autotools(self)
            autotools.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)
        # libtool 归档 .la 不进包：其 libdir 指向 conan 缓存绝对路径，
        # 会污染下游链接（E236，gsv3/dbus-glib 同款）。
        for root, _, files in os.walk(os.path.join(self.package_folder, "lib")):
            for name in files:
                if name.endswith(".la"):
                    os.unlink(os.path.join(root, name))
        # 上游唯一测试用例二进制一并交付（rule4：上游测试必须真实执行）：
        # libtool noinst_PROGRAMS 落在构建树 libcryptui/tests/cryptui-test，
        # 安装期不会安装，这里显式收入包内 tools/ 并签名，供消费者在
        # dbus-run-session + broadwayd（GDK_BACKEND=broadway）下以 keyset
        # 模式（无 UI 对话框路径）真实执行。
        # libtool 布局：构建树 tests/ 下是 shell 包装脚本，真 ELF 在
        # .libs/cryptui-test——glob 的 ** 不匹配点前缀隐藏目录（.libs），
        # 必须用 os.walk 按 ELF 魔数筛出真二进制。
        test_bins = []
        for root, _dirs, files in os.walk(self.build_folder):
            if "cryptui-test" in files:
                path = os.path.join(root, "cryptui-test")
                with open(path, "rb") as handle:
                    if handle.read(4) == b"\x7fELF":
                        test_bins.append(path)
        if test_bins:
            copy(self, "cryptui-test", os.path.dirname(sorted(test_bins)[0]),
                 os.path.join(self.package_folder, "tools"))
        self._compile_gsettings_schema()
        if str(self.settings.os) == "OHOS":
            self._sign_installed_elfs()
            tools_dir = os.path.join(self.package_folder, "tools")
            if os.path.isdir(tools_dir):
                self._sign_elf(os.path.join(tools_dir, "cryptui-test"))

    def package_info(self):
        self.cpp_info.libs = ["cryptui"]
        self.cpp_info.libdirs = ["lib"]
        # 上游 incdir = $(includedir)/libcryptui，cryptui-0.0.pc 的 Cflags 即
        # -I${includedir}/libcryptui；同时放出 include 便于 <libcryptui/xxx.h>
        # 形式的包含（gsv3 同款双目录）。
        incs = [d for d in ("include/libcryptui", "include")
                if os.path.isdir(os.path.join(self.package_folder, d))]
        self.cpp_info.includedirs = incs or ["include"]
        # cryptui.h 用 #error 强制声明 API 稳定性认知，必须替消费者定义
        self.cpp_info.defines = ["LIBCRYPTUI_API_SUBJECT_TO_CHANGE"]
        # 安装产物：lib/pkgconfig/cryptui-0.0.pc（LIBCRYPTUI_MAJOR=0）
        self.cpp_info.set_property("pkg_config_name", "cryptui-0.0")

    # ------------------------------------------------------------------
    # 构建配置
    # ------------------------------------------------------------------

    def _configure_args(self):
        args = []
        if self.options.shared:
            args += ["--enable-shared", "--disable-static"]
        else:
            args += ["--enable-static", "--disable-shared"]
        args += [
            # po/ 已从 SUBDIRS 裁剪；intltool 需 Perl XML::Parser（HMDFS 不可用）
            "--disable-nls",
            # gtk-doc / gobject-introspection 交叉工具链在 OHOS 不可用
            "--disable-gtk-doc",
            "--disable-introspection",
            # /usr/share 不存在：mime 数据库由平台提供，安装期不调用外部工具
            "--disable-update-mime-database",
            # 安装期 glib-compile-schemas 由本配方在 package() 内自行调用（见
            # _compile_gsettings_schema），不依赖 configure 钩子
            "--disable-schemas-compile",
            # daemon/ 已裁剪：GPG 校验与桌面通知与库本体无关
            "--disable-gpg-check",
            "--disable-libnotify",
        ]
        return args

    def _build_environment(self):
        """构建期环境（在 build()/package() 内以 env.vars(self).apply() 生效）。"""
        env = Environment()
        # E002: /tmp 只读（HMDFS）→ 构建目录内 tmp（E011 config.status 亦依赖）
        tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp, exist_ok=True)
        env.define_path("TMPDIR", tmp)
        env.define_path("TMP", tmp)
        env.define_path("TEMP", tmp)
        # configure 期工具（glib-compile-schemas）优先于依赖包 bin/
        tools = os.path.join(self.build_folder, "conan-native-tools")
        if os.path.isdir(tools):
            env.prepend_path("PATH", tools)
        for dep in self.dependencies.host.values():
            bindir = os.path.join(dep.package_folder, "bin")
            if os.path.isdir(bindir):
                env.prepend_path("PATH", bindir)  # glib-genmarshal 等构建期工具
            for libdir in dep.cpp_info.libdirs:
                if not os.path.isabs(libdir):
                    libdir = os.path.join(dep.package_folder, libdir)
                if os.path.isdir(libdir):
                    env.prepend_path("LD_LIBRARY_PATH", libdir)
        if str(self.settings.os) == "OHOS":
            for pattern in ("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib",
                            "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib/aarch64-linux-ohos"):
                matches = sorted(glob.glob(pattern))
                if matches:
                    # SDK lld 运行期需要 ABI 匹配的 libxml2.so.16；libc++_shared.so 供 harfbuzz 等
                    env.prepend_path("LD_LIBRARY_PATH", matches[-1])
        return env

    def _pin_build_env(self):
        """把构建环境固化进 conanbuild.sh（conanbuildenv-*.sh）。

        只在 os.environ 里临时改 PATH/LD_LIBRARY_PATH 会被 conan 生成构建脚本时
        丢弃（gtksourceview3/4 同款教训），故经 buildenv_info 落盘。
        """
        tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp, exist_ok=True)
        self.buildenv_info.define_path("TMPDIR", tmp)
        tools = os.path.join(self.build_folder, "conan-native-tools")
        if os.path.isdir(tools):
            self.buildenv_info.prepend_path("PATH", tools)
        for dep in self.dependencies.host.values():
            bindir = os.path.join(dep.package_folder, "bin")
            if os.path.isdir(bindir):
                self.buildenv_info.prepend_path("PATH", bindir)
        if str(self.settings.os) == "OHOS":
            for pattern in ("/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib",
                            "/data/service/hnp/ohos-sdk.org/*/ohos/native/llvm/lib/aarch64-linux-ohos"):
                matches = sorted(glob.glob(pattern))
                if matches:
                    self.buildenv_info.prepend_path("LD_LIBRARY_PATH", matches[-1])

    def _stage_build_tools(self):
        """把 glib 依赖内的构建期 ELF 工具拷进构建目录（并按需重签）。

        glib 包的 bin/ 未进入构建期 PATH，而 configure 的 GLIB_GSETTINGS 宏在
        交叉编译分支用 AC_PATH_PROG 查找 glib-compile-schemas，缺失即
        as_fn_error（`configure: error: glib-compile-schemas not found.`）硬失败；
        缓存包内的未签名 aarch64 ELF 也无法直接 exec（XPM 拒绝）。
        """
        staged = [self._stage_glib_tool(name)
                  for name in ("glib-compile-schemas",)]
        staged = [path for path in staged if path]
        if not staged:
            self.output.warning(
                "no glib build tool staged (glib-compile-schemas missing in glib dep)")
            return None
        self.output.info("staged glib build tools: %s" % ", ".join(
            os.path.basename(path) for path in staged))
        return os.path.dirname(staged[0])

    def _fix_dependency_la_metadata(self):
        """修正依赖包 .la 里的 `libdir='//lib'`（E236）。

        conan 依赖以 --prefix=/ 构建，.la 的 libdir 落成 '//lib'，dependency_libs
        里也残留 '//lib/lib*.la'；libtool 链接本库时按该 libdir 读依赖 .la，报
        `grep: //lib/libpcre2-8.la: No such file` /
        `'//lib/libpcre2-8.la' is not a valid libtool archive`（实测由
        glib→pcre2 链触发，freetype/libpng/fribidi 同为 'was moved'）。
        就地改写为真实 lib 路径（libgsf 1.14.5 先例），不动依赖配方本体。
        """
        fixed = []
        for dep in self.dependencies.host.values():
            libdir = os.path.join(dep.package_folder, "lib")
            if not os.path.isdir(libdir):
                continue
            for name in sorted(os.listdir(libdir)):
                if not name.endswith(".la"):
                    continue
                path = os.path.join(libdir, name)
                if not os.path.isfile(path) or os.path.islink(path):
                    continue
                with open(path, "r", encoding="utf-8",
                          errors="surrogateescape") as handle:
                    text = handle.read()
                patched = text.replace("libdir='//lib'",
                                       "libdir='%s'" % libdir)
                patched = patched.replace("//lib/", "%s/" % libdir)
                if patched == text:
                    continue
                if not os.access(path, os.W_OK):
                    try:
                        os.chmod(path, 0o644)
                    except OSError:
                        pass
                with open(path, "w", encoding="utf-8",
                          errors="surrogateescape") as handle:
                    handle.write(patched)
                fixed.append("%s/%s" % (dep.ref.name, name))
        if fixed:
            self.output.info("patched dependency .la metadata: %s"
                             % ", ".join(fixed))

    def _pin_generated_marshallers(self):
        """保持 cryptui-marshal.c/.h 的新鲜度，避免构建期调用 glib-genmarshal。

        tarball 内 marshal 产物（2014-04-11）本比 cryptui-marshal.list（2011-07-22）
        新，make 不会重新生成；但解包/复制可能重置 mtime，一旦触发
        `$(GLIB_GENMARSHAL) $< --header ...`，就会依赖 conan 包内未签名的
        ELF 工具（OHOS 上直接 exec 被 XPM 拒绝）。显式触摸产物保证 Up-to-date。
        """
        libdir = os.path.join(self.source_folder, "libcryptui")
        for name in ("cryptui-marshal.c", "cryptui-marshal.h"):
            path = os.path.join(libdir, name)
            if os.path.isfile(path):
                os.utime(path, None)
        self.output.info("cryptui-marshal.c/.h touched (avoid glib-genmarshal rebuild)")

    # ------------------------------------------------------------------
    # 安装后处理
    # ------------------------------------------------------------------

    def _compile_gsettings_schema(self):
        """best-effort 编译已安装的 gschema（configure 已 --disable-schemas-compile）。

        OHOS 上 glib-compile-schemas 是 conan 包内的未签名 aarch64 ELF，直接从
        缓存路径 exec 会被 XPM 拒绝；这里拷贝到构建目录、按需重签后执行。
        失败不阻塞打包（消费者可自行编译或使用未编译 XML），仅告警。
        """
        schema_dir = os.path.join(self.package_folder, "share", "glib-2.0", "schemas")
        if not os.path.isdir(schema_dir) or not glob.glob(
                os.path.join(schema_dir, "*.gschema.xml")):
            return
        tool = self._stage_glib_tool("glib-compile-schemas")
        if not tool:
            self.output.warning(
                "glib-compile-schemas not found in glib dependency; "
                "gschemas.compiled not generated (schema XML still installed)")
            return
        try:
            subprocess.run([tool, schema_dir], check=True, capture_output=True, text=True)
            self.output.info("gschemas.compiled generated (org.gnome.seahorse.recipients)")
        except (OSError, subprocess.CalledProcessError) as exc:
            self.output.warning(f"glib-compile-schemas failed ({exc}); "
                                "keeping uncompiled schema XML")

    def _stage_glib_tool(self, tool):
        """从 glib 依赖包拷贝构建期 ELF 工具到构建目录并按需重签。"""
        glib_pkg = None
        for dep in self.dependencies.host.values():
            if dep.ref.name == "glib":
                glib_pkg = dep
                break
        if glib_pkg is None:
            return None
        src = os.path.join(glib_pkg.package_folder, "bin", tool)
        if not os.path.isfile(src):
            return None
        tools = os.path.join(self.build_folder, "conan-native-tools")
        os.makedirs(tools, exist_ok=True)
        dst = os.path.join(tools, tool)
        shutil.copyfile(src, dst)
        os.chmod(dst, 0o755)
        if str(self.settings.os) == "OHOS":
            self._sign_elf(dst)
        return dst

    def _sign_installed_elfs(self):
        libdir = os.path.join(self.package_folder, "lib")
        if not os.path.isdir(libdir):
            return
        for name in os.listdir(libdir):
            if ".so" not in name:
                continue
            path = os.path.join(libdir, name)
            if os.path.islink(path) or not os.path.isfile(path):
                continue
            with open(path, "rb") as handle:
                if handle.read(4) != b"\x7fELF":
                    continue
            self._sign_elf(path)

    def _sign_elf(self, binary):
        """OHOS 自签名（未签名 ELF 在 HMDFS/XPM 下无法加载/执行）。"""
        signer = "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            self.output.warning(f"HarmonyOS signer missing: {signer} (skip signing)")
            return
        # signer 自身依赖系统 libc++，需在剥离 conan 环境的干净子进程中执行
        clean_env = {
            "PATH": "/data/service/hnp/bin:/system/bin:/usr/bin:/bin",
            "HOME": os.environ.get("HOME", "/data/storage/el2/base"),
            "LD_LIBRARY_PATH": "",
            "TMPDIR": os.environ.get("TMPDIR", "/data/storage/el2/base/temp"),
        }
        result = subprocess.run(
            [signer, "sign", "-inFile", binary, "-outFile", binary, "-selfSign", "1"],
            env=clean_env, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            raise ConanInvalidConfiguration(
                f"binary-sign-tool failed for {binary}: "
                f"{result.stdout[-500:]} {result.stderr[-500:]}")
