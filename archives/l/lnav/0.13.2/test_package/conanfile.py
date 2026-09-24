#!/usr/bin/env python3
"""lnav test_package — application 型消费者测试。

test_type=explicit；被测物 = self.tested_reference_str 解析出的包内 bin/lnav
（application 包无库可链）。test.sh 真跑该二进制（R34：实质执行被测物）：
--version 断言、syslog 解析 + SQL 计数（pcre2 格式识别 + sqlite3 查询引擎）、
gzip/bzip2 压缩日志透明解压（zlib/bzip2）、纯文本格式探测负路径（lnav_file
加载成功、format 未识别）、SQL 标量表达式（sqlite3 活性）。
"""
import os

from conan import ConanFile


class LnavTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 运行期共享库直依赖（G2 实测收敛）：bin/lnav 的 DT_NEEDED 是
        # libarchive.so.13 / libcurl.so，且 zlib/bzip2/xz 静态链入 libarchive
        # 后以全局符号再导出（bin/lnav 的 deflate* 为 UND，由 libarchive.so.13
        # 提供；readelf 实测）。conan 对 application 消费者的运行闭包只保留
        # 贡献 runenv/被 package_info 引用的包（实测 necessary =
        # lnav/curl/tzdata，libarchive 落在 Skipped binaries → 不进
        # self.dependencies.host，test() 枚举不到其 libdir → musl 找不到
        # libarchive.so.13 → `deflateBound: symbol not found`，采信轮实测）。
        # 显式声明为直依赖后 libarchive 计入必要包（conan graph install 实测
        # binary=Cache、package_folder 可用），test() 的 libdir 枚举才能拿到它。
        self.requires("libarchive/3.8.7")

    def test(self):
        # 运行期共享库（libarchive.so.13/libcurl.so）只存在于 conan 缓存包
        # 目录（设备 /system/lib 无同名库，实测）：缺任一 libdir 即 musl
        # relocation 失败（deflateBound / curl_easy_cleanup: symbol not
        # found，采信轮实测）。VirtualRunEnv 只导出 lnav 自身 runenv
        # （PATH/TZDIR）与 curl/tzdata 的 libdirs——组件化包的 cpp_info.libdirs
        # 为空，VirtualRunEnv 不为其生成 LD_LIBRARY_PATH——这里直接枚举各依赖
        # 包缓存目录下的 lib/lib64 显式注入 LD_LIBRARY_PATH（zlib 的 libdir
        # 只有静态 libz.a、不可被加载，仅作无害占位；真正 provider 是
        # libarchive.so.13 的再导出符号）。
        ld_dirs = []
        seen = set()
        for dep in self.dependencies.host.values():
            for sub in ("lib", "lib64"):
                d = os.path.join(dep.package_folder, sub)
                if os.path.isdir(d) and d not in seen:
                    seen.add(d)
                    ld_dirs.append(d)
        ld_path = ":".join(ld_dirs)
        script = os.path.join(self.source_folder, "test.sh")
        self.run(
            f'LD_LIBRARY_PATH="{ld_path}:$LD_LIBRARY_PATH" sh "{script}"',
            env="conanrun")
