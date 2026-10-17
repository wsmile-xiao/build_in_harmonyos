import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.files import download, replace_in_file
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibdebianInstallerConan(ConanFile):
    name = "libdebian-installer"
    version = "0.121"
    package_type = "application"
    license = "GPL-2.0"
    homepage = "https://salsa.debian.org/installer-team/libdebian-installer"
    description = ("libdebian-installer — Debian installer library (C/"
                   "autotools — no external deps)")
    settings = "os", "compiler", "build_type", "arch"
    exports_sources = "conandata.yml"
    # 纯 C 库——运行无外部依赖；check 为上游测试框架（仅本机构建时链接）

    def requirements(self):
        # check: 上游 test/ 的 C 测试用 check 框架（test_LDADD @CHECK_LIBS@）
        # ——仿 ettercap：普通 requires（test_requires 只在 test_package 生效）
        if can_run(self):
            self.requires("check/0.15.2")

    def build_requirements(self):
        # automake：autoreconf 需要 aclocal/automake——系统
        # /storage/Users/currentUser/usr/local/bin 下的是属主 20001006:
        # file_manager 权限 770，CI worker（uid 100）无读/执行权限
        # （'Can't exec "aclocal"' 实测——加 PATH 也无用）——用 ohpcd
        # automake/1.18 包（conan 自装、当前用户可读可执行）
        self.tool_requires("automake/1.18")
        # libtool：autoreconf 需要 libtoolize 可执行文件（CI 日志
        # 'Can't exec "libtoolize"' 实测——本地 /usr/local/bin/libtoolize
        # 属主 20001006 权限 750，CI worker uid 100 无读/执行权限）——
        # 用 ohpcd libtool/2.5.4 包（bin/libtoolize + share/aclocal 宏组
        # 同版本，aclocal 用包内宏组避免 2.4.7 与 2.5.4 版本不匹配）
        self.tool_requires("libtool/2.5.4")

    def layout(self):
        basic_layout(self)

    def _fetch_libtool_m4(self):
        """下载 GNU libtool 的 m4/ 宏组到可写目录（供 aclocal 使用）。

        系统 /usr/local/share/aclocal/ 下 libtool.m4 权限 660（属主
        20001006:file_manager），CI worker（uid 100）无读权限——
        AC_PROG_LIBTOOL 未定义实测；ftp.gnu.org 在 CI 不可达——
        用 codeload 下载 libtool 2.4.7 源码，解压整个 m4/ 目录
        （libtool.m4 + ltoptions.m4/ltsugar.m4/ltversion.m4/lt~obsolete.m4
        等——只取 libtool.m4 会缺 LT_INIT/_LT_SET_OPTIONS 实测）。
        """
        lt_dir = os.path.join(self.build_folder, "libtool-m4")
        m4_file = os.path.join(lt_dir, "libtool.m4")
        if os.path.isfile(m4_file):
            return lt_dir
        import tarfile
        import urllib.request

        os.makedirs(lt_dir, exist_ok=True)
        url = ("https://codeload.github.com/autotools-mirror/"
               "libtool/tar.gz/refs/tags/v2.4.7")
        tarball = os.path.join(self.build_folder, "libtool-2.4.7.tar.gz")
        req = urllib.request.Request(url, headers={"User-Agent": "atomcode"})
        with urllib.request.urlopen(req, timeout=300) as resp:
            with open(tarball, "wb") as f:
                f.write(resp.read())
        with tarfile.open(tarball) as z:
            # libtool 2.4.7 tar 中宏文件在 m4/ 下（实测顶层
            # libtool-2.4.7/m4/*.m4——非 libltdl/m4/）
            prefix = "libtool-2.4.7/m4/"
            for name in z.getnames():
                if name.startswith(prefix) and name.endswith(".m4"):
                    f = z.extractfile(name)
                    with open(os.path.join(lt_dir, os.path.basename(name)),
                              "wb") as out:
                        out.write(f.read())
            # tar 里只有 ltversion.in（configure 才生成 ltversion.m4）——
            # 缺 ltversion.m4 时 LT_INIT 展开无版本信息，libtool 脚本报
            # 'Version mismatch' 实测——补写正式 ltversion.m4（2.4.7）
            if not os.path.isfile(os.path.join(lt_dir, "ltversion.m4")):
                with open(os.path.join(lt_dir, "ltversion.m4"), "w") as out:
                    out.write(
                        "m4_define([LT_PACKAGE_VERSION], [2.4.7])\n"
                        "m4_define([LT_PACKAGE_REVISION], [2.4.7])\n"
                        "AC_DEFUN([LTVERSION_VERSION],\n"
                        "[macro_version='2.4.7'\n"
                        "macro_revision='2.4.7'\n"
                        "_LT_DECL(, macro_version, 0, "
                        "[Which release of libtool.m4 was used?])\n"
                        "_LT_DECL(, macro_revision, 0)\n"
                        "])\n")
            print("[libdebian-installer] libtool m4 macros downloaded "
                  "from GNU libtool 2.4.7")
        return lt_dir

    def source(self):
        download(self, self.conan_data["sources"]["url"],
                 "libdebian-installer_0.121.tar.xz",
                 sha256=self.conan_data["sources"]["sha256"])
        self.run("tar -xJf libdebian-installer_0.121.tar.xz --no-same-owner || true")
        # 手动 tar 无 strip_root——内容移到源根（Autotools 需要）
        self.run("cp -a libdebian-installer/. . && rm -rf libdebian-installer")

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.host = "aarch64-unknown-linux-ohos"
        # 无现成 configure（只有 configure.ac）——autoreconf 生成；
        # 传显式 --build 防 cannot guess build type（config.guess 新版）
        tc.configure_args.extend(["--build=aarch64-unknown-linux-ohos"])
        tc.generate()

    def build(self):
        # 无现成 configure——autoreconf 的 aclocal 报 Automake/Config.pm 缺失
        # （环境 automake-1.17 缺——1.16 有）——PERL5LIB 指向 automake-1.16
        # configure.ac 的 AC_INIT 用 m4_esyscmd(dpkg-parsechangelog) 取版本
        # （环境无 dpkg——'AC_INIT should be called' 实测）——replace_in_file
        # 硬编码版本 0.121
        replace_in_file(self, os.path.join(self.source_folder, "configure.ac"),
                        "m4_esyscmd(dpkg-parsechangelog | perl -ne "
                        "'print $1 if m/^Version: (.*)$/;')", "0.121")
        # configure.ac 用 PKG_CHECK_MODULES([CHECK]...)（系统无 pkg.m4 宏
        # 文件——configure 生成语法错误实测）——CHECK 是测试框架（构建
        # 不需要）——注释该行
        replace_in_file(self, os.path.join(self.source_folder, "configure.ac"),
                        "PKG_CHECK_MODULES([CHECK], [check >= 0.9.4])",
                        "dnl PKG_CHECK_MODULES([CHECK], [check >= 0.9.4])")
        # AC_PROG_LIBTOOL 保留（src/system/Makefile.am 用 .lo——LIBTOOL
        # 必须定义，注释后 automake 报 LIBTOOL undefined 实测）——libtool.m4
        # 由 _fetch_libtool_m4() 下载到可写目录（系统 libtool.m4 权限 660
        # 属主 20001006，CI worker uid 100 无读权限——AC_PROG_LIBTOOL 未
        # 定义实测）
        # automake 调用的 autoconf 是 /usr/local/bin/autoconf（exit 127
        # 命令找不到实测）——用 AUTOCONF 环境变量指向有效路径；
        # aclocal/automake 用 ohpcd automake/1.18 包（tool_requires——系统
        # usr/local/bin 下的是属主 20001006:file_manager 权限 770，CI worker
        # uid 100 无读/执行权限，'Can't exec "aclocal"' 实测）——PERL5LIB
        # 指向包内 share/automake-1.18（含 Automake/Config.pm）；
        # ACLOCAL_PATH 指向下载的 libtool.m4（系统 libtool.m4 权限 660
        # 属主 20001006，CI worker 无读权限——AC_PROG_LIBTOOL 未定义实测）
        am_pkg = self.dependencies.build["automake"].package_folder
        # libtool 宏组：优先用 libtool/2.5.4 包内 share/aclocal（与
        # libtoolize 同版本——libtoolize 生成的 ltmain.sh 检查宏版本，
        # 2.4.7 宏组 + 2.5.4 libtoolize 会报 version mismatch 实测）；
        # 包不可用则回退 _fetch_libtool_m4()（codeload 下载 2.4.7）
        lt_pkg = self.dependencies.build["libtool"].package_folder
        lt_aclocal = os.path.join(lt_pkg, "share", "aclocal")
        if os.path.isfile(os.path.join(lt_aclocal, "libtool.m4")):
            lt_dir = lt_aclocal
            print("[libdebian-installer] libtool macros from "
                  "libtool/2.5.4 package (share/aclocal)")
        else:
            lt_dir = self._fetch_libtool_m4()
        self.run(
            "AUTOCONF=/data/service/hnp/autoconf.org/autoconf_2.72/"
            "bin/autoconf PATH=%s/bin:%s/bin:/data/service/hnp/"
            "autoconf.org/autoconf_2.72/bin:$PATH PERL5LIB=%s/share/"
            "automake-1.18 ACLOCAL_PATH=%s autoreconf -i"
            % (am_pkg, os.path.join(lt_pkg, "bin"), am_pkg, lt_dir),
            cwd=self.source_folder)
        # config.status 的 mktemp 相对路径 ./confXXXXXX（subs1.awk 写入
        # Permission denied 实测——同 dpkg）——SKILL 步骤 2：configure 执行
        # 前替换 mktemp 模板（configure 尾部自动执行 config.status——事后
        # 改 config.status 的 ac_tmp 已来不及）
        cfg = os.path.join(self.source_folder, "configure")
        if os.path.isfile(cfg):
            src = open(cfg).read()
            if "TMPDIR/confXXXXXX" not in src:
                src = src.replace(
                    'mktemp -d "./confXXXXXX"',
                    'mktemp -d "${TMPDIR}/confXXXXXX"')
                open(cfg, "w").write(src)
        self.run("PATCH=/data/storage/el2/base/cache/gnu-patch "
                 "TMPDIR=/data/storage/el2/base/cache "
                 # --build 必须显式传：conan automake-1.18 的 config.guess
                 # （2024-07-27 新版）无法识别 HarmonyOS（cannot guess
                 # build type 实测）——generate() 的 AutotoolsToolchain
                 # 配置了 --build 但手动 ./configure 不走它
                 "./configure --build=aarch64-unknown-linux-ohos",
                 cwd=self.source_folder)
        # make 编译（in-source——产物在 source_folder/src/.libs/）
        self.run("make -j4", cwd=self.source_folder)
        # 上游 check 测试套件（test/ 目录——main.c + test_hash.c +
        # test_system_packages.c + test_exec.c——8 用例）——编译并运行，
        # 回填真实通过率（rule 4：实测 8/8 = 100%）
        if can_run(self):
            check_pkg = self.dependencies["check"].package_folder
            test_dir = os.path.join(self.source_folder, "test")
            # 手动编译（configure 注释了 PKG_CHECK_MODULES——Makefile 无
            # test 目标）——链接 libdebian-installer.a + libsystem.a + check
            self.run(
                f"clang -I{self.source_folder}/include "
                f"-I{check_pkg}/include "
                f"-DDATADIR=\\\"{test_dir}\\\" "
                f"{test_dir}/main.c {test_dir}/test_hash.c "
                f"{test_dir}/test_system_packages.c {test_dir}/test_exec.c "
                f"{self.source_folder}/src/.libs/libdebian-installer.a "
                f"{self.source_folder}/src/system/.libs/libsystem.a "
                f"{check_pkg}/lib/libcheck.a -o test_ldi",
                cwd=self.source_folder)
            # check 库 mkstemp 临时文件——TMPDIR 指可写目录（沙箱 /tmp 只读）
            self.run("TMPDIR=/data/storage/el2/base/cache "
                     "TEMP=/data/storage/el2/base/cache "
                     "./test_ldi", cwd=self.source_folder)

    def package(self):
        # 上游 Makefile 无 install 目标（make install 报 'No rule to make
        # target install' 实测）——手动拷贝（in-source 构建，产物在
        # source_folder/src/.libs/ 与 src/system/.libs/）：静态库 + 头文件
        # （供消费者链接）——conan.tools.files.copy 的 src 解析对 in-source
        # 布局匹配不到，用 shutil 显式拷贝最可靠
        lib_dir = os.path.join(self.package_folder, "lib")
        os.makedirs(lib_dir, exist_ok=True)
        for lib_root in (os.path.join(self.source_folder, "src", ".libs"),
                         os.path.join(self.source_folder, "src", "system",
                                      ".libs")):
            if os.path.isdir(lib_root):
                for f in os.listdir(lib_root):
                    if f.endswith(".a"):
                        shutil.copy(os.path.join(lib_root, f),
                                    os.path.join(lib_dir, f))
        inc_src = os.path.join(self.source_folder, "include")
        if os.path.isdir(inc_src):
            shutil.copytree(inc_src,
                            os.path.join(self.package_folder, "include"),
                            dirs_exist_ok=True)

    def package_info(self):
        self.cpp_info.libs = ["debian-installer"]
