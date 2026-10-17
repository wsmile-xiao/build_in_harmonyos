#!/usr/bin/env python3
"""Conan recipe for libsmartcols 2.42.3 on HarmonyOS PC.

libsmartcols is the table output library from util-linux. This recipe
builds ONLY the libsmartcols subdirectory from the util-linux 2.42.3
source tree (same source-extraction approach as the other util-linux
sub-libraries: util-linux/2.42 builds libblkid/libuuid/libmount;
util-linux-login/2.42.2 builds login only).

Build shape: configure the full util-linux tree with
--disable-all-programs + --enable-libsmartcols (+ --enable-libuuid for
the configure-time dependency resolution), build the libsmartcols.la
target, package only libsmartcols headers/libs.
"""
import os
import glob
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibsmartcolsConan(ConanFile):
    name = "libsmartcols"
    version = "2.42.3"
    description = ("Table output library from util-linux "
                   "(libsmartcols — structured table rendering)")
    license = "LGPL-2.1-or-later"
    homepage = "https://kernel.org/pub/linux/utils/util-linux/"
    url = "https://git.kernel.org/pub/scm/utils/util-linux/util-linux.git"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def requirements(self):
        # 任务指定的前置：libuuid/2.40.4（制品仓已发布 ✅）。
        # libsmartcols 源码本身不直接调用 uuid API（内部依赖 libcommon），
        # 但 util-linux configure 树的库模块链按惯例保留 uuid 前置
        # （下游 lsblk/uuidparse 等消费方需要 cols+uuid 组合）。
        self.requires("libuuid/2.40.4")

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "libsmartcols requires a Linux-compatible environment")

    def source(self):
        data = self.conan_data["sources"][self.version]
        primary = data["url"]
        mirrors = [
            "https://mirrors.edge.kernel.org/pub/linux/utils/util-linux/v2.42/util-linux-2.42.3.tar.xz",
            "https://www.kernel.org/pub/linux/utils/util-linux/v2.42/util-linux-2.42.3.tar.xz",
        ]
        for url in [primary] + mirrors:
            try:
                get(self, url, sha256=data["sha256"], strip_root=True)
                return
            except Exception as e:
                self.output.warning(f"source download failed from {url}: {e}")

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.append("--host=aarch64-unknown-linux-ohos")
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        # 沿用 util-linux/2.42 已合入配方同款裁剪：只编库，禁所有工具
        tc.configure_args.append("--disable-all-programs")
        tc.configure_args.append("--enable-libsmartcols")
        # libuuid 同树构建（configure 依赖解析需要；不打包其产物）
        tc.configure_args.append("--enable-libuuid")
        # 关闭无关可选依赖（与 util-linux/2.42 同款）
        tc.configure_args.append("--disable-pam")
        tc.configure_args.append("--disable-libudev")
        tc.configure_args.append("--disable-liblastlog2")
        tc.configure_args.append("--disable-libmount")
        tc.configure_args.append("--disable-libblkid")
        tc.configure_args.append("--disable-libfdisk")
        tc.configure_args.append("--without-systemd")
        tc.configure_args.append("--without-python")
        tc.configure_args.append("--without-btrfs")
        tc.configure_args.append("--disable-nls")
        tc.generate()
        # autoconf $ac_tmp 落 /tmp（OHOS 只读）→ build_folder（util-linux/2.42 同款）
        env = Environment()
        env.define("TMPDIR", self.build_folder)
        envvars = env.vars(self)
        envvars.save_script("conantmpdir")

    def build(self):
        apply_conandata_patches(self)
        self._patch_ohos_platform()
        self._patch_memstream_flush()
        # 清理前次失败残留的 conf* 临时目录（umask 077 建 700 权限写不进）
        for stale in glob.glob(os.path.join(self.build_folder, "conf*")):
            if os.path.isdir(stale):
                shutil.rmtree(stale, ignore_errors=True)
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j4"])

    def _patch_memstream_flush(self):
        """OHOS libc open_memstream 时序差异修复（实测定位）：
        scols_print_table_to_string() 内部 open_memstream → do_print_table
        → fclose——glibc 语义下 fclose 后 *data 保证指向完整输出；
        OHOS musl 实测：do_print_table 的写入在无显式 fflush 时不会
        出现在最终 buffer（*data 空串），且部分路径进程退出时
        Illegal instruction（min3 复现：print rc=0 data=[] + 退出崩；
        min7 复刻：加 fflush(stream) 后 data 完整且干净退出——
        scols_print_table 直接写 stdout 则完全正常）。
        修法：fclose 前显式 fflush(stream)（glibc/musl 双兼容——
        glibc fflush+fclose 幂等无副作用）。"""
        import os as _os
        path = _os.path.join(self.source_folder,
                             "libsmartcols", "src", "print-api.c")
        if not _os.path.isfile(path):
            self.output.warning("print-api.c not found")
            return
        text = open(path, encoding="utf-8", errors="ignore").read()
        old = """\told_stream = scols_table_get_stream(tb);
\tscols_table_set_stream(tb, stream);
\trc = do_print_table(tb, NULL);
\tfclose(stream);
\tscols_table_set_stream(tb, old_stream);"""
        new = """\told_stream = scols_table_get_stream(tb);
\tscols_table_set_stream(tb, stream);
\trc = do_print_table(tb, NULL);
\tfflush(stream);  /* [ohos] musl open_memstream: flush before fclose */
\tfclose(stream);
\tscols_table_set_stream(tb, old_stream);"""
        if old in text:
            text = text.replace(old, new, 1)
            open(path, "w").write(text)
            self.output.info("patched print-api.c: fflush before fclose")
        else:
            self.output.warning("print_to_string pattern not found")

    def _patch_ohos_platform(self):
        """config.guess/config.sub OHOS 识别 + configure umask 077 修复（E011）。
        util-linux 的 config.guess/config.sub 在 config/ 子目录且为 2026 新版
        ——按 util-linux/2.42 已合入配方同款 patch。"""
        import os as _os
        cfg = _os.path.join(self.source_folder, "configure")
        if _os.path.isfile(cfg):
            ctext = open(cfg, encoding="utf-8", errors="ignore").read()
            if "umask 000" not in ctext:
                nl = ctext.find("\n")
                ctext = ctext[:nl+1] + "umask 000\n" + ctext[nl+1:]
                changed = True
            else:
                changed = False
            old_mkt = '(umask 077 && mktemp -d "./confXXXXXX")'
            if old_mkt in ctext:
                ctext = ctext.replace(old_mkt, '(umask 000 && mktemp -d "./confXXXXXX")')
                changed = True
            if changed:
                with open(cfg, "w") as f:
                    f.write(ctext)
                self.output.info("patched configure: umask 077->000 (E011 hmdfs tmp dir)")
        # util-linux 的 config.guess/config.sub 在 config/ 子目录
        for name in ("config.guess", "config.sub"):
            path = _os.path.join(self.source_folder, "config", name)
            if not _os.path.isfile(path):
                path = _os.path.join(self.source_folder, name)
            if not _os.path.isfile(path):
                continue
            text = open(path, encoding="utf-8", errors="ignore").read()
            changed = False
            if name == "config.sub":
                old1 = "| nsk* | powerunix* | genode* | zvmoe* | qnx* | emx* | zephyr* \\"
                if old1 in text and "ohos*)" not in text:
                    text = text.replace(old1, old1.replace("zephyr* \\", "zephyr* \\\n\t     | ohos* \\"), 1)
                    changed = True
                old2 = "linux-gnu*- | linux-android*- | linux-dietlibc*- | linux-llvm*- \\"
                if old2 in text and "linux-ohos*-" not in text:
                    text = text.replace(old2, old2.replace("linux-llvm*- \\", "linux-llvm*- | linux-ohos*- \\"), 1)
                    changed = True
            else:
                old3 = "    aarch64:Linux:*:*)\n\tset_cc_for_build"
                if old3 in text and "OHOS" not in text:
                    new3 = ("    aarch64:Linux:*:*)\n"
                            "\tcase `uname` in\n"
                            "\t  *OHOS*) echo $UNAME_MACHINE-unknown-linux-ohos ; exit ;;\n"
                            "\tesac\n"
                            "\tset_cc_for_build")
                    text = text.replace(old3, new3, 1)
                    changed = True
            if changed:
                with open(path, "w") as f:
                    f.write(text)
                self.output.info(f"patched {name}: OHOS platform recognition")

    def package(self):
        # 只打包 libsmartcols 本体：源码树 make install 后筛 libsmartcols 产物
        autotools = Autotools(self)
        autotools.install()
        # 删除同树构建的 libuuid 产物（本包只交付 libsmartcols——uuid 归
        # libuuid/2.40.4 包管）
        for pat in ("libuuid*", "uuid"):
            for f in glob.glob(os.path.join(self.package_folder, "lib", pat)):
                if os.path.isfile(f):
                    os.remove(f)
        for f in glob.glob(os.path.join(self.package_folder, "include", "uuid")):
            if os.path.isdir(f):
                shutil.rmtree(f)
            elif os.path.isfile(f):
                os.remove(f)
        for f in glob.glob(os.path.join(self.package_folder, "lib", "pkgconfig", "uuid.pc")):
            os.remove(f)
        # 头文件平移：util-linux 安装为 include/libsmartcols/libsmartcols.h
        # （子目录约定），Conan 消费惯例是 include 根——平移并修 .pc 文件
        inc_sub = os.path.join(self.package_folder, "include", "libsmartcols")
        inc_root = os.path.join(self.package_folder, "include")
        if os.path.isdir(inc_sub):
            for f in os.listdir(inc_sub):
                shutil.move(os.path.join(inc_sub, f),
                            os.path.join(inc_root, f))
            os.rmdir(inc_sub)
        pc = os.path.join(self.package_folder, "lib", "pkgconfig",
                          "smartcols.pc")
        if os.path.isfile(pc):
            txt = open(pc).read()
            txt = txt.replace("includedir=${prefix}/include/libsmartcols",
                              "includedir=${prefix}/include")
            open(pc, "w").write(txt)
        # libtool .la 归档文件不随包分发（ Conan 消费走 cpp_info ）
        for f in glob.glob(os.path.join(self.package_folder, "lib", "*.la")):
            os.remove(f)
        # bin/ 里可能有 uuidgen 等残留（--disable-all-programs 后一般没有）
        bdir = os.path.join(self.package_folder, "bin")
        if os.path.isdir(bdir) and not os.listdir(bdir):
            os.rmdir(bdir)
        copy(self, "COPYING", src=os.path.join(self.source_folder, "libsmartcols"),
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["smartcols"]
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []  # 只编库，无 bin
        self.cpp_info.requires = ["libuuid::libuuid"]
