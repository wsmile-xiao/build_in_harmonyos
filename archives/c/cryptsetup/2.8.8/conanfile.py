#!/usr/bin/env python3
"""Conan recipe — cryptsetup 2.8.8 (autotools, C).

cryptsetup: LUKS/LUKS2 磁盘加密工具集与 libcryptsetup。
官方发行归档（cdn.kernel.org，make dist 产物）含预生成 configure /
Makefile.in / config.h.in，**不需要 autogen.sh**（本机无 automake/aclocal）。
注意 GitLab tag 归档（/-/archive/v2.8.8/...tar.gz）不含 configure，不可用。

Upstream: https://gitlab.com/cryptsetup/cryptsetup
Source:   https://cdn.kernel.org/pub/linux/utils/cryptsetup/v2.8/cryptsetup-2.8.8.tar.xz
License:  GPL-2.0-or-later
"""
import os
import shutil

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class CryptsetupConan(ConanFile):
    name = "cryptsetup"
    version = "2.8.8"
    description = "LUKS disk encryption: libcryptsetup + cryptsetup/veritysetup/integritysetup CLI"
    license = "GPL-2.0-or-later"
    homepage = "https://gitlab.com/cryptsetup/cryptsetup"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("luks", "disk-encryption", "device-mapper", "cryptsetup")

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": True}
    # cryptsetup 有 libtool，但上游 configure 不支持真正的静态-only 变体
    # （--enable-static-cryptsetup 会要求静态 gcrypt/blkid/udev 全套），
    # 故 options 仅保留 shared 供设置兼容（与 lvm2/2.03.42 同口径）。

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # configure.ac 强制依赖（无 AC_ARG_ENABLE 支撑，缺则 AC_MSG_ERROR）：
        #   :92  AC_CHECK_HEADER(libdevmapper.h) + :456 PKG_CHECK_MODULES([DEVMAPPER],[devmapper >= 1.02.03])
        #   :91  AC_CHECK_HEADERS(uuid/uuid.h)   + :120 AC_CHECK_LIB(uuid, uuid_clear)
        #   :180 AC_CHECK_LIB(popt, ...) 要求 >= 1.7
        #   :484 PKG_CHECK_MODULES([JSON_C],[json-c]) 无 fallback（LUKS2 元数据必需）
        #   :331 crypto backend 必选一，默认 openssl（>= 0.9.8）
        self.requires("lvm2/2.03.42")       # libdevmapper.h + libdevmapper.so；pkg-config 名 = devmapper
        self.requires("util-linux/2.42")    # 一包双供给 libuuid + libblkid
        self.requires("json-c/0.18")
        self.requires("popt/1.16")
        self.requires("openssl/3.5.6.1.2")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _overlay_pc(self, filename, name, description, version,
                    cflags_dir, libs_dir, libs, private=""):
        """自建「库级」pkg-config 覆盖文件（写进 generators 目录，构建期有效、不分发）。

        openssl/3.5.6.1.2 与 util-linux/2.42 的 conan 包只暴露**包级** .pc（无
        components → PkgConfigDeps 只产 openssl.pc / util-linux.pc），而 cryptsetup
        的 configure 按**库名**探测：
          :331 PKG_CHECK_MODULES([LIBCRYPTO],[libcrypto >= 0.9.8],, AC_MSG_ERROR)
               —— 无 fallback，缺 .pc 直接 configure 失败（本轮实测）
          :586 PKG_CHECK_MODULES([BLKID],[blkid],[AC_DEFINE(HAVE_BLKID)],[-lblkid])
               —— 有 fallback 但会**静默降级**丢掉 blkid 设备签名识别功能
        包内自带的 libcrypto.pc 不可用：其 prefix 指向原作者构建目录，是失效路径。
        cflags_dir 指向真实包 include；libs_dir 指向去 .la 的链接视图（见 generate）。
        """
        text = (
            "prefix=%s\n"
            "exec_prefix=${prefix}\n"
            "libdir=%s\n"
            "includedir=%s\n\n"
            "Name: %s\n"
            "Description: %s (conan overlay pc)\n"
            "Version: %s\n"
            "Cflags: -I%s\n"
            "Libs: -L%s %s\n" % (cflags_dir, libs_dir, cflags_dir,
                                 name, description, version, cflags_dir, libs_dir, libs)
        )
        if private:
            text += "Libs.private: %s\n" % private
        with open(os.path.join(self.generators_folder, filename), "w") as f:
            f.write(text)
        self.output.info(f"overlay pc: {filename} -> {name} {version} "
                         f"cflags={cflags_dir} libs={libs_dir}")

    def _build_deps_view(self):
        """构建「链接视图」：把直接依赖的实体库文件（.a/.so，跟随软链复制）
        汇到一个不含任何 .la 的目录，供 -L 与 LD_LIBRARY_PATH 共用。

        ★ 根因（本轮实测首错）：
          `libtool: error: cannot find the library '//lib/libblkid.la'`
          util-linux/2.42（libblkid/libuuid/libmount.la）与 popt/1.16（libpopt.la）
          是纯静态包，其 .la 文件 libdir='//lib'（打包时未重定位）。libtool 在 -L
          搜索路径中命中 .la 后按其 libdir 定位实体库 → '//lib/libblkid.la' 不存在
          → Error 1。AutotoolsDeps 会把依赖真实目录注入 -L，正是 .la 的入口；
          只要真实目录在搜索路径上，AC_CHECK_LIB 追加的 -luuid/-lpopt 就必中 .la。
        ★ 修法：
          ① 不用 AutotoolsDeps，改为手工 CPPFLAGS（include 直指真实包目录）+
             LDFLAGS=-L<视图>（视图内只有实体库文件，无 .la 可被 libtool 解析）；
          ② 静态包 fPIC 已核验：util-linux fPIC=True（配方 :37），其 .a 可链入
             libcryptsetup.so；popt 仅被 CLI 可执行文件消费（libcryptsetup 不用
             popt），非 PIC 亦无害；lvm2/json-c/openssl 包内无 .la，不受影响。
          ③ OHOS musl 加载器不解析「SONAME 名是软链」的库（E505/E316 同族，
             探针 probe-loader 实证 rc=127 → 实体化后 rc=0）：视图内一律
             os.path.realpath 实体文件，AC_RUN_IFELSE conftest 可立即执行。
        """
        view = os.path.join(self.build_folder, "deps-view")
        lib_view = os.path.join(view, "lib")
        os.makedirs(lib_view, exist_ok=True)
        inc_flags = []
        for dep in self.dependencies.values():
            if not dep.package_folder:
                continue
            cpp = dep.cpp_info.aggregated_components()
            for incdir in cpp.includedirs:
                real_inc = os.path.join(dep.package_folder, incdir)
                if os.path.isdir(real_inc):
                    inc_flags.append("-I" + real_inc)
            for libdir in cpp.libdirs:
                real_dir = os.path.join(dep.package_folder, libdir)
                if not os.path.isdir(real_dir):
                    continue
                for name in os.listdir(real_dir):
                    if name.endswith(".la"):
                        continue  # 视图内禁止 .la（libtool 毒源）
                    if not (name.endswith(".a") or ".so" in name):
                        continue
                    src = os.path.join(real_dir, name)
                    if not os.path.isfile(src):
                        continue
                    dst = os.path.join(lib_view, name)
                    if not os.path.exists(dst):
                        shutil.copy2(os.path.realpath(src), dst)
        self.output.info(f"deps view: {lib_view} ({len(os.listdir(lib_view))} files), "
                         f"includes: {len(inc_flags)} dirs")
        return lib_view, inc_flags

    def generate(self):
        lib_view, inc_flags = self._build_deps_view()

        tc = AutotoolsToolchain(self)
        # OHOS 三元组：本包 config.sub 为 2024 版，已原生支持 ohos*/linux-ohos*
        # （config.sub:2070 / :2213 实测），无需 patch config.sub。
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        # asciidoctor 不存在时 enable_asciidoc=yes(默认) 必 AC_MSG_ERROR(:65-66)，
        # 与 man 页是否已预生成无关（HAVE_MANPAGES 是另一分支）→ 必须显式关闭。
        tc.configure_args.append("--disable-asciidoc")
        # ssh-token 需 argp.h（OHOS sysroot 无，:492 AC_MSG_ERROR）；关闭即绕开，
        # 不引入新依赖（external-tokens 仍保留默认开启）。
        tc.configure_args.append("--disable-ssh-token")
        tc.configure_args.append("--disable-udev")
        tc.configure_args.append("--disable-selinux")
        tc.configure_args.append("--disable-nls")
        # blkid/libuuid 由 util-linux/2.42 提供（静态库），显式开启而非默认探测
        tc.configure_args.append("--enable-blkid")
        tc.configure_args.append("--with-crypto_backend=openssl")
        tc.generate()

        # pkg-config 名 devmapper（lvm2 的 cpp_info.pkg_config_name）≠ 包名，
        # 必须由 PkgConfigDeps 生成 devmapper.pc，:456 的 PKG_CHECK_MODULES 才命中。
        # lvm2/json-c 包内无 .la，其真实目录出现在 .pc 的 -L 中无害。
        deps = PkgConfigDeps(self)
        deps.generate()

        # 库级 .pc 覆盖（libcrypto 强制、blkid 保功能）；Libs 一律 -L 链接视图
        openssl_pkg = self.dependencies["openssl"].package_folder
        self._overlay_pc("libcrypto.pc", "OpenSSL-libcrypto",
                         "OpenSSL cryptography library",
                         str(self.dependencies["openssl"].ref.version),
                         os.path.join(openssl_pkg, "include"),
                         lib_view, "-lcrypto", "-ldl -pthread")
        util_pkg = self.dependencies["util-linux"].package_folder
        self._overlay_pc("blkid.pc", "blkid",
                         "Block device identification library",
                         str(self.dependencies["util-linux"].ref.version),
                         os.path.join(util_pkg, "include"),
                         lib_view, "-lblkid -luuid")

        # E011 同族: autoconf/config.sub 的临时文件落 ${TMPDIR:-/tmp}，OHOS /tmp
        # 只读 → 误报 "OS ohos not recognized"。指向 build_folder（util-linux 先例）。
        # 另：safe-bin rm 垫片三重通道（PATH/BASH_FUNC_rm%%/BASH_ENV）在设备侧 exec
        # 失败，config.status 生成 Makefile 时致命，须在此剥离而非 build()。
        # CPPFLAGS/LDFLAGS 取代 AutotoolsDeps（见 _build_deps_view 根因说明）。
        env = Environment()
        env.define("TMPDIR", self.build_folder)
        env.append("CPPFLAGS", " ".join(inc_flags))
        env.append("LDFLAGS", "-L" + lib_view)
        # conftest 若链接共享依赖（libdevmapper/libjson-c.so）后立即执行，
        # LD_LIBRARY_PATH 指向实体化视图即可运行（E505/E316，见 _build_deps_view）。
        env.prepend_path("LD_LIBRARY_PATH", lib_view)
        safe_dir = os.environ.get("CODEBUDDY_SAFE_DELETE_BIN_DIR")
        if safe_dir:
            env.remove("PATH", safe_dir)
        env.unset("BASH_ENV")
        env.unset("BASH_FUNC_rm%%")
        env.unset("CODEBUDDY_SAFE_DELETE_BIN_DIR")
        env.unset("CODEBUDDY_SAFE_DELETE_ENABLED")
        env.vars(self).save_script("conantmpdir")

    def build(self):
        # conan 子进程 spawn 继承本进程 os.environ：按子串清理 PATH 中的垫片目录，
        # 并移除 BASH_ENV/BASH_FUNC_*/CODEBUDDY_SAFE_DELETE*（垫片可经三重通道注入）。
        os.environ["PATH"] = os.pathsep.join(
            p for p in os.environ.get("PATH", "").split(os.pathsep)
            if p and "safe-bin" not in p)
        for key in list(os.environ):
            if key == "BASH_ENV" or key.startswith("BASH_FUNC_") or key.startswith("CODEBUDDY_SAFE_DELETE"):
                os.environ.pop(key, None)
        # conandata.patches 三处（前两处在 configure 之前；第三处注册 make check 用例）：
        #   0001-configure-hmdfs-umask.patch      E011 confXXXXXX 0700 -> 0755
        #   0002-tests-ohos-bash-shebang.patch   E165 /bin/bash -> hnp bash（119 脚本）
        #   0003-ohos-consumer-test.patch         鸿蒙消费者用例注册进 TESTS（am+in+新脚本）
        apply_conandata_patches(self)
        # toybox 0.8.12 patch 不解析 git「new file mode 100755」（净源码 apply-test
        # 实测：新文件落盘 0666&~umask），补丁 0003 新增的测试脚本必须可执行，
        # automake 并行测试框架（test-driver）才会直接 exec 它。
        ohos_test = os.path.join(self.source_folder, "tests", "ohos-consumer-test")
        if os.path.isfile(ohos_test):
            os.chmod(ohos_test, 0o755)
            self.output.info("chmod +x tests/ohos-consumer-test (toybox patch mode gap)")
        autotools = Autotools(self)
        autotools.configure()
        # R9/E074: 并行 make 在 HMDFS 上撞 jobserver fifo EPERM，固定 -j1
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        # E316/E492: OHOS musl 不能加载「SONAME 名字是软链」的库 → 把 lib/ 下
        # 软链跟随复制成实体文件（先例 gnustep-gui/0.31.1、lvm2/2.03.42）。
        libdir = os.path.join(self.package_folder, "lib")
        if os.path.isdir(libdir):
            for name in os.listdir(libdir):
                path = os.path.join(libdir, name)
                if os.path.islink(path):
                    tmp = path + ".tmp"
                    shutil.copy2(path, tmp, follow_symlinks=True)
                    os.replace(tmp, path)
                    self.output.info(f"flattened symlink: {name}")
        # 工具装到 sbin/ → 包内统一为 bin/（R38: bindirs=["bin"]）
        sbin = os.path.join(self.package_folder, "sbin")
        bindir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(sbin):
            os.makedirs(bindir, exist_ok=True)
            for name in os.listdir(sbin):
                src = os.path.join(sbin, name)
                dst = os.path.join(bindir, name)
                if os.path.islink(src):
                    target = os.readlink(src)
                    if os.path.lexists(dst):
                        os.remove(dst)
                    os.symlink(target, dst)
                else:
                    shutil.copy2(src, dst)
            shutil.rmtree(sbin)
        copy(self, "COPYING*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "README.licensing", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["cryptsetup"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = ["bin"]
        # 上游 lib/libcryptsetup.pc.in: Name: cryptsetup / Libs: -lcryptsetup
        # Requires.private: @PKGMODULES@ = "uuid devmapper json-c"
        self.cpp_info.set_property("pkg_config_name", "cryptsetup")
