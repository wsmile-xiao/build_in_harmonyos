#!/usr/bin/env python3
"""Conan recipe — libatasmart 0.19 (autotools, OHOS).

libatasmart = ATA S.M.A.R.T. 读取库(纯 C,零外部依赖,仅 libc/内核 ATA 面)。
tarball 自带生成的 atasmart.strpool.c;补丁 0001 跳过 strpool host 工具
(交叉构建时 strpool 会被交叉编译却要在构建机上执行,必挂)。
"""
import os

from conan import ConanFile
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class LibatasmartConan(ConanFile):
    name = "libatasmart"
    version = "0.19"
    description = "libatasmart — ATA S.M.A.R.T. reading and reporting library"
    license = "LGPL-2.1-or-later"
    homepage = "http://git.0pointer.net/git/libatasmart.git"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}
    exports_sources = "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        self.settings.rm_safe("compiler.cppstd")
        self.settings.rm_safe("compiler.libcxx")

    def requirements(self):
        # configure.ac 硬检查 PKG_CHECK_MODULES([LIBUDEV], [libudev >= 143]):
        # 制品仓 eudev/3.2.14 提供 libudev.pc(仅构建期探测,库本体不链接 udev)
        self.requires("eudev/3.2.14")

    def source(self):
        get(self, **self.conan_data["sources"]["0.19"], strip_root=True)

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        tc = AutotoolsToolchain(self)
        # skdump/sktest 为诊断工具,随库一并构建(不执行)
        tc.generate()
        # PkgConfigDeps 从 eudev 包 cpp_info 生成 libudev.pc(含 Requires 链),
        # conan 自动把它加入 conanbuild 的 PKG_CONFIG_PATH——configure 的
        # PKG_CHECK_MODULES 命中;LIBUDEV_*/triplet args 作为双保险保留
        deps = PkgConfigDeps(self)
        deps.generate()
        # CI 66371/66494/66547 根因:worker shell 无 ksh `print` 内建,
        # config.status(CI 66547 实测 line 713/725/1444 "print: command
        # not found")写出的 libtool 转义损坏,make 一解析即炸。给 PATH
        # 注入一个 ksh print 语义的 shim(bash 实现,-r raw / -n 无换行),
        # config.status 的 print 调用即可正常写文件。eudev(包龄新)同
        # 流程无此雷,佐证是 2012 老 config.status 的 shell 探测差异。
        bindir = os.path.join(self.build_folder, "_bin")
        os.makedirs(bindir, exist_ok=True)
        with open(os.path.join(bindir, "print"), "w", newline="\n") as f:
            f.write(
                "#!/bin/sh\n"
                "# minimal ksh print shim (config.status uses print -r --)\n"
                "raw=0; nl=1\n"
                "while [ $# -gt 0 ]; do\n"
                "  case \"$1\" in\n"
                "    -r) raw=1; shift ;;\n"
                "    -n) nl=0; shift ;;\n"
                "    --) shift; break ;;\n"
                "    -*) shift ;;\n"
                "    *) break ;;\n"
                "  esac\n"
                "done\n"
                "if [ \"$raw\" = 1 ]; then\n"
                "  first=1\n"
                "  for a in \"$@\"; do\n"
                "    [ \"$first\" = 1 ] || printf ' '\n"
                "    printf '%s' \"$a\"\n"
                "    first=0\n"
                "  done\n"
                "else\n"
                "  printf '%b' \"$*\"\n"
                "fi\n"
                "[ \"$nl\" = 1 ] && printf '\\n'\n")
        os.chmod(os.path.join(bindir, "print"), 0o755)
        env = Environment()
        env.prepend_path("PATH", bindir)
        env.vars(self, scope="build").save_script("libatasmart-print-shim")

    def _eudev_paths(self):
        eudev = self.dependencies["eudev"]
        inc = eudev.cpp_info.includedirs[0].replace("\\", "/")
        lib = eudev.cpp_info.libdirs[0].replace("\\", "/")
        return inc, lib

    def build(self):
        apply_conandata_patches(self)
        # R5:OHOS 无 /bin/sh 兼容面(config.status 的 print/subs.awk 在
        # mksh/dash 下挂),configure/config.status 显式用 hnp bash
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        os.environ["CONFIG_SHELL"] = bash
        # HMDFS 临时文件权限异常(eudev 同款):TMPDIR 指向可写 build 目录
        os.environ["TMPDIR"] = self.build_folder
        # HMDFS umask 077 雷(consolation/doas 同款):config.status
        # 'could not setup config files machinery' → 预防性归一为 022
        cfg = os.path.join(self.source_folder, "configure")
        if os.path.isfile(cfg):
            with open(cfg, "rb") as f:
                data = f.read()
            if b"umask 077" in data:
                with open(cfg, "wb") as f:
                    f.write(data.replace(b"umask 077", b"umask 022"))
        inc, lib = self._eudev_paths()
        autotools = Autotools(self)
        # tc.configure_args 在 worker 的 conan 2.29 不落 configure 命令行
        # (RUN 行实证)——LIBUDEV_* precious vars 与 triplet 一律直传 args
        autotools.configure(args=[
            "LIBUDEV_CFLAGS=-I{}".format(inc),
            "LIBUDEV_LIBS=-L{} -ludev".format(lib),
            "--host=aarch64-linux-ohos",
            "--build=aarch64-linux-ohos",
        ])
        # CI 66494/66547:worker 的 shell 无 ksh `print` 内建(config.status
        # line 713/725/1444 print not found),生成的 libtool 的
        # archive_expsym_cmds 多行赋值区转义损坏,make 一解析即炸(line 350
        # syntax error `}`;WSL 同树全绿对照确认该段为 symver 版本脚本)。
        # 本库无符号版本需求——把赋值改名,libtool 退化普通链接。注意 conan
        # 拷源后构建发生在 build-release/(basic_layout),两处都试。
        for cand in (self.build_folder, self.source_folder):
            lt = os.path.join(cand, "libtool")
            if not os.path.isfile(lt):
                continue
            with open(lt, "rb") as f:
                d = f.read()
            d2 = d.replace(b"\narchive_expsym_cmds=",
                           b"\narchive_expsym_cmds_disabled=", 1)
            if d2 != d:
                with open(lt, "wb") as f:
                    f.write(d2)
                break
        # CI 66371:make 默认 SHELL=/bin/sh(mksh),2012 年的 libtool 脚本
        # 含 mksh 不兼容语法(line 350 syntax error `}`)——命令行变量把
        # make 的 SHELL 钉到 hnp bash(GNU make 命令行覆盖一切)
        autotools.make(args=["-j4", "SHELL=" + bash])

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        import shutil
        # 清理发行附带的文档段,保留头/库/pc/vapi
        for extra in ("share/doc", "share/man"):
            p = os.path.join(self.package_folder, extra)
            if os.path.isdir(p):
                shutil.rmtree(p, ignore_errors=True)

    def package_info(self):
        self.cpp_info.libs = ["atasmart"]
        self.cpp_info.set_property("cmake_file_name", "libatasmart")
        self.cpp_info.set_property("cmake_target_name", "libatasmart::libatasmart")
        self.cpp_info.set_property("pkg_config_name", "libatasmart")
