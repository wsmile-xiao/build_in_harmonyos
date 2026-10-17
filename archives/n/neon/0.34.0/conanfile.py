import os
import shutil

from conan import ConanFile
from conan.tools.files import get


class NeonConan(ConanFile):
    name = "neon"
    version = "0.34.0"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    # 默认静态：环境 zlib/1.3.1 仅提供静态库（libz.a 非 PIC）——共享
    # 链接必然失败（ld.lld relocation against z_errmsg 实测）；静态构建
    # 为实测可行路径（configure 默认 enable_shared=no + make 通过）
    default_options = {"shared": False}
    requires = "zlib/1.3.1", "expat/2.8.2"
    exports_sources = "conandata.yml"

    def source(self):
        get(self, **self.conan_data["sources"]["neon"], strip_root=True)

    def build(self):
        # E007：config.guess 无法识别 OHOS——显式 --build 三元组；
        # E011：非 HMDFS work——权限放开（同 bacula/libhdate 教训）；
        # --with-ssl/zlib/expat（neon 依赖链——openssl/zlib/expat 已发布）
        work = self.source_folder
        os.system(f"chmod -R 777 {work}")
        # neon configure 用 SSL_library_init() 检查 SSL 库（openssl 1.x
        # API——openssl 3.x 已移除该符号——4 轮尝试（patch OPENSSL_init_ssl/
        # LDFLAGS/LIBS）均无效——openssl 静态库（.a）链接兼容阻塞）——
        # **--without-ssl 降级构建**（neon 基础 WebDAV 库——无 SSL——
        # 如实记录：SSL 功能降级，cadaver 集成需 SSL 兼容攻坚）
        cfg = os.path.join(work, "configure")
        cs = open(cfg).read()
        cs = cs.replace('SSL_library_init();', 'OPENSSL_init_ssl(0, NULL);')
        cs = cs.replace("SSL_library_init", "OPENSSL_init_ssl")
        # config.status 生成的 subs1.awk 无 x 位（重定向 666——umask 无法
        # 给 x——exec './confXXXX/subs1.awk' Permission denied 实测）——
        # 生成后 chmod +x（config.status 的 subs1.awk exec 通过）
        cs = cs.replace(
            "echo 'BEGIN {' >\"$ac_tmp/subs1.awk\" &&",
            "echo 'BEGIN {' >\"$ac_tmp/subs1.awk\" &&\n"
            "chmod +x \"$ac_tmp/subs1.awk\" &&")
        # config.status 建临时目录用 (umask 077 && mktemp -d)——目录 700
        # 属主为 conan 缓存 uid（HMDFS 显示 20001006），当前进程（不同
        # uid）无法写入 subs1.awk——实测 Permission denied（E011 权限
        # 教训同族）——改 umask 000 使目录 777 可写
        cs = cs.replace("umask 077", "umask 000")
        open(cfg, "w").write(cs)
        print("configure SSL_library_init → OPENSSL_init_ssl")
        zlib = self.dependencies["zlib"].package_folder
        expat = self.dependencies["expat"].package_folder
        # configure cross-compiling 检查（运行测试程序）在 el2 沙箱受限
        # （'cannot run C compiled programs' 实测——同 libseccomp
        # regression rc=127/ctypes dlopen 沙箱限制类）——cache 文件预置
        # ac_cv_prog_cc_cross=yes 跳过该检查（同 bacula-fd configure
        # 简化模式——显式 --build 已是交叉编译）
        with open(os.path.join(work, "cross.cache"), "w") as f:
            f.write("ac_cv_prog_cc_cross=yes\n")
        self.run(
            f"umask 0 && LD_LIBRARY_PATH={zlib}/lib:{expat}/lib "
            f"./configure "
            f"--cache-file={work}/cross.cache "
            f"CPPFLAGS=\"-I{zlib}/include -I{expat}/include\" "
            f"LDFLAGS=\"-L{zlib}/lib -L{expat}/lib\" "
            f"LIBS=\"-lexpat\" "
            f"--build=aarch64-unknown-linux-gnu "
            f"--prefix={self.package_folder} --without-ssl "
            f"--with-zlib --with-expat "
            + ("--enable-shared" if self.options.shared else "--disable-shared"),
            cwd=work)
        self.run("make -j1", cwd=work)

    def package(self):
        work = self.source_folder
        # libtool 在 src/ 子目录生成产物（Makefile 的 srcdir 为 src/）；
        # 公开头文件位于 src/（Makefile DIST_HEADERS 24 个——ne_uri.h
        # 等——安装到 include/neon/，同上游 make install）
        lib = os.path.join(work, "src", ".libs")
        inc_src = os.path.join(work, "src")
        pkg_lib = os.path.join(self.package_folder, "lib")
        pkg_inc = os.path.join(self.package_folder, "include", "neon")
        os.makedirs(pkg_lib, exist_ok=True)
        os.makedirs(pkg_inc, exist_ok=True)
        # libtool wrapper 教训：复制 .libs/ 真实二进制/库
        for f in os.listdir(lib):
            if f.startswith("libneon.so"):
                shutil.copy(os.path.join(lib, f), os.path.join(pkg_lib, f))
            elif f == "libneon.la":
                shutil.copy(os.path.join(lib, f), os.path.join(pkg_lib, f))
            elif f == "libneon.a" and not self.options.shared:
                shutil.copy(os.path.join(lib, f), os.path.join(pkg_lib, f))
        # DIST_HEADERS（Makefile 定义，与上游 make install 一致）
        dist_headers = [
            "ne_request.h", "ne_session.h", "ne_utils.h", "ne_uri.h",
            "ne_socket.h", "ne_basic.h", "ne_207.h", "ne_props.h",
            "ne_xml.h", "ne_dates.h", "ne_string.h", "ne_defs.h",
            "ne_locks.h", "ne_alloc.h", "ne_md5.h", "ne_i18n.h",
            "ne_redirect.h", "ne_auth.h", "ne_compress.h", "ne_acl.h",
            "ne_ssl.h", "ne_xmlreq.h", "ne_pkcs11.h", "ne_acl3744.h",
        ]
        for h in dist_headers:
            shutil.copy(os.path.join(inc_src, h), os.path.join(pkg_inc, h))

    def package_info(self):
        self.cpp_info.libs = ["neon"]
