import os
import re
import shutil
import subprocess
import sys

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import (apply_conandata_patches, download, export_conandata_patches,
                               get, replace_in_file)

# 上游 configure.ac 的硬依赖（AC_CHECK_HEADERS / AC_CHECK_LIB）：
#   numa.h   → numactl（**必须 shared**：静态 libnuma.a 的符号带版本标签
#              `numa_node_to_cpus@@libnuma_1.2`，而 libqat 自身用
#              `-export-symbols-regex` 生成版本脚本，lld 会因「undefined version
#              libnuma_1.2」拒绝链接；shared libnuma.so 自带版本定义，可解）
#   md5.h    → openssl
NUMA_REF = "numactl/2.0.18"
OPENSSL_REF = "openssl/3.5.8.1"


class QatlibConan(ConanFile):
    name = "qatlib"
    version = "26.02.0"
    license = "BSD-3-Clause"
    homepage = "https://github.com/intel/qatlib"
    description = ("qatlib — user space library for Intel QuickAssist Technology "
                   "(cryptographic/compression acceleration; libqat + libusdm)")
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True], "with_systemd": [True, False]}
    default_options = {"shared": True, "with_systemd": False,
                       # 见上方说明：numactl 必须 shared
                       "numactl/*:shared": True}
    exports_sources = "patches/*"

    def requirements(self):
        self.requires(NUMA_REF)
        self.requires(OPENSSL_REF)

    def build_requirements(self):
        # Autotools bootstrap（仅构建上下文）。CI 干净 PATH 里有 SDK 的
        # autoconf 2.72 / autoreconf / m4 / perl，但**没有 aclocal/automake/
        # libtoolize**——autoreconf 会去 exec `aclocal` 而 PATH 上找不到：
        #   Can't exec "aclocal": No such file or directory at
        #       .../autoconf-2.72/share/autoconf/Autom4te/FileUtils.pm line 299.
        #   autoreconf: error: aclocal failed with exit status: 2
        # automake/1.18 自带 aclocal+automake（其 buildenv_info 会挂 PATH /
        # ACLOCAL_PATH / PERL5LIB），libtool/2.5.4 自带 libtoolize。
        # autoconf/m4 刻意不声明：声明 autoconf/2.72 会拉入 ohos 构建的
        # perl/5.42.2，其 XS .so 与 SDK perl 5.42.0 冲突
        # （Perl_my_cxt_init: symbol not found），且 SDK 已提供二者
        # （accel-config/4.1.9 的既有结论）。
        self.tool_requires("automake/1.18")
        self.tool_requires("libtool/2.5.4")

    def source(self):
        download(self, self.conan_data["sources"]["url"],
                 "qatlib-26.02.0.tar.gz",
                 sha256=self.conan_data["sources"]["sha256"])
        # --no-same-owner: hmdfs 上归档属主与构建 UID 不一致（同 packaging）
        self.run("tar -xzf qatlib-26.02.0.tar.gz --no-same-owner || true")
        self.run("cp -a qatlib-26.02.0/. . && rm -rf qatlib-26.02.0")
        apply_conandata_patches(self)

    def _patch_config_guess_ohos(self):
        """给 autoreconf 生成的 config.guess 补 HarmonyOS 识别。

        CI 的 automake/1.18 自带 config.guess 是 2024-07-27 版，**没有**
        HarmonyOS/ohos 分支，而本机 automake 1.16 的那份恰好有——这正是
        「本地绿、CI 红」的根因。此处等效实现仓内既有做法（scamp 2.15.0 /
        abiword-plugin-* 的 _patch_ohos_autotools），把分支插到
        ``*:NetBSD:*:*`` 之前（用假 uname 实测：打补丁前报 "unable to guess
        system type"，打补丁后输出 ``aarch64-unknown-linux-ohos``）。

        config.sub 无需改动：CI 的 automake/1.18 那份**已支持** ``ohos*``
        系统名与 ``linux-ohos*`` 组合（实测 grep 命中），故只补 config.guess。
        """
        cg = os.path.join(self.source_folder, "config.guess")
        if not os.path.isfile(cg):
            raise ConanException(
                "config.guess not found after autoreconf at %s — cannot add "
                "HarmonyOS detection; configure would fail with 'cannot guess "
                "build type'" % cg)
        with open(cg, encoding="utf-8", errors="ignore") as fh:
            text = fh.read()
        if "HarmonyOS" in text:
            return
        block = ("    *:HarmonyOS:*:*)\n"
                 "\tcase \"$UNAME_MACHINE\" in\n"
                 "\t    aarch64|arm64) MACHINE=aarch64 ;;\n"
                 "\t    armv7*|armv8*) MACHINE=arm ;;\n"
                 "\t    x86_64|amd64)  MACHINE=x86_64 ;;\n"
                 "\t    i?86)         MACHINE=i686 ;;\n"
                 "\t    *)            MACHINE=\"$UNAME_MACHINE\" ;;\n"
                 "\tesac\n"
                 "\tGUESS=${MACHINE}-unknown-linux-ohos\n"
                 "\t;;\n\n")
        new = re.sub(r"(^[ \t]+\*:NetBSD:\*:\*\)[ \t]*\n)", block + r"\1",
                     text, flags=re.M)
        if new == text:
            raise ConanException(
                "could not insert the HarmonyOS branch into config.guess — the "
                "'*:NetBSD:*:*' anchor was not found (the toolchain config.guess "
                "changed shape); refusing to continue with a config.guess that "
                "cannot identify this system")
        with open(cg, "w", encoding="utf-8") as fh:
            fh.write(new)
        self.output.info("patched config.guess: added HarmonyOS detection")

    def _dep_paths(self):
        numa = self.dependencies[NUMA_REF.split("/")[0]].package_folder
        ssl = self.dependencies[OPENSSL_REF.split("/")[0]].package_folder
        return numa, ssl

    def build(self):
        if not can_run(self):
            return
        numa, ssl = self._dep_paths()
        env = dict(os.environ)
        # tool_requires（automake/1.18 + libtool/2.5.4）的 buildenv_info 会提供
        # PATH / ACLOCAL_PATH / PERL5LIB / AUTOMAKE / ACLOCAL 等；本方法用
        # subprocess.run(env=...) 而非 self.run(env="conanbuild")，故需显式把
        # virtualbuildenv 展开进 env，否则 aclocal 仍不在 PATH 上。
        vbe = VirtualBuildEnv(self).vars()
        for k, v in vbe.items():
            env[k] = v
        provided = set(vbe.keys())
        # 下面的"本地兜底"**只在 tool_requires 未提供该变量时**才生效，绝不覆盖：
        # automake/1.18 的 PERL5LIB 指向它自己的 share/automake-1.18（其脚本里
        # 的 @INC 被装成了坏前缀 `//share/automake-1.18`，靠这条 PERL5LIB 兜住）。
        # 覆盖成 usr/local 的 1.16 后，conan 的 aclocal 找不到模块，CI #65764 报
        #   Can't locate Automake/Config.pm in @INC (... //share/automake-1.18
        #   /storage/.../usr/local/share/automake-1.16 ...)
        #   .aclocal-real line 33.
        env["PATH"] = ("/data/service/hnp/bin"
                       + os.pathsep + env.get("PATH", ""))
        _local_bin = "/storage/Users/currentUser/usr/local/bin"
        if os.path.isdir(_local_bin):
            env["PATH"] = env["PATH"] + os.pathsep + _local_bin
        if "PERL5LIB" not in provided:
            _pl = "/storage/Users/currentUser/usr/local/share/automake-1.16"
            if os.path.isdir(_pl):
                env["PERL5LIB"] = _pl
        # autoconf/m4 来自 SDK（见 build_requirements 说明）；AUTOMAKE/ACLOCAL
        # 由 automake/1.18 提供，故二者不在此处覆盖。
        for k, v in (("AUTOCONF", "/data/service/hnp/bin/autoconf"),
                     ("AUTOM4TE", "/data/service/hnp/bin/autom4te"),
                     ("AUTOHEADER", "/data/service/hnp/bin/autoheader"),
                     ("AUTOMAKE", "/storage/Users/currentUser/usr/local/bin/automake"),
                     ("ACLOCAL", "/storage/Users/currentUser/usr/local/bin/aclocal")):
            if k in provided:
                continue
            if os.path.isfile(v):
                env[k] = v
        # TMPDIR 可能只读（HMBS readonly_tmp）→ 统一走构建目录内 tmp
        tmp = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp, exist_ok=True)
        for v in ("TMPDIR", "TMP", "TEMP"):
            env.setdefault(v, tmp)
        # ★ PWD 必须与下面 subprocess.run(cwd=...) 的目标一致。
        #
        # env 是 dict(os.environ)，PWD 继承自启动 conan 的 shell（仓库目录），
        # 而实际 cwd 是 self.source_folder。本平台的 getcwd() 在 HMDFS 上并不可靠
        # （实测 bash 报 "getcwd: cannot access parent directories: Not supported"），
        # 于是 `pwd` 拿不到路径而**返回空串**，libtool 的
        #   my_xabs=`pwd`"/$my_xlib"
        # 就拼出 `/./.libs/libosal.a` 这种以 `/./` 开头的路径，链接 libqat 时：
        #   ar: /./.libs/libosal.a: No such file or directory
        #   make[1]: *** [Makefile:2614: libqat.la] Error 9
        # 干净现场下 3 次 conan create 均确定性复现；而手动在构建目录里跑 make
        # （PWD 由 shell 正确设置）则成功——这正是判定依据。
        env["PWD"] = self.source_folder

        def run(cmd, **kw):
            r = subprocess.run(cmd, cwd=self.source_folder, capture_output=True,
                               text=True, env=env, **kw)
            out = r.stdout + r.stderr
            for line in out.splitlines()[-6:]:
                print("[qatlib %s]" % cmd[0], line)
            return r, out

        # ① autoreconf（sdist 不含 configure）
        # -I m4：显式把源树内的 m4/ 加进 aclocal 搜索路径。configure.ac:29 用到
        # AX_PTHREAD，而 CI 构建环境**没有 autoconf-archive**，故由 patch 04 把
        # autoconf-archive 的 m4/ax_pthread.m4 随源码交付；不能只依赖
        # configure.ac 里的 AC_CONFIG_MACRO_DIR 声明（未必存在），显式 -I 最稳。
        # 此前 patch 04 未登记进 conandata.yml，CI #65788 报
        #   configure.ac:29: error: AX_PTHREAD not found. Please install
        #   autoconf-archive or place ax_pthread.m4 in m4/
        r, out = run(["autoreconf", "-fi", "-I", "m4"], timeout=1800)
        if r.returncode != 0:
            raise ConanException("autoreconf failed:\n%s" % out[-3000:])

        # ①b **autoreconf 之后**给 config.guess 补 HarmonyOS 识别（顺序要紧）
        #
        # autoreconf 会用工具链自带的 config.guess 覆盖源码树里的同名文件，故
        # 任何在其之前做的修补都会被打回。CI #65907 实测（automake/1.18 提供的
        # config.guess，timestamp 2024-07-27）：
        #   ./config.guess: line 1613: .../dummy.c: Permission denied
        #   ./config.guess: unable to guess system type
        #   configure: error: cannot guess build type; you must specify one
        # 本机之所以一直绿，是因为系统 automake 1.16 的 config.guess **已自带**
        # `*:HarmonyOS:*:*` 分支——又一个「本地绿、CI 红」。
        #
        # 刻意**不**用 `--build=aarch64-unknown-linux-ohos`：按项目既有结论，
        # autotools 包在 CI 上显式传 --build 会导致 "C compiler cannot create
        # executables"（psfex / weightwatcher / skymaker 同报），正确姿势是让
        # config.guess/config.sub 认识 OHOS。
        self._patch_config_guess_ohos()

        # ①c configure 里用 `umask 077 && mktemp -d ./confXXXXXX` 建临时目录，
        # 而 HMDFS 上 077/070 建出来的目录**不可写**（权限位被忽略/受限），
        # 于是 config.status 后续 exec 其中的 subs1.awk 直接失败（CI #65907 的
        # 下一道坎，本地复现同上）：
        #   ./config.status: line 821: ./confXXXXXX/subs1.awk: Permission denied
        #   config.status: error: could not setup config files machinery
        # 修法与仓内 scamp 2.15.0 一致：把 configure 里的 umask 077 改为 000
        # （只改这一处模式，不动其它 umask）。
        cfg_f = os.path.join(self.source_folder, "configure")
        if os.path.isfile(cfg_f):
            with open(cfg_f, encoding="utf-8", errors="ignore") as fh:
                ctext = fh.read()
            if "umask 077" in ctext:
                with open(cfg_f, "w", encoding="utf-8") as fh:
                    fh.write(ctext.replace("umask 077", "umask 000"))
                self.output.info(
                    "patched configure: umask 077 -> 000 "
                    "(HMDFS cannot write into 077 temp dirs)")

        # ② configure
        #  - --disable-fast-crc-in-assembler: 汇编 CRC 用 `nasm -f elf64`，x86 专属
        #  - --disable-samples: 示例代码含 x86 专属 rdtsc 内联汇编
        #  - cross.cache: aarch64 交叉编译下 conftest 无法在构建机执行
        cache = os.path.join(self.build_folder, "cross.cache")
        with open(cache, "w", encoding="utf-8") as fh:
            fh.write("# OHOS aarch64 交叉编译：conftest 无法在构建机上运行\n"
                     "ac_cv_prog_cc_works=yes\n"
                     "ac_cv_prog_cc_cross=yes\n")
        cfg = ["./configure",
               "--cache-file=" + cache,
               "--disable-fast-crc-in-assembler",
               "--disable-samples",
               "--enable-systemd=" + ("yes" if self.options.with_systemd else "no"),
               "--prefix=" + self.package_folder]
        env["CPPFLAGS"] = "-I%s/include -I%s/include" % (numa, ssl)
        # LIBS 里的 -lnuma 走 shared .so（见 numactl shared 说明）
        env["LDFLAGS"] = "-L%s/lib -L%s/lib" % (numa, ssl)
        r, out = run(cfg, timeout=1800)
        if r.returncode != 0:
            raise ConanException("configure failed:\n%s" % out[-3000:])

        # ③ make（需要 LIBS=-lnuma 让 configure 生成的 Makefile 找到 numa 符号）
        r, out = run(["make", "-j%d" % (os.cpu_count() or 4),
                      "LIBS=-lnuma"], timeout=3600)
        if r.returncode != 0:
            raise ConanException("make failed:\n%s" % out[-4000:])

        # 产物自检：libqat / libusdm 必须存在
        built = []
        for root, _, files in os.walk(self.source_folder):
            for f in files:
                if re.match(r"^lib(qat|usdm)\.so", f):
                    built.append(os.path.join(root, f))
        self.output.info("[qatlib] built libraries: %s"
                         % [os.path.basename(b) for b in built])
        if len(built) < 2:
            raise ConanException("expected libqat + libusdm, got %s" % built)

        r, out = run(["make", "install"], timeout=1800)
        if r.returncode != 0:
            raise ConanException("make install failed:\n%s" % out[-3000:])
        self._built = [os.path.basename(b) for b in built]

    def package(self):
        # make install 已装到 self.package_folder；此处补头文件目录结构校验
        inc = os.path.join(self.package_folder, "include")
        if not os.path.isdir(inc):
            raise ConanException("headers not installed to include/")
        # 上游 make install **漏装** qat_library_version.h，而公开头
        # icp_sal_versions.h 以 `<qat_library_version.h>`（顶层）引用它 →
        # 消费者编译时必然 "file not found"。此处从构建树补装到 include/ 顶层。
        ver_h = os.path.join(self.source_folder, "quickassist", "lookaside",
                             "access_layer", "include",
                             "qat_library_version.h")
        if os.path.isfile(ver_h):
            shutil.copy2(ver_h, os.path.join(inc, "qat_library_version.h"))
            self.output.info("[qatlib] installed missing qat_library_version.h")
        else:
            raise ConanException("qat_library_version.h not found in source tree")
        # 上游测试结果 marker（本包无自带单元测试，如实记录）
        import json
        marker = {"status": "built", "framework": "none",
                  "notes": ["qatlib 上游未提供单元测试框架（autotools 无 TESTS/"
                            "check_PROGRAMS）；--disable-samples 关闭了唯一的示例"
                            "可执行文件（含 x86 专属 rdtsc 汇编）"],
                  "libraries_built": getattr(self, "_built", [])}
        dest = os.path.join(self.package_folder, "res",
                            "upstream_test_result.json")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w", encoding="utf-8") as fh:
            json.dump(marker, fh, ensure_ascii=False, indent=2)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "qatlib")
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["qat", "usdm"]
        self.cpp_info.requires = []  # openssl/numactl 为 C 库，由链接器链接
        libdir = os.path.join(self.package_folder, "lib")
        if self.settings.os == "Linux":
            self.cpp_info.system_libs = ["pthread", "dl"]
        # 运行期库路径（消费侧 dlopen/链接 .so 需要）
        self.runenv_info.append_path("LD_LIBRARY_PATH", libdir)
