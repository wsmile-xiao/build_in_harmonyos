#!/usr/bin/env python3
"""tlog 14 消费者侧测试（conan L1，真实执行）。

四类验证，都跑真实代码、统计真实断言数：
1. libtlog 公开 API（test_libtlog.c，18 条断言）：grc 错误码族 / utf8 /
   timestr（**struct timespec**）/ pkt 四族。timestr 与 pkt 用的正是本次
   头文件补丁（0004-0010）补上的 POSIX 类型，编译通过本身即是对补丁的回归。
2. OHOS/musl 特有回归（7 条断言，build() 中）：把 0004-0010 补过的 7 个公开头
   各自做成一个 TU 的**唯一** include 单独编译 —— 这 7 个头在 glibc 上能靠
   <stdlib.h>/<stdint.h> 间接拿到 struct timespec/ssize_t，musl(OHOS) 上不能，
   补丁正是为此而加。断言在 glibc 上恒真、在 musl 上无补丁必假，属本适配
   特有的回归网（上游测试集与 test_libtlog.c 都覆盖不到「头自包含」）。
3. 三个 CLI 的功能与配置加载（test_cli.sh，7 条断言）：--version / --help /
   --configuration，并用上游自己的「按二进制路径定位配置」规则
   （lib/tlog/misc.c:44）让默认配置真实加载。
4. 上游测试集（src/tltest，13 项）在包构建期由 ../conanfile.py 的
   `_run_upstream_tests()` 以 `make check` 执行（清点见 MANIFEST.yml）。
"""
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building


class TlogTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    # 本包补丁 0004-0010 补过的公开头（每个都补了 <time.h> 或 <sys/types.h>）
    OHOS_PATCHED_HEADERS = ("json_msg", "json_stream", "pkt", "rl_json_writer",
                            "source", "timestr", "tty_source")

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _probe_flags(self):
        """收集被测包 + 整条依赖链的 INCLUDE/LIB 标志（只收绝对路径）。"""
        dep = self.dependencies["tlog"].cpp_info
        # libtlog 默认静态（options.shared=False），链接期要拿「所有依赖」的
        # include/lib 目录与库名（libtlog.a 的成员会引到 json-c/curl 等符号）。
        incs, libdirs, libs = [], [], ["-l" + name for name in dep.libs or []]
        for ref, _dep in self.dependencies.items():
            cpp_info = _dep.cpp_info
            for path in cpp_info.includedirs or []:
                # 相对路径没有意义：依赖链/宿主环境里可能混进 `-Iinclude`，
                # 在 test_package 的构建目录下它指向不存在的目录。
                if not os.path.isabs(path):
                    continue
                incs.append("-I" + path)
                # 库常把公开头装在 <includedir>/<name>/ 下（json-c 即
                # include/json-c/），而上游源码用扁平写法（#include
                # <json_object.h>）；配方 generate() 同样补齐该子目录，否则此处
                # 编译不过。注意 key 是 Requirement，包名经其 .ref 取（与配方
                # generate() 中的 dep.ref.name 同一口径）。
                sub = os.path.join(path, ref.ref.name)
                if os.path.isdir(sub):
                    incs.append("-I" + sub)
            libdirs += [p for p in cpp_info.libdirs or [] if os.path.isabs(p)]
            for name in cpp_info.libs or []:
                flag = "-l" + name
                if flag not in libs:
                    libs.append(flag)
        return incs, libdirs, libs

    def build(self):
        incs, libdirs, libs = self._probe_flags()
        cc = os.environ.get("CC", "clang")
        cmd = "{} -o test_probe test_libtlog.c {} {}".format(
            cc, " ".join(incs), " ".join(["-L" + p for p in libdirs] + libs))
        self.output.info(cmd)
        self.run(cmd)

        # ── OHOS/musl 特有回归：7 个补丁头的「自包含」编译断言 ──
        # -include 让该头成为这个 TU 的第一个（也是唯一的）include，
        # -x c /dev/null 提供空源；头内若缺 POSIX 类型声明，musl 下即编译失败。
        bad = []
        for name in self.OHOS_PATCHED_HEADERS:
            probe = "{} -fsyntax-only {} -include tlog/{}.h -x c /dev/null".format(
                cc, " ".join(incs), name)
            if self.run(probe, ignore_errors=True) != 0:
                bad.append(name)
        passed = len(self.OHOS_PATCHED_HEADERS) - len(bad)
        self.output.info("OHOS/musl 头自包含: {}/{} 通过".format(
            passed, len(self.OHOS_PATCHED_HEADERS)))
        if bad:
            raise ConanException(
                "OHOS/musl 头文件自包含断言失败（补丁 0004-0010 未生效？）: "
                + ", ".join(bad))

    def test(self):
        if cross_building(self):
            self.output.info("交叉构建：仅验证编译与链接（宿主无法运行目标程序）")
            return
        # 1) libtlog 公开 API（真实调用，断言在 test_libtlog.c）
        self.run("./test_probe", env="conanrun")
        # 2) CLI 功能 + 默认配置加载（上游按「二进制路径」定位配置的规则）；
        #    经 sh 执行，避免依赖脚本的可执行位（HMDFS 上 chmod 不生效，E046）
        dep = self.dependencies["tlog"]
        # 每次都用**新建**目录：HMDFS 上目录权限是固定值（E046/E129），复用上次
        # 运行留下的 cli-run/ 会得到 `cp: ... Operation not permitted`（目录属主
        # 与当前进程用户不同、且只带 x 位），测试随即失败——实测踩中。目录放
        # build_folder 下（写权限必然有，不依赖 /tmp——本平台 /tmp 只读，E002），
        # 跑完即删，避免把临时产物留在仓库树里（CI JC4 会拦）。
        work = os.path.join(self.build_folder, "cli-run-{}".format(os.getpid()))
        sh = os.environ.get("CONFIG_SHELL", "/system/bin/sh")
        cmd = '{} test_cli.sh "{}" "{}"'.format(sh, work, dep.package_folder)
        self.output.info(cmd)
        try:
            self.run(cmd, env="conanrun")
        finally:
            shutil.rmtree(work, ignore_errors=True)
