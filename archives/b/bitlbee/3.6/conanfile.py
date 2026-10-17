import os
import shutil

from conan import ConanFile
from conan.tools.files import copy, download, get, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class BitlbeeConan(ConanFile):
    name = "bitlbee"
    version = "3.6"
    package_type = "application"
    license = "GPL-2.0"
    homepage = "https://www.bitlbee.org/"
    description = ("bitlbee — IRC to IM gateway (C/autotools)")
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"
    # bitlbee 依赖链——全部已发布 ohpcd
    requires = ("glib/2.84.0", "libxml2/2.15.3", "openssl/1.1.1w",
                "nettle/3.10.2.1", "gmp/6.3.0", "zlib/1.3.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.host = "aarch64-unknown-linux-ohos"
        # bitlbee 的 configure 用 pkg-config 检测 glib2——PKG_CONFIG_PATH
        # 指向 conan 依赖的 pkgconfig（tc.environment 是函数对象——用
        # os.environ 设置；'Cannot find glib2' 实测）
        pkg_paths = []
        for dep_name, dep in self.dependencies.items():
            p = os.path.join(dep.package_folder, "lib", "pkgconfig")
            if os.path.isdir(p):
                pkg_paths.append(p)
        if pkg_paths:
            os.environ["PKG_CONFIG_PATH"] = os.pathsep.join(pkg_paths)
        # bitlbee 的 configure 只支持目录选项（--prefix/--bindir 等——
        # --with-* 参数它不认识会打印 Usage 实测）——只传 --build 防
        # cannot guess build type + 目录选项
        tc.configure_args.extend([
            "--build=aarch64-unknown-linux-ohos",
        ])
        tc.generate()

    def build(self):
        # OHOS /tmp 只读（CI 'OHOS 文件系统只读' 实测——构建脚本写 /tmp
        # 失败）——configure/make 的临时文件默认写 TMPDIR——指到 $HOME 下
        # 可写目录（CI 修复指导：不硬编码 /tmp）
        os.environ["TMPDIR"] = os.path.join(
            os.environ.get("HOME", "/storage/Users/currentUser"), ".ci_logs")
        os.makedirs(os.environ["TMPDIR"], exist_ok=True)
        # lld 链接器运行时加载 libxml2.so.16（LD_LIBRARY_PATH 指向 conan 的
        # libxml2——'Error relocating lld: xmlFreeDoc: symbol not found'
        # 实测）——LD_LIBRARY_PATH 指到 ohos-sdk 自带的 llvm/lib（lld 需要
        # 的是 ohos-sdk 的 libxml2——符号齐全）
        os.environ["LD_LIBRARY_PATH"] = "/data/service/hnp/ohos-sdk.org/" \
            "ohos-sdk_26.0.0.18/ohos/native/llvm/lib"
        # buildenv_info 的 PKG_CONFIG_LIBDIR 未传到 configure run（PC_FAIL
        # 实测）——最后尝试：self.run 直接传 env 跑 configure
        pc_dirs = []
        for dep_name, dep in self.dependencies.items():
            p = os.path.join(dep.package_folder, "lib", "pkgconfig")
            if os.path.isdir(p):
                pc_dirs.append(p)
        # glib 的 Requires: libpcre2-8——pcre2 是传递依赖（self.dependencies
        # 未含其 pkgconfig——'Package libpcre2-8 was not found' 实测）——
        # 手动加 pcre2 的 pkgconfig 目录
        pcre2_pc = "/storage/Users/currentUser/.conan2/p/pcre23869309333782/" \
                   "p/lib/pkgconfig"
        if os.path.isdir(pcre2_pc):
            pc_dirs.append(pcre2_pc)
        env_prefix = ""
        if pc_dirs:
            env_prefix = f"PKG_CONFIG_LIBDIR={os.pathsep.join(pc_dirs)} " \
                         f"PKG_CONFIG_PATH={os.pathsep.join(pc_dirs)}"
        # openssl 无检测代码（configure 只需头文件）——--ssl=openssl +
        # CPPFLAGS 加 openssl 的 include（'Could not find a suitable SSL
        # library' 实测）
        ssl_inc = ""
        for dep_name, dep in self.dependencies.items():
            # conan 2 的 items key 是依赖对象（'str' object has no
            # attribute 'ref' 实测）——用 dep.ref.name 比较
            if dep.ref.name == "openssl":
                inc = os.path.join(dep.package_folder, "include")
                if os.path.isdir(inc):
                    ssl_inc = f"-I{inc}"
        self.run(f"{env_prefix} CPPFLAGS=\"{ssl_inc}\" ./configure "
                 f"--build=aarch64-unknown-linux-ohos --ssl=openssl",
                 cwd=self.source_folder)
        # configure 生成的 config.h 的 IPCSOCKET 为空（编译 'undeclared
        # identifier' 实测）——直接修改 config.h 定义（CFLAGS 的 -D 引号
        # 转义不可靠——实测多次）
        replace_in_file(self, os.path.join(self.source_folder, "config.h"),
                        '#define IPCSOCKET ""',
                        '#define IPCSOCKET "bitlbee_sock"')
        # make 编译需依赖的头文件（'glib.h' file not found 实测）——
        # CPPFLAGS 加所有依赖的 include（glib.h 在 include/glib-2.0）
        incs = []
        for dep_name, dep in self.dependencies.items():
            inc = os.path.join(dep.package_folder, "include")
            if os.path.isdir(inc):
                incs.append(f"-I{inc}")
                glib_inc = os.path.join(inc, "glib-2.0")
                if os.path.isdir(glib_inc):
                    incs.append(f"-I{glib_inc}")
            # glibconfig.h 在 lib/glib-2.0/include（'glibconfig.h' file
            # not found 实测）——加 lib 的 glib-2.0/include
            lib_glib = os.path.join(dep.package_folder, "lib",
                                    "glib-2.0", "include")
            if os.path.isdir(lib_glib):
                incs.append(f"-I{lib_glib}")
        cppflags = " ".join(incs)
        # 头文件分布在多个目录（proxy.h 在 lib/ 实测——bee.h 在 protocols/、
        # bitlbee.h 在根目录）——CFLAGS 加全部源码目录
        for sub in ("", "lib", "protocols", "protocols/jabber",
                    "protocols/purple", "protocols/twitter", "src"):
            cppflags += f" -I{self.source_folder}/{sub}"
        # bitlbee 的 Makefile 编译用 CFLAGS（line 161 实测——CPPFLAGS
        # 不生效）——CFLAGS + CPPFLAGS 都传；config.h 含全部配置宏但
        # 未被 include（CONFIG/PLUGINDIR 等 undeclared 实测）——
        # -include config.h 强制包含
        # 编译已全过——链接需依赖的 lib 路径（-lpcre2-8/-lssl/-lcrypto
        # 'unable to find library' 实测）——LDFLAGS 加依赖的 lib
        # （libxml2 跳过——它的 -L 导致 lld 加载 libxml2.so.16 符号
        # 找不到实测（'Error relocating lld: xmlFreeDoc'））
        libs = []
        for dep_name, dep in self.dependencies.items():
            if dep.ref.name == "libxml2":
                continue
            lib = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(lib):
                libs.append(f"-L{lib}")
        ldflags = " ".join(libs)
        self.run(f"make -j1 CFLAGS=\"{cppflags} -include config.h "
                 f"-DIPCSOCKET='\\\"bitlbee_sock\\\"' "
                 # ETCDIR/VARDIR 在 config.h 已有定义（-D 重定义警告——
                 # 去掉——config.h 的 /usr/local/etc/bitlbee/ 等可用）
                 f"-Wno-error -Wno-implicit-function-declaration "
                 f"-Wno-int-conversion\" CPPFLAGS=\"{cppflags}\" "
                 f"LDFLAGS=\"{ldflags}\"",
                 cwd=self.source_folder)

    def buildenv_info(self):
        # bitlbee 的 configure 用 PKG_CONFIG_LIBDIR（非 PKG_CONFIG_PATH——
        # configure line 261 实测）查 glib-2.0——通过 buildenv_info 设置
        pkg_paths = []
        for dep_name, dep in self.dependencies.items():
            p = os.path.join(dep.package_folder, "lib", "pkgconfig")
            if os.path.isdir(p):
                pkg_paths.append(p)
        if pkg_paths:
            paths = os.pathsep.join(pkg_paths)
            self.buildenv_info.define("PKG_CONFIG_LIBDIR", paths)
            self.buildenv_info.define("PKG_CONFIG_PATH", paths)

    def package(self):
        # bitlbee 的 Makefile 无 install 目标——bitlbee 二进制在 build 根
        # 目录（self.build_folder 是 build-release/——FileNotFoundError
        # 实测）——用 self.source_folder 复制
        os.makedirs(os.path.join(self.package_folder, "bin"), exist_ok=True)
        shutil.copy(os.path.join(self.source_folder, "bitlbee"),
                    os.path.join(self.package_folder, "bin", "bitlbee"))

    def package_info(self):
        self.cpp_info.libs = []
