#!/usr/bin/env python3
"""Conan recipe for dietlibc 0.34-cvs20160606 — 轻量级 libc 静态库（鸿蒙 PC aarch64）。

dietlibc 是一个面向静态链接、体积优先的 C 标准库实现（libc 本体，零外部依赖）。
适配要点：
- 上游构建系统是自定义 Makefile（非 autotools/cmake），通过 ``ARCH`` 与 ``CC`` 交叉编译。
- 交叉编译只构建核心静态库目标（libc.a/dietlibc.a 及子库、start*.o、dyn_start/dyn_stop.o），
  跳过 diet/elftrunc/dnsd（这些需要先用宿主机 diet 包装器做二次交叉，属工具链场景，非库消费所需）。
- 用 Conan copy 手动打包，不用 ``make install``（HarmonyOS 无 GNU install 命令，见知识库 E098）。
- 补丁：Makefile 增加 AR 变量（HarmonyOS 只有 llvm-ar，无 GNU ar）；去掉 ``-fno-integrated-as``
  （HarmonyOS 无 GNU gas，改用 clang 集成汇编器）；aarch64 汇编 ``.type #function`` → ``%function``
  （clang 集成汇编器兼容，与上游 arm 架构写法一致）。
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class DietlibcConan(ConanFile):
    name = "dietlibc"
    version = "0.34-cvs20160606"
    description = "diet libc — a libc optimized for small size and static linking"
    license = "GPL-2.0-or-later"
    homepage = "https://www.fefe.de/dietlibc/"
    # dietlibc 只构建静态库（libc.a 等），无动态库，故用 static-library（避免 Conan 要求 shared option）
    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    # conan arch → dietlibc Makefile ARCH
    _ARCH_MAP = {
        "armv8": "aarch64",
        "armv7": "arm",
        "armv6": "arm",
        "x86_64": "x86_64",
        "x86": "i386",
        "ppc64le": "ppc64le",
        "ppc64": "ppc64",
        "ppc32": "ppc",
        "mips64": "mips64",
        "mips": "mips",
        "sparc": "sparc",
        "sparcv9": "sparc64",
        "s390": "s390",
        "s390x": "s390x",
    }

    def _diet_arch(self):
        return self._ARCH_MAP.get(str(self.settings.arch), str(self.settings.arch))

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # dietlibc 是 libc 本体，零外部依赖（不依赖任何其他库）。
        pass

    def layout(self):
        basic_layout(self)
        # dietlibc 在源码树内构建（Makefile 产物输出到 bin-<ARCH>/）。
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        arch = self._diet_arch()
        # R33: 编译器/归档器从 Conan conf 获取，禁止裸用 shell 环境变量。
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        ar = compilers.get("ar", "") if compilers else ""
        if not ar:
            # 编译环境 PATH 不含 hnp 工具链目录，相对名 llvm-ar 会解析到受限 stub（Permission denied）。
            # 从 CC 同目录推导 llvm-ar 完整路径（clang 与 llvm-ar 同处 hnp/bin）。
            cc_dir = os.path.dirname(cc)
            ar = os.path.join(cc_dir, "llvm-ar") if cc_dir else "llvm-ar"
        # 只构建核心静态库目标，避免 diet/elftrunc/dnsd 的宿主机二次交叉复杂度。
        targets = (
            f"bin-{arch}/start.o "
            f"bin-{arch}/start-pie.o "
            f"bin-{arch}/dyn_start.o "
            f"bin-{arch}/dyn_stop.o "
            f"bin-{arch}/dietlibc.a "
            f"bin-{arch}/libm.a "
            f"bin-{arch}/libpthread.a "
            f"bin-{arch}/librpc.a "
            f"bin-{arch}/liblatin1.a "
            f"bin-{arch}/libcompat.a "
            f"bin-{arch}/libcrypt.a"
        )
        # R9: make -j1（dietlibc 汇编 + 归档在多核下偶发 jobserver/FIFO 问题，且单包错峰）。
        self.run(f'make ARCH={arch} CC="{cc}" AR="{ar}" -j1 {targets}')
        self._run_upstream_tests(cc, arch)

    def _run_upstream_tests(self, cc, arch):
        """编译并运行 dietlibc 上游 test/ 测试套件（runtests.sh 口径）。

        上游用 `diet gcc` 编译测试程序，这里等价改为 clang 静态链接
        （-static -no-pie -nostdlib -nostdinc -D__dietlibc__ + start.o + dietlibc.a +
        builtins + libpthread.a + libcompat.a，--start-group 解循环依赖）。
        """
        import subprocess
        src = self.source_folder
        bindir = os.path.join(src, f"bin-{arch}")
        inc = os.path.join(src, "include")
        try:
            builtins = subprocess.check_output(
                [cc, "-print-libgcc-file-name"], text=True, stderr=subprocess.DEVNULL
            ).strip()
        except Exception:
            builtins = ""
        link = f"-static -no-pie -nostdlib -nostdinc -isystem {inc} -D__dietlibc__"
        group = (
            f"-Wl,--start-group {bindir}/dietlibc.a {builtins} "
            f"{bindir}/libpthread.a {bindir}/libcompat.a -Wl,--end-group"
        )
        objs = f"{bindir}/start.o {bindir}/dyn_start.o {bindir}/dyn_stop.o"
        outdir = os.path.join(self.build_folder, "upstream-tests")
        os.makedirs(outdir, exist_ok=True)

        # (名称, 相对源码路径, 运行参数, 是否经 stdin 喂 "foobar")
        top = [
            "adjtime", "alarm", "argv", "atexit", "bsearch", "byteswap", "calloc",
            "confstr", "empty", "fadvise", "flush", "fputc", "ffs", "fnmatch", "ftw",
            "fwrite", "getaddrinfo", "getenv", "getdelim", "getgrnam", "gethostbyaddr",
            "gethostbyname", "gethostbyname_r", "getmntent", "getopt", "getpwnam",
            "getservbyname", "getservbyport", "getusershell", "glob", "grent",
            "hasmntopt", "hello", "iconv", "if_nameindex", "ltostr", "malloc-debugger",
            "md5_testharness", "memccpy", "memchr", "memcmp", "memrchr", "memusage",
            "mktime", "mmap_test", "pipe", "printf", "printftest", "protoent",
            "prototypes", "putenv", "pwent", "rand48", "readdir", "regex", "select",
            "sendfile", "servent", "siglist", "speed", "spent", "sprintf", "sscanf",
            "stdarg", "strcasecmp", "strcmp", "strncat", "strncpy", "strptime",
            "strrchr", "strstr", "strtol", "sysenter", "ungetc", "utime", "waitpid",
        ]
        subdirs = {
            "dirent": ["opendir-tst1", "tst-seekdir"],
            "inet": ["test_ifindex", "tst-gethnm", "tst-ntoa"],
            "stdio": ["tst-ferror", "tstdiomisc", "tst-fdopen", "tst-fileno",
                      "tst-fphex", "tst-fseek", "tst-printf", "tstscanf",
                      "tst-sprintf", "tst-sscanf", "tst-tmpnam", "tst-unbputc",
                      "tst-ungetc", "tstgetln"],
            "string": ["memccpy", "memchr", "memcmp", "memcpy", "memrchr",
                       "strcasecmp", "strcmp", "strlen", "strncat", "strncpy",
                       "strrchr", "strstr", "strspn", "strcspn", "strpbrk", "mempcpy"],
            "stdlib": ["test-canon", "testdiv", "testrand", "testsort", "tst-calloc",
                       "tst-environ", "tst-limits", "tst-malloc", "tst-rand48",
                       "tst-strtod", "tst-strtol", "tst-strtoll", "tst-system"],
            "time": ["tst-strptime", "tst-mktime", "tst-posixtz", "tst-strftime"],
        }
        tests = []  # (name, relsrc, args, use_stdin)
        for t in top:
            tests.append((t, f"test/{t}.c", "", False))
        for d, names in subdirs.items():
            for t in names:
                tests.append((t, f"test/{d}/{t}.c", "", False))
        tests.append(("asprintf", "test/asprintf.c", "foobar", False))
        tests.append(("cycles", "test/cycles.c", "strncpy", False))
        tests.append(("read1", "test/read1.c", "", True))
        tests.append(("getpass", "test/getpass.c", "", True))

        # 上游 test/stdio/runtests.sh 与 test/stdlib/runtests.sh 给这些读 stdin 的测试
        # 喂固定输入（否则 scanf/getline/fgets 阻塞到 15s timeout 超时）。
        stdin_feed = {
            "tstgetln": ("\n25 54.32E-1 thompson\n56789 0123 56a72\n"
                         "2 quarts of oil\n-12.8degrees Celsius\n"
                         "lots of luck\n10.0LBS      of       fertilizer\n"
                         "100ergs of energy\n"),
            "tst-ferror": ("\n25 54.32E-1 thompson\n56789 0123 56a72\n"
                           "2 quarts of oil\n-12.8degrees Celsius\n"
                           "lots of luck\n10.0LBS      of       fertilizer\n"
                           "100ergs of energy\n"),
            "tstscanf": ("\n25 54.32E-1 thompson\n56789 0123 56a72\n"
                         "2 quarts of oil\n-12.8degrees Celsius\n"
                         "lots of luck\n10.0LBS      of       fertilizer\n"
                         "100ergs of energy\n"),
            "testdiv": ("12 165 12 10000 10 123 546 752 12 87 98 347 "
                        "3186 482 92 3941 7563 865 85371 547 28\n"),
        }

        passed, failed, cfailed = [], [], []
        for name, relsrc, args, use_stdin in tests:
            s = os.path.join(src, relsrc)
            b = os.path.join(outdir, name)
            r = self.run(
                f'{cc} {link} "{s}" {objs} {group} -o "{b}"',
                env="conanbuild", ignore_errors=True,
            )
            if r != 0:
                cfailed.append(name)
                continue
            if name in stdin_feed:
                in_file = os.path.join(outdir, name + ".in")
                with open(in_file, "w") as fh:
                    fh.write(stdin_feed[name])
                run_cmd = f'timeout 15 "./{name}" < "{name}.in"'
            elif use_stdin:
                run_cmd = f'echo foobar | timeout 15 "./{name}"'
            elif args:
                run_cmd = f'timeout 15 "./{name}" {args}'
            else:
                run_cmd = f'timeout 15 "./{name}"'
            # 在 outdir（可写）运行，避免部分测试 fopen("test","wb") 因 cwd 只读而失败（fwrite）。
            r = self.run(run_cmd, cwd=outdir, env="conanbuild", ignore_errors=True)
            (passed if r == 0 else failed).append(name)

        self.output.info(
            f"upstream tests: {len(passed)} passed, {len(failed)} failed, "
            f"{len(cfailed)} compile-failed"
        )
        if failed:
            self.output.warning(f"failed tests: {' '.join(failed)}")
        if cfailed:
            self.output.warning(f"compile-failed tests: {' '.join(cfailed)}")
        # 上游测试失败不阻塞 conan create（libc 部分 syscall/环境依赖在 OHOS 上有边界），
        # 结果如实写入文件供 notes 引用。
        result = os.path.join(self.build_folder, "upstream-tests-summary.txt")
        with open(result, "w") as f:
            f.write(f"passed={len(passed)}\nfailed={len(failed)}\ncompile_failed={len(cfailed)}\n")
            if failed:
                f.write("failed_list=" + " ".join(failed) + "\n")
            if cfailed:
                f.write("compile_failed_list=" + " ".join(cfailed) + "\n")

    def package(self):
        arch = self._diet_arch()
        src = self.source_folder
        bindir = os.path.join(src, f"bin-{arch}")
        inc_src = os.path.join(src, "include")
        inc_dst = os.path.join(self.package_folder, "include")
        lib_dst = os.path.join(self.package_folder, "lib")
        # 头文件：227 个 *.h（含 arpa/asm/linux/net/sys 等子目录）＋ 5 个 C++ 头（clocale 等无扩展名）。
        copy(self, "*.h", inc_src, inc_dst, keep_path=True)
        for name in ("clocale", "cstddef", "cstdlib", "cwchar", "cwctype"):
            copy(self, name, inc_src, inc_dst)
        # 静态库 + 启动对象文件。
        for f in (
            "dietlibc.a", "libm.a", "libpthread.a", "librpc.a",
            "liblatin1.a", "libcompat.a", "libcrypt.a",
            "start.o", "start-pie.o", "dyn_start.o", "dyn_stop.o",
        ):
            copy(self, f, bindir, lib_dst)

    def package_info(self):
        # 主库 dietlibc.a 即 libc.a；消费者需自行传入 start.o 并使用 -nostdlib。
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = ["lib"]
        self.cpp_info.libs = ["dietlibc"]
